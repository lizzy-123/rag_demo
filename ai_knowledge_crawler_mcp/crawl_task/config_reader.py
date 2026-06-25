"""
配置读取器 - 读取并管理爬虫配置

功能：
1. 读取黑名单域名
2. 读取分领域搜索关键词（中文/英文）
3. 域名过滤检查
"""

import logging
from typing import List, Set
from urllib.parse import urlparse

from ..config import CrawlerConfig

logger = logging.getLogger(__name__)


class ConfigReader:
    """配置读取器"""

    def __init__(self, config: CrawlerConfig = None):
        """
        初始化配置读取器

        Args:
            config: CrawlerConfig 实例，None 则使用默认配置
        """
        self.config = config or CrawlerConfig()
        self._blacklist_domains: Set[str] = set()
        self._initialize_blacklist()
        logger.info(f"ConfigReader 初始化完成")

    def _initialize_blacklist(self) -> None:
        """初始化黑名单域名集合"""
        self._blacklist_domains = set(self.config.BLACKLIST_DOMAINS)
        logger.debug(f"黑名单域名：{self._blacklist_domains}")

    # ========== 关键词相关 ==========

    def get_search_keywords(self) -> List[str]:
        """
        获取中文搜索关键词

        Returns:
            关键词列表
        """
        return self.config.SEARCH_KEYWORDS.copy()

    def get_english_keywords(self) -> List[str]:
        """
        获取英文搜索关键词

        Returns:
            关键词列表
        """
        return self.config.ENGLISH_KEYWORDS.copy()

    def get_all_keywords(self) -> List[str]:
        """
        获取所有搜索关键词（中文 + 英文）

        Returns:
            关键词列表
        """
        return self.get_search_keywords() + self.get_english_keywords()

    def add_keyword(self, keyword: str, is_english: bool = False) -> None:
        """
        添加搜索关键词（运行时动态添加）

        Args:
            keyword: 关键词
            is_english: 是否为英文关键词
        """
        keyword = keyword.strip()
        if not keyword:
            logger.warning("忽略空关键词")
            return

        if is_english:
            if keyword not in self.config.ENGLISH_KEYWORDS:
                self.config.ENGLISH_KEYWORDS.append(keyword)
        else:
            if keyword not in self.config.SEARCH_KEYWORDS:
                self.config.SEARCH_KEYWORDS.append(keyword)

        logger.info(f"添加关键词：{keyword}")

    def remove_keyword(self, keyword: str, is_english: bool = False) -> bool:
        """
        移除搜索关键词

        Args:
            keyword: 关键词
            is_english: 是否为英文关键词

        Returns:
            是否成功移除
        """
        keyword_list = self.config.ENGLISH_KEYWORDS if is_english else self.config.SEARCH_KEYWORDS

        if keyword in keyword_list:
            keyword_list.remove(keyword)
            logger.info(f"移除关键词：{keyword}")
            return True
        return False

    # ========== 黑名单相关 ==========

    def is_domain_blacklisted(self, url: str) -> bool:
        """
        检查 URL 域名是否在黑名单中

        Args:
            url: URL 地址

        Returns:
            True 表示在黑名单中
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # 检查完整域名
            if domain in self._blacklist_domains:
                logger.debug(f"URL 域名在黑名单中：{domain}")
                return True

            # 检查父域名（如 example.com 匹配 sub.example.com）
            parts = domain.split(".")
            for i in range(len(parts)):
                parent_domain = ".".join(parts[i:])
                if parent_domain in self._blacklist_domains:
                    logger.debug(f"URL 父域名在黑名单中：{parent_domain}")
                    return True

            return False
        except Exception as e:
            logger.warning(f"解析 URL 失败 {url}: {e}")
            return False

    def filter_blacklisted_urls(self, urls: List[str]) -> List[str]:
        """
        过滤黑名单 URL

        Args:
            urls: URL 列表

        Returns:
            过滤后的 URL 列表（排除黑名单域名）
        """
        filtered = [url for url in urls if not self.is_domain_blacklisted(url)]
        removed_count = len(urls) - len(filtered)
        if removed_count > 0:
            logger.info(f"黑名单过滤：原始 {len(urls)} 条，过滤 {removed_count} 条")
        return filtered

    def add_blacklist_domain(self, domain: str) -> None:
        """
        添加黑名单域名

        Args:
            domain: 域名
        """
        domain = domain.lower().strip()
        if domain:
            self._blacklist_domains.add(domain)
            # 同步到 config
            if domain not in self.config.BLACKLIST_DOMAINS:
                self.config.BLACKLIST_DOMAINS.append(domain)
            logger.info(f"添加黑名单域名：{domain}")

    def remove_blacklist_domain(self, domain: str) -> bool:
        """
        移除黑名单域名

        Args:
            domain: 域名

        Returns:
            是否成功移除
        """
        domain = domain.lower().strip()
        if domain in self._blacklist_domains:
            self._blacklist_domains.remove(domain)
            if domain in self.config.BLACKLIST_DOMAINS:
                self.config.BLACKLIST_DOMAINS.remove(domain)
            logger.info(f"移除黑名单域名：{domain}")
            return True
        return False

    def get_blacklist_domains(self) -> List[str]:
        """
        获取所有黑名单域名

        Returns:
            域名列表
        """
        return sorted(list(self._blacklist_domains))

    # ========== 其他配置 ==========

    def get_chunk_size(self) -> int:
        """获取分片大小"""
        return self.config.CHUNK_SIZE

    def get_chunk_overlap(self) -> int:
        """获取分片重叠长度"""
        return self.config.CHUNK_OVERLAP

    def get_similarity_threshold(self) -> float:
        """获取去重相似度阈值"""
        return self.config.SIMILARITY_THRESHOLD

    def get_max_urls_per_run(self) -> int:
        """获取单次最大抓取 URL 数量"""
        return self.config.MAX_URLS_PER_RUN

    def get_fetch_timeout(self) -> int:
        """获取云端 Fetch MCP 超时时间"""
        return self.config.FETCH_MCP_TIMEOUT

    def get_retry_count(self) -> int:
        """获取失败重试次数"""
        return self.config.RETRY_COUNT

    def get_schedule_interval_hours(self) -> int:
        """获取定时间隔（小时）"""
        return self.config.SCHEDULE_INTERVAL_HOURS
