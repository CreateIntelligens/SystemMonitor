#!/usr/bin/env python3
"""
Docker 輔助工具
處理 Docker 容器相關操作
"""

try:
    import docker
except ImportError:
    docker = None

class DockerHelper:
    """Docker 輔助類別"""
    
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.docker_client = self._init_docker_client()
    
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
                client.ping()
                return client
            except Exception:
                continue
        return None
    
    def get_container_process_map(self) -> dict:
        """獲取容器進程映射表 (PID -> 容器信息)"""
        container_map = {}
        if not self.docker_client:
            return container_map
        
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                try:
                    processes = container.top()['Processes']
                    container_info = {
                        'name': container.name,
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'status': container.status
                    }
                    
                    for process in processes:
                        if len(process) >= 2:
                            try:
                                pid = int(process[1])
                                container_map[pid] = container_info
                            except (ValueError, IndexError):
                                continue
                                
                except Exception:
                    continue
                    
        except Exception:
            pass
            
        return container_map
