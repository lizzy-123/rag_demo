"""
全局配置类

包含定时间隔、分片长度、搜索关键词、黑名单域名等配置。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from typing import List


@dataclass
class CrawlerConfig:
    """爬虫全局配置"""

    # ========== 搜索关键词配置 ==========
    # AI 技术分类关键词
    SEARCH_KEYWORDS: List[str] = field(
        default_factory=lambda: ["RAG", "大模型基础", "Multi-Agent 智能体", "Vibe Coding", "大模型评测"]
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
    # 当前有效地址：https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp
    # FETCH_MCP_STREAM_URL: str = "https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp"
    FETCH_MCP_STREAM_URL: str = "https://mcp.api-inference.modelscope.net/61670935bda94d/mcp"

    # 文档处理 MCP（LLM）
    DOC_PROCESSOR_MCP_URL: str = "http://127.0.0.1:8012/mcp"

    # ========== 抓取配置 ==========
    # 云端 Fetch MCP 超时时间（秒）
    FETCH_MCP_TIMEOUT: int = 120

    # 失败重试次数
    RETRY_COUNT: int = 2

    # ========== 日志配置 ==========
    # 日志级别
    LOG_LEVEL: str = "INFO"

    # ========== 路径配置 ==========
    # 项目根路径（自动计算）
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

    # 原始 MD 存储路径
    RAW_SOURCE_MD_PATH: Path = Path("ai_knowledge_crawler_mcp/raw_source_md")

    # 处理后知识库路径
    PROCESSED_KNOWLEDGE_PATH: Path = Path("ai_knowledge_crawler_mcp/processed_knowledge")

    # RAG 导出路径
    RAG_EXPORT_PATH: Path = Path("ai_knowledge_crawler_mcp/rag_export")

    # 日志路径
    LOGS_PATH: Path = Path("ai_knowledge_crawler_mcp/logs")
