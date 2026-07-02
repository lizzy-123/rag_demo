"""本地文档处理器自测脚本

测试清洗、分片、去重、分类全流程
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根路径
#project_root = Path(__file__).resolve().parent.parent.parent
#sys.path.insert(0, str(project_root))

from ..utils.logger import get_logger
from ai_knowledge_crawler_mcp.config import CrawlerConfig
config = CrawlerConfig()

get_logger(logs_path=config.LOGS_PATH)  # 这将初始化日志配置
from ai_knowledge_crawler_mcp.document_processor import (
    TextCleaner,
    TextChunkSplitter,
    TextDeduplicator,
    TextClassifier,
    DocumentPipeline,
)


def test_text_cleaner():
    """测试文本清洗模块"""
    print("\n" + "=" * 60)
    print("测试：文本清洗模块")
    print("=" * 60)

    cleaner = TextCleaner()

    # 测试用例 1：含 HTML 标签
    raw_text = """
    <div class="content">
        <h1>Python 入门教程</h1>
        <p>这是一篇关于 Python 的教程文章。</p>
        <script>console.log("ad");</script>
    </div>
    <footer>© 2024 Copyright</footer>
    """

    result = cleaner.process(raw_text, "https://example.com/tutorial")
    print(f"原始长度：{result['original_length']}")
    print(f"清洗后长度：{result['cleaned_length']}")
    print(f"清洗后文本:\n{result['cleaned_text']}")

    # 测试用例 2：空文本
    result_empty = cleaner.process("", "https://example.com")
    print(f"\n空文本测试：清洗后长度 = {result_empty['cleaned_length']}")

    print("✅ 文本清洗模块测试完成")
    return True


def test_text_chunk_splitter():
    """测试文本分片模块"""
    print("\n" + "=" * 60)
    print("测试：文本分片模块")
    print("=" * 60)

    splitter = TextChunkSplitter(chunk_size=200, chunk_overlap=50)

    # 测试用例 1：含标题的文本
    text = """
# Python 入门

Python 是一种高级编程语言，由 Guido van Rossum 于 1989 年创建。

## 特点

Python 以其简洁的语法和易读性而闻名。它支持多种编程范式，包括过程式、面向对象和函数式编程。

## 应用场景

Python 广泛应用于 Web 开发、数据分析、人工智能、科学计算等领域。

## 安装指南

