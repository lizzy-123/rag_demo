"""
Fetch 网页内容抓取 MCP 适配器

封装云端 Fetch MCP 服务（streamable_http 协议），用于批量抓取网页并输出纯净 Markdown 原文。

云端服务地址：https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp
注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址。
"""

import logging
from typing import Any, Dict, List

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from .base_adapter import MCPAdapterBase

logger = logging.getLogger(__name__)


class FetchAdapter(MCPAdapterBase):
    """Fetch 网页内容抓取适配器 - 云端 streamable_http 版本"""

    def __init__(self, config: CrawlerConfig | None = None):
        """
        初始化 Fetch 适配器

        Args:
            config: 全局配置对象，可选。如果未提供，使用默认云端地址
        """
        if config is None:
            config = CrawlerConfig()

        # 使用云端 streamable_http 地址
        base_url = config.FETCH_MCP_STREAM_URL
        timeout = config.FETCH_MCP_TIMEOUT

        super().__init__(base_url=base_url, timeout=timeout, adapter_name="fetch_cloud")
        self.config = config

    async def fetch_url(
        self,
        url: str,
        max_length: int = 5000,
        start_index: int = 0,
        raw: bool = False,
    ) -> Dict[str, Any]:
        """
        抓取单个 URL 并转换为 Markdown

        使用云端 fetch 工具，对齐官方入参标准。

        Args:
            url: 目标 URL（必填）
            max_length: 最大返回内容长度（tokens），默认 5000
            start_index: 起始索引，默认 0
            raw: 是否返回原始内容，默认 False

        Returns:
            抓取结果
            {
                "url": "原始 URL",
                "markdown": "纯净 Markdown 原文",
                "title": "页面标题",
                "status": "success|failed",
                "error": "错误信息（如果失败）"
            }
        """
        arguments = {
            "url": url,
            "max_length": max_length,
            "start_index": start_index,
            "raw": raw,
        }

        try:
            result = await self.call_tool("fetch", arguments)
            # 处理返回结果：可能是字典或字符串
            if isinstance(result, str):
                # 如果是字符串，尝试解析 JSON 或作为 markdown 内容
                import json
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    # 无法解析 JSON，直接作为 markdown 内容
                    return {
                        "url": url,
                        "markdown": result,
                        "title": "",
                        "status": "success",
                        "error": None,
                    }
            # 统一返回结构
            return {
                "url": url,
                "markdown": result.get("markdown", result.get("content", "")) if isinstance(result, dict) else str(result),
                "title": result.get("title", "") if isinstance(result, dict) else "",
                "status": "success",
                "error": None,
            }
        except Exception as e:
            logger.error(f"[fetch] Failed to fetch {url}: {e}")
            return {
                "url": url,
                "markdown": "",
                "title": "",
                "status": "failed",
                "error": str(e),
            }

    async def fetch_urls_batch(
        self,
        urls: List[str],
        max_length: int = 5000,
        retry_count: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        批量抓取 URL 列表

        Args:
            urls: URL 列表
            max_length: 最大返回内容长度（tokens），默认 5000
            retry_count: 失败重试次数

        Returns:
            抓取结果列表
            [
                {
                    "url": "原始 URL",
                    "markdown": "纯净 Markdown 原文",
                    "title": "页面标题",
                    "status": "success|failed",
                    "retry_count": 实际重试次数
                },
                ...
            ]
        """
        results = []

        for url in urls:
            last_error = None
            success = False

            for attempt in range(retry_count + 1):
                try:
                    logger.info(
                        f"[fetch] Fetching {url} (attempt {attempt + 1}/{retry_count + 1})"
                    )
                    result = await self.fetch_url(url, max_length=max_length)
                    result["retry_count"] = attempt
                    results.append(result)
                    success = True
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"[fetch] Failed to fetch {url} (attempt {attempt + 1}): {e}"
                    )

            if not success:
                # 记录失败结果
                results.append(
                    {
                        "url": url,
                        "markdown": "",
                        "title": "",
                        "status": "failed",
                        "error": last_error,
                        "retry_count": retry_count,
                    }
                )
                logger.error(f"[fetch] Final failure for {url}: {last_error}")

        return results

    async def fetch_single_with_retry(
        self,
        url: str,
        max_length: int = 5000,
        retry_count: int = 2,
    ) -> Dict[str, Any] | None:
        """
        抓取单个 URL，带重试逻辑

        Args:
            url: 目标 URL
            max_length: 最大返回内容长度（tokens），默认 5000
            retry_count: 失败重试次数

        Returns:
            成功时返回抓取结果，失败时返回 None
        """
        for attempt in range(retry_count + 1):
            try:
                logger.info(
                    f"[fetch] Fetching {url} (attempt {attempt + 1}/{retry_count + 1})"
                )
                result = await self.fetch_url(url, max_length=max_length)
                result["retry_count"] = attempt
                if result.get("status") == "success":
                    return result
            except Exception as e:
                logger.warning(
                    f"[fetch] Failed to fetch {url} (attempt {attempt + 1}): {e}"
                )

        return None

    async def health_check(self) -> bool:
        """
        健康检测：检查云端 Fetch 服务是否可用

        通过调用 fetch 工具抓取一个测试 URL 来验证服务连通性。

        Returns:
            True 表示服务正常，False 表示服务不可用
        """
        try:
            # 使用一个稳定的测试 URL
            test_url = "https://www.example.com"
            logger.info(f"[fetch] Health check: testing connectivity to {test_url}")

            result = await self.fetch_url(test_url, max_length=100)

            if result.get("status") == "success" and result.get("markdown"):
                logger.info("[fetch] Health check: service is healthy")
                return True
            else:
                logger.warning(
                    f"[fetch] Health check: service returned invalid response: {result}"
                )
                return False

        except Exception as e:
            logger.error(f"[fetch] Health check failed: {e}")
            return False
