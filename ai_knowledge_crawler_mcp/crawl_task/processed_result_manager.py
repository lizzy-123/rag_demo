"""处理结果文件管理器 - 保存清洗分片后的成品数据"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib

from ..utils.logger import get_child_logger

logger = get_child_logger("processed_result_manager")


class ProcessedResultManager:
    """处理结果文件管理器 - 按日期分层存储成品 JSON"""

    def __init__(self, base_path: Path):
        """
        初始化

        Args:
            base_path: 基础存储路径（processed_knowledge）
        """
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"[processed_result_manager] 初始化完成，存储路径：{base_path}")

    def _get_date_directory(self, date_str: Optional[str] = None) -> Path:
        """
        获取日期目录（自动创建）

        Args:
            date_str: 日期字符串（YYYY-MM-DD），None 使用当前日期

        Returns:
            日期目录路径
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        date_dir = self.base_path / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir

    def _generate_filename(self, url: str, suffix: str = "_result.json") -> str:
        """
        生成文件名（使用 URL 哈希）

        Args:
            url: 源 URL
            suffix: 文件后缀

        Returns:
            文件名
        """
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        return f"{url_hash}{suffix}"

    def save_single_result(
        self,
        result: Dict[str, Any],
        date_str: Optional[str] = None,
        raw_md_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        保存单文档处理结果

        Args:
            result: 处理结果（document_processor 输出）
            date_str: 日期字符串
            raw_md_path: 关联的原始 MD 文件路径

        Returns:
            保存的文件路径（成功）或 None（失败）
        """
        try:
            date_dir = self._get_date_directory(date_str)

            # 添加原始文件路径关联
            if raw_md_path:
                result["raw_source_md_path"] = raw_md_path

            # 生成文件名（使用 source_url）
            source_url = result.get("source_url", "unknown")
            filename = self._generate_filename(source_url)
            file_path = date_dir / filename

            # 写入 JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.debug(
                f"[processed_result_manager] 保存单文档结果：{file_path} (source: {source_url})"
            )
            return str(file_path)

        except Exception as e:
            logger.error(f"[processed_result_manager] 保存单文档结果失败：{e}")
            return None

    def save_batch_summary(
        self,
        results: List[Dict[str, Any]],
        date_str: Optional[str] = None,
    ) -> Optional[str]:
        """
        保存批次汇总统计

        Args:
            results: 处理结果列表
            date_str: 日期字符串

        Returns:
            保存的文件路径（成功）或 None（失败）
        """
        try:
            date_dir = self._get_date_directory(date_str)

            # 统计信息
            success_count = sum(1 for r in results if r.get("status") == "success")
            failed_count = len(results) - success_count

            # 汇总结构
            summary = {
                "batch_time": datetime.now().isoformat(),
                "date": date_str or datetime.now().strftime("%Y-%m-%d"),
                "total_count": len(results),
                "success_count": success_count,
                "failed_count": failed_count,
                "documents": [],
            }

            # 添加每个文档的摘要信息
            for result in results:
                doc_summary = {
                    "document_index": result.get("document_index"),
                    "source_url": result.get("source_url", "unknown"),
                    "status": result.get("status"),
                    "chunk_count": result.get("metadata", {}).get("chunk_count", 0)
                    if result.get("status") == "success"
                    else 0,
                    "word_count": result.get("metadata", {}).get("word_count", 0)
                    if result.get("status") == "success"
                    else 0,
                    "error": result.get("error", ""),
                }
                summary["documents"].append(doc_summary)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_{timestamp}_summary.json"
            file_path = date_dir / filename

            # 写入 JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            logger.info(
                f"[processed_result_manager] 保存批次汇总：{file_path} "
                f"(总数：{len(results)}, 成功：{success_count}, 失败：{failed_count})"
            )
            return str(file_path)

        except Exception as e:
            logger.error(f"[processed_result_manager] 保存批次汇总失败：{e}")
            return None

    def save_batch_results(
        self,
        results: List[Dict[str, Any]],
        raw_md_paths: Optional[List[str]] = None,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        保存批次全部结果（单文档 + 汇总）

        Args:
            results: 处理结果列表
            raw_md_paths: 原始 MD 文件路径列表（可选）
            date_str: 日期字符串

        Returns:
            {
                "saved_count": 成功保存数量，
                "failed_count": 失败数量，
                "summary_path": 汇总文件路径，
                "file_paths": 单文档文件路径列表
            }
        """
        saved_count = 0
        failed_count = 0
        file_paths = []

        for idx, result in enumerate(results):
            raw_md_path = raw_md_paths[idx] if raw_md_paths and idx < len(raw_md_paths) else None

            file_path = self.save_single_result(
                result=result,
                date_str=date_str,
                raw_md_path=raw_md_path,
            )

            if file_path:
                saved_count += 1
                file_paths.append(file_path)
            else:
                failed_count += 1

        # 保存汇总
        summary_path = self.save_batch_summary(results, date_str)

        return {
            "saved_count": saved_count,
            "failed_count": failed_count,
            "summary_path": summary_path,
            "file_paths": file_paths,
        }

    def get_date_dirs(self) -> List[Path]:
        """获取所有日期目录"""
        dirs = []
        if self.base_path.exists():
            for item in self.base_path.iterdir():
                if item.is_dir():
                    dirs.append(item)
        return sorted(dirs)

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        date_dirs = self.get_date_dirs()
        total_files = 0

        for date_dir in date_dirs:
            total_files += len(list(date_dir.glob("*.json")))

        return {
            "base_path": str(self.base_path),
            "date_dirs_count": len(date_dirs),
            "total_files": total_files,
        }
