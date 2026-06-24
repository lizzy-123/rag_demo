# import sys
# import asyncio
# import logging
# from typing import Any
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# import json

# logging.basicConfig(level=logging.INFO)

# class MCPClient:
#     def __init__(self, command: str, args: list):
#         self.params = StdioServerParameters(command=command, args=args)

#     async def call_tool(self, tool_name: str, arguments: dict) -> Any:
#         async with stdio_client(self.params) as (read, write):
#             async with ClientSession(read, write) as session:
#                 await session.initialize()
#                 result = await session.call_tool(tool_name, arguments=arguments)

#                 raw_text = ""
#                 if hasattr(result, 'content') and result.content:
#                     raw_text = result.content[0].text
#                 else:
#                     # 无文本内容，直接返回原始result对象兜底
#                     return result

#                 # 通用自动JSON解析
#                 try:
#                     parsed_data = json.loads(raw_text)
#                     logging.debug(f"[{tool_name}] 自动解析JSON成功")
#                     return parsed_data
#                 except json.JSONDecodeError:
#                     # 非JSON文本原样返回
#                     logging.debug(f"[{tool_name}] 返回非结构化文本，不解析JSON")
#                     return raw_text
            
                

# # ========== 下面所有代码 完全不动 ==========
# FILE_SERVER_ARGS = ["multi_agent/agent/mcp_servers/file_server.py"]
# EMAIL_SERVER_ARGS = ["multi_agent/agent/mcp_servers/email_server.py"]
# LLM_SERVER_ARGS = ["multi_agent/agent/mcp_servers/llm_server.py"]
# RENDER_SERVER_ARGS = ["multi_agent/agent/mcp_servers/render_server.py"]
# SEARCH_SERVER_ARGS = ["multi_agent/agent/mcp_servers/search_server.py"]

# file_mcp_client = MCPClient(command=sys.executable, args=FILE_SERVER_ARGS)
# email_mcp_client = MCPClient(command=sys.executable, args=EMAIL_SERVER_ARGS)
# llm_mcp_client = MCPClient(command=sys.executable, args=LLM_SERVER_ARGS)
# render_mcp_client = MCPClient(command=sys.executable, args=RENDER_SERVER_ARGS)
# search_mcp_client = MCPClient(command=sys.executable, args=SEARCH_SERVER_ARGS)

# ALL_MCP_CLIENTS = [
#     file_mcp_client,
#     email_mcp_client,
#     llm_mcp_client,
#     render_mcp_client,
#     search_mcp_client
# ]

# # 空实现，兼容原有代码调用（现在无需手动关闭）
# async def close_all_mcp_clients() -> None:
#     pass

# ===================== MCP 服务统一配置 =====================
# SERVER_ROOT = "multi_agent/agent/mcp_servers"
# FILE_SERVER_ARGS = [f"{SERVER_ROOT}/file_server.py"]
# EMAIL_SERVER_ARGS = [f"{SERVER_ROOT}/email_server.py"]
# LLM_SERVER_ARGS = [f"{SERVER_ROOT}/llm_server.py"]
# RENDER_SERVER_ARGS = [f"{SERVER_ROOT}/render_server.py"]
# SEARCH_SERVER_ARGS = [f"{SERVER_ROOT}/search_server.py"]

# # 全局单例客户端
# file_mcp_client = PersistentMCPClient(command=sys.executable, args=FILE_SERVER_ARGS)
# email_mcp_client = PersistentMCPClient(command=sys.executable, args=EMAIL_SERVER_ARGS)
# llm_mcp_client = PersistentMCPClient(command=sys.executable, args=LLM_SERVER_ARGS)
# render_mcp_client = PersistentMCPClient(command=sys.executable, args=RENDER_SERVER_ARGS)
# search_mcp_client = PersistentMCPClient(command=sys.executable, args=SEARCH_SERVER_ARGS)

