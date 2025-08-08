#!/usr/bin/env python3
"""
配置管理模塊
"""

import os
from pathlib import Path
from typing import Dict, Any
import json


class Config:
    """配置管理器"""
    
    # 默認配置
    DEFAULT_CONFIG = {
        'database': {
            'path': 'data/monitoring.db',
            'cleanup_days': 30
        },
        'monitoring': {
            'interval': 30,
            'auto_cleanup': True
        },
        'web': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False
        },
        'plots': {
            'output_dir': 'data/plots',
            'default_timespan': '24h',
            'dpi': 300
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/monitor.log',
            'max_size': '10MB',
            'backup_count': 5
        }
    }
    
    def __init__(self, config_file: str = None):
        """
        初始化配置
        
        Args:
            config_file: 配置文件路徑
        """
        self.config_file = config_file or 'config/config.json'
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
        self.create_directories()
    
    def load_config(self):
        """加載配置文件"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 深度合併配置
                self._deep_merge(self.config, user_config)
                print(f"✅ 配置已加載: {config_path}")
                
            except Exception as e:
                print(f"⚠️  配置文件載入失敗，使用預設配置: {e}")
        else:
            print(f"ℹ️  配置文件不存在，使用預設配置")
            self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存: {config_path}")
        except Exception as e:
            print(f"❌ 配置保存失敗: {e}")
    
    def create_directories(self):
        """創建必要的目錄"""
        directories = [
            self.get('database.path', '').rsplit('/', 1)[0] if '/' in self.get('database.path', '') else 'data',
            self.get('plots.output_dir'),
            self.get('logging.file', '').rsplit('/', 1)[0] if '/' in self.get('logging.file', '') else 'logs'
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str, default: Any = None):
        """
        獲取配置值，支持點記法
        
        Args:
            key: 配置鍵，支持 'section.key' 格式
            default: 默認值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        設置配置值，支持點記法
        
        Args:
            key: 配置鍵
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def _deep_merge(self, base: Dict, update: Dict):
        """深度合併字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    @property
    def database_path(self) -> str:
        """數據庫路徑"""
        return self.get('database.path')
    
    @property
    def monitoring_interval(self) -> int:
        """監控間隔"""
        return self.get('monitoring.interval')
    
    @property
    def web_host(self) -> str:
        """Web 服務主機"""
        return self.get('web.host')
    
    @property
    def web_port(self) -> int:
        """Web 服務端口"""
        return self.get('web.port')
    
    @property
    def plots_dir(self) -> str:
        """圖表輸出目錄"""
        return self.get('plots.output_dir')


def main():
    """測試配置功能"""
    print("🔧 配置管理測試")
    print("=" * 40)
    
    config = Config()
    
    print(f"數據庫路徑: {config.database_path}")
    print(f"監控間隔: {config.monitoring_interval}s")
    print(f"Web 服務: {config.web_host}:{config.web_port}")
    print(f"圖表目錄: {config.plots_dir}")
    
    # 測試設置配置
    config.set('monitoring.interval', 60)
    print(f"更新後監控間隔: {config.monitoring_interval}s")


if __name__ == "__main__":
    main()