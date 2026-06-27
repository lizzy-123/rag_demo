# 开发计划文档

> 最后更新：2026-06-25

---

## 2026-06-25 MCP 客户端统一改造开发计划

### 1. 改造步骤

#### 步骤 1：配置层改造

**文件**: `ai_knowledge_crawler_mcp/config/settings.py`

**操作**:
1. 删除 `FETCH_MCP_URL = "http://127.0.0.1:8013/mcp"`
2. 新增 `FETCH_MCP_STREAM_URL = "https://mcp.api-inference.modelscope.net/f8c8c47b0f7f4a/mcp"`
3. 新增 `FETCH_MCP_TIMEOUT = 120`
4. 路径类型从 `str` 改为 `Path`

#### 步骤 2：客户端层重构

**文件**: `multi_agent/agent/mcp_client.py`

**操作**:
1. 移除 `mcp.client.http` 导入
2. 移除 `HttpMCPClient` 类定义
3. 保留并增强 `FastMCPClient` 类
4. 全部全局单例改用 `FastMCPClient` 实例化
5. 添加详细注释区分本地/云端用途

#### 步骤 3：适配器层改造

**文件**: `ai_knowledge_crawler_mcp/mcp_client_adapter/fetch_adapter.py`

**操作**:
1. `__init__` 读取云端配置地址
2. 工具名从 `fetch_url` 改为 `fetch`
3. 删除 `render_js` 参数
4. 对齐官方入参：`url, max_length, start_index, raw`
5. 新增 `health_check()` 方法
6. 处理返回结果（可能是字符串或字典）

#### 步骤 4：业务层适配

**文件**: `ai_knowledge_crawler_mcp/crawl_task/crawl_pipeline.py`

**操作**:
1. 修改 `FetchAdapter` 初始化方式（传入 config 而非 base_url）
2. `_fetch_phase` 开头增加健康检测
3. 删除 `render_js` 传参

#### 步骤 5：配置读取器更新

**文件**: `ai_knowledge_crawler_mcp/crawl_task/config_reader.py`

**操作**:
1. `get_fetch_timeout` 改为读取 `FETCH_MCP_TIMEOUT`

#### 步骤 6：创建测试脚本

**文件**: `ai_knowledge_crawler_mcp/scripts/test_fetch_connectivity.py`

**内容**:
- 健康检测测试
- 单次抓取测试
- 测试总结输出

### 2. 文件修改清单

| 文件路径 | 修改类型 | 主要变更 |
|----------|----------|----------|
| `config/settings.py` | 修改 | 删除本地 Fetch 配置，新增云端配置，路径类型改为 Path |
| `multi_agent/agent/mcp_client.py` | 重构 | 移除 HttpMCPClient，统一使用 FastMCPClient |
| `mcp_client_adapter/fetch_adapter.py` | 改造 | 云端适配、参数对齐、新增健康检测 |
| `crawl_task/crawl_pipeline.py` | 修改 | FetchAdapter 初始化、健康检测、删除 render_js |
| `crawl_task/config_reader.py` | 修改 | get_fetch_timeout 读取新配置 |
| `scripts/test_fetch_connectivity.py` | 新增 | 连通性测试脚本 |

### 3. 执行顺序

```
1. config/settings.py (配置层)
   ↓
2. multi_agent/agent/mcp_client.py (客户端层)
   ↓
3. mcp_client_adapter/fetch_adapter.py (适配器层)
   ↓
4. crawl_task/config_reader.py (配置读取)
   ↓
5. crawl_task/crawl_pipeline.py (业务层)
   ↓
6. scripts/test_fetch_connectivity.py (测试脚本)
```

### 4. 前置依赖

| 依赖项 | 说明 |
|--------|------|
| `fastmcp` | 已安装，用于 Client 实现 |
| 云端 Fetch 服务 | 需确保服务地址有效 |
| SearXNG | 本地搜索服务（可选） |

### 5. 测试流程

#### 5.1 基础导入测试

