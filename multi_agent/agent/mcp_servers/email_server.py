import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))


from fastmcp import FastMCP
import logging
from multi_agent.agent.skills.email_skill import send_email
from dotenv import load_dotenv
import os
# 加载项目.env文件
load_dotenv()


logging.basicConfig(level=logging.INFO)
mcp = FastMCP("email-mcp")


@mcp.tool(name="send_email")
def send_email_tool(subject: str, html_content: str)->str:
    """发送 HTML 格式邮件"""
    try:
        #参数直接传给底层skill
        res = send_email(subject,html_content)
        return res
    except Exception as e:
        #全局异常捕获，异常返回字符串
        return f"【发送失败】异常信息:{str(e)}"
  

if __name__ == "__main__":
    mcp.run(transport="stdio")