"""
AI 知识库 MCP 采集预处理模块 - 统一入口

支持手动单次执行 / 后台定时循环执行。
"""

import asyncio
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """入口函数 - 待实现抓取、清洗、定时、RAG 导出逻辑"""
    logger.info("AI Knowledge Crawler MCP Module Started")
    logger.info("Directory structure created. MCP adapters initialized.")
    logger.info("TODO: Implement crawl_task, scheduling, and RAG export logic.")


if __name__ == "__main__":
    main()
