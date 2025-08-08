#!/usr/bin/env python3
"""
系統監控數據存儲模塊
使用 SQLite 存儲時序數據
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading


class MonitoringDatabase:
    """監控數據庫管理器"""
    
    def __init__(self, db_path: str = "monitoring.db"):
        """
        初始化數據庫
        
        Args:
            db_path: 資料庫檔案路徑
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 資料庫連接鎖
        self._lock = threading.Lock()
        
        # 初始化資料庫結構
        self._init_database()
    
    def _init_database(self):
        """初始化資料庫結構"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 創建主要數據表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    unix_timestamp REAL NOT NULL,
                    cpu_usage REAL,
                    ram_usage REAL,
                    ram_used_gb REAL,
                    ram_total_gb REAL,
                    gpu_usage REAL,
                    vram_usage REAL,
                    vram_used_mb REAL,
                    vram_total_mb REAL,
                    gpu_temperature REAL,
                    raw_data TEXT
                )
            """)
            
            # 創建 GPU 進程數據表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gpu_processes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    unix_timestamp REAL NOT NULL,
                    pid INTEGER NOT NULL,
                    process_name TEXT,
                    command TEXT,
                    gpu_uuid TEXT,
                    gpu_memory_mb REAL,
                    cpu_percent REAL,
                    ram_mb REAL,
                    start_time TEXT,
                    raw_data TEXT
                )
            """)
            
            # 創建索引提高查詢效能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON system_metrics(unix_timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_datetime 
                ON system_metrics(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_gpu_proc_timestamp 
                ON gpu_processes(unix_timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_gpu_proc_pid 
                ON gpu_processes(pid, unix_timestamp)
            """)
            
            # 創建配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """獲取資料庫連接"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # 允許通過列名訪問
        return conn
    
    def insert_metrics(self, data: Dict) -> bool:
        """
        插入監控數據
        
        Args:
            data: 監控數據字典
            
        Returns:
            是否插入成功
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT INTO system_metrics (
                            timestamp, unix_timestamp, cpu_usage, ram_usage, 
                            ram_used_gb, ram_total_gb, gpu_usage, vram_usage,
                            vram_used_mb, vram_total_mb, gpu_temperature, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data.get('timestamp'),
                        data.get('unix_timestamp'),
                        data.get('cpu_usage'),
                        data.get('ram_usage'),
                        data.get('ram_used_gb'),
                        data.get('ram_total_gb'),
                        data.get('gpu_usage'),
                        data.get('vram_usage'),
                        data.get('vram_used_mb'),
                        data.get('vram_total_mb'),
                        data.get('gpu_temperature'),
                        json.dumps(data)  # 保存完整原始數據
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"❌ 插入數據失敗: {e}")
            return False
    
    def get_metrics(self, 
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[Dict]:
        """
        查詢監控數據
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            limit: 限制返回數量
            
        Returns:
            監控數據列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 構建查詢條件
                conditions = []
                params = []
                
                if start_time:
                    conditions.append("unix_timestamp >= ?")
                    params.append(start_time.timestamp())
                
                if end_time:
                    conditions.append("unix_timestamp <= ?")
                    params.append(end_time.timestamp())
                
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                order_clause = "ORDER BY unix_timestamp DESC"
                limit_clause = ""
                if limit:
                    limit_clause = f"LIMIT {limit}"
                
                query = f"""
                    SELECT * FROM system_metrics 
                    {where_clause} 
                    {order_clause} 
                    {limit_clause}
                """
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # 轉換為字典列表
                metrics = []
                for row in rows:
                    metric = dict(row)
                    # 解析原始數據
                    if metric.get('raw_data'):
                        try:
                            metric['raw_data'] = json.loads(metric['raw_data'])
                        except json.JSONDecodeError:
                            pass
                    metrics.append(metric)
                
                return metrics
                
        except Exception as e:
            print(f"❌ 查詢數據失敗: {e}")
            return []
    
    def get_latest_metrics(self, count: int = 1) -> List[Dict]:
        """獲取最新的監控數據"""
        return self.get_metrics(limit=count)
    
    def insert_gpu_processes(self, processes: List[Dict], timestamp: Optional[datetime] = None) -> bool:
        """
        插入 GPU 進程數據
        
        Args:
            processes: 進程信息列表
            timestamp: 時間戳（可選，預設使用當前時間）
            
        Returns:
            是否插入成功
        """
        if not processes:
            return True
            
        if timestamp is None:
            timestamp = datetime.now()
            
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 批量插入進程數據
                    for process in processes:
                        cursor.execute("""
                            INSERT INTO gpu_processes (
                                timestamp, unix_timestamp, pid, process_name, command,
                                gpu_uuid, gpu_memory_mb, cpu_percent, ram_mb, start_time, raw_data
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            timestamp.isoformat(),
                            timestamp.timestamp(),
                            process.get('pid'),
                            process.get('name'),
                            process.get('command'),
                            process.get('gpu_uuid'),
                            process.get('gpu_memory_mb'),
                            process.get('cpu_percent'),
                            process.get('ram_mb'),
                            process.get('start_time'),
                            json.dumps(process)
                        ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"❌ 插入 GPU 進程數據失敗: {e}")
            return False
    
    def get_gpu_processes(self, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         pid: Optional[int] = None,
                         limit: Optional[int] = None) -> List[Dict]:
        """
        查詢 GPU 進程數據
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            pid: 特定進程 ID
            limit: 限制返回數量
            
        Returns:
            進程數據列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 構建查詢條件
                conditions = []
                params = []
                
                if start_time:
                    conditions.append("unix_timestamp >= ?")
                    params.append(start_time.timestamp())
                
                if end_time:
                    conditions.append("unix_timestamp <= ?")
                    params.append(end_time.timestamp())
                
                if pid:
                    conditions.append("pid = ?")
                    params.append(pid)
                
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                order_clause = "ORDER BY unix_timestamp DESC"
                limit_clause = ""
                if limit:
                    limit_clause = f"LIMIT {limit}"
                
                query = f"""
                    SELECT * FROM gpu_processes 
                    {where_clause} 
                    {order_clause} 
                    {limit_clause}
                """
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # 轉換為字典列表
                processes = []
                for row in rows:
                    process = dict(row)
                    # 解析原始數據
                    if process.get('raw_data'):
                        try:
                            process['raw_data'] = json.loads(process['raw_data'])
                        except json.JSONDecodeError:
                            pass
                    processes.append(process)
                
                return processes
                
        except Exception as e:
            print(f"❌ 查詢 GPU 進程數據失敗: {e}")
            return []
    
    def get_top_gpu_processes_by_timespan(self, timespan: str = '1h', limit: int = 10) -> List[Dict]:
        """
        根據時間範圍獲取消耗 GPU 最多的進程
        
        Args:
            timespan: 時間範圍 ('1h', '6h', '24h', '7d')
            limit: 返回數量限制
            
        Returns:
            進程信息列表，按 GPU 記憶體使用量排序
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
            # 預設 1 小時
            start_time = now - timedelta(hours=1)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 查詢指定時間範圍內平均 GPU 記憶體使用量最高的進程
                query = """
                    SELECT 
                        pid,
                        process_name,
                        command,
                        AVG(gpu_memory_mb) as avg_gpu_memory,
                        MAX(gpu_memory_mb) as max_gpu_memory,
                        COUNT(*) as sample_count,
                        MAX(timestamp) as last_seen
                    FROM gpu_processes 
                    WHERE unix_timestamp >= ? 
                    GROUP BY pid, process_name 
                    ORDER BY avg_gpu_memory DESC 
                    LIMIT ?
                """
                
                cursor.execute(query, (start_time.timestamp(), limit))
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ 查詢頂級 GPU 進程失敗: {e}")
            return []
    
    def get_metrics_by_timespan(self, timespan: str) -> List[Dict]:
        """
        根據時間範圍獲取數據
        
        Args:
            timespan: 時間範圍 (支援: '90m', '24h', '3000s', '7d' 等格式)
        """
        import re
        
        now = datetime.now()
        
        # 解析時間範圍 - 支援更多格式
        if timespan.endswith('s'):
            # 秒：3000s
            seconds = int(timespan[:-1])
            start_time = now - timedelta(seconds=seconds)
        elif timespan.endswith('m'):
            # 分鐘：90m
            minutes = int(timespan[:-1])
            start_time = now - timedelta(minutes=minutes)
        elif timespan.endswith('h'):
            # 小時：24h
            hours = int(timespan[:-1])
            start_time = now - timedelta(hours=hours)
        elif timespan.endswith('d'):
            # 天：7d
            days = int(timespan[:-1])
            start_time = now - timedelta(days=days)
        elif timespan.endswith('w'):
            # 週：2w
            weeks = int(timespan[:-1])
            start_time = now - timedelta(weeks=weeks)
        else:
            # 預設 24 小時
            start_time = now - timedelta(hours=24)
        
        return self.get_metrics(start_time=start_time, end_time=now)
    
    def cleanup_old_data(self, keep_days: int = 30) -> int:
        """
        清理舊數據
        
        Args:
            keep_days: 保留天數
            
        Returns:
            刪除的記錄數
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=keep_days)
            
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        DELETE FROM system_metrics 
                        WHERE unix_timestamp < ?
                    """, (cutoff_time.timestamp(),))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    # 優化資料庫
                    cursor.execute("VACUUM")
                    
                    return deleted_count
                    
        except Exception as e:
            print(f"❌ 清理數據失敗: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """獲取資料庫統計資訊"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 總記錄數
                cursor.execute("SELECT COUNT(*) FROM system_metrics")
                total_records = cursor.fetchone()[0]
                
                # 時間範圍
                cursor.execute("""
                    SELECT MIN(unix_timestamp), MAX(unix_timestamp) 
                    FROM system_metrics
                """)
                time_range = cursor.fetchone()
                
                # 資料庫檔案大小
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                stats = {
                    'total_records': total_records,
                    'database_size_mb': round(db_size / (1024 * 1024), 2),
                    'earliest_record': None,
                    'latest_record': None
                }
                
                if time_range[0] and time_range[1]:
                    stats['earliest_record'] = datetime.fromtimestamp(time_range[0]).isoformat()
                    stats['latest_record'] = datetime.fromtimestamp(time_range[1]).isoformat()
                
                return stats
                
        except Exception as e:
            print(f"❌ 獲取統計失敗: {e}")
            return {}
    
    def export_to_csv(self, output_path: str, 
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None) -> bool:
        """
        導出數據到 CSV
        
        Args:
            output_path: 輸出檔案路徑
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            是否導出成功
        """
        try:
            import csv
            
            metrics = self.get_metrics(start_time=start_time, end_time=end_time)
            
            if not metrics:
                print("❌ 沒有數據可導出")
                return False
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 定義欄位
                fieldnames = [
                    'timestamp', 'cpu_usage', 'ram_usage', 'ram_used_gb', 'ram_total_gb',
                    'gpu_usage', 'vram_usage', 'vram_used_mb', 'vram_total_mb', 'gpu_temperature'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for metric in reversed(metrics):  # 時間順序
                    row = {field: metric.get(field) for field in fieldnames}
                    writer.writerow(row)
            
            print(f"✅ 成功導出 {len(metrics)} 條記錄到 {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 導出 CSV 失敗: {e}")
            return False
    
    def set_config(self, key: str, value: str):
        """設定配置項目"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO config (key, value, updated_at)
                        VALUES (?, ?, ?)
                    """, (key, value, datetime.now().isoformat()))
                    
                    conn.commit()
                    
        except Exception as e:
            print(f"❌ 設定配置失敗: {e}")
    
    def get_config(self, key: str, default: str = None) -> Optional[str]:
        """獲取配置項目"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
                result = cursor.fetchone()
                
                return result[0] if result else default
                
        except Exception as e:
            print(f"❌ 獲取配置失敗: {e}")
            return default


def main():
    """測試存儲功能"""
    print("🗄️  系統監控數據庫測試")
    print("=" * 50)
    
    # 創建測試數據庫
    db = MonitoringDatabase("test_monitoring.db")
    
    # 插入測試數據
    print("📝 插入測試數據...")
    test_data = {
        'timestamp': datetime.now().isoformat(),
        'unix_timestamp': datetime.now().timestamp(),
        'cpu_usage': 45.5,
        'ram_usage': 67.2,
        'ram_used_gb': 8.5,
        'ram_total_gb': 16.0,
        'gpu_usage': 85.3,
        'vram_usage': 75.0,
        'vram_used_mb': 6000,
        'vram_total_mb': 8000,
        'gpu_temperature': 72
    }
    
    success = db.insert_metrics(test_data)
    print(f"插入結果: {'成功' if success else '失敗'}")
    
    # 查詢數據
    print("\n📊 查詢最新數據...")
    latest = db.get_latest_metrics(count=1)
    if latest:
        metric = latest[0]
        print(f"時間: {metric['timestamp']}")
        print(f"CPU: {metric['cpu_usage']}%")
        print(f"RAM: {metric['ram_usage']}%")
        if metric['gpu_usage']:
            print(f"GPU: {metric['gpu_usage']}%")
    
    # 統計資訊
    print("\n📈 資料庫統計:")
    stats = db.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 導出測試
    print("\n💾 測試 CSV 導出...")
    export_success = db.export_to_csv("test_export.csv")
    if export_success and Path("test_export.csv").exists():
        print("CSV 導出成功")
        Path("test_export.csv").unlink()  # 清理測試檔案
    
    # 清理測試資料庫
    if Path("test_monitoring.db").exists():
        Path("test_monitoring.db").unlink()
    
    print("\n✅ 數據庫測試完成")


if __name__ == "__main__":
    main()