#!/usr/bin/env python3
"""
自動清理腳本
- 清理7天前的資料庫數據
- 清理1天前的圖片文件
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
import time

# 添加 src 目錄到 Python 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.storage import MonitoringDatabase


def cleanup_system(data_keep_days=7, plots_keep_days=1, db_path="data/monitoring.db", plots_dir="plots"):
    """
    執行系統清理
    
    Args:
        data_keep_days: 資料庫數據保留天數
        plots_keep_days: 圖片保留天數
        db_path: 資料庫路徑
        plots_dir: 圖片目錄
    """
    print("🧹 開始執行系統清理...")
    print(f"📅 資料保留: {data_keep_days} 天")
    print(f"🖼️ 圖片保留: {plots_keep_days} 天")
    print("=" * 50)
    
    try:
        # 初始化資料庫
        database = MonitoringDatabase(db_path)
        
        # 清理前統計
        before_stats = database.get_statistics()
        print(f"📊 清理前統計:")
        print(f"  總記錄數: {before_stats.get('total_records', 0)}")
        print(f"  資料庫大小: {before_stats.get('database_size_mb', 0)} MB")
        
        # 清理資料庫數據
        print(f"\n🗄️ 清理 {data_keep_days} 天前的資料庫數據...")
        deleted_records = database.cleanup_old_data(keep_days=data_keep_days)
        
        # 清理圖片文件
        print(f"\n🖼️ 清理 {plots_keep_days} 天前的圖片文件...")
        deleted_plots = database.cleanup_old_plots(keep_days=plots_keep_days, plots_dir=plots_dir)
        
        # 清理後統計
        after_stats = database.get_statistics()
        print(f"\n📊 清理後統計:")
        print(f"  總記錄數: {after_stats.get('total_records', 0)}")
        print(f"  資料庫大小: {after_stats.get('database_size_mb', 0)} MB")
        print(f"  節省空間: {before_stats.get('database_size_mb', 0) - after_stats.get('database_size_mb', 0):.2f} MB")
        
        # 總結
        print("\n" + "=" * 50)
        print("✅ 清理完成!")
        print(f"📝 刪除記錄: {deleted_records} 條")
        print(f"🖼️ 刪除圖片: {deleted_plots} 張")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失敗: {e}")
        return False


def daemon_mode(interval_hours=24, data_keep_days=7, plots_keep_days=1, 
                db_path="data/monitoring.db", plots_dir="plots"):
    """
    守護進程模式，定期執行清理
    
    Args:
        interval_hours: 清理間隔（小時）
        data_keep_days: 資料保留天數
        plots_keep_days: 圖片保留天數
        db_path: 資料庫路徑
        plots_dir: 圖片目錄
    """
    print(f"🤖 啟動清理守護進程（每 {interval_hours} 小時執行一次）")
    print(f"⏰ 下次清理時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("按 Ctrl+C 停止\n")
    
    try:
        while True:
            cleanup_system(
                data_keep_days=data_keep_days,
                plots_keep_days=plots_keep_days,
                db_path=db_path,
                plots_dir=plots_dir
            )
            
            # 計算下次執行時間
            next_run = datetime.now().replace(second=0, microsecond=0)
            next_run = next_run.replace(hour=(next_run.hour + interval_hours) % 24)
            
            print(f"\n⏰ 下次清理時間: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💤 休眠 {interval_hours} 小時...")
            
            time.sleep(interval_hours * 3600)  # 轉換為秒
            
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信號，正在退出...")
    except Exception as e:
        print(f"❌ 守護進程錯誤: {e}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="系統監控數據清理工具")
    parser.add_argument('--data-days', type=int, default=int(os.getenv('DATA_KEEP_DAYS', 7)), help='資料庫數據保留天數')
    parser.add_argument('--plots-days', type=int, default=int(os.getenv('PLOTS_KEEP_DAYS', 1)), help='圖片保留天數')
    parser.add_argument('--db-path', default=os.getenv('DB_PATH', 'data/monitoring.db'), help='資料庫路徑')
    parser.add_argument('--plots-dir', default=os.getenv('PLOTS_DIR', 'plots'), help='圖片目錄')
    parser.add_argument('--daemon', action='store_true', help='守護進程模式')
    parser.add_argument('--interval', type=int, default=24, help='守護進程清理間隔（小時，預設24）')
    
    args = parser.parse_args()
    
    if args.daemon:
        daemon_mode(
            interval_hours=args.interval,
            data_keep_days=args.data_days,
            plots_keep_days=args.plots_days,
            db_path=args.db_path,
            plots_dir=args.plots_dir
        )
    else:
        cleanup_system(
            data_keep_days=args.data_days,
            plots_keep_days=args.plots_days,
            db_path=args.db_path,
            plots_dir=args.plots_dir
        )


if __name__ == "__main__":
    main()