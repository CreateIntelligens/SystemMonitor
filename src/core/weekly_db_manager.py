#!/usr/bin/env python3
"""
週週分檔資料庫管理器
每週自動創建新的資料庫檔案，保留所有歷史資料
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import glob

class WeeklyDatabaseManager:
    """週週分檔資料庫管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def get_week_number(self, date: Optional[datetime] = None) -> tuple:
        """
        獲取年份和週數
        
        Args:
            date: 指定日期，默認為當前時間
            
        Returns:
            (year, week_number) 元組
        """
        if date is None:
            date = datetime.now()
        
        # 獲取 ISO 週數（週一開始）
        year, week, _ = date.isocalendar()
        return year, week
    
    def get_current_database_path(self) -> str:
        """獲取當前週的資料庫路徑"""
        year, week = self.get_week_number()
        db_name = f"monitoring_{year}_W{week:02d}.db"
        return str(self.data_dir / db_name)
    
    def get_database_path_for_date(self, date: datetime) -> str:
        """獲取指定日期的資料庫路徑"""
        year, week = self.get_week_number(date)
        db_name = f"monitoring_{year}_W{week:02d}.db"
        return str(self.data_dir / db_name)
    
    def list_all_weekly_databases(self) -> List[dict]:
        """
        列出所有週資料庫檔案
        
        Returns:
            包含資料庫資訊的字典列表，按時間排序（新到舊）
        """
        pattern = str(self.data_dir / "monitoring_*_W*.db")
        db_files = glob.glob(pattern)
        
        db_info = []
        for db_file in db_files:
            db_name = Path(db_file).name
            
            # 解析檔名獲取年週資訊
            try:
                # monitoring_2025_W33.db -> 2025, 33
                parts = db_name.replace('.db', '').split('_')
                if len(parts) >= 3 and parts[0] == 'monitoring':
                    year = int(parts[1])
                    week_str = parts[2]
                    if week_str.startswith('W'):
                        week = int(week_str[1:])
                        
                        # 計算該週的開始和結束日期
                        start_date = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
                        end_date = start_date + timedelta(days=6)
                        
                        # 獲取檔案大小
                        file_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                        
                        db_info.append({
                            'filename': db_name,
                            'full_path': db_file,
                            'year': year,
                            'week': week,
                            'start_date': start_date.strftime('%Y-%m-%d'),
                            'end_date': end_date.strftime('%Y-%m-%d'),
                            'display_name': f"{year}年第{week}週 ({start_date.strftime('%m/%d')}-{end_date.strftime('%m/%d')})",
                            'size_mb': round(file_size, 2),
                            'is_current': db_file == self.get_current_database_path()
                        })
            except (ValueError, IndexError):
                continue
        
        # 按年週排序（新到舊）
        db_info.sort(key=lambda x: (x['year'], x['week']), reverse=True)
        return db_info
    
    def ensure_current_database_exists(self) -> str:
        """確保當前週的資料庫存在，如果不存在則創建"""
        current_db_path = self.get_current_database_path()
        
        if not os.path.exists(current_db_path):
            self._create_new_database(current_db_path)
            print(f"📅 新週資料庫: {Path(current_db_path).name}")
        
        return current_db_path
    
    def _create_new_database(self, db_path: str):
        """創建新的資料庫檔案並初始化表結構"""
        # 導入資料庫結構初始化邏輯
        from .storage import MonitoringDatabase
        
        # 創建新資料庫（這會自動初始化表結構）
        db = MonitoringDatabase(db_path)
        db.close() if hasattr(db, 'close') else None
    
    def get_database_for_timespan(self, timespan: str) -> List[str]:
        """
        根據時間範圍獲取需要查詢的資料庫列表
        
        Args:
            timespan: 時間範圍如 "1h", "6h", "24h", "7d", "30d"
            
        Returns:
            資料庫路徑列表
        """
        now = datetime.now()
        
        # 解析時間範圍
        if timespan.endswith('h'):
            hours = int(timespan[:-1])
            start_time = now - timedelta(hours=hours)
        elif timespan.endswith('d'):
            days = int(timespan[:-1])
            start_time = now - timedelta(days=days)
        else:
            # 默認為當前週
            return [self.get_current_database_path()]
        
        # 收集需要的資料庫
        db_paths = set()
        current_date = start_time
        while current_date <= now:
            db_path = self.get_database_path_for_date(current_date)
            if os.path.exists(db_path):
                db_paths.add(db_path)
            current_date += timedelta(days=1)
        
        # 確保包含當前週資料庫
        current_db = self.get_current_database_path()
        if os.path.exists(current_db):
            db_paths.add(current_db)
        
        return sorted(list(db_paths))


# 全域實例
weekly_db_manager = WeeklyDatabaseManager()