from datetime import datetime
import logging, json, re, os
from openai import OpenAI
from jinja2 import Template
from .state import AgentState
import requests  # 用于 SearXNG

# =====  SearXNG 搜索引擎配置（你本地部署的地址）=====
SEARXNG_URL = "http://127.0.0.1:8888/search"
SEARCH_TIMEOUT = 60

# ===== 复用你已有的常量 =====
REQUIRED_KEYS = {"category_distribution", "question_clusters", "answer_evaluations", "retrieval_issues", "suggestions"}
EMAIL_TEMPLATE = """
<h2>📊 RAG 问答分析报告（MVP）｜{{ date }}</h2>
<p>🔹 共分析 <strong>{{ total }}</strong> 条问答记录</p>
<hr>
<h3>📈 问题分类分布</h3>
<ul>
{% for cat, count in category_distribution.items() %}
  <li><strong>{{ cat }}</strong>：{{ count }} 次</li>
{% endfor %}
</ul>

<h3>🔥 高频问题簇</h3>
{% if question_clusters %}
  {% for cluster in question_clusters %}
  <div style="background:#f8f9fa; padding:10px; margin:8px 0; border-left:4px solid #0d6efd; border-radius:4px;">
    <strong>📌 {{ cluster.representative }}</strong><br>
    <small style="color:#666;">分类：{{ cluster.category }} | 频次：{{ cluster.count }} | 相似问：{{ cluster.similar_questions | join(', ') }}</small>
  </div>
  {% endfor %}
{% else %}
  <p>✅ 暂无明显聚集问题</p>
{% endif %}

<h3>⭐ 答案质量评估</h3>
<p>📊 平均分：<strong>{{ avg_score }}</strong> / 5.0</p>
{% for ev in answer_evaluations[:5] %}
  <div style="margin:6px 0; padding:6px; background:#fff; border:1px solid #eee; border-radius:4px;">
    <strong>Q{{ ev.id }}</strong> | 评分: <span style="color:#{% if ev.score>=4 %}#198754{% elif ev.score>=3 %}#ffc107{% else %}#dc3545{% endif %}">{{ ev.score }}/5</span><br>
    <small>{{ ev.reason }}</small>
  </div>
{% endfor %}

<h3>🔍 检索风险提示</h3>
{% if retrieval_issues %}
  <ul>
  {% for issue in retrieval_issues %}<li style="color:#dc3545;">⚠️ {{ issue }}</li>{% endfor %}
  </ul>
{% else %}
  <p style="color:#198754;">✅ 未发现明显检索缺陷</p>
{% endif %}

<h3>💡 改进建议</h3>
<ol>
{% for s in suggestions %}<li>{{ s }}</li>{% endfor %}
</ol>
<hr>
<small style="color:#666;">* 本报告由 RAG 分析 Agent MVP 自动生成，数据截止：{{ date }}</small>
"""

# 分析 Prompt（强约束 JSON 输出）
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

【Few-Shot 示例】（仅参考格式，勿照抄内容）
输入 2 条数据：
[
  {"id":1, "question":"应用服务器和中间件有什么区别？", "answer":"...", "sources":["..."]},
  {"id":2, "question":"论文第三点如何写部署效果？", "answer":"...", "sources":["..."]}
]
期望输出：
{
  "category_distribution": {"应用服务器基础软件": 1, "软件系统架构风格": 0, "面向服务的架构及其应用": 0, "企业集成平台的技术与应用": 1},
  "question_clusters": [
    {"representative": "应用服务器和中间件有什么区别？", "similar_questions": ["中间件与应用服务器异同"], "count": 2, "category": "应用服务器基础软件"}
  ],
  "answer_evaluations": [
    {"id": 1, "score": 4, "reason": "切题且结构清晰，但未引用 sources 中的具体定义"},
    {"id": 2, "score": 5, "reason": "紧扣论文要求，分阶段说明部署效果，无幻觉"}
  ],
  "retrieval_issues": ["来源 1 截断导致关键对比缺失"],
  "suggestions": ["对'区别类'问题补充标准对比模板", "优化文档分块避免跨章节拼接"]
}

