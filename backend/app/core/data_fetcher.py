"""Market data access with normalization, bounded caching, and explicit failures."""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

from app.core.config import BENCHMARK_INDEX, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)


class MarketDataUnavailable(RuntimeError):
    """Raised when a provider cannot supply usable market data."""


_CACHE: Dict[Tuple[str, str, str], Tuple[float, pd.DataFrame]] = {}
_CACHE_LOCK = threading.Lock()


def _normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    result = frame.copy()
    if isinstance(result.columns, pd.MultiIndex):
        fields = {"open", "high", "low", "close", "volume"}
        selected = {}
        for col in result.columns:
            parts = [str(part) for part in col]
            match = next((part for part in parts if part.lower() in fields), None)
            if match:
                selected[match.title()] = col
        result = result[[selected[key] for key in selected]].copy()
        result.columns = list(selected)

    result.columns = [str(col).title() for col in result.columns]
    required = ["Open", "High", "Low", "Close", "Volume"]
    if any(col not in result.columns for col in required):
        return pd.DataFrame(columns=required)
    result = result[required]
    for col in required:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result = result.replace([np.inf, -np.inf], np.nan).dropna(subset=required)
    result = result.sort_index()
    result = result[~result.index.duplicated(keep="last")]
    result = result[(result[["Open", "High", "Low", "Close"]] > 0).all(axis=1)]
    result = result[result["High"] >= result["Low"]]
    result["Volume"] = result["Volume"].clip(lower=0).astype("int64")
    return result


def fetch_ohlcv(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    key = (symbol.upper(), period, interval)
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1].copy()

    try:
        raw = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        frame = _normalize_ohlcv(raw)
        if frame.empty:
            raise MarketDataUnavailable(f"No usable market data returned for {symbol}.")
    except MarketDataUnavailable:
        raise
    except Exception as exc:
        logger.exception("Market data provider failed for %s (%s, %s)", symbol, period, interval)
        raise MarketDataUnavailable(f"Market data is currently unavailable for {symbol}.") from exc

    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), frame.copy())
        # Bound memory for long-running API processes.
        if len(_CACHE) > 512:
            oldest = sorted(_CACHE, key=lambda cache_key: _CACHE[cache_key][0])[:128]
            for cache_key in oldest:
                _CACHE.pop(cache_key, None)
    return frame.copy()


def fetch_benchmark(period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    return fetch_ohlcv(BENCHMARK_INDEX, period=period, interval=interval)
