# AI 知识库 MCP 采集预处理模块

## 模块概述

AI 知识库 MCP 采集预处理模块是一个基于 MCP (Model Context Protocol) 协议的自动化知识采集系统。该模块通过复用项目原有的 `FastMCPClient` 通信层，封装必应搜索、网页抓取、文档处理等 MCP 服务，实现 AI 技术资料的自动化采集、清洗、去重、分片、分类打标签，最终导出为 RAG 系统可消费的结构化数据。

## 目录结构

```
ai_knowledge_crawler_mcp/
├── entry.py                          # 统一入口：手动单次执行 / 后台定时循环执行
├── config/                           # 配置模块
│   ├── __init__.py                   # 导出 CrawlerConfig
│   └── settings.py                   # 全局配置类：定时间隔、分片长度、搜索关键词、黑名单域名等
├── crawl_task/                       # 任务调度模块
│   └── __init__.py                   # 任务调度、定时逻辑、关键词管理、流程编排 (待实现)
├── mcp_client_adapter/               # MCP 客户端适配层
│   ├── __init__.py                   # 导出 BingSearchAdapter, FetchAdapter, DocProcessorAdapter
│   ├── base_adapter.py               # 基础适配器：封装 FastMCPClient 通用调用逻辑
│   ├── bing_search_adapter.py        # 必应搜索适配器：分领域批量搜索 AI 技术关键词
│   ├── fetch_adapter.py              # 网页抓取适配器：批量抓取网页并输出纯净 Markdown
│   └── doc_processor_adapter.py      # 文档处理适配器：文本清洗、去重、分片、分类打标签
├── rag_export/                       # RAG 对接层
│   └── __init__.py                   # 分片结构化 JSON → LangChain Document 转换 (待实现)
├── raw_source_md/                    # 原始 Markdown 存储目录 (运行时生成)
├── processed_knowledge/              # 处理后知识库目录 (运行时生成)
├── rag_export/                       # RAG 导出目录 (运行时生成)
└── logs/                             # 日志目录 (运行时生成)
```

## 核心文件功能说明

### 1. entry.py - 统一入口

**功能**: 模块启动入口，支持手动单次执行和后台定时循环执行两种模式。

**当前状态**: 基础框架已创建，待实现抓取、清洗、定时、RAG 导出逻辑。

```python
def main():
    """入口函数 - 待实现抓取、清洗、定时、RAG 导出逻辑"""
    logger.info("AI Knowledge Crawler MCP Module Started")
```

---

### 2. config/settings.py - 全局配置类

**功能**: 定义爬虫模块的所有可配置参数，使用 `dataclass` 实现集中管理。

**核心配置项**:

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SEARCH_KEYWORDS` | `["RAG", "大模型基础", "Multi-Agent 智能体", "Vibe Coding", "大模型评测"]` | AI 技术分类关键词 |
| `ENGLISH_KEYWORDS` | `["LLM RAG", "Multi-Agent Systems", "LangChain", "Vector Database"]` | 英文素材关键词 |
| `SCHEDULE_INTERVAL_HOURS` | `24` | 定时间隔（小时） |
| `CHUNK_SIZE` | `800` | 分片 token 长度 |
| `CHUNK_OVERLAP` | `150` | 分片重叠长度 |
| `SIMILARITY_THRESHOLD` | `0.85` | 去重相似度阈值（0-1） |
| `BLACKLIST_DOMAINS` | `["ad.example.com", "spam.example.com"]` | 黑名单域名 |
| `BING_SEARCH_MCP_URL` | `http://127.0.0.1:8014/mcp` | 必应搜索 MCP 地址 |
| `FETCH_MCP_URL` | `http://127.0.0.1:8013/mcp` | Fetch MCP 地址 |
| `DOC_PROCESSOR_MCP_URL` | `http://127.0.0.1:8012/mcp` | 文档处理 MCP 地址 |
| `FETCH_TIMEOUT` | `120` | 抓取超时时间（秒） |
| `RETRY_COUNT` | `2` | 失败重试次数 |
| `MAX_URLS_PER_RUN` | `50` | 单次最大抓取 URL 数量 |

---

### 3. mcp_client_adapter/base_adapter.py - MCP 适配器基类

**功能**: 封装 `FastMCPClient` 的通用调用逻辑，为所有 MCP 适配器提供统一基础。

**复用验证**: ✅ 已成功复用项目原有 `multi_agent/agent/mcp_client.py` 中的 `FastMCPClient`

```python
# 添加项目根路径到 sys.path，导入 FastMCPClient
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.agent.mcp_client import FastMCPClient
```

