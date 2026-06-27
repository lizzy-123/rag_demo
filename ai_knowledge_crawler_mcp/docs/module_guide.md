# 模块说明

> 最后更新：2026-06-26

---

## BingSearchAdapter 模块说明

### 1. 模块定位

`BingSearchAdapter` 封装 ModelScope 云端 Bing 搜索 MCP 服务（streamable_http 协议），用于批量搜索 AI 技术关键词。

### 2. 核心方法

#### `search_keywords()`

批量搜索关键词，返回结构化搜索结果。

**参数定义**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `keywords` | List[str] | 是 | - | 搜索关键词列表 |
| `days` | Optional[int] | 否 | None | 限定近 N 天 |
| `category` | Optional[str] | 否 | None | 搜索分类 |
| `exclude_urls` | Optional[List[str]] | 否 | None | 排除的 URL 列表 |
| `count` | int | 否 | 10 | 返回条数，最大 50 |
| `offset` | int | 否 | 0 | 翻页偏移 |

**参数边界约束**:
- `count`: 1 ≤ count ≤ 50
- `offset`: offset ≥ 0

**MCP 工具调用参数** (`bing_search`):

| MCP 参数 | 来源 | 说明 |
|----------|------|------|
| `query` | `", ".join(keywords)` | 必填，搜索关键词字符串 |
| `count` | 参数 `count` | 返回条数，默认 10 |
| `offset` | 参数 `offset` | 翻页偏移，默认 0 |
| `days` | 参数 `days` | 可选，时间范围 |
| `category` | 参数 `category` | 可选，分类 |
| `exclude_urls` | 参数 `exclude_urls` | 可选，排除 URL |

**返回结构**:
```python
{
    "results": [
        {"title": "...", "url": "...", "published_date": "...", "snippet": "..."}
    ],
    "total": int,
    "filtered_count": int
}
```

### 3. 健康检测

`health_check()` 方法用于验证云端服务连通性，通过搜索测试关键词验证服务可用性。

---

*文档自动归档，最后更新：2026-06-26*
