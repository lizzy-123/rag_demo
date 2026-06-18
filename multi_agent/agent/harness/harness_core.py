# agent/harness/harness_core.py
import logging
from dotenv import load_dotenv
from typing import Dict,Callable
from ..state import AgentState



#全局初始化(统一配置、日志、环境加载)

def init_env():
    load_dotenv()
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    #通用运行器：统一封装调用、状态初始化、异常捕获

def run_agent(
        agent_graph:Callable,
        init_state:AgentState,
        agent_name:str = "agent"
)->AgentState:
    logger = logging.getLogger(f"Harness-{agent_name}")
    logging.info(f"===={agent_name}开始执行====")
    try:
        final_state = agent_graph.invoke(init_state)
        logging.info(f"==={agent_name}执行完成====")
        return final_state
    except Exception as e:
        logger.error(f"【harness捕获异常】{agent_name}运行失败:{str(e)}",exc_info = True)
        init_state["status"] = "failed"
        init_state["error"] = str(e)

        return init_state
def build_default_state()->AgentState:
    return{
        "raw_data":[],
                "analysis_result":{},
        "web_search_result":{},
        "html_content":"",
        "search_html":"",
        "status":"",
        "error":None,
        "retry_count":0,
        "need_search_ids":[],
        "search_status":"idle",
        "search_retry_count":0
    }    
