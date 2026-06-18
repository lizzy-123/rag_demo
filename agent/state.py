from typing import TypedDict, List, Optional, Any

class AgentState(TypedDict):
    """Agent 全局状态，所有节点共享读写"""
    raw_data: List[dict]          # 原始问答（含自动注入的 id）
    analysis_result: Optional[dict]  # LLM 分析结果（JSON）
    html_content: Optional[str]   # 渲染后的邮件 HTML
    status: str                   # 当前状态: "pending" | "analyzing" | "validated" | "rendered" | "sent" | "failed"
    error: Optional[str]          # 错误信息（用于调试）
    retry_count: int              # 分析重试次数

    #==============新增：SearXng联网搜索专用字段
    need_web_search:bool
    search_status:str             #搜索状态：idle/running/completed/failed
    search_retry_count:int        #搜索重试次数(防止死循环)
    web_search_result:Any         #联网搜索返回的结果(JSON?文本)
    final_answer_source:str       #答案来源：rag/web_search
    need_search_ids: List[int]
    search_html: Optional[str]

    