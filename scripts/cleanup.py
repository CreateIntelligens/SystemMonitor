#!/usr/bin/env python3
"""
自動清理腳本 - 週週分檔版本
- 只清理圖片文件，不清理資料庫數據（資料庫已改為週週分檔保存）
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


def cleanup_system(plots_keep_days=1, plots_dir="plots"):
    """
    執行系統清理 - 只清理圖片文件
    
    Args:
        plots_keep_days: 圖片保留天數
        plots_dir: 圖片目錄
    """
    print("🧹 開始執行系統清理...")
    print("📅 資料庫: 使用週週分檔系統，不清理數據")
    print(f"🖼️ 圖片保留: {plots_keep_days} 天")
    print("=" * 50)
    
    try:
        # 初始化資料庫（只用於清理圖片功能）
        database = MonitoringDatabase("data/monitoring.db")  # 臨時實例，用於圖片清理
        
        # 清理圖片文件
        print(f"\n🖼️ 清理 {plots_keep_days} 天前的圖片文件...")
        deleted_plots = database.cleanup_old_plots(keep_days=plots_keep_days, plots_dir=plots_dir)
        
        # 總結
        print("\n" + "=" * 50)
        print("✅ 清理完成!")
        print(f"🖼️ 刪除圖片: {deleted_plots} 張")
        print("📝 資料庫數據保持原樣（週週分檔管理）")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失敗: {e}")
        return False


def daemon_mode(interval_hours=24, plots_keep_days=1, plots_dir="plots"):
    """
    守護進程模式，定期執行清理（只清理圖片）
    
    Args:
        interval_hours: 清理間隔（小時）
        plots_keep_days: 圖片保留天數
        plots_dir: 圖片目錄
    """
    print(f"🤖 啟動圖片清理守護進程（每 {interval_hours} 小時執行一次）")
    print(f"⏰ 下次清理時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("按 Ctrl+C 停止\n")
    
    try:
        while True:
            cleanup_system(
                plots_keep_days=plots_keep_days,
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
    parser = argparse.ArgumentParser(description="系統監控圖片清理工具（週週分檔版本）")
    parser.add_argument('--plots-days', type=int, default=int(os.getenv('PLOTS_KEEP_DAYS', 1)), help='圖片保留天數')
    parser.add_argument('--plots-dir', default=os.getenv('PLOTS_DIR', 'plots'), help='圖片目錄')
    parser.add_argument('--daemon', action='store_true', help='守護進程模式')
    parser.add_argument('--interval', type=int, default=24, help='守護進程清理間隔（小時，預設24）')
    
    args = parser.parse_args()
    
    if args.daemon:
        daemon_mode(
            interval_hours=args.interval,
            plots_keep_days=args.plots_days,
            plots_dir=args.plots_dir
        )
    else:
        cleanup_system(
            plots_keep_days=args.plots_days,
            plots_dir=args.plots_dir
        )


if __name__ == "__main__":
    main()