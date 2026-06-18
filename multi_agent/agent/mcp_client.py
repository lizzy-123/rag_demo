import sys
import asyncio
import logging
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json

logging.basicConfig(level=logging.INFO)

class MCPClient:
    def __init__(self, command: str, args: list):
        self.params = StdioServerParameters(command=command, args=args)

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        async with stdio_client(self.params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)

                raw_text = ""
                if hasattr(result, 'content') and result.content:
                    raw_text = result.content[0].text
                else:
                    # 无文本内容，直接返回原始result对象兜底
                    return result

                # 通用自动JSON解析
                try:
                    parsed_data = json.loads(raw_text)
                    logging.debug(f"[{tool_name}] 自动解析JSON成功")
                    return parsed_data
                except json.JSONDecodeError:
                    # 非JSON文本原样返回
                    logging.debug(f"[{tool_name}] 返回非结构化文本，不解析JSON")
                    return raw_text
            
                

# ========== 下面所有代码 完全不动 ==========
FILE_SERVER_ARGS = ["multi_agent/agent/mcp_servers/file_server.py"]
EMAIL_SERVER_ARGS = ["multi_agent/agent/mcp_servers/email_server.py"]
LLM_SERVER_ARGS = ["multi_agent/agent/mcp_servers/llm_server.py"]
RENDER_SERVER_ARGS = ["multi_agent/agent/mcp_servers/render_server.py"]
SEARCH_SERVER_ARGS = ["multi_agent/agent/mcp_servers/search_server.py"]

file_mcp_client = MCPClient(command=sys.executable, args=FILE_SERVER_ARGS)
email_mcp_client = MCPClient(command=sys.executable, args=EMAIL_SERVER_ARGS)
llm_mcp_client = MCPClient(command=sys.executable, args=LLM_SERVER_ARGS)
render_mcp_client = MCPClient(command=sys.executable, args=RENDER_SERVER_ARGS)
search_mcp_client = MCPClient(command=sys.executable, args=SEARCH_SERVER_ARGS)

ALL_MCP_CLIENTS = [
    file_mcp_client,
    email_mcp_client,
    llm_mcp_client,
    render_mcp_client,
    search_mcp_client
]

# 空实现，兼容原有代码调用（现在无需手动关闭）
async def close_all_mcp_clients() -> None:
    pass