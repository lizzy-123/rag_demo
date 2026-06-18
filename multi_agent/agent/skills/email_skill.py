# agent/skills/email_skill.py
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject: str, html_content: str) -> str:
    """Skill：发送HTML邮件"""

    logging.info(f"【执行加载send_email】，入参subject={subject}")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender = os.getenv("SENDER_EMAIL")
    auth_code = os.getenv("EMAIL_AUTH_CODE")
    recipient = os.getenv("RECIPIENT_EMAIL")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, auth_code)
        server.sendmail(sender, [recipient], msg.as_string())

    return f"【发送成功】收件邮箱：{recipient},邮件标题:{subject}"