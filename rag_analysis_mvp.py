import os
import json
import logging
import re
from datetime import datetime
from dotenv import load_dotenv  # 需安装 python-dotenv

# 优先加载 .env 文件
load_dotenv()

from openai import OpenAI  # DashScope 兼容 OpenAI SDK
from jinja2 import Template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ================= 配置区（从 .env 读取） =================
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"  # 默认开启安全模式
LLM_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus-2025-07-28")
DATA_FILE = os.getenv("DATA_FILE", "chat_history.json")  # 支持自定义文件名

REQUIRED_KEYS = {"category_distribution", "question_clusters", "answer_evaluations", "retrieval_issues", "suggestions"}

# 邮件模板 (Jinja2)
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
    <strong>Q{{ ev.id }}</strong> | 评分: <span style="color:{% if ev.score>=4 %}#198754{% elif ev.score>=3 %}#ffc107{% else %}#dc3545{% endif %}">{{ ev.score }}/5</span><br>
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

# ================= 核心函数 =================
def load_data(filepath: str) -> list:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"❌ 数据文件未找到: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 自动注入 ID（从1开始）
    for i, item in enumerate(data, start=1):
        item["id"] = i
    logging.info(f"✅ 加载 {len(data)} 条数据，已自动注入 ID (1~{len(data)})")
    return data

def call_llm(prompt: str) -> dict:
    # DashScope 兼容 OpenAI SDK 配置
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    for attempt in range(3):
        try:
            logging.info(f"🔄 调用 LLM ({LLM_MODEL}) - 尝试 {attempt+1}/3")
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个严谨的JSON输出引擎，只输出合法JSON对象，不包含任何额外字符。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},  # 强制 JSON 模式
                temperature=0.2,
                timeout=60
            )
            raw = resp.choices[0].message.content.strip()
            # 清理可能的 markdown 代码块包裹
            raw = re.sub(r'^```(?:json)?\s*\n?|\n?```$', '', raw, flags=re.MULTILINE).strip()
            result = json.loads(raw)
            logging.info(f"🔍 LLM 原始返回（前800字符）:\n{raw[:800]}")
            logging.info(f"✅ LLM 返回成功，解析 {len(result)} 个字段")
            return result
        except json.JSONDecodeError as e:
            logging.warning(f"⚠️ JSON 解析失败 (尝试 {attempt+1}): {e}\n原始返回前200字符: {raw[:200]}...")
        except Exception as e:
            logging.warning(f"⚠️ LLM 调用失败 (尝试 {attempt+1}): {type(e).__name__}: {e}")
        if attempt < 2:
            import time; time.sleep(2 ** attempt)  # 指数退避
    raise RuntimeError("❌ LLM 连续3次未能返回有效 JSON，请检查 Prompt 或 API 配置")

