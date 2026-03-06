from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.secrets import AI_SECRETS, get_secret_value
from app.models.chat_history import ChatHistory
from app.schemas.responses import AIChatResponse
from app.services.ai_reasoning_engine import AIReasoningEngine

logger = logging.getLogger(__name__)


class AIProviderUnavailableError(RuntimeError):
    pass


class AIChatService:
    _openai_cooldown_until: datetime | None = None
    _openai_last_error: str | None = None
    _gemini_cooldown_until: datetime | None = None
    _gemini_last_error: str | None = None
    _gemini_discovered_model: str | None = None
    _gemini_discovered_model_checked_at: datetime | None = None
    _gemini_available_models: list[str] | None = None
    _advisory_failure_message = "We are unable to generate an advisory response at the moment. Please try again."

    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = AIReasoningEngine()

    @staticmethod
    def _openai_api_key() -> str | None:
        return get_secret_value(AI_SECRETS, "OPENAI_API_KEY", env_fallback="OPENAI_API_KEY")

    @staticmethod
    def _gemini_api_key() -> str | None:
        return get_secret_value(AI_SECRETS, "GEMINI_API_KEY", env_fallback="GEMINI_API_KEY")

    @staticmethod
    def _system_prompt_for(query_context: dict[str, Any]) -> str:
        return (
            "You are a commodities market analyst. Use only supplied facts. "
            "Answer the user's message directly and naturally from the provided context. "
            "Do not rely on fixed templates or hardcoded phrase rules; choose structure based on the question."
        )

    async def ask(
        self,
        session: AsyncSession,
        user_id: str,
        message: str,
        preferred_region: str = "us",
    ) -> AIChatResponse:
        clean_message = message.strip()
        query = await self.engine.build_context(
            session=session,
            user_id=user_id,
            message=clean_message,
            preferred_region=preferred_region,
        )
        data_context = await self.engine.build_data_context(session=session, query=query)
        query_context = self._query_to_dict(query)
        if self.isAdvisoryQuestion(clean_message):
            answer = await self._gemini_advisory_answer(
                question=clean_message,
                query_context=query_context,
                data_context=data_context,
            )
        else:
            fallback_answer = self.engine.generate_answer(query=query, data=data_context)
            answer = await self._maybe_llm_refine(query_context, data_context, fallback_answer)

        session.add(ChatHistory(user_id=user_id, message=clean_message, response=answer))
        await session.commit()

        return AIChatResponse(
            answer=answer,
            intent=query.intent,
            region=query.region,
            commodity=query.commodity,
            horizon_days=query.horizon_days,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def isAdvisoryQuestion(question: str) -> bool:
        text = question.lower()
        advisory_tokens = (
            "invest",
            "buy",
            "sell",
            "hold",
            "should i",
            "good time",
            "entry price",
            "exit price",
            "forecast",
        )
        return any(token in text for token in advisory_tokens)

    async def _gemini_advisory_answer(
        self,
        question: str,
        query_context: dict[str, Any],
        data_context: dict[str, Any],
    ) -> str:
        system_prompt = (
            "You are a commodities market analyst specializing in precious metals and macroeconomic signals.\n\n"
            "Your task is to answer investor questions using the market data provided.\n\n"
            "Rules:\n"
            "1. Base your reasoning strictly on the supplied market data.\n"
            "2. Do not produce generic financial advice.\n"
            "3. Explain the reasoning behind the recommendation.\n"
            "4. Consider trend strength, volatility, macro factors, and momentum.\n"
            "5. Clearly discuss both upside and downside risk.\n"
            "6. Provide a practical interpretation for retail investors.\n"
            "7. Do not use templated responses or fixed phrases.\n\n"
            "Your response must include:\n"
            "- Short market interpretation\n"
            "- Investment outlook (bullish, neutral, cautious)\n"
            "- Risk considerations\n"
            "- Practical takeaway"
        )
        prompt = self._build_advisory_prompt(
            question=question,
            query_context=query_context,
            data_context=data_context,
        )
        answer = await self._gemini_generate_content(
            system_prompt=system_prompt,
            prompt=prompt,
            use_model_cache=False,
        )
        if answer:
            logger.info(
                "Gemini advisory response generated",
                extra={"question": question, "llmUsed": True},
            )
            return answer
        logger.warning(
            "Gemini advisory response failed",
            extra={"question": question, "llmUsed": False, "error": self._gemini_last_error},
        )
        return self._advisory_failure_message

    async def _maybe_llm_refine(
        self,
        query_context: dict[str, Any],
        data_context: dict[str, Any],
        fallback_answer: str,
    ) -> str:
        provider = self.settings.ai_chat_provider.lower().strip()
        if provider == "disabled":
            return fallback_answer
        if provider == "openai":
            return await self._openai_refine(query_context, data_context, fallback_answer)
        if provider == "gemini":
            # Fail open for non-advisory responses: when Gemini is unavailable/rate-limited,
            # continue with the deterministic engine answer instead of returning 503.
            return await self._gemini_refine(query_context, data_context, fallback_answer)
        if provider == "ollama":
            return await self._ollama_refine(query_context, data_context, fallback_answer)
        return fallback_answer

    async def _openai_refine(self, query_context: dict[str, Any], data_context: dict[str, Any], fallback_answer: str) -> str:
        openai_api_key = self._openai_api_key()
        if not openai_api_key:
            self._openai_last_error = "OPENAI_API_KEY is missing"
            return fallback_answer
        now = datetime.now(timezone.utc)
        if self._openai_cooldown_until and now < self._openai_cooldown_until:
            self._openai_last_error = "OpenAI in cooldown after rate limit"
            return fallback_answer

        prompt = self._build_refinement_prompt(query_context, data_context, fallback_answer)
        model_candidates: list[str] = []
        preferred = self.settings.openai_chat_model.strip()
        if preferred:
            model_candidates.append(preferred)
        for item in self.settings.openai_fallback_models.split(","):
            model = item.strip()
            if model and model not in model_candidates:
                model_candidates.append(model)
        model_candidates = model_candidates[:2]

        system_prompt = self._system_prompt_for(query_context)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                headers = {
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                }

                for model in model_candidates:
                    # Preferred path for latest models.
                    responses_call = await client.post(
                        "https://api.openai.com/v1/responses",
                        headers=headers,
                        json={
                            "model": model,
                            "temperature": 0.15,
                            "input": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt},
                            ],
                        },
                    )
                    if responses_call.status_code < 300:
                        text = self._extract_responses_text(responses_call.json())
                        if text:
                            return text
                    elif responses_call.status_code == 429:
                        self._set_openai_cooldown(seconds=self._cooldown_from_rate_limit(responses_call, default_seconds=300))
                        self._openai_last_error = "OpenAI rate limited on /v1/responses"
                        logger.warning("openai_rate_limited endpoint=responses model=%s", model)
                        return fallback_answer
                    elif not self._is_model_error(responses_call):
                        self._openai_last_error = f"OpenAI /v1/responses returned status {responses_call.status_code}"
                        logger.warning("openai_responses_failed status=%s model=%s", responses_call.status_code, model)
                        continue

                    # Fallback path for compatibility.
                    chat_call = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json={
                            "model": model,
                            "temperature": 0.15,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt},
                            ],
                        },
                    )
                    if chat_call.status_code < 300:
                        body = chat_call.json()
                        content = body.get("choices", [{}])[0].get("message", {}).get("content")
                        if isinstance(content, str) and content.strip():
                            return content.strip()
                    elif chat_call.status_code == 429:
                        self._set_openai_cooldown(seconds=self._cooldown_from_rate_limit(chat_call, default_seconds=300))
                        self._openai_last_error = "OpenAI rate limited on /v1/chat/completions"
                        logger.warning("openai_rate_limited endpoint=chat model=%s", model)
                        return fallback_answer
                    elif not self._is_model_error(chat_call):
                        self._openai_last_error = f"OpenAI /v1/chat/completions returned status {chat_call.status_code}"
                        logger.warning("openai_chat_failed status=%s model=%s", chat_call.status_code, model)
                        continue
        except Exception:
            self._openai_last_error = "OpenAI request exception"
            logger.exception("openai_refine_exception")
            return fallback_answer
        self._openai_last_error = "OpenAI model unavailable or unsupported"
        return fallback_answer

    async def _ollama_refine(self, query_context: dict[str, Any], data_context: dict[str, Any], fallback_answer: str) -> str:
        prompt = self._build_refinement_prompt(query_context, data_context, fallback_answer)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
                    json={
                        "model": self.settings.ollama_model,
                        "prompt": (
                            "Rewrite the market note with professional tone. Use only facts from context.\n\n"
                            + prompt
                        ),
                        "stream": False,
                    },
                )
            if response.status_code >= 300:
                return fallback_answer
            body = response.json()
            text = str(body.get("response", "")).strip()
            return text or fallback_answer
        except Exception:
            return fallback_answer

    async def _gemini_refine(self, query_context: dict[str, Any], data_context: dict[str, Any], fallback_answer: str) -> str:
        system_prompt = self._system_prompt_for(query_context)
        prompt = self._build_refinement_prompt(query_context, data_context, fallback_answer)
        text = await self._gemini_generate_content(system_prompt=system_prompt, prompt=prompt, use_model_cache=True)
        return text or fallback_answer

    async def _gemini_generate_content(self, system_prompt: str, prompt: str, use_model_cache: bool) -> str:
        gemini_api_key = self._gemini_api_key()
        if not gemini_api_key:
            self._gemini_last_error = "GEMINI_API_KEY is missing"
            return ""
        now = datetime.now(timezone.utc)
        if self._gemini_cooldown_until and now < self._gemini_cooldown_until:
            self._gemini_last_error = "Gemini in cooldown after rate limit"
            return ""
        available_models = await self._get_gemini_available_models(use_cache=use_model_cache)
        model_candidates = self._select_gemini_candidates(available_models)
        if not model_candidates:
            self._gemini_last_error = "No Gemini generateContent model available"
            return ""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                for model in model_candidates:
                    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    response = await client.post(
                        endpoint,
                        headers={
                            "Content-Type": "application/json",
                            "x-goog-api-key": gemini_api_key,
                        },
                        json={
                            "system_instruction": {
                                "parts": [{"text": system_prompt}],
                            },
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [{"text": prompt}],
                                }
                            ],
                            "generationConfig": {"temperature": 0.15},
                        },
                    )
                    if response.status_code < 300:
                        text = self._extract_gemini_text(response.json())
                        if text:
                            self._gemini_last_error = None
                            return text
                    elif response.status_code == 429:
                        self._set_gemini_cooldown(seconds=self._cooldown_from_rate_limit(response, default_seconds=300))
                        self._gemini_last_error = "Gemini rate limited"
                        logger.warning("gemini_rate_limited model=%s", model)
                        return ""
                    elif self._is_gemini_model_not_found(response):
                        self._gemini_last_error = f"Gemini model '{model}' unavailable"
                        logger.warning("gemini_model_not_found model=%s", model)
                        continue
                    elif not self._is_model_error(response):
                        self._gemini_last_error = f"Gemini returned status {response.status_code}"
                        logger.warning("gemini_failed status=%s model=%s", response.status_code, model)
                        continue
        except Exception:
            self._gemini_last_error = "Gemini request exception"
            logger.exception("gemini_refine_exception")
            return ""
        self._gemini_last_error = "Gemini model unavailable or unsupported"
        return ""

    async def _get_gemini_available_models(self, use_cache: bool = True) -> list[str]:
        now = datetime.now(timezone.utc)
        if (
            use_cache
            and self._gemini_available_models is not None
            and self._gemini_discovered_model_checked_at
            and (now - self._gemini_discovered_model_checked_at).total_seconds() < 3600
        ):
            return self._gemini_available_models
        gemini_api_key = self._gemini_api_key()
        if not gemini_api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    headers={"x-goog-api-key": gemini_api_key},
                )
            if resp.status_code >= 300:
                self._gemini_last_error = f"Gemini model list failed ({resp.status_code})"
                return []
            payload = resp.json()
            models = payload.get("models", [])
            available: list[str] = []
            for model in models:
                if not isinstance(model, dict):
                    continue
                name = str(model.get("name", ""))
                methods = model.get("supportedGenerationMethods", [])
                if name and isinstance(methods, list) and "generateContent" in methods:
                    available.append(name.replace("models/", ""))
            self._gemini_available_models = available
            self._gemini_discovered_model_checked_at = now
            self._gemini_discovered_model = available[0] if available else None
            return available
        except Exception:
            return []

    @staticmethod
    def _build_refinement_prompt(query_context: dict[str, Any], data_context: dict[str, Any], fallback_answer: str) -> str:
        serializable_context = {
            "query_context": query_context,
            "data_context": data_context,
            "draft_answer": fallback_answer,
        }
        return json.dumps(serializable_context, default=str, ensure_ascii=True)

    @staticmethod
    def _build_advisory_prompt(
        question: str,
        query_context: dict[str, Any],
        data_context: dict[str, Any],
    ) -> str:
        commodity = str(query_context.get("commodity", "commodity")).replace("_", " ").title()
        current = data_context.get("current_price") or {}
        trend = data_context.get("historical_trend") or {}
        signal = str(trend.get("signal_text", "neutral"))
        momentum = data_context.get("regional_market_signal", "unavailable")
        price = current.get("price", "N/A")
        currency = current.get("currency", "")
        unit = current.get("unit", "")
        volatility = trend.get("volatility_pct", data_context.get("volatility", "N/A"))
        change = trend.get("change_pct", "N/A")

        market_context = (
            f"Commodity: {commodity}\n"
            f"Current Price: {price} {currency} per {unit}\n"
            f"Price Change (Trend Strength): {change}%\n"
            f"Volatility: {volatility}%\n"
            f"Market Signal: {signal}\n"
            f"Regional Momentum Leader: {momentum}\n"
        )
        market_drivers = (
            "Market Drivers:\n"
            "- Industrial demand\n"
            "- Currency fluctuations\n"
            "- Interest rate expectations\n"
            "- Inflation outlook\n"
        )
        reasoning = (
            "Analyze the situation step by step:\n"
            "1. Interpret the current price trend.\n"
            "2. Evaluate the volatility and what it means for short-term risk.\n"
            "3. Explain what the market signal suggests.\n"
            "4. Consider macro drivers like industrial demand and currency.\n"
            "5. Provide an investment interpretation based on these signals.\n\n"
            "Answer in clear paragraphs rather than bullet lists.\n"
            "Avoid repeating the same phrases across responses."
        )
        return (
            f"User Question: {question}\n\n"
            "Market Data:\n"
            f"{market_context}\n"
            f"{market_drivers}\n"
            "Instructions for Gemini:\n"
            "Provide a natural analytical answer explaining whether the user should consider investing now. "
            "Discuss risk, volatility, and possible scenarios. Do not use generic disclaimers or template phrases.\n\n"
            f"{reasoning}"
        )

    @staticmethod
    def _query_to_dict(query: Any) -> dict[str, Any]:
        return {
            "message": getattr(query, "message", ""),
            "intent": getattr(query, "intent", "market_summary"),
            "commodity": getattr(query, "commodity", None),
            "comparison_commodity": getattr(query, "comparison_commodity", None),
            "region": getattr(query, "region", "us"),
            "comparison_region": getattr(query, "comparison_region", None),
            "horizon_days": int(getattr(query, "horizon_days", 30)),
            "target_date": getattr(query, "target_date", None),
            "is_long_term": bool(getattr(query, "is_long_term", False)),
            "concise": bool(getattr(query, "concise", False)),
        }

    @staticmethod
    def _extract_responses_text(payload: dict[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
        output = payload.get("output")
        if not isinstance(output, list):
            return ""
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
        return "\n".join(chunks).strip()

    @staticmethod
    def _extract_gemini_text(payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return ""
        first = candidates[0]
        if not isinstance(first, dict):
            return ""
        content = first.get("content", {})
        if not isinstance(content, dict):
            return ""
        parts = content.get("parts")
        if not isinstance(parts, list):
            return ""
        chunks: list[str] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
        return "\n".join(chunks).strip()

    @staticmethod
    def _is_gemini_model_not_found(response: httpx.Response) -> bool:
        if response.status_code != 404:
            return False
        try:
            payload = response.json()
        except Exception:
            return False
        message = str(payload.get("error", {}).get("message", "")).lower()
        return "is not found for api version" in message or "supported for generatecontent" in message

    def _select_gemini_candidates(self, available_models: list[str]) -> list[str]:
        if not available_models:
            return []
        available_set = set(available_models)
        configured: list[str] = []
        preferred = self.settings.gemini_model.strip()
        if preferred:
            configured.append(preferred)
        for item in self.settings.gemini_fallback_models.split(","):
            model = item.strip()
            if model and model not in configured:
                configured.append(model)

        preferred_order = configured + [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
        out: list[str] = []
        for model in preferred_order:
            if model in available_set and model not in out:
                out.append(model)
        if not out:
            out = available_models[:2]
        return out[:2]

    @staticmethod
    def _is_model_error(response: httpx.Response) -> bool:
        try:
            payload = response.json()
        except Exception:
            return False
        message = str(payload.get("error", {}).get("message", "")).lower()
        code = str(payload.get("error", {}).get("code", "")).lower()
        return "model" in message or "model" in code or "not found" in message

    def _set_openai_cooldown(self, seconds: int) -> None:
        self._openai_cooldown_until = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=seconds)

    def _set_gemini_cooldown(self, seconds: int) -> None:
        self._gemini_cooldown_until = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=seconds)

    @staticmethod
    def _cooldown_from_rate_limit(response: httpx.Response, default_seconds: int = 300) -> int:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(30, int(float(retry_after)))
            except ValueError:
                pass
        return max(30, default_seconds)

    def provider_status(self) -> dict[str, Any]:
        provider = self.settings.ai_chat_provider.lower().strip()
        if provider not in {"openai", "gemini", "ollama", "disabled"}:
            provider = "disabled"
        now = datetime.now(timezone.utc)
        openai_cooldown_remaining = 0
        if self._openai_cooldown_until and self._openai_cooldown_until > now:
            openai_cooldown_remaining = int((self._openai_cooldown_until - now).total_seconds())
        gemini_cooldown_remaining = 0
        if self._gemini_cooldown_until and self._gemini_cooldown_until > now:
            gemini_cooldown_remaining = int((self._gemini_cooldown_until - now).total_seconds())
        openai_fallback_models = [item.strip() for item in self.settings.openai_fallback_models.split(",") if item.strip()]
        gemini_fallback_models = [item.strip() for item in self.settings.gemini_fallback_models.split(",") if item.strip()]
        return {
            "provider": provider,
            "openai_model": self.settings.openai_chat_model,
            "openai_fallback_models": openai_fallback_models,
            "openai_api_key_present": bool(self._openai_api_key()),
            "openai_cooldown_seconds_remaining": max(0, openai_cooldown_remaining),
            "last_openai_error": self._openai_last_error,
            "gemini_model": self.settings.gemini_model,
            "gemini_fallback_models": gemini_fallback_models,
            "gemini_api_key_present": bool(self._gemini_api_key()),
            "gemini_cooldown_seconds_remaining": max(0, gemini_cooldown_remaining),
            "last_gemini_error": self._gemini_last_error,
            "gemini_discovered_model": self._gemini_discovered_model,
        }
