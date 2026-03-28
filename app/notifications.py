import logging
from typing import Optional

import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import TELEGRAM_BOT_TOKEN, SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD

logger = logging.getLogger(__name__)


async def send_telegram(chat_id: str, message: str, bot_token: str = "") -> bool:
    """Отправка сообщения через Telegram Bot API."""
    token = bot_token or TELEGRAM_BOT_TOKEN
    if not token or not chat_id:
        logger.warning("Telegram: токен или chat_id не указаны")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info(f"Telegram: сообщение отправлено в чат {chat_id}")
                return True
            else:
                logger.error(f"Telegram ошибка: {response.status_code} — {response.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram исключение: {e}")
        return False


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    smtp_server: str = "",
    smtp_port: int = 0,
    smtp_email: str = "",
    smtp_password: str = ""
) -> bool:
    """Отправка email через SMTP."""
    server = smtp_server or SMTP_SERVER
    port = smtp_port or SMTP_PORT
    from_email = smtp_email or SMTP_EMAIL
    password = smtp_password or SMTP_PASSWORD

    if not from_email or not password or not to_email:
        logger.warning("Email: SMTP настройки не заполнены")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #6c5ce7;">🔔 Веб-мониторинг — Обнаружено изменение</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
            {body}
        </div>
        <p style="color: #636e72; font-size: 12px; margin-top: 20px;">
            Это автоматическое уведомление от системы мониторинга
        </p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=server,
            port=port,
            start_tls=True,
            username=from_email,
            password=password,
        )
        logger.info(f"Email: письмо отправлено на {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email исключение: {e}")
        return False


async def notify_user(
    settings,
    tracking_name: str,
    tracking_url: str,
    old_value: Optional[str],
    new_value: Optional[str]
) -> None:
    """Отправка уведомления пользователю через все активные каналы."""
    old_display = old_value[:200] if old_value else "(первая проверка)"
    new_display = new_value[:200] if new_value else "(пусто)"

    # Telegram
    if settings.telegram_notifications and settings.telegram_chat_id:
        tg_message = (
            f"🔔 <b>Обнаружено изменение!</b>\n\n"
            f"📌 <b>{tracking_name}</b>\n"
            f"🔗 {tracking_url}\n\n"
            f"📄 <b>Было:</b> {old_display}\n"
            f"📄 <b>Стало:</b> {new_display}"
        )
        await send_telegram(settings.telegram_chat_id, tg_message)

    # Email
    if settings.email_notifications and settings.notification_email:
        email_body = f"""
        <p><strong>Отслеживание:</strong> {tracking_name}</p>
        <p><strong>URL:</strong> <a href="{tracking_url}">{tracking_url}</a></p>
        <p><strong>Старое значение:</strong> {old_display}</p>
        <p><strong>Новое значение:</strong> {new_display}</p>
        """
        await send_email(
            to_email=settings.notification_email,
            subject=f"🔔 Изменение: {tracking_name}",
            body=email_body,
            smtp_server=settings.smtp_server or "",
            smtp_port=settings.smtp_port or 0,
            smtp_email=settings.smtp_email or "",
            smtp_password=settings.smtp_password or "",
        )
