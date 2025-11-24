#!/usr/bin/env python3
"""
系統監控 Web 界面
提供簡單的狀態顯示和圖表生成功能
"""

import sys
import os
from pathlib import Path
from datetime import datetime

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
PROJECT_ROOT = BACKEND_ROOT.parent

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import uvicorn
from pydantic import BaseModel
from typing import List

from system_monitor.core import SystemMonitorCollector, MonitoringDatabase, SystemMonitorVisualizer
from system_monitor.core.weekly_db_manager import weekly_db_manager
from system_monitor.utils import Config

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
templates = Jinja2Templates(directory=str(BACKEND_ROOT / "webui" / "templates"))
app.mount("/static", StaticFiles(directory=str(BACKEND_ROOT / "webui" / "static")), name="static")

# 提供 React 前端（如果存在 frontend/dist）
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

# 初始化組件
config = Config()
collector = SystemMonitorCollector()
# 使用週週分檔系統
weekly_db_manager.ensure_current_database_exists()
database = MonitoringDatabase(weekly_db_manager.get_current_database_path())
visualizer = SystemMonitorVisualizer()

class PlotProcessesRequest(BaseModel):
    pids: List[int]
    timespan: str = "1h"
    database_file: str = "monitoring.db"


@app.get("/api/databases")
async def get_databases():
    """獲取所有資料庫列表（包含週資料庫和其他 .db 檔案）"""
    try:
        import glob

        # 獲取週資料庫
        weekly_databases = weekly_db_manager.list_all_weekly_databases()
        weekly_filenames = {db['filename'] for db in weekly_databases}

        # 掃描 data/ 目錄下所有 .db 檔案
        data_dir = Path("data")
        all_db_files = list(data_dir.glob("*.db"))

        other_databases = []
        for db_file in all_db_files:
            if db_file.name not in weekly_filenames:
                # 非週格式的資料庫
                file_size = db_file.stat().st_size / (1024 * 1024)  # MB
                mtime = datetime.fromtimestamp(db_file.stat().st_mtime)

                other_databases.append({
                    'filename': db_file.name,
                    'full_path': str(db_file),
                    'display_name': f"📁 {db_file.stem}",
                    'size_mb': round(file_size, 2),
                    'is_current': False,
                    'year': mtime.year,
                    'week': 0,
                    'start_date': mtime.strftime('%Y-%m-%d'),
                    'end_date': mtime.strftime('%Y-%m-%d'),
                    'is_external': True  # 標記為外部資料庫
                })

        # 合併列表：週資料庫在前，其他資料庫在後
        all_databases = weekly_databases + sorted(other_databases, key=lambda x: x['filename'])

        return {
            "success": True,
            "databases": all_databases,
            "current_database": weekly_db_manager.get_current_database_path()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sources")
async def get_sources(database_file: str = None):
    """獲取資料庫中的所有來源（主機）"""
    try:
        from system_monitor.core import MonitoringDatabase

        if database_file:
            if not database_file.startswith('data/'):
                database_file = f"data/{database_file}"
            db_instance = MonitoringDatabase(database_file)
        else:
            db_instance = database

        # 查詢所有不重複的 source
        sources = set()
        with db_instance._get_connection() as conn:
            cursor = conn.cursor()

            # 從各表獲取來源
            for table in ['system_metrics', 'gpu_metrics', 'gpu_processes']:
                try:
                    cursor.execute(f"SELECT DISTINCT source FROM {table} WHERE source IS NOT NULL")
                    for row in cursor.fetchall():
                        if row[0]:
                            sources.add(row[0])
                except Exception:
                    pass

        return {
            "success": True,
            "sources": sorted(list(sources)),
            "count": len(sources)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "sources": []}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主頁面 - 優先使用 React 前端"""
    frontend_index = frontend_dist / "index.html"
    if frontend_index.exists():
        # 提供 React 前端
        with open(frontend_index, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        # 回退到舊版模板
        return templates.TemplateResponse("index.html", {"request": request})



@app.get("/api/status")
async def get_status():
    """獲取系統狀態API"""
    try:
        # 獲取當前狀態
        try:
            current_data = collector.collect_simple()
        except Exception as e:
            print(f"❌ collect_simple 失敗: {e}")
            current_data = {
                'cpu_usage': 0, 'ram_usage': 0, 'ram_used_gb': 0, 'ram_total_gb': 0,
                'gpu_usage': None, 'vram_usage': None, 'vram_used_mb': None, 'vram_total_mb': None,
                'gpu_temperature': None, 'cpu_source': 'error', 'ram_source': 'error'
            }
        
        # 獲取資料庫統計
        try:
            stats = database.get_statistics()
        except Exception as e:
            print(f"❌ database.get_statistics 失敗: {e}")
            stats = {
                'total_records': 0, 'database_size_mb': 0, 'earliest_record': None
            }
        
        # 獲取系統資訊
        import socket
        import platform
        import os
        import urllib.request

        # 獲取主機名（優先從掛載的 /etc/hostname 讀取）
        hostname = socket.gethostname()
        try:
            host_hostname_path = "/host/etc/hostname"
            if os.path.exists(host_hostname_path):
                with open(host_hostname_path, 'r') as f:
                    hostname = f.read().strip()
        except Exception:
            pass

        # 獲取外網 IP 地址
        external_ip = None
        try:
            with urllib.request.urlopen("https://ifconfig.me/ip", timeout=3) as resp:
                external_ip = resp.read().decode('utf-8').strip()
        except Exception:
            pass

        # 備用：獲取內網 IP
        local_ip = external_ip
        if not local_ip:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "127.0.0.1"

        system_info = {
            "hostname": hostname,
            "platform": platform.system(),
            "cpu_count": os.cpu_count(),
            "local_ip": local_ip,
        }
        
        # 獲取 GPU 資訊 - 支援多張 GPU
        gpu_list = []
        if collector.is_gpu_available():
            try:
                gpu_stats = collector.gpu_collector.get_gpu_stats()
                if gpu_stats and isinstance(gpu_stats, list):
                    # GPU 資訊是列表格式，保存所有 GPU
                    gpu_list = gpu_stats
                    # 為了向後兼容，保留第一張GPU的資訊在 system_info 中
                    if len(gpu_stats) > 0:
                        first_gpu = gpu_stats[0]
                        system_info["gpu_name"] = first_gpu.get("gpu_name", "Unknown GPU")
                        system_info["gpu_memory_total"] = first_gpu.get("vram_total_mb", 0)
                elif gpu_stats and isinstance(gpu_stats, dict):
                    # 單GPU舊格式相容
                    gpu_list = [gpu_stats]
                    system_info["gpu_name"] = gpu_stats.get("gpu_name", "Unknown GPU")
                    system_info["gpu_memory_total"] = gpu_stats.get("vram_total_mb", 0)
            except Exception as e:
                # GPU 資訊獲取失敗，使用預設值
                pass
        
        return {
            **current_data,
            **stats,
            "gpu_available": collector.is_gpu_available(),
            "gpu_list": gpu_list,  # 新增：所有 GPU 的詳細資訊列表
            "system_info": system_info
        }
    except Exception as e:
        print(f"❌ /api/status 錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PlotRequest(BaseModel):
    database_file: str | None = None

@app.post("/api/plot/{timespan}")
async def generate_plot(timespan: str, background_tasks: BackgroundTasks,
                       req: PlotRequest = None):
    """生成圖表API - 支援週週分檔多資料庫"""
    try:
        # 決定使用哪個資料庫
        database_file = req.database_file if req and req.database_file else None

        from system_monitor.core import MonitoringDatabase

        if database_file and database_file != "monitoring.db":
            # 使用指定的單一資料庫
            if not database_file.startswith('data/'):
                database_file = f"data/{database_file}"
            custom_database = MonitoringDatabase(database_file)
            metrics = custom_database.get_metrics_by_timespan(timespan)
            db_name = Path(database_file).name
        else:
            # 使用週週分檔系統，自動合併多個資料庫
            db_paths = weekly_db_manager.get_database_for_timespan(timespan)
            all_metrics = []
            for db_path in db_paths:
                if os.path.exists(db_path):
                    temp_db = MonitoringDatabase(db_path)
                    db_metrics = temp_db.get_metrics_by_timespan(timespan)
                    if db_metrics:
                        all_metrics.extend(db_metrics)
            
            # 按時間排序
            all_metrics.sort(key=lambda x: x.get('timestamp', ''))
            metrics = all_metrics
            db_name = f"週週分檔系統 ({len(db_paths)} 個資料庫)"
        
        if not metrics:
            return {"success": False, "error": f"資料庫 {db_name} 中沒有 {timespan} 時間範圍的數據"}
        
        # 生成圖表（只生成 1 張圖：CPU+RAM 和 GPU+VRAM）
        charts = []

        overview_path = await run_in_threadpool(visualizer.plot_system_overview, metrics, timespan=timespan)
        charts.append({"title": f"系統概覽 ({db_name})", "path": Path(overview_path).relative_to("plots")})

        return {"success": True, "charts": charts, "database": db_name}

    except Exception as e:
        return {"success": False, "error": str(e)}


class MultiGPUPlotRequest(BaseModel):
    gpu_ids: List[int] | None = None  # None = all GPUs
    database_file: str | None = None


@app.post("/api/plot/gpu/{timespan}")
async def generate_gpu_plot(timespan: str, req: MultiGPUPlotRequest = None):
    """生成多 GPU 對比圖表 API"""
    try:
        gpu_ids = req.gpu_ids if req else None
        database_file = req.database_file if req and req.database_file else None

        from system_monitor.core import MonitoringDatabase

        # 獲取 GPU 指標數據
        if database_file:
            if not database_file.startswith('data/'):
                database_file = f"data/{database_file}"
            db_instance = MonitoringDatabase(database_file)
            db_name = Path(database_file).name
        else:
            # 使用週週分檔系統
            db_paths = weekly_db_manager.get_database_for_timespan(timespan)
            all_metrics = []
            for db_path in db_paths:
                if os.path.exists(db_path):
                    temp_db = MonitoringDatabase(db_path)
                    db_metrics = temp_db.get_gpu_metrics_by_timespan(timespan, gpu_id=None)
                    if db_metrics:
                        all_metrics.extend(db_metrics)

            if not all_metrics:
                return {"success": False, "error": f"沒有 GPU 指標數據"}

            # 生成圖表
            chart_path = await run_in_threadpool(visualizer.plot_multi_gpu, all_metrics, gpu_ids=gpu_ids, timespan=timespan)

            return {
                "success": True,
                "chart": {
                    "title": f"多 GPU 監控 ({timespan})",
                    "path": str(Path(chart_path).relative_to("plots"))
                },
                "gpu_count": len(set(m.get('gpu_id') for m in all_metrics)),
                "database": f"週週分檔系統 ({len(db_paths)} 個資料庫)"
            }

        # 單一資料庫模式
        gpu_metrics = db_instance.get_gpu_metrics_by_timespan(timespan, gpu_id=None)
        if not gpu_metrics:
            return {"success": False, "error": f"資料庫 {db_name} 中沒有 GPU 指標數據"}

        chart_path = await run_in_threadpool(visualizer.plot_multi_gpu, gpu_metrics, gpu_ids=gpu_ids, timespan=timespan)

        return {
            "success": True,
            "chart": {
                "title": f"多 GPU 監控 ({timespan})",
                "path": str(Path(chart_path).relative_to("plots"))
            },
            "gpu_count": len(set(m.get('gpu_id') for m in gpu_metrics)),
            "database": db_name
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/gpu-list")
async def get_gpu_list():
    """獲取可用的 GPU 列表"""
    try:
        # 從當前資料庫獲取 GPU 列表
        gpu_metrics = database.get_gpu_metrics_by_timespan("1h")

        gpu_map = {}
        for m in gpu_metrics:
            gpu_id = m.get('gpu_id')
            if gpu_id is not None and gpu_id not in gpu_map:
                gpu_map[gpu_id] = {
                    "gpu_id": gpu_id,
                    "gpu_name": m.get('gpu_name', f'GPU {gpu_id}')
                }

        gpu_list = sorted(gpu_map.values(), key=lambda x: x['gpu_id'])

        return {
            "success": True,
            "gpus": gpu_list
        }
    except Exception as e:
        return {"success": False, "error": str(e), "gpus": []}


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
        from system_monitor.core import MonitoringDatabase
        
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
        # 驗證PID列表
        if not req.pids or len(req.pids) == 0:
            return {"success": False, "error": "請至少選擇一個有效的PID"}
        
        # 確保所有PID都是有效的整數
        for pid in req.pids:
            if not isinstance(pid, int) or pid <= 0:
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

        # 2. 決定使用哪個資料庫
        database_file = req.database_file if req.database_file else "monitoring.db"
        
        if database_file != "monitoring.db":
            # 使用指定的資料庫，確保在 data/ 目錄下
            if not database_file.startswith('data/'):
                database_file = f"data/{database_file}"
            from system_monitor.core import MonitoringDatabase
            custom_database = MonitoringDatabase(database_file)
            db_instance = custom_database
        else:
            # 使用預設資料庫
            db_instance = database
        
        # 3. 從資料庫獲取所有選定PID的數據
        process_data = db_instance.get_processes_by_pids(req.pids, start_time, now)

        if not process_data:
            return {"success": False, "error": f"在指定時間範圍內沒有找到任何選定PID的數據。"}

        # 4. 調用 visualizer 生成圖表
        chart_path = await run_in_threadpool(visualizer.plot_process_comparison, process_data, req.pids, req.timespan)

        return {
            "success": True,
            "chart": {
                "title": f"進程對比圖 ({len(req.pids)} 個進程)",
                "path": Path(chart_path).relative_to("plots")
            }
        }
    except Exception as e:
        error_msg = f"生成圖表時發生錯誤: {str(e)}"
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
            
        chart_path = await run_in_threadpool(
            visualizer.plot_process_timeline,
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
app.mount("/plots", StaticFiles(directory=str(PROJECT_ROOT / "plots")), name="plots")

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
    
    print(f"🌐 啟動 Web 界面: http://{args.host}:{args.port}")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
