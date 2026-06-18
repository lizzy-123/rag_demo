import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))
import asyncio
from multi_agent.agent.mcp_client import close_all_mcp_clients, llm_mcp_client

async def test_llm_mcp():
    try:
        print("2. 调用 call_llm_tool")
        res = await llm_mcp_client.call_tool("call_llm_tool", {
            "system_prompt": "简洁回答问题,**必须输出标准JSON格式**，不要额外文字",
            "prompt": "简单介绍MCP协议"
        })
        print("LLM结果:", res)
        print("✅ 功能正常")
    except Exception as e:
        print(f"❌ 异常: {e}")
    finally:
        print("4. 统一关闭所有连接")
        await close_all_mcp_clients()

if __name__ == "__main__":
    asyncio.run(test_llm_mcp())