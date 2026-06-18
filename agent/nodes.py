from datetime import datetime
import logging, json, re, os
from openai import OpenAI
from jinja2 import Template
from .state import AgentState
import requests

# ===== SearXNG 配置 =====
SEARXNG_URL = "http://127.0.0.1:8888/search"
SEARCH_TIMEOUT = 15

# ===== 常量 =====
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

【待分析数据】
{{ qa_data }}
"""

# ========================== 节点 1：数据加载 ==========================
def collect_node(state: AgentState) -> AgentState:
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

# ========================== 节点 2：LLM 分析 ==========================
def analyze_node(state: AgentState) -> AgentState:
    if state["retry_count"] >= 3:
        return {"status": "failed", "error": "LLM 重试超限"}
    
    raw_data = state["raw_data"]
    if not raw_data:
        return {"status": "failed", "error": "raw_data 为空"}

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    qa_text = json.dumps(raw_data, ensure_ascii=False, indent=2)
    prompt = Template(ANALYSIS_PROMPT_JINJA).render(qa_data=qa_text)

    try:
        resp = client.chat.completions.create(
            model=os.getenv("DASHSCOPE_MODEL", "qwen3.6-plus"),
            messages=[
                {"role": "system", "content": "你是一个严谨的 JSON 输出引擎，只输出合法扁平 JSON 对象，5 个字段直接并列，禁止任何额外文字、解释、Markdown。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=120
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*\n?|\n?```$', '', raw, flags=re.MULTILINE).strip()
        
        match = re.search(r'\{[\s\S]*\}', raw)
        result = json.loads(match.group(0)) if match else json.loads(raw)
        
        logging.info(f"✅ [Analyze] 解析成功，字段：{list(result.keys())}")
        return {
            "analysis_result": result,
            "status": "analyzed",
            "retry_count": state["retry_count"]
        }
        
    except Exception as e:
        logging.warning(f"⚠️ [Analyze] 失败 {state['retry_count']+1}: {e}")
        return {
            "status": "analyzing",
            "retry_count": state["retry_count"] + 1
        }

# ========================== 节点 3：校验 + 联网判断 ==========================
def validate_node(state: AgentState) -> AgentState:
    result = state["analysis_result"]
    missing = REQUIRED_KEYS - set(result.keys())
    if missing:
        return {"status": "failed", "error": f"缺失字段: {missing}"}

    scores = [ev.get("score", 0) for ev in result.get("answer_evaluations", [])]
    result["avg_score"] = round(sum(scores)/len(scores), 2) if scores else 0.0

    need_web = False
    need_search_ids = []
    for item in state.get("raw_data", []):
        q = str(item.get("question", ""))
        a = str(item.get("answer", ""))
        sources = item.get("sources", [])
        if len(sources)==0 or "无法回答" in a or "不知道" in a or any(w in q for w in ["实时","最新","是什么","怎么办"]):
            need_web = True
            need_search_ids.append(item.get("id"))

    logging.info(f"✅ [Validate] 平均分：{result['avg_score']} | 需要联网：{need_web} | 待搜索ID：{need_search_ids}")
    return {
        "analysis_result": result,
        "status": "validated",
        "need_web_search": need_web,
        "need_search_ids": need_search_ids
    }

# ========================== 节点 4：联网搜索 + 生成搜索报告 ==========================
def web_search_node(state: AgentState) -> AgentState:
    raw_data = state.get("raw_data", [])
    need_ids = state.get("need_search_ids", [])
    search_results = []

    try:
        for item in raw_data:
            if item.get("id") not in need_ids:
                continue
            q = item["question"]
            logging.info(f"🔍 正在搜索：{q}")

            resp = requests.get(SEARXNG_URL, params={"q": q, "format": "json"}, timeout=SEARCH_TIMEOUT)
            data = resp.json()
            res_list = [{"title": r.get("title",""), "content": r.get("content","")} for r in data.get("results", [])[:3]]
            
            search_results.append({
                "id": item["id"],
                "question": q,
                "web_results": res_list
            })
            if len(search_results) >= 3:
                break

        # 保存搜索结果
        with open("search_results.json", "w", encoding="utf-8") as f:
            json.dump(search_results, f, ensure_ascii=False, indent=2)

        # 生成搜索 HTML
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
        logging.info(f"✅ [WebSearch] 搜索完成：{len(search_results)} 条，已保存到 search_results.json")
        return {
            "web_search_result": search_results,
            "search_status": "completed",
            "need_web_search": False,
            "search_html": search_html
        }
    except Exception as e:
        logging.error(f"❌ [WebSearch] 失败：{e}")
        return {"search_status": "failed", "error": str(e)}

# ========================== 节点 5：渲染报告 ==========================
def render_node(state: AgentState) -> AgentState:
    html = Template(EMAIL_TEMPLATE).render(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        total=len(state["analysis_result"].get("answer_evaluations", [])),
        **state["analysis_result"]
    )
    logging.info("✅ [Render] 分析报告 HTML 已生成")
    return {"html_content": html, "status": "rendered"}

# ========================== 节点 6：发送双邮件 ==========================
def send_node(state: AgentState) -> AgentState:
    DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
    html = state["html_content"]
    search_html = state.get("search_html", "")

    if DRY_RUN:
        with open("preview_analysis.html", "w", encoding="utf-8") as f:
            f.write(html)
        if search_html:
            with open("preview_search.html", "w", encoding="utf-8") as f:
                f.write(search_html)
        logging.info("📧 [DRY_RUN] 预览文件已保存")
        return {"status": "sent"}

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SENDER = os.getenv("SENDER_EMAIL")
    AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    RECIPIENT = os.getenv("RECIPIENT_EMAIL")

    def send(title, content):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = SENDER
        msg["To"] = RECIPIENT
        msg.attach(MIMEText(content, "html", "utf-8"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER, AUTH_CODE)
            server.sendmail(SENDER, [RECIPIENT], msg.as_string())

    try:
        send("📊 RAG 分析报告", html)
        if search_html:
            send("🔍 联网搜索报告", search_html)
        logging.info("✅ [Send] 双邮件发送成功")
        return {"status": "sent"}
    except Exception as e:
        logging.error(f"❌ [Send] 失败：{e}")
        return {"status": "failed", "error": str(e)}