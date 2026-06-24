import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))



from fastmcp import FastMCP
from typing import Dict, Any
import logging

# 导入原有 skill 业务逻辑 + 模板常量
from multi_agent.agent.skills.render_skill import render_html, EMAIL_TEMPLATE

from dotenv import load_dotenv
import os
# 加载项目.env文件
load_dotenv()

logging.basicConfig(level=logging.INFO)
mcp = FastMCP("render-mcp")

@mcp.tool()
def render_html_tool(template_str: str, context: Dict[str, Any]) -> str:
    """Jinja2 模板渲染 HTML"""
    return render_html(template_str, context)

@mcp.resource("template://email")
#@mcp.tool()
def get_email_template() -> str:
    """获取内置邮件 HTML 模板（MCP 资源）"""
    return EMAIL_TEMPLATE

if __name__ == "__main__":
    #mcp.run(transport="stdio")
    mcp.run(
        transport = "streamable-http",
        host = "0.0.0.0",
        port = 8013
    )