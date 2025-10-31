#!/usr/bin/env python3
"""
GPU 收集器
處理 NVIDIA GPU 統計和進程信息收集
"""

import subprocess
import psutil
import platform
from datetime import datetime
from typing import Dict, Optional, List

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    pynvml = None

from .docker_helper import DockerHelper
from .process import ProcessHelper

class GPUCollector:
    """NVIDIA GPU 數據收集器"""
    
    def __init__(self):
        self.gpu_available = self._check_nvidia_smi()
        self.docker_helper = DockerHelper()
        self.process_helper = ProcessHelper()
        self.debug = True
        self.nvml_initialized = False
        self._init_nvml()
    
    def _init_nvml(self):
        """初始化 NVML"""
        if not PYNVML_AVAILABLE:
            return
        
        try:
            pynvml.nvmlInit()
            self.nvml_initialized = True
        except Exception:
            pass
    
    def _check_nvidia_smi(self) -> bool:
        """檢查 nvidia-smi 是否可用"""
        test_commands = [
            ['nvidia-smi', '--version'],
            ['nvidia-smi', '--list-gpus'],
            ['nvidia-smi', '-L'],
            ['nvidia-smi', '--help'],
            ['nvidia-smi']
        ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"[DEBUG] NVIDIA GPU 檢測成功，使用命令: {' '.join(cmd)}")
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                continue
        
        return False
    
    def get_pid_gpu_info(self, target_pid: int) -> Optional[Dict]:
        """使用 NVML 查詢特定 PID 的 GPU 使用情況"""
        if not self.nvml_initialized:
            return None
        
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            
            for gpu_id in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                
                try:
                    accounting_enabled = (pynvml.nvmlDeviceGetAccountingMode(handle) == pynvml.NVML_FEATURE_ENABLED)
                except pynvml.NVMLError:
                    accounting_enabled = False

                all_procs = []
                try:
                    all_procs.extend(pynvml.nvmlDeviceGetComputeRunningProcesses(handle))
                except pynvml.NVMLError:
                    pass
                try:
                    all_procs.extend(pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle))
                except pynvml.NVMLError:
                    pass
                
                for proc in all_procs:
                    if proc.pid == target_pid:
                        vram_used_mb = proc.usedGpuMemory // (1024 * 1024) if proc.usedGpuMemory is not None else 0
                        
                        gpu_utilization = 0
                        if accounting_enabled:
                            try:
                                acc_stats = pynvml.nvmlDeviceGetAccountingStats(handle, target_pid)
                                if acc_stats.isRunning:
                                    gpu_utilization = acc_stats.gpuUtilization
                            except pynvml.NVMLError:
                                pass

                        try:
                            gpu_name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                        except:
                            gpu_name = f"GPU {gpu_id}"
                        
                        return {
                            'gpu_id': gpu_id,
                            'gpu_name': gpu_name,
                            'vram_used_mb': vram_used_mb,
                            'gpu_utilization': gpu_utilization,
                            'found': True,
                            'detected_by_nvml': True
                        }
            
            return {'found': False}
            
        except Exception:
            return None
    
    def get_gpu_stats(self) -> Optional[List[Dict]]:
        """獲取 GPU 使用統計"""
        if not self.gpu_available:
            return None
        
        try:
            cmd = [
                'nvidia-smi',
                '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name',
                '--format=csv,noheader,nounits'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None
            
            lines = result.stdout.strip().split('\n')
            gpu_stats = []
            
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                    
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 5:
                    try:
                        gpu_usage = int(parts[0]) if parts[0] and parts[0] != 'N/A' and parts[0].strip() else 0
                        memory_used = int(parts[1]) if parts[1] and parts[1] != 'N/A' and parts[1].strip() else 0
                        memory_total = int(parts[2]) if parts[2] and parts[2] != 'N/A' and parts[2].strip() else 1
                        temperature = int(parts[3]) if parts[3] and parts[3] != 'N/A' and parts[3].strip() else 0
                        gpu_name = parts[4] if len(parts) > 4 else 'Unknown GPU'
                        
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

        processes = {}
        
        container_map = self.docker_helper.get_container_process_map()
        pid_namespace_map = self.process_helper.build_pid_namespace_map()

        # 使用 NVML 收集進程
        if self.nvml_initialized:
            processes = self._collect_gpu_processes_nvml(container_map, pid_namespace_map)
        
        # 使用 nvidia-smi 補充
        if not self.nvml_initialized or not processes:
            processes = self._collect_gpu_processes_nvidia_smi(container_map, processes)
        
        # 關鍵字搜索補充
        self._supplement_with_keyword_search(processes, container_map, pid_namespace_map)

        return list(processes.values()) if processes else None
    
    def _collect_gpu_processes_nvml(self, container_map, pid_namespace_map) -> dict:
        """使用 NVML 收集 GPU 進程"""
        processes = {}
        
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            
            for gpu_id in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)

                try:
                    accounting_enabled = (pynvml.nvmlDeviceGetAccountingMode(handle) == pynvml.NVML_FEATURE_ENABLED)
                except pynvml.NVMLError:
                    accounting_enabled = False
                
                all_procs = []
                try:
                    all_procs.extend(pynvml.nvmlDeviceGetComputeRunningProcesses(handle))
                except pynvml.NVMLError:
                    pass
                try:
                    all_procs.extend(pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle))
                except pynvml.NVMLError:
                    pass
                
                try:
                    gpu_name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                except:
                    gpu_name = f"GPU {gpu_id}"
                
                for proc in all_procs:
                    nvml_pid = proc.pid
                    vram_used_mb = proc.usedGpuMemory // (1024 * 1024) if proc.usedGpuMemory is not None else 0
                    
                    target_pid = self._resolve_pid(nvml_pid, pid_namespace_map, vram_used_mb)
                    
                    if not target_pid:
                        continue

                    gpu_utilization = 0
                    if accounting_enabled:
                        try:
                            acc_stats = pynvml.nvmlDeviceGetAccountingStats(handle, target_pid)
                            if acc_stats.isRunning:
                                gpu_utilization = acc_stats.gpuUtilization
                        except pynvml.NVMLError:
                            pass

                    if psutil.pid_exists(target_pid):
                        try:
                            p = psutil.Process(target_pid)
                            container_info = container_map.get(target_pid, None)
                            container_name = container_info['name'] if container_info else 'Host'
                            container_source = f"{container_info['name']} ({container_info['image']})" if container_info else '主機'
                            
                            proc_type = f"🎯 GPU {gpu_id} ({gpu_name})"
                            if gpu_utilization > 0:
                                proc_type += f" - {gpu_utilization}% GPU"
                            if vram_used_mb > 0:
                                proc_type += f" - {vram_used_mb}MB VRAM"
                            if gpu_utilization == 0 and vram_used_mb == 0:
                                proc_type += " - 使用中"
                            
                            processes[target_pid] = {
                                'pid': target_pid,
                                'name': p.name(),
                                'command': ' '.join(p.cmdline()) if p.cmdline() else 'Unknown',
                                'gpu_memory_mb': vram_used_mb,
                                'gpu_utilization': gpu_utilization,
                                'cpu_percent': round(p.cpu_percent(), 1),
                                'ram_mb': round(p.memory_info().rss / (1024 * 1024), 1),
                                'start_time': datetime.fromtimestamp(p.create_time()).strftime('%m-%d %H:%M:%S'),
                                'type': proc_type,
                                'container': container_name,
                                'container_source': container_source
                            }
                                
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                                
        except Exception as e:
            if self.debug:
                print(f"[WARNING] NVML 收集失敗: {e}")
        
        return processes
    
    def _resolve_pid(self, nvml_pid: int, pid_namespace_map: dict, vram_used_mb: int) -> Optional[int]:
        """解析 NVML PID 到實際主機 PID"""
        if psutil.pid_exists(nvml_pid):
            return nvml_pid
        
        if nvml_pid in pid_namespace_map:
            return pid_namespace_map[nvml_pid]
        
        for host_pid in self.process_helper.host_to_container.keys():
            try:
                verification = self.get_pid_gpu_info(host_pid)
                if verification and verification.get('found'):
                    vram_diff = abs(verification.get('vram_used_mb', 0) - vram_used_mb)
                    if vram_diff <= 1:
                        return host_pid
            except:
                continue
        
        return None
    
    def _collect_gpu_processes_nvidia_smi(self, container_map, processes) -> dict:
        """使用 nvidia-smi 收集進程（備用方案）"""
        if processes is None:
            processes = {}
        
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10, encoding='utf-8')
            if result.returncode == 0:
                output = result.stdout
                in_processes_section = False
                for line in output.split('\n'):
                    if line.startswith('| Processes:'):
                        in_processes_section = True
                        continue
                    if not in_processes_section or not line.startswith('|'):
                        continue
                    
                    if '===' in line or 'GPU' in line or 'PID' in line or 'No running processes' in line:
                        continue
                    
                    line_cleaned = line.strip('|').strip()
                    if not line_cleaned:
                        continue
                        
                    parts = line_cleaned.split()
                    if len(parts) >= 5:
                        try:
                            pid = None
                            proc_type = None
                            memory_usage = None
                            
                            for part in parts:
                                if part.isdigit() and pid is None:
                                    pid = int(part)
                                elif part in ['C', 'G', 'C+G'] and proc_type is None:
                                    proc_type = part
                                elif part.endswith('MiB') and memory_usage is None:
                                    try:
                                        memory_usage = int(part.replace('MiB', ''))
                                    except ValueError:
                                        memory_usage = 0
                            
                            if pid is None:
                                continue
                                
                            proc_type = proc_type or 'Unknown'
                            gpu_memory_mb = memory_usage or 0

                            if psutil.pid_exists(pid) and pid not in processes:
                                p = psutil.Process(pid)
                                
                                container_info = container_map.get(pid, None)
                                container_name = container_info['name'] if container_info else 'Host'
                                container_source = f"{container_info['name']} ({container_info['image']})" if container_info else '主機'
                                
                                processes[pid] = {
                                    'pid': pid, 
                                    'name': p.name(),
                                    'command': ' '.join(p.cmdline()) if p.cmdline() else 'Unknown',
                                    'gpu_memory_mb': gpu_memory_mb,
                                    'gpu_utilization': 0,
                                    'cpu_percent': round(p.cpu_percent(), 1),
                                    'ram_mb': round(p.memory_info().rss / (1024 * 1024), 1),
                                    'start_time': datetime.fromtimestamp(p.create_time()).strftime('%m-%d %H:%M:%S'),
                                    'type': f'NVIDIA {"Graphics" if proc_type == "G" else "Compute"}',
                                    'container': container_name,
                                    'container_source': container_source
                                }
                        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                            continue
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return processes
    
    def _supplement_with_keyword_search(self, processes, container_map, pid_namespace_map):
        """使用關鍵字搜索補充 GPU 進程"""
        gpu_keywords = ['torch', 'cuda', 'tensorflow', 'uvr5', 'ncnn']
        matched_procs = self.process_helper.search_gpu_processes_by_keywords(gpu_keywords)
        
        for proc in matched_procs:
            if proc.info['pid'] in processes:
                continue
            
            p = psutil.Process(proc.info['pid'])
            nvml_info = self.get_pid_gpu_info(p.pid)
            
            if not nvml_info or not nvml_info.get('found'):
                for container_pid, host_pid in pid_namespace_map.items():
                    if host_pid == p.pid:
                        nvml_info = self.get_pid_gpu_info(container_pid)
                        break
            
            gpu_memory_mb = 0
            gpu_utilization = 0
            proc_type = 'Potential GPU (Keyword)'
            
            if nvml_info and nvml_info.get('found'):
                gpu_memory_mb = nvml_info.get('vram_used_mb', 0)
                gpu_utilization = nvml_info.get('gpu_utilization', 0)
                
                proc_type = f"🎯 GPU {nvml_info['gpu_id']}"
                if gpu_utilization > 0:
                    proc_type += f" - {gpu_utilization}% GPU"
                if gpu_memory_mb > 0:
                    proc_type += f" - {gpu_memory_mb}MB VRAM"
            
            container_info = container_map.get(p.pid, None)
            container_name = container_info['name'] if container_info else 'Host'
            container_source = f"{container_info['name']} ({container_info['image']})" if container_info else '主機'
            
            if p.pid not in processes:
                cmd_line = ' '.join(proc.info['cmdline'] or [])
                processes[p.pid] = {
                    'pid': p.pid, 
                    'name': p.name(),
                    'command': cmd_line,
                    'gpu_memory_mb': gpu_memory_mb,
                    'gpu_utilization': gpu_utilization,
                    'cpu_percent': round(p.cpu_percent(), 1),
                    'ram_mb': round(p.memory_info().rss / (1024 * 1024), 1),
                    'start_time': datetime.fromtimestamp(p.create_time()).strftime('%m-%d %H:%M:%S'),
                    'type': proc_type,
                    'container': container_name,
                    'container_source': container_source
                }
    
    def get_top_gpu_processes(self, limit: int = 10) -> Optional[List[Dict]]:
        """獲取佔用 GPU 最多的進程"""
        processes = self.get_gpu_processes()
        if not processes:
            return None
        
        sorted_processes = sorted(processes, key=lambda x: x['gpu_memory_mb'], reverse=True)
        return sorted_processes[:limit]
