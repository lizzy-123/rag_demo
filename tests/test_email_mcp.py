import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

import asyncio
from multi_agent.agent.mcp_client import close_all_mcp_clients, email_mcp_client

async def test_email_mcp():
    try:
        print("2. 调用 send_email")
        # 只保留服务端定义的 subject、html_content
        res = await email_mcp_client.call_tool("send_email", {
            "subject": "MCP自动化测试邮件",
            "html_content": "<h2>周报已生成</h2><p>AI生成周报测试</p>"
        })
        print("邮件发送结果:", res)
        print("✅ 功能正常")
    except Exception as e:
        print(f"❌ 异常: {e}")
    finally:
        print("4. 统一关闭所有连接")
        await close_all_mcp_clients()
        print("连接清理完成\n")

if __name__ == "__main__":
    asyncio.run(test_email_mcp())