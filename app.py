#!/usr/bin/env python3
"""
系統監控 Web 界面
提供簡單的狀態顯示和圖表生成功能
"""

import sys
import os
from pathlib import Path

# 添加 src 目錄到 Python 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core import SystemMonitorCollector, MonitoringDatabase, SystemMonitorVisualizer
from utils import Config

# 創建 FastAPI 應用
app = FastAPI(title="System Monitor", description="系統監控 Web 界面", version="1.0")

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 設置模板和靜態文件
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化組件
config = Config()
collector = SystemMonitorCollector()
database = MonitoringDatabase(config.database_path)
visualizer = SystemMonitorVisualizer()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主頁面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    """獲取系統狀態API"""
    try:
        # 獲取當前狀態
        current_data = collector.collect_simple()
        
        # 獲取資料庫統計
        stats = database.get_statistics()
        
        # 獲取系統資訊
        import socket
        import platform
        import os
        
        # 獲取本機 IP 地址
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        
        system_info = {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "cpu_count": os.cpu_count(),
            "local_ip": local_ip,
        }
        
        # 獲取 GPU 資訊
        if collector.is_gpu_available():
            try:
                gpu_stats = collector.gpu_collector.get_gpu_stats()
                if gpu_stats and isinstance(gpu_stats, list) and len(gpu_stats) > 0:
                    # GPU 資訊是列表格式，取第一個 GPU
                    first_gpu = gpu_stats[0]
                    system_info["gpu_name"] = first_gpu.get("gpu_name", "Unknown GPU")
                    system_info["gpu_memory_total"] = first_gpu.get("vram_total_mb", 0)
                elif gpu_stats and isinstance(gpu_stats, dict):
                    system_info["gpu_name"] = gpu_stats.get("gpu_name", "Unknown GPU")
                    system_info["gpu_memory_total"] = gpu_stats.get("vram_total_mb", 0)
            except Exception:
                # 如果獲取 GPU 資訊失敗，使用預設值
                pass
        
        return {
            **current_data,
            **stats,
            "gpu_available": collector.is_gpu_available(),
            "system_info": system_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/plot/{timespan}")
async def generate_plot(timespan: str, background_tasks: BackgroundTasks):
    """生成圖表API"""
    try:
        # 獲取數據
        metrics = database.get_metrics_by_timespan(timespan)
        
        if not metrics:
            return {"success": False, "error": "沒有數據可生成圖表"}
        
        # 生成圖表
        charts = []
        
        overview_path = visualizer.plot_system_overview(metrics, timespan=timespan)
        charts.append({"title": "系統概覽", "path": Path(overview_path).relative_to("plots")})
        
        comparison_path = visualizer.plot_resource_comparison(metrics)
        charts.append({"title": "資源對比", "path": Path(comparison_path).relative_to("plots")})
        
        memory_path = visualizer.plot_memory_usage(metrics)
        charts.append({"title": "記憶體使用", "path": Path(memory_path).relative_to("plots")})
        
        distribution_path = visualizer.plot_usage_distribution(metrics)
        charts.append({"title": "使用率分佈", "path": Path(distribution_path).relative_to("plots")})
        
        return {"success": True, "charts": charts}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/gpu-processes")
async def get_gpu_processes():
    """獲取GPU進程信息API"""
    try:
        current_processes = collector.get_top_gpu_processes(limit=10)
        historical_processes = database.get_top_gpu_processes_by_timespan('1h', 5)
        
        return {
            "current": current_processes or [],
            "historical": historical_processes or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 靜態文件服務
app.mount("/plots", StaticFiles(directory="plots"), name="plots")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="系統監控 Web 界面")
    parser.add_argument('--host', default='0.0.0.0', help='綁定主機地址')
    parser.add_argument('--port', type=int, default=5000, help='綁定端口')
    
    args = parser.parse_args()
    
    print(f"🌐 啟動 Web 界面...")
    print(f"📍 訪問地址: http://{args.host}:{args.port}")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")