"""
Bing 搜索 MCP 适配器 - 云端 streamable_http 版本

封装云端 Bing 搜索 MCP 服务（streamable_http 协议），用于分领域批量搜索 AI 技术关键词。

云端服务地址：https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp
注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址。
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from ai_knowledge_crawler_mcp.utils.exceptions import BingSearchError
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
        exclude_urls: Optional[List[str]] = None,
        count: int = 10,
        max_total_results: int = 100,
    ) -> Dict[str, Any]:
        """
        批量搜索 AI 技术关键词（逐个关键词独立搜索后合并去重）

        Args:
            keywords: 搜索关键词列表，如 ["RAG", "大模型基础", "Multi-Agent 智能体"]
            days: 限定近 N 天增量内容（如 7 表示近 7 天）
            exclude_urls: 排除的 URL 列表（已抓取链接）
            count: 每个关键词返回条数，默认 10，最大 50
            max_total_results: 最大总结果数限制（用于分页控制）

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
            raise BingSearchError(f"count 参数必须在 1-50 之间，当前值：{count}")

        if not keywords:
            return {"results": [], "total": 0, "filtered_count": 0}

        logger.info(f"[bing_search] 开始搜索 {len(keywords)} 个关键词")

        all_results: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        # 逐个关键词独立搜索
        for keyword in keywords:
            try:
                logger.debug(f"[bing_search] 搜索关键词：{keyword}")

                # 分页拉取直到达到最大结果数或无更多结果
                offset = 0
                while len(all_results) < max_total_results:
                    # 计算本次需要获取的数量
                    remaining = max_total_results - len(all_results)
                    current_count = min(count, remaining)

                    if current_count <= 0:
                        break

                    # 构建参数
                    arguments = {"query": keyword}
                    if current_count != 10:
                        arguments["count"] = current_count
                    if offset != 0:
                        arguments["offset"] = offset
                    if days is not None:
                        arguments["days"] = days
                    if exclude_urls:
                        arguments["exclude_urls"] = exclude_urls

                    # 调用 MCP 工具
                    result = await self.call_tool("bing_search", arguments)

                    # 解析结果
                    if isinstance(result, str):
                        try:
                            result = json.loads(result)
                        except json.JSONDecodeError:
                            raise BingSearchError.InvalidResponse(
                                f"搜索关键词 '{keyword}' 返回格式错误：非 JSON 字符串"
                            )

                    keyword_results = result.get("results", [])

                    if not keyword_results:
                        logger.warning(f"[bing_search] 关键词 '{keyword}' 无搜索结果")
                        break

                    # 去重并添加结果
                    added_count = 0
                    for item in keyword_results:
                        url = item.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(item)
                            added_count += 1

                    logger.debug(
                        f"[bing_search] 关键词 '{keyword}' 第 {offset // count + 1} 页：获取 {len(keyword_results)} 条，新增 {added_count} 条"
                    )

                    # 如果返回结果少于请求数量，说明没有更多结果
                    if len(keyword_results) < current_count:
                        break

                    offset += current_count

                    # 请求间隔防限流
                    if self.config.MCP_REQUEST_INTERVAL > 0:
                        await asyncio.sleep(self.config.MCP_REQUEST_INTERVAL)

            except BingSearchError:
                raise
            except TimeoutError as e:
                raise BingSearchError.Timeout(f"搜索关键词 '{keyword}' 超时：{e}")
            except Exception as e:
                logger.error(f"[bing_search] 搜索关键词 '{keyword}' 失败：{e}")
                continue

        # 应用 exclude_urls 过滤（双重保险）
        if exclude_urls:
            exclude_set = set(exclude_urls)
            all_results = [r for r in all_results if r.get("url") not in exclude_set]

        logger.info(f"[bing_search] 搜索完成，共获取 {len(all_results)} 条结果")

        return {
            "results": all_results,
            "total": len(all_results),
            "filtered_count": len(all_results),
        }

    async def search_single_keyword(
        self,
        keyword: str,
        days: Optional[int] = None,
        count: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        搜索单个关键词

        Args:
            keyword: 单个搜索关键词
            days: 限定近 N 天
            count: 返回结果数量限制

        Returns:
            搜索结果列表
        """
        result = await self.search_keywords(keywords=[keyword], days=days, count=count)
        return result.get("results", [])

    async def health_check(self) -> bool:
        """
        健康检测：检查云端 Bing 搜索服务是否可用

        通过调用 bing_search 工具搜索一个测试关键词来验证服务连通性。

        Returns:
            True 表示服务正常，False 表示服务不可用
        """
        try:
            logger.info("[bing_search] Health check: testing connectivity...")
            result = await self.search_keywords(keywords=["test"], days=1, count=1)

            # 严格校验：必须无错误字段，且 results 列表非空
            if isinstance(result, dict) and not result.get("error") and result.get("results"):
                logger.info("[bing_search] Health check: service is healthy")
                return True
            else:
                logger.warning(f"[bing_search] Health check: service returned invalid or empty response: {result}")
                return False
        except BingSearchError as e:
            logger.error(f"[bing_search] Health check failed with BingSearchError: {e}")
            return False
        except TimeoutError:
            logger.error("[bing_search] Health check timeout")
            return False
        except Exception as e:
            logger.error(f"[bing_search] Health check failed: {e}")
            return False
