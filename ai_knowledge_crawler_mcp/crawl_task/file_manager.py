"""
文件管理器 - 原始 Markdown 文件存储与目录管理

功能：
1. 按 [日期/分类] 创建文件夹结构
2. 写入原始 Markdown 文件
3. 文件命名规范：{日期}_{序号}_{标题}.md
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class RawMarkdownManager:
    """原始 Markdown 文件管理器"""

    def __init__(self, base_path: str):
        """
        初始化文件管理器

        Args:
            base_path: 原始 Markdown 存储根路径
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"RawMarkdownManager 初始化：{self.base_path}")

    def _get_category_dir(self, category: str, date_str: Optional[str] = None) -> Path:
        """
        获取分类目录（按日期/分类组织）

        Args:
            category: 分类名称
            date_str: 日期字符串（YYYY-MM-DD 格式），默认今天

        Returns:
            分类目录路径
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 目录结构：raw_source_md/2024-01-15/RAG/
        category_dir = self.base_path / date_str / category
        category_dir.mkdir(parents=True, exist_ok=True)
        return category_dir

    def _generate_filename(
        self,
        title: str,
        category: str,
        date_str: str,
        counter: int
    ) -> str:
        """
        生成文件名

        Args:
            title: 文章标题（用于文件名）
            category: 分类
            date_str: 日期字符串
            counter: 序号（同目录下递增）

        Returns:
            文件名（不含扩展名）
        """
        # 清理标题中的非法字符
        safe_title = self._sanitize_filename(title)
        # 文件名格式：{日期}_{序号}_{标题}
        filename = f"{date_str}_{counter:03d}_{safe_title}"
        return filename

    def _sanitize_filename(self, name: str, max_length: int = 100) -> str:
        """
        清理文件名中的非法字符

        Args:
            name: 原始名称
            max_length: 最大长度

        Returns:
            安全的文件名
        """
        # 移除或替换非法字符
        illegal_chars = '<>:/"|?*'
        for char in illegal_chars:
            name = name.replace(char, '_')

        # 移除多余空格
        name = " ".join(name.split())

        # 截断超长名称
        if len(name) > max_length:
            name = name[:max_length]

        return name

    def _get_next_counter(self, category_dir: Path, date_str: str) -> int:
        """
        获取下一个序号

        Args:
            category_dir: 分类目录
            date_str: 日期字符串

        Returns:
            下一个序号
        """
        # 查找同目录下今日已存在的文件
        existing_files = list(category_dir.glob(f"{date_str}_*.md"))
        if not existing_files:
            return 1

        # 解析现有文件的序号
        max_counter = 0
        for file in existing_files:
            stem = file.stem  # 文件名不含扩展名
            parts = stem.split("_", 2)  # 分割：日期_序号_标题
            if len(parts) >= 2:
                try:
                    counter = int(parts[1])
                    max_counter = max(max_counter, counter)
                except ValueError:
                    continue

        return max_counter + 1

    def save_raw_markdown(
        self,
        url: str,
        markdown_content: str,
        title: str,
        category: str,
        date_str: Optional[str] = None
    ) -> Path:
        """
        保存原始 Markdown 文件

        Args:
            url: 原文链接
            markdown_content: Markdown 内容
            title: 文章标题
            category: 分类
            date_str: 日期字符串（默认今天）

        Returns:
            保存的文件路径
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 获取分类目录
        category_dir = self._get_category_dir(category, date_str)

        # 获取下一个序号
        counter = self._get_next_counter(category_dir, date_str)

        # 生成文件名
        filename = self._generate_filename(title, category, date_str, counter)
        file_path = category_dir / f"{filename}.md"

        # 写入文件（添加元数据头部）
        content_with_metadata = self._add_metadata(
            url=url,
            title=title,
            category=category,
            crawl_date=date_str,
            markdown_content=markdown_content
        )

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content_with_metadata)
            logger.info(f"保存原始 Markdown: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")
            raise

    def _add_metadata(
        self,
        url: str,
        title: str,
        category: str,
        crawl_date: str,
        markdown_content: str
    ) -> str:
        """
        添加文件头部元数据

        Args:
            url: 原文链接
            title: 标题
            category: 分类
            crawl_date: 抓取日期
            markdown_content: 原始 Markdown 内容

        Returns:
            带元数据的完整内容
        """
        metadata = f"""---
source_url: {url}
title: {title}
category: {category}
crawl_date: {crawl_date}
crawl_time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

{markdown_content}
"""
        return metadata

    def get_existing_files(
        self,
        category: str,
        date_str: Optional[str] = None
    ) -> List[Path]:
        """
        获取指定分类已存在的文件

        Args:
            category: 分类
            date_str: 日期字符串（None 表示所有日期）

        Returns:
            文件路径列表
        """
        if date_str:
            category_dir = self._get_category_dir(category, date_str)
            return list(category_dir.glob("*.md"))
        else:
            # 遍历所有日期目录
            all_files = []
            for date_dir in self.base_path.iterdir():
                if date_dir.is_dir():
                    category_subdir = date_dir / category
                    if category_subdir.exists():
                        all_files.extend(list(category_subdir.glob("*.md")))
            return all_files

    def get_today_dirs(self) -> List[Path]:
        """
        获取今天创建的日期目录

        Returns:
            日期目录列表
        """
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = self.base_path / today
        if today_dir.exists():
            return [today_dir]
        return []

    def get_all_categories(self) -> List[str]:
        """
        获取所有分类名称

        Returns:
            分类名称列表
        """
        categories = set()
        for date_dir in self.base_path.iterdir():
            if date_dir.is_dir():
                for category_dir in date_dir.iterdir():
                    if category_dir.is_dir():
                        categories.add(category_dir.name)
        return sorted(list(categories))

    def get_file_count_by_category(self) -> Dict[str, int]:
        """
        获取各分类的文件数量统计

        Returns:
            {分类：数量} 字典
        """
        stats = {}
        for date_dir in self.base_path.iterdir():
            if date_dir.is_dir():
                for category_dir in date_dir.iterdir():
                    if category_dir.is_dir():
                        category = category_dir.name
                        file_count = len(list(category_dir.glob("*.md")))
                        stats[category] = stats.get(category, 0) + file_count
        return stats
