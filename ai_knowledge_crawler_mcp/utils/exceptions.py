"""
分层自定义异常

异常层次结构：
- MCPBaseException (基类)
  ├─ ConfigValidateError (配置验证错误)
  ├─ BingSearchError (Bing 搜索错误)
  ├─ FetchError (网页抓取错误)
  └─ CrawlPipelineError (流水线执行错误)
"""


class MCPBaseException(Exception):
    """MCP 爬虫系统基类异常"""

    def __init__(self, message: str, details: dict = None):
        """
        Args:
            message: 异常消息
            details: 附加详细信息（可选）
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class ConfigValidateError(MCPBaseException):
    """配置验证异常"""

    def __init__(self, message: str, field_name: str = None, value: any = None):
        """
        Args:
            message: 异常消息
            field_name: 出错的配置字段名
            value: 非法值
        """
        details = {}
        if field_name:
            details["field"] = field_name
        if value is not None:
            details["value"] = value
        super().__init__(message, details)


class BingSearchError(MCPBaseException):
    """Bing 搜索相关异常"""

    class Timeout(MCPBaseException):
        """搜索超时异常"""
        pass

    class ConnectionFailed(MCPBaseException):
        """连接失败异常"""
        pass

    class InvalidResponse(MCPBaseException):
        """响应格式异常"""
        pass

    class RateLimit(MCPBaseException):
        """触发限流异常"""
        pass

    class NoResults(MCPBaseException):
        """无搜索结果异常"""
        pass


class FetchError(MCPBaseException):
    """网页抓取相关异常"""

    class Timeout(MCPBaseException):
        """抓取超时异常"""
        pass

    class ConnectionFailed(MCPBaseException):
        """连接失败异常"""
        pass

    class InvalidContent(MCPBaseException):
        """内容格式异常"""
        pass

    class RateLimit(MCPBaseException):
        """触发限流异常"""
        pass

    class MaxRetriesExceeded(MCPBaseException):
        """超过最大重试次数"""
        pass


class CrawlPipelineError(MCPBaseException):
    """流水线执行异常"""

    class SearchPhaseError(MCPBaseException):
        """搜索阶段错误"""
        pass

    class FilterPhaseError(MCPBaseException):
        """过滤阶段错误"""
        pass

    class FetchPhaseError(MCPBaseException):
        """抓取阶段错误"""
        pass

    class SavePhaseError(MCPBaseException):
        """保存阶段错误"""
        pass

    class HealthCheckFailed(MCPBaseException):
        """健康检测失败"""
        pass
