import os
import logging
from dotenv import load_dotenv
from multi_agent.agent.skills.llm_skill import call_llm

# 配置日志，显示详细信息
logging.basicConfig(level=logging.INFO)

# 加载 .env 环境变量
load_dotenv()

def test_llm():
    print("=== 开始测试 call_llm ===")
    # 简单 prompt，期望返回 JSON
    prompt = "请返回一个 JSON 对象，包含字段 'status' 和 'message'，例如 {\"status\": \"ok\", \"message\": \"测试成功\"}"
    system_prompt = "你是一个 JSON 输出引擎，只输出合法的 JSON 对象，不要有任何额外文字。"
    
    try:
        result = call_llm(prompt=prompt, system_prompt=system_prompt, timeout=30)
        print("✅ 调用成功！返回结果：")
        print(result)
        print("类型：", type(result))
    except Exception as e:
        print(f"❌ 调用失败：{e}")

if __name__ == "__main__":
    test_llm()