# agent/harness/test_harness.py
from unittest.mock import patch, MagicMock
from .harness_core import init_env, build_default_state, run_agent
from .registry import run_task

# 全局初始化一次环境、日志
init_env()

# ====================== 1、逐个单元测试所有底层Skill ======================
@patch("os.getenv")
@patch("smtplib.SMTP")
def test_email_skill(mock_smtp, mock_os_env):
    """测试邮件发送，Mock SMTP和环境变量，不会真实发邮件"""
    mock_os_env.side_effect = lambda k, default=None: {
        "SMTP_SERVER": "smtp.mock.com",
        "SMTP_PORT": "587",
        "SENDER_EMAIL": "test@mock.com",
        "EMAIL_AUTH_CODE": "mock_code123",
        "RECIPIENT_EMAIL": "recv@mock.com"
    }.get(k, default)
    # mock smtp上下文管理器
    mock_conn = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_conn
    res = run_task("send_email", subject="测试单元测试邮件", html_content="<h1>测试内容</h1>")
    print("[测试send_email] ->", res)


@patch("builtins.open")
@patch("json.load")
def test_load_json_skill(mock_json_load, mock_open_file):
    """Mock文件，不读写本地磁盘"""
    mock_json_load.return_value = [
        {"id": 1, "question": "应用服务器是什么", "answer": "测试答案", "sources": []}
    ]
    data = run_task("load_json_file", file_path="mock_data.json")
    print("[测试load_json_file] ->读取数据条数：", len(data))


@patch("builtins.open")
@patch("json.dump")
def test_save_json_skill(mock_json_dump, mock_open_file):
    save_data = [{"id": 1, "q": "测试"}]
    run_task("save_json_file", file_path="save_mock.json", data=save_data)
    print("[测试save_json_file] 执行完成")


@patch("os.getenv")
@patch("multi_agent.agent.skills.llm_skill.OpenAI")
def test_llm_skill(mock_openai_cls, mock_os_env):
    """Mock大模型，不消耗真实token计费"""
    mock_os_env.side_effect = lambda k, default=None: {
        "DASHSCOPE_API_KEY": "mock_key",
        "DASHSCOPE_MODEL": "qwen-mock"
        }.get(k, default)
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '''
    {
        "category_distribution":{"应用服务器基础软件":1,"软件系统架构风格":0,"面向服务的架构及其应用":0,"企业集成平台的技术与应用":0},
        "question_clusters":[],
        "answer_evaluations":[{"id":1,"score":4,"reason":"回答规范"}],
        "retrieval_issues":[],
        "suggestions":["优化知识库文档"]
    }
    '''
    mock_client.chat.completions.create.return_value = mock_resp
    mock_openai_cls.return_value = mock_client

    llm_result = run_task("call_llm", prompt="测试prompt", system_prompt="输出json", temperature=0.1)
    print("[测试call_llm] ->LLM分类统计：", llm_result["category_distribution"])


