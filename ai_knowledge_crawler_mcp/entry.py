"""
AI 知识库 MCP 采集预处理模块 - 统一入口

支持手动单次执行 / 后台定时循环执行。

对外提供三类调用函数：
1. run_full_pipeline() - 完整全链路（采集 + 预处理）
2. run_only_crawl() - 仅执行采集（搜索 + 抓取）
3. run_only_process() - 仅执行预处理（读取存量 MD 文件）
4. load_rag_documents() - RAG 专用：读取分片转 LangChain Document
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# 尝试导入 langchain Document（可选依赖）
try:
    from langchain_core.documents import Document as LangChainDocument

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    LangChainDocument = None  # type: ignore
    print(
        "[提示] langchain-core 未安装，load_rag_documents 功能不可用。"
        "运行：pip install langchain-core"
    )

from ai_knowledge_crawler_mcp.config import CrawlerConfig
from ai_knowledge_crawler_mcp.utils.logger import get_logger, get_child_logger
from ai_knowledge_crawler_mcp.utils.exceptions import MCPBaseException
from ai_knowledge_crawler_mcp.crawl_task.crawl_pipeline import CrawlPipeline


# ========== 日志初始化 ==========
config = CrawlerConfig()
get_logger(logs_path=config.LOGS_PATH, log_level=config.LOG_LEVEL)
logger = get_child_logger("entry")


# ========== 自定义异常 ==========
class EntryError(MCPBaseException):
    """入口模块异常"""

    class DocumentLoadFailed(MCPBaseException):
        """文档加载失败"""
        pass

    class InvalidConfig(MCPBaseException):
        """配置无效"""
        pass


# ========== 对外统一入口函数 ==========


def run_full_pipeline(
    category: Optional[str] = "all",
    days: int = 30,
    use_local_processor: bool = True,
) -> Dict[str, Any]:
    """
    完整一键全链路：Bing 检索抓取网页 → raw_source_md 落地 → document_processor 本地清洗/分片/去重/分类 → processed_knowledge 归档

    Args:
        category: 采集分类，可选值：'chinese'(中文), 'english'(英文), 'all'(全部)
        days: 搜索最近 N 天的内容
        use_local_processor: 是否启用本地文档处理器（覆盖配置 USE_LOCAL_DOC_PROCESSOR）

    Returns:
        统计信息字典，包含 search_count, fetch_success, process_success 等

    Example:
        >>> stats = run_full_pipeline(category="all", days=30)
        >>> print(stats)
    """
    logger.info(
        f"[entry] 启动完整全链路 - category={category}, days={days}, "
        f"use_local_processor={use_local_processor}"
    )

    # 临时覆盖配置
    original_use_local = config.USE_LOCAL_DOC_PROCESSOR
    config.USE_LOCAL_DOC_PROCESSOR = use_local_processor

    try:
        pipeline = CrawlPipeline(config)
        stats = asyncio.run(pipeline.run(category=category, days=days))

        logger.info(f"[entry] 完整全链路执行完成 - {stats}")
        return stats

    except Exception as e:
        logger.error(f"[entry] 完整全链路执行失败：{e}")
        raise EntryError(f"完整全链路执行失败：{e}")

    finally:
        # 恢复原配置
        config.USE_LOCAL_DOC_PROCESSOR = original_use_local


def run_only_crawl(
    category: Optional[str] = "all",
    days: int = 30,
) -> Dict[str, Any]:
    """
    仅执行采集流程：搜索 + 抓取，仅落地原始 md 文件，跳过文档预处理环节

    Args:
        category: 采集分类
        days: 搜索最近 N 天的内容

    Returns:
        统计信息字典

    Example:
        >>> stats = run_only_crawl(category="chinese", days=7)
    """
    logger.info(f"[entry] 启动仅采集流程 - category={category}, days={days}")

    # 禁用本地处理器
    original_use_local = config.USE_LOCAL_DOC_PROCESSOR
    original_save_result = config.SAVE_PROCESSED_RESULT
    config.USE_LOCAL_DOC_PROCESSOR = False
    config.SAVE_PROCESSED_RESULT = False

    try:
        pipeline = CrawlPipeline(config)
        stats = asyncio.run(pipeline.run(category=category, days=days))

        logger.info(f"[entry] 仅采集流程执行完成 - {stats}")
        return stats

    except Exception as e:
        logger.error(f"[entry] 仅采集流程执行失败：{e}")
        raise EntryError(f"仅采集流程执行失败：{e}")

    finally:
        config.USE_LOCAL_DOC_PROCESSOR = original_use_local
        config.SAVE_PROCESSED_RESULT = original_save_result


async def run_only_process(
    date_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    仅执行预处理流程：读取 raw_source_md 存量文件，使用本地 document_processor 处理并归档成品数据

    Args:
        date_str: 日期字符串（YYYY-MM-DD），None 表示处理所有存量文件

    Returns:
        处理统计信息

    Example:
        >>> stats = asyncio.run(run_only_process(date_str="2026-07-01"))
    """
    from ai_knowledge_crawler_mcp.crawl_task import RawMarkdownManager
    from ai_knowledge_crawler_mcp.document_processor import DocumentPipeline

    logger.info(f"[entry] 启动仅预处理流程 - date_str={date_str}")

    # 初始化组件
    file_manager = RawMarkdownManager(config.RAW_SOURCE_MD_PATH)
    doc_pipeline = DocumentPipeline(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        use_semantic_dedup=config.USE_SEMANTIC_DEDUP,
        dedup_threshold=config.LOCAL_DEDUP_THRESHOLD,
    )

    # 读取存量 MD 文件
    md_files = file_manager.get_all_markdown_files(date_str=date_str)

    if not md_files:
        logger.warning("[entry] 未找到待处理的 MD 文件")
        return {"processed_count": 0, "success_count": 0, "failed_count": 0}

    logger.info(f"[entry] 找到 {len(md_files)} 个待处理 MD 文件")

    # 批量处理
    documents = []
    for md_file in md_files:
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 从文件 frontmatter 提取 metadata
            source_url = md_file.name  # 简单使用文件名
            category = "unknown"

            documents.append(
                {
                    "markdown": content,
                    "source_url": source_url,
                    "tech_category": category if category != "unknown" else None,
                }
            )
        except Exception as e:
            logger.warning(f"[entry] 读取 MD 文件失败 {md_file}: {e}")
            continue

    # 执行处理
    results = doc_pipeline.process_batch(documents)

    success_count = sum(1 for r in results if r.get("status") == "success")
    failed_count = len(results) - success_count

    stats = {
        "processed_count": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
    }

    logger.info(f"[entry] 仅预处理流程执行完成 - {stats}")
    return stats


