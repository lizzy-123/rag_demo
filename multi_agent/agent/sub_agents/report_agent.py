# # agent/sub_agents/report_agent.py
# import os
# import logging
# from datetime import datetime
# from langgraph.graph import StateGraph
# from ..state import AgentState
# from ..skills.render_skill import render_html, EMAIL_TEMPLATE
# from ..skills.email_skill import send_email
# from ..skills.file_skill import save_json_file

# def render_node(state: AgentState) -> AgentState:
#     context = {
#         "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
#         "total": len(state["analysis_result"].get("answer_evaluations", [])),
#         **state["analysis_result"]
#     }
#     html = render_html(EMAIL_TEMPLATE, context)
#     logging.info("[报告子Agent] HTML报告渲染完成")
#     return {"html_content": html, "status": "rendered"}

# def send_node(state: AgentState) -> AgentState:
#     dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
#     html = state["html_content"]
#     search_html = state.get("search_html", "")

#     if dry_run:
#         save_json_file("preview_analysis.html", html)
#         if search_html:
#             save_json_file("preview_search.html", search_html)
#         logging.info("[报告子Agent] 预览文件已生成")
#         return {"status": "sent"}

#     try:
#         send_email("📊 RAG 分析报告", html)
#         if search_html:
#             send_email("🔍 联网搜索报告", search_html)
#         logging.info("[报告子Agent] 邮件发送成功")
#         return {"status": "sent"}
#     except Exception as e:
#         logging.error(f"[报告子Agent] 邮件发送失败: {e}")
#         return {"status": "failed", "error": str(e)}

# def build_report_agent():
#     graph = StateGraph(AgentState)
#     graph.add_node("render", render_node)
#     graph.add_node("send", send_node)
#     graph.set_entry_point("render")
#     graph.add_edge("render", "send")
#     graph.add_edge("send", "__end__")
#     return graph.compile()



# agent/sub_agents/report_agent.py
import os
import logging
from datetime import datetime
from langgraph.graph import StateGraph
from ..state import AgentState
from ..mcp_client import render_mcp_client,email_mcp_client,file_mcp_client



async def render_node(state: AgentState) -> AgentState:
    template = await render_mcp_client.call_tool("get_email_template",{})

    context = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(state["analysis_result"].get("answer_evaluations", [])),
        **state["analysis_result"]
    }
    html = await render_mcp_client.call_tool(
        "render_html_tool",
          {"template_str":template,"context":context}
        )
    logging.info("[报告子Agent] HTML报告渲染完成")
    return {"html_content": html, "status": "rendered"}

async def send_node(state: AgentState) -> AgentState:
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    html = state["html_content"]
    search_html = state.get("search_html", "")

    if dry_run:
        await file_mcp_client.call_tool("savejson", {"file_path": "preview_analysis.html", "data": html})
        if search_html:
            await file_mcp_client.call_tool("savejson", {"file_path": "preview_search.html", "data": search_html})
        logging.info("[报告子Agent] 预览文件已生成")
        return {"status": "sent"}

    try:
        await email_mcp_client.call_tool(
            "send_email",
            {"subject": "📊 RAG 分析报告", "html_content": html}
        )
        if search_html:
            await email_mcp_client.call_tool(
                "send_email",
                {"subject": "🔍 联网搜索报告", "html_content": search_html}
            )
        logging.info("[报告子Agent] 邮件发送成功")
        return {"status": "sent"}
    except Exception as e:
        logging.error(f"[报告子Agent] 邮件发送失败: {e}")
        return {"status": "failed", "error": str(e)}
def build_report_agent():
    graph = StateGraph(AgentState)
    graph.add_node("render", render_node)
    graph.add_node("send", send_node)
    graph.set_entry_point("render")
    graph.add_edge("render", "send")
    graph.add_edge("send", "__end__")
    return graph.compile()

