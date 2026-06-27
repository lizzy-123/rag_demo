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
| `render_mcp_client` | 渲染服务 | `http://127.0.0.1:8013/mcp` | 50s |



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

## 2026-06-26 Bing 云端 MCP 迁移需求

### 1. 改造背景

原 Bing 搜索 MCP 使用本地部署服务（`http://127.0.0.1:8014/mcp`），需要迁移至 ModelScope 云端 streamable_http 服务，与 Fetch 改造方案对齐。

### 2. 改造目标

1. **不改动 `mcp_client.py`**: 保持现有统一 `FastMCPClient` 逻辑不变
2. **Bing 适配器云端化**: 实例化 `FastMCPClient`，读取配置内云端地址
3. **删除本地依赖**: 移除所有 `127.0.0.1:8090` 和 `127.0.0.1:8014` 硬编码地址
4. **健康检测**: 在采集流水线中增加 Bing 云端服务健康检测
5. **配置更新**: 新增云端 Bing MCP 地址和超时配置项

### 3. 云端 Bing MCP 服务配置

```json
{
  "mcpServers": {
    "bing-cn-mcp-server": {
      "type": "streamable_http",
      "url": "https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp"
    }
  }
}
```

### 4. 功能需求

#### 4.1 云端 Bing 服务信息

| 配置项 | 值 |
|--------|-----|
| 传输类型 | streamable_http |
| 服务地址 | `https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp` |
| 工具名称 | `bing_search` |
| 超时时间 | 120 秒 |

#### 4.2 BingSearchAdapter 改造

| 改造项 | 旧实现 | 新实现 |
|--------|--------|--------|
| 初始化参数 | `base_url, timeout` | `config: CrawlerConfig` |
| 默认地址 | `http://127.0.0.1:8090/mcp` | 从 config 读取 `BING_SEARCH_MCP_STREAM_URL` |
| 超时配置 | 固定 60 秒 | 从 config 读取 `BING_MCP_TIMEOUT` |

---

## 2026-06-26 Bing search 参数规范调整

### 1. 调整背景

对齐 `bing_search` MCP 工具标准参数规范，明确必填/可选参数定义及边界约束。

### 2. 参数规范

#### 2.1 MCP 工具参数定义

| 参数名 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|--------|------|------|--------|------|------|
| `query` | str | 是 | - | - | 搜索关键词字符串 |
| `count` | int | 否 | 10 | 1 ≤ count ≤ 50 | 返回条数 |
| `offset` | int | 否 | 0 | offset ≥ 0 | 翻页偏移 |

#### 2.2 Adapter 层参数映射

| Adapter 参数 | MCP 参数 | 转换逻辑 |
|--------------|----------|----------|
| `keywords` (List[str]) | `query` (str) | `", ".join(keywords)` |
| `count` (int) | `count` (int) | 直接传递 |
| `offset` (int) | `offset` (int) | 直接传递 |

#### 2.3 边界校验规则

```python
if count < 1 or count > 50:
    raise ValueError(f"count 参数必须在 1-50 之间")
if offset < 0:
    raise ValueError(f"offset 参数不能为负数")
```

### 3. 验收标准

1. 参数边界校验生效（count>50 或 offset<0 抛出异常）
2. `keywords` 列表正确转换为 `query` 字符串
3. 默认值正确（count=10, offset=0）
4. 原有结果格式化逻辑不变
5. CrawlPipeline 调用无改动

---

*文档自动归档，最后更新：2026-06-26*
| 健康检测 | 无 | 新增 `health_check()` 方法 |

#### 4.3 配置新增项

| 配置名 | 类型 | 值 | 说明 |
|--------|------|-----|------|
| `BING_SEARCH_MCP_STREAM_URL` | str | `https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp` | 云端 Bing MCP 地址 |
| `BING_MCP_TIMEOUT` | int | `120` | 云端 Bing MCP 超时时间 |

#### 4.4 删除内容

- `BING_SEARCH_MCP_URL` (本地 8014 地址)
- 所有本地 8090 端口相关硬编码
- 本地 Bing MCP 启动相关逻辑和注释

### 5. 验收标准

1. 模块导入无报错
2. `BingSearchAdapter` 使用云端地址
3. `CrawlPipeline` 初始化成功
4. Bing 健康检测功能正常
5. `mcp_client.py` 无任何修改
6. 本地 8090/8014 端口不再依赖

---

*文档自动归档，最后更新：2026-06-26*