**核心方法**:

| 方法 | 功能 |
|------|------|
| `__init__(base_url, timeout, adapter_name)` | 初始化 MCP 适配器，创建 FastMCPClient 实例 |
| `call_tool(tool_name, arguments)` | 调用 MCP 工具，自动解析 JSON 或返回原始文本 |
| `read_resource(resource_uri)` | 读取 MCP 资源（如模板） |

**异常处理**:
- `TimeoutError`: 工具调用超时
- 通用异常捕获与日志记录

---

### 4. mcp_client_adapter/bing_search_adapter.py - 必应搜索适配器

**功能**: 封装必应搜索 MCP 服务，用于分领域批量搜索 AI 技术关键词。

**核心方法**:

```python
# 批量搜索 AI 技术关键词
async def search_keywords(
    keywords: List[str],
    days: Optional[int] = None,        # 限定近 N 天增量内容
    category: Optional[str] = None,    # 搜索分类（如 "tech", "news"）
    exclude_urls: Optional[List[str]] = None  # 排除已抓取链接
) -> Dict[str, Any]

# 搜索单个关键词
async def search_single_keyword(
    keyword: str,
    days: Optional[int] = None,
    limit: int = 10
) -> List[Dict[str, Any]]
```

**返回格式**:
```json
{
  "results": [
    {
      "title": "文章标题",
      "url": "原文链接",
      "published_date": "发布时间",
      "snippet": "摘要"
    }
  ],
  "total": 总数，
  "filtered_count": 过滤后的数量
}
```

---

### 5. mcp_client_adapter/fetch_adapter.py - 网页抓取适配器

**功能**: 封装 Fetch MCP 服务，用于批量抓取网页并输出纯净 Markdown 原文。

**核心方法**:

```python
# 抓取单个 URL 并转换为 Markdown
async def fetch_url(
    url: str,
    render_js: bool = False   # 是否需要渲染 JavaScript 动态内容
) -> Dict[str, Any]

# 批量抓取 URL 列表（带重试）
async def fetch_urls_batch(
    urls: List[str],
    render_js: bool = False,
    retry_count: int = 2
) -> List[Dict[str, Any]]

# 抓取单个 URL，带重试逻辑
async def fetch_single_with_retry(
    url: str,
    render_js: bool = False,
    retry_count: int = 2
) -> Optional[Dict[str, Any]]
```

**返回格式**:
```json
{
  "url": "原始 URL",
  "markdown": "纯净 Markdown 原文",
  "title": "页面标题",
  "status": "success|failed",
  "error": "错误信息（如果失败）",
  "retry_count": 实际重试次数
}
```

**特性**:
- 自动重试机制（默认 2 次）
- 支持 JavaScript 渲染（用于动态内容网站）
- 失败结果记录与错误追踪

---

### 6. mcp_client_adapter/doc_processor_adapter.py - 文档处理适配器

**功能**: 封装智能体文档处理 MCP 服务，用于批量执行文本清洗、去重、分片、分类打标签。

**核心方法**:

```python
# 处理单个文档：清洗、去重、分片、分类
async def process_document(
    markdown_content: str,
    source_url: Optional[str] = None,
    tech_category: Optional[str] = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> Dict[str, Any]

# 批量处理文档列表
async def process_documents_batch(
    documents: List[Dict[str, str]],
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[Dict[str, Any]]

# 仅执行文本清洗（不执行分片）
async def clean_text(text: str) -> Dict[str, Any]

# 执行分片去重
async def deduplicate_chunks(
    chunks: List[str],
    similarity_threshold: float = 0.85
) -> Dict[str, Any]

# 文档自动分类打标签
async def classify_document(
    text: str,
    available_categories: Optional[List[str]] = None
) -> Dict[str, Any]
```

**返回格式**:
```json
{
  "status": "success|failed",
  "cleaned_markdown": "清洗后的完整 Markdown",
  "chunks": [
    {
      "text": "分片文本",
      "start_index": 起始位置，
      "end_index": 结束位置
    }
  ],
  "metadata": {
    "title": "文章标题",
    "summary": "文章摘要",
    "source_url": "原文链接",
    "tech_tags": ["技术标签 1", "技术标签 2"],
    "crawl_time": "抓取时间",
    "word_count": 字数，
    "chunk_count": 分片数量
  },
  "dedup_info": {
    "full_text_hash": "全文哈希",
    "removed_duplicate_chunks": 移除的重复分片数量
  }
}
```

---

## FastMCPClient 复用验证

### 复用方式

本模块通过以下方式复用项目原有 `FastMCPClient`:

