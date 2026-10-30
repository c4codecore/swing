"""Configurable NSE screening universes with a 24-hour NIFTY 500 cache."""
from __future__ import annotations

import csv
import io
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from app.core import config
from app.core.stock_universe import get_nse_equities

logger = logging.getLogger(__name__)
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_BUNDLED_CSV = _DATA_DIR / "ind_nifty500list.csv"
_CACHE_CSV = _DATA_DIR / "ind_nifty500list.cache.csv"
_lock = threading.RLock()
_symbols_cache: list[str] | None = None
_cache_time = 0.0
_metadata: dict[str, Any] = {}


def _parse_constituents(raw: str) -> list[str]:
    rows = csv.DictReader(io.StringIO(raw.lstrip("\ufeff")))
    result = []
    for row in rows:
        normalized = {str(k or "").strip().casefold(): str(v or "").strip() for k, v in row.items()}
        symbol = normalized.get("symbol", "").upper()
        if symbol:
            result.append(f"{symbol}.NS")
    return list(dict.fromkeys(result))


def _read_csv(path: Path) -> list[str]:
    return _parse_constituents(path.read_text(encoding="utf-8-sig")) if path.exists() else []


def _download_nifty500() -> list[str]:
    request = Request(config.NIFTY500_CONSTITUENTS_URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept": "text/csv,application/octet-stream,*/*",
        "Referer": "https://www.niftyindices.com/",
    })
    with urlopen(request, timeout=15) as response:
        content = response.read().decode("utf-8-sig", errors="replace")
    symbols = _parse_constituents(content)
    if len(symbols) < 450:
        raise ValueError(f"NIFTY 500 CSV returned only {len(symbols)} EQ constituents")
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_CSV.write_text(content, encoding="utf-8-sig")
    return symbols


def get_nifty500_symbols(force_refresh: bool = False) -> tuple[list[str], dict[str, Any]]:
    """Load NIFTY 500 from a 24h local cache, official source, then bundled CSV."""
    global _symbols_cache, _cache_time, _metadata
    now = time.monotonic()
    with _lock:
        if not force_refresh and _symbols_cache is not None and now - _cache_time < config.UNIVERSE_CACHE_TTL_SECONDS:
            return list(_symbols_cache), dict(_metadata)

        cached_file_is_fresh = (
            _CACHE_CSV.exists()
            and time.time() - _CACHE_CSV.stat().st_mtime < config.UNIVERSE_CACHE_TTL_SECONDS
        )
        if not force_refresh and cached_file_is_fresh:
            symbols = _read_csv(_CACHE_CSV)
            if len(symbols) >= 450:
                _symbols_cache, _cache_time = symbols, now
                _metadata = {"source": "local NIFTY 500 cache", "status": "cached", "count": len(symbols)}
                return list(symbols), dict(_metadata)

        try:
            symbols = _download_nifty500()
            source, status = "NSE Indices NIFTY 500 constituent CSV", "available"
        except Exception as exc:
            logger.warning("Unable to refresh NIFTY 500 constituents: %s", exc)
            symbols = _read_csv(_CACHE_CSV)
            source, status = "stale local NIFTY 500 cache", "stale"
            if len(symbols) < 450:
                symbols = _read_csv(_BUNDLED_CSV)
                source, status = "bundled NIFTY 500 fallback", "fallback"
            if len(symbols) < 450:
                raise RuntimeError("NIFTY 500 source, local cache, and bundled fallback are unavailable or incomplete.") from exc
        _symbols_cache, _cache_time = symbols, time.monotonic()
        _metadata = {"source": source, "status": status, "count": len(symbols),
                     "retrieved_at": datetime.now(timezone.utc).isoformat()}
        return list(symbols), dict(_metadata)


def get_screening_universe(mode: str | None = None, force_refresh: bool = False) -> tuple[list[str], dict[str, Any]]:
    if mode is None:
        if config.USE_NIFTY50_ONLY and config.USE_FULL_NSE_EQUITY_LIST:
            raise ValueError("Choose only one universe override: USE_NIFTY50_ONLY or USE_FULL_NSE_EQUITY_LIST.")
        if config.USE_NIFTY50_ONLY:
            mode = "nifty50"
        elif config.USE_FULL_NSE_EQUITY_LIST:
            mode = "nse_equities"
        else:
            mode = config.SCREENING_UNIVERSE_MODE
    selected = mode.strip().lower()
    if selected == "nifty50":
        symbols = list(config.NIFTY50_UNIVERSE)
        return symbols, {"mode": selected, "source": "NIFTY50_UNIVERSE in core/config.py", "count": len(symbols)}
    if selected == "nifty500":
        symbols, metadata = get_nifty500_symbols(force_refresh=force_refresh)
        return symbols, {**metadata, "mode": selected}
    if selected in {"nse_equities", "full_nse", "all_nse"}:
        stocks, metadata = get_nse_equities(force_refresh=force_refresh)
        symbols = [f"{item['symbol']}.NS" for item in stocks if item.get("series", "EQ").upper() == "EQ"]
        return list(dict.fromkeys(symbols)), {**metadata, "mode": "nse_equities", "count": len(symbols)}
    raise ValueError(f"Unsupported SCREENING_UNIVERSE_MODE: {selected}")
