# 需求文档

> 最后更新：2026-06-25

---

## 2026-06-25 MCP 客户端统一改造需求

### 1. 改造背景

项目原使用 `mcp.client.http` 模块实现本地 HTTP MCP 客户端，但该模块在当前环境中不存在（`ModuleNotFoundError: No module named 'mcp.client.http'`），导致沙箱环境版本兼容问题。

同时，项目需要接入 ModelScope 云端 streamable_http Fetch 服务，原架构无法统一处理本地 HTTP 和云端流式传输两种协议。

### 2. 改造目标

1. **移除不兼容依赖**：彻底移除 `HttpMCPClient` 和 `mcp.client.http` 导入，解决版本兼容问题
2. **统一客户端实现**：全局仅保留一套 `FastMCPClient`，基于 `fastmcp.Client`
3. **双协议兼容**：同时支持本地 streamable-http 和云端 streamable_http 两种传输协议
4. **向后兼容**：保持全局单例名称不变，上层业务代码无需修改

### 3. 功能需求

#### 3.1 FastMCPClient 功能规格

| 功能 | 说明 | 参数/返回值 |
|------|------|-------------|
| `__init__` | 初始化客户端 | `base_url: str`, `timeout: int = 50` |
| `call_tool` | 调用 MCP 工具 | `tool_name: str`, `arguments: dict` → `Any` |
| `read_resource` | 读取 MCP 资源 | `resource_uri: str` → `str \| None` |

#### 3.2 协议适配要求

| 服务类型 | 地址格式 | 传输协议 | 客户端实例 |
|----------|----------|----------|------------|
| 本地 MCP | `http://127.0.0.1:801x/mcp` | streamable-http | 全局单例（file/llm/search/email/render） |
| 云端 Fetch | `https://mcp.api-inference.modelscope.net/xxx/mcp` | streamable_http | FetchAdapter 单独实例化 |

#### 3.3 全局单例定义

| 单例名称 | 服务类型 | 地址 | 超时 |
|----------|----------|------|------|
| `file_mcp_client` | 文件服务 | `http://127.0.0.1:8011/mcp` | 50s |
| `llm_mcp_client` | LLM 服务 | `http://127.0.0.1:8012/mcp` | 180s |
| `search_mcp_client` | 搜索服务 | `http://127.0.0.1:8014/mcp` | 50s |
| `email_mcp_client` | 邮件服务 | `http://127.0.0.1:8010/mcp` | 50s |
| `render_mcp_client` | 渲染服务（已废弃） | `http://127.0.0.1:8013/mcp` | 50s |

**注意**：`render_mcp_client` 对应本地 8013 Fetch 服务，已迁移到云端，保留单例但不再使用。

### 4. FetchAdapter 适配需求

#### 4.1 云端 Fetch 服务信息

| 配置项 | 值 |
|--------|-----|
| 传输类型 | streamable_http |
| 服务地址 | `https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp` |
| 工具名称 | `fetch` |
| 超时时间 | 120 秒 |

#### 4.2 工具标准入参

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `url` | str | 是 | - | 目标 URL |
| `max_length` | int | 否 | 5000 | 最大返回内容长度（tokens） |
| `start_index` | int | 否 | 0 | 起始索引 |
| `raw` | bool | 否 | False | 是否返回原始内容 |

#### 4.3 已删除参数

- `render_js`: 云端服务不支持此参数，全部删除相关逻辑

#### 4.4 新增功能

- `health_check()`: 健康探测方法，提前校验云端服务连通状态

### 5. 配置变更需求

#### 5.1 config/settings.py 变更

| 删除配置 | 新增配置 |
|----------|----------|
| `FETCH_MCP_URL` (本地 8013) | `FETCH_MCP_STREAM_URL` (云端地址) |
| `FETCH_TIMEOUT` | `FETCH_MCP_TIMEOUT = 120` |

#### 5.2 路径类型变更

- `PROJECT_ROOT`: `str` → `Path`
- `RAW_SOURCE_MD_PATH`: `str` → `Path`
- `PROCESSED_KNOWLEDGE_PATH`: `str` → `Path`
- `RAG_EXPORT_PATH`: `str` → `Path`
- `LOGS_PATH`: `str` → `Path`

### 6. 功能边界

| 包含 | 不包含 |
|------|--------|
| MCP 客户端统一改造 | 文本清洗分片逻辑 |
| FetchAdapter 云端适配 | 定时调度逻辑 |
| CrawlPipeline 健康检测 | RAG 导出逻辑 |
| 连通性测试脚本 | 其他 MCP 服务改造 |

### 7. 验收标准

1. 所有模块导入无报错
2. 本地 MCP 单例正常实例化
3. Fetch 云端服务连通性测试通过
4. CrawlPipeline 初始化成功
5. 上层业务代码无需修改

---

*文档自动归档，最后更新：2026-06-25*
