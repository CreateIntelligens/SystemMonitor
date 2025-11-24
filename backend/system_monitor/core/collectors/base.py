#!/usr/bin/env python3
"""
統合系統監控收集器
整合 GPU、CPU、RAM 等所有收集器
"""

from datetime import datetime
from typing import Dict, Optional, List

from .gpu import GPUCollector
from .system import SystemCollector

class SystemMonitorCollector:
    """統合系統監控收集器"""
    
    def __init__(self):
        self.gpu_collector = GPUCollector()
        self.system_collector = SystemCollector()
    
    def collect_all(self) -> Dict:
        """收集所有系統數據"""
        timestamp = datetime.now()
        
        gpu_data = self.gpu_collector.get_gpu_stats()
        gpu_processes = self.gpu_collector.get_gpu_processes()
        cpu_data = self.system_collector.get_cpu_stats()
        memory_data = self.system_collector.get_memory_stats()
        
        data = {
            'timestamp': timestamp.isoformat(),
            'unix_timestamp': timestamp.timestamp(),
            'cpu': cpu_data,
            'memory': memory_data,
            'gpu': gpu_data,
            'gpu_processes': gpu_processes
        }
        
        return data
    
    def collect_simple(self) -> Dict:
        """收集簡化數據（用於存儲）"""
        all_data = self.collect_all()
        
        simple_data = {
            'timestamp': all_data['timestamp'],
            'unix_timestamp': all_data['unix_timestamp'],
            'cpu_usage': all_data['cpu'].get('cpu_usage', 0),
            'ram_usage': all_data['memory'].get('ram_usage', 0),
            'ram_used_gb': all_data['memory'].get('ram_used_gb', 0),
            'ram_total_gb': all_data['memory'].get('ram_total_gb', 0),
            'cpu_source': all_data['cpu'].get('source', 'N/A'),
            'ram_source': all_data['memory'].get('source', 'N/A'),
        }
        
        if all_data['gpu'] and len(all_data['gpu']) > 0:
            gpu0 = all_data['gpu'][0]
            simple_data.update({
                'gpu_usage': gpu0.get('gpu_usage', 0),
                'vram_usage': gpu0.get('vram_usage', 0),
                'vram_used_mb': gpu0.get('vram_used_mb', 0),
                'vram_total_mb': gpu0.get('vram_total_mb', 0),
                'gpu_temperature': gpu0.get('temperature', 0),
            })
        else:
            simple_data.update({
                'gpu_usage': None,
                'vram_usage': None,
                'vram_used_mb': None,
                'vram_total_mb': None,
                'gpu_temperature': None,
            })
        
        return simple_data
    
    def is_gpu_available(self) -> bool:
        """檢查 GPU 是否可用"""
        return self.gpu_collector.gpu_available
    
    def get_top_gpu_processes(self, limit: int = 10) -> Optional[List[Dict]]:
        """獲取佔用 GPU 最多的進程"""
        return self.gpu_collector.get_top_gpu_processes(limit)