```bash
uv run python -c "
from multi_agent.agent.mcp_client import FastMCPClient, file_mcp_client, search_mcp_client, render_mcp_client
print('统一 FastMCPClient 导入成功，本地全部 MCP 单例正常')
"
```

#### 5.2 模块导入测试

```bash
uv run python -c "
from ai_knowledge_crawler_mcp.crawl_task import CrawlPipeline
print('CrawlPipeline 模块导入、初始化无异常')
"
```

#### 5.3 连通性测试

```bash
uv run python -m ai_knowledge_crawler_mcp.scripts.test_fetch_connectivity
```

### 6. 验证命令

| 验证项 | 命令 | 预期结果 |
|--------|------|----------|
| 基础导入 | `uv run python -c "from multi_agent.agent.mcp_client import FastMCPClient..."` | 无报错 |
| 流水线导入 | `uv run python -c "from ai_knowledge_crawler_mcp.crawl_task import CrawlPipeline"` | 无报错 |
| 云端连通 | `uv run python -m ai_knowledge_crawler_mcp.scripts.test_fetch_connectivity` | 健康检测通过 + 单次抓取通过 |

### 7. 变更总结

| 变更类型 | 数量 | 说明 |
|----------|------|------|
| 新增文件 | 2 | test_fetch_connectivity.py, docs/ 目录 |
| 修改文件 | 5 | settings.py, mcp_client.py, fetch_adapter.py, crawl_pipeline.py, config_reader.py |
| 删除代码 | 1 | HttpMCPClient 类及 mcp.client.http 导入 |
| 新增功能 | 1 | health_check 健康检测 |

---

## 统一代码运行规则（强制规范）

### 1. 模块化执行方式

项目所有脚本、自测、模块校验**必须使用模块化执行方式**：

```bash
uv run python -m 完整模块名
```

### 2. 禁止直接使用文件路径

**禁止**直接使用文件路径执行（如 `uv run python xxx/xxx.py`）。

**原因**: 直接运行单文件会破坏 Python 模块搜索路径，引发 `ModuleNotFoundError` 导入异常。使用 `-m` 能保证项目根目录模块解析正常。

### 3. 正确示例

```bash
# 导入校验
uv run python -c "from multi_agent.agent.mcp_client import FastMCPClient"

# 脚本运行
uv run python -m ai_knowledge_crawler_mcp.scripts.test_fetch_connectivity

# CrawlPipeline 测试
uv run python -m ai_knowledge_crawler_mcp.crawl_task.crawl_pipeline
```

### 4. 禁止写法

```bash
# ❌ 错误：直接使用文件路径
uv run python ai_knowledge_crawler_mcp/scripts/test_fetch_connectivity.py

# ❌ 错误：相对路径执行
uv run python scripts/test_fetch_connectivity.py
```

### 5. 规范适用范围

- 所有测试脚本执行
- 所有调试命令
- 所有模块导入校验
- 所有计划文档中的校验命令
- 所有自动化脚本

### 6. MCP 改造校验命令（统一格式）

| 验证项 | 命令 | 预期结果 |
|--------|------|----------|
| 基础导入 | `uv run python -c "from multi_agent.agent.mcp_client import FastMCPClient, file_mcp_client, search_mcp_client, render_mcp_client"` | 无报错 |
| 流水线导入 | `uv run python -c "from ai_knowledge_crawler_mcp.crawl_task import CrawlPipeline"` | 无报错 |
| Fetch 云端连通 | `uv run python -m ai_knowledge_crawler_mcp.scripts.test_fetch_connectivity` | 健康检测通过 + 单次抓取通过 |

---

## 2026-06-26 Bing 云端 MCP 迁移开发计划

### 1. 改造步骤

#### 步骤 1：配置层更新

**文件**: `ai_knowledge_crawler_mcp/config/settings.py`