# ALL_MCP_CLIENTS = [
#     file_mcp_client,
#     email_mcp_client,
#     llm_mcp_client,
#     render_mcp_client,
#     search_mcp_client
# ]


# # 启动 start_all_mcp_clients() 并发 gather 批量启动 5 个 MCP 长连接，
# # 多个 stdio_client 同时抢占标准输入输出流（stdout/stderr），子进程管道争抢、
# # 握手中断，服务连接直接关闭，初始化失败。
# # 关键改造规则
# # 禁止全局缓存 _read / _write / _session 流对象，所有 stdio 上下文必须限制在同一个协程任务内；
# # 每个 MCP 客户端独占独立后台常驻 Task，所有 call 操作全部转发至该专属 Task 执行，保证 enter/exit 同一任务；
# # 串行启动 MCP 服务，禁止 asyncio.gather 并发拉起多个 stdio 进程，避免 IO 冲突。


# async def start_all_mcp_clients():
#     """程序启动时批量初始化所有MCP连接"""
#     tasks = [client.start() for client in ALL_MCP_CLIENTS]
#     await asyncio.gather(*tasks)
#     logging.info("全部MCP服务长连接初始化完成")

# async def close_all_mcp_clients() -> None:
#     """程序退出时销毁所有子进程"""
#     tasks = [client.stop() for client in ALL_MCP_CLIENTS]
#     await asyncio.gather(*tasks, return_exceptions=True)
#     logging.info("所有MCP连接已全部释放")


import sys
import asyncio
import logging
import json
from typing import Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

#from mcp.client.http import http_client
from fastmcp import Client


logging.basicConfig(level=logging.INFO)

# class PersistentMCPClient:
#     """长连接复用MCP客户端，单进程常驻，不每次新建"""
#     def __init__(self, command: str, args: list, timeout: int = 30):
#         self.params = StdioServerParameters(command=command, args=args)
#         self.timeout = timeout
#         self._read: Any = None
#         self._write: Any = None
#         self._session: Optional[ClientSession] = None
#         self._lock = asyncio.Lock()
#         self._initialized = False

#     async def start(self):
#         """启动常驻子进程+session，只执行一次"""
#         async with self._lock:
#             if self._initialized:
#                 return
#             self._read, self._write = await stdio_client(self.params).__aenter__()
#             self._session = ClientSession(self._read, self._write)
#             await self._session.__aenter__()
#             await self._session.initialize()
#             self._initialized = True
#             logging.info(f"MCP Server {self.params.args[0]} 长连接已启动")

#     async def stop(self):
#         """销毁进程与会话"""
#         async with self._lock:
#             if not self._initialized:
#                 return
#             if self._session:
#                 await self._session.__aexit__(None, None, None)
#             if self._read and self._write:
#                 await stdio_client(self.params).__aexit__(None, None, None)
#             self._initialized = False
#             logging.info(f"MCP Server {self.params.args[0]} 连接已关闭")

#     async def call_tool(self, tool_name: str, arguments: dict) -> Any:
#         await self.start()
#         try:
#             result = await asyncio.wait_for(
#                 self._session.call_tool(tool_name, arguments=arguments),
#                 timeout=self.timeout
#             )
#         except asyncio.TimeoutError:
#             raise TimeoutError(f"MCP工具 {tool_name} 调用超时({self.timeout}s)")

#         raw_text = ""
#         if hasattr(result, 'content') and result.content:
#             raw_text = result.content[0].text
#         else:
#             return result

#         try:
#             return json.loads(raw_text)
#         except json.JSONDecodeError:
#             return raw_text

#     async def read_resource(self, resource_uri: str) -> str:
#         """读取MCP Resource（模板等资源）"""
#         await self.start()
#         res = await asyncio.wait_for(
#             self._session.read_resource(resource_uri),
#             timeout=self.timeout
#         )
#         return res.content


# class HttpMCPClient:
#     def __init__(self,base_url:str,timeout:int = 50):
#         self.base_url = base_url
#         self.timeout = timeout

