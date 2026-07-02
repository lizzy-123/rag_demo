"""文档处理基础类 - 统一结果格式化和公共能力"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..utils.exceptions import MCPBaseException
from ..utils.logger import get_child_logger


logger = get_child_logger("base_processor")


class DocumentProcessorError(MCPBaseException):
    """文档处理相关异常"""

    class InvalidInput(MCPBaseException):
        """输入格式异常"""
        pass

    class ProcessingFailed(MCPBaseException):
        """处理失败异常"""
        pass

    class ValidationError(MCPBaseException):
        """参数验证异常"""
        pass


class BaseProcessor(ABC):
    """文档处理基础父类 - 提供统一结果格式化"""

    def __init__(self, name: str = "base"):
        """
        Args:
            name: 处理器名称，用于日志前缀
        """
        self.name = name
        self._logger = get_child_logger(f"document_processor.{name}")

    def _validate_positive_int(
        self,
        value: int,
        param_name: str,
        min_value: int = 1,
        max_value: Optional[int] = None,
    ) -> None:
        """
        验证正整数参数（复用通用校验）

        Args:
            value: 待验证值
            param_name: 参数名称
            min_value: 最小值（包含）
            max_value: 最大值（包含，可选）

        Raises:
            DocumentProcessorError.ValidationError: 参数越界
        """
        if value < min_value:
            raise DocumentProcessorError.ValidationError(
                f"{param_name} 必须大于等于 {min_value}",
                details={"param": param_name, "value": value, "min": min_value},
            )
        if max_value is not None and value > max_value:
            raise DocumentProcessorError.ValidationError(
                f"{param_name} 必须小于等于 {max_value}",
                details={"param": param_name, "value": value, "max": max_value},
            )

    def _validate_non_negative_int(
        self,
        value: int,
        param_name: str,
        max_value: Optional[int] = None,
    ) -> None:
        """
        验证非负整数参数

        Args:
            value: 待验证值
            param_name: 参数名称
            max_value: 最大值（包含，可选）

        Raises:
            DocumentProcessorError.ValidationError: 参数越界
        """
        if value < 0:
            raise DocumentProcessorError.ValidationError(
                f"{param_name} 必须大于等于 0",
                details={"param": param_name, "value": value},
            )
        if max_value is not None and value > max_value:
            raise DocumentProcessorError.ValidationError(
                f"{param_name} 必须小于等于 {max_value}",
                details={"param": param_name, "value": value, "max": max_value},
            )

    def _format_success_result(
        self,
        cleaned_markdown: str,
        chunks: list[Dict[str, Any]],
        metadata: Dict[str, Any],
        dedup_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        格式化成功返回结果（统一结构）

        Args:
            cleaned_markdown: 清洗后的完整 Markdown
            chunks: 分片列表
            metadata: 元数据
            dedup_info: 去重信息（可选）

        Returns:
            标准化成功结果字典
        """
        result = {
            "status": "success",
            "cleaned_markdown": cleaned_markdown,
            "chunks": chunks,
            "metadata": metadata,
        }
        if dedup_info is not None:
            result["dedup_info"] = dedup_info
        return result

    def _format_failed_result(
        self,
        error: str,
        document_index: Optional[int] = None,
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        格式化失败返回结果（统一结构）

        Args:
            error: 错误信息
            document_index: 文档索引（批量处理时）
            source_url: 源 URL

        Returns:
            标准化失败结果字典
        """
        result = {"status": "failed", "error": error}
        if document_index is not None:
            result["document_index"] = document_index
        if source_url is not None:
            result["source_url"] = source_url
        return result

    def _log_process_start(self, action: str, context: Optional[str] = None) -> None:
        """
        记录处理开始日志

        Args:
            action: 操作描述
            context: 上下文信息（可选）
        """
        msg = f"[{self.name}] 开始{action}"
        if context:
            msg += f" - {context}"
        self._logger.info(msg)

    def _log_process_complete(self, action: str, count: int = 0) -> None:
        """
        记录处理完成日志

        Args:
            action: 操作描述
            count: 处理数量
        """
        msg = f"[{self.name}] 完成{action}"
        if count > 0:
            msg += f"，数量：{count}"
        self._logger.info(msg)

    def _log_error(self, action: str, error: Exception) -> None:
        """
        记录错误日志

        Args:
            action: 操作描述
            error: 异常对象
        """
        self._logger.error(f"[{self.name}] {action}失败：{error}")

    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """抽象方法 - 由子类实现具体处理逻辑"""
        pass
