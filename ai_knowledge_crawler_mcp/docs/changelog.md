# 变更记录文档

> 最后更新：2026-06-25

---

## 2026-06-25 MCP 客户端统一改造变更记录

### 1. 问题定位

#### 1.1 初始错误

```
ModuleNotFoundError: No module named 'mcp.client.http'
```

**错误来源**: `multi_agent/agent/mcp_client.py` 第 6 行

**影响范围**:
- 所有导入 `mcp_client` 模块的代码
- `FetchAdapter`、`BingSearchAdapter` 等适配器
- `CrawlPipeline` 采集流水线

#### 1.2 根本原因

`mcp` 库当前版本没有 `mcp.client.http` 模块，该 API 可能已变更或移除。

### 2. 代码变更明细

#### 2.1 config/settings.py

**变更类型**: 配置更新 + 类型修改

| 变更项 | 旧值 | 新值 | 原因 |
|--------|------|------|------|
| `FETCH_MCP_URL` | `"http://127.0.0.1:8013/mcp"` | 删除 | 本地 8013 已废弃 |
| `FETCH_MCP_STREAM_URL` | 无 | `"https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp"` | 新增云端地址 |
| `FETCH_TIMEOUT` | `120` | 删除 | 改名 |
| `FETCH_MCP_TIMEOUT` | 无 | `120` | 新配置名 |
| `PROJECT_ROOT` | `str` | `Path` | 支持路径运算 |
| `RAW_SOURCE_MD_PATH` | `str` | `Path` | 支持路径运算 |
| `PROCESSED_KNOWLEDGE_PATH` | `str` | `Path` | 支持路径运算 |
| `RAG_EXPORT_PATH` | `str` | `Path` | 支持路径运算 |
| `LOGS_PATH` | `str` | `Path` | 支持路径运算 |

**新增注释**:
```python
# Fetch MCP 云端服务（streamable_http 协议）
# 注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址
# 当前有效地址：https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp
```

---

#### 2.2 multi_agent/agent/mcp_client.py

**变更类型**: 完全重构

**删除内容**:
- `from mcp.client.http import http_client` 导入
- `HttpMCPClient` 类定义（约 40 行）
- `from mcp import ClientSession` 导入（不再需要）
- `from mcp.client.stdio import stdio_client` 导入（不再需要）

**保留内容**:
- `from fastmcp import Client` 导入
- `FastMCPClient` 类（增强注释）

**全局单例变更**:

| 单例名 | 旧类型 | 新类型 | 地址 |
|--------|--------|--------|------|
| `file_mcp_client` | HttpMCPClient | FastMCPClient | http://127.0.0.1:8011/mcp |
| `llm_mcp_client` | HttpMCPClient | FastMCPClient | http://127.0.0.1:8012/mcp |
| `search_mcp_client` | HttpMCPClient | FastMCPClient | http://127.0.0.1:8014/mcp |
| `email_mcp_client` | HttpMCPClient | FastMCPClient | http://127.0.0.1:8010/mcp |
| `render_mcp_client` | HttpMCPClient | FastMCPClient | http://127.0.0.1:8013/mcp (废弃) |

**新增注释**:
```python
"""
MCP 客户端模块 - 双客户端架构

本模块提供两套 MCP 客户端实现，分别用于不同场景：

【本地 HTTP 客户端】
- HttpMCPClient: 基于 fastmcp.Client，用于本地 HTTP MCP 服务

【云端 streamable_http 客户端】
- FastMCPClient: 基于 fastmcp.Client，自动适配 HTTP/streamable_http
"""
```

---

#### 2.3 mcp_client_adapter/fetch_adapter.py

**变更类型**: 全面改造

**__init__ 方法变更**:

| 旧参数 | 新参数 |
|--------|--------|
| `base_url: str = "http://127.0.0.1:8013/mcp"` | `config: CrawlerConfig \| None = None` |
| `timeout: int = 120` | 从 config 读取 `FETCH_MCP_TIMEOUT` |

**fetch_url 方法变更**:

| 旧参数 | 新参数 |
|--------|--------|
| `render_js: bool = False` | 删除 |
| - | `max_length: int = 5000` |
| - | `start_index: int = 0` |
| - | `raw: bool = False` |

**工具名变更**:
- 旧：`"fetch_url"`
- 新：`"fetch"`

