# agent/harness/registry.py
from typing import Dict,Callable,Any
from .harness_core import run_agent

#导入skill
from ..skills.email_skill import send_email
from ..skills.file_skill import load_json_file,save_json_file
from ..skills.llm_skill import call_llm
from ..skills.render_skill import render_html
from ..skills.search_skill import searxng_search

#导入agent构建
from ..sub_agents.analysis_agent import build_analysis_agent
from ..sub_agents.data_agent import build_data_agent
from ..sub_agents.report_agent import build_report_agent
from ..sub_agents.search_agent import build_search_agent
from ..main_graph import build_main_agent

#skill注册表(普通函数，直接入参执行)
SKILL_REGISTRY:Dict[str,Callable[...,Any]]={
    "send_email":send_email,
    "load_json_file":load_json_file,
    "save_json_file":save_json_file,
    "call_llm":call_llm,
    "render_html":render_html,
    "searxng_search":searxng_search,
}

#Agent注册表，包装成通过harness.run_agent执行
AGENT_REGISTRY:Dict[str,Callable[...,Any]]={
    "build_analysis_agent":build_analysis_agent,
    "build_data_agent":build_data_agent,
    "build_report_agent":build_report_agent,
    "build_search_agent":build_search_agent,
    "build_main_agent":build_main_agent
}

ALL_REGISTRY={**SKILL_REGISTRY,**AGENT_REGISTRY}

def run_task(task_name:str,**kwargs):
    if task_name not in ALL_REGISTRY:
        raise KeyError(f"不存在任务:{task_name}")
    return ALL_REGISTRY[task_name](**kwargs)
    


