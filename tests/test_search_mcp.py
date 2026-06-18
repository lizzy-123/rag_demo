import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

import asyncio
from multi_agent.agent.mcp_client import close_all_mcp_clients, search_mcp_client

async def test_search_mcp():
    try:
        print("2. 调用 searxng_search")
        res = await search_mcp_client.call_tool("searxng_search", {
            "query": "2026 Multi-Agent MCP 技术发展趋势"
        })
        print("搜索结果:", res)
        print("✅ 功能正常")
    except Exception as e:
        print(f"❌ 异常: {e}")
    finally:
        print("4. 统一关闭所有连接")
        await close_all_mcp_clients()
        print("连接清理完成\n")

if __name__ == "__main__":
    asyncio.run(test_search_mcp())