from .harness.harness_core import init_env,build_default_state
from .sub_agents.data_agent import build_data_agent
from .sub_agents.analysis_agent import build_analysis_agent
from .sub_agents.search_agent import build_search_agent


if __name__=="main__":
    init_env()
    base_state = build_default_state()

    #单独测试，数据加载字agent
    print("===测试数据Agent===")
    #run_agent(build_data_agent(),base_state.copy(),"数据子Agent")

    #单独测试，分析字Agent
    print("测试分析Agent===")
    #run_agent(build_analysis_agent(),base_state.copy(),"分析字Agent")

    #单独测试，搜索Agent
    print("测试分析Agent====")
    #run_agent(build_default_state(),base_state.copy(),"搜索字Agent")

    
