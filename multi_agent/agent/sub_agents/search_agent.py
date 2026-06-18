# agent/sub_agents/search_agent.py
import logging
from datetime import datetime
from langgraph.graph import StateGraph
from ..state import AgentState
from ..skills.search_skill import searxng_search
from ..skills.file_skill import save_json_file

from ..mcp_client import search_mcp_client,file_mcp_client


#from mcp_servers import MCPClient
#连接到本地MCP Server(子进程/本地服务)
# client =MCPClient(
#     command = "python",
#     args = ["./agent/mcp_servers/search_server.py"]
# )


async def web_search_node(state: AgentState) -> AgentState:
    raw_data = state.get("raw_data", [])
    need_ids = state.get("need_search_ids", [])
    search_results = []

    try:
        for item in raw_data:
            if item.get("id") not in need_ids:
                continue
            q = item["question"]
            logging.info(f"[搜索子Agent] 检索问题: {q}")
            #res_list = searxng_search(q)
            #res_list = client.call_tool("search",{"query":q})
            res_list = await search_mcp_client.call_tool("searxng_search",{"query":q})
            search_results.append({
                "id": item["id"],
                "question": q,
                "web_results": res_list
            })
            if len(search_results) >= 3:
                break

        #save_json_file("search_results.json", search_results)
        await file_mcp_client.call_tool("savejson",{"file_path":"search_results.json",
                                                    "data":search_results})
        # 拼接搜索HTML
        search_html = f"""
<h2>🔍 联网搜索结果报告</h2>
<p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<hr>
"""
        for s in search_results:
            search_html += f"<h4>❓ 问题：{s['question']}</h4>"
            for r in s["web_results"]:
                search_html += f"""
<div style='border-left:4px solid #0d6efd; padding:10px; margin:8px 0; background:#f9fafb;'>
<strong>{r['title']}</strong><br>{r['content']}</div>
"""
        return {
            "web_search_result": search_results,
            "search_status": "completed",
            "search_html": search_html
        }
    except Exception as e:
        logging.error(f"[搜索子Agent] 失败: {e}")
        return {"search_status": "failed", "error": str(e)}

def build_search_agent():
    graph = StateGraph(AgentState)
    graph.add_node("web_search", web_search_node)
    graph.set_entry_point("web_search")
    graph.add_edge("web_search", "__end__")
    return graph.compile()