首先访问 Python 官网下载最新版本，然后运行安装程序。
"""

    result = splitter.process(text)
    print(f"文本长度：{result['total_length']}")
    print(f"分片数量：{result['chunk_count']}")

    for i, chunk in enumerate(result['chunks']):
        print(f"\n--- 分片 {i+1} ---")
        print(f"类型：{chunk['chunk_type']}")
        print(f"范围：{chunk['start_index']} - {chunk['end_index']}")
        print(f"内容预览：{chunk['text'][:100]}...")

    # 测试用例 2：短文本（小于分片阈值）
    short_text = "短文本测试"
    result_short = splitter.process(short_text)
    print(f"\n短文本测试：分片数量 = {result_short['chunk_count']}")

    # 测试用例 3：参数越界
    try:
        invalid_splitter = TextChunkSplitter(chunk_size=100, chunk_overlap=150)
        print("❌ 参数校验失败：应抛出异常")
    except Exception as e:
        print(f"✅ 参数校验正常：{e}")

    print("\n✅ 文本分片模块测试完成")
    return True


def test_text_deduplicator():
    """测试分片去重模块"""
    print("\n" + "=" * 60)
    print("测试：分片去重模块")
    print("=" * 60)

    deduplicator = TextDeduplicator(use_semantic=True, similarity_threshold=0.85)
    print(f"去重模式：{'语义' if deduplicator._semantic_available else '哈希'}")

    # 测试用例 1：含重复分片
    chunks = [
        {"text": "Python 是一种高级编程语言", "start_index": 0, "end_index": 13},
        {"text": "Python 是一种高级编程语言", "start_index": 100, "end_index": 113},  # 重复
        {"text": "Java 是一种面向对象的编程语言", "start_index": 200, "end_index": 220},
        {"text": "Java 是一种面向对象的编程语言", "start_index": 300, "end_index": 320},  # 重复
        {"text": "Go 语言适合并发编程", "start_index": 400, "end_index": 415},
    ]

    result = deduplicator.process(chunks)
    print(f"原始分片数：{len(chunks)}")
    print(f"去重后分片数：{len(result['chunks'])}")
    print(f"移除数量：{result['removed_count']}")
    print(f"重复对：{result['duplicate_pairs']}")
    print(f"去重模式：{result['mode']}")

    # 测试用例 2：空列表
    result_empty = deduplicator.process([])
    print(f"\n空列表测试：去重后分片数 = {len(result_empty['chunks'])}")

    print("\n✅ 分片去重模块测试完成")
    return True


def test_text_classifier():
    """测试文档分类模块"""
    print("\n" + "=" * 60)
    print("测试：文档分类模块")
    print("=" * 60)

    classifier = TextClassifier()

    # 测试用例 1：Python 相关
    text_python = """
    Python Django 框架教程

    Django 是一个高级 Python Web 框架，鼓励快速开发和干净、实用的设计。
    它由开源社区维护，拥有强大的 ORM 和 REST API 支持。
    """

    result = classifier.process(text_python, "Python Django 框架教程")
    print(f"文本：Python Django 框架教程")
    print(f"主分类：{result['primary_category']}")
    print(f"标签：{result['tags']}")
    print(f"置信度：{result['confidence']}")

    # 测试用例 2：数据库相关
    text_db = """
    MySQL 和 PostgreSQL 数据库对比

    MySQL 和 PostgreSQL 都是流行的关系型数据库，Redis 作为缓存也很常用。
    """

    result_db = classifier.process(text_db, "数据库对比")
    print(f"\n文本：数据库对比")
    print(f"主分类：{result_db['primary_category']}")
    print(f"标签：{result_db['tags']}")
    print(f"置信度：{result_db['confidence']}")

    # 测试用例 3：短文本
    result_short = classifier.process("短", "标题")
    print(f"\n短文本测试：主分类 = {result_short['primary_category']}, 置信度 = {result_short['confidence']}")

    print("\n✅ 文档分类模块测试完成")
    return True


def test_document_pipeline():
    """测试完整流水线"""
    print("\n" + "=" * 60)
    print("测试：完整文档处理流水线")
    print("=" * 60)

    pipeline = DocumentPipeline(
        chunk_size=300,
        chunk_overlap=50,
        use_semantic_dedup=True,
        dedup_threshold=0.85,
    )

    # 测试用例 1：单文档处理
    markdown = """
    # LangChain RAG 教程

    LangChain 是一个用于构建大语言链应用的框架。

    ## RAG 概述

    RAG（Retrieval-Augmented Generation）是一种结合信息检索和文本生成的技术。

    ## 实现步骤

    1. 文档加载和分片
    2. 向量化存储（使用 FAISS 或 Chroma）
    3. 相似度检索
    4. 上下文组装
    5. LLM 生成回答

    ## 最佳实践

    - 选择合适的 chunk_size（推荐 500-1000）
    - 使用高质量的 embedding 模型
    - 实现检索结果重排序
    """

    results = pipeline.process(
       {
        "markdown":markdown,
        "source_url":"https://example.com/langchain-rag-tutorial",
        "tech_category":None,
       }
    )
    result = results[0]

    print(f"处理状态：{result['status']}")

    if result['status'] == 'success':
        print(f"清洗后长度：{len(result['cleaned_markdown'])}")
        print(f"分片数量：{len(result['chunks'])}")
        print(f"元数据：")
        print(f"  - 标题：{result['metadata']['title']}")
        print(f"  - 主分类：{result['metadata']['primary_category']}")
        print(f"  - 标签：{result['metadata']['tech_tags']}")
        print(f"  - 词数：{result['metadata']['word_count']}")
        print(f"去重信息：")
        print(f"  - 全文哈希：{result['dedup_info']['full_text_hash'][:16]}...")
        print(f"  - 移除重复：{result['dedup_info']['removed_duplicate_chunks']}")

        # 打印分片预览
        print(f"\n分片预览:")
        for i, chunk in enumerate(result['chunks'][:3]):
            print(f"  分片 {i+1}: {chunk['text'][:80]}...")

    else:
        print(f"错误：{result.get('error')}")

    # 测试用例 2：批量处理
    print("\n--- 批量处理测试 ---")
    documents = [
        {
            "markdown": "# Python 教程\nPython 是一种编程语言，使用 Python 开发非常高效。",
            "source_url": "https://example.com/python",
            "tech_category": "编程语言",
        },
        {
            "markdown": "# Docker 指南\nDocker 容器化技术，使用 Docker 部署应用。",
            "source_url": "https://example.com/docker",
            "tech_category": "运维",
        },
        {
            "markdown": "",  # 空文档测试
            "source_url": "https://example.com/empty",
        },
    ]

    batch_results = pipeline.process(documents)

    success_count = sum(1 for r in batch_results if r.get('status') == 'success')
    failed_count = len(batch_results) - success_count

    print(f"批量处理结果：成功 {success_count}, 失败 {failed_count}")

    for result in batch_results:
        idx = result.get('document_index', '?')
        status = result.get('status', 'unknown')
        url = result.get('source_url', 'unknown')
        print(f"  文档 {idx}: {status} - {url}")

    print("\n✅ 完整流水线测试完成")
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("本地文档处理器自测脚本")
    print("=" * 60)




    tests = [
        ("文本清洗", test_text_cleaner),
        ("文本分片", test_text_chunk_splitter),
        ("分片去重", test_text_deduplicator),
        ("文档分类", test_text_classifier),
        ("完整流水线", test_document_pipeline),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} 测试失败：{e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"测试汇总：通过 {passed}, 失败 {failed}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
