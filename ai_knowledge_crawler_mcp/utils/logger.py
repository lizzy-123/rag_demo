"""
全局日志工具 - 统一日志管理

功能：
1. 全局单例日志器
2. 同时输出到控制台和按日分割的文件
3. 替换项目所有原生 logging 调用
"""

import logging
import os
import sys
from datetime import datetime
from logging import Handler, LogRecord
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from pathlib import Path
from pathlib import Path
from pathlib import Path
from pathlib import Path
from pathlib import Path
from pathlib import Path
from pathlib import Path
from typing import Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",      # 重置
    }

    def format(self, record: LogRecord) -> str:
        # 根据日志级别添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        record.levelname = levelname
        return super().format(record)


class CrawlerLogger:
    """全局单例日志器"""

    _instance: Optional["CrawlerLogger"] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> "CrawlerLogger":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化（仅执行一次）"""
        if self._initialized:
            return
        self._initialized = True
        self._logger = None
        self._setup_lock = False

    def setup(
        self,
        logs_path: Path,
        log_level: str = "INFO",
        log_name: str = "crawler",
    ) -> logging.Logger:
        """
        配置日志系统

        Args:
            logs_path: 日志文件存储路径
            log_level: 日志级别
            log_name: 日志器名称

        Returns:
            Logger 实例
        """
        if self._logger is not None:
            return self._logger

        # 创建日志目录
        logs_path.mkdir(parents=True, exist_ok=True)

        # 创建 logger
        self._logger = logging.getLogger(log_name)
        self._logger.setLevel(getattr(logging, log_level.upper()))

        # 避免重复添加 handler
        if self._logger.handlers:
            return self._logger

        # 控制台 handler - 带颜色
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        console_handler.setFormatter(ColoredFormatter(console_format))

        # 文件 handler - 按日滚动
        log_file = logs_path / f"{log_name}.log"
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",  # 每天零点滚动
            interval=1,       # 每 1 个间隔
            backupCount=30,   # 保留 30 天
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        file_handler.setFormatter(logging.Formatter(file_format))

        # 添加 handler
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

        # 禁止向父 logger 传播
        self._logger.propagate = False

        return self._logger

    def get_logger(self) -> logging.Logger:
        """
        获取 Logger 实例

        Returns:
            Logger 实例

        Raises:
            RuntimeError: 如果未调用 setup 初始化
        """
        if self._logger is None:
            raise RuntimeError("Logger not initialized. Call setup() first.")
        return self._logger

    def get_child_logger(self, name: str) -> logging.Logger:
        """
        获取子 Logger（按模块名称）

        Args:
            name: 子模块名称

        Returns:
            子 Logger 实例
        """
        parent = self.get_logger()
        return logging.getLogger(f"{parent.name}.{name}")


# 全局单例实例
_logger_instance: Optional[CrawlerLogger] = None


def get_logger(
    logs_path: Optional[Path] = None,
    log_level: str = "INFO",
    log_name: str = "crawler",
) -> logging.Logger:
    """
    获取全局 Logger（首次调用时自动初始化）

    Args:
        logs_path: 日志路径（仅在首次初始化时需要）
        log_level: 日志级别
        log_name: 日志器名称

    Returns:
        Logger 实例
    """
    global _logger_instance

    if _logger_instance is None:
        _logger_instance = CrawlerLogger()
        if logs_path is None:
            raise RuntimeError("logs_path is required for initial setup")
        return _logger_instance.setup(logs_path, log_level, log_name)

    return _logger_instance.get_logger()


def get_child_logger(name: str) -> logging.Logger:
    """
    获取子 Logger

    Args:
        name: 子模块名称

    Returns:
        子 Logger 实例
    """
    global _logger_instance

    if _logger_instance is None:
        raise RuntimeError("Logger not initialized. Call get_logger() first.")

    return _logger_instance.get_child_logger(name)


# ========== 便捷函数 ==========

def init_logger(
    logs_path: Path,
    log_level: str = "INFO",
    log_name: str = "crawler",
) -> logging.Logger:
    """
    初始化全局日志（便捷函数）

    Args:
        logs_path: 日志路径
        log_level: 日志级别
        log_name: 日志器名称

    Returns:
        Logger 实例
    """
    return get_logger(logs_path, log_level, log_name)
