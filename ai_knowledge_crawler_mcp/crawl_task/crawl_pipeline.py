"""
知识采集流水线 - 单次手动采集流程

流程：
1. ConfigReader 读取分领域搜索关键词、黑名单
2. BingSearchAdapter 发起搜索
3. URLManager 过滤已抓取链接 + 黑名单域名
4. FetchAdapter 批量获取网页 Markdown 原文
5. RawMarkdownManager 按日期 + 分类写入 raw_source_md
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from ai_knowledge_crawler_mcp.crawl_task import (
    ConfigReader,
    RawMarkdownManager,
    URLManager,
)
from ai_knowledge_crawler_mcp.mcp_client_adapter import BingSearchAdapter, FetchAdapter
from ai_knowledge_crawler_mcp.utils import init_logger
from ai_knowledge_crawler_mcp.utils.exceptions import (
    CrawlPipelineError,
    BingSearchError,
    FetchError,
)

logger = logging.getLogger(__name__)


class FailedUrlPool:
    """失败 URL 池 - 持久化存储失败的 URL 供后续重试"""

    def __init__(self, storage_path: str):
        """
        初始化失败 URL 池

        Args:
            storage_path: 存储文件路径（JSON 格式）
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._failed_data: dict = self._load_data()

    def _load_data(self) -> dict:
        """加载失败 URL 数据"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载失败 URL 池失败：{e}，创建新文件")
        return {"urls": [], "stats": {"total": 0}}

    def _save_data(self):
        """保存失败 URL 数据"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._failed_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存失败 URL 池失败：{e}")

    def add_failed_url(self, url: str, category: str, error: str):
        """添加失败 URL"""
        record = {
            "url": url,
            "category": category,
            "error": error,
            "failed_date": datetime.now().strftime("%Y-%m-%d"),
        }
        self._failed_data["urls"].append(record)
        self._failed_data["stats"]["total"] += 1
        self._save_data()

    def remove_url(self, url: str) -> bool:
        """移除 URL（重试成功后）"""
        original_len = len(self._failed_data["urls"])
        self._failed_data["urls"] = [r for r in self._failed_data["urls"] if r["url"] != url]
        new_len = len(self._failed_data["urls"])
        if new_len < original_len:
            self._failed_data["stats"]["total"] -= 1
            self._save_data()
            return True
        return False

    def get_all_failed_urls(self) -> list:
        """获取所有失败 URL 记录"""
        return self._failed_data["urls"].copy()

    def get_failed_url_set(self) -> set:
        """获取失败 URL 集合"""
        return {r["url"] for r in self._failed_data["urls"]}

    def clear_all(self):
        """清空所有失败记录"""
        self._failed_data = {"urls": [], "stats": {"total": 0}}
        self._save_data()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self._failed_data["stats"]


