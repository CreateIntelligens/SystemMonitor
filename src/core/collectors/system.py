#!/usr/bin/env python3
"""
系統資源收集器
收集 CPU、RAM 使用率數據
"""

import time
import psutil
import requests
from typing import Dict, Optional

class WindowsHostCollector:
    """Windows 主機資源收集器（通過 HTTP 請求獲取）"""
    
    def __init__(self, host_url="http://host.docker.internal:9182"):
        self.host_url = host_url
        self.timeout = 5
    
    def _get_windows_metrics(self):
        """從 windows_exporter 獲取指標"""
        try:
            response = requests.get(f"{self.host_url}/metrics", timeout=self.timeout)
            if response.status_code == 200:
                return response.text
        except:
            pass
        return None
    
    def _parse_prometheus_metric(self, metrics_text, metric_name):
        """解析 Prometheus 格式的指標"""
        try:
            lines = metrics_text.split('\n')
            for line in lines:
                if line.startswith(metric_name) and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        return float(parts[-1])
        except:
            pass
        return None
    
    def get_windows_cpu_usage(self):
        """獲取 Windows CPU 使用率"""
        metrics = self._get_windows_metrics()
        if not metrics:
            return None
        
        cpu_idle = self._parse_prometheus_metric(metrics, 'windows_cpu_time_total{mode="idle"}')
        if cpu_idle is not None:
            return round(100 - cpu_idle, 2)
        return None
    
    def get_windows_memory_stats(self):
        """獲取 Windows 記憶體統計"""
        metrics = self._get_windows_metrics()
        if not metrics:
            return None
        
        try:
            total_memory = self._parse_prometheus_metric(metrics, 'windows_os_physical_memory_total_bytes')
            free_memory = self._parse_prometheus_metric(metrics, 'windows_os_physical_memory_free_bytes')
            
            if total_memory and free_memory:
                used_memory = total_memory - free_memory
                usage_percent = (used_memory / total_memory) * 100
                
                return {
                    'ram_total_gb': round(total_memory / (1024**3), 2),
                    'ram_used_gb': round(used_memory / (1024**3), 2),
                    'ram_usage': round(usage_percent, 2),
                    'ram_available_gb': round(free_memory / (1024**3), 2),
                    'source': 'windows_host'
                }
        except:
            pass
        return None


class SystemCollector:
    """系統 CPU 和記憶體收集器"""
    
    def __init__(self):
        self.windows_collector = WindowsHostCollector()
    
    def _read_host_cpu_stats(self):
        """讀取主機 CPU 統計"""
        import os
        if not os.path.exists('/host/proc/stat'):
            return None
        
        try:
            with open('/host/proc/stat', 'r') as f:
                line = f.readline()
                if line.startswith('cpu '):
                    values = [int(x) for x in line.split()[1:]]
                    idle = values[3]
                    total = sum(values)
                    return {'idle': idle, 'total': total}
        except:
            pass
        return None
    
    def _get_host_cpu_usage(self):
        """計算主機 CPU 使用率"""
        try:
            stat1 = self._read_host_cpu_stats()
            if not stat1:
                return None
            
            time.sleep(1)
            
            stat2 = self._read_host_cpu_stats()
            if not stat2:
                return None
            
            idle_diff = stat2['idle'] - stat1['idle']
            total_diff = stat2['total'] - stat1['total']
            
            if total_diff <= 0:
                return None
            
            cpu_usage = (total_diff - idle_diff) / total_diff * 100
            return round(cpu_usage, 2)
            
        except Exception:
            return None
    
    def get_cpu_stats(self) -> Dict:
        """獲取 CPU 使用統計"""
        try:
            cpu_percent = None
            source = 'unknown'
            
            # 嘗試從 Windows Performance Counters 獲取
            windows_cpu = self.windows_collector.get_windows_cpu_usage()
            if windows_cpu is not None:
                cpu_percent = windows_cpu
                source = 'windows_host'
            elif True:
                # 嘗試從主機 /proc/stat 獲取
                host_cpu_usage = self._get_host_cpu_usage()
                if host_cpu_usage is not None:
                    cpu_percent = host_cpu_usage
                    source = 'host_proc'
                else:
                    # 回退到容器 CPU
                    cpu_percent = psutil.cpu_percent(interval=1)
                    source = 'container'
            
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            cpu_per_core = psutil.cpu_percent(percpu=True, interval=0.1)
            
            load_avg = None
            try:
                import os
                if os.path.exists('/host/proc/loadavg'):
                    with open('/host/proc/loadavg', 'r') as f:
                        line = f.readline().strip()
                        load_values = line.split()[:3]
                        load_avg = [float(x) for x in load_values]
                else:
                    load_avg = psutil.getloadavg()
            except (AttributeError, FileNotFoundError, ValueError):
                pass
            
            return {
                'cpu_usage': round(cpu_percent, 2) if cpu_percent is not None else 0,
                'cpu_count': cpu_count,
                'cpu_freq_mhz': round(cpu_freq.current) if cpu_freq else None,
                'cpu_per_core': [round(usage, 2) for usage in cpu_per_core],
                'load_avg': [round(load, 2) for load in load_avg] if load_avg else None,
                'source': source
            }
            
        except Exception as e:
            return {
                'cpu_usage': 0,
                'cpu_count': psutil.cpu_count(),
                'error': str(e),
                'source': 'error'
            }
    
    def get_memory_stats(self) -> Dict:
        """獲取記憶體使用統計"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # 嘗試從 /proc/meminfo 獲取主機記憶體信息
            host_memory_info = None
            try:
                import os
                if os.path.exists('/host/proc/meminfo'):
                    with open('/host/proc/meminfo', 'r') as f:
                        meminfo = {}
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                key = parts[0].rstrip(':')
                                value = int(parts[1]) * 1024
                                meminfo[key] = value
                    
                    if 'MemTotal' in meminfo and 'MemAvailable' in meminfo:
                        host_total = meminfo['MemTotal']
                        host_available = meminfo['MemAvailable']
                        host_used = host_total - host_available
                        host_percent = (host_used / host_total) * 100
                        
                        host_memory_info = {
                            'ram_total_gb': round(host_total / (1024**3), 2),
                            'ram_used_gb': round(host_used / (1024**3), 2),
                            'ram_usage': round(host_percent, 2),
                            'ram_available_gb': round(host_available / (1024**3), 2),
                            'source': 'host'
                        }
            except:
                pass
            
            if host_memory_info:
                result = host_memory_info
                result.update({
                    'swap_total_gb': round(swap.total / (1024**3), 2),
                    'swap_used_gb': round(swap.used / (1024**3), 2),
                    'swap_usage': round(swap.percent, 2) if swap.total > 0 else 0
                })
                return result
            else:
                return {
                    'ram_total_gb': round(memory.total / (1024**3), 2),
                    'ram_used_gb': round(memory.used / (1024**3), 2),
                    'ram_usage': round(memory.percent, 2),
                    'ram_available_gb': round(memory.available / (1024**3), 2),
                    'swap_total_gb': round(swap.total / (1024**3), 2),
                    'swap_used_gb': round(swap.used / (1024**3), 2),
                    'swap_usage': round(swap.percent, 2) if swap.total > 0 else 0,
                    'source': 'container'
                }
            
        except Exception as e:
            return {
                'ram_usage': 0,
                'ram_total_gb': 0,
                'error': str(e)
            }