# ========== RAG 专用工具函数 ==========


def load_rag_documents(
    rag_export_path: Optional[Path] = None,
    since_datetime: Optional[datetime] = None,
) -> List[Any]:
    """
    读取 rag_export 目录下所有分片 JSON 文件，转换为 LangChain Document 标准对象

    Args:
        rag_export_path: rag_export 目录路径，None 使用配置路径
        since_datetime: 只加载此时间之后修改的文件（增量加载）

    Returns:
        LangChain Document 列表，每个文档携带完整元数据：
        - page_content: 分片文本
        - metadata: {
            "source_url": str,
            "primary_category": str,
            "tech_tags": List[str],
            "chunk_start_index": int,
            "chunk_end_index": int,
            "crawl_time": str,
            "full_text_hash": str,
          }

    Raises:
        EntryError.DocumentLoadFailed: 目录不存在、文件损坏、JSON 解析失败

    Example:
        >>> docs = load_rag_documents()
        >>> for doc in docs:
        ...     print(doc.page_content[:100], doc.metadata["source_url"])
    """
    if not LANGCHAIN_AVAILABLE:
        logger.error(
            "[entry] langchain-core 未安装，无法使用 load_rag_documents 功能"
        )
        raise EntryError.DocumentLoadFailed(
            "langchain-core 未安装，请先运行：pip install langchain-core"
        )

    if rag_export_path is None:
        rag_export_path = config.RAG_EXPORT_PATH

    if not rag_export_path.exists():
        logger.warning(f"[entry] rag_export 目录不存在：{rag_export_path}")
        return []

    if not rag_export_path.is_dir():
        raise EntryError.DocumentLoadFailed(
            f"rag_export 路径不是目录：{rag_export_path}"
        )

    logger.info(f"[entry] 开始加载 RAG 分片 - 路径：{rag_export_path}")

    documents = []
    failed_count = 0

    # 遍历所有 JSON 文件
    json_files = list(rag_export_path.glob("*.json"))

    for json_file in json_files:
        try:
            # 时间过滤
            if since_datetime is not None:
                file_mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
                if file_mtime <= since_datetime:
                    continue

            # 读取 JSON
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 判断是单文档结果还是批次汇总
            if "chunks" in data:
                # 单文档结果
                docs = _convert_to_langchain_docs(data, json_file)
                documents.extend(docs)
            elif "documents" in data:
                # 批次汇总（不包含实际分片，跳过）
                logger.debug(f"[entry] 跳过批次汇总文件：{json_file.name}")
                continue
            else:
                logger.warning(f"[entry] 未知 JSON 格式：{json_file.name}")
                failed_count += 1
                continue

        except json.JSONDecodeError as e:
            logger.error(f"[entry] JSON 解析失败 {json_file}: {e}")
            failed_count += 1
            continue
        except Exception as e:
            logger.error(f"[entry] 加载文件失败 {json_file}: {e}")
            failed_count += 1
            continue

    if failed_count > 0:
        logger.warning(f"[entry] 加载完成，{failed_count} 个文件失败")

    logger.info(f"[entry] 成功加载 {len(documents)} 个 LangChain Document")

    return documents