class CrawlPipeline:
    """知识采集流水线 - 单次手动采集流程"""

    def __init__(self, config: CrawlerConfig):
        """
        初始化采集流水线

        Args:
            config: 全局配置对象
        """
        self.config = config
        self._init_components()
        self._stats = {
            "search_count": 0,
            "filtered_count": 0,
            "fetch_success": 0,
            "fetch_failed": 0,
            "saved_count": 0,
        }

    def _init_components(self) -> None:
        """初始化各组件"""
        # 配置读取器
        self.config_reader = ConfigReader(self.config)

        # URL 管理器 - 持久化路径
        self.url_manager = URLManager(
            storage_path=self.config.PROJECT_ROOT / "crawl_task_data" / "crawled_urls.json"
        )

        # 文件管理器 - 原始 Markdown 存储
        self.file_manager = RawMarkdownManager(self.config.RAW_SOURCE_MD_PATH)

        # 失败 URL 池
        self.failed_url_pool = FailedUrlPool(str(self.config.FAILED_URLS_POOL_PATH))

        # MCP 适配器
        # BingSearchAdapter 使用云端 streamable_http 服务
        self.bing_adapter = BingSearchAdapter(config=self.config)
        # FetchAdapter 使用云端 streamable_http 服务
        self.fetch_adapter = FetchAdapter(config=self.config)

        logger.info("采集流水线组件初始化完成")

    async def run(
        self,
        category: Optional[str] = None,
        days: int = 30,
    ) -> dict:
        """
        执行采集流水线主流程

        Args:
            category: 采集分类，可选值：'chinese'(中文), 'english'(英文), 'all'(全部)
                     默认 'all'
            days: 搜索最近 N 天的内容，默认 30 天

        Returns:
            统计信息字典
        """
        start_time = datetime.now()
        logger.info(f"开始执行采集流水线，category={category}, days={days}")

        # 阶段 1: 搜索
        search_results = await self._search_phase(category, days)
        if not search_results:
            logger.warning("搜索阶段未获取到任何结果，流程结束")
            return self._stats

        # 阶段 2: 过滤
        valid_urls = await self._filter_phase(search_results)
        if not valid_urls:
            logger.warning("过滤后无有效 URL，流程结束")
            return self._stats

        # 阶段 3: 抓取
        fetch_results = await self._fetch_phase(valid_urls)
        if not fetch_results:
            logger.warning("抓取阶段未获取到任何内容，流程结束")
            return self._stats

        # 阶段 4: 保存
        await self._save_phase(fetch_results)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"采集流水线执行完成，耗时 {elapsed:.2f} 秒")

        self._print_stats()
        return self._stats

    async def _search_phase(
        self,
        category: Optional[str],
        days: int,
    ) -> list[dict]:
        """
        搜索阶段：根据分类获取关键词并搜索

        Args:
            category: 分类标识
            days: 搜索最近 N 天

        Returns:
            搜索结果列表（每个结果绑定 category 字段）
        """
        # 健康检测：检查云端 Bing 搜索服务是否可用
        logger.info("搜索阶段：执行 Bing 云端服务健康检测")
        if not await self.bing_adapter.health_check():
            raise CrawlPipelineError.HealthCheckFailed(
                "Bing 云端服务不可用或已过期！请检查云端 MCP 服务地址是否有效。"
            )

        # 根据分类选择关键词
        if category == "chinese":
            keywords = self.config_reader.get_search_keywords()
            category_name = "chinese"
        elif category == "english":
            keywords = self.config_reader.get_english_keywords()
            category_name = "english"
        else:
            # 默认全部，合并中文和英文关键词
            keywords = self.config_reader.get_all_keywords()
            category_name = "all"

        if not keywords:
            logger.warning(f"未找到 {category_name} 分类的关键词")
            return []

        logger.info(f"搜索阶段：使用 {len(keywords)} 个关键词 - {keywords}")

        # 获取本地已爬 URL（用于 MCP 提前过滤）
        crawled_urls = list(self.url_manager.get_all_crawled_urls())
        logger.info(f"搜索阶段：本地已爬 URL {len(crawled_urls)} 条，将传入 MCP 排除")

        # 调用必应搜索适配器
        try:
            search_result = await self.bing_adapter.search_keywords(
                keywords=keywords,
                days=days,
                exclude_urls=crawled_urls,  # 传入已爬 URL 提前过滤
                count=2,
                max_total_results=10,
            )

            results = search_result.get("results", [])

            # 为每个结果绑定 category 分类
            for item in results:
                item["category"] = category_name

            self._stats["search_count"] = len(results)
            logger.info(f"搜索阶段完成，获取到 {len(results)} 条结果")

            return results

        except BingSearchError as e:
            logger.error(f"搜索阶段发生 BingSearchError: {e}")
            raise CrawlPipelineError.SearchPhaseError(f"搜索失败：{e}")
        except Exception as e:
            logger.error(f"搜索阶段发生未知错误：{e}")
            raise CrawlPipelineError.SearchPhaseError(f"搜索失败：{e}")

    async def _filter_phase(self, search_results: list[dict]) -> list[dict]:
        """
        过滤阶段：过滤黑名单域名和已抓取 URL

        Args:
            search_results: 搜索结果列表

        Returns:
            过滤后的有效 URL 列表
        """
        # 提取 URL 列表
        urls = [item["url"] for item in search_results if "url" in item]
        total_urls = len(urls)
        logger.info(f"过滤阶段：待过滤 {total_urls} 个 URL")

        # 过滤黑名单域名
        filtered_urls = self.config_reader.filter_blacklisted_urls(urls)
        blacklist_removed = total_urls - len(filtered_urls)
        if blacklist_removed > 0:
            logger.info(f"黑名单过滤：移除 {blacklist_removed} 个黑名单域名 URL")

        # 过滤已抓取 URL
        new_urls = self.url_manager.filter_new_urls(filtered_urls)
        duplicate_removed = len(filtered_urls) - len(new_urls)
        if duplicate_removed > 0:
            logger.info(f"去重过滤：移除 {duplicate_removed} 个已抓取 URL")

        self._stats["filtered_count"] = total_urls - len(new_urls)

        # 构建返回结果（保留原始搜索结果信息）
        url_set = set(new_urls)
        valid_results = [item for item in search_results if item.get("url") in url_set]

        logger.info(f"过滤阶段完成，剩余 {len(valid_results)} 个有效 URL")
        return valid_results

    async def _fetch_phase(self, valid_urls: list[dict]) -> list[dict]:
        """
        抓取阶段：批量获取网页 Markdown 内容

        Args:
            valid_urls: 有效 URL 列表（包含 title, url, published_date, category 等信息）

        Returns:
            抓取结果列表
        """
        # 健康检测：检查云端 Fetch 服务是否可用
        logger.info("抓取阶段：执行 Fetch 云端服务健康检测")
        if not await self.fetch_adapter.health_check():
            raise CrawlPipelineError.HealthCheckFailed(
                "Fetch 云端服务不可用或已过期！请检查云端 MCP 服务地址是否有效。"
            )

        urls = [item["url"] for item in valid_urls]
        logger.info(f"抓取阶段：开始抓取 {len(urls)} 个网页")

        try:
            # 批量抓取（异步并发）
            fetch_results = await self.fetch_adapter.fetch_urls_batch(
                urls=urls,
                max_length=5000,
            )

            # 统计成功/失败
            success_count = sum(1 for r in fetch_results if r.get("status") == "success")
            failed_count = len(fetch_results) - success_count

            self._stats["fetch_success"] = success_count
            self._stats["fetch_failed"] = failed_count

            logger.info(
                f"抓取阶段完成，成功 {success_count}, 失败 {failed_count}"
            )

            # 只返回成功的结果
            successful_results = [r for r in fetch_results if r.get("status") == "success"]

            # 关联原始搜索结果信息（title, published_date, category 等）
            url_to_result = {item["url"]: item for item in valid_urls}
            for fetch_result in successful_results:
                url = fetch_result.get("url")
                if url in url_to_result:
                    original = url_to_result[url]
                    fetch_result["original_title"] = original.get("title", "")
                    fetch_result["published_date"] = original.get("published_date", "")
                    # category 已在搜索阶段绑定
                    if "category" not in fetch_result:
                        fetch_result["category"] = original.get("category", "all")

            # 处理失败结果：加入失败池
            failed_results = [r for r in fetch_results if r.get("status") == "failed"]
            for failed in failed_results:
                url = failed.get("url")
                # 从原始结果中获取 category
                category = url_to_result.get(url, {}).get("category", "unknown")
                error = failed.get("error", "Unknown error")
                self.failed_url_pool.add_failed_url(url, category, error)
                logger.debug(f"抓取阶段：URL {url} 加入失败池，错误：{error}")

            return successful_results

        except FetchError as e:
            logger.error(f"抓取阶段发生 FetchError: {e}")
            raise CrawlPipelineError.FetchPhaseError(f"抓取失败：{e}")
        except Exception as e:
            logger.error(f"抓取阶段发生未知错误：{e}")
            raise CrawlPipelineError.FetchPhaseError(f"抓取失败：{e}")

    async def _save_phase(self, fetch_results: list[dict]) -> None:
        """
        保存阶段：按日期 + 分类保存 Markdown 文件

        Args:
            fetch_results: 抓取结果列表
        """
        if not fetch_results:
            logger.warning("保存阶段：无数据需要保存")
            return

        date_str = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"保存阶段：开始保存 {len(fetch_results)} 个文件到 {date_str}")

        saved_count = 0
        for result in fetch_results:
            try:
                url = result.get("url")
                markdown = result.get("markdown", "")
                title = result.get("title", result.get("original_title", "Untitled"))
                category = result.get("category", "all")

                if not markdown:
                    logger.warning(f"URL {url} 无 Markdown 内容，跳过")
                    continue

                # 保存到文件（按分类分目录）
                self.file_manager.save_raw_markdown(
                    url=url,
                    markdown_content=markdown,
                    title=title,
                    category=category,  # 按 category 分目录
                    date_str=date_str,
                )

                # 记录到 URL 管理器
                self.url_manager.add_url_record(
                    url=url,
                    category=category,
                    status="success",
                )

                # 从失败池中移除（如果存在）
                self.failed_url_pool.remove_url(url)

                saved_count += 1

            except Exception as e:
                logger.error(f"保存文件失败 {result.get('url')}: {e}")
                # 记录失败
                self.url_manager.add_url_record(
                    url=result.get("url"),
                    category=result.get("category", "all"),
                    status="failed",
                )

        self._stats["saved_count"] = saved_count
        logger.info(f"保存阶段完成，成功保存 {saved_count} 个文件")

    def _print_stats(self) -> None:
        """打印统计信息"""
        print("\n" + "=" * 50)
        print("采集流水线执行统计")
        print("=" * 50)
        print(f"搜索获取：{self._stats['search_count']} 条")
        print(f"过滤移除：{self._stats['filtered_count']} 条")
        print(f"抓取成功：{self._stats['fetch_success']} 条")
        print(f"抓取失败：{self._stats['fetch_failed']} 条")
        print(f"文件保存：{self._stats['saved_count']} 个")
        print("=" * 50 + "\n")


async def main():
    """主入口函数"""
    # 初始化配置
    config = CrawlerConfig()

    # 使用封装日志工具初始化
    logger = init_logger(
        logs_path=config.LOGS_PATH,
        log_level=config.LOG_LEVEL,
        log_name="crawl_pipeline",
    )

    logger.info("知识采集流水线启动")

    # 创建流水线并执行
    pipeline = CrawlPipeline(config)

    # 执行采集（默认全部分类，最近 30 天）
    stats = await pipeline.run(category="all", days=30)

    return stats


if __name__ == "__main__":
    asyncio.run(main())
