"""
MCP 客户端模块 - 统一 FastMCP Client 实现
移除依赖 mcp.client.http 的 HttpMCPClient，全部使用 fastmcp.Client，无模块缺失报错
"""
import asyncio
import logging
import json
from typing import Any
from fastmcp import Client

logging.basicConfig(level=logging.INFO)

class FastMCPClient:
    def __init__(self, base_url: str, timeout: int = 50):
        self.base_url = base_url
        self.timeout = timeout

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        async with Client(self.base_url, timeout=self.timeout) as client:
            result = await client.call_tool(tool_name, arguments)
            raw_text = ""
            if result.content and len(result.content) > 0:
                raw_text = result.content[0].text
                try:
                    parsed_data = json.loads(raw_text)
                    logging.debug(f"[{tool_name}]自动解析JSON成功")
                    return parsed_data
                except json.JSONDecodeError:
                    logging.debug(f"[{tool_name}]返回非结构化文本，不解析Json")
                    return raw_text
            return result

    async def read_resource(self, resource_uri: str) -> str | None:
        async with Client(self.base_url, timeout=self.timeout) as client:
            result = await client.read_resource(resource_uri)
            if result and len(result) > 0:
                content = result[0]
                if hasattr(content, "text"):
                    return content.text
                elif hasattr(content, "blob"):
                    return content.blob.decode("utf-8")
                else:
                    return str(content)
            return None

# 本地HTTP MCP 全局客户端（统一用FastMCPClient，不再用HttpMCPClient）
file_mcp_client = FastMCPClient("http://127.0.0.1:8011/mcp")
llm_mcp_client = FastMCPClient("http://127.0.0.1:8012/mcp",timeout=120)
render_mcp_client = FastMCPClient("http://127.0.0.1:8013/mcp")
search_mcp_client = FastMCPClient("http://127.0.0.1:8014/mcp")
email_mcp_client = FastMCPClient("http://127.0.0.1:8010/mcp")

ALL_MCP_CLIENTS = [
    file_mcp_client,
    llm_mcp_client,
    search_mcp_client,
    render_mcp_client,
    email_mcp_client
]

# 兼容main原有调用，空函数
async def start_all_mcp_clients():
    logging.info("Stream-Http模式：请手动提前启动所有mcp服务，无需代码拉起")

async def close_all_mcp_clients() -> None:
    logging.info("http无常驻子进程资源，无需释放")