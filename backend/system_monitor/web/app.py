#!/usr/bin/env python3
"""
FastAPI Web 應用
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from src.core import SystemMonitorCollector, MonitoringDatabase, SystemMonitorVisualizer


def create_app(monitor_instance=None):
    """創建 FastAPI Web 應用"""
    app = FastAPI(title="系統監控工具", description="GPU/CPU/RAM 監控與可視化", version="1.0")
    
    # 添加 CORS 中間件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 如果沒有傳入監控實例，創建新的
    if monitor_instance is None:
        collector = SystemMonitorCollector()
        database = MonitoringDatabase("data/monitoring.db")
        visualizer = SystemMonitorVisualizer()
        monitor_running = False
    else:
        collector = monitor_instance.collector
        database = monitor_instance.database
        visualizer = monitor_instance.visualizer
        monitor_running = monitor_instance.running
    
    # HTML 模板
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系統監控儀表板</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #333; margin: 0; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h3 { margin: 0 0 10px 0; color: #333; }
        .card .value { font-size: 24px; font-weight: bold; color: #4CAF50; }
        .card .unit { font-size: 14px; color: #666; }
        .controls { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .controls h3 { margin: 0 0 15px 0; }
        .btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
        .btn:hover { background: #45a049; }
        .btn.secondary { background: #008CBA; }
        .btn.secondary:hover { background: #007bb5; }
        .btn.danger { background: #f44336; }
        .btn.danger:hover { background: #da190b; }
        .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
        .status.running { background: #d4edda; color: #155724; }
        .status.stopped { background: #f8d7da; color: #721c24; }
        .plots { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-top: 20px; }
        .plot-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .plot-card img { width: 100%; height: auto; border-radius: 4px; }
        select { padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-right: 10px; }
        .stats { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 20px; }
        .stats table { width: 100%; border-collapse: collapse; }
        .stats th, .stats td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .stats th { background-color: #f8f9fa; }
    </style>
    <script>
        let autoRefresh = false;
        let refreshInterval;
        
        async function fetchData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }
        
        function updateDashboard(data) {
            document.getElementById('cpu-value').textContent = data.current.cpu_usage.toFixed(1);
            document.getElementById('ram-value').textContent = data.current.ram_usage.toFixed(1);
            document.getElementById('ram-used').textContent = data.current.ram_used_gb.toFixed(1) + '/' + data.current.ram_total_gb.toFixed(1) + ' GB';
            
            if (data.current.gpu_usage !== null) {
                document.getElementById('gpu-value').textContent = data.current.gpu_usage.toFixed(1);
                document.getElementById('vram-value').textContent = data.current.vram_usage.toFixed(1);
                document.getElementById('vram-used').textContent = (data.current.vram_used_mb/1024).toFixed(1) + '/' + (data.current.vram_total_mb/1024).toFixed(1) + ' GB';
                document.getElementById('gpu-temp').textContent = data.current.gpu_temperature + ' °C';
            } else {
                document.getElementById('gpu-card').style.display = 'none';
                document.getElementById('vram-card').style.display = 'none';
                document.getElementById('temp-card').style.display = 'none';
            }
            
            // Update status
            const statusEl = document.getElementById('monitor-status');
            statusEl.textContent = data.monitoring ? '監控運行中' : '監控已停止';
            statusEl.className = 'status ' + (data.monitoring ? 'running' : 'stopped');
            
            // Update stats
            document.getElementById('total-records').textContent = data.stats.total_records.toLocaleString();
            document.getElementById('db-size').textContent = data.stats.database_size_mb + ' MB';
        }
        
        async function generatePlots() {
            const timespan = document.getElementById('timespan').value;
            try {
                const response = await fetch('/api/plots?timespan=' + timespan, { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    loadPlots();
                    alert('圖表生成成功');
                } else {
                    alert('圖表生成失敗: ' + result.message);
                }
            } catch (error) {
                alert('操作失敗: ' + error.message);
            }
        }
        
        async function loadPlots() {
            try {
                const response = await fetch('/api/plots');
                const plots = await response.json();
                const plotsContainer = document.getElementById('plots-container');
                plotsContainer.innerHTML = '';
                
                plots.forEach(plot => {
                    const plotCard = document.createElement('div');
                    plotCard.className = 'plot-card';
                    plotCard.innerHTML = `
                        <h4>${plot.title}</h4>
                        <img src="/plots/${plot.filename}" alt="${plot.title}">
                        <p><small>生成時間: ${new Date(plot.created).toLocaleString()}</small></p>
                    `;
                    plotsContainer.appendChild(plotCard);
                });
            } catch (error) {
                console.error('Error loading plots:', error);
            }
        }
        
        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const btn = document.getElementById('refresh-btn');
            
            if (autoRefresh) {
                btn.textContent = '停止自動更新';
                refreshInterval = setInterval(fetchData, 5000);
                fetchData();
            } else {
                btn.textContent = '開始自動更新';
                clearInterval(refreshInterval);
            }
        }
        
        // 頁面載入時執行
        document.addEventListener('DOMContentLoaded', function() {
            fetchData();
            loadPlots();
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ 系統監控儀表板</h1>
        </div>
        
        <div class="cards">
            <div class="card">
                <h3>🖥️ CPU 使用率</h3>
                <div class="value" id="cpu-value">--</div>
                <div class="unit">%</div>
            </div>
            <div class="card">
                <h3>💾 RAM 使用率</h3>
                <div class="value" id="ram-value">--</div>
                <div class="unit">% (<span id="ram-used">--</span>)</div>
            </div>
            <div class="card" id="gpu-card">
                <h3>🎮 GPU 使用率</h3>
                <div class="value" id="gpu-value">--</div>
                <div class="unit">%</div>
            </div>
            <div class="card" id="vram-card">
                <h3>📈 VRAM 使用率</h3>
                <div class="value" id="vram-value">--</div>
                <div class="unit">% (<span id="vram-used">--</span>)</div>
            </div>
            <div class="card" id="temp-card">
                <h3>🌡️ GPU 溫度</h3>
                <div class="value" id="gpu-temp">--</div>
            </div>
        </div>
        
        <div class="controls">
            <h3>📊 圖表生成</h3>
            <select id="timespan">
                <option value="1h">過去 1 小時</option>
                <option value="6h">過去 6 小時</option>
                <option value="24h" selected>過去 24 小時</option>
                <option value="7d">過去 7 天</option>
                <option value="30d">過去 30 天</option>
            </select>
            <button class="btn secondary" onclick="generatePlots()">生成圖表</button>
            <button class="btn secondary" id="refresh-btn" onclick="toggleAutoRefresh()">開始自動更新</button>
        </div>
        
        <div class="stats">
            <h3>📈 數據庫統計</h3>
            <table>
                <tr><th>總記錄數</th><td id="total-records">--</td></tr>
                <tr><th>數據庫大小</th><td id="db-size">--</td></tr>
            </table>
        </div>
        
        <div class="plots" id="plots-container">
            <!-- 圖表將在這裡載入 -->
        </div>
    </div>
</body>
</html>
    """
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return HTMLResponse(content=HTML_TEMPLATE)
    
    @app.get("/api/status")
    async def api_status():
        try:
            # 獲取當前系統狀態
            current_data = collector.collect_simple()
            
            # 獲取數據庫統計
            db_stats = database.get_statistics()
            
            return {
                'monitoring': monitor_running,
                'current': current_data,
                'stats': db_stats
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/plots")
    async def api_plots_get():
        # GET: 返回可用的圖片列表
        try:
            plots_dir = visualizer.output_dir
            plots = []
            
            if plots_dir.exists():
                for plot_file in plots_dir.glob('*.png'):
                    stat = plot_file.stat()
                    plots.append({
                        'filename': plot_file.name,
                        'title': plot_file.stem.replace('_', ' ').title(),
                        'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'size': stat.st_size
                    })
            
            # 按創建時間排序
            plots.sort(key=lambda x: x['created'], reverse=True)
            
            return plots
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plots")
    async def api_plots_post(timespan: str = "24h"):
        try:
            # 生成圖表
            metrics = database.get_metrics_by_timespan(timespan)
            
            if not metrics:
                return {'success': False, 'message': '沒有數據可生成圖表'}
            
            # 生成各種圖表
            visualizer.plot_system_overview(metrics, timespan=timespan)
            visualizer.plot_resource_comparison(metrics)
            visualizer.plot_memory_usage(metrics)
            visualizer.plot_usage_distribution(metrics)
            
            return {'success': True, 'message': '圖表生成成功'}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get('/plots/{filename}')
    async def serve_plot(filename: str):
        try:
            plot_path = visualizer.output_dir / filename
            if plot_path.exists() and plot_path.suffix == '.png':
                return FileResponse(plot_path, media_type='image/png')
            else:
                raise HTTPException(status_code=404, detail="Plot not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error serving plot: {e}")
    
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=5000)