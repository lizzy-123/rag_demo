# agent/state.py
from typing import TypedDict, List, Dict, Any, Optional

# 全局主状态（主Agent流转使用）
class AgentState(TypedDict):
    raw_data: List[Dict[str, Any]]
    analysis_result: Dict[str, Any]
    web_search_result: List[Dict[str, Any]]
    html_content: str
    search_html: str
    status: str
    error: Optional[str]
    retry_count: int
    need_web_search: bool
    need_search_ids: List[int]
    search_status: str
    search_retry_count: int