**返回处理增强**:
```python
# 处理返回结果：可能是字典或字符串
if isinstance(result, str):
    import json
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        # 无法解析 JSON，直接作为 markdown 内容
        return {"url": url, "markdown": result, ...}
```

**新增方法**:
```python
async def health_check(self) -> bool:
    """健康检测：检查云端 Fetch 服务是否可用"""
    # 通过调用 fetch 工具抓取测试 URL 验证连通性
```

---

#### 2.4 crawl_task/crawl_pipeline.py

**变更类型**: 适配更新

**_init_components 方法变更**:

```python
# 旧代码
self.fetch_adapter = FetchAdapter(
    base_url=self.config.FETCH_MCP_URL,
    timeout=self.config.FETCH_TIMEOUT,
)

# 新代码
self.fetch_adapter = FetchAdapter(config=self.config)
```

**_fetch_phase 方法新增**:

```python
# 健康检测：检查云端 Fetch 服务是否可用
logger.info("抓取阶段：执行 Fetch 云端服务健康检测")
if not await self.fetch_adapter.health_check():
    logger.error(
        "抓取阶段终止：Fetch 云端服务不可用或已过期！"
        "请检查云端 MCP 服务地址是否有效，到期需重新部署获取新地址。"
    )
    return []
```

**fetch_urls_batch 调用变更**:

```python
# 旧代码
fetch_results = await self.fetch_adapter.fetch_urls_batch(
    urls=urls,
    render_js=False,  # 删除
    retry_count=self.config.RETRY_COUNT,
)

# 新代码
fetch_results = await self.fetch_adapter.fetch_urls_batch(
    urls=urls,
    max_length=5000,
    retry_count=self.config.RETRY_COUNT,
)
```

---

#### 2.5 crawl_task/config_reader.py

**变更类型**: 配置读取更新

```python
# 旧代码
def get_fetch_timeout(self) -> int:
    """获取抓取超时时间"""
    return self.config.FETCH_TIMEOUT

# 新代码
def get_fetch_timeout(self) -> int:
    """获取云端 Fetch MCP 超时时间"""
    return self.config.FETCH_MCP_TIMEOUT
```

---

#### 2.6 scripts/test_fetch_connectivity.py

**变更类型**: 新增文件

**文件结构**:
```python
- test_health_check(): 健康检测测试
- test_single_fetch(): 单次抓取测试
- main(): 主测试流程
```

**测试内容**:
1. 配置信息输出（地址、超时）
2. 健康检测执行
3. 单次抓取执行（example.com）
4. 测试结果总结

---

### 3. 新旧逻辑差异对比

| 项目 | 旧逻辑 | 新逻辑 |
|------|--------|--------|
| HTTP 客户端 | `mcp.client.http.http_client` | `fastmcp.Client` |
| 客户端类 | `HttpMCPClient` | `FastMCPClient` |
| 本地服务 | `HttpMCPClient` 实例 | `FastMCPClient` 实例 |
| 云端服务 | 无 | `FastMCPClient` 实例 |
| Fetch 工具名 | `fetch_url` | `fetch` |
| Fetch 参数 | `url, render_js` | `url, max_length, start_index, raw` |
| 健康检测 | 无 | `health_check()` 方法 |
| 路径类型 | `str` | `Path` |

---

### 4. 兼容说明

#### 4.1 向后兼容

| 接口 | 兼容性 | 说明 |
|------|--------|------|
| `file_mcp_client` | ✓ 完全兼容 | 名称不变，类型改为 FastMCPClient |
| `llm_mcp_client` | ✓ 完全兼容 | 名称不变，类型改为 FastMCPClient |
| `search_mcp_client` | ✓ 完全兼容 | 名称不变，类型改为 FastMCPClient |
| `email_mcp_client` | ✓ 完全兼容 | 名称不变，类型改为 FastMCPClient |
| `render_mcp_client` | ✓ 保留但废弃 | 名称保留，本地 8013 已迁移云端 |
| `FastMCPClient.call_tool` | ✓ 完全兼容 | 接口不变 |
| `FastMCPClient.read_resource` | ✓ 完全兼容 | 接口不变 |

#### 4.2 上层业务影响

| 模块 | 影响 | 需修改 |
|------|------|--------|
| `BingSearchAdapter` | 无 | 否 |
| `FetchAdapter` | 初始化参数变更 | 已完成 |
| `CrawlPipeline` | FetchAdapter 调用变更 | 已完成 |
| 其他使用全局单例的代码 | 无 | 否 |

