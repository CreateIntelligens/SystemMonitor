#!/usr/bin/env python3
"""
系統資源收集器
收集 GPU、CPU、RAM 使用率數據
"""

import subprocess
import psutil
import re
import json
import time
import requests
from datetime import datetime
from typing import Dict, Optional, List


class GPUCollector:
    """NVIDIA GPU 數據收集器"""
    
    def __init__(self):
        self.gpu_available = self._check_nvidia_smi()
    
    def _check_nvidia_smi(self) -> bool:
        """檢查 nvidia-smi 是否可用"""
        try:
            result = subprocess.run(['nvidia-smi', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def get_gpu_stats(self) -> Optional[Dict]:
        """獲取 GPU 使用統計"""
        if not self.gpu_available:
            return None
        
        try:
            # 查詢 GPU 使用率和記憶體使用情況
            cmd = [
                'nvidia-smi',
                '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name',
                '--format=csv,noheader,nounits'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None
            
            # 解析輸出
            lines = result.stdout.strip().split('\n')
            gpu_stats = []
            
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                    
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 5:
                    try:
                        gpu_usage = int(parts[0]) if parts[0] != 'N/A' else 0
                        memory_used = int(parts[1]) if parts[1] != 'N/A' else 0
                        memory_total = int(parts[2]) if parts[2] != 'N/A' else 1
                        temperature = int(parts[3]) if parts[3] != 'N/A' else 0
                        gpu_name = parts[4]
                        
                        vram_usage = (memory_used / memory_total * 100) if memory_total > 0 else 0
                        
                        gpu_stats.append({
                            'gpu_id': i,
                            'gpu_name': gpu_name,
                            'gpu_usage': gpu_usage,
                            'vram_used_mb': memory_used,
                            'vram_total_mb': memory_total,
                            'vram_usage': round(vram_usage, 2),
                            'temperature': temperature
                        })
                        
                    except (ValueError, ZeroDivisionError):
                        continue
            
            return gpu_stats if gpu_stats else None
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return None
    
    def get_gpu_processes(self) -> Optional[List[Dict]]:
        """獲取 GPU 進程信息"""
        if not self.gpu_available:
            return None
        
        try:
            # 查詢計算應用程序進程
            cmd = [
                'nvidia-smi',
                '--query-compute-apps=pid,process_name,gpu_uuid,used_gpu_memory',
                '--format=csv,noheader,nounits'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None
            
            processes = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 4:
                    try:
                        pid = int(parts[0]) if parts[0] != 'N/A' else 0
                        process_name = parts[1] if parts[1] != 'N/A' else 'Unknown'
                        gpu_uuid = parts[2] if parts[2] != 'N/A' else ''
                        used_memory = int(parts[3]) if parts[3] != 'N/A' else 0
                        
                        # 嘗試獲取更多進程信息
                        try:
                            if pid > 0 and psutil.pid_exists(pid):
                                process = psutil.Process(pid)
                                cmd_line = ' '.join(process.cmdline()[:3]) if process.cmdline() else process_name
                                cpu_percent = process.cpu_percent()
                                memory_mb = process.memory_info().rss / (1024 * 1024)
                                create_time = datetime.fromtimestamp(process.create_time()).strftime('%H:%M:%S')
                            else:
                                cmd_line = process_name
                                cpu_percent = 0
                                memory_mb = 0
                                create_time = 'N/A'
                        except:
                            cmd_line = process_name
                            cpu_percent = 0
                            memory_mb = 0
                            create_time = 'N/A'
                        
                        processes.append({
                            'pid': pid,
                            'name': process_name,
                            'command': cmd_line,
                            'gpu_uuid': gpu_uuid,
                            'gpu_memory_mb': used_memory,
                            'cpu_percent': round(cpu_percent, 1),
                            'ram_mb': round(memory_mb, 1),
                            'start_time': create_time
                        })
                        
                    except (ValueError, IndexError):
                        continue
            
            return processes if processes else None
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return None
    
    def get_top_gpu_processes(self, limit: int = 10) -> Optional[List[Dict]]:
        """獲取佔用 GPU 最多的進程"""
        processes = self.get_gpu_processes()
        if not processes:
            return None
        
        # 按 GPU 記憶體使用量排序
        sorted_processes = sorted(processes, key=lambda x: x['gpu_memory_mb'], reverse=True)
        return sorted_processes[:limit]


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
                    # 提取數值
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
        
        # 解析 CPU 使用率（100 - idle）
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
            # 解析記憶體指標
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
                    # values: [user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice]
                    idle = values[3]
                    total = sum(values)
                    return {'idle': idle, 'total': total}
        except:
            pass
        return None
    
    def _get_host_cpu_usage(self):
        """計算主機 CPU 使用率"""
        try:
            # 讀取兩次 CPU 統計來計算使用率
            stat1 = self._read_host_cpu_stats()
            if not stat1:
                return None
            
            time.sleep(1)  # 等待 1 秒
            
            stat2 = self._read_host_cpu_stats()
            if not stat2:
                return None
            
            # 計算差值
            idle_diff = stat2['idle'] - stat1['idle']
            total_diff = stat2['total'] - stat1['total']
            
            if total_diff <= 0:
                return None
            
            # 計算 CPU 使用率
            cpu_usage = (total_diff - idle_diff) / total_diff * 100
            return round(cpu_usage, 2)
            
        except Exception:
            return None
    
    def get_cpu_stats(self) -> Dict:
        """獲取 CPU 使用統計"""
        try:
            # 嘗試多種方法獲取 CPU 使用率
            cpu_percent = None
            source = 'unknown'
            
            # 方法 1: 嘗試從 Windows Performance Counters 獲取
            windows_cpu = self.windows_collector.get_windows_cpu_usage()
            if windows_cpu is not None:
                cpu_percent = windows_cpu
                source = 'windows_host'
            
            # 方法 2: 嘗試從主機 /proc/stat 獲取
            elif True:  # 總是嘗試這個方法作為備援
                host_cpu_usage = self._get_host_cpu_usage()
                if host_cpu_usage is not None:
                    cpu_percent = host_cpu_usage
                    source = 'host_proc'
                else:
                    # 方法 3: 回退到容器 CPU
                    cpu_percent = psutil.cpu_percent(interval=1)
                    source = 'container'
            
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # 每核心使用率（只能從容器獲取）
            cpu_per_core = psutil.cpu_percent(percpu=True, interval=0.1)
            
            load_avg = None
            try:
                import os
                # 嘗試從主機獲取 load average
                if os.path.exists('/host/proc/loadavg'):
                    with open('/host/proc/loadavg', 'r') as f:
                        line = f.readline().strip()
                        load_values = line.split()[:3]
                        load_avg = [float(x) for x in load_values]
                else:
                    # Linux/macOS 可用
                    load_avg = psutil.getloadavg()
            except (AttributeError, FileNotFoundError, ValueError):
                # Windows 不支援 load average
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
            # 系統記憶體
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # 嘗試從 /proc/meminfo 獲取更準確的主機記憶體信息（如果是在容器中）
            host_memory_info = None
            try:
                import os
                if os.path.exists('/host/proc/meminfo'):
                    # 讀取主機的記憶體信息
                    with open('/host/proc/meminfo', 'r') as f:
                        meminfo = {}
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                key = parts[0].rstrip(':')
                                value = int(parts[1]) * 1024  # KB to bytes
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
            
            # 如果有主機記憶體信息，使用主機的，否則使用容器的
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


class SystemMonitorCollector:
    """統合系統監控收集器"""
    
    def __init__(self):
        self.gpu_collector = GPUCollector()
        self.system_collector = SystemCollector()
    
    def collect_all(self) -> Dict:
        """收集所有系統數據"""
        timestamp = datetime.now()
        
        # 收集 GPU 數據
        gpu_data = self.gpu_collector.get_gpu_stats()
        
        # 收集 GPU 進程數據
        gpu_processes = self.gpu_collector.get_gpu_processes()
        
        # 收集系統數據
        cpu_data = self.system_collector.get_cpu_stats()
        memory_data = self.system_collector.get_memory_stats()
        
        # 統合數據
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
        
        # 提取關鍵指標
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
        
        # 添加 GPU 數據（如果可用）
        if all_data['gpu'] and len(all_data['gpu']) > 0:
            # 使用第一個 GPU 的數據
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


def main():
    """測試收集器功能"""
    collector = SystemMonitorCollector()
    
    print("🔍 系統監控收集器測試")
    print("=" * 50)
    
    # 檢查 GPU 可用性
    if collector.is_gpu_available():
        print("✅ NVIDIA GPU 可用")
    else:
        print("⚠️  NVIDIA GPU 不可用，將只監控 CPU/RAM")
    
    print("\n📊 收集系統數據...")
    
    # 收集數據
    data = collector.collect_all()
    
    print(f"⏰ 時間: {data['timestamp']}")
    print(f"🖥️  CPU 使用率: {data['cpu']['cpu_usage']:.2f}%")
    print(f"💾 RAM 使用率: {data['memory']['ram_usage']:.2f}% ({data['memory']['ram_used_gb']:.2f}GB/{data['memory']['ram_total_gb']:.2f}GB)")
    
    if data['gpu']:
        for i, gpu in enumerate(data['gpu']):
            print(f"🎮 GPU {i} ({gpu['gpu_name']}): {gpu['gpu_usage']:.2f}%")
            print(f"📈 VRAM {i}: {gpu['vram_usage']:.2f}% ({gpu['vram_used_mb']:.0f}MB/{gpu['vram_total_mb']:.0f}MB)")
            print(f"🌡️  溫度 {i}: {gpu['temperature']}°C")
    
    print("\n📋 簡化數據格式:")
    simple_data = collector.collect_simple()
    for key, value in simple_data.items():
        if value is not None:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