**操作**:
1. 删除 `BING_SEARCH_MCP_URL = "http://127.0.0.1:8014/mcp"`
2. 新增 `BING_SEARCH_MCP_STREAM_URL = "https://mcp.api-inference.modelscope.net/6904a6ead8de4c/mcp"`
3. 新增 `BING_MCP_TIMEOUT = 120`

#### 步骤 2：Bing 适配器改造

**文件**: `ai_knowledge_crawler_mcp/mcp_client_adapter/bing_search_adapter.py`

**操作**:
1. `__init__` 改为读取 `config` 参数
2. 从 config 读取 `BING_SEARCH_MCP_STREAM_URL` 和 `BING_MCP_TIMEOUT`
3. 删除默认本地地址 `http://127.0.0.1:8090/mcp`
4. 新增 `health_check()` 方法
5. 处理返回结果（可能是字符串或字典）

#### 步骤 3：采集流水线适配

**文件**: `ai_knowledge_crawler_mcp/crawl_task/crawl_pipeline.py`

**操作**:
1. `BingSearchAdapter` 初始化改为传入 `config`
2. `_search_phase` 开头增加 Bing 健康检测
3. 删除 `base_url` 和 `timeout` 硬编码参数

#### 步骤 4：创建测试脚本

**文件**: `ai_knowledge_crawler_mcp/scripts/test_bing_connectivity.py`

**内容**:
- 健康检测测试
- 单次搜索测试
- 测试总结输出

#### 步骤 5：清理本地代码

**操作**:
1. 删除所有 `8090` 端口相关硬编码
2. 删除所有 `127.0.0.1:8014` 相关注释
3. 删除本地 Bing MCP 启动相关逻辑

### 2. 文件修改清单

| 文件路径 | 修改类型 | 主要变更 |
|----------|----------|----------|
| `config/settings.py` | 修改 | 删除本地 Bing 配置，新增云端配置 |
| `mcp_client_adapter/bing_search_adapter.py` | 改造 | 云端适配、参数对齐、新增健康检测 |
| `crawl_task/crawl_pipeline.py` | 修改 | BingAdapter 初始化、健康检测 |
| `scripts/test_bing_connectivity.py` | 新增 | Bing 连通性测试脚本 |

### 3. 执行顺序

```
1. config/settings.py (配置层)
   ↓
2. mcp_client_adapter/bing_search_adapter.py (适配器层)
   ↓
3. crawl_task/crawl_pipeline.py (业务层)
   ↓
4. scripts/test_bing_connectivity.py (测试脚本)
```

### 4. 前置依赖

| 依赖项 | 说明 |
|--------|------|
| `fastmcp` | 已安装，用于 Client 实现 |
| 云端 Bing 服务 | 需确保服务地址有效 |
| `mcp_client.py` | **不改动**，保持现有 FastMCPClient 逻辑 |

### 5. 测试流程

#### 5.1 Bing 云端连通性测试

```bash
uv run python -m ai_knowledge_crawler_mcp.scripts.test_bing_connectivity
```

#### 5.2 完整采集流水线初始化校验

```bash
uv run python -m ai_knowledge_crawler_mcp.crawl_task.crawl_pipeline
```

### 6. 验证命令

| 验证项 | 命令 | 预期结果 |
|--------|------|----------|
| Bing 云端连通 | `uv run python -m ai_knowledge_crawler_mcp.scripts.test_bing_connectivity` | 健康检测通过 + 单次搜索通过 |
| 流水线初始化 | `uv run python -m ai_knowledge_crawler_mcp.crawl_task.crawl_pipeline` | 初始化成功，不报错 |

### 7. 变更总结

| 变更类型 | 数量 | 说明 |
|----------|------|------|
| 新增文件 | 1 | test_bing_connectivity.py |
| 修改文件 | 3 | settings.py, bing_search_adapter.py, crawl_pipeline.py |
| 删除配置 | 1 | BING_SEARCH_MCP_URL (本地 8014) |
| 新增功能 | 1 | Bing health_check 健康检测 |

---

*文档自动归档，最后更新：2026-06-26*
