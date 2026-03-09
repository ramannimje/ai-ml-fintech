from __future__ import annotations

from dataclasses import replace
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
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class AIProviderUnavailableError(RuntimeError):
    pass


class AIChatService:
    _openrouter_cooldown_until: datetime | None = None
    _openrouter_last_error: str | None = None

    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = AIReasoningEngine()

    @staticmethod
    def _openrouter_api_key() -> str | None:
        return get_secret_value(AI_SECRETS, "OPENROUTER_API_KEY", env_fallback="OPENROUTER_API_KEY")

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
        fallback_query = query if query.intent == "trading_outlook" else replace(query, intent="trading_outlook")
        fallback_answer = self.engine.generate_answer(query=fallback_query, data=data_context)

        if self.isAdvisoryQuestion(clean_message):
            answer = await self._openrouter_advisory_answer(
                session=session,
                question=clean_message,
                query_context=query_context,
                data_context=data_context,
                fallback_answer=fallback_answer,
            )
        else:
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
            "outlook",
            "analysis",
            "trend",
        )
        return any(token in text for token in advisory_tokens)

    async def _openrouter_advisory_answer(
        self,
        session: AsyncSession,
        question: str,
        query_context: dict[str, Any],
        data_context: dict[str, Any],
        fallback_answer: str,
    ) -> str:
        related_knowledge = await vector_service.search_knowledge_base(session, question, top_k=3)
        knowledge_texts: list[str] = []
        for kb_entry, distance in related_knowledge:
            if distance < 0.25:
                src = kb_entry.source.upper()
                knowledge_texts.append(f"[{src}] {kb_entry.content}")

        news_context = "\n".join(knowledge_texts) if knowledge_texts else "No recent RAG news context found."

        system_prompt = (
            "You are a commodities market analyst specializing in precious metals and macroeconomic signals.\n\n"
            "Your task is to answer investor questions using the market data and RAG news context provided.\n\n"
            "Rules:\n"
            "1. Base your reasoning strictly on the supplied market data and news.\n"
            "2. Do not produce generic financial advice.\n"
            "3. Explain the reasoning behind the recommendation.\n"
            "4. Consider trend strength, volatility, macro factors, and news sentiment.\n"
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
            news_context=news_context,
        )

        answer = await self._openrouter_generate_content(
            system_prompt=system_prompt,
            prompt=prompt,
            temperature=0.15,
            max_tokens=1000,
        )
        if answer:
            logger.info("openrouter_advisory_response_generated", extra={"question": question, "llmUsed": True})
            return answer

        logger.warning(
            "openrouter_advisory_response_failed",
            extra={"question": question, "llmUsed": False, "error": self._openrouter_last_error},
        )
        return fallback_answer

    async def _maybe_llm_refine(
        self,
        query_context: dict[str, Any],
        data_context: dict[str, Any],
        fallback_answer: str,
    ) -> str:
        provider = self.settings.ai_chat_provider.lower().strip()
        if provider == "disabled":
            return fallback_answer
        return await self._openrouter_refine(query_context, data_context, fallback_answer)

    async def _openrouter_refine(self, query_context: dict[str, Any], data_context: dict[str, Any], fallback_answer: str) -> str:
        system_prompt = self._system_prompt_for(query_context)
        prompt = self._build_refinement_prompt(query_context, data_context, fallback_answer)
        out = await self._openrouter_generate_content(system_prompt=system_prompt, prompt=prompt, temperature=0.15, max_tokens=1000)
        return out or fallback_answer

    async def _openrouter_generate_content(self, system_prompt: str, prompt: str, temperature: float, max_tokens: int) -> str:
        api_key = self._openrouter_api_key()
        if not api_key:
            self._openrouter_last_error = "OPENROUTER_API_KEY is missing"
            return ""

        now = datetime.now(timezone.utc)
        if self._openrouter_cooldown_until and now < self._openrouter_cooldown_until:
            self._openrouter_last_error = "OpenRouter in cooldown after rate limit"
            return ""

        payload = {
            "model": self.settings.openrouter_chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.settings.openrouter_base_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code == 429:
                self._set_openrouter_cooldown(seconds=self._cooldown_from_rate_limit(response, default_seconds=300))
                self._openrouter_last_error = "OpenRouter rate limited"
                logger.warning("openrouter_rate_limited model=%s", self.settings.openrouter_chat_model)
                return ""

            if response.status_code >= 300:
                self._openrouter_last_error = f"OpenRouter returned status {response.status_code}"
                logger.warning("openrouter_failed status=%s model=%s", response.status_code, self.settings.openrouter_chat_model)
                return ""

            content = self._extract_openrouter_text(response.json())
            if not content:
                self._openrouter_last_error = "OpenRouter returned empty content"
                return ""
            self._openrouter_last_error = None
            return content
        except Exception:
            self._openrouter_last_error = "OpenRouter request exception"
            logger.exception("openrouter_request_exception")
            return ""

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
        news_context: str = "",
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
            "5. Incorporate the RAG Macro News Context if it discusses related geopolitical or supply factors.\n"
            "6. Provide an investment interpretation based on these signals.\n\n"
            "Answer in clear paragraphs rather than bullet lists.\n"
            "Avoid repeating the same phrases across responses."
        )
        return (
            f"User Question: {question}\n\n"
            "Market Data:\n"
            f"{market_context}\n"
            f"{market_drivers}\n\n"
            "RAG Macro News Context (Semantic Search Results):\n"
            f"{news_context}\n\n"
            "Instructions for Gemini:\n"
            "Provide a natural analytical answer explaining whether the user should consider investing now. "
            "Discuss risk, volatility, news sentiment, and possible scenarios. Do not use generic disclaimers or template phrases.\n\n"
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
    def _extract_openrouter_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            chunks: list[str] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
            return "\n".join(chunks).strip()
        return ""

    def _set_openrouter_cooldown(self, seconds: int) -> None:
        self._openrouter_cooldown_until = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=seconds)

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
        if provider not in {"openrouter", "disabled"}:
            provider = "openrouter"

        cooldown_remaining = 0
        now = datetime.now(timezone.utc)
        if self._openrouter_cooldown_until and self._openrouter_cooldown_until > now:
            cooldown_remaining = int((self._openrouter_cooldown_until - now).total_seconds())

        return {
            "provider": provider,
            "openrouter_model": self.settings.openrouter_chat_model,
            "openrouter_api_key_present": bool(self._openrouter_api_key()),
            "openrouter_cooldown_seconds_remaining": max(0, cooldown_remaining),
            "last_openrouter_error": self._openrouter_last_error,
        }
