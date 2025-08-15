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
from pydantic import BaseModel
from typing import List

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

class PlotProcessesRequest(BaseModel):
    pids: List[int]
    timespan: str = "1h"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主頁面"""
    return templates.TemplateResponse("index.html", {"request": request})



@app.get("/api/status")
async def get_status():
    """獲取系統狀態API"""
    try:
        # 獲取當前狀態
        try:
            current_data = collector.collect_simple()
            print(f"[DEBUG] current_data 獲取成功")
        except Exception as e:
            print(f"[ERROR] collect_simple() 失敗: {e}")
            import traceback
            traceback.print_exc()
            current_data = {
                'cpu_usage': 0, 'ram_usage': 0, 'ram_used_gb': 0, 'ram_total_gb': 0,
                'gpu_usage': None, 'vram_usage': None, 'vram_used_mb': None, 'vram_total_mb': None,
                'gpu_temperature': None, 'cpu_source': 'error', 'ram_source': 'error'
            }
        
        # 獲取資料庫統計
        try:
            stats = database.get_statistics()
            print(f"[DEBUG] database stats 獲取成功")
        except Exception as e:
            print(f"[ERROR] database.get_statistics() 失敗: {e}")
            import traceback
            traceback.print_exc()
            stats = {
                'total_records': 0, 'database_size_mb': 0, 'earliest_record': None
            }
        
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
            except Exception as e:
                print(f"[ERROR] GPU資訊獲取失敗: {e}")
                # 如果獲取 GPU 資訊失敗，使用預設值
                pass
        
        return {
            **current_data,
            **stats,
            "gpu_available": collector.is_gpu_available(),
            "system_info": system_info
        }
    except Exception as e:
        print(f"[ERROR] /api/status 總體錯誤: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class PlotRequest(BaseModel):
    database_file: str = "monitoring.db"

@app.post("/api/plot/{timespan}")
async def generate_plot(timespan: str, background_tasks: BackgroundTasks, 
                       req: PlotRequest = None):
    """生成圖表API - 支援多資料庫"""
    try:
        # 決定使用哪個資料庫
        database_file = req.database_file if req and req.database_file else "monitoring.db"
        
        if database_file != "monitoring.db":
            # 使用指定的資料庫，確保在 data/ 目錄下
            if not database_file.startswith('data/'):
                database_file = f"data/{database_file}"
            from core import MonitoringDatabase
            custom_database = MonitoringDatabase(database_file)
            metrics = custom_database.get_metrics_by_timespan(timespan)
            db_name = database_file
        else:
            # 使用預設資料庫
            metrics = database.get_metrics_by_timespan(timespan)
            db_name = "monitoring.db"
        
        if not metrics:
            return {"success": False, "error": f"資料庫 {db_name} 中沒有 {timespan} 時間範圍的數據"}
        
        # 生成圖表
        charts = []
        
        overview_path = visualizer.plot_system_overview(metrics, timespan=timespan)
        charts.append({"title": f"系統概覽 ({db_name})", "path": Path(overview_path).relative_to("plots")})
        
        comparison_path = visualizer.plot_resource_comparison(metrics)
        charts.append({"title": f"資源對比 ({db_name})", "path": Path(comparison_path).relative_to("plots")})
        
        memory_path = visualizer.plot_memory_usage(metrics)
        charts.append({"title": f"記憶體使用 ({db_name})", "path": Path(memory_path).relative_to("plots")})
        
        distribution_path = visualizer.plot_usage_distribution(metrics)
        charts.append({"title": f"使用率分佈 ({db_name})", "path": Path(distribution_path).relative_to("plots")})
        
        return {"success": True, "charts": charts, "database": db_name}
        
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

@app.post("/api/all-processes/{timespan}")
async def get_all_processes(timespan: str, req: PlotRequest = None):
    """獲取指定時間範圍內的所有歷史進程（包括已結束的）- 支援多資料庫"""
    try:
        from datetime import datetime, timedelta
        from core import MonitoringDatabase
        
        # 決定使用哪個資料庫
        database_file = req.database_file if req and req.database_file else "monitoring.db"
        
        if database_file != "monitoring.db":
            # 使用指定的資料庫，確保在 data/ 目錄下
            if not database_file.startswith('data/'):
                database_file = f"data/{database_file}"
            custom_database = MonitoringDatabase(database_file)
            db_instance = custom_database
        else:
            # 使用預設資料庫
            db_instance = database
        
        # 計算時間範圍
        now = datetime.now()
        if timespan.endswith('m'):
            minutes = int(timespan[:-1])
            start_time = now - timedelta(minutes=minutes)
        elif timespan.endswith('h'):
            hours = int(timespan[:-1])
            start_time = now - timedelta(hours=hours)
        elif timespan.endswith('d'):
            days = int(timespan[:-1])
            start_time = now - timedelta(days=days)
        else:
            start_time = now - timedelta(hours=24)  # 預設24小時
        
        # 獲取該時間範圍內的所有進程（包括已結束的）
        all_processes = db_instance.get_unique_processes_in_timespan(start_time, now)
        
        return {
            "success": True,
            "processes": all_processes,
            "timespan": timespan,
            "count": len(all_processes),
            "database": database_file
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/processes/plot-comparison")
async def plot_multiple_processes(req: PlotProcessesRequest):
    """為多個指定PID生成對比圖表"""
    try:
        print(f"🔍 接收到進程對比繪圖請求")
        print(f"   PIDs: {req.pids} (類型: {type(req.pids)})")
        print(f"   時間範圍: {req.timespan}")
        
        # 驗證PID列表
        if not req.pids or len(req.pids) == 0:
            return {"success": False, "error": "請至少選擇一個有效的PID"}
        
        # 確保所有PID都是有效的整數
        for i, pid in enumerate(req.pids):
            print(f"   PID[{i}]: {pid} (類型: {type(pid)})")
            if not isinstance(pid, int) or pid <= 0:
                print(f"❌ 無效的PID: {pid}")
                return {"success": False, "error": f"PID列表包含無效值: {pid}"}
        from datetime import datetime, timedelta

        # 1. 計算時間範圍
        now = datetime.now()
        if req.timespan.endswith('m'):
            minutes = int(req.timespan[:-1])
            start_time = now - timedelta(minutes=minutes)
        elif req.timespan.endswith('h'):
            hours = int(req.timespan[:-1])
            start_time = now - timedelta(hours=hours)
        elif req.timespan.endswith('d'):
            days = int(req.timespan[:-1])
            start_time = now - timedelta(days=days)
        else:
            start_time = now - timedelta(hours=1) # 預設1小時

        # 2. 從資料庫獲取所有選定PID的數據
        process_data = database.get_processes_by_pids(req.pids, start_time, now)

        if not process_data:
            return {"success": False, "error": f"在指定時間範圍內沒有找到任何選定PID的數據。"}
        
        # 調試：打印數據結構
        print(f"🔍 找到 {len(process_data)} 條進程數據")
        if process_data:
            print(f"   第一條數據的欄位: {list(process_data[0].keys())}")
            print(f"   第一條數據: {process_data[0]}")

        # 3. 調用 visualizer 生成圖表
        chart_path = visualizer.plot_process_comparison(process_data, req.pids, req.timespan)

        return {
            "success": True,
            "chart": {
                "title": f"進程對比圖 ({len(req.pids)} 個進程)",
                "path": Path(chart_path).relative_to("plots")
            }
        }
    except Exception as e:
        import traceback
        error_msg = f"生成圖表時發生錯誤: {str(e)}"
        print(f"❌ 進程圖表生成錯誤: {error_msg}")
        print(f"   錯誤詳情: {traceback.format_exc()}")
        return {"success": False, "error": error_msg}


@app.post("/api/plot/process/{timespan}")
async def generate_process_plot(timespan: str, background_tasks: BackgroundTasks, 
                               process_name: str = None, command_filter: str = None,
                               pid: int = None, group_by_pid: bool = True):
    """生成進程特定圖表API"""
    try:
        from datetime import datetime, timedelta
        
        # 計算時間範圍
        now = datetime.now()
        if timespan.endswith('h'):
            hours = int(timespan[:-1])
            start_time = now - timedelta(hours=hours)
        elif timespan.endswith('d'):
            days = int(timespan[:-1])
            start_time = now - timedelta(days=days)
        else:
            start_time = now - timedelta(hours=24)
        
        # 獲取進程數據
        process_data = database.get_gpu_processes(
            start_time=start_time,
            end_time=now,
            pid=pid,
            process_name=process_name,
            command_filter=command_filter
        )
        
        if not process_data:
            filter_desc = []
            if pid: filter_desc.append(f"PID {pid}")
            if process_name: filter_desc.append(f"進程名 '{process_name}'")
            if command_filter: filter_desc.append(f"指令 '{command_filter}'")
            filter_str = ", ".join(filter_desc) if filter_desc else "所有條件"
            return {"success": False, "error": f"沒有找到匹配 {filter_str} 的進程數據"}
        
        # 生成進程圖表
        if pid:
            filter_name = f"PID {pid}"
        elif process_name and command_filter:
            filter_name = f"{process_name} ({command_filter})"
        elif process_name:
            filter_name = process_name
        elif command_filter:
            filter_name = command_filter
        else:
            filter_name = "All Processes"
            
        chart_path = visualizer.plot_process_timeline(
            process_data, 
            process_name=filter_name, 
            timespan=timespan,
            group_by_pid=group_by_pid
        )
        
        return {
            "success": True, 
            "chart": {"title": f"Process Timeline: {filter_name}", 
                     "path": Path(chart_path).relative_to("plots")},
            "data_count": len(process_data)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# 靜態文件服務
app.mount("/plots", StaticFiles(directory="plots"), name="plots")

@app.get("/favicon.ico")
async def favicon():
    """返回空的favicon，避免404錯誤"""
    from fastapi.responses import Response
    return Response(status_code=204)  # No Content

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="系統監控 Web 界面")
    parser.add_argument('--host', default='0.0.0.0', help='綁定主機地址')
    parser.add_argument('--port', type=int, default=int(os.getenv('WEB_PORT', 5000)), help='綁定端口')
    
    args = parser.parse_args()
    
    print(f"🌐 啟動 Web 界面...")
    print(f"📍 訪問地址: http://{args.host}:{args.port}")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")