"""文档处理流水线 - 对外统一入口"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from .base_processor import BaseProcessor, DocumentProcessorError
from .text_cleaner import TextCleaner
from .text_chunk_splitter import TextChunkSplitter
from .text_deduplicate import TextDeduplicator
from .text_classifier import TextClassifier

logger = logging.getLogger(__name__)


class DocumentPipeline(BaseProcessor):
    """文档处理流水线 - 提供单文档和批量处理入口"""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        use_semantic_dedup: bool = True,
        dedup_threshold: float = 0.85,
        custom_categories: Optional[List[str]] = None,
    ):
        """
        Args:
            chunk_size: 分片大小（字符数）
            chunk_overlap: 分片重叠大小
            use_semantic_dedup: 是否使用语义去重
            dedup_threshold: 语义相似度阈值
            custom_categories: 自定义分类列表
        """
        super().__init__("document_pipeline")

        # 初始化各子模块
        self.cleaner = TextCleaner()
        self.splitter = TextChunkSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self.deduplicator = TextDeduplicator(
            use_semantic=use_semantic_dedup, similarity_threshold=dedup_threshold
        )
        self.classifier = TextClassifier(categories=custom_categories)
  
    def process(
            self,document,**kwargs
    )->Any:
        """
        统一处理入口，实现BaseProcessor 的抽象方法
        Args:
          document:单文档火文档列表(每个字典需包含markdown,source_url等)
          **kwargs：额外参数
          return:
             - 结果列表：若输入为单文档，返回包含一个结果的列表；若输入为列表，返回对应结果列表。
          Raises:
            TypeError:输入类型不为dict或者list
        """
        # 判断输入类型并归一化列表
        if isinstance(document,dict):
            doc_list = [document]
        elif isinstance(document,list):
            doc_list = document
        else:
            raise TypeError("document must be dict or list of dicts")
        #调用批量处理
        result = self.process_batch(doc_list)
        return result

    def process_single(
        self,
        markdown: str,
        source_url: str,
        tech_category: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        单文档处理：清洗→分片→去重→分类

        Args:
            markdown: 原始 Markdown 文本
            source_url: 源 URL
            tech_category: 可选的技术分类（用于覆盖自动分类）
            chunk_size: 可选的分片大小（覆盖初始化参数）
            chunk_overlap: 可选的分片重叠（覆盖初始化参数）

        Returns:
            标准化结果结构体
        """
        try:
            self._log_process_start("处理单文档", source_url)

            # 动态调整分片参数
            if chunk_size is not None or chunk_overlap is not None:
                self.splitter._validate_params()

            # 1. 文本清洗
            clean_result = self.cleaner.process(markdown, source_url)
            cleaned_text = clean_result.get("cleaned_text", "")

            if not cleaned_text.strip():
                return self._format_failed_result(
                    "清洗后文本为空",
                    source_url=source_url,
                )

            # 2. 文本分片
            split_result = self.splitter.process(cleaned_text)
            chunks = split_result.get("chunks", [])

            if not chunks:
                return self._format_failed_result(
                    "分片结果为空",
                    source_url=source_url,
                )

            # 3. 分片去重
            dedup_result = self.deduplicator.process(chunks)
            deduped_chunks = dedup_result.get("chunks", [])
            removed_count = dedup_result.get("removed_count", 0)
            duplicate_pairs = dedup_result.get("duplicate_pairs", [])

            # 4. 文档分类
            # 从 Markdown 中提取标题（如果有）
            title = self._extract_title(markdown) or self._extract_title_from_url(
                source_url
            )
            classify_result = self.classifier.process(cleaned_text, title)

            # 如果提供了技术分类，覆盖主分类
            if tech_category:
                classify_result["primary_category"] = tech_category
                if tech_category not in classify_result.get("tags", []):
                    classify_result["tags"].insert(0, tech_category)

            # 构建元数据
            metadata = self._build_metadata(
                cleaned_text,
                source_url,
                title,
                classify_result,
                len(deduped_chunks),
            )

            # 构建去重信息
            import hashlib

            full_text_hash = hashlib.md5(cleaned_text.encode("utf-8")).hexdigest()
            dedup_info = {
                "full_text_hash": full_text_hash,
                "removed_duplicate_chunks": removed_count,
                "duplicate_pairs": duplicate_pairs,
            }

            # 格式化成功结果
            return self._format_success_result(
                cleaned_markdown=cleaned_text,
                chunks=deduped_chunks,
                metadata=metadata,
                dedup_info=dedup_info,
            )

        except DocumentProcessorError as e:
            self._log_error("处理单文档", e)
            return self._format_failed_result(
                str(e),
                source_url=source_url,
            )
        except Exception as e:
            self._logger.error(f"[document_pipeline] 处理单文档发生未知错误：{e}")
            return self._format_failed_result(
                f"未知错误：{e}",
                source_url=source_url,
            )

    def process_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        批量文档处理：单文档异常隔离

        Args:
            documents: 文档列表，每个文档包含：
                {
                    "markdown": str,
                    "source_url": str,
                    "tech_category": Optional[str],
                    "chunk_size": Optional[int],
                    "chunk_overlap": Optional[int],
                }

        Returns:
            结果列表，每个结果附加 document_index 用于溯源
        """
        if not documents:
            self._logger.warning("[document_pipeline] 批量文档列表为空")
            return []

        self._log_process_start("批量处理文档", f"数量：{len(documents)}")

        results = []
        success_count = 0
        failed_count = 0

        for idx, doc in enumerate(documents):
            try:
                markdown = doc.get("markdown", "")
                source_url = doc.get("source_url", "")

                if not markdown:
                    result = self._format_failed_result(
                        "markdown 字段为空",
                        document_index=idx,
                        source_url=source_url,
                    )
                    result["document_index"] = idx
                    results.append(result)
                    failed_count += 1
                    continue

                if not source_url:
                    result = self._format_failed_result(
                        "source_url 字段为空",
                        document_index=idx,
                    )
                    result["document_index"] = idx
                    results.append(result)
                    failed_count += 1
                    continue

                # 调用单文档处理
                result = self.process_single(
                    markdown=markdown,
                    source_url=source_url,
                    tech_category=doc.get("tech_category"),
                    chunk_size=doc.get("chunk_size"),
                    chunk_overlap=doc.get("chunk_overlap"),
                )

                # 附加文档索引
                result["document_index"] = idx

                if result.get("status") == "success":
                    success_count += 1
                else:
                    failed_count += 1

                results.append(result)

            except Exception as e:
                self._logger.error(
                    f"[document_pipeline] 批量处理文档 {idx} 发生未知错误：{e}"
                )
                result = self._format_failed_result(
                    f"未知错误：{e}",
                    document_index=idx,
                    source_url=doc.get("source_url", "unknown"),
                )
                result["document_index"] = idx
                results.append(result)
                failed_count += 1

        self._logger.info(
            f"[document_pipeline] 批量处理完成 - 成功：{success_count}, 失败：{failed_count}"
        )

        return results

    def _extract_title(self, markdown: str) -> Optional[str]:
        """从 Markdown 中提取标题"""
        import re

        # 查找第一个#标题
        match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_title_from_url(self, url: str) -> Optional[str]:
        """从 URL 中提取标题（使用域名 + 路径）"""
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return parsed.netloc
        return f"{parsed.netloc}/{path}"

    def _build_metadata(
        self,
        cleaned_text: str,
        source_url: str,
        title: Optional[str],
        classify_result: Dict[str, Any],
        chunk_count: int,
    ) -> Dict[str, Any]:
        """构建元数据"""
        return {
            "title": title or "Untitled",
            "summary": self._generate_summary(cleaned_text),
            "source_url": source_url,
            "tech_tags": classify_result.get("tags", []),
            "primary_category": classify_result.get("primary_category", "unknown"),
            "crawl_time": datetime.now().isoformat(),
            "word_count": len(cleaned_text),
            "chunk_count": chunk_count,
        }

    def _generate_summary(self, text: str, max_length: int = 200) -> str:
        """生成简短摘要（取开头部分）"""
        # 移除 Markdown 标记
        import re

        cleaned = re.sub(r"[#*`\[\]]", "", text)
        cleaned = cleaned.strip()

        if len(cleaned) <= max_length:
            return cleaned

        # 在句子边界截断
        truncated = cleaned[:max_length]
        last_period = truncated.rfind(".")
        last_question = truncated.rfind("?")

        end_pos = max(last_period, last_question)
        if end_pos > max_length * 0.5:
            truncated = truncated[:end_pos + 1]
        else:
            truncated = truncated + "..."

        return truncated
