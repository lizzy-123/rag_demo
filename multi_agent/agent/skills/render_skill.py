# agent/skills/render_skill.py
from jinja2 import Template
from typing import Dict, Any

# 模板常量抽离
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

def render_html(template_str: str, context: Dict[str, Any]) -> str:
    """Skill：Jinja2 HTML渲染"""
    template = Template(template_str)
    return template.render(**context)