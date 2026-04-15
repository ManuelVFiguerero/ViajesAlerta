import smtplib
import time
from email.message import EmailMessage

import requests
from flight_alert.config import AppConfig


_TELEGRAM_MESSAGE_LIMIT = 3900
_TELEGRAM_MAX_RETRIES = 3
_TELEGRAM_BACKOFF_BASE_SECONDS = 2.0


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


def _send_telegram_chunk_with_retry(url: str, payload: dict[str, str]) -> None:
    attempt = 0
    while True:
        try:
            response = requests.post(url, data=payload, timeout=20)
        except requests.RequestException as exc:
            if attempt >= _TELEGRAM_MAX_RETRIES:
                raise RuntimeError(
                    "No se pudo conectar a Telegram luego de varios reintentos."
                ) from exc
            wait_seconds = min(20.0, _TELEGRAM_BACKOFF_BASE_SECONDS * (2**attempt))
            time.sleep(wait_seconds)
            attempt += 1
            continue

        if response.ok:
            return

        retryable = response.status_code == 429 or response.status_code >= 500
        if not retryable or attempt >= _TELEGRAM_MAX_RETRIES:
            _raise_telegram_error(response)

        wait_seconds = min(20.0, _TELEGRAM_BACKOFF_BASE_SECONDS * (2**attempt))
        time.sleep(wait_seconds)
        attempt += 1


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
        _send_telegram_chunk_with_retry(url=url, payload=payload)


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