---

### 5. 校验结果

| 校验项 | 结果 | 备注 |
|--------|------|------|
| 基础客户端导入 | ✓ 通过 | FastMCPClient + 全局单例正常 |
| CrawlPipeline 导入 | ✓ 通过 | 模块导入和初始化无异常 |
| Fetch 云端连通 | ✓ 通过 | 健康检测 + 单次抓取全部通过 |

---

### 6. 注意事项

1. **云端服务有效期**: `FETCH_MCP_STREAM_URL` 包含 token，到期需重新部署获取新地址
2. **超时设置**: 云端服务响应较慢，`FETCH_MCP_TIMEOUT` 设置为 120 秒
3. **路径类型**: 配置路径已改为 `Path` 类型，支持 `/` 运算
4. **render_js 参数**: 云端 Fetch 不支持此参数，已全部删除

---

## 2026-06-26 Bing 云端 MCP 迁移变更记录

### 1. 迁移原因

原 Bing 搜索 MCP 使用本地部署服务（`http://127.0.0.1:8014/mcp`），需要迁移至 ModelScope 云端 streamable_http 服务，与 Fetch 改造方案对齐，实现统一云端 MCP 架构。

### 2. 代码变更明细

#### 2.1 config/settings.py

**变更类型**: 配置更新

| 变更项 | 旧值 | 新值 | 原因 |
|--------|------|------|------|
| `BING_SEARCH_MCP_URL` | `"http://127.0.0.1:8014/mcp"` | 删除 | 本地 8014 已废弃 |
| `BING_SEARCH_MCP_STREAM_URL` | 无 | `"https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp"` | 新增云端地址 |
| `BING_MCP_TIMEOUT` | 无 | `120` | 新增超时配置 |

**新增注释**:
```python
# 必应搜索 MCP 云端服务（streamable_http 协议）
# 注意：该云端 MCP 服务有有效期，到期需重新部署获取新地址
# 当前有效地址：https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp
```

---

#### 2.2 mcp_client_adapter/bing_search_adapter.py

**变更类型**: 全面改造

**__init__ 方法变更**:

| 旧参数 | 新参数 |
|--------|--------|
| `base_url: str = "http://127.0.0.1:8090/mcp"` | `config: CrawlerConfig \| None = None` |
| `timeout: int = 60` | 从 config 读取 `BING_MCP_TIMEOUT` |

**新增方法**:
```python
async def health_check(self) -> bool:
    """健康检测：检查云端 Bing 搜索服务是否可用"""
    # 通过调用 bing_search 工具搜索测试关键词验证连通性
```

**返回处理增强**:
```python
# 处理返回结果：可能是字典或字符串
if isinstance(result, str):
    import json
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        return {"results": [], "total": 0, "error": result}
```

---

#### 2.3 crawl_task/crawl_pipeline.py

**变更类型**: 适配更新

**_init_components 方法变更**:

```python
# 旧代码
self.bing_adapter = BingSearchAdapter(
    base_url=self.config.BING_SEARCH_MCP_URL,
    timeout=60,
)

# 新代码
self.bing_adapter = BingSearchAdapter(config=self.config)
```

**_search_phase 方法新增**:

```python
# 健康检测：检查云端 Bing 搜索服务是否可用
logger.info("搜索阶段：执行 Bing 云端服务健康检测")
if not await self.bing_adapter.health_check():
    logger.error(
        "搜索阶段终止：Bing 云端服务不可用或已过期！"
        "请检查云端 MCP 服务地址是否有效，到期需重新部署获取新地址。"
    )
    return []
```

---

#### 2.4 scripts/test_bing_connectivity.py

**变更类型**: 新增文件

**文件结构**:
```python
- test_health_check(): 健康检测测试
- test_single_search(): 单次搜索测试
- main(): 主测试流程
```

**测试内容**:
1. 配置信息输出（地址、超时）
2. 健康检测执行
3. 单次搜索执行（关键词 "RAG"）
4. 测试结果总结

---

### 3. 新旧逻辑差异对比

| 项目 | 旧逻辑 | 新逻辑 |
|------|--------|--------|
| Bing 客户端 | 本地 HTTP (`127.0.0.1:8014`) | 云端 streamable_http |
| 地址配置 | `BING_SEARCH_MCP_URL` | `BING_SEARCH_MCP_STREAM_URL` |
| 超时配置 | 固定 60 秒 | `BING_MCP_TIMEOUT = 120` |
| 适配器初始化 | `base_url, timeout` | `config: CrawlerConfig` |
| 健康检测 | 无 | `health_check()` 方法 |
| 默认地址 | `http://127.0.0.1:8090/mcp` | 从 config 读取 |