#     async def call_tool(self,tool_name:str,arguments:dict)->Any:
#         async with http_client(self.base_url) as (read,write):
#             async with ClientSession(self.base_url) as session:
#                 await session.initialize()
#                 try:
#                     res = await asyncio.wait_for(
#                         session.call_tool(tool_name,arguments = arguments),
#                         timeout=self.timeout
#                     )
#                 except asyncio.TimeoutError:
#                     raise TimeoutError(f"MCP工具{tool_name}调用超时({self.timeout})s")
#                 raw_text = ""
#                 if res.content and len(res.content)>0:
#                     raw_text = res.content[0].text

#                 try:
#                     parsed_data = json.load(raw_text)
#                     logging.debug(f"[{tool_name}]自动解析JSON成功")
#                     return parsed_data
#                 except json.JSONDecodeError:
#                     logging.debug(f"[{tool_name}]返回非结构化文本，不解析Json")
#                     return raw_text
                
#     async def read_resource(self, resource_uri: str) -> str:
#         async with http_client(self.base_url) as (read, write):
#             async with ClientSession(read, write) as session:
#                 await session.initialize()
#                 res = await asyncio.wait_for(
#                     session.read_resource(resource_uri),
#                     timeout=self.timeout
#                 )
#                 return res.content            

        
        
# #======================接端口绑定各个MCP服务地址============
# file_mcp_client = HttpMCPClient("http://127.0.0.1:8011/mcp")
# llm_mcp_client = HttpMCPClient("http://127.0.0.1:8012/mcp")
# search_mcp_client = HttpMCPClient("http://127.0.0.1:8014/mcp")
# render_mcp_client = HttpMCPClient("http://127.0.0.1:8013/mcp")
# email_mcp_client=HttpMCPClient("http://127.0.0.1:8010/mcp")

# ALL_MCP_CLIENTS=[
#     file_mcp_client,
#     llm_mcp_client,
#     search_mcp_client,
#     render_mcp_client,
#     email_mcp_client
# ]

# #http模式无需预启动子进程，空兼容函数
# async def start_all_mcp_client():
#     logging.info("Stream-Http模式：请手动提前启动所有mcp服务，无需代码拉起")

# #无本地子进程，关闭逻辑空实现
# async def close_all_mcp_clients()->None:
#     logging.info("http无常驻子进程资源，无需释放")

from fastmcp import Client

class FastMCPClient:
    def __init__(self, base_url: str, timeout: int = 50):
        self.base_url = base_url
        self.timeout = timeout

    async def call_tool(self, tool_name: str, arguments: dict):
        """每次调用创建临时连接，用完自动释放"""
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
            return result  # 无内容时兜底/result.content[0].text

    async def read_resource(self, resource_uri: str):
        """读取 MCP 资源（如模板），返回文本内容"""
        async with Client(self.base_url, timeout=self.timeout) as client:
            result = await client.read_resource(resource_uri)
            if result and len(result) > 0:
                content = result[0]
                # 资源内容可能是 TextContent 或 BlobContent
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'blob'):
                    # 如果是二进制，假设是 UTF-8 文本
                    return content.blob.decode('utf-8')
                else:
                    return str(content)  # 兜底
            return None
        

file_mcp_client = FastMCPClient("http://127.0.0.1:8011/mcp")
llm_mcp_client = FastMCPClient("http://127.0.0.1:8012/mcp",timeout=180)
search_mcp_client = FastMCPClient("http://127.0.0.1:8014/mcp")
render_mcp_client = FastMCPClient("http://127.0.0.1:8013/mcp")
email_mcp_client = FastMCPClient("http://127.0.0.1:8010/mcp")

async def start_all_mcp_clients():
    logging.info("No pre-start needed for FastMCPClient (lazy connection)")

async def close_all_mcp_clients():
    logging.info("No explicit cleanup needed for FastMCPClient")