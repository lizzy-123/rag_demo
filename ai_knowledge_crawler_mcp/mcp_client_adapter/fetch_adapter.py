"""
Fetch 网页内容抓取 MCP 适配器

封装云端 Fetch MCP 服务（streamable_http 协议），用于批量抓取网页并输出纯净 Markdown 原文。

云端服务地址：https://mcp.api-inference.modelscope.net/955c976957164d/mcp

"""

import asyncio
import json
import logging
import time
from functools import wraps
from typing import Any, Dict, List, Optional, Callable

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from ai_knowledge_crawler_mcp.utils.exceptions import FetchError
from .base_adapter import MCPAdapterBase

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 2, delay: float = 1.0):
    """
    重试装饰器 - 捕获 FetchError 并自动重试

    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except FetchError as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            f"[fetch] {func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise FetchError.MaxRetriesExceeded(
                            f"{func.__name__} 超过最大重试次数 {max_retries}",
                            details={"url": kwargs.get("url"), "last_error": str(e)}
                        )
                except Exception as e:
                    # 非 FetchError 直接抛出
                    raise

            raise FetchError.MaxRetriesExceeded(f"未知的重试错误")

        return wrapper
    return decorator


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
        # 信号量控制并发数
        self._semaphore = asyncio.Semaphore(config.FETCH_CONCURRENT_LIMIT)

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
            # 使用信号量控制并发
            async with self._semaphore:
                # 单次抓取独立超时
                result = await asyncio.wait_for(
                    self.call_tool("fetch", arguments),
                    timeout=min(self.timeout, self.config.FETCH_MCP_TIMEOUT)
                )

            # 处理返回结果：可能是字典或字符串
            if isinstance(result, str):
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

        except asyncio.TimeoutError as e:
            raise FetchError.Timeout(f"抓取 {url} 超时：{e}")
        except TimeoutError as e:
            raise FetchError.Timeout(f"抓取 {url} 超时：{e}")
        except Exception as e:
            # 判断是否为连接错误
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["connection", "connect", "network", "refused"]):
                raise FetchError.ConnectionFailed(f"抓取 {url} 连接失败：{e}")
            raise FetchError(f"抓取 {url} 失败：{e}")

    async def fetch_urls_batch(
        self,
        urls: List[str],
        max_length: int = 5000,
        retry_count: int = None,
    ) -> List[Dict[str, Any]]:
        """
        批量抓取 URL 列表（异步并发）

        Args:
            urls: URL 列表
            max_length: 最大返回内容长度（tokens），默认 5000
            retry_count: 失败重试次数，None 使用配置默认值

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
        if retry_count is None:
            retry_count = self.config.RETRY_COUNT

        logger.info(f"[fetch] 开始批量抓取 {len(urls)} 个 URL，并发数：{self.config.FETCH_CONCURRENT_LIMIT}")

        async def fetch_with_retry(url: str) -> Dict[str, Any]:
            """带重试的单 URL 抓取"""
            last_error = None

            for attempt in range(retry_count + 1):
                try:
                    logger.debug(f"[fetch] 抓取 {url} (尝试 {attempt + 1}/{retry_count + 1})")
                    result = await self.fetch_url(url, max_length=max_length)
                    result["retry_count"] = attempt
                    return result
                except FetchError as e:
                    last_error = str(e)
                    logger.warning(f"[fetch] 抓取 {url} 失败 (尝试 {attempt + 1}/{retry_count + 1}): {e}")
                    if attempt < retry_count:
                        await asyncio.sleep(1.0)  # 重试间隔
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"[fetch] 抓取 {url} 发生未知错误 (尝试 {attempt + 1}/{retry_count + 1}): {e}")

            # 所有重试失败
            return {
                "url": url,
                "markdown": "",
                "title": "",
                "status": "failed",
                "error": last_error,
                "retry_count": retry_count,
            }

        # 并发执行所有抓取任务
        tasks = [fetch_with_retry(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        final_results = []
        for i, result in enumerate(results):
            url = urls[i]
            if isinstance(result, Exception):
                final_results.append({
                    "url": url,
                    "markdown": "",
                    "title": "",
                    "status": "failed",
                    "error": str(result),
                    "retry_count": retry_count,
                })
            else:
                final_results.append(result)

        # 统计
        success_count = sum(1 for r in final_results if r.get("status") == "success")
        logger.info(f"[fetch] 批量抓取完成，成功 {success_count}/{len(urls)}")

        # 请求间隔防限流
        if self.config.MCP_REQUEST_INTERVAL > 0 and urls:
            await asyncio.sleep(self.config.MCP_REQUEST_INTERVAL)

        return final_results

    async def fetch_single_with_retry(
        self,
        url: str,
        max_length: int = 5000,
        retry_count: int = None,
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
        if retry_count is None:
            retry_count = self.config.RETRY_COUNT

        for attempt in range(retry_count + 1):
            try:
                logger.info(f"[fetch] 抓取 {url} (尝试 {attempt + 1}/{retry_count + 1})")
                result = await self.fetch_url(url, max_length=max_length)
                result["retry_count"] = attempt
                if result.get("status") == "success":
                    return result
            except FetchError as e:
                logger.warning(f"[fetch] 抓取 {url} 失败 (尝试 {attempt + 1}/{retry_count + 1}): {e}")
            except Exception as e:
                logger.warning(f"[fetch] 抓取 {url} 发生未知错误 (尝试 {attempt + 1}/{retry_count + 1}): {e}")

        return None

    async def health_check(self) -> bool:
        """
        健康检测：检查云端 Fetch 服务是否可用

        通过调用 fetch 工具抓取多个测试 URL 来验证服务连通性。

        Returns:
            True 表示服务正常，False 表示服务不可用
        """
        # 多个测试域名
        test_urls = [
            "https://xiaolinnote.com/",
            "https://www.cnblogs.com",
        ]

        success_count = 0

        for test_url in test_urls:
            try:
                logger.info(f"[fetch] Health check: testing connectivity to {test_url}")
                result = await asyncio.wait_for(
                    self.fetch_url(test_url, max_length=100),
                    timeout=30  # 健康检测独立超时
                )

                if result.get("status") == "success" and result.get("markdown"):
                    success_count += 1
                    logger.info(f"[fetch] Health check: {test_url} 成功")
                else:
                    logger.warning(f"[fetch] Health check: {test_url} 返回无效响应：{result}")

            except asyncio.TimeoutError:
                logger.warning(f"[fetch] Health check: {test_url} 超时")
            except FetchError as e:
                logger.warning(f"[fetch] Health check: {test_url} 失败：{e}")
            except Exception as e:
                logger.warning(f"[fetch] Health check: {test_url} 未知错误：{e}")

        # 至少一个成功即认为健康
        is_healthy = success_count > 0
        if is_healthy:
            logger.info(f"[fetch] Health check: service is healthy ({success_count}/{len(test_urls)} 成功)")
        else:
            logger.error("[fetch] Health check: service is unhealthy (0 成功)")

        return is_healthy
