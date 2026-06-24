import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from fastmcp import FastMCP
import logging
from typing import List, Dict

# 导入原有 skill 业务逻辑
from multi_agent.agent.skills.search_skill import searxng_search

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("search-mcp")

@mcp.tool(name="searxng_search")
def search_tool(query: str) -> List[Dict[str, str]]:
    """调用本地 SearXNG 联网搜索"""
    return searxng_search(query)

if __name__ == "__main__":
    #mcp.run(transport="stdio")
    mcp.run(
        transport = "streamable-http",
        host = "0.0.0.0",
        port = 8014
    )