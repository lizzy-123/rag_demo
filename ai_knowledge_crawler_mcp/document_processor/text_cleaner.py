"""文本清洗模块 - 去除噪声、规整 Markdown"""

import logging
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from .base_processor import BaseProcessor, DocumentProcessorError

logger = logging.getLogger(__name__)


class TextCleaner(BaseProcessor):
    """文本清洗器 - 去除导航、广告、页脚、HTML 残留、多余空白"""

    # HTML 标签正则
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>", re.DOTALL)
    # HTML 实体
    HTML_ENTITY_PATTERN = re.compile(r"&#\d+;|&[a-zA-Z]+;")
    # 多余空白行（3 行及以上连续空行）
    EXCESS_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")
    # 行首行尾空白
    LINE_WHITESPACE_PATTERN = re.compile(r"^[ \t]+|[ \t]+$", re.MULTILINE)
    # 常见导航链接模式
    NAVIGATION_PATTERN = re.compile(
        r"^\s*(首页 | 关于我们 | 联系我们 | 网站地图 | 版权声明 | 加入收藏 | 返回顶部 | 菜单|Menu|Home|About|Contact)\s*:",
        re.IGNORECASE | re.MULTILINE,
    )
    # 页脚版权信息
    FOOTER_PATTERN = re.compile(
        r"^\s*(©|Copyright)\s*[\d\-]+.*$(|^\s*Powered by.*$|^\s*ICP 备 [\d\-]+号.*$)",
        re.IGNORECASE | re.MULTILINE,
    )
    # 广告关键词
    AD_KEYWORDS_PATTERN = re.compile(
        r"(广告 | 赞助 | 推荐 | 热门 | 排行榜 | 猜你喜欢 | Advertisement|Sponsored)",
        re.IGNORECASE,
    )
    # 孤立 URL（单独一行的完整 URL）
    STANDALONE_URL_PATTERN = re.compile(r"^\s*(https?://[^\s]+)\s*$", re.MULTILINE)
    # 多余标点
    EXCESS_PUNCTUATION_PATTERN = re.compile(r"[!！?？…\.\.\.]{2,}")

    def __init__(self):
        super().__init__("text_cleaner")

    def clean(self, raw_text: str, source_url: Optional[str] = None) -> str:
        """
        清洗文本

        Args:
            raw_text: 原始文本
            source_url: 源 URL（可选，用于额外过滤）

        Returns:
            清洗后的文本

        Raises:
            DocumentProcessorError.InvalidInput: 输入为空
        """
        if not raw_text or not raw_text.strip():
            self._logger.warning("[text_cleaner] 输入为空或全空白")
            return ""

        self._log_process_start("清洗文本", f"长度：{len(raw_text)}")

        cleaned = raw_text

        # 1. 移除 HTML 标签
        cleaned = self._remove_html_tags(cleaned)

        # 2. 解码 HTML 实体
        cleaned = self._decode_html_entities(cleaned)

        # 3. 移除导航信息
        cleaned = self._remove_navigation(cleaned)

        # 4. 移除页脚
        cleaned = self._remove_footer(cleaned)

        # 5. 移除广告内容
        cleaned = self._remove_ads(cleaned)

        # 6. 移除孤立 URL
        if source_url:
            cleaned = self._remove_standalone_urls(cleaned, source_url)

        # 7. 规整空白
        cleaned = self._normalize_whitespace(cleaned)

        # 8. 规整多余标点
        cleaned = self._normalize_punctuation(cleaned)

        self._log_process_complete("清洗文本", len(cleaned))

        return cleaned

    def _remove_html_tags(self, text: str) -> str:
        """移除 HTML 标签"""
        return self.HTML_TAG_PATTERN.sub("", text)

    def _decode_html_entities(self, text: str) -> str:
        """解码 HTML 实体"""
        import html

        return html.unescape(text)

    def _remove_navigation(self, text: str) -> str:
        """移除导航信息"""
        lines = text.split("\n")
        filtered = []
        for line in lines:
            if not self.NAVIGATION_PATTERN.match(line):
                filtered.append(line)
        return "\n".join(filtered)

    def _remove_footer(self, text: str) -> str:
        """移除页脚信息"""
        lines = text.split("\n")
        filtered = []
        for line in lines:
            if not self.FOOTER_PATTERN.match(line):
                filtered.append(line)
        return "\n".join(filtered)

    def _remove_ads(self, text: str) -> str:
        """移除广告内容"""
        lines = text.split("\n")
        filtered = []
        for line in lines:
            if not self.AD_KEYWORDS_PATTERN.search(line):
                filtered.append(line)
        return "\n".join(filtered)

    def _remove_standalone_urls(self, text: str, source_url: str) -> str:
        """移除孤立 URL（与源 URL 相同）"""
        parsed_source = urlparse(source_url)
        source_domain = parsed_source.netloc

        def replace_url(match):
            url = match.group(1)
            parsed = urlparse(url)
            if parsed.netloc == source_domain:
                return ""
            return match.group(0)

        return self.STANDALONE_URL_PATTERN.sub(replace_url, text)

    def _normalize_whitespace(self, text: str) -> str:
        """规整空白字符"""
        # 移除行首行尾空白
        text = self.LINE_WHITESPACE_PATTERN.sub("", text)
        # 压缩多余空行
        text = self.EXCESS_BLANK_LINES_PATTERN.sub("\n\n", text)
        # 移除首尾空白
        text = text.strip()
        return text

    def _normalize_punctuation(self, text: str) -> str:
        """规整多余标点"""
        return self.EXCESS_PUNCTUATION_PATTERN.sub(lambda m: m.group(0)[0], text)

    def process(self, raw_text: str, source_url: Optional[str] = None) -> Dict[str, Any]:
        """
        执行清洗（符合 BaseProcessor 接口）

        Args:
            raw_text: 原始文本
            source_url: 源 URL

        Returns:
            {"cleaned_text": str, "original_length": int, "cleaned_length": int}
        """
        original_length = len(raw_text) if raw_text else 0
        cleaned = self.clean(raw_text, source_url)
        return {
            "cleaned_text": cleaned,
            "original_length": original_length,
            "cleaned_length": len(cleaned),
        }
