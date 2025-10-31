#!/usr/bin/env python3
"""
進程處理工具
處理 PID 映射、容器進程識別等
"""

import os
import psutil

class ProcessHelper:
    """進程處理輔助類別"""
    
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.host_to_container = {}
    
    def build_pid_namespace_map(self) -> dict:
        """建立 PID 映射表，支援雙向查找"""
        container_to_host = {}
        host_to_container = {}
        
        try:
            proc_path = "/host/proc" if os.path.exists("/host/proc") else "/proc"
            
            if os.path.exists("/host/proc"):
                # 在容器中，掃描主機的 /proc
                for pid_dir in os.listdir("/host/proc"):
                    if not pid_dir.isdigit():
                        continue
                    
                    try:
                        host_pid = int(pid_dir)
                        status_file = f"/host/proc/{host_pid}/status"
                        
                        if os.path.exists(status_file):
                            with open(status_file, 'r') as f:
                                for line in f:
                                    if line.startswith('NSpid:'):
                                        pids = line.split(':')[1].strip().split()
                                        if len(pids) >= 2:
                                            actual_host_pid = int(pids[0])
                                            container_pid = int(pids[1])
                                            
                                            container_to_host[container_pid] = actual_host_pid
                                            host_to_container[actual_host_pid] = container_pid
                                            
                                            if self.debug:
                                                print(f"[DEBUG] PID映射: 容器{container_pid} -> 主機{actual_host_pid}")
                                        break
                    except (FileNotFoundError, PermissionError, ValueError, OSError):
                        continue
            else:
                # 在主機上，使用 psutil
                for proc in psutil.process_iter(['pid']):
                    try:
                        host_pid = proc.info['pid']
                        status_file = f"/proc/{host_pid}/status"
                        
                        if os.path.exists(status_file):
                            with open(status_file, 'r') as f:
                                for line in f:
                                    if line.startswith('NSpid:'):
                                        pids = line.split(':')[1].strip().split()
                                        if len(pids) >= 2:
                                            actual_host_pid = int(pids[0])
                                            container_pid = int(pids[1])
                                            
                                            container_to_host[container_pid] = actual_host_pid
                                            host_to_container[actual_host_pid] = container_pid
                                            
                                            if self.debug:
                                                print(f"[DEBUG] PID映射: 容器{container_pid} -> 主機{actual_host_pid}")
                                        break
                    except (FileNotFoundError, PermissionError, ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
            if self.debug:
                print(f"[DEBUG] 建立了 {len(container_to_host)} 個 PID 映射")
                    
        except Exception as e:
            if self.debug:
                print(f"[WARNING] PID namespace映射失敗: {e}")
        
        self.host_to_container = host_to_container
        return container_to_host
    
    def search_gpu_processes_by_keywords(self, gpu_keywords: list) -> list:
        """通過關鍵字搜索可能使用 GPU 的進程"""
        matched_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'create_time']):
                try:
                    cmd_line = ' '.join(proc.info['cmdline'] or [])
                    proc_name = proc.info['name'] or ''
                    full_search_text = f"{proc_name} {cmd_line}".lower()
                    
                    has_gpu_keywords = any(keyword in full_search_text for keyword in gpu_keywords)
                    is_python_process = 'python' in proc_name.lower() or 'python' in cmd_line.lower()
                    
                    if has_gpu_keywords or is_python_process:
                        matched_processes.append(proc)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            if self.debug:
                print(f"[WARNING] 關鍵字搜索失敗: {e}")
        
        return matched_processes
