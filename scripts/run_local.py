#!/usr/bin/env python3
"""
本機直接運行腳本
"""

import sys
import subprocess
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
CLI_ENTRY = BACKEND_DIR / "cli.py"
REQUIREMENTS_FILE = BACKEND_DIR / "requirements.txt"

def check_python():
    """檢查 Python 環境"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("需要 Python 3.8+")
        return False
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    return True

def install_dependencies():
    """安裝依賴"""
    print("檢查依賴...")
    
    try:
        import fastapi, uvicorn, psutil, pandas, matplotlib
        print("核心依賴已安裝")
        return True
    except ImportError as e:
        print(f"缺少依賴: {e}")
        
        choice = input("是否自動安裝依賴? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            print("安裝依賴中...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])
                print("依賴安裝完成")
                return True
            except subprocess.CalledProcessError:
                print("依賴安裝失敗")
                return False
        else:
            print(f"💡 請手動執行: pip install -r {REQUIREMENTS_FILE}")
            return False

def check_gpu():
    """檢查 GPU 可用性"""
    try:
        result = subprocess.run(['nvidia-smi', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ NVIDIA GPU 可用")
            return True
    except:
        pass
    
    print("⚠️  NVIDIA GPU 不可用，將只監控 CPU/RAM")
    return False

def main():
    print("系統監控工具 - 本機運行")
    print("=" * 40)
    
    # 檢查 Python
    if not check_python():
        sys.exit(1)
    
    # 檢查依賴
    if not install_dependencies():
        sys.exit(1)
    
    # 檢查 GPU
    check_gpu()
    
    print("\n🎯 可用指令:")
    print("  python backend/cli.py status         # 查看狀態")
    print("  python backend/cli.py monitor        # 開始監控")  
    print("  python backend/cli.py web            # Web 介面")
    print("  python backend/cli.py plot 24h       # 生成圖表")
    
    # 如果有參數，直接執行
    if len(sys.argv) > 1:
        cmd = [sys.executable, str(CLI_ENTRY)] + sys.argv[1:]
        print(f"\n🔄 執行: {' '.join(cmd)}")
        subprocess.call(cmd)
    else:
        print(f"\n💡 範例: python {sys.argv[0]} web")

if __name__ == "__main__":
    main()
