import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from fastmcp import FastMCP
import logging
from typing import Dict, Any

from dotenv import load_dotenv
import os
# 加载项目.env文件
load_dotenv()

# 导入原有 skill 业务逻辑
from multi_agent.agent.skills.llm_skill import call_llm

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("llm-mcp")

@mcp.tool()
def call_llm_tool(
    prompt: str,
    system_prompt: str,
    temperature: float = 0.1
) -> Dict[str, Any]:
    """调用大模型并返回结构化 JSON 结果"""
    return call_llm(prompt, system_prompt, temperature)

if __name__ == "__main__":
    mcp.run(transport="stdio")