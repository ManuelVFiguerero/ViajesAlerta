import smtplib
from email.message import EmailMessage
from typing import Any

import requests
from flight_alert.config import AppConfig


def _normalize_whatsapp_number(number: str) -> str:
    digits = "".join(ch for ch in number if ch.isdigit())
    if not digits:
        raise ValueError("WHATSAPP_TO no tiene digitos validos.")
    return f"whatsapp:+{digits}"


def send_whatsapp_alert(config: AppConfig, body: str) -> None:
    if not config.whatsapp_to:
        raise ValueError("SEND_WHATSAPP=true requiere WHATSAPP_TO.")
    if not config.twilio_account_sid or not config.twilio_auth_token:
        raise ValueError(
            "SEND_WHATSAPP=true requiere TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN."
        )
    if not config.twilio_whatsapp_from:
        raise ValueError("SEND_WHATSAPP=true requiere TWILIO_WHATSAPP_FROM.")

    to_number = _normalize_whatsapp_number(config.whatsapp_to)
    from_number = config.twilio_whatsapp_from.strip()
    if not from_number.startswith("whatsapp:+"):
        digits = "".join(ch for ch in from_number if ch.isdigit())
        from_number = f"whatsapp:+{digits}"

    url = (
        "https://api.twilio.com/2010-04-01/Accounts/"
        f"{config.twilio_account_sid}/Messages.json"
    )
    payload: dict[str, Any] = {"From": from_number, "To": to_number, "Body": body}
    response = requests.post(
        url,
        data=payload,
        auth=(config.twilio_account_sid, config.twilio_auth_token),
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
