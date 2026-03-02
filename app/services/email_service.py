from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmailDeliveryResult:
    status: str
    provider: str | None = None
    error: str | None = None
    attempts: int = 0


class EmailService:
    def _render_html(self, subject: str, message: str, market_context: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            "<html><body style=\"font-family:Arial,sans-serif;background:#f8fafc;padding:20px;\">"
            "<div style=\"max-width:640px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;\">"
            "<h2 style=\"margin:0 0 8px 0;color:#0f172a;\">Commodity Price Alert</h2>"
            f"<p style=\"margin:0 0 16px 0;color:#334155;font-size:14px;\">{subject}</p>"
            f"<p style=\"color:#0f172a;font-size:15px;line-height:1.5;\">{message}</p>"
            f"<p style=\"color:#475569;font-size:13px;line-height:1.5;\">Market context: {market_context}</p>"
            f"<p style=\"margin-top:20px;color:#94a3b8;font-size:12px;\">Generated at {timestamp}</p>"
            "</div></body></html>"
        )

    async def _send_with_resend(
        self,
        to_email: str,
        subject: str,
        text_message: str,
        html_message: str,
    ) -> EmailDeliveryResult:
        settings = get_settings()
        attempts = 0
        for _ in range(3):
            attempts += 1
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
                            "text": text_message,
                            "html": html_message,
                        },
                    )
                if response.status_code < 300:
                    return EmailDeliveryResult(status="sent", provider="resend", attempts=attempts)
                body = response.text.lower()
                if response.status_code in {400, 422} and ("bounce" in body or "invalid" in body):
                    return EmailDeliveryResult(
                        status="bounced",
                        provider="resend",
                        error=response.text[:300],
                        attempts=attempts,
                    )
                if response.status_code < 500:
                    return EmailDeliveryResult(
                        status="failed",
                        provider="resend",
                        error=response.text[:300],
                        attempts=attempts,
                    )
            except Exception as exc:
                logger.warning("Resend send failed attempt=%s: %s", attempts, exc)
        return EmailDeliveryResult(status="failed", provider="resend", error="retry_exhausted", attempts=attempts)

    async def _send_with_sendgrid(
        self,
        to_email: str,
        subject: str,
        text_message: str,
        html_message: str,
    ) -> EmailDeliveryResult:
        settings = get_settings()
        attempts = 0
        for _ in range(3):
            attempts += 1
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
                            "content": [
                                {"type": "text/plain", "value": text_message},
                                {"type": "text/html", "value": html_message},
                            ],
                        },
                    )
                if response.status_code < 300:
                    return EmailDeliveryResult(status="sent", provider="sendgrid", attempts=attempts)
                body = response.text.lower()
                if response.status_code in {400, 422} and ("bounce" in body or "invalid" in body):
                    return EmailDeliveryResult(
                        status="bounced",
                        provider="sendgrid",
                        error=response.text[:300],
                        attempts=attempts,
                    )
                if response.status_code < 500:
                    return EmailDeliveryResult(
                        status="failed",
                        provider="sendgrid",
                        error=response.text[:300],
                        attempts=attempts,
                    )
            except Exception as exc:
                logger.warning("SendGrid send failed attempt=%s: %s", attempts, exc)
        return EmailDeliveryResult(status="failed", provider="sendgrid", error="retry_exhausted", attempts=attempts)

    async def send_alert(
        self,
        to_email: str | None,
        subject: str,
        message: str,
        market_context: str = "",
        send_enabled: bool = True,
    ) -> EmailDeliveryResult:
        if not send_enabled:
            return EmailDeliveryResult(status="skipped:disabled")
        if not to_email:
            return EmailDeliveryResult(status="skipped:no-recipient")

        settings = get_settings()
        html_message = self._render_html(subject, message, market_context)

        if settings.resend_api_key:
            result = await self._send_with_resend(to_email, subject, message, html_message)
            if result.status == "sent":
                return result
            logger.warning("Resend failed status=%s error=%s", result.status, result.error)

        if settings.sendgrid_api_key:
            result = await self._send_with_sendgrid(to_email, subject, message, html_message)
            if result.status == "sent":
                return result
            logger.warning("SendGrid failed status=%s error=%s", result.status, result.error)

        return EmailDeliveryResult(status="skipped:no-provider")
