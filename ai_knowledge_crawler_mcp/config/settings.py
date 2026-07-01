"""
全局配置类

包含定时间隔、分片长度、搜索关键词、黑名单域名等配置。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from ..utils import ConfigValidateError


@dataclass
class CrawlerConfig:
    """爬虫全局配置"""

    # ========== 搜索关键词配置 ==========
    # AI 技术分类关键词
    # SEARCH_KEYWORDS: List[str] = field(
    #     default_factory=lambda: ["AI应用开发","Claude code 技巧","RAG", "大模型基础", "Multi-Agent 智能体", "Vibe Coding", "大模型评测"]
    # )
    SEARCH_KEYWORDS: List[str] = field(
        default_factory=lambda: ["AI应用开发"]
    )

    # 英文素材关键词（可选扩展）
    ENGLISH_KEYWORDS: List[str] = field(
        default_factory=lambda: ["LLM RAG", "Multi-Agent Systems", "LangChain", "Vector Database"]
    )

    # ========== 定时任务配置 ==========
    # 定时间隔（小时）
    SCHEDULE_INTERVAL_HOURS: int = 24

    # ========== 分片配置 ==========
    # 分片 token 长度
    CHUNK_SIZE: int = 800

    # 分片重叠长度
    CHUNK_OVERLAP: int = 150

    # ========== 去重配置 ==========
    # 相似度阈值（0-1）
    SIMILARITY_THRESHOLD: float = 0.85

    # ========== 黑名单配置 ==========
    # 黑名单域名
    BLACKLIST_DOMAINS: List[str] = field(
        default_factory=lambda: ["ad.example.com", "spam.example.com"]
    )

    # ========== MCP 服务地址配置 ==========
    # 必应搜索 MCP 云端服务（streamable_http 协议）
    # 注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址
    # 当前有效地址：https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp
    BING_SEARCH_MCP_STREAM_URL: str = "https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp"

    # 云端 Bing MCP 超时时间（秒）
    BING_MCP_TIMEOUT: int = 120

    # Fetch MCP 云端服务（streamable_http 协议）
    # 注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址
    # 当前有效地址：https://mcp.api-inference.modelscope.net/61670935bda94d/mcp
    FETCH_MCP_STREAM_URL: str = "https://mcp.api-inference.modelscope.net/955c976957164d/mcp"

    # 文档处理 MCP（LLM）
    DOC_PROCESSOR_MCP_URL: str = "http://127.0.0.1:8012/mcp"

    # ========== 抓取配置 ==========
    # 云端 Fetch MCP 超时时间（秒）
    FETCH_MCP_TIMEOUT: int = 300

    # 失败重试次数 2 
    RETRY_COUNT: int = 1

    # 抓取并发数（异步并发控制），5避免批量并发压垮MCP
    FETCH_CONCURRENT_LIMIT: int = 1

    # MCP 请求间隔（秒，防限流）0.5
    MCP_REQUEST_INTERVAL: float = 30

    # ========== 日志配置 ==========
    # 日志级别
    LOG_LEVEL: str = "INFO"

    # ========== 路径配置 ==========
    # 项目根路径（自动计算）
    PROJECT_ROOT: Path = field(default=None, init=False)

    # 原始 MD 存储路径
    RAW_SOURCE_MD_PATH: Path = field(default=None, init=False)

    # 处理后知识库路径
    PROCESSED_KNOWLEDGE_PATH: Path = field(default=None, init=False)

    # RAG 导出路径
    RAG_EXPORT_PATH: Path = field(default=None, init=False)

    # 日志路径
    LOGS_PATH: Path = field(default=None, init=False)

    # 失败 URL 池路径
    FAILED_URLS_POOL_PATH: Path = field(default=None, init=False)

    def __post_init__(self):
        """初始化后自动计算路径并校验配置"""
        # 计算项目根路径
        self.PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

        # 计算相对路径
        self.RAW_SOURCE_MD_PATH = self.PROJECT_ROOT / "ai_knowledge_crawler_mcp" / "raw_source_md"
        self.PROCESSED_KNOWLEDGE_PATH = self.PROJECT_ROOT / "ai_knowledge_crawler_mcp" / "processed_knowledge"
        self.RAG_EXPORT_PATH = self.PROJECT_ROOT / "ai_knowledge_crawler_mcp" / "rag_export"
        self.LOGS_PATH = self.PROJECT_ROOT / "ai_knowledge_crawler_mcp" / "logs"
        self.FAILED_URLS_POOL_PATH = self.PROJECT_ROOT / "crawl_task_data" / "failed_urls.json"

        # 校验配置
        self._validate_config()

    def _validate_config(self):
        """校验配置合法性"""
        # 校验定时间隔
        if self.SCHEDULE_INTERVAL_HOURS < 1:
            raise ConfigValidateError(
                "SCHEDULE_INTERVAL_HOURS 必须大于 0",
                field_name="SCHEDULE_INTERVAL_HOURS",
                value=self.SCHEDULE_INTERVAL_HOURS
            )

        # 校验分片配置
        if self.CHUNK_SIZE < 100:
            raise ConfigValidateError(
                "CHUNK_SIZE 必须大于等于 100",
                field_name="CHUNK_SIZE",
                value=self.CHUNK_SIZE
            )

        if self.CHUNK_OVERLAP < 0 or self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ConfigValidateError(
                "CHUNK_OVERLAP 必须在 0 到 CHUNK_SIZE 之间",
                field_name="CHUNK_OVERLAP",
                value=self.CHUNK_OVERLAP
            )

        # 校验相似度阈值
        if not 0 < self.SIMILARITY_THRESHOLD <= 1:
            raise ConfigValidateError(
                "SIMILARITY_THRESHOLD 必须在 (0, 1] 范围内",
                field_name="SIMILARITY_THRESHOLD",
                value=self.SIMILARITY_THRESHOLD
            )

        # 校验超时时间
        if self.BING_MCP_TIMEOUT < 10:
            raise ConfigValidateError(
                "BING_MCP_TIMEOUT 必须大于等于 10 秒",
                field_name="BING_MCP_TIMEOUT",
                value=self.BING_MCP_TIMEOUT
            )

        if self.FETCH_MCP_TIMEOUT < 10:
            raise ConfigValidateError(
                "FETCH_MCP_TIMEOUT 必须大于等于 10 秒",
                field_name="FETCH_MCP_TIMEOUT",
                value=self.FETCH_MCP_TIMEOUT
            )

        # 校验重试次数
        if self.RETRY_COUNT < 0:
            raise ConfigValidateError(
                "RETRY_COUNT 不能为负数",
                field_name="RETRY_COUNT",
                value=self.RETRY_COUNT
            )

        # 校验抓取并发数
        if self.FETCH_CONCURRENT_LIMIT < 1:
            raise ConfigValidateError(
                "FETCH_CONCURRENT_LIMIT 必须大于等于 1",
                field_name="FETCH_CONCURRENT_LIMIT",
                value=self.FETCH_CONCURRENT_LIMIT
            )

        # 校验 MCP 请求间隔
        if self.MCP_REQUEST_INTERVAL < 0:
            raise ConfigValidateError(
                "MCP_REQUEST_INTERVAL 不能为负数",
                field_name="MCP_REQUEST_INTERVAL",
                value=self.MCP_REQUEST_INTERVAL
            )

        # 校验日志级别
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            raise ConfigValidateError(
                f"LOG_LEVEL 必须是以下之一：{valid_log_levels}",
                field_name="LOG_LEVEL",
                value=self.LOG_LEVEL
            )

        # 校验关键词
        if not self.SEARCH_KEYWORDS:
            raise ConfigValidateError(
                "SEARCH_KEYWORDS 不能为空",
                field_name="SEARCH_KEYWORDS",
                value=self.SEARCH_KEYWORDS
            )

        # 校验 MCP 服务地址
        if not self.BING_SEARCH_MCP_STREAM_URL.startswith(("http://", "https://")):
            raise ConfigValidateError(
                "BING_SEARCH_MCP_STREAM_URL 必须是有效的 HTTP/HTTPS 地址",
                field_name="BING_SEARCH_MCP_STREAM_URL",
                value=self.BING_SEARCH_MCP_STREAM_URL
            )

        if not self.FETCH_MCP_STREAM_URL.startswith(("http://", "https://")):
            raise ConfigValidateError(
                "FETCH_MCP_STREAM_URL 必须是有效的 HTTP/HTTPS 地址",
                field_name="FETCH_MCP_STREAM_URL",
                value=self.FETCH_MCP_STREAM_URL
            )
