#!/usr/bin/env python3
"""
系統監控主程式 - 重構後的版本
"""

import argparse
import sys
import time
import signal
import threading
from pathlib import Path
from typing import Optional

from core import SystemMonitorCollector, MonitoringDatabase, SystemMonitorVisualizer
from utils import Config, setup_logger

# 可選的 Web 相關導入
try:
    import uvicorn
    from web.app import create_app as create_web_app
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False


class SystemMonitor:
    """系統監控主類"""
    
    def __init__(self, config=None):
        """初始化系統監控"""
        self.config = config or Config()
        self.db_path = self.config.database_path
        self.interval = self.config.monitoring_interval
        self.running = False
        
        # 設置日誌
        self.logger = setup_logger(
            level=self.config.get('logging.level', 'INFO'),
            log_file=self.config.get('logging.file')
        )
        
        # 初始化組件
        self.collector = SystemMonitorCollector()
        self.database = MonitoringDatabase(self.db_path)
        self.visualizer = SystemMonitorVisualizer()
        self.visualizer.output_dir = Path(self.config.plots_dir)
        
        # 監控線程
        self.monitor_thread = None
        
        # 設置信號處理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信號處理器，優雅停止監控"""
        print(f"\n🛑 接收到信號 {signum}，正在停止監控...")
        self.stop_monitoring()
        sys.exit(0)
    
    def _monitor_loop(self):
        """監控循環"""
        print(f"🔄 開始監控循環，間隔 {self.interval} 秒")
        
        while self.running:
            try:
                # 收集基本系統數據
                data = self.collector.collect_simple()
                
                # 收集 GPU 進程數據
                gpu_processes = self.collector.get_top_gpu_processes(limit=5)
                
                # 存儲到數據庫
                success = self.database.insert_metrics(data)
                
                # 存儲 GPU 進程數據
                if gpu_processes:
                    from datetime import datetime
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    self.database.insert_gpu_processes(gpu_processes, timestamp)
                
                if success:
                    timestamp = data['timestamp'][:19]
                    cpu = data.get('cpu_usage', 0)
                    ram_used = data.get('ram_used_gb', 0)
                    ram_total = data.get('ram_total_gb', 0)
                    ram_percent = data.get('ram_usage', 0)
                    
                    status = f"⏰ {timestamp} | 🖥️  CPU: {cpu:.1f}% | 💾 RAM: {ram_used:.1f}GB/{ram_total:.1f}GB ({ram_percent:.1f}%)"
                    
                    if data.get('gpu_usage') is not None:
                        gpu = data.get('gpu_usage', 0)
                        vram = data.get('vram_usage', 0)
                        status += f" | 🎮 GPU: {gpu:.1f}% | 📈 VRAM: {vram:.1f}%"
                    
                    # 顯示頂級 GPU 進程信息
                    cpu_source = data.get('cpu_source', 'N/A')
                    ram_source = data.get('ram_source', 'N/A')
                    status += f" (src: {cpu_source}/{ram_source})"
                    
                    print(status)
                else:
                    print("❌ 數據存儲失敗")
                
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"❌ 監控循環錯誤: {e}")
                time.sleep(self.interval)
    
    def start_monitoring(self):
        """開始監控"""
        if self.running:
            print("⚠️  監控已在運行中")
            return
        
        print("🚀 啟動系統監控")
        print(f"📁 數據庫: {self.db_path}")
        print(f"⏱️  收集間隔: {self.interval} 秒")
        
        if self.collector.is_gpu_available():
            print("✅ NVIDIA GPU 可用")
        else:
            print("⚠️  NVIDIA GPU 不可用，將只監控 CPU/RAM")
        
        print("-" * 70)
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止監控"""
        if not self.running:
            print("⚠️  監控未運行")
            return
        
        print("🛑 停止監控...")
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        print("✅ 監控已停止")
    
    def show_status(self):
        """顯示當前狀態"""
        print("📊 系統監控狀態")
        print("=" * 50)
        
        print(f"🔄 監控運行: {'是' if self.running else '否'}")
        print(f"📁 數據庫: {self.db_path}")
        print(f"🎮 GPU 可用: {'是' if self.collector.is_gpu_available() else '否'}")
        
        # 數據庫統計
        stats = self.database.get_statistics()
        if stats:
            print(f"📈 總記錄數: {stats.get('total_records', 0):,}")
            print(f"💾 數據庫大小: {stats.get('database_size_mb', 0)} MB")
            
            if stats.get('earliest_record'):
                earliest = stats['earliest_record'][:19]
                latest = stats.get('latest_record', '')[:19]
                print(f"⏰ 數據範圍: {earliest} ~ {latest}")
        
        # 當前系統狀態
        current_data = self.collector.collect_simple()
        print(f"\n🖥️  當前 CPU: {current_data.get('cpu_usage', 0):.2f}% (來源: {current_data.get('cpu_source', 'N/A')})")
        print(f"💾 當前 RAM: {current_data.get('ram_used_gb', 0):.1f}GB/{current_data.get('ram_total_gb', 0):.1f}GB "
              f"({current_data.get('ram_usage', 0):.1f}%) (來源: {current_data.get('ram_source', 'N/A')})")
        
        if current_data.get('gpu_usage') is not None:
            print(f"🎮 當前 GPU: {current_data.get('gpu_usage', 0):.2f}%")
            print(f"📈 當前 VRAM: {current_data.get('vram_usage', 0):.2f}% "
                  f"({current_data.get('vram_used_mb', 0):.0f}MB/"
                  f"{current_data.get('vram_total_mb', 0):.0f}MB)")
            print(f"🌡️  GPU 溫度: {current_data.get('gpu_temperature', 0)}°C")
            
            # 顯示當前 GPU 進程
            gpu_processes = self.collector.get_top_gpu_processes(limit=5)
            if gpu_processes:
                print(f"\n🔥 當前 GPU 進程 (前5名):")
                print(f"{'PID':>8} {'進程名':<15} {'GPU記憶體':<10} {'CPU%':<6} {'指令':<30}")
                print("-" * 70)
                for proc in gpu_processes:
                    cmd = proc.get('command', proc.get('name', 'N/A'))
                    if len(cmd) > 28:
                        cmd = cmd[:25] + "..."
                    print(f"{proc.get('pid', 0):>8} {proc.get('name', 'N/A'):<15} "
                          f"{proc.get('gpu_memory_mb', 0):>8.0f}MB "
                          f"{proc.get('cpu_percent', 0):>5.1f} {cmd:<30}")
            else:
                print("\n📋 無 GPU 進程正在運行")
    
    def show_gpu_processes(self, timespan: str = '1h', limit: int = 10):
        """顯示 GPU 進程信息"""
        print(f"🎮 GPU 進程分析 ({timespan})")
        print("=" * 70)
        
        if not self.collector.is_gpu_available():
            print("❌ NVIDIA GPU 不可用")
            return
        
        # 獲取當前進程
        current_processes = self.collector.get_top_gpu_processes(limit=limit)
        
        if current_processes:
            print("🔥 當前 GPU 進程:")
            print(f"{'PID':>8} {'進程名':<15} {'GPU記憶體':>10} {'CPU%':>6} {'RAM':>8} {'指令':<25}")
            print("-" * 80)
            
            for proc in current_processes:
                cmd = proc.get('command', proc.get('name', 'N/A'))
                if len(cmd) > 23:
                    cmd = cmd[:20] + "..."
                
                print(f"{proc.get('pid', 0):>8} "
                      f"{proc.get('name', 'N/A'):<15} "
                      f"{proc.get('gpu_memory_mb', 0):>8.0f}MB "
                      f"{proc.get('cpu_percent', 0):>5.1f}% "
                      f"{proc.get('ram_mb', 0):>6.0f}MB "
                      f"{cmd:<25}")
        
        # 獲取歷史統計
        top_historical = self.database.get_top_gpu_processes_by_timespan(timespan, limit)
        
        if top_historical:
            print(f"\n📈 {timespan} 期間平均 GPU 記憶體使用排行:")
            print(f"{'PID':>8} {'進程名':<15} {'平均GPU記憶體':>12} {'最大GPU記憶體':>12} {'樣本數':>8} {'最後記錄':<16}")
            print("-" * 80)
            
            for proc in top_historical:
                last_seen = proc.get('last_seen', 'N/A')
                if isinstance(last_seen, str) and len(last_seen) > 16:
                    last_seen = last_seen[:13] + "..."
                
                print(f"{proc.get('pid', 0):>8} "
                      f"{proc.get('process_name', 'N/A'):<15} "
                      f"{proc.get('avg_gpu_memory', 0):>10.0f}MB "
                      f"{proc.get('max_gpu_memory', 0):>10.0f}MB "
                      f"{proc.get('sample_count', 0):>8} "
                      f"{last_seen:<16}")
        else:
            print(f"\n📋 {timespan} 期間無 GPU 進程記錄")
    
    def generate_plots(self, timespan: str = "24h", output_dir: Optional[str] = None):
        """生成圖表"""
        print(f"📊 生成 {timespan} 圖表...")
        
        metrics = self.database.get_metrics_by_timespan(timespan)
        
        if not metrics:
            print("❌ 沒有數據可生成圖表")
            return
        
        print(f"📈 找到 {len(metrics)} 條記錄")
        
        if output_dir:
            self.visualizer.output_dir = Path(output_dir)
            self.visualizer.output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            print("🔄 生成系統概覽圖...")
            overview_path = self.visualizer.plot_system_overview(metrics, timespan=timespan)
            print(f"✅ 系統概覽圖: {overview_path}")
            
            print("🔄 生成資源對比圖...")
            comparison_path = self.visualizer.plot_resource_comparison(metrics)
            print(f"✅ 資源對比圖: {comparison_path}")
            
            print("🔄 生成記憶體使用圖...")
            memory_path = self.visualizer.plot_memory_usage(metrics)
            print(f"✅ 記憶體使用圖: {memory_path}")
            
            print("🔄 生成使用率分佈圖...")
            distribution_path = self.visualizer.plot_usage_distribution(metrics)
            print(f"✅ 使用率分佈圖: {distribution_path}")
            
            print("📋 統計摘要:")
            stats = self.visualizer.generate_summary_stats(metrics)
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print(f"\n✅ 所有圖表已生成完成")
            
        except Exception as e:
            print(f"❌ 生成圖表失敗: {e}")
    
    def export_data(self, output_path: str, timespan: Optional[str] = None):
        """導出數據到 CSV"""
        print(f"💾 導出數據到 {output_path}...")
        
        success = self.database.export_to_csv(output_path)
        
        if success:
            print("✅ 數據導出成功")
        else:
            print("❌ 數據導出失敗")
    
    def cleanup_data(self, keep_days: int = 30):
        """清理舊數據"""
        print(f"🧹 清理 {keep_days} 天前的數據...")
        
        deleted_count = self.database.cleanup_old_data(keep_days)
        
        if deleted_count > 0:
            print(f"✅ 已清理 {deleted_count:,} 條記錄")
        else:
            print("ℹ️  沒有需要清理的記錄")
    
    def run_web_server(self, host: str = None, port: int = None, debug: bool = False):
        """運行 Web 伺服器"""
        host = host or self.config.web_host
        port = port or self.config.web_port
        
        print(f"🌐 啟動 FastAPI Web 介面...")
        print(f"📍 訪問地址: http://{host}:{port}")
        print(f"🗂️  數據庫: {self.db_path}")
        print(f"📊 圖表目錄: {self.visualizer.output_dir}")
        print(f"📖 API 文檔: http://{host}:{port}/docs")
        
        app = create_web_app(self)
        uvicorn.run(app, host=host, port=port, log_level="info" if debug else "warning")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="系統監控工具")
    
    # 通用參數
    parser.add_argument('--config', help='配置文件路徑')
    
    # 子指令
    subparsers = parser.add_subparsers(dest='command', help='可用指令')
    
    # 監控指令
    monitor_parser = subparsers.add_parser('monitor', help='開始監控')
    monitor_parser.add_argument('--interval', type=int, help='數據收集間隔秒數')
    
    # 狀態指令
    subparsers.add_parser('status', help='顯示監控狀態')
    
    # GPU 進程指令
    gpu_parser = subparsers.add_parser('gpu-processes', help='顯示 GPU 進程信息')
    gpu_parser.add_argument('--timespan', default='1h', 
                           choices=['1h', '6h', '24h', '7d'],
                           help='查看時間範圍 (預設: 1h)')
    gpu_parser.add_argument('--limit', type=int, default=10,
                           help='顯示進程數量 (預設: 10)')
    
    # 圖表指令
    plot_parser = subparsers.add_parser('plot', help='生成系統圖表')
    plot_parser.add_argument('--timespan', default='24h',
                            help='時間範圍 (支援: 90m, 24h, 3000s, 7d 等格式，預設: 24h)')
    plot_parser.add_argument('--output', help='輸出目錄')
    plot_parser.add_argument('--database', help='指定資料庫檔案 (如: monitoring_server2.db)', default='monitoring.db')
    
    # 新增進程對比繪圖命令
    process_plot_parser = subparsers.add_parser('plot-processes', help='繪製進程對比圖')
    process_plot_parser.add_argument('pids', nargs='+', type=int, help='進程PID列表')
    process_plot_parser.add_argument('timespan', help='時間範圍 (如: 1h, 24h, 3d)')
    process_plot_parser.add_argument('--database', help='指定資料庫檔案', default='monitoring.db')
    process_plot_parser.add_argument('--output', help='輸出檔案路徑')
    process_plot_parser.add_argument('--title', help='圖表標題')
    
    # 導出指令
    export_parser = subparsers.add_parser('export', help='導出數據')
    export_parser.add_argument('output', help='輸出 CSV 文件路徑')
    
    # 清理指令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理舊數據')
    cleanup_parser.add_argument('--keep-days', type=int, default=30,
                               help='保留天數 (預設: 30)')
    
    # Web 介面指令
    web_parser = subparsers.add_parser('web', help='啟動 Web 介面')
    web_parser.add_argument('--host', help='綁定主機地址')
    web_parser.add_argument('--port', type=int, help='綁定端口')
    web_parser.add_argument('--debug', action='store_true', help='啟用除錯模式')
    
    args = parser.parse_args()
    
    # 如果沒有指定指令，預設顯示狀態
    if not args.command:
        args.command = 'status'
    
    # 創建配置
    config = Config(args.config) if args.config else Config()
    
    # 如果指令行指定了參數，覆蓋配置
    if hasattr(args, 'interval') and args.interval:
        config.set('monitoring.interval', args.interval)
    
    # 創建監控器
    monitor = SystemMonitor(config)
    
    try:
        if args.command == 'monitor':
            monitor.start_monitoring()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                monitor.stop_monitoring()
                
        elif args.command == 'status':
            monitor.show_status()
            
        elif args.command == 'gpu-processes':
            monitor.show_gpu_processes(timespan=args.timespan, limit=args.limit)
            
        elif args.command == 'plot':
            # 如果指定了不同的資料庫，創建新的監控器
            if args.database != 'monitoring.db':
                from pathlib import Path
                db_path = Path(args.database)
                if not db_path.exists():
                    print(f"❌ 資料庫檔案不存在: {args.database}")
                    sys.exit(1)
                
                print(f"📊 使用資料庫: {args.database}")
                # 創建新的監控器實例
                monitor_alt = SystemMonitor(config)
                monitor_alt.database = MonitoringDatabase(str(db_path))
                monitor_alt.generate_plots(timespan=args.timespan, output_dir=args.output)
            else:
                monitor.generate_plots(timespan=args.timespan, output_dir=args.output)
            
        elif args.command == 'export':
            monitor.export_data(args.output)
            
        elif args.command == 'cleanup':
            monitor.cleanup_data(args.keep_days)
            
        elif args.command == 'plot-processes':
            # 如果指定了不同的資料庫，創建新的監控器
            if args.database != 'monitoring.db':
                # 創建新的資料庫實例
                from pathlib import Path
                db_path = Path(args.database)
                if not db_path.exists():
                    print(f"❌ 資料庫檔案不存在: {args.database}")
                    sys.exit(1)
                
                print(f"📊 使用資料庫: {args.database}")
                database = MonitoringDatabase(str(db_path))
                visualizer = SystemMonitorVisualizer()
                visualizer.output_dir = Path(config.plots_dir)
            else:
                database = monitor.database
                visualizer = monitor.visualizer
            
            # 計算時間範圍
            from datetime import datetime, timedelta
            now = datetime.now()
            if args.timespan.endswith('m'):
                minutes = int(args.timespan[:-1])
                start_time = now - timedelta(minutes=minutes)
            elif args.timespan.endswith('h'):
                hours = int(args.timespan[:-1])
                start_time = now - timedelta(hours=hours)
            elif args.timespan.endswith('d'):
                days = int(args.timespan[:-1])
                start_time = now - timedelta(days=days)
            else:
                print(f"❌ 不支援的時間格式: {args.timespan}")
                print("支援格式: 30m, 2h, 3d")
                sys.exit(1)
            
            # 獲取進程資料
            process_data = database.get_processes_by_pids(args.pids, start_time, now)
            if not process_data:
                print(f"❌ 在時間範圍 {args.timespan} 內沒有找到PID {args.pids} 的資料")
                sys.exit(1)
            
            print(f"📈 找到 {len(process_data)} 條進程記錄")
            
            # 生成圖表
            try:
                chart_path = visualizer.plot_process_comparison(
                    process_data, 
                    args.pids, 
                    args.timespan
                )
                
                if args.output:
                    # 如果指定了輸出路徑，複製檔案
                    import shutil
                    shutil.copy2(chart_path, args.output)
                    print(f"✅ 進程對比圖已生成: {args.output}")
                else:
                    print(f"✅ 進程對比圖已生成: {chart_path}")
                    
            except Exception as e:
                print(f"❌ 生成圖表失敗: {e}")
                sys.exit(1)
            
        elif args.command == 'web':
            if not WEB_AVAILABLE:
                print("❌ Web 功能不可用：缺少 uvicorn 或相關依賴")
                print("請安裝: pip install uvicorn fastapi")
                sys.exit(1)
            monitor.run_web_server(host=args.host, port=args.port, debug=args.debug)
            
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()