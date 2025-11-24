#!/usr/bin/env python3
"""
系統資源收集器 - 向後兼容入口
原始 collectors.py 已拆分為多個模組，此檔案保留向後兼容性

新代碼請使用:
    from src.core.collectors import SystemMonitorCollector

拆分結構:
    - collectors/base.py          - SystemMonitorCollector (主入口)
    - collectors/gpu.py            - GPUCollector
    - collectors/system.py         - SystemCollector, WindowsHostCollector
    - collectors/docker_helper.py  - DockerHelper
    - collectors/process.py        - ProcessHelper
"""

# 從新模組導入所有類別，保持向後兼容
from .collectors import (
    SystemMonitorCollector,
    GPUCollector,
    SystemCollector,
    WindowsHostCollector,
    DockerHelper,
    ProcessHelper,
)

__all__ = [
    'SystemMonitorCollector',
    'GPUCollector',
    'SystemCollector',
    'WindowsHostCollector',
    'DockerHelper',
    'ProcessHelper',
]

def main():
    """測試收集器功能"""
    collector = SystemMonitorCollector()
    
    print("🔍 系統監控收集器測試")
    print("=" * 50)
    
    if collector.is_gpu_available():
        print("✅ NVIDIA GPU 可用")
    else:
        print("⚠️  NVIDIA GPU 不可用，將只監控 CPU/RAM")
    
    print("\n📊 收集系統數據...")
    
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
