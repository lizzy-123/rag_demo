# agent/sub_agents/data_agent.py
# import os
# import logging
# from langgraph.graph import StateGraph
# from ..state import AgentState
# from ..skills.file_skill import load_json_file

# def data_load_node(state: AgentState) -> AgentState:
#     logging.info(f"【执行加载data_load_node】")
#     data_file = os.getenv("DATA_FILE", "chat_history.json")
#     raw_data = load_json_file(data_file)
#     # 给每条数据加ID
#     for idx, item in enumerate(raw_data, start=1):
#         item["id"] = idx
#     logging.info(f"[数据子Agent] 加载 {len(raw_data)} 条数据")
#     return {
#         "raw_data": raw_data,
#         "status": "collected",
#         "retry_count": 0,
#         "need_web_search": False
#     }

# def build_data_agent():
#     graph = StateGraph(AgentState)
#     graph.add_node("load_data", data_load_node)
#     graph.set_entry_point("load_data")
#     graph.add_edge("load_data", "__end__")
#     return graph.compile()


import os
import logging
from langgraph.graph import StateGraph # type: ignore
from ..mcp_client import file_mcp_client
from ..state import AgentState
import json
#from ..skills.file_skill import load_json_file

# 1. 实例化客户端：自动化拉起 file_server子进程


async def data_load_node(state: AgentState) -> AgentState:
    logging.info(f"【执行加载data_load_node】")
    data_file = os.getenv("DATA_FILE", "chat_history.json")
    #raw_data = load_json_file(data_file)
    #===替换为MCP调用=========
    data_list  = await file_mcp_client.call_tool(
        tool_name="loadjson",
        arguments={"file_path": data_file}
    )
    logging.info(f"【调试】MCP返回类型: {type(data_list)}, 内容: {data_list}")
 
    # # 第一步：先判断返回是否为空字符串
    # if not raw_str or raw_str.strip() == "":
    #     logging.warning(f"【数据加载】文件 {data_file} 内容为空，无历史对话数据")
    #     data_list = []
    # else:
    #     # 关键：把MCP返回的JSON字符串转成Python对象
    #     try:
    #         raw_data = json.loads(raw_str)
    #         logging.info(f"【数据加载】JSON解析成功，原始类型: {type(raw_data)}")
    #     except json.JSONDecodeError as e:
    #         logging.error(f"【数据加载】文件 {data_file} JSON解析失败: {str(e)}，原始内容: {raw_str[:200]}...")
    #         data_list = []
    #         raw_data = None

    #     # 标准化统一成列表
    #     data_list = []
    #     if isinstance(raw_data, list):
    #         data_list = raw_data
    #         logging.info(f"【数据加载】读取到数组，长度: {len(data_list)}")
    #     elif isinstance(raw_data, dict):
    #         data_list = [raw_data]
    #         logging.info(f"【数据加载】顶层为单个字典，自动包装为数组")
    #     else:
    #         logging.warning(f"【数据加载】数据非数组/字典，丢弃")
    #         data_list = []

    # # 遍历加ID，只处理字典
    # for idx, item in enumerate(data_list, start=1):
    #     if isinstance(item, dict):
    #         item["id"] = idx
    #     else:
    #         logging.warning(f"【数据加载】第{idx}条不是字典，跳过ID赋值: {item}")


    # 兜底转列表，兼容异常
    if not isinstance(data_list, list):
        if isinstance(data_list, dict):
            data_list = [data_list]
        else:
            logging.warning(f"【数据加载】文件数据为空或格式非法")
            data_list = []

    # 给每条字典数据添加id
    for idx, item in enumerate(data_list, start=1):
        if isinstance(item, dict):
            item["id"] = idx
        else:
            logging.warning(f"【数据加载】第{idx}条非字典，跳过ID赋值")

    logging.info(f"[数据子Agent] 最终有效数据条数 {len(data_list)}")
    return {
        "raw_data": data_list,
        "status": "collected",
        "retry_count": 0,
        "need_web_search": False
    }

def build_data_agent():
    graph = StateGraph(AgentState)
    graph.add_node("load_data", data_load_node)
    graph.set_entry_point("load_data")
    graph.add_edge("load_data", "__end__")
    return graph.compile()