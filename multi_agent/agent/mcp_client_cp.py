#agent/mcp_client.py

import sys
import asyncio
from typing import Any
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
import logging

class MCPClient:
    """通用STDIO MCP客户端"""
    def __init__(self,command:str,args:list):
        self.params = StdioServerParameters(command=command,args=args)
        self.session:ClientSession|None=None
        self._stdio_ctx = None          # 保存 stdio_client 的上下文管理器
        self._read = None
        self._write = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self.session is not None:
                return
            try:
                # 启动子进程并保持连接（不要立即退出上下文）
                self._stdio_ctx = stdio_client(self.params)
                self._read, self._write = await self._stdio_ctx.__aenter__()
                self.session = ClientSession(self._read, self._write)
                await self.session.initialize()
                logging.info(f"MCP client connected: {self.params.args[0]}")
            except Exception as e:
                logging.error(f"Failed to connect MCP client {self.params.args[0]}: {e}")
                raise

                      

    async def close(self)->None:
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
        if self._stdio_ctx:
            await self._stdio_ctx.__aexit__(None, None, None)
            self._stdio_ctx = None
            self._read = None
            self._write = None

    async def call_tool(self,tool_name:str,arguments:dict)->Any:
        """调用MCP工具，自动处理返回体"""
        await self.connect()
        result = await self.session.call_tool(tool_name,arguments=arguments)
        #处理MCP返回结果
        if hasattr(result,'content')and result.content:
            return result.content[0].text
        return result
    

#=============================统一初始化所有的MCP客户端===========

FILE_SERVER_ARGS = ["multi_agent/agent/mcp_servers/file_server.py"]
EMAIL_SERVER_ARGS = ["multi_agent/agent/mcp_servers/email_server.py"]
LLM_SERVER_ARGS = ["multi_agent/agent/mcp_servers/llm_server.py"]
RENDER_SERVER_ARGS = ["multi_agent/agent/mcp_servers/render_server.py"]
SEARCH_SERVER_ARGS = ["multi_agent/agent/mcp_servers/search_server.py"]



#文件操作MCP
# 文件操作 MCP
# file_mcp_client = MCPClient(command="python", args=FILE_SERVER_ARGS)
# # 邮件发送 MCP
# email_mcp_client = MCPClient(command="python", args=EMAIL_SERVER_ARGS)
# # LLM 调用 MCP
# llm_mcp_client = MCPClient(command="python", args=LLM_SERVER_ARGS)
# # HTML 渲染 MCP
# render_mcp_client = MCPClient(command="python", args=RENDER_SERVER_ARGS)
# # 联网搜索 MCP
# search_mcp_client = MCPClient(command="python", args=SEARCH_SERVER_ARGS)


file_mcp_client = MCPClient(command=sys.executable, args=FILE_SERVER_ARGS)
# 邮件发送 MCP
email_mcp_client = MCPClient(command=sys.executable, args=EMAIL_SERVER_ARGS)
# LLM 调用 MCP
llm_mcp_client = MCPClient(command=sys.executable, args=LLM_SERVER_ARGS)
# HTML 渲染 MCP
render_mcp_client = MCPClient(command=sys.executable, args=RENDER_SERVER_ARGS)
# 联网搜索 MCP
search_mcp_client = MCPClient(command=sys.executable, args=SEARCH_SERVER_ARGS)

#客户端集合，方便全局统一初始化/关闭
ALL_MCP_CLIENTS=[
    file_mcp_client,
    email_mcp_client,
    llm_mcp_client,
    render_mcp_client,
    search_mcp_client
]

#===============全局工具方法(一键初始化后/关闭)==============
# async def init_all_mcp_clients()->None:
#     """一次性初始化所有的MCP客户端连接"""
#     for client in ALL_MCP_CLIENTS:
#         await client.connect()

# async def close_all_mcp_clients()->None:
#     """一次性关闭所有MCP客户端连接"""
#     for client in ALL_MCP_CLIENTS:
#         await client.close()

async def init_all_mcp_clients()->None:
    #并发初始化所有客户端，解决串行阻塞
    tasks = [client.connect() for client in ALL_MCP_CLIENTS]
    await asyncio.gather(*tasks)

async def close_all_mcp_clients()->None:
    tasks = [client.close() for client in ALL_MCP_CLIENTS]
    await asyncio.gather(*tasks)
        