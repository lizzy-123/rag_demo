# agent/skills/llm_skill.py
import os
import re
import json
import logging
from openai import OpenAI
from typing import Dict, Any

def call_llm(prompt: str, system_prompt: str, temperature: float = 0.1, timeout: int = 120) -> Dict[str, Any]:
    """Skill：通用LLM调用，输出JSON"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = os.getenv("DASHSCOPE_MODEL", "qwen3.6-plus")

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            timeout=timeout
        )
        content = resp.choices[0].message.content.strip()
        # 清洗代码块标记
        content = re.sub(r'^```(?:json)?\s*\n?|\n?```$', '', content, flags=re.MULTILINE).strip()
        match = re.search(r'\{[\s\S]*\}', content)
        json_str = match.group(0) if match else content
        return json.loads(json_str)
    except Exception as e:
        logging.error(f"LLM调用失败: {e}")
        raise