【待分析数据】
{{ qa_data }}
"""

def collect_node(state: AgentState) -> AgentState:
    """节点 1: 加载数据 + 自动注入 ID"""
    from datetime import datetime
    data_file = os.getenv("DATA_FILE", "chat_history.json")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    for i, item in enumerate(data, start=1):
        item["id"] = i
    logging.info(f"✅ [Collect] 加载 {len(data)} 条数据")
    return {
        "raw_data": data,
        "status": "collected",
        "retry_count": 0,
        "need_web_search": False,
        "search_status": "idle",
        "search_retry_count": 0,
        "web_search_result": None
    }

def analyze_node(state: AgentState) -> AgentState:
    """节点 2: 调用 LLM 分析（含重试 + 智能提取 JSON）"""
    if state["retry_count"] >= 3:
        return {"status": "failed", "error": "LLM 重试超限"}
    
    raw_data = state["raw_data"]
    if not raw_data:
        logging.error("❌ [Analyze] raw_data 为空！检查 collect_node 是否正常加载")
        return {"status": "failed", "error": "raw_data 为空"}
    
    logging.info(f"🔍 [Analyze] 待分析数据: {len(raw_data)} 条，ID 范围: [{raw_data[0].get('id')}, {raw_data[-1].get('id')}]")

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    qa_text = json.dumps(state["raw_data"], ensure_ascii=False, indent=2)
    logging.info(f"🔍 [Analyze] qa_text 长度: {len(qa_text)} 字符 ≈ {len(qa_text)//4} tokens")
    
    prompt = Template(ANALYSIS_PROMPT_JINJA).render(qa_data=qa_text)
    logging.info(f"🔍 [Analyze] 最终 Prompt 长度: {len(prompt)} 字符 ≈ {len(prompt)//4} tokens")
    MAX_PROMPT_CHARS = 100000  # 安全阈值
    if len(prompt) > MAX_PROMPT_CHARS:
        logging.warning(f"⚠️ [Analyze] Prompt 超长 ({len(prompt)} > {MAX_PROMPT_CHARS})，自动缩减数据条数...")
        low, high = 1, len(raw_data)
        while low < high:
            mid = (low + high + 1) // 2
            test_qa = json.dumps(raw_data[:mid], ensure_ascii=False, indent=2)
            test_prompt = Template(ANALYSIS_PROMPT_JINJA).render(qa_data=test_qa)
            if len(test_prompt) <= MAX_PROMPT_CHARS:
                low = mid
            else:
                high = mid - 1
        raw_data = raw_data[:low]
        qa_text = json.dumps(raw_data, ensure_ascii=False, indent=2)
        prompt = Template(ANALYSIS_PROMPT_JINJA).render(qa_data=qa_text)
        logging.info(f"✅ [Analyze] 已缩减至 {len(raw_data)} 条数据，Prompt 长度: {len(prompt)}")

    try:
        resp = client.chat.completions.create(
            model=os.getenv("DASHSCOPE_MODEL", "qwen-plus-2025-07-28"),
            messages=[
                {"role": "system", "content": "你是一个严谨的 JSON 输出引擎，只输出合法扁平 JSON 对象，5 个字段直接并列，禁止任何额外文字、解释、Markdown。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=60
        )
        raw = resp.choices[0].message.content.strip()
        
        logging.info(f"🔍 [Analyze] LLM 原始返回前 500 字:\n{raw[:500]}")
        
        raw = re.sub(r'^```(?:json)?\s*\n?|\n?```$', '', raw, flags=re.MULTILINE).strip()
        
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            logging.warning("⚠️ [Analyze] 直接解析失败，尝试提取字符串中的 JSON...")
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                json_str = match.group(0)
                logging.info(f"🔍 [Analyze] 提取到 JSON 字符串（前 200 字）: {json_str[:200]}")
                result = json.loads(json_str)
            else:
                raise ValueError("无法从返回内容中提取合法 JSON")
        
        if isinstance(result, dict) and "message" in result:
            msg_content = result["message"]
            logging.warning(f"⚠️ [Analyze] 检测到 message 包装，类型: {type(msg_content).__name__}")
            
            if isinstance(msg_content, str):
                try:
                    result = json.loads(msg_content)
                except json.JSONDecodeError:
                    match = re.search(r'\{[\s\S]*\}', msg_content)
                    if match:
                        result = json.loads(match.group(0))
                    else:
                        logging.error(f"❌ [Analyze] message 内容无法解析: {msg_content[:200]}")
                        raise ValueError("message 内容不是合法 JSON")
            elif isinstance(msg_content, dict):
                result = msg_content
        
        if isinstance(result, dict) and len(result) == 1:
            inner_value = list(result.values())[0]
            if isinstance(inner_value, dict) and any(k in inner_value for k in REQUIRED_KEYS):
                logging.warning("⚠️ [Analyze] 检测到嵌套结构，自动解包")
                result = inner_value
        
        FIELD_MAPPING = {
            "categories": "category_distribution",
            "clusters": "question_clusters",
            "evaluations": "answer_evaluations", 
            "issues": "retrieval_issues",
            "advice": "suggestions"
        }
        for old_key, new_key in FIELD_MAPPING.items():
            if old_key in result and new_key not in result:
                logging.warning(f"⚠️ [Analyze] 字段名映射: {old_key} → {new_key}")
                result[new_key] = result.pop(old_key)
        
        final_keys = list(result.keys()) if isinstance(result, dict) else []
        logging.info(f"✅ [Analyze] 解析成功，最终字段: {final_keys}")
        
        return {
            "analysis_result": result,
            "status": "analyzed",
            "retry_count": state["retry_count"]
        }
        
    except Exception as e:
        logging.warning(f"⚠️ [Analyze] 失败 (尝试 {state['retry_count']+1}): {type(e).__name__}: {e}")
        return {
            "status": "analyzing",
            "retry_count": state["retry_count"] + 1,
            "error": f"{type(e).__name__}: {e}"
        }
    

def validate_node(state: AgentState) -> AgentState:
    """节点 3: 校验结果 + 判断是否需要联网搜索（核心增强）"""
    result = state["analysis_result"]
    missing = REQUIRED_KEYS - set(result.keys())
    if missing:
        return {"status": "failed", "error": f"缺失字段: {missing}"}

    evaluations = result.get("answer_evaluations", [])
    if evaluations:
        scores = [ev.get("score", 0) for ev in evaluations if isinstance(ev.get("score"), (int, float))]
        result["avg_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0
    else:
        result["avg_score"] = 0.0

    # ====================== 新增：判断是否触发联网搜索 ======================
    need_web = False
    raw_data = state.get("raw_data", [])

    for item in raw_data:
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        sources = item.get("sources", [])

        # 触发条件：无知识库、答案差、无法回答
        if (
            len(sources) == 0
            or "无法回答" in a
            or "不知道" in a
            or "暂无信息" in a
            or any(word in q for word in ["明天", "后天", "实时", "最新", "是什么", "怎么办"])
        ):
            need_web = True
            break

    logging.info(f"✅ [Validate] 校验通过 | 平均分: {result['avg_score']}/5.0 | 需要联网: {need_web}")
    # ======================================================================

    return {
        "analysis_result": result,
        "status": "validated",
        "need_web_search": need_web
    }


# ====================== 新增：SearXNG 联网搜索节点 ======================
def web_search_node(state: AgentState) -> AgentState:
    """联网检索：调用本地 SearXNG"""
    raw_data = state.get("raw_data", [])
    search_results = []

    try:
        for item in raw_data[:3]:  # 只搜前3条，避免超时
            q = item.get("question", "")
            if not q:
                continue

            params = {"q": q, "format": "json"}
            resp = requests.get(SEARXNG_URL, params=params, timeout=SEARCH_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            res_list = []
            for r in data.get("results", [])[:2]:
                res_list.append({
                    "title": r.get("title", ""),
                    "content": r.get("content", "")
                })

            search_results.append({
                "id": item.get("id"),
                "question": q,
                "web_results": res_list
            })

        logging.info(f"✅ [WebSearch] 联网检索完成，共 {len(search_results)} 条结果")
        return {
            "web_search_result": search_results,
            "search_status": "completed",
            "need_web_search": False
        }

    except Exception as e:
        logging.error(f"❌ [WebSearch] 失败: {str(e)}")
        return {
            "search_status": "failed",
            "error": f"搜索失败: {str(e)}"
        }

# ====================== 原有渲染、发送节点完全不变 ======================
def render_node(state: AgentState) -> AgentState:
    """节点 4: 渲染邮件 HTML"""
    from datetime import datetime
    template = Template(EMAIL_TEMPLATE)
    html = template.render(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        total=len(state["analysis_result"].get("answer_evaluations", [])),
        **state["analysis_result"]
    )
    logging.info("✅ [Render] 邮件 HTML 生成成功")
    return {
        "html_content": html,
        "status": "rendered"
    }

def send_node(state: AgentState) -> AgentState:
    """节点 5: 发送/预览邮件"""
    DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
    html = state["html_content"]
    
    if DRY_RUN:
        with open("preview_email.html", "w", encoding="utf-8") as f:
            f.write(html)
        logging.info("📧 [Send] [DRY_RUN] 已保存 preview_email.html")
        return {"status": "sent"}
    
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER = os.getenv("SENDER_EMAIL")
    AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    RECIPIENT = os.getenv("RECIPIENT_EMAIL")
    
    if not all([SMTP_SERVER, SENDER, AUTH_CODE, RECIPIENT]):
        return {"status": "failed", "error": "邮件配置不完整"}
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 RAG 分析报告 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(html, "html", "utf-8"))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER, AUTH_CODE)
            server.sendmail(SENDER, [RECIPIENT], msg.as_string())
        logging.info(f"✅ [Send] 邮件已发送至: {RECIPIENT}")
        return {"status": "sent"}
    except Exception as e:
        logging.error(f"❌ [Send] 发送失败: {e}")
        return {"status": "failed", "error": str(e)}