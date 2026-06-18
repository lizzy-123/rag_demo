# agent/sub_agents/analysis_agent.py
import logging
from langgraph.graph import StateGraph
from jinja2 import Template
from ..state import AgentState
#from ..skills.llm_skill import call_llm
from ..mcp_client import llm_mcp_client
import asyncio


REQUIRED_KEYS = {"category_distribution", "question_clusters", "answer_evaluations", "retrieval_issues", "suggestions"}

ANALYSIS_PROMPT_JINJA = """你是一个软考架构师辅导专家 & RAG 系统分析师。请严格按以下要求输出**纯 JSON 对象**，禁止任何额外文本、Markdown、解释或注释。

【固定分类】（必须且只能从以下 4 类中选择，不可自创/合并/省略）
["应用服务器基础软件", "软件系统架构风格", "面向服务的架构及其应用", "企业集成平台的技术与应用"]

【分析任务】
1. 问题分类：遍历每条问答，根据其内容归入上述 4 类之一，统计分布
2. 聚集检测：找出语义相近或考点重复的问题簇（≥2 条即算），列出代表问题、相似问法、频次、对应分类
3. 答案评估：为**每条问答**（按 id）打分 (1-5)。标准：①是否切题 ②是否紧扣给定 sources ③结构是否清晰 ④有无幻觉/过度延伸
4. 检索质量：指出 sources 存在的问题（如截断严重、跨主题混杂、关键信息缺失、来源无关等）
5. 改进建议：给出 2-3 条针对知识库/Prompt/检索策略的落地建议

【输出格式】（字段名/类型/顺序必须完全一致，值不能为空）
{
  "category_distribution": {"应用服务器基础软件": 整数, "软件系统架构风格": 整数, "面向服务的架构及其应用": 整数, "企业集成平台的技术与应用": 整数},
  "question_clusters": [{"representative": "字符串", "similar_questions": ["字符串"], "count": 整数, "category": "字符串"}],
  "answer_evaluations": [{"id": 整数, "score": 整数, "reason": "字符串"}],
  "retrieval_issues": ["字符串"],
  "suggestions": ["字符串"]
}

【待分析数据】
{{ qa_data }}
"""

async  def llm_analyze_node(state: AgentState) -> AgentState:
    if state["retry_count"] >= 3:
        return {"status": "failed", "error": "LLM 重试超限"}
    
    raw_data = state["raw_data"]
    if not raw_data:
        return {"status": "failed", "error": "raw_data 为空"}

    qa_text = Template(ANALYSIS_PROMPT_JINJA).render(qa_data=raw_data)
    system_prompt = "你是一个严谨的 JSON 输出引擎，只输出合法扁平 JSON 对象，禁止任何额外文字。"
    try:
        #analysis_res = call_llm(prompt=qa_text, system_prompt=system_prompt)
        analysis_res = await llm_mcp_client.call_tool(
            "call_llm_tool",
            {"prompt":qa_text,"system_prompt":system_prompt}
        )
        return {
            "analysis_result": analysis_res,
            "status": "analyzed",
            "retry_count": state["retry_count"]
        }
    except Exception as e:
        logging.warning(f"LLM分析失败 重试次数:{state['retry_count']+1} {e}")
        return {
            "status": "analyzing",
            "retry_count": state["retry_count"] + 1
        }

def validate_node(state: AgentState) -> AgentState:
    res = state["analysis_result"]
    missing = REQUIRED_KEYS - set(res.keys())
    if missing:
        return {"status": "failed", "error": f"缺失字段: {missing}"}

    # 计算平均分
    scores = [ev.get("score", 0) for ev in res.get("answer_evaluations", [])]
    res["avg_score"] = round(sum(scores)/len(scores), 2) if scores else 0.0

    # 判断是否需要联网搜索
    need_web = False
    need_ids = []
    for item in state.get("raw_data", []):
        q = str(item.get("question", ""))
        a = str(item.get("answer", ""))
        sources = item.get("sources", [])
        if len(sources)==0 or "无法回答" in a or "不知道" in a or any(w in q for w in ["实时","最新","是什么","怎么办"]):
            need_web = True
            need_ids.append(item.get("id"))

    logging.info(f"[分析子Agent] 平均分:{res['avg_score']} 是否联网:{need_web}")
    return {
        "analysis_result": res,
        "status": "validated",
        "need_web_search": need_web,
        "need_search_ids": need_ids
    }

# 重试路由
def route_analyze(state: AgentState):
    if state["status"] == "failed":
        return "__end__"
    if state["status"] == "analyzed":
        return "validate"
    return "llm_analyze"

def build_analysis_agent():
    graph = StateGraph(AgentState)
    graph.add_node("llm_analyze", llm_analyze_node)
    graph.add_node("validate", validate_node)
    graph.set_entry_point("llm_analyze")

    graph.add_conditional_edges(
        "llm_analyze",
        route_analyze,
        {"llm_analyze": "llm_analyze", "validate": "validate", "__end__": "__end__"}
    )
    graph.add_edge("validate", "__end__")
    return graph.compile()