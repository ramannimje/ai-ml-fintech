from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.secrets import AUTH_SECRETS, get_secret_value

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppDeliveryResult:
    status: str
    provider: str | None = None
    error: str | None = None
    attempts: int = 0


class WhatsAppService:
    @staticmethod
    def _twilio_account_sid() -> str | None:
        return get_secret_value(AUTH_SECRETS, "TWILIO_ACCOUNT_SID", env_fallback="TWILIO_ACCOUNT_SID")

    @staticmethod
    def _twilio_auth_token() -> str | None:
        return get_secret_value(AUTH_SECRETS, "TWILIO_AUTH_TOKEN", env_fallback="TWILIO_AUTH_TOKEN")

    @staticmethod
    def _twilio_whatsapp_number() -> str | None:
        return get_secret_value(AUTH_SECRETS, "TWILIO_WHATSAPP_NUMBER", env_fallback="TWILIO_WHATSAPP_NUMBER")

    @staticmethod
    def _whatsapp_meta_access_token() -> str | None:
        return get_secret_value(AUTH_SECRETS, "WHATSAPP_META_ACCESS_TOKEN", env_fallback="WHATSAPP_META_ACCESS_TOKEN")

    @staticmethod
    def _whatsapp_meta_phone_number_id() -> str | None:
        return get_secret_value(
            AUTH_SECRETS,
            "WHATSAPP_META_PHONE_NUMBER_ID",
            env_fallback="WHATSAPP_META_PHONE_NUMBER_ID",
        )

    @staticmethod
    def _normalize_twilio_number(number: str) -> str:
        value = number.strip()
        if value.startswith("whatsapp:"):
            return value
        return f"whatsapp:{value}"

    @staticmethod
    def _normalize_meta_to(number: str) -> str:
        value = number.strip()
        if value.startswith("whatsapp:"):
            value = value.split(":", 1)[1]
        return value.lstrip("+")

    async def _send_via_twilio(self, to_number: str, message: str) -> WhatsAppDeliveryResult:
        settings = get_settings()
        twilio_account_sid = self._twilio_account_sid()
        twilio_auth_token = self._twilio_auth_token()
        twilio_whatsapp_number = self._twilio_whatsapp_number()
        if not twilio_account_sid or not twilio_auth_token or not twilio_whatsapp_number:
            return WhatsAppDeliveryResult(status="skipped:no-twilio-config", provider="twilio")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_account_sid}/Messages.json"
        payload = {
            "From": self._normalize_twilio_number(twilio_whatsapp_number),
            "To": self._normalize_twilio_number(to_number),
            "Body": message,
        }
        attempts = 0
        for _ in range(3):
            attempts += 1
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url,
                        data=payload,
                        auth=(twilio_account_sid, twilio_auth_token),
                    )
                if resp.status_code < 300:
                    return WhatsAppDeliveryResult(status="sent", provider="twilio", attempts=attempts)
                if resp.status_code < 500:
                    return WhatsAppDeliveryResult(
                        status="failed",
                        provider="twilio",
                        error=resp.text[:300],
                        attempts=attempts,
                    )
            except Exception as exc:
                logger.warning("twilio_whatsapp_send_failed attempt=%s error=%s", attempts, exc)
        return WhatsAppDeliveryResult(status="failed", provider="twilio", error="retry_exhausted", attempts=attempts)

    async def _send_via_meta(self, to_number: str, message: str) -> WhatsAppDeliveryResult:
        settings = get_settings()
        whatsapp_meta_access_token = self._whatsapp_meta_access_token()
        whatsapp_meta_phone_number_id = self._whatsapp_meta_phone_number_id()
        if not whatsapp_meta_access_token or not whatsapp_meta_phone_number_id:
            return WhatsAppDeliveryResult(status="skipped:no-meta-config", provider="meta")

        url = (
            f"https://graph.facebook.com/{settings.whatsapp_meta_api_version}/"
            f"{whatsapp_meta_phone_number_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": self._normalize_meta_to(to_number),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }

        attempts = 0
        for _ in range(3):
            attempts += 1
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {whatsapp_meta_access_token}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if resp.status_code < 300:
                    return WhatsAppDeliveryResult(status="sent", provider="meta", attempts=attempts)
                if resp.status_code < 500:
                    return WhatsAppDeliveryResult(
                        status="failed",
                        provider="meta",
                        error=resp.text[:300],
                        attempts=attempts,
                    )
            except Exception as exc:
                logger.warning("meta_whatsapp_send_failed attempt=%s error=%s", attempts, exc)
        return WhatsAppDeliveryResult(status="failed", provider="meta", error="retry_exhausted", attempts=attempts)

    async def send_alert(self, to_number: str | None, message: str) -> WhatsAppDeliveryResult:
        if not to_number:
            return WhatsAppDeliveryResult(status="skipped:no-recipient")

        provider = get_settings().whatsapp_provider.strip().lower()
        if provider == "meta":
            return await self._send_via_meta(to_number=to_number, message=message)
        return await self._send_via_twilio(to_number=to_number, message=message)
