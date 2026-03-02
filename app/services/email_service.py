from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    async def send_alert(self, to_email: str | None, subject: str, message: str) -> str:
        if not to_email:
            return "skipped:no-recipient"

        settings = get_settings()
        if settings.resend_api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {settings.resend_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "from": settings.resend_from_email,
                            "to": [to_email],
                            "subject": subject,
                            "text": message,
                        },
                    )
                if response.status_code < 300:
                    return "sent:resend"
                logger.warning("Resend failed status=%s body=%s", response.status_code, response.text)
            except Exception as exc:
                logger.warning("Resend send failed: %s", exc)

        if settings.sendgrid_api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "https://api.sendgrid.com/v3/mail/send",
                        headers={
                            "Authorization": f"Bearer {settings.sendgrid_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "personalizations": [{"to": [{"email": to_email}]}],
                            "from": {"email": settings.sendgrid_from_email},
                            "subject": subject,
                            "content": [{"type": "text/plain", "value": message}],
                        },
                    )
                if response.status_code < 300:
                    return "sent:sendgrid"
                logger.warning("SendGrid failed status=%s body=%s", response.status_code, response.text)
            except Exception as exc:
                logger.warning("SendGrid send failed: %s", exc)

        return "skipped:no-provider"
