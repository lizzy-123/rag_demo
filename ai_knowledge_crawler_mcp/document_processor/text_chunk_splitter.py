"""文本分片模块 - 按 token 近似换算分割，支持标题优先切割"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple

from .base_processor import BaseProcessor, DocumentProcessorError

logger = logging.getLogger(__name__)


class TextChunkSplitter(BaseProcessor):
    """文本分片器 - 纯 Python 实现，按近似 token 换算"""

    # 中文近似 token 换算：1 token ≈ 0.6 个汉字
    CHARS_PER_TOKEN = 0.6
    # 英文近似 token 换算：1 token ≈ 4 个字符
    EN_CHARS_PER_TOKEN = 4
    # 默认分片大小（字符数，按中文换算）
    DEFAULT_CHUNK_SIZE = 800
    # 默认重叠大小
    DEFAULT_CHUNK_OVERLAP = 150
    # 标题行正则（Markdown 标题）
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        """
        Args:
            chunk_size: 分片大小（字符数）
            chunk_overlap: 分片重叠大小（字符数）
        """
        super().__init__("text_chunk_splitter")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._validate_params()

    def _validate_params(self) -> None:
        """验证分片参数"""
        self._validate_positive_int(
            self.chunk_size,
            "chunk_size",
            min_value=50,
        )
        self._validate_non_negative_int(
            self.chunk_overlap,
            "chunk_overlap",
            max_value=self.chunk_size - 1,
        )
        if self.chunk_overlap >= self.chunk_size:
            raise DocumentProcessorError.ValidationError(
                "chunk_overlap 必须小于 chunk_size",
                details={
                    "chunk_overlap": self.chunk_overlap,
                    "chunk_size": self.chunk_size,
                },
            )

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, value: int) -> None:
        self._chunk_size = value

    @property
    def chunk_overlap(self) -> int:
        return self._chunk_overlap

    @chunk_overlap.setter
    def chunk_overlap(self, value: int) -> None:
        self._chunk_overlap = value

    def split(self, text: str) -> List[Dict[str, Any]]:
        """
        分片文本

        Args:
            text: 待分片文本（应为已清洗的 Markdown）

        Returns:
            分片列表，每个分片包含：
            {
                "text": str,
                "start_index": int,
                "end_index": int,
                "chunk_type": "heading" | "content"
            }
        """
        if not text or not text.strip():
            self._logger.warning("[text_chunk_splitter] 输入为空")
            return []

        self._log_process_start("分片文本", f"长度：{len(text)}")

        # 全文短于分片阈值时整体作为单一片段
        if len(text) <= self.chunk_size:
            chunk = {
                "text": text,
                "start_index": 0,
                "end_index": len(text),
                "chunk_type": "content",
            }
            self._log_process_complete("分片文本", 1)
            return [chunk]

        # 提取标题位置，用于优先切割
        heading_positions = self._extract_heading_positions(text)

        # 按标题优先分片
        chunks = self._split_by_headings(text, heading_positions)

        # 如果按标题分片后仍有超大块，进行二次切割
        chunks = self._split_large_chunks(chunks)

        self._log_process_complete("分片文本", len(chunks))

        return chunks

    def _extract_heading_positions(self, text: str) -> List[Tuple[int, int, int, str]]:
        """
        提取所有标题的位置信息

        Returns:
            列表：[(start, end, level, heading_text), ...]
        """
        positions = []
        for match in self.HEADING_PATTERN.finditer(text):
            start = match.start()
            end = match.end()
            level = len(match.group(1))  # # 的数量
            heading_text = match.group(2).strip()
            positions.append((start, end, level, heading_text))
        return positions

    def _split_by_headings(
        self, text: str, heading_positions: List[Tuple[int, int, int, str]]
    ) -> List[Dict[str, Any]]:
        """
        按标题位置分片

        Args:
            text: 全文本
            heading_positions: 标题位置列表

        Returns:
            分片列表
        """
        if not heading_positions:
            # 无标题时直接按字符数切割
            return self._split_by_char_count(text)

        chunks = []
        current_pos = 0

        for start, end, level, heading_text in heading_positions:
            # 标题前的内容
            if start > current_pos:
                content_before = text[current_pos:start]
                if content_before.strip():
                    chunks.extend(
                        self._split_by_char_count(content_before, current_pos)
                    )

            # 标题本身（尝试与后续内容合并）
            next_start = heading_positions[
                heading_positions.index((start, end, level, heading_text)) + 1
            ][0] if heading_positions.index((start, end, level, heading_text)) + 1 < len(
                heading_positions
            ) else len(text)

            heading_with_content = text[start:next_start]
            if len(heading_with_content) <= self.chunk_size:
                # 标题和后续内容一起作为一个分片
                chunks.append(
                    {
                        "text": heading_with_content.strip(),
                        "start_index": start,
                        "end_index": next_start,
                        "chunk_type": "heading",
                    }
                )
                current_pos = next_start
            else:
                # 标题单独，后续内容再分片
                chunks.append(
                    {
                        "text": heading_text,
                        "start_index": start,
                        "end_index": end,
                        "chunk_type": "heading",
                    }
                )
                current_pos = end

        # 最后剩余内容
        if current_pos < len(text):
            remaining = text[current_pos:]
            if remaining.strip():
                chunks.extend(self._split_by_char_count(remaining, current_pos))

        return chunks

    def _split_by_char_count(
        self, text: str, start_offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按字符数简单切割（带重叠）

        Args:
            text: 待切割文本
            start_offset: 起始偏移量（在原文中的位置）

        Returns:
            分片列表
        """
        chunks = []
        pos = 0
        text_len = len(text)

        while pos < text_len:
            end_pos = pos + self.chunk_size

            # 尝试在句子边界切割
            if end_pos < text_len:
                # 向前查找最近的换行或句号
                split_pos = self._find_split_point(text, pos, end_pos)
                end_pos = split_pos

            chunk_text = text[pos:end_pos]
            chunks.append(
                {
                    "text": chunk_text.strip(),
                    "start_index": start_offset + pos,
                    "end_index": start_offset + end_pos,
                    "chunk_type": "content",
                }
            )

            # 移动到下一个分片（带重叠）
            pos = end_pos - self.chunk_overlap if end_pos < text_len else text_len

        return chunks

    def _find_split_point(self, text: str, start: int, end: int) -> int:
        """
        在指定范围内查找最佳切割点（优先换行，其次句号）

        Args:
            text: 全文本
            start: 搜索起始
            end: 搜索结束

        Returns:
            切割位置
        """
        search_text = text[start:end]

        # 优先查找换行
        newline_pos = search_text.rfind("\n")
        if newline_pos != -1 and newline_pos > len(search_text) * 0.3:
            return start + newline_pos

        # 查找句号
        for punct in ["。", ".", "！", "!", "?", "?"]:
            punct_pos = search_text.rfind(punct)
            if punct_pos != -1 and punct_pos > len(search_text) * 0.3:
                return start + punct_pos + len(punct)

        # 查找空格（英文）
        space_pos = search_text.rfind(" ")
        if space_pos != -1 and space_pos > len(search_text) * 0.5:
            return start + space_pos

        # 找不到合适位置，返回原始 end
        return end

    def _split_large_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对超大分片进行二次切割

        Args:
            chunks: 分片列表

        Returns:
            切割后的分片列表
        """
        result = []
        for chunk in chunks:
            if len(chunk["text"]) > self.chunk_size:
                # 递归切割
                sub_chunks = self._split_by_char_count(
                    chunk["text"], chunk["start_index"]
                )
                result.extend(sub_chunks)
            else:
                result.append(chunk)
        return result

    def process(self, text: str) -> Dict[str, Any]:
        """
        执行分片（符合 BaseProcessor 接口）

        Args:
            text: 待分片文本

        Returns:
            {"chunks": list, "chunk_count": int, "total_length": int}
        """
        chunks = self.split(text)
        return {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "total_length": len(text) if text else 0,
        }
