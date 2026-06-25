"""
MCP Client Adapter Layer

复用项目原有 multi_agent/agent/mcp_client.py 中的 FastMCPClient 通信逻辑，
仅做业务参数封装，不重复实现 MCP 底层协议。
"""

from .bing_search_adapter import BingSearchAdapter
from .fetch_adapter import FetchAdapter
from .doc_processor_adapter import DocProcessorAdapter

__all__ = [
    "BingSearchAdapter",
    "FetchAdapter",
    "DocProcessorAdapter",
]
