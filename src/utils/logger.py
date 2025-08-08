#!/usr/bin/env python3
"""
日誌管理模塊
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "monitor",
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_size: str = "10MB",
    backup_count: int = 5
) -> logging.Logger:
    """
    設置日誌記錄器
    
    Args:
        name: 日誌器名稱
        level: 日誌級別
        log_file: 日誌文件路徑
        max_size: 日誌文件最大大小
        backup_count: 備份文件數量
    
    Returns:
        配置好的日誌記錄器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重複添加處理器
    if logger.handlers:
        return logger
    
    # 創建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件處理器（如果指定了日誌文件）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 解析文件大小
        size_bytes = parse_size(max_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=size_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def parse_size(size_str: str) -> int:
    """
    解析大小字符串為字節數
    
    Args:
        size_str: 大小字符串，如 '10MB', '1GB'
    
    Returns:
        字節數
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(float(size_str[:-2]) * 1024)
    elif size_str.endswith('MB'):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith('GB'):
        return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
    else:
        # 假設是字節數
        return int(size_str)


class MonitorLogger:
    """監控專用日誌器"""
    
    def __init__(self, config=None):
        """
        初始化監控日誌器
        
        Args:
            config: 配置對象
        """
        if config:
            level = config.get('logging.level', 'INFO')
            log_file = config.get('logging.file', 'logs/monitor.log')
            max_size = config.get('logging.max_size', '10MB')
            backup_count = config.get('logging.backup_count', 5)
        else:
            level = 'INFO'
            log_file = 'logs/monitor.log'
            max_size = '10MB'
            backup_count = 5
        
        self.logger = setup_logger(
            name='monitor',
            level=level,
            log_file=log_file,
            max_size=max_size,
            backup_count=backup_count
        )
    
    def info(self, msg: str):
        """記錄信息日誌"""
        self.logger.info(msg)
    
    def warning(self, msg: str):
        """記錄警告日誌"""
        self.logger.warning(msg)
    
    def error(self, msg: str):
        """記錄錯誤日誌"""
        self.logger.error(msg)
    
    def debug(self, msg: str):
        """記錄調試日誌"""
        self.logger.debug(msg)
    
    def exception(self, msg: str):
        """記錄異常日誌"""
        self.logger.exception(msg)


def main():
    """測試日誌功能"""
    print("📝 日誌管理測試")
    print("=" * 40)
    
    # 測試基本日誌器
    logger = setup_logger(
        name="test",
        level="DEBUG",
        log_file="logs/test.log"
    )
    
    logger.debug("這是調試信息")
    logger.info("這是信息日誌")
    logger.warning("這是警告日誌")
    logger.error("這是錯誤日誌")
    
    # 測試監控日誌器
    monitor_logger = MonitorLogger()
    monitor_logger.info("監控系統啟動")
    monitor_logger.warning("GPU 不可用")
    
    print("✅ 日誌測試完成，查看 logs/ 目錄")


if __name__ == "__main__":
    main()