def _convert_to_langchain_docs(
    data: Dict[str, Any], source_file: Path
) -> List[LangChainDocument]:
    """
    将单文档处理结果转换为 LangChain Document 列表

    Args:
        data: 单文档处理结果字典
        source_file: 源文件路径

    Returns:
        LangChain Document 列表
    """
    if LangChainDocument is None:
        raise EntryError.DocumentLoadFailed("langchain-core 未安装")

    documents = []
    chunks = data.get("chunks", [])
    metadata = data.get("metadata", {})
    dedup_info = data.get("dedup_info", {})

    for chunk in chunks:
        doc = LangChainDocument(
            page_content=chunk.get("text", ""),
            metadata={
                "source_url": metadata.get("source_url", str(source_file)),
                "primary_category": metadata.get("primary_category", "unknown"),
                "tech_tags": metadata.get("tech_tags", []),
                "chunk_start_index": chunk.get("start_index", 0),
                "chunk_end_index": chunk.get("end_index", 0),
                "crawl_time": metadata.get("crawl_time", ""),
                "full_text_hash": dedup_info.get("full_text_hash", ""),
                "source_file": str(source_file),
            },
        )
        documents.append(doc)

    return documents


# ========== 主入口 ==========


def main():
    """入口函数 - 演示调用"""
    logger.info("AI Knowledge Crawler MCP Module Started")

    # 示例：运行完整全链路
    # stats = run_full_pipeline(category="all", days=30)
    # print(f"执行统计：{stats}")

    # 示例：仅采集
    # stats = run_only_crawl(category="chinese", days=7)
    # print(f"采集统计：{stats}")

    # 示例：仅预处理
    # stats = asyncio.run(run_only_process(date_str="2026-07-01"))
    # print(f"预处理统计：{stats}")

    # 示例：加载 RAG 分片
    # docs = load_rag_documents()
    # print(f"加载 {len(docs)} 个 Document")

    logger.info("入口函数就绪，调用 run_full_pipeline / run_only_crawl / run_only_process")


if __name__ == "__main__":
    main()
