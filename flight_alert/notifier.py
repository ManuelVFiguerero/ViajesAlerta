import smtplib
from email.message import EmailMessage

import requests
from flight_alert.config import AppConfig


def send_telegram_alert(config: AppConfig, body: str) -> None:
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError(
            "SEND_TELEGRAM=true requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID."
        )

    url = (
        f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    )
    payload = {
        "chat_id": config.telegram_chat_id,
        "text": body,
        "disable_web_page_preview": True,
    }
    response = requests.post(
        url,
        data=payload,
        timeout=20,
    )
    response.raise_for_status()


def send_email_alert(config: AppConfig, body: str) -> None:
    if not config.email_sender or not config.email_password or not config.email_receiver:
        raise ValueError(
            "SEND_EMAIL=true requiere EMAIL_SENDER, EMAIL_PASSWORD y EMAIL_RECEIVER."
        )

    msg = EmailMessage()
    msg["Subject"] = config.email_subject
    msg["From"] = config.email_sender
    msg["To"] = config.email_receiver
    msg.set_content(body)

    if config.smtp_ssl:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
            smtp.login(config.email_sender, config.email_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(config.email_sender, config.email_password)
            smtp.send_message(msg)
