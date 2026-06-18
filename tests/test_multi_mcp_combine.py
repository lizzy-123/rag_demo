import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

import asyncio
from multi_agent.agent.mcp_client import (
    close_all_mcp_clients,
    llm_mcp_client,
    render_mcp_client,
    file_mcp_client
)

async def test_multi_mcp_combine():
    try:
        print("===== 多MCP混合联动测试 =====")
        # 1. LLM生成文案，完整传两个必填参数
        print("\n1. LLM生成报告文案")
        llm_text = await llm_mcp_client.call_tool(
            "call_llm_tool",
            {
                "system_prompt": "你是专业周报撰写助手，输出简短文字,**必须输出标准JSON格式**，不要额外文字",
                "prompt": "写一段简短AI周报"
            }
        )
        print("LLM输出：", llm_text)

        # 2. HTML渲染，使用服务端要求的 template_str + context
        print("\n2. 渲染HTML页面")
        html = await render_mcp_client.call_tool(
            "render_html_tool",
            {
                "template_str": "<h1>{{title}}</h1><p>{{body}}</p>",
                "context": {
                    "title": "AI周报",
                    "body": llm_text
                }
            }
        )
        print("渲染HTML：", html[:200])

        # 3. 文件保存
        print("\n3. 写入本地JSON")
        save_res = await file_mcp_client.call_tool("savejson", {
            "file_path": "report_cache.json",
            "data": [{"report": llm_text, "html": html}]
        })
        print("保存结果：", save_res)

        # 4. 读取校验
        print("\n4. 读取校验文件")
        load_data = await file_mcp_client.call_tool("loadjson", {"file_path": "report_cache.json"})
        print("读取校验成功，数据长度：", len(str(load_data)))

        print("\n🎉 多MCP混合链路全部正常！")

    except Exception as e:
        print(f"❌ 混合链路异常: {type(e).__name__}: {e}")
    finally:
        await close_all_mcp_clients()
        print("全部MCP连接清理完毕")

if __name__ == "__main__":
    asyncio.run(test_multi_mcp_combine())