@patch("requests.get")
def test_searxng_skill(mock_req_get):
    """Mock联网搜索，不请求SearXNG服务"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [{"title": "架构知识点", "content": "测试搜索内容"}]
    }
    mock_req_get.return_value = mock_resp
    search_res = run_task("searxng_search", query="软件架构")
    print("[测试searxng_search] ->搜索结果数：", len(search_res))


def test_render_html_skill():
    """渲染模板无IO，无需Mock，直接运行"""
    from ..skills.render_skill import EMAIL_TEMPLATE
    ctx = {
        "date": "2025-12-01",
        "total": 1,
        "category_distribution": {"应用服务器基础软件":1},
        "question_clusters": [],
        "answer_evaluations": [{"id":1,"score":4,"reason":"ok"}],
        "avg_score":4.0,
        "retrieval_issues":[],
        "suggestions":["优化数据"]
    }
    html = run_task("render_html", template_str=EMAIL_TEMPLATE, context=ctx)
    print("[测试render_html] HTML长度：", len(html))

# ====================== 2、分步单独测试各个子Agent ======================
@patch("multi_agent.agent.skills.file_skill.load_json_file")
def test_data_agent(mock_load_json):
    """单独测试data_agent，Mock加载文件，不读真实json"""
    mock_load_json.return_value = [{"question":"测试问题","answer":"答案","sources":[]}]
    state = build_default_state()
    # 1. 获取图实例 2. 执行agent 3. 拿到最终状态字典
    graph = run_task("build_data_agent")
    out_state = run_agent(graph, state)
    print("[单测build_data_agent] raw_data长度：", len(out_state["raw_data"]))


@patch("multi_agent.agent.skills.llm_skill.call_llm")
def test_analysis_agent(mock_call_llm):
    """绕过data，手动构造raw_data，单独测分析Agent"""
    mock_call_llm.return_value = {
        "category_distribution":{"应用服务器基础软件":1,"软件系统架构风格":0,"面向服务的架构及其应用":0,"企业集成平台的技术与应用":0},
        "question_clusters":[],
        "answer_evaluations":[{"id":1,"score":4,"reason":"回答准确"}],
        "retrieval_issues":[],
        "suggestions":["扩充知识库"]
    }
    init_st = build_default_state()
    init_st["raw_data"] = [{"id":1,"question":"测试","answer":"ans","sources":[]}]
    graph = run_task("build_analysis_agent")
    ana_state = run_agent(graph, init_st)
    print("[build_analysis_agent] 平均分：", ana_state["analysis_result"]["avg_score"])


@patch("multi_agent.agent.skills.email_skill.send_email")
@patch("multi_agent.agent.skills.file_skill.save_json_file")
def test_report_agent(mock_save, mock_send_mail):
    """手动注入analysis_result，跳过data、analysis，只测报表渲染发送"""
    st = build_default_state()
    st["analysis_result"] = {
        "category_distribution":{"应用服务器基础软件":1},
        "question_clusters":[],
        "answer_evaluations":[{"id":1,"score":4,"reason":"ok"}],
        "avg_score":4.0,
        "retrieval_issues":[],
        "suggestions":["优化"]
    }
    graph = run_task("build_report_agent")
    report_out = run_agent(graph, st)
    print("[单测report_agent] 最终状态：", report_out["status"])


# 只保留文件保存的patch，去掉搜索相关patch，在函数内部mock
@patch("multi_agent.agent.skills.file_skill.save_json_file")
def test_search_agent(mock_save):
    """单独测试搜索Agent"""
    st = build_default_state()
    st["raw_data"] = [{"id":1,"question":"实时架构","answer":"","sources":[]}]
    st["need_search_ids"] = [1]

    graph = run_task("build_search_agent")
    # 执行前，手动mock内部依赖（绕过模块查找问题）
    # 如果内部是 from xxx import client，就在当前作用域临时替换
    import multi_agent.agent.sub_agents.search_agent as sa
    sa.client = MagicMock()
    sa.client.call_tool.return_value = [{"title":"搜索标题","content":"搜索详情"}]

    search_out = run_agent(graph, st)
    print("[单测search_agent] 搜索状态：", search_out["search_status"])

# ======================3、全链路集成测试main_agent ======================
# 原：@patch("multi_agent.agent.sub_agents.search_agent.client")
# 替换为和上面一致的路径
@patch("multi_agent.agent.sub_agents.search_agent.call_tool")
@patch("multi_agent.agent.skills.email_skill.send_email")
@patch("multi_agent.agent.skills.llm_skill.call_llm")
@patch("multi_agent.agent.skills.file_skill.load_json_file")
def test_main_full_flow(mock_load, mock_llm, mock_send, mock_call_tool):
    mock_load.return_value = [{"id":1,"question":"软件架构","answer":"测试答案","sources":[]}]
    mock_llm.return_value = {
        "category_distribution":{"应用服务器基础软件":1,"软件系统架构风格":0,"面向服务的架构及其应用":0,"企业集成平台的技术与应用":0},
        "question_clusters":[],
        "answer_evaluations":[{"id":1,"score":4,"reason":"ok"}],
        "retrieval_issues":[],
        "suggestions":["优化知识库"]
    }
    mock_call_tool.return_value = [{"title":"网页","content":"内容"}]
    init_state = build_default_state()
    graph = run_task("main_agent")
    final_state = run_agent(graph, init_state)
    print("[全链路main_agent测试结束，最终状态：]", final_state["status"])

# 统一入口执行所有用例
if __name__ == "__main__":
    # 测试skill
    test_email_skill()
    test_load_json_skill()
    test_save_json_skill()
    test_llm_skill()
    #test_searxng_skill()
    test_render_html_skill()

    # 单测各个子agent
    test_data_agent()
    test_analysis_agent()
    test_report_agent()
   # test_search_agent()

    # 全流程集成测试
    #test_main_full_flow()