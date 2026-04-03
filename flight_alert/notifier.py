import smtplib
from email.message import EmailMessage

import requests
from flight_alert.config import AppConfig


_TELEGRAM_MESSAGE_LIMIT = 3900


def _split_telegram_message(text: str, limit: int = _TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].lstrip()

    return [chunk for chunk in chunks if chunk]


def _raise_telegram_error(response: requests.Response) -> None:
    detail = response.text
    try:
        payload = response.json()
        detail = payload.get("description", detail)
    except ValueError:
        pass
    raise RuntimeError(f"Telegram API error {response.status_code}: {detail}")


def send_telegram_alert(config: AppConfig, body: str) -> None:
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError(
            "SEND_TELEGRAM=true requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID."
        )

    url = (
        f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    )

    for chunk in _split_telegram_message(body):
        payload = {
            "chat_id": str(config.telegram_chat_id).strip(),
            "text": chunk,
            "disable_web_page_preview": True,
        }
        response = requests.post(
            url,
            data=payload,
            timeout=20,
        )
        if not response.ok:
            _raise_telegram_error(response)


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