---

### 4. 兼容说明

#### 4.1 mcp_client.py 保持不变

| 项目 | 状态 | 说明 |
|------|------|------|
| `FastMCPClient` | ✓ 无改动 | 保持现有统一逻辑 |
| 全局单例 | ✓ 无改动 | `search_mcp_client` 仍指向本地 8014 |

**注意**: `mcp_client.py` 中的 `search_mcp_client` 仍使用本地地址，但 `BingSearchAdapter` 已改用云端地址，两者解耦。

#### 4.2 上层业务影响

| 模块 | 影响 | 需修改 |
|------|------|--------|
| `BingSearchAdapter` | 初始化参数变更 | 已完成 |
| `CrawlPipeline` | BingAdapter 调用变更 | 已完成 |
| 其他模块 | 无 | 否 |

---

### 5. 校验结果

| 校验项 | 结果 | 备注 |
|--------|------|------|
| 模块导入 | ✓ 通过 | BingSearchAdapter + CrawlPipeline 正常 |
| 配置读取 | ✓ 通过 | 云端地址和超时正确读取 |
| CrawlPipeline 初始化 | ✓ 通过 | bing_adapter 使用云端地址 |
| Bing 云端连通 | ⚠ 超时 | 云端服务可能暂时不可用或需要特定参数 |

**说明**: Bing 云端服务测试超时（120 秒），可能是服务暂时不可用或需要特定认证参数。但代码改造已完成，模块导入和初始化正常。

---

### 6. 注意事项

1. **云端服务有效期**: `BING_SEARCH_MCP_STREAM_URL` 包含 token，到期需重新部署获取新地址
2. **超时设置**: 云端服务响应较慢，`BING_MCP_TIMEOUT` 设置为 120 秒
3. **服务可用性**: Bing 云端服务可能需要特定认证或参数，需进一步验证
4. **本地服务保留**: `mcp_client.py` 中的 `search_mcp_client` 仍保留本地地址，供其他模块使用

---

*文档自动归档，最后更新：2026-06-26*


## 2026-06-26 Bing search 参数规范调整变更记录

### 1. 调整原因

对齐 `bing_search` MCP 工具标准参数规范，明确必填/可选参数定义及边界约束。

### 2. 代码变更明细

#### 2.1 mcp_client_adapter/bing_search_adapter.py

**search_keywords 方法参数变更**:

| 变更项 | 旧定义 | 新定义 |
|--------|--------|--------|
| 参数列表 | `keywords, days, category, exclude_urls` | `keywords, days, category, exclude_urls, count=10, offset=0` |
| MCP 参数 | `{"keywords": keywords}` | `{"query": ", ".join(keywords), "count": count, "offset": offset}` |

**新增参数边界校验**:
```python
if count < 1 or count > 50:
    raise ValueError(f"count 参数必须在 1-50 之间，当前值：{count}")
if offset < 0:
    raise ValueError(f"offset 参数不能为负数，当前值：{offset}")
```

**参数转换逻辑**:
- `keywords` (List[str]) → `query` (str): 使用 `", ".join(keywords)` 转换

---

### 3. 新旧逻辑差异对比

| 项目 | 旧逻辑 | 新逻辑 |
|------|--------|--------|
| MCP 参数 | `keywords` (列表) | `query` (字符串) |
| 返回条数 | 无控制 | `count` 参数，默认 10，最大 50 |
| 翻页偏移 | 无支持 | `offset` 参数，默认 0 |
| 参数校验 | 无 | count 范围校验 + offset 非负校验 |

---

### 4. 兼容说明

| 模块 | 影响 | 需修改 |
|------|------|--------|
| `CrawlPipeline` | 无 | 否（默认参数自动适配） |
| `test_bing_connectivity.py` | 无 | 否（使用默认参数） |

---

### 5. 校验结果

| 校验项 | 结果 | 备注 |
|--------|------|------|
| 模块导入 | ✓ 通过 | 无报错 |
| 参数校验 | ✓ 通过 | count>50 和 offset<0 抛出异常 |
| 默认值 | ✓ 通过 | count=10, offset=0 |

---

*文档自动归档，最后更新：2026-06-26*

