"""
智能体文档处理 MCP 适配器

封装智能体文档处理 MCP 服务，用于批量执行文本清洗、去重、分片、分类打标签。
"""

import logging
from typing import Any, List, Dict, Optional
from .base_adapter import MCPAdapterBase

logger = logging.getLogger(__name__)


class DocProcessorAdapter(MCPAdapterBase):
    """智能体文档处理 MCP 适配器"""

    def __init__(self, base_url: str = "http://127.0.0.1:8085/mcp", timeout: int = 180):
        """
        初始化文档处理适配器

        Args:
            base_url: 文档处理 MCP 服务地址（通常使用 LLM MCP）
            timeout: 调用超时时间（秒，文档处理需要较长时间）
        """
        super().__init__(base_url=base_url, timeout=timeout, adapter_name="doc_processor")

    async def process_document(
        self,
        markdown_content: str,
        source_url: Optional[str] = None,
        tech_category: Optional[str] = None,
        chunk_size: int = 800,
        chunk_overlap: int = 150
    ) -> Dict[str, Any]:
        """
        处理单个文档：清洗、去重、分片、分类

        Args:
            markdown_content: 原始 Markdown 内容
            source_url: 原文链接
            tech_category: 技术分类标签（可选，自动分类则不传）
            chunk_size: 分片 token 长度
            chunk_overlap: 分片重叠长度

        Returns:
            处理结果
            {
                "status": "success|failed",
                "cleaned_markdown": "清洗后的完整 Markdown",
                "chunks": [
                    {
                        "text": "分片文本",
                        "start_index": 起始位置，
                        "end_index": 结束位置
                    }
                ],
                "metadata": {
                    "title": "文章标题",
                    "summary": "文章摘要",
                    "source_url": "原文链接",
                    "tech_tags": ["技术标签 1", "技术标签 2"],
                    "crawl_time": "抓取时间",
                    "word_count": 字数，
                    "chunk_count": 分片数量
                },
                "dedup_info": {
                    "full_text_hash": "全文哈希",
                    "removed_duplicate_chunks": 移除的重复分片数量
                }
            }
        """
        arguments = {
            "markdown_content": markdown_content,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        }

        if source_url:
            arguments["source_url"] = source_url
        if tech_category:
            arguments["tech_category"] = tech_category

        result = await self.call_tool("process_document", arguments)
        return result

    async def process_documents_batch(
        self,
        documents: List[Dict[str, str]],
        chunk_size: int = 800,
        chunk_overlap: int = 150
    ) -> List[Dict[str, Any]]:
        """
        批量处理文档列表

        Args:
            documents: 文档列表
                [
                    {
                        "markdown": "Markdown 内容",
                        "source_url": "原文链接",
                        "tech_category": "技术分类（可选）"
                    },
                    ...
                ]
            chunk_size: 分片 token 长度
            chunk_overlap: 分片重叠长度

        Returns:
            处理结果列表
        """
        results = []

        for idx, doc in enumerate(documents):
            try:
                logger.info(f"[doc_processor] Processing document {idx + 1}/{len(documents)}")
                result = await self.process_document(
                    markdown_content=doc["markdown"],
                    source_url=doc.get("source_url"),
                    tech_category=doc.get("tech_category"),
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                result["document_index"] = idx
                results.append(result)
            except Exception as e:
                logger.error(f"[doc_processor] Failed to process document {idx + 1}: {e}")
                results.append({
                    "status": "failed",
                    "document_index": idx,
                    "error": str(e),
                    "source_url": doc.get("source_url", "unknown")
                })

        return results

    async def clean_text(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        仅执行文本清洗（不执行分片）

        Args:
            text: 原始文本

        Returns:
            {
                "cleaned_text": "清洗后的文本",
                "removed_patterns": ["移除的模式 1", ...]
            }
        """
        result = await self.call_tool("clean_text", {"text": text})
        return result

    async def deduplicate_chunks(
        self,
        chunks: List[str],
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        执行分片去重

        Args:
            chunks: 分片列表
            similarity_threshold: 相似度阈值（0-1）

        Returns:
            {
                "unique_chunks": ["去重后的分片"],
                "removed_count": 移除的重复分片数量，
                "duplicate_pairs": [
                    {"chunk1_index": 0, "chunk2_index": 1, "similarity": 0.92}
                ]
            }
        """
        result = await self.call_tool(
            "deduplicate_chunks",
            {"chunks": chunks, "similarity_threshold": similarity_threshold}
        )
        return result

    async def classify_document(
        self,
        text: str,
        available_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        文档自动分类打标签

        Args:
            text: 文档文本
            available_categories: 可选的分类列表

        Returns:
            {
                "primary_category": "主分类",
                "tags": ["标签 1", "标签 2"],
                "confidence": 0.95
            }
        """
        arguments = {"text": text}
        if available_categories:
            arguments["categories"] = available_categories

        result = await self.call_tool("classify_document", arguments)
        return result
