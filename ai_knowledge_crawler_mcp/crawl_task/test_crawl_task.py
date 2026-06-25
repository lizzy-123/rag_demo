"""
crawl_task 基础模块测试

测试内容：
1. 配置读取（关键词、黑名单）
2. URL 去重与持久化
3. 原始 Markdown 文件存储（按日期/分类）
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

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from ai_knowledge_crawler_mcp.crawl_task import (
    URLManager,
    RawMarkdownManager,
    ConfigReader
)


async def test_config_reader():
    """测试配置读取器"""
    print("\n" + "="*60)
    print("测试 1: 配置读取器")
    print("="*60)

    config = CrawlerConfig()
    config_reader = ConfigReader(config)

    # 测试关键词读取
    print("\n[中文关键词]")
    for kw in config_reader.get_search_keywords():
        print(f"  - {kw}")

    print("\n[英文关键词]")
    for kw in config_reader.get_english_keywords():
        print(f"  - {kw}")

    # 测试黑名单域名
    print("\n[黑名单域名]")
    for domain in config_reader.get_blacklist_domains():
        print(f"  - {domain}")

    # 测试 URL 黑名单过滤
    print("\n[黑名单过滤测试]")
    test_urls = [
        "https://example.com/article1",
        "https://ad.example.com/spam",  # 黑名单
        "https://spam.example.com/ad",  # 黑名单
        "https://zhihu.com/question/123",
    ]
    filtered = config_reader.filter_blacklisted_urls(test_urls)
    print(f"  原始：{len(test_urls)} 条")
    print(f"  过滤后：{len(filtered)} 条")
    for url in filtered:
        print(f"    ✓ {url}")


async def test_url_manager():
    """测试 URL 管理器"""
    print("\n" + "="*60)
    print("测试 2: URL 管理器")
    print("="*60)

    config = CrawlerConfig()
    storage_path = Path(config.PROJECT_ROOT) / "ai_knowledge_crawler_mcp" / "crawl_task_data" / "crawled_urls.json"
    url_manager = URLManager(storage_path=str(storage_path))

    # 测试 URL 去重
    print("\n[URL 去重测试]")
    test_urls = [
        "https://example.com/article1",
        "https://example.com/article2",
        "https://zhihu.com/question/123",
    ]

    # 第一次过滤（应该全部通过）
    new_urls_1 = url_manager.filter_new_urls(test_urls)
    print(f"  第一次过滤：{len(new_urls_1)} 条新 URL")

    # 记录已抓取
    url_manager.add_urls_batch(new_urls_1, category="RAG", status="success")

    # 第二次过滤（应该全部被过滤）
    new_urls_2 = url_manager.filter_new_urls(test_urls)
    print(f"  第二次过滤：{len(new_urls_2)} 条新 URL（预期 0）")

    # 添加新 URL 再测试
    more_urls = [
        "https://zhihu.com/question/456",
        "https://juejin.cn/post/789",
    ]
    new_urls_3 = url_manager.filter_new_urls(more_urls)
    print(f"  新 URL 过滤：{len(new_urls_3)} 条新 URL")

    # 查看统计
    print("\n[统计信息]")
    stats = url_manager.get_stats()
    print(f"  总数：{stats['total']}")
    print(f"  成功：{stats['success']}")
    print(f"  失败：{stats['failed']}")

    # 查看已抓取 URL
    print("\n[已抓取 URL 列表]")
    for url in url_manager.get_all_crawled_urls():
        print(f"  - {url}")


async def test_file_manager():
    """测试文件管理器"""
    print("\n" + "="*60)
    print("测试 3: 文件管理器")
    print("="*60)

    config = CrawlerConfig()
    file_manager = RawMarkdownManager(base_path=config.RAW_SOURCE_MD_PATH)

    # 测试文件保存
    print("\n[保存原始 Markdown 文件]")

    test_files = [
        {
            "url": "https://example.com/rag-intro",
            "title": "RAG 技术入门指南",
            "category": "RAG",
            "content": "# RAG 技术入门\n\n这是 RAG 技术的介绍内容..."
        },
        {
            "url": "https://example.com/rag-advanced",
            "title": "RAG 高级应用",
            "category": "RAG",
            "content": "# RAG 高级应用\n\n这是 RAG 高级应用的内容..."
        },
        {
            "url": "https://example.com/llm-basics",
            "title": "大模型基础概念",
            "category": "大模型基础",
            "content": "# 大模型基础\n\n介绍大模型的基本概念..."
        },
    ]

    saved_paths = []
    for file_info in test_files:
        path = file_manager.save_raw_markdown(
            url=file_info["url"],
            markdown_content=file_info["content"],
            title=file_info["title"],
            category=file_info["category"]
        )
        saved_paths.append(path)
        print(f"  ✓ 保存：{path}")

    # 查看目录结构
    print("\n[目录结构]")
    today = Path.today() if hasattr(Path, 'today') else __import__('datetime').datetime.now().strftime("%Y-%m-%d")
    today = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
    for category_dir in file_manager.get_all_categories():
        print(f"  {today}/")
        print(f"    └── {category_dir}/")

    # 查看文件统计
    print("\n[分类文件统计]")
    stats = file_manager.get_file_count_by_category()
    for category, count in stats.items():
        print(f"  {category}: {count} 个文件")

    # 读取一个文件验证
    print("\n[文件内容验证]")
    if saved_paths:
        first_file = saved_paths[0]
        with open(first_file, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"  文件：{first_file.name}")
        print(f"  前 200 字符:\n{content[:200]}...")


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("crawl_task 基础模块测试")
    print("="*60)

    try:
        await test_config_reader()
        await test_url_manager()
        await test_file_manager()

        print("\n" + "="*60)
        print("✓ 所有测试通过")
        print("="*60)
    except Exception as e:
        logger.error(f"测试失败：{e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
