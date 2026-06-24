# main.py
from .agent.main_graph import build_main_agent
from .agent.harness.harness_core import init_env,build_default_state,run_agent
from .agent.harness.registry import run_task
import asyncio
from .agent.mcp_client import close_all_mcp_clients,start_all_mcp_clients
#死循环诱因
#忘记设置终止节点，没有指向END,节点执行完又跳回自己，无出口：
#State字段永远满足循环条件

async def main():
    init_env()
    await start_all_mcp_clients()
    init_state = build_default_state()
    main_agent = build_main_agent()
    
    try:
        result = await main_agent.ainvoke(init_state)
        return result
    finally:
        # 程序结束销毁所有MCP子进程
        await close_all_mcp_clients()

if __name__=="__main__":
    asyncio.run(main())
    #1. Harness 统一初始化环境
    #init_env()

    #场景1：调用单个工具skill
    #res = run_task("send_email",subject="测试",html_content="<h1>hello</h1>")
    #场景2：构建标准初始化状态
    #init_state = build_default_state()
    #使用harmess 运行主Agent
    #init_state = build_main_agent()
    #final_state = run_task("build_main_agent")
    #final_state.invoke(init_state)

    #data_graph  = run_task("build_data_agent")
    #data_graph.invoke(init_state)
    #data_graph  = run_task("build_report_agent")
    #final_state = run_agent(data_graph , init_state, agent_name="build_report_agent")

    #data_graph.invoke(init_state)

    #final_state = run_agent(data_graph , init_state, agent_name="DataAgent")
    #print("Agent运行结果state：", final_state)
    #skill_res  = run_task("searxng_search", query="最近有什么agent相关新闻")
    #print("skill结果：", skill_res)
    # #2. stream 分布看运行
    # for s in final_state.stream(init_state):
    #     print("data单步：",s)

    # res = final_state.invoke(final_state)
    # print("最终结果：",res)    


    