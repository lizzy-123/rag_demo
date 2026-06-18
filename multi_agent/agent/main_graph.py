# agent/main_graph.py
import logging
from langgraph.graph import StateGraph, END
from .state import AgentState
from .sub_agents import (
    data_agent,
    analysis_agent,
    search_agent,
    report_agent
)

# 实例化所有子Agent
data_graph = data_agent.build_data_agent()
analysis_graph = analysis_agent.build_analysis_agent()
search_graph = search_agent.build_search_agent()
report_graph = report_agent.build_report_agent()

# 封装节点：调用子Agent
# def call_data_agent(state: AgentState) -> AgentState:
#     return data_graph.invoke(state)

# def call_analysis_agent(state: AgentState) -> AgentState:
#     return analysis_graph.invoke(state)

# def call_search_agent(state: AgentState) -> AgentState:
#     return search_graph.invoke(state)

# def call_report_agent(state: AgentState) -> AgentState:
#     return report_graph.invoke(state)


async  def call_data_agent(state: AgentState) -> AgentState:
    return await data_graph.ainvoke(state)

async  def call_analysis_agent(state: AgentState) -> AgentState:
    return await analysis_graph.ainvoke(state)

async  def call_search_agent(state: AgentState) -> AgentState:
    return await search_graph.ainvoke(state)

async  def call_report_agent(state: AgentState) -> AgentState:
    return await report_graph.ainvoke(state)

# 路由：分析后判断走向
def route_after_analysis(state: AgentState):
    if state["status"] == "failed":
        logging.error("主流程：分析阶段失败，终止")
        return END
    if state.get("need_web_search"):
        return "call_search"
    return "call_report"

# 路由：搜索后走向
def route_after_search(state: AgentState):
    if state.get("search_status") == "completed":
        return "call_report"
    return END

def build_main_agent():
    main_workflow = StateGraph(AgentState)

    # 注册子Agent调用节点
    main_workflow.add_node("call_data", call_data_agent)
    main_workflow.add_node("call_analysis", call_analysis_agent)
    main_workflow.add_node("call_search", call_search_agent)
    main_workflow.add_node("call_report", call_report_agent)

    # 主流程连线
    main_workflow.set_entry_point("call_data")
    main_workflow.add_edge("call_data", "call_analysis")

    # 分析后分支
    main_workflow.add_conditional_edges(
        "call_analysis",
        route_after_analysis,
        {"call_search": "call_search", "call_report": "call_report", END: END}
    )

    # 搜索后分支
    main_workflow.add_conditional_edges(
        "call_search",
        route_after_search,
        {"call_report": "call_report", END: END}
    )

    main_workflow.add_edge("call_report", END)
    return main_workflow.compile()