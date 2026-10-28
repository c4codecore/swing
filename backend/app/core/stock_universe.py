"""Cached NSE main-board and SME equity symbols from the exchange's public lists."""
from __future__ import annotations

import csv
import io
import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from app.core.config import DEFAULT_UNIVERSE

logger = logging.getLogger(__name__)

_LIST_URLS = (
    ("NSE equity", "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"),
    ("NSE SME", "https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv"),
)
_CACHE_SECONDS = 24 * 60 * 60
_cache_lock = threading.Lock()
_cached_stocks: Optional[List[Dict[str, str]]] = None
_cached_at = 0.0
_cached_metadata: Dict[str, Any] = {}


def _read_listing(label: str, url: str) -> List[Dict[str, str]]:
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept": "text/csv,application/octet-stream,*/*",
        "Referer": "https://www.nseindia.com/",
    })
    with urlopen(request, timeout=10) as response:
        content = response.read().decode("utf-8-sig", errors="replace")

    stocks: Dict[str, Dict[str, str]] = {}
    for row in csv.DictReader(io.StringIO(content)):
        normalized = {str(key or "").strip().upper(): str(value or "").strip() for key, value in row.items()}
        symbol = normalized.get("SYMBOL", "").upper()
        name = normalized.get("NAME OF COMPANY") or normalized.get("COMPANY NAME") or normalized.get("NAME") or symbol
        if not re.fullmatch(r"[A-Z0-9&._-]{1,24}", symbol):
            continue
        series = normalized.get("SERIES", "")
        item = {"symbol": symbol, "name": name, "exchange": "NSE", "segment": label, "series": series}
        prior = stocks.get(symbol)
        if prior is None or series == "EQ":
            stocks[symbol] = item
    return list(stocks.values())


def get_nse_equities(force_refresh: bool = False) -> tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Return all symbols in the NSE cash equity and SME lists, with a 24-hour cache."""
    global _cached_stocks, _cached_at, _cached_metadata
    now = time.monotonic()
    if not force_refresh and _cached_stocks is not None and now - _cached_at < _CACHE_SECONDS:
        return list(_cached_stocks), dict(_cached_metadata)

    with _cache_lock:
        now = time.monotonic()
        if not force_refresh and _cached_stocks is not None and now - _cached_at < _CACHE_SECONDS:
            return list(_cached_stocks), dict(_cached_metadata)

        loaded: List[Dict[str, str]] = []
        loaded_sources: List[str] = []
        failures: List[str] = []
        for label, url in _LIST_URLS:
            try:
                rows = _read_listing(label, url)
                if rows:
                    loaded.extend(rows)
                    loaded_sources.append(label)
                else:
                    failures.append(f"{label} list returned no symbols")
            except Exception as exc:
                logger.warning("Unable to refresh %s symbol list: %s", label, exc)
                failures.append(label)

        if loaded:
            merged: Dict[str, Dict[str, str]] = {}
            for item in loaded:
                symbol = item["symbol"]
                # Prefer the main-board record where a company appears in both lists.
                if symbol not in merged or item["segment"] == "NSE equity":
                    merged[symbol] = item
            _cached_stocks = sorted(merged.values(), key=lambda item: item["symbol"])
            _cached_at = time.monotonic()
            _cached_metadata = {
                "source": "NSE official equity and SME listing CSVs",
                "list_status": "available" if len(loaded_sources) == len(_LIST_URLS) else "partial",
                "sources": loaded_sources,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "message": "; ".join(failures) if failures else None,
            }
            return list(_cached_stocks), dict(_cached_metadata)

        if _cached_stocks is not None:
            stale_metadata = dict(_cached_metadata)
            stale_metadata.update({"list_status": "stale", "message": "NSE refresh failed; showing the last cached listing."})
            return list(_cached_stocks), stale_metadata

        # Keep basic research usable if NSE is unreachable on the first request.
        fallback = {symbol.replace(".NS", ""): {
            "symbol": symbol.replace(".NS", ""), "name": symbol.replace(".NS", ""),
            "exchange": "NSE", "segment": "Fallback", "series": "EQ",
        } for symbol in DEFAULT_UNIVERSE}
        fallback["IRCTC"] = {"symbol": "IRCTC", "name": "Indian Railway Catering and Tourism Corporation Limited", "exchange": "NSE", "segment": "Fallback", "series": "EQ"}
        _cached_stocks = sorted(fallback.values(), key=lambda item: item["symbol"])
        _cached_at = time.monotonic()
        _cached_metadata = {
            "source": "Fallback NSE research symbols",
            "list_status": "fallback",
            "sources": [],
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "message": "NSE listings could not be reached, so only the built-in fallback symbols are shown.",
        }
        return list(_cached_stocks), dict(_cached_metadata)


def is_supported_nse_equity(symbol: str) -> bool:
    """Check whether a ticker is present in the cached NSE cash equity universe."""
    normalized = symbol.strip().upper()
    if normalized.endswith(".NS"):
        normalized = normalized[:-3]
    stocks, _ = get_nse_equities()
    return any(item["symbol"] == normalized for item in stocks)
