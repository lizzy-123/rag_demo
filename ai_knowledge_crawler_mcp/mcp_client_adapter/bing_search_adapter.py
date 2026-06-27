"""
Bing 搜索 MCP 适配器 - 云端 streamable_http 版本

封装云端 Bing 搜索 MCP 服务（streamable_http 协议），用于分领域批量搜索 AI 技术关键词。

云端服务地址：https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp
注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址。
"""

import logging
from typing import Any, Dict, List, Optional

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from .base_adapter import MCPAdapterBase

logger = logging.getLogger(__name__)


class BingSearchAdapter(MCPAdapterBase):
    """Bing 搜索 MCP 适配器 - 云端 streamable_http 版本"""

    def __init__(self, config: CrawlerConfig | None = None):
        """
        初始化 Bing 搜索适配器

        Args:
            config: 全局配置对象，可选。如果未提供，使用默认云端地址
        """
        if config is None:
            config = CrawlerConfig()

        # 使用云端 streamable_http 地址
        base_url = config.BING_SEARCH_MCP_STREAM_URL
        timeout = config.BING_MCP_TIMEOUT

        super().__init__(base_url=base_url, timeout=timeout, adapter_name="bing_search_cloud")
        self.config = config

    async def search_keywords(
        self,
        keywords: List[str],
        days: Optional[int] = None,
        category: Optional[str] = None,
        exclude_urls: Optional[List[str]] = None,
        count: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        批量搜索 AI 技术关键词

        Args:
            keywords: 搜索关键词列表，如 ["RAG", "大模型基础", "Multi-Agent 智能体"]
            days: 限定近 N 天增量内容（如 7 表示近 7 天）
            category: 搜索分类（如 "tech", "news"）
            exclude_urls: 排除的 URL 列表（已抓取链接）
            count: 返回条数，默认 10，最大 50
            offset: 翻页偏移，默认 0

        Returns:
            搜索结果，包含文章标题、发布时间、原文链接
            {
                "results": [...],
                "total": 总数，
                "filtered_count": 过滤后的数量
            }
        """
        # 参数边界校验
        if count < 1 or count > 50:
            raise ValueError(f"count 参数必须在 1-50 之间，当前值：{count}")
        if offset < 0:
            raise ValueError(f"offset 参数不能为负数，当前值：{offset}")

        # 组装 MCP 调用参数（使用 query 作为必填参数）
        arguments = {
            "query": ", ".join(keywords),  # 将关键词列表转为查询字符串
            "count": count,
            "offset": offset,
        }
        if days is not None:
            arguments["days"] = days
        if category is not None:
            arguments["category"] = category
        if exclude_urls is not None:
            arguments["exclude_urls"] = exclude_urls
            arguments["days"] = days
        if category is not None:
            arguments["category"] = category
        if exclude_urls is not None:
            arguments["exclude_urls"] = exclude_urls

        try:
            result = await self.call_tool("bing_search", arguments)
            # 统一返回结构
            if isinstance(result, str):
                import json

                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    return {"results": [], "total": 0, "filtered_count": 0, "error": result}

            return {
                "results": result.get("results", []),
                "total": result.get("total", 0),
                "filtered_count": result.get("filtered_count", len(result.get("results", []))),
            }
        except Exception as e:
            logger.error(f"[bing_search] Search failed: {e}")
            return {"results": [], "total": 0, "filtered_count": 0, "error": str(e)}

    async def search_single_keyword(
        self, keyword: str, days: Optional[int] = None, limit: int = 10
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
        result = await self.search_keywords(keywords=[keyword], days=days)
        return result.get("results", [])[:limit]

    async def health_check(self) -> bool:
        """
        健康检测：检查云端 Bing 搜索服务是否可用

        通过调用 bing_search 工具搜索一个测试关键词来验证服务连通性。

        Returns:
            True 表示服务正常，False 表示服务不可用
        """
        try:
            logger.info("[bing_search] Health check: testing connectivity to cloud service")

            # 使用一个通用关键词测试
            result = await self.search_keywords(keywords=["test"], days=1)

            # 只要能返回结构化结果即视为服务正常
            if isinstance(result, dict) and "results" in result:
                logger.info("[bing_search] Health check: service is healthy")
                return True
            else:
                logger.warning(
                    f"[bing_search] Health check: service returned invalid response: {result}"
                )
                return False

        except Exception as e:
            logger.error(f"[bing_search] Health check failed: {e}")
            return False
