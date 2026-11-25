import os
import smtplib
from email.mime.text import MIMEText
import httpx

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_FROM")
    msg["To"] = to_email
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST"), 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)

def send_telegram_message(chat_id: int, text: str):
    token = os.getenv("NOTIFY_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    httpx.post(url, json={"chat_id": chat_id, "text": text})