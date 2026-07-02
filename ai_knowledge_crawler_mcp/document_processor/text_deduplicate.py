"""分片去重模块 - 支持哈希精确去重和语义相似度去重双模式"""

import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple

from .base_processor import BaseProcessor, DocumentProcessorError
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TextDeduplicator(BaseProcessor):
    """分片去重器 - 双模式自动降级"""

    # 语义相似度阈值默认值
    DEFAULT_SIMILARITY_THRESHOLD = 0.85
    # 语义模式依赖包
    SEMANTIC_DEPS = {"sentence_transformers", "numpy"}

    def __init__(
        self,
        use_semantic: bool = True,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        """
        Args:
            use_semantic: 是否尝试使用语义相似度模式
            similarity_threshold: 相似度阈值（0~0.85，超过视为重复）
        """
        super().__init__("text_deduplicator")
        self.use_semantic = use_semantic
        self.similarity_threshold = similarity_threshold
        self._semantic_available = False
        self._similarity_model = None
        self._numpy = None

        self._validate_params()
        self._check_semantic_deps()

    def _validate_params(self) -> None:
        """验证参数"""
        if not (0 <= self.similarity_threshold <= 0.85):
            raise DocumentProcessorError.ValidationError(
                "similarity_threshold 必须在 0~0.85 之间",
                details={"value": self.similarity_threshold},
            )

    def _check_semantic_deps(self) -> None:
        """检查语义模式依赖是否可用"""
        if not self.use_semantic:
            self._logger.info("[text_deduplicator] 语义模式已禁用，使用哈希模式")
            return

        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer

            self._numpy = np
            self._similarity_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self._semantic_available = True
            self._logger.info("[text_deduplicator] 语义模式可用")
        except ImportError as e:
            self._logger.warning(
                f"[text_deduplicator] 语义模式依赖缺失：{e}，降级到哈希模式"
            )
            self._semantic_available = False
        except Exception as e:
            self._logger.warning(
                f"[text_deduplicator] 语义模式初始化失败：{e}，降级到哈希模式"
            )
            self._semantic_available = False

    def deduplicate(
        self, chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int, List[Tuple[int, int]]]:
        """
        去重分片

        Args:
            chunks: 分片列表，每个分片包含"text"字段

        Returns:
            (去重后分片列表，移除数量，重复对列表 [(idx1, idx2), ...])
        """
        if not chunks:
            self._logger.warning("[text_deduplicator] 输入为空")
            return [], 0, []

        self._log_process_start("去重", f"分片数：{len(chunks)}")

        # 提取文本列表
        texts = [chunk.get("text", "") for chunk in chunks]

        if self._semantic_available:
            # 语义相似度去重
            unique_texts, removed_count, duplicate_pairs = self._semantic_deduplicate(
                texts
            )
        else:
            # 哈希精确去重
            unique_texts, removed_count, duplicate_pairs = self._hash_deduplicate(texts)

        # 构建返回分片列表（保留原始分片的其他字段）
        unique_chunks = []
        removed_indices = set()
        for idx, (i, j) in enumerate(duplicate_pairs):
            removed_indices.add(j)  # 保留 i，移除 j

        for idx, chunk in enumerate(chunks):
            if idx not in removed_indices:
                unique_chunks.append(chunk)

        self._log_process_complete("去重", len(unique_chunks))

        return unique_chunks, removed_count, duplicate_pairs

    def _hash_deduplicate(
        self, texts: List[str]
    ) -> Tuple[List[str], int, List[Tuple[int, int]]]:
        """
        哈希精确去重（无依赖兜底）

        Args:
            texts: 文本列表

        Returns:
            (去重后文本列表，移除数量，重复对列表)
        """
        seen_hashes = {}
        unique_texts = []
        duplicate_pairs = []
        removed_count = 0

        for idx, text in enumerate(texts):
            if not text.strip():
                unique_texts.append(text)
                continue

            text_hash = self._compute_hash(text)

            if text_hash in seen_hashes:
                # 发现重复
                original_idx = seen_hashes[text_hash]
                duplicate_pairs.append((original_idx, idx))
                removed_count += 1
            else:
                seen_hashes[text_hash] = idx
                unique_texts.append(text)

        return unique_texts, removed_count, duplicate_pairs

    def _semantic_deduplicate(
        self, texts: List[str]
    ) -> Tuple[List[str], int, List[Tuple[int, int]]]:
        """
        语义相似度去重

        Args:
            texts: 文本列表

        Returns:
            (去重后文本列表，移除数量，重复对列表)
        """
        if self._similarity_model is None or self._numpy is None:
            # 降级到哈希模式
            return self._hash_deduplicate(texts)

        # 过滤空文本
        non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
        non_empty_texts = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            return texts, 0, []

        # 计算向量
        try:
            embeddings = self._similarity_model.encode(non_empty_texts)
        except Exception as e:
            self._logger.warning(
                f"[text_deduplicator] 语义向量计算失败：{e}，降级到哈希模式"
            )
            return self._hash_deduplicate(texts)

        # 计算余弦相似度并去重
        unique_texts = []
        duplicate_pairs = []
        removed_count = 0
        kept_indices = set()

        for i, text in enumerate(non_empty_texts):
            original_idx = non_empty_indices[i]
            is_duplicate = False

            for j, kept_idx in enumerate(kept_indices):
                # 计算余弦相似度
                similarity = self._cosine_similarity(embeddings[i], embeddings[kept_idx])

                if similarity >= self.similarity_threshold:
                    duplicate_pairs.append((non_empty_indices[kept_idx], original_idx))
                    removed_count += 1
                    is_duplicate = True
                    break

            if not is_duplicate:
                kept_indices.add(i)
                unique_texts.append(text)
            else:
                continue

        # 重建完整列表（包含空文本位置）
        result_texts = []
        unique_set = set((i, t) for i, t in enumerate(unique_texts))
        for idx in range(len(texts)):
            if texts[idx].strip():
                # 查找是否在 unique_texts 中
                for i, (orig_idx, text) in enumerate(zip(non_empty_indices, unique_texts)):
                    if orig_idx == idx:
                        result_texts.append(text)
                        break
            else:
                result_texts.append(texts[idx])

        return result_texts, removed_count, duplicate_pairs

    def _cosine_similarity(self, vec1, vec2) -> float:
        """计算余弦相似度"""
        norm1 = self._numpy.linalg.norm(vec1)
        norm2 = self._numpy.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(self._numpy.dot(vec1, vec2) / (norm1 * norm2))

    def _compute_hash(self, text: str) -> str:
        """计算文本哈希"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def process(
        self, chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行去重（符合 BaseProcessor 接口）

        Args:
            chunks: 分片列表

        Returns:
            {
                "chunks": 去重后分片列表，
                "removed_count": 移除数量，
                "duplicate_pairs": 重复对列表，
                "mode": "semantic" | "hash"
            }
        """
        unique_chunks, removed_count, duplicate_pairs = self.deduplicate(chunks)
        mode = "semantic" if self._semantic_available else "hash"

        return {
            "chunks": unique_chunks,
            "removed_count": removed_count,
            "duplicate_pairs": duplicate_pairs,
            "mode": mode,
        }
