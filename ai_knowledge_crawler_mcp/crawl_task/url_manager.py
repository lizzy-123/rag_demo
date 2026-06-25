"""
URL 管理器 - 历史抓取 URL 持久化存储与去重

功能：
1. 历史抓取 URL 持久化存储（JSON 文件）
2. URL 去重检查
3. 增量过滤（排除已抓取链接）
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict, Optional

logger = logging.getLogger(__name__)


class URLManager:
    """URL 管理器：持久化存储与去重"""

    def __init__(self, storage_path: str):
        """
        初始化 URL 管理器

        Args:
            storage_path: URL 存储文件路径（JSON 格式）
        """
        self.storage_path = Path(storage_path)
        # 确保父目录存在
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._url_data: Dict = self._load_url_data()

    def _load_url_data(self) -> Dict:
        """
        加载 URL 数据

        Returns:
            URL 数据字典
            {
                "urls": [
                    {
                        "url": "https://example.com/article",
                        "category": "RAG",
                        "crawl_date": "2024-01-15",
                        "status": "success|failed"
                    }
                ],
                "stats": {
                    "total": 总数，
                    "success": 成功数，
                    "failed": 失败数
                }
            }
        """
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"加载 URL 数据：共 {data.get('stats', {}).get('total', 0)} 条记录")
                return data
            except Exception as e:
                logger.warning(f"加载 URL 数据失败：{e}，创建新文件")

        # 初始化空数据结构
        return {
            "urls": [],
            "stats": {
                "total": 0,
                "success": 0,
                "failed": 0
            }
        }

    def _save_url_data(self) -> None:
        """保存 URL 数据到 JSON 文件"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._url_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"保存 URL 数据：{self._url_data['stats']['total']} 条记录")
        except Exception as e:
            logger.error(f"保存 URL 数据失败：{e}")
            raise

    def is_url_crawled(self, url: str) -> bool:
        """
        检查 URL 是否已抓取

        Args:
            url: 待检查的 URL

        Returns:
            True 表示已抓取，False 表示未抓取
        """
        for record in self._url_data["urls"]:
            if record["url"] == url:
                return True
        return False

    def get_all_crawled_urls(self) -> Set[str]:
        """
        获取所有已抓取的 URL 集合

        Returns:
            URL 集合
        """
        return {record["url"] for record in self._url_data["urls"]}

    def filter_new_urls(self, urls: List[str]) -> List[str]:
        """
        过滤出新 URL（排除已抓取链接）

        Args:
            urls: URL 列表

        Returns:
            新 URL 列表（未抓取过的）
        """
        crawled_urls = self.get_all_crawled_urls()
        new_urls = [url for url in urls if url not in crawled_urls]
        logger.info(f"URL 过滤：原始 {len(urls)} 条，新 URL {len(new_urls)} 条，已存在 {len(urls) - len(new_urls)} 条")
        return new_urls

    def add_url_record(
        self,
        url: str,
        category: str,
        status: str = "success"
    ) -> None:
        """
        添加 URL 记录

        Args:
            url: URL 地址
            category: 分类（对应搜索关键词）
            status: 抓取状态（success/failed）
        """
        record = {
            "url": url,
            "category": category,
            "crawl_date": datetime.now().strftime("%Y-%m-%d"),
            "status": status
        }
        self._url_data["urls"].append(record)

        # 更新统计
        self._url_data["stats"]["total"] += 1
        if status == "success":
            self._url_data["stats"]["success"] += 1
        else:
            self._url_data["stats"]["failed"] += 1

        # 异步保存（避免频繁 IO）
        self._save_url_data()

    def add_urls_batch(
        self,
        urls: List[str],
        category: str,
        status: str = "success"
    ) -> None:
        """
        批量添加 URL 记录

        Args:
            urls: URL 列表
            category: 分类
            status: 抓取状态
        """
        for url in urls:
            self.add_url_record(url, category, status)

    def get_urls_by_category(self, category: str) -> List[str]:
        """
        获取指定分类的 URL 列表

        Args:
            category: 分类名称

        Returns:
            URL 列表
        """
        return [
            record["url"]
            for record in self._url_data["urls"]
            if record["category"] == category
        ]

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return self._url_data["stats"]

    def clear_failed_urls(self) -> int:
        """
        清除失败的 URL 记录（允许重试）

        Returns:
            清除的记录数量
        """
        original_count = len(self._url_data["urls"])
        self._url_data["urls"] = [
            record for record in self._url_data["urls"]
            if record["status"] != "failed"
        ]

        # 更新统计
        removed_count = original_count - len(self._url_data["urls"])
        self._url_data["stats"]["total"] -= removed_count
        self._url_data["stats"]["failed"] -= removed_count

        self._save_url_data()
        logger.info(f"清除 {removed_count} 条失败记录")
        return removed_count


# ========== 模块级单例 ==========
# 在 crawl_task/__init__.py 中初始化
