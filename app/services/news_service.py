from __future__ import annotations

from datetime import datetime, timezone
import json
import re

import httpx

from app.core.config import get_settings
from app.core.secrets import AI_SECRETS, get_secret_value
from app.schemas.responses import CommodityNewsSummaryResponse, NewsHeadline

DEFAULT_HEADLINES = {
    "gold": [
        "Gold steadies as markets assess inflation and rate-cut path",
        "Central bank buying supports long-term gold demand outlook",
        "Safe-haven flows rise amid macro uncertainty",
    ],
    "silver": [
        "Silver tracks gold gains as industrial demand outlook improves",
        "Bullion traders watch dollar weakness for next silver move",
        "ETF inflows indicate renewed investor interest in silver",
    ],
    "crude_oil": [
        "Crude oil edges higher on supply discipline expectations",
        "Energy traders weigh demand signals against inventory data",
        "Geopolitical risk premium keeps oil volatility elevated",
    ],
    "natural_gas": [
        "Natural gas swings as weather outlook shifts demand expectations",
        "Storage updates drive short-term volatility in gas futures",
        "LNG export trends remain key catalyst for gas prices",
    ],
    "copper": [
        "Copper sentiment improves on infrastructure demand optimism",
        "Traders track manufacturing signals for copper direction",
        "Supply disruptions keep copper market tightly balanced",
    ],
}

BULLISH_WORDS = {"rise", "rises", "up", "gain", "gains", "bullish", "surge", "strong", "support"}
BEARISH_WORDS = {"fall", "falls", "down", "drop", "drops", "bearish", "slump", "weak", "pressure"}


class CommodityNewsService:
    @staticmethod
    def _newsapi_key() -> str | None:
        return get_secret_value(AI_SECRETS, "NEWSAPI_KEY", env_fallback="NEWSAPI_KEY")

    @staticmethod
    def _anthropic_api_key() -> str | None:
        return get_secret_value(AI_SECRETS, "ANTHROPIC_API_KEY", env_fallback="ANTHROPIC_API_KEY")

    async def summarize(self, commodity: str) -> CommodityNewsSummaryResponse:
        headlines = await self._fetch_headlines(commodity)
        summary, sentiment = await self._summarize_with_claude(commodity, headlines)
        if not summary:
            summary = self._fallback_summary(commodity, headlines)
        if sentiment not in {"bullish", "bearish", "neutral"}:
            sentiment = self._heuristic_sentiment(headlines)

        return CommodityNewsSummaryResponse(
            commodity=commodity,
            sentiment=sentiment,
            summary=summary,
            headlines=headlines,
            updated_at=datetime.now(timezone.utc),
        )

    async def _fetch_headlines(self, commodity: str) -> list[NewsHeadline]:
        newsapi_key = self._newsapi_key()
        if newsapi_key:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    response = await client.get(
                        "https://newsapi.org/v2/everything",
                        params={
                            "q": f"{commodity} commodity price",
                            "language": "en",
                            "sortBy": "publishedAt",
                            "pageSize": 6,
                            "apiKey": newsapi_key,
                        },
                    )
                if response.status_code == 200:
                    payload = response.json()
                    result: list[NewsHeadline] = []
                    for item in payload.get("articles", []):
                        published = item.get("publishedAt") or datetime.now(timezone.utc).isoformat()
                        try:
                            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        except ValueError:
                            published_dt = datetime.now(timezone.utc)
                        result.append(
                            NewsHeadline(
                                title=item.get("title") or "Untitled",
                                source=(item.get("source") or {}).get("name") or "NewsAPI",
                                url=item.get("url") or "",
                                published_at=published_dt,
                            )
                        )
                    if result:
                        return result
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        return [
            NewsHeadline(title=title, source="Fallback Feed", url="", published_at=now)
            for title in DEFAULT_HEADLINES.get(commodity, DEFAULT_HEADLINES["gold"])
        ]

    async def _summarize_with_claude(self, commodity: str, headlines: list[NewsHeadline]) -> tuple[str, str]:
        settings = get_settings()
        anthropic_api_key = self._anthropic_api_key()
        if not anthropic_api_key:
            return "", ""

        title_lines = "\n".join(f"- {h.title}" for h in headlines[:6])
        prompt = (
            f"You are a commodity strategist. Explain why {commodity.replace('_', ' ')} is moving today in exactly 3 concise lines. "
            "Also classify sentiment as bullish, bearish, or neutral. "
            "Return strict JSON with keys summary and sentiment.\n"
            f"Headlines:\n{title_lines}"
        )

        try:
            async with httpx.AsyncClient(timeout=18.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": settings.anthropic_model,
                        "max_tokens": 220,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
            if response.status_code >= 300:
                return "", ""

            payload = response.json()
            text = ""
            for block in payload.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return "", ""
            parsed = json.loads(match.group(0))
            return str(parsed.get("summary", "")).strip(), str(parsed.get("sentiment", "")).strip().lower()
        except Exception:
            return "", ""

    def _heuristic_sentiment(self, headlines: list[NewsHeadline]) -> str:
        score = 0
        for h in headlines:
            words = set(re.findall(r"[a-zA-Z]+", h.title.lower()))
            score += len(words & BULLISH_WORDS)
            score -= len(words & BEARISH_WORDS)
        if score > 0:
            return "bullish"
        if score < 0:
            return "bearish"
        return "neutral"

    def _fallback_summary(self, commodity: str, headlines: list[NewsHeadline]) -> str:
        sentiment = self._heuristic_sentiment(headlines)
        driver = {
            "bullish": "safe-haven and momentum flows are supporting prices",
            "bearish": "risk appetite and profit-taking are weighing on prices",
            "neutral": "mixed macro signals are keeping direction balanced",
        }[sentiment]
        return (
            f"{commodity.replace('_', ' ').title()} is reacting to mixed macro and supply-demand headlines.\n"
            f"Current tone suggests {driver}.\n"
            "Watch rate expectations, currency moves, and inventory updates for the next leg."
        )