1. **路径注入**: 在 `base_adapter.py` 中动态添加项目根路径到 `sys.path`
2. **直接导入**: `from multi_agent.agent.mcp_client import FastMCPClient`
3. **零修改**: 所有 MCP 适配器仅封装业务参数，不重复实现 MCP 底层协议

### FastMCPClient 核心特性

```python
class FastMCPClient:
    """轻量级 HTTP MCP 客户端，每次调用创建临时连接，用完自动释放"""
    
    def __init__(self, base_url: str, timeout: int = 50):
        self.base_url = base_url
        self.timeout = timeout
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """每次调用创建临时连接，用完自动释放"""
        async with Client(self.base_url, timeout=self.timeout) as client:
            result = await client.call_tool(tool_name, arguments)
            # 自动 JSON 解析或返回原始文本
            ...
    
    async def read_resource(self, resource_uri: str):
        """读取 MCP 资源（如模板），返回文本内容"""
        ...
```

**优势**:
- ✅ **无状态设计**: 每次调用独立创建连接，无需维护长连接
- ✅ **自动资源释放**: 使用 `async with` 上下文管理器，连接自动关闭
- ✅ **自动 JSON 解析**: 智能识别返回内容类型，自动解析 JSON 或返回原始文本
- ✅ **超时控制**: 支持自定义超时时间，避免长时间阻塞

### 复用验证结果

| 验证项 | 结果 | 说明 |
|--------|------|------|
| 导入成功 | ✅ | `from multi_agent.agent.mcp_client import FastMCPClient` 无错误 |
| 初始化成功 | ✅ | `FastMCPClient(base_url, timeout)` 创建成功 |
| 适配器继承 | ✅ | `MCPAdapterBase` 成功封装 `FastMCPClient` |
| 业务适配 | ✅ | 3 个业务适配器均基于 `MCPAdapterBase` 实现 |

---

## 待实现功能

### crawl_task/ - 任务调度模块

**待实现内容**:
- 任务调度逻辑
- 定时循环执行（基于 `SCHEDULE_INTERVAL_HOURS`）
- 关键词管理（动态增删改查）
- 流程编排：搜索 → 抓取 → 处理 → 导出

### rag_export/ - RAG 对接层

**待实现内容**:
- 分片结构化 JSON 转换为 LangChain `Document` 对象
- 兼容现有 `rag_main.py` 的文档格式
- 增量更新 FAISS 向量库

---

## 使用示例

### 1. 初始化配置

```python
from ai_knowledge_crawler_mcp.config import CrawlerConfig

config = CrawlerConfig()
print(config.SEARCH_KEYWORDS)  # ['RAG', '大模型基础', ...]
```

### 2. 使用必应搜索适配器

```python
from ai_knowledge_crawler_mcp.mcp_client_adapter import BingSearchAdapter

adapter = BingSearchAdapter()
results = await adapter.search_keywords(
    keywords=["RAG", "大模型基础"],
    days=7  # 近 7 天内容
)
```

### 3. 使用网页抓取适配器

```python
from ai_knowledge_crawler_mcp.mcp_client_adapter import FetchAdapter

adapter = FetchAdapter()
result = await adapter.fetch_url(
    url="https://example.com/article",
    render_js=False
)
print(result["markdown"])  # 纯净 Markdown 原文
```

### 4. 使用文档处理适配器

```python
from ai_knowledge_crawler_mcp.mcp_client_adapter import DocProcessorAdapter

adapter = DocProcessorAdapter()
result = await adapter.process_document(
    markdown_content=markdown_text,
    source_url="https://example.com/article",
    chunk_size=800,
    chunk_overlap=150
)
print(result["metadata"]["tech_tags"])  # ['RAG', '向量检索']
```

---

## 依赖的 MCP 服务

本模块依赖以下外部 MCP 服务（需提前启动）:

| 服务 | 默认地址 | 功能 |
|------|----------|------|
| 必应搜索 MCP | `http://127.0.0.1:8014/mcp` | 关键词搜索 |
| Fetch MCP | `http://127.0.0.1:8013/mcp` | 网页内容抓取 |
| 文档处理 MCP | `http://127.0.0.1:8012/mcp` | 文本清洗、分片、分类 |

---

## 开发计划

1. **Phase 1**: 完成 `crawl_task/` 任务调度逻辑
2. **Phase 2**: 完成 `rag_export/` RAG 对接层
3. **Phase 3**: 集成测试与性能优化
4. **Phase 4**: 文档完善与部署指南

---

## 许可证

与主项目保持一致。
