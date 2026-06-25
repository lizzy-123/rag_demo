"""
必应搜索 MCP 适配器

封装必应搜索 MCP 服务，用于分领域批量搜索 AI 技术关键词。
"""

import logging
from typing import Any, List, Dict, Optional
from .base_adapter import MCPAdapterBase

logger = logging.getLogger(__name__)


class BingSearchAdapter(MCPAdapterBase):
    """必应搜索 MCP 适配器"""

    def __init__(self, base_url: str = "http://127.0.0.1:8014/mcp", timeout: int = 60):
        """
        初始化必应搜索适配器

        Args:
            base_url: 必应搜索 MCP 服务地址
            timeout: 调用超时时间（秒）
        """
        super().__init__(base_url=base_url, timeout=timeout, adapter_name="bing_search")

    async def search_keywords(
        self,
        keywords: List[str],
        days: Optional[int] = None,
        category: Optional[str] = None,
        exclude_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        批量搜索 AI 技术关键词

        Args:
            keywords: 搜索关键词列表，如 ["RAG", "大模型基础", "Multi-Agent 智能体"]
            days: 限定近 N 天增量内容（如 7 表示近 7 天）
            category: 搜索分类（如 "tech", "news"）
            exclude_urls: 排除的 URL 列表（已抓取链接）

        Returns:
            搜索结果，包含文章标题、发布时间、原文链接
            {
                "results": [
                    {
                        "title": "文章标题",
                        "url": "原文链接",
                        "published_date": "发布时间",
                        "snippet": "摘要"
                    }
                ],
                "total": 总数，
                "filtered_count": 过滤后的数量
            }
        """
        arguments = {
            "keywords": keywords,
        }
        if days is not None:
            arguments["days"] = days
        if category is not None:
            arguments["category"] = category
        if exclude_urls is not None:
            arguments["exclude_urls"] = exclude_urls

        return await self.call_tool("bing_search", arguments)

    async def search_single_keyword(
        self,
        keyword: str,
        days: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索单个关键词

        Args:
            keyword: 单个搜索关键词
            days: 限定近 N 天
            limit: 返回结果数量限制

        Returns:
            搜索结果列表
        """
        result = await self.search_keywords(
            keywords=[keyword],
            days=days
        )
        return result.get("results", [])[:limit]
