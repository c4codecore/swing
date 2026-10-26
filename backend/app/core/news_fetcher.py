"""Best-effort recent company headlines for live setup review.

Yahoo Finance news is a discovery feed, not a complete or authoritative source.
This module flags obvious event-risk wording; it deliberately does not claim to
understand headline sentiment or treat missing headlines as positive evidence.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import yfinance as yf

logger = logging.getLogger(__name__)
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_LOCK = threading.Lock()
_TTL_SECONDS = 900
_MAX_AGE_SECONDS = 72 * 60 * 60
_EVENT_RISK_TERMS = (
    "fraud", "probe", "investigation", "default", "insolvency", "bankruptcy",
    "sebi action", "regulatory action", "accounting issue", "resigns", "resignation",
    "earnings miss", "profit warning", "guidance cut", "downgrade", "recall",
    "production halt", "plant shutdown", "debt restructuring",
)


def _article_content(article: dict) -> dict:
    content = article.get("content", article)
    return content if isinstance(content, dict) else article


def _published_at(content: dict, article: dict) -> int:
    for value in (
        content.get("providerPublishTime"), article.get("providerPublishTime"),
        content.get("pubDate"), content.get("displayTime"),
    ):
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return int(parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).timestamp())
            except ValueError:
                continue
    return 0


def fetch_news_context(symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Return recent headlines and a conservative event-risk flag for a ticker."""
    now = time.time()
    with _LOCK:
        cached = _CACHE.get(symbol)
        if not force_refresh and cached and now - cached[0] < _TTL_SECONDS:
            return dict(cached[1])

    try:
        articles = yf.Ticker(symbol).get_news(count=12, tab="news") or []
        headlines: List[dict] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            content = _article_content(article)
            title = content.get("title") or article.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            published = _published_at(content, article)
            age_seconds = now - published if published else None
            if age_seconds is not None and age_seconds > _MAX_AGE_SECONDS:
                continue
            canonical = content.get("canonicalUrl") or article.get("link") or {}
            url = canonical.get("url") if isinstance(canonical, dict) else canonical
            headlines.append({
                "title": title.strip(), "url": url if isinstance(url, str) else None,
                "published_at": datetime.fromtimestamp(published, timezone.utc).isoformat() if published else None,
                "source": (content.get("provider") or {}).get("displayName")
                    if isinstance(content.get("provider"), dict) else None,
            })
        flagged = [
            item for item in headlines
            if any(term in item["title"].casefold() for term in _EVENT_RISK_TERMS)
        ]
        result = {
            "status": "available" if headlines else "no_recent_headlines",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "lookback_hours": 72,
            "event_risk": bool(flagged),
            "event_risk_headlines": flagged[:3],
            "headlines": headlines[:5],
            "source": "Yahoo Finance news via yfinance",
            "limitations": "Headline keyword screening only; verify the full story and primary disclosures.",
        }
    except Exception as exc:
        logger.info("News lookup unavailable for %s: %s", symbol, exc)
        result = {
            "status": "unavailable", "checked_at": datetime.now(timezone.utc).isoformat(),
            "lookback_hours": 72, "event_risk": None, "event_risk_headlines": [],
            "headlines": [], "source": "Yahoo Finance news via yfinance",
            "limitations": "News feed could not be checked; review current company disclosures manually.",
        }

    with _LOCK:
        _CACHE[symbol] = (now, result)
        if len(_CACHE) > 512:
            oldest = sorted(_CACHE, key=lambda key: _CACHE[key][0])[:128]
            for key in oldest:
                _CACHE.pop(key, None)
    return dict(result)
