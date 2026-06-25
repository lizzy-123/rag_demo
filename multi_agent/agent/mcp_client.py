"""
MCP 客户端模块 - 双客户端架构

本模块提供两套 MCP 客户端实现，分别用于不同场景：

【本地 HTTP 客户端】
- HttpMCPClient: 基于 fastmcp.Client，用于本地 HTTP MCP 服务
- 适用于本地 HTTP 端口 MCP 服务（如 8011/8012/8014）

【云端 streamable_http 客户端】
- FastMCPClient: 基于 fastmcp.Client，自动适配 HTTP/streamable_http
- 适用于云端 MCP 服务（如 ModelScope Fetch）

导入说明：
- 本地客户端：from multi_agent.agent.mcp_client import HttpMCPClient, file_mcp_client, ...
- 云端客户端：from multi_agent.agent.mcp_client import FastMCPClient
"""

import asyncio
import logging
import json
from typing import Any

# 统一使用 fastmcp.Client 处理 HTTP 和 streamable_http
from fastmcp import Client

logging.basicConfig(level=logging.INFO)

# =============================================================================
# ===================== 本地 HTTP 客户端 =====================
# =============================================================================
# 用于本地 HTTP 端口 MCP 服务（如 8011/8012/8014）


class HttpMCPClient:
    """
    本地 HTTP MCP 客户端

    基于 fastmcp.Client 实现，用于本地 HTTP 端口 MCP 服务。
    每次调用创建临时连接，用完自动释放。
    """

    def __init__(self, base_url: str, timeout: int = 50):
        """
        初始化 HTTP MCP 客户端

        Args:
            base_url: HTTP 服务地址，如 "http://127.0.0.1:8011/mcp"
            timeout: 调用超时时间（秒）
        """
        self.base_url = base_url
        self.timeout = timeout

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具返回结果（自动解析 JSON）
        """
        async with Client(self.base_url, timeout=self.timeout) as client:
            try:
                result = await asyncio.wait_for(
                    client.call_tool(tool_name, arguments),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"MCP 工具{tool_name}调用超时 ({self.timeout})s")

            # result 是 CallToolResult 对象
            if result.content and len(result.content) > 0:
                raw_text = result.content[0].text

                try:
                    parsed_data = json.loads(raw_text)
                    logging.debug(f"[{tool_name}] 自动解析 JSON 成功")
                    return parsed_data
                except json.JSONDecodeError:
                    logging.debug(f"[{tool_name}] 返回非结构化文本，不解析 Json")
                    return raw_text
            return result

    async def read_resource(self, resource_uri: str) -> str:
        """
        读取 MCP 资源

        Args:
            resource_uri: 资源 URI

        Returns:
            资源内容文本
        """
        async with Client(self.base_url, timeout=self.timeout) as client:
            res = await asyncio.wait_for(
                client.read_resource(resource_uri),
                timeout=self.timeout
            )
            if res and len(res) > 0:
                content = res[0]
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'blob'):
                    return content.blob.decode('utf-8')
                else:
                    return str(content)
            return ""


# ===================== 本地 HTTP MCP 服务客户端实例 =====================
# 文件服务 MCP (8011)
file_mcp_client = HttpMCPClient("http://127.0.0.1:8011/mcp")

# LLM 服务 MCP (8012)
llm_mcp_client = HttpMCPClient("http://127.0.0.1:8012/mcp", timeout=180)

# 搜索服务 MCP (8014)
search_mcp_client = HttpMCPClient("http://127.0.0.1:8014/mcp")

# 邮件服务 MCP (8010)
email_mcp_client = HttpMCPClient("http://127.0.0.1:8010/mcp")

# 注意：本地 8013 Fetch 服务已迁移到云端，不再使用 render_mcp_client


# =============================================================================
# ===================== 云端 streamable_http 客户端 =====================
# =============================================================================
# 用于云端 MCP 服务（如 ModelScope Fetch）


class FastMCPClient:
    """
    通用 MCP 客户端，支持 HTTP 和 streamable_http 协议

    基于 fastmcp 原生 Client，自动适配不同传输协议：
    - 本地 HTTP: http://127.0.0.1:801x/mcp
    - 云端 streamable_http: https://mcp.api-inference.modelscope.net/xxx/mcp

    注意：此客户端仅包含通用 call_tool / read_resource 方法，
    不包含任何业务逻辑（如 fetch 抓取），业务逻辑由上层适配器实现。
    """

    def __init__(self, base_url: str, timeout: int = 50):
        """
        初始化 MCP 客户端

        Args:
            base_url: MCP 服务地址（支持 HTTP 和 HTTPS）
            timeout: 调用超时时间（秒）
        """
        self.base_url = base_url
        self.timeout = timeout

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        调用 MCP 工具，自动适配传输协议

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具返回结果（自动解析 JSON）
        """
        async with Client(self.base_url, timeout=self.timeout) as client:
            result = await client.call_tool(tool_name, arguments)
            # result 是 CallToolResult 对象
            if result.content and len(result.content) > 0:
                raw_text = result.content[0].text
                # 尝试解析 JSON
                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError:
                    # 非 JSON 则原样返回文本
                    return raw_text
            return result  # 无内容时兜底

    async def read_resource(self, resource_uri: str) -> str | None:
        """
        读取 MCP 资源（如模板），返回文本内容

        Args:
            resource_uri: 资源 URI

        Returns:
            资源文本内容，失败返回 None
        """
        async with Client(self.base_url, timeout=self.timeout) as client:
            result = await client.read_resource(resource_uri)
            if result and len(result) > 0:
                content = result[0]
                # 资源内容可能是 TextContent 或 BlobContent
                if hasattr(content, "text"):
                    return content.text
                elif hasattr(content, "blob"):
                    # 如果是二进制，假设是 UTF-8 文本
                    return content.blob.decode("utf-8")
                else:
                    return str(content)  # 兜底
            return None


# 注意：
# - 旧版全局单例（file_mcp_client 等）使用 HttpMCPClient
# - 新客户端 FastMCPClient 需由使用者自行实例化，传入对应云端地址
# 例如：fetch_client = FastMCPClient("https://mcp.api-inference.modelscope.net/xxx/mcp")
