#/multi_agent/agent/mcp_servers/file_server.py

import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from fastmcp import FastMCP
import logging
from typing import List,Dict,Any
from multi_agent.agent.skills.file_skill import load_json_file,save_json_file
#from ...agent.skills.file_skill import load_json_file,save_json_file


# 确保能找到 multi_agent 包


logging.basicConfig(level=logging.INFO)
#把skill包装成MCP工具

mcp = FastMCP("file-mcp")

@mcp.tool()
def loadjson(file_path: str)->List[Dict[str,Any]]:
    """加载本地JSON文件  """
    return load_json_file(file_path)

@mcp.tool()
def savejson(file_path:str,data:Any)->str:
    """保存数据到JSON文件"""
    save_json_file(file_path,data)
    return f"文件已成功保存至:{file_path}"


if __name__ =="__main__":
    #启动MCP Server(独立进程)
    mcp.run(transport="stdio")