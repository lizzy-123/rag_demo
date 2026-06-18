from langgraph.graph import StateGraph, END
import logging
from .state import AgentState
from .nodes import (
    collect_node, analyze_node, validate_node,
    render_node, send_node, web_search_node
)

def build_agent_graph():
    """RAG分析Agent + 本地SearXNG联网检索 整合流程图"""
    workflow = StateGraph(AgentState)

    workflow.add_node("collect", collect_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("render", render_node)
    workflow.add_node("send", send_node)

    workflow.set_entry_point("collect")
    workflow.add_edge("collect", "analyze")
    workflow.add_edge("render", "send")
    workflow.add_edge("send", END)

    # 1. analyze 后路由
    def route_after_analyze(state: AgentState):
        if state["status"] == "failed":
            return END
        if state["status"] == "analyzed":
            return "validate"
        return "analyze"

    workflow.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"validate": "validate", "analyze": "analyze", END: END}
    )

    # 2. validate 后路由
    def route_after_validate(state: AgentState):
        status = state.get("status")
        error = state.get("error")
        need_web = state.get("need_web_search", False)

        if status == "failed":
            logging.error(f"[Route] 校验失败：{error}，流程终止")
            return END
        if need_web:
            return "web_search"
        if status == "validated":
            return "render"
        return "validate"

    workflow.add_conditional_edges(
        "validate",
        route_after_validate,
        {"web_search": "web_search", "render": "render", "validate": "validate", END: END}
    )

    # ====================== 【修复点】======================
    # 3. 搜索完成 → 直接去渲染，不再回 validate
    def route_after_web_search(state: AgentState):
        s_status = state.get("search_status", "failed")
        if s_status == "completed":
            return "render"  
        return END
    # ======================================================

    workflow.add_conditional_edges(
        "web_search",
        route_after_web_search,
        {"validate": "validate", "render": "render", END: END}
    )

    return workflow.compile()