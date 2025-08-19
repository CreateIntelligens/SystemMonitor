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
try:
    import docker
except ImportError:
    docker = None
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    pynvml = None


class GPUCollector:
    """NVIDIA GPU 數據收集器"""
    
    def __init__(self):
        self.gpu_available = self._check_nvidia_smi()
        self.docker_client = self._init_docker_client()
        self.debug = True
        self.nvml_initialized = False
        self._init_nvml()
    
    def _init_docker_client(self):
        """初始化Docker客戶端"""
        if docker is None:
            return None
        
        # 嘗試多種連接方式
        connection_attempts = [
            lambda: docker.from_env(),
            lambda: docker.DockerClient(base_url='unix://var/run/docker.sock'),
            lambda: docker.DockerClient(base_url='npipe:////./pipe/docker_engine'),  # Windows
            lambda: docker.DockerClient(base_url='tcp://host.docker.internal:2375'),
        ]
        
        for attempt in connection_attempts:
            try:
                client = attempt()
                # 測試連接
                client.ping()
                return client
            except Exception as e:
                continue
        return None
    
    def _init_nvml(self):
        """初始化 NVML"""
        if not PYNVML_AVAILABLE:
            return
        
        try:
            pynvml.nvmlInit()
            self.nvml_initialized = True
        except Exception as e:
            pass
    
    def get_pid_gpu_info(self, target_pid: int) -> Optional[Dict]:
        """使用 NVML 查詢特定 PID 的 GPU 使用情況，包含 VRAM 和 GPU 使用率"""
        if not self.nvml_initialized:
            return None
        
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            
            for gpu_id in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                
                # 檢查會計模式是否啟用
                try:
                    accounting_enabled = (pynvml.nvmlDeviceGetAccountingMode(handle) == pynvml.NVML_FEATURE_ENABLED)
                except pynvml.NVMLError:
                    accounting_enabled = False

                # 查詢計算和圖形進程
                all_procs = []
                try:
                    all_procs.extend(pynvml.nvmlDeviceGetComputeRunningProcesses(handle))
                except pynvml.NVMLError:
                    pass
                try:
                    all_procs.extend(pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle))
                except pynvml.NVMLError:
                    pass
                
                # 檢查目標 PID
                for proc in all_procs:
                    if proc.pid == target_pid:
                        vram_used_mb = proc.usedGpuMemory // (1024 * 1024) if proc.usedGpuMemory is not None else 0
                        
                        # 獲取 GPU 使用率 (如果會計模式啟用)
                        gpu_utilization = 0
                        if accounting_enabled:
                            try:
                                acc_stats = pynvml.nvmlDeviceGetAccountingStats(handle, target_pid)
                                if acc_stats.isRunning:
                                    gpu_utilization = acc_stats.gpuUtilization
                            except pynvml.NVMLError:
                                pass  # 忽略錯誤，可能只是該進程沒有統計數據

                        # 獲取 GPU 名稱
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
            
        except Exception as e:
            if self.debug:
                pass
            return None
    
    def _build_pid_namespace_map(self) -> Dict[int, int]:
        """建立 PID 映射表，支援雙向查找"""
        container_to_host = {}  # 容器PID -> 主機PID
        host_to_container = {}  # 主機PID -> 容器PID
        
        try:
            # 方法1: 讀取 /proc/*/status 的 NSpid
            import os
            proc_path = "/host/proc" if os.path.exists("/host/proc") else "/proc"
            
            # 掃描所有主機進程
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
                                            # pids[0] 是主機PID，pids[1] 是容器PID
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
                                            # pids[0] 是主機PID，pids[1] 是容器PID
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
    
    def _get_container_process_map(self) -> Dict[int, Dict]:
        """獲取容器進程映射表 (PID -> 容器信息)"""
        container_map = {}
        if not self.docker_client:
            return container_map
        
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                try:
                    # 獲取容器內的進程
                    processes = container.top()['Processes']
                    container_info = {
                        'name': container.name,
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'status': container.status
                    }
                    
                    # 解析進程信息
                    for process in processes:
                        if len(process) >= 2:
                            try:
                                pid = int(process[1])  # 通常PID在第二列
                                container_map[pid] = container_info
                            except (ValueError, IndexError):
                                continue
                                
                except Exception:
                    continue
                    
        except Exception:
            pass
            
        return container_map
    
    def _check_nvidia_smi(self) -> bool:
        """檢查 nvidia-smi 是否可用，支援多種檢測方式以提高兼容性"""
        # 嘗試多種nvidia-smi命令來檢測可用性
        test_commands = [
            ['nvidia-smi', '--version'],       # 最常用的版本檢查
            ['nvidia-smi', '--list-gpus'],     # 適用於較舊驅動版本
            ['nvidia-smi', '-L'],              # 簡短的GPU列表命令
            ['nvidia-smi', '--help'],          # 基本幫助命令
            ['nvidia-smi']                     # 基本狀態查詢
        ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(cmd, 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"[DEBUG] NVIDIA GPU 檢測成功，使用命令: {' '.join(cmd)}")
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                continue
                
        pass
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
        """獲取 GPU 進程的混合方法。
        1. 主要方法: 解析 nvidia-smi 的完整輸出，獲取詳細進程信息。
        2. 備用方法: 掃描系統進程列表，查找可能使用 GPU 的進程關鍵字。
        3. 新增: 整合Docker容器信息，識別進程來源。
        """
        if not self.gpu_available:
            return None

        processes = {}
        
        # 獲取容器進程映射和PID namespace映射
        container_map = self._get_container_process_map()
        pid_namespace_map = self._build_pid_namespace_map()  # 容器PID -> 主機PID

        # 1. 主要方法: NVML (更快更準確)
        if self.nvml_initialized:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                
                for gpu_id in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)

                    # 檢查會計模式
                    try:
                        accounting_enabled = (pynvml.nvmlDeviceGetAccountingMode(handle) == pynvml.NVML_FEATURE_ENABLED)
                        if self.debug:
                            print(f"[DEBUG] GPU {gpu_id}: Accounting mode enabled: {accounting_enabled}")
                    except pynvml.NVMLError as e:
                        accounting_enabled = False
                        if self.debug:
                            print(f"[DEBUG] GPU {gpu_id}: Could not get accounting mode. Error: {e}")
                    
                    # 獲取所有GPU進程
                    all_procs = []
                    try:
                        compute_procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                        all_procs.extend(compute_procs)
                        if self.debug:
                            print(f"[DEBUG] GPU {gpu_id}: 找到 {len(compute_procs)} 個 Compute 進程")
                    except pynvml.NVMLError as e:
                        if self.debug:
                            print(f"[DEBUG] GPU {gpu_id}: 無法獲取 Compute 進程: {e}")
                    try:
                        graphics_procs = pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle)
                        all_procs.extend(graphics_procs)
                        if self.debug:
                            print(f"[DEBUG] GPU {gpu_id}: 找到 {len(graphics_procs)} 個 Graphics 進程")
                    except pynvml.NVMLError as e:
                        if self.debug:
                            print(f"[DEBUG] GPU {gpu_id}: 無法獲取 Graphics 進程: {e}")
                    
                    if self.debug:
                        print(f"[DEBUG] GPU {gpu_id}: 總共找到 {len(all_procs)} 個 GPU 進程")
                    
                    # 獲取GPU名稱
                    try:
                        gpu_name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    except:
                        gpu_name = f"GPU {gpu_id}"
                    
                    # 處理每個GPU進程
                    for proc in all_procs:
                        nvml_pid = proc.pid
                        vram_used_mb = proc.usedGpuMemory // (1024 * 1024) if proc.usedGpuMemory is not None else 0
                        
                        if self.debug:
                            print(f"[DEBUG] 處理 GPU 進程: NVML_PID={nvml_pid}, VRAM={vram_used_mb}MB")
                            # 添加進程詳細信息
                            try:
                                proc_name = pynvml.nvmlSystemGetProcessName(nvml_pid)
                                print(f"[DEBUG]   - NVML 進程名稱: {proc_name}")
                            except Exception as e:
                                print(f"[DEBUG]   - 無法從 NVML 獲取進程名稱: {e}")
                            
                            # 顯示當前的PID映射狀態
                            print(f"[DEBUG]   - 可用的PID映射: {dict(list(pid_namespace_map.items())[:5])}")  # 只顯示前5個
                            print(f"[DEBUG]   - PID {nvml_pid} 是否存在於主機: {psutil.pid_exists(nvml_pid)}")
                            if nvml_pid in pid_namespace_map:
                                print(f"[DEBUG]   - 容器PID {nvml_pid} -> 主機PID {pid_namespace_map[nvml_pid]}")
                        
                        # 智能 PID 解析：NVML 可能回報主機 PID 或容器 PID
                        target_pid = None
                        pid_source = "unknown"
                        
                        # 方法1: 假設 NVML 回報的是主機 PID（最常見情況）
                        if psutil.pid_exists(nvml_pid):
                            target_pid = nvml_pid
                            pid_source = "direct_host"
                            if self.debug:
                                print(f"[DEBUG] NVML PID {nvml_pid} 直接存在於主機系統中")
                        
                        # 方法2: 假設 NVML 回報的是容器 PID，需要映射到主機 PID
                        elif nvml_pid in pid_namespace_map:
                            target_pid = pid_namespace_map[nvml_pid]
                            pid_source = "container_to_host"
                            if self.debug:
                                print(f"[DEBUG] 容器PID {nvml_pid} 映射到主機PID {target_pid}")
                        
                        # 方法2b: 暫時禁用 Docker API 查找（因為存在兼容性問題）
                        # elif self.docker_client:
                        #     # Docker API 查找暫時禁用
                        #     pass
                        
                        # 方法3: 嘗試反向查找 - 檢查是否有主機PID對應到這個容器PID
                        else:
                            # 在所有已知的PID映射中查找
                            found_host_pid = None
                            for container_pid, host_pid in pid_namespace_map.items():
                                # 檢查是否有其他容器PID映射到可能相關的主機PID
                                if abs(container_pid - nvml_pid) <= 10:  # 容器內PID通常相近
                                    # 驗證這個主機PID是否真的在使用GPU
                                    verification = self.get_pid_gpu_info(host_pid)
                                    if verification and verification.get('found'):
                                        found_host_pid = host_pid
                                        if self.debug:
                                            print(f"[DEBUG] 通過相近PID推測: 容器PID {nvml_pid} 可能對應主機PID {host_pid}")
                                        break
                            
                            if found_host_pid:
                                target_pid = found_host_pid
                                pid_source = "nearby_pid_guess"
                            else:
                                # 方法4: 智能搜索策略
                                if self.debug:
                                    print(f"[DEBUG] 開始智能搜索以找到 NVML PID {nvml_pid} 的對應進程")
                                
                                # 策略4a: 檢查所有已知的主機PID，看是否有使用GPU的
                                for host_pid in self.host_to_container.keys():
                                    try:
                                        verification = self.get_pid_gpu_info(host_pid)
                                        if verification and verification.get('found'):
                                            # 檢查VRAM使用量是否匹配（允許小幅差異）
                                            vram_diff = abs(verification.get('vram_used_mb', 0) - vram_used_mb)
                                            if vram_diff <= 1:  # 允許1MB的差異
                                                target_pid = host_pid
                                                pid_source = "host_pid_verification"
                                                if self.debug:
                                                    print(f"[DEBUG] 通過主機PID驗證找到: NVML PID {nvml_pid} -> 主機PID {target_pid} (VRAM差異: {vram_diff}MB)")
                                                break
                                    except:
                                        continue
                                
                                # 策略4b: 如果還沒找到，搜索可能的GPU進程
                                if not target_pid and vram_used_mb > 0:  # 只有在有VRAM使用時才搜索
                                    if self.debug:
                                        print(f"[DEBUG] 開始搜索VRAM使用量為 {vram_used_mb}MB 的進程")
                                    
                                    # 高效搜索：只檢查可能使用GPU的進程類型
                                    search_count = 0
                                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                                        search_count += 1
                                        if search_count > 100:  # 限制搜索數量
                                            break
                                            
                                        try:
                                            proc_name = proc.info['name'].lower()
                                            cmdline = ' '.join(proc.info.get('cmdline', [])).lower()
                                            
                                            # 只檢查可能使用GPU的進程
                                            gpu_keywords = ['python', 'torch', 'cuda', 'nvidia', 'tensorflow', 'uvr5', 'ncnn']
                                            if any(keyword in proc_name or keyword in cmdline for keyword in gpu_keywords):
                                                # 直接用NVML驗證
                                                verification = self.get_pid_gpu_info(proc.info['pid'])
                                                if verification and verification.get('found'):
                                                    vram_diff = abs(verification.get('vram_used_mb', 0) - vram_used_mb)
                                                    if vram_diff <= 2:  # 允許2MB的差異
                                                        target_pid = proc.info['pid']
                                                        pid_source = "keyword_search_match"
                                                        if self.debug:
                                                            print(f"[DEBUG] 關鍵字搜索找到匹配: NVML PID {nvml_pid} -> 主機PID {target_pid} (VRAM差異: {vram_diff}MB)")
                                                        break
                                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                                            continue
                                    
                                    if self.debug:
                                        print(f"[DEBUG] 關鍵字搜索檢查了 {search_count} 個進程")
                        
                        # 對於Windows WDDM模式，無法獲得進程級別的VRAM，但可以記錄進程存在
                        if not target_pid:
                            if self.debug:
                                print(f"[DEBUG] 無法找到 NVML PID {nvml_pid} 對應的主機PID")
                                # 在WDDM模式下，嘗試記錄Graphics進程資訊
                                try:
                                    proc_name = pynvml.nvmlSystemGetProcessName(nvml_pid)
                                    if proc_name and not proc_name.startswith('/X'):  # 排除X11相關進程
                                        print(f"[DEBUG] Windows WDDM模式 - 發現GPU進程但無法映射PID: {proc_name}")
                                except:
                                    pass
                            continue

                        # 獲取 GPU 使用率
                        gpu_utilization = 0
                        if accounting_enabled:
                            try:
                                # 使用目標 PID 進行查詢
                                acc_stats = pynvml.nvmlDeviceGetAccountingStats(handle, target_pid)
                                if acc_stats.isRunning:
                                    gpu_utilization = acc_stats.gpuUtilization
                                if self.debug:
                                    print(f"[DEBUG] PID {target_pid}: Accounting stats found. GPU Util: {gpu_utilization}")
                            except pynvml.NVMLError as e:
                                if self.debug:
                                    print(f"[DEBUG] PID {target_pid}: Could not get accounting stats. Error: {e}")
                                pass
                        elif self.debug:
                            print(f"[DEBUG] GPU {gpu_id}: Accounting mode disabled for PID {nvml_pid}. Skipping utilization check.")

                        if psutil.pid_exists(target_pid):
                            try:
                                p = psutil.Process(target_pid)
                                container_info = container_map.get(target_pid, None)
                                container_name = container_info['name'] if container_info else 'Host'
                                container_source = f"{container_info['name']} ({container_info['image']})" if container_info else '主機'
                                
                                # 組合進程類型描述
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
                                
                                if self.debug:
                                    print(f"🎯 NVML主要方法: PID {target_pid}(NVML:{nvml_pid},{pid_source}) 使用 {proc_type}")
                                    
                            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                                if self.debug:
                                    print(f"[DEBUG] 無法訪問PID {target_pid}: {e}")
                                continue
                        else:
                            if self.debug:
                                print(f"[DEBUG] PID {target_pid} 不存在於系統中")
                                
            except Exception as e:
                if self.debug:
                    print(f"[WARNING] NVML主要方法失敗: {e}")
        
        # 2. 備用方法: nvidia-smi (當NVML失效時)
        if not self.nvml_initialized:
            if self.debug:
                print("[DEBUG] NVML 未初始化，使用 nvidia-smi 作為備用方案。")
        elif not processes:  # 只有當NVML沒找到進程時才用nvidia-smi
            if self.debug:
                print("[DEBUG] NVML 已初始化但未找到進程，使用 nvidia-smi 作為備用方案。")
                # 在Windows WDDM模式下，提供總體GPU使用情況
                try:
                    gpu_stats = self.get_gpu_stats()
                    if gpu_stats and len(gpu_stats) > 0:
                        gpu_info = gpu_stats[0]
                        if gpu_info.get('gpu_usage', 0) > 0 or gpu_info.get('vram_used_mb', 0) > 1000:
                            print(f"[DEBUG] Windows WDDM模式 - GPU正在使用中:")
                            print(f"[DEBUG]   - GPU使用率: {gpu_info.get('gpu_usage', 0)}%")
                            print(f"[DEBUG]   - VRAM使用: {gpu_info.get('vram_used_mb', 0)}MB / {gpu_info.get('vram_total_mb', 0)}MB")
                            print(f"[DEBUG]   - 溫度: {gpu_info.get('temperature', 0)}°C")
                except Exception as e:
                    print(f"[DEBUG] 無法獲取GPU總體狀態: {e}")
        
        if not self.nvml_initialized or not processes:
            try:
                # 標準nvidia-smi輸出
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
                        
                        # 跳過分隔線和標題行
                        if '===' in line or 'GPU' in line or 'PID' in line or 'No running processes' in line:
                            continue
                        
                        # 簡單分割處理，更穩定
                        line_cleaned = line.strip('|').strip()
                        if not line_cleaned:
                            continue
                            
                        # 以空白分割，尋找 PID 和記憶體使用
                        parts = line_cleaned.split()
                        if len(parts) >= 5:
                            try:
                                # 典型格式: |   PID   Type   Process name                    GPU Memory Usage |
                                #          |     0    N/A    N/A        1234      C   python3                      123MiB |
                                
                                # 找到第一個數字作為PID
                                pid = None
                                proc_type = None
                                memory_usage = None
                                
                                for i, part in enumerate(parts):
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
                                proc_name = ' '.join([p for p in parts if not p.isdigit() and p not in ['N/A', 'C', 'G', 'C+G'] and not p.endswith('MiB')])[:50]

                                if psutil.pid_exists(pid):
                                    p = psutil.Process(pid)
                                    
                                    # 檢查是否為容器進程
                                    container_info = container_map.get(pid, None)
                                    container_name = container_info['name'] if container_info else 'Host'
                                    container_source = f"{container_info['name']} ({container_info['image']})" if container_info else '主機'
                                    
                                    processes[pid] = {
                                        'pid': pid, 
                                        'name': p.name(),
                                        'command': ' '.join(p.cmdline()) if p.cmdline() else proc_name,
                                        'gpu_memory_mb': gpu_memory_mb,
                                        'gpu_utilization': 0, # nvidia-smi不提供此數據
                                        'cpu_percent': round(p.cpu_percent(), 1),
                                        'ram_mb': round(p.memory_info().rss / (1024 * 1024), 1),
                                        'start_time': datetime.fromtimestamp(p.create_time()).strftime('%m-%d %H:%M:%S'),
                                        'type': f'NVIDIA {"Graphics" if proc_type == "G" else "Compute"}',
                                        'container': container_name,
                                        'container_source': container_source
                                    }
                            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError) as e:
                                if self.debug:
                                    print(f"⚠️  無法訪問PID {pid}: {e}")
                                continue
                else:
                    if self.debug:
                        print(f"[WARNING] nvidia-smi 命令執行失敗: {result.stderr}")

                # 方法2: 嘗試compute apps查詢補充GPU記憶體信息
                try:
                    compute_result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,used_memory', '--format=csv,noheader,nounits'], 
                                                  capture_output=True, text=True, timeout=10)
                    if compute_result.returncode == 0:
                        for line in compute_result.stdout.strip().split('\n'):
                            if line.strip():
                                parts = [p.strip() for p in line.split(',')]
                                if len(parts) >= 2:
                                    try:
                                        pid = int(parts[0]) if parts[0] and parts[0].isdigit() else None
                                        if pid is None:
                                            continue
                                        mem_usage = parts[1]
                                        gpu_memory_mb = int(mem_usage) if mem_usage and mem_usage != '[N/A]' and mem_usage.isdigit() else 0
                                        
                                        # 更新已存在的進程或新增進程
                                        if pid in processes:
                                            processes[pid]['gpu_memory_mb'] = gpu_memory_mb
                                        elif psutil.pid_exists(pid):
                                            p = psutil.Process(pid)
                                            container_info = container_map.get(pid, None)
                                            container_name = container_info['name'] if container_info else 'Host'
                                            container_source = f"{container_info['name']} ({container_info['image']})" if container_info else '主機'
                                            
                                            processes[pid] = {
                                                'pid': pid,
                                                'name': p.name(),
                                                'command': ' '.join(p.cmdline()) if p.cmdline() else 'Unknown',
                                                'gpu_memory_mb': gpu_memory_mb,
                                                'gpu_utilization': 0, # nvidia-smi不提供此數據
                                                'cpu_percent': round(p.cpu_percent(), 1),
                                                'ram_mb': round(p.memory_info().rss / (1024 * 1024), 1),
                                                'start_time': datetime.fromtimestamp(p.create_time()).strftime('%m-%d %H:%M:%S'),
                                                'type': 'NVIDIA Compute',
                                                'container': container_name,
                                                'container_source': container_source
                                            }
                                    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                                        continue
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
                if self.debug:
                    print(f"[ERROR] 執行 nvidia-smi 時出錯: {e}")
        
        # 3. 補充方法: 關鍵字掃描 (找可能遺漏的GPU相關進程)
        try:
            gpu_keywords = ['torch', 'cuda', 'tensorflow', 'uvr5', 'ncnn']
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'create_time']):
                if proc.info['pid'] in processes: # 如果主要方法已經找到了，就跳過
                    continue
                
                cmd_line = ' '.join(proc.info['cmdline'] or [])
                proc_name = proc.info['name'] or ''
                full_search_text = f"{proc_name} {cmd_line}".lower()
                
                # 檢查GPU關鍵字
                has_gpu_keywords = any(keyword in full_search_text for keyword in gpu_keywords)
                
                # 檢查是否為Python進程（檢查進程名和命令行）
                is_python_process = (
                    'python' in proc_name.lower() or 
                    'python' in cmd_line.lower()
                )
                
                if has_gpu_keywords or is_python_process:
                    p = psutil.Process(proc.info['pid'])
                    
                    # 使用 NVML 查詢精確的 GPU 使用情況
                    # 首先直接用主機PID查詢
                    nvml_info = self.get_pid_gpu_info(p.pid)
                    
                    # 如果直接查詢失敗，嘗試反向PID映射 (主機PID可能對應容器PID)
                    if not nvml_info or not nvml_info.get('found'):
                        # 查找是否有容器PID對應到這個主機PID
                        for container_pid, host_pid in pid_namespace_map.items():
                            if host_pid == p.pid:
                                nvml_info = self.get_pid_gpu_info(container_pid)
                                if nvml_info and nvml_info.get('found') and self.debug:
                                    print(f"[DEBUG] 通過PID映射找到: 主機PID {p.pid} <-> 容器PID {container_pid}")
                                break
                    
                    gpu_memory_mb = 0
                    gpu_utilization = 0
                    proc_type = 'Potential GPU (Keyword)' if has_gpu_keywords else 'Python Process'
                    
                    if nvml_info and nvml_info.get('found'):
                        gpu_memory_mb = nvml_info.get('vram_used_mb', 0)
                        gpu_utilization = nvml_info.get('gpu_utilization', 0)
                        
                        # 更新進程類型描述
                        proc_type = f"🎯 GPU {nvml_info['gpu_id']}"
                        if gpu_utilization > 0:
                            proc_type += f" - {gpu_utilization}% GPU"
                        if gpu_memory_mb > 0:
                            proc_type += f" - {gpu_memory_mb}MB VRAM"
                        if gpu_utilization == 0 and gpu_memory_mb == 0:
                            proc_type += " - 使用中"

                        if self.debug:
                            print(f"🎯 NVML 確認 PID={p.pid} 使用 GPU {nvml_info['gpu_id']}, VRAM={gpu_memory_mb}MB, Util={gpu_utilization}%")
                    else:
                        # Windows WDDM模式下，無法獲得進程級VRAM，但可以根據關鍵字推測
                        if has_gpu_keywords:
                            # 檢查GPU是否正在被大量使用
                            try:
                                gpu_stats = self.get_gpu_stats()
                                if gpu_stats and len(gpu_stats) > 0:
                                    gpu_info = gpu_stats[0]
                                    if gpu_info.get('gpu_usage', 0) > 80:  # GPU使用率>80%
                                        proc_type = f"🔥 可能的GPU進程 (系統GPU: {gpu_info.get('gpu_usage', 0)}%)"
                                        if self.debug:
                                            print(f"🔥 Windows WDDM模式 - 高GPU使用率時發現關鍵字進程: PID={p.pid}, 名稱={proc_name}")
                                    elif self.debug:
                                        print(f"🔍 關鍵字匹配但GPU使用率低: PID={p.pid}, 名稱={proc_name}")
                                elif self.debug:
                                    print(f"🔍 關鍵字匹配但無法獲取GPU狀態: PID={p.pid}, 名稱={proc_name}")
                            except:
                                if self.debug:
                                    print(f"🔍 關鍵字匹配但GPU狀態查詢失敗: PID={p.pid}, 名稱={proc_name}")
                        elif self.debug and is_python_process:
                            print(f"🐍 Python進程: PID={p.pid}, 名稱={proc_name}")
                    
                    # 檢查是否為容器進程
                    container_info = container_map.get(p.pid, None)
                    container_name = container_info['name'] if container_info else 'Host'
                    container_source = f"{container_info['name']} ({container_info['image']})" if container_info else '主機'
                    
                    # 避免重複：如果該進程已經在 processes 中，更新其資訊而不是覆蓋
                    if p.pid not in processes:
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
                    else:
                        # 如果進程已存在，但有更準確的GPU資訊，則更新
                        existing = processes[p.pid]
                        if gpu_memory_mb > existing.get('gpu_memory_mb', 0):
                            existing['gpu_memory_mb'] = gpu_memory_mb
                            existing['gpu_utilization'] = gpu_utilization
                            existing['type'] = proc_type
                            if self.debug:
                                print(f"[DEBUG] 更新現有進程 {p.pid} 的GPU資訊: {gpu_memory_mb}MB")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return list(processes.values()) if processes else None
    
    
    
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