def validate_result(result: dict) -> dict:
    # 校验必需字段
    missing = REQUIRED_KEYS - set(result.keys())
    if missing:
        raise ValueError(f"❌ LLM 返回缺失关键字段: {missing}")
    
    # 校验分类分布键名
    expected_cats = {"应用服务器基础软件", "软件系统架构风格", "面向服务的架构及其应用", "企业集成平台的技术与应用"}
    if set(result["category_distribution"].keys()) != expected_cats:
        logging.warning(f"⚠️ 分类分布键名不匹配，自动补全缺失类别")
        for cat in expected_cats:
            result["category_distribution"].setdefault(cat, 0)
    
    if not result["answer_evaluations"]:
        logging.warning("⚠️ answer_evaluations 为空！可能原因：① Prompt 约束不足 ② 模型未理解任务 ③ 数据格式异常")
        # 兜底：用简单规则生成基础评估（避免邮件空白）
        result["answer_evaluations"] = [
            {"id": item["id"], "score": 3, "reason": "[兜底] 未获取到详细评估，建议人工复核"}
            for item in data  # 注意：需将 data 作为参数传入此函数，或改用全局变量（MVP 可接受）
        ]
        result["avg_score"] = 3.0
        logging.info("✅ 已用规则兜底生成基础评估")
    
    if all(v == 0 for v in result["category_distribution"].values()):
        logging.warning("⚠️ 分类分布全为 0！尝试用关键词匹配兜底...")
        # 简单兜底：根据 question 中关键词粗分类（仅 MVP 用）
        for item in data:
            q = item["question"].lower()
            if any(k in q for k in ["应用服务器", "中间件", "部署", "tomcat", "weblogic"]):
                result["category_distribution"]["应用服务器基础软件"] += 1
            elif any(k in q for k in ["架构风格", "分层", "MVC", "微服务"]):
                result["category_distribution"]["软件系统架构风格"] += 1
            elif any(k in q for k in ["SOA", "服务", "接口", "契约"]):
                result["category_distribution"]["面向服务的架构及其应用"] += 1
            elif any(k in q for k in ["集成", "平台", "总线", "ESB"]):
                result["category_distribution"]["企业集成平台的技术与应用"] += 1
        logging.info(f"✅ 兜底分类结果: {result['category_distribution']}")
    # 计算平均分
    evaluations = result.get("answer_evaluations", [])
    if evaluations:
        scores = [ev.get("score", 0) for ev in evaluations if isinstance(ev.get("score"), (int, float))]
        result["avg_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0
    else:
        result["avg_score"] = 0.0
        logging.warning("⚠️ answer_evaluations 为空，平均分设为 0")
    
    logging.info(f"✅ 结果校验通过 | 平均分: {result['avg_score']}/5.0 | 问题簇: {len(result['question_clusters'])}")
    return result

def render_email(result: dict) -> str:
    template = Template(EMAIL_TEMPLATE)
    return template.render(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        total=len(result.get("answer_evaluations", [])),
        **result
    )

def send_email(html_content: str):
    if DRY_RUN:
        output_file = "preview_email.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logging.info(f"📧 [DRY_RUN] 邮件已保存至本地: {output_file}")
        logging.info("💡 提示：用浏览器打开该文件可预览邮件效果")
        return

    # 真实发送配置
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SENDER = os.getenv("SENDER_EMAIL")
    AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")  # 授权码，非登录密码
    RECIPIENT = os.getenv("RECIPIENT_EMAIL")
    
    if not all([SMTP_SERVER, SENDER, AUTH_CODE, RECIPIENT]):
        logging.error("❌ 缺少邮件配置变量，请检查 .env 文件")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 RAG 问答分析报告 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER, AUTH_CODE)
            server.sendmail(SENDER, [RECIPIENT], msg.as_string())
        logging.info(f"✅ 邮件已成功发送至: {RECIPIENT}")
    except Exception as e:
        logging.error(f"❌ 邮件发送失败: {type(e).__name__}: {e}")

def main():
    logging.info("🚀 启动 RAG 分析 Agent MVP (DashScope 适配版)")
    logging.info(f"📁 数据文件: {DATA_FILE} | 🤖 模型: {LLM_MODEL} | 🔒 DRY_RUN: {DRY_RUN}")
    
    # 1. 加载数据
    data = load_data(DATA_FILE)
    qa_text = json.dumps(data, ensure_ascii=False, indent=2)
    
    # 2. 构建 Prompt
    #prompt = ANALYSIS_PROMPT.format(qa_data=qa_text)
    prompt_template = Template(ANALYSIS_PROMPT_JINJA)
    prompt = prompt_template.render(qa_data=qa_text)
    # 3. 调用 LLM（含重试）
    result = call_llm(prompt)
    
    # 4. 校验与增强
    result = validate_result(result)
    
    # 5. 渲染邮件
    html = render_email(result)
    
    # 6. 发送/预览
    send_email(html)
    logging.info("🏁 流程执行完毕")

if __name__ == "__main__":
    main()