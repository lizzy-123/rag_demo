"""文档分类模块 - 自动分类打标签"""

import logging
from typing import Dict, Any, List, Optional

from .base_processor import BaseProcessor, DocumentProcessorError

logger = logging.getLogger(__name__)


class TextClassifier(BaseProcessor):
    """文本分类器 - 自动分类和打标签"""

    # 默认技术分类（可根据需要扩展）
    DEFAULT_CATEGORIES = [
        "编程语言",
        "框架",
        "数据库",
        "运维",
        "安全",
        "算法",
        "架构",
        "工具",
        "其他",
    ]

    # 分类关键词映射（简单关键词匹配，实际可替换为 LLM 分类）
    CATEGORY_KEYWORDS = {
        "编程语言": ["python", "java", "go", "rust", "javascript", "typescript", "c++", "c#", "php", "ruby"],
        "框架": ["spring", "django", "flask", "fastapi", "react", "vue", "angular", "laravel", "next.js"],
        "数据库": ["mysql", "postgresql", "mongodb", "redis", "elasticsearch", "sqlite", "oracle"],
        "运维": ["docker", "kubernetes", "jenkins", "ansible", "nginx", "linux", "ci/cd"],
        "安全": ["security", "加密", "认证", "oauth", "jwt", "ssl", "tls", "渗透", "漏洞"],
        "算法": ["算法", "排序", "搜索", "机器学习", "深度学习", "神经网络", "nlp", "cv"],
        "架构": ["架构", "微服务", "分布式", "高并发", "高可用", "设计模式", "系统架构"],
        "工具": ["git", "vim", "idea", "pycharm", "vscode", "terminal", "命令行"],
    }

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        use_llm: bool = False,
    ):
        """
        Args:
            categories: 可选分类列表，None 使用默认分类
            use_llm: 是否使用 LLM 分类（目前预留，默认为关键词匹配）
        """
        super().__init__("text_classifier")
        self.categories = categories or self.DEFAULT_CATEGORIES
        self.use_llm = use_llm
        self._llm_client = None

    def classify(
        self, text: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分类文本

        Args:
            text: 待分类文本
            title: 可选标题（用于辅助分类）

        Returns:
            {
                "primary_category": 主分类，
                "tags": 多标签列表，
                "confidence": 置信度 (0~1)
            }
        """
        if not text or not text.strip():
            self._logger.warning("[text_classifier] 输入为空或全空白")
            return {
                "primary_category": "unknown",
                "tags": [],
                "confidence": 0.0,
            }

        self._log_process_start("分类", f"长度：{len(text)}")

        # 有效内容过少返回 unknown
        if len(text.strip()) < 20:
            self._logger.warning("[text_classifier] 有效内容过少")
            return {
                "primary_category": "unknown",
                "tags": [],
                "confidence": 0.0,
            }

        # 合并标题和文本用于分类
        content = text
        if title:
            content = f"{title} {text}"

        if self.use_llm and self._llm_client:
            # LLM 分类（预留接口）
            result = self._llm_classify(content, title)
        else:
            # 关键词匹配分类
            result = self._keyword_classify(content)

        self._log_process_complete("分类")

        return result

    def _keyword_classify(self, content: str) -> Dict[str, Any]:
        """
        关键词匹配分类

        Args:
            content: 待分类内容

        Returns:
            分类结果
        """
        content_lower = content.lower()
        category_scores = {}

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if category not in self.categories:
                continue

            score = 0
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    score += 1

            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return {
                "primary_category": "其他",
                "tags": [],
                "confidence": 0.3,
            }

        # 按得分排序
        sorted_categories = sorted(
            category_scores.items(), key=lambda x: x[1], reverse=True
        )

        primary_category = sorted_categories[0][0]
        max_score = sorted_categories[0][1]

        # 计算置信度（得分/总关键词数）
        total_keywords = sum(len(kws) for kws in self.CATEGORY_KEYWORDS.values())
        confidence = min(1.0, max_score / 5)  # 最多 5 个关键词命中即满置信度

        # 提取多标签（得分前 3）
        tags = [cat for cat, _ in sorted_categories[:3] if cat != primary_category]

        return {
            "primary_category": primary_category,
            "tags": tags,
            "confidence": round(confidence, 2),
        }

    def _llm_classify(self, content: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        LLM 分类（预留接口）

        Args:
            content: 待分类内容
            title: 可选标题

        Returns:
            分类结果
        """
        # TODO: 接入 LLM API
        # 目前降级到关键词匹配
        return self._keyword_classify(content)

    def process(
        self, text: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行分类（符合 BaseProcessor 接口）

        Args:
            text: 待分类文本
            title: 可选标题

        Returns:
            分类结果
        """
        return self.classify(text, title)
