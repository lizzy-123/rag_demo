import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))
import asyncio
from multi_agent.agent.mcp_client import close_all_mcp_clients, render_mcp_client

async def test_render_mcp():
    try:
        print("2. 调用 render_html_tool")
        res = await render_mcp_client.call_tool("render_html_tool", {
            "template_str": "<h1>{{title}}</h1><p>{{content}}</p>",
            "context": {
                "title": "测试页面",
                "content": "MCP渲染测试内容"
            }
        })
        print("渲染结果:", res)
        print("✅ 功能正常")
    except Exception as e:
        print(f"❌ 异常: {e}")
    finally:
        print("4. 统一关闭所有连接")
        await close_all_mcp_clients()

if __name__ == "__main__":
    asyncio.run(test_render_mcp())