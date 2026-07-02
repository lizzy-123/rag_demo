"""
任务调度模块 - 基础模块

包含：
1. URLManager - 历史抓取 URL 持久化存储与去重
2. RawMarkdownManager - 原始 Markdown 文件存储与目录管理
3. ConfigReader - 配置读取器（黑名单域名、搜索关键词）
4. CrawlPipeline - 采集流水线（单次手动采集流程）
5. ProcessedResultManager - 处理结果文件管理器

使用示例:
    from ai_knowledge_crawler_mcp.crawl_task import (
        URLManager,
        RawMarkdownManager,
        ConfigReader,
        CrawlPipeline,
        ProcessedResultManager,
    )
    from ai_knowledge_crawler_mcp.config import CrawlerConfig

    config = CrawlerConfig()
    url_manager = URLManager(storage_path=config.PROJECT_ROOT + "/crawl_task_data/crawled_urls.json")
    file_manager = RawMarkdownManager(base_path=config.RAW_SOURCE_MD_PATH)
    config_reader = ConfigReader(config)

    # 读取关键词
    keywords = config_reader.get_search_keywords()

    # 过滤黑名单 URL
    urls = ["https://example.com/a", "https://ad.example.com/b"]
    filtered_urls = config_reader.filter_blacklisted_urls(urls)

    # 过滤已抓取 URL
    new_urls = url_manager.filter_new_urls(filtered_urls)

    # 保存原始 Markdown
    file_manager.save_raw_markdown(
        url="https://example.com/a",
        markdown_content="# Content",
        title="Article Title",
        category="RAG"
    )

    # 记录已抓取 URL
    url_manager.add_url_record(url="https://example.com/a", category="RAG", status="success")

    # 运行采集流水线
    # pipeline = CrawlPipeline(config)
    # await pipeline.run(category="all", days=30)
"""

from .url_manager import URLManager
from .file_manager import RawMarkdownManager
from .config_reader import ConfigReader
from .crawl_pipeline import CrawlPipeline
from .processed_result_manager import ProcessedResultManager

__all__ = [
    "URLManager",
    "RawMarkdownManager",
    "ConfigReader",
    "CrawlPipeline",
    "ProcessedResultManager",
]
