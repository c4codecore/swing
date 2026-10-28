"""Rank liquid NSE stocks by OHLCV-based accumulation/distribution pressure.

This is an activity proxy derived from daily candle location and traded volume.
It does not identify institutional investors or measure actual FII/DII flows.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time
import logging
import threading
import time as clock
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import pandas as pd

from app.core.config import DEFAULT_UNIVERSE
from app.core.data_fetcher import MarketDataUnavailable, fetch_ohlcv
from app.core.stock_universe import get_nse_equities

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")
_CACHE_SECONDS = 300
_CACHE_LOCK = threading.Lock()
_CACHE: Optional[Tuple[float, Dict[str, Any]]] = None


def _completed_candles(frame: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(_IST)
    if now.time() < time(15, 45):
        today = now.date()
        return frame[[stamp.date() < today for stamp in frame.index]]
    return frame


def _score_symbol(symbol: str, names: Dict[str, str]) -> Optional[Dict[str, Any]]:
    frame = _completed_candles(fetch_ohlcv(symbol, period="3mo"))
    if len(frame) < 25:
        return None
    candles = frame.iloc[-20:].copy()
    ranges = candles["High"] - candles["Low"]
    close_location = ((2 * candles["Close"] - candles["High"] - candles["Low"]) / ranges.replace(0, float("nan"))).replace([float("inf"), float("-inf")], 0).fillna(0).clip(-1, 1)
    traded_value = candles["Close"] * candles["Volume"]
    total_turnover = float(traded_value.sum())
    if total_turnover <= 0:
        return None

    signed_value = close_location * traded_value
    flow_20_cr = float(signed_value.sum()) / 10_000_000
    flow_5_cr = float(signed_value.iloc[-5:].sum()) / 10_000_000
    pressure_20 = float(signed_value.sum() / total_turnover * 100)
    recent_turnover = float(traded_value.iloc[-5:].sum())
    pressure_5 = float(signed_value.iloc[-5:].sum() / recent_turnover * 100) if recent_turnover else 0.0
    previous_volumes = frame["Volume"].iloc[-21:-1]
    volume_ratio = float(frame["Volume"].iloc[-1] / previous_volumes.mean()) if len(previous_volumes) and previous_volumes.mean() else 0.0
    last = frame.iloc[-1]
    previous_close = float(frame["Close"].iloc[-2])
    avg_turnover_cr = float(traded_value.mean()) / 10_000_000

    return {
        "symbol": symbol.removesuffix(".NS"),
        "company_name": names.get(symbol.removesuffix(".NS"), symbol.removesuffix(".NS")),
        "as_of": frame.index[-1].strftime("%Y-%m-%d"),
        "close": round(float(last["Close"]), 2),
        "change_pct": round((float(last["Close"]) / previous_close - 1) * 100, 2) if previous_close else None,
        "pressure_5d_pct": round(pressure_5, 1),
        "pressure_20d_pct": round(pressure_20, 1),
        "flow_proxy_5d_cr": round(flow_5_cr, 2),
        "flow_proxy_20d_cr": round(flow_20_cr, 2),
        "turnover_20d_cr": round(float(traded_value.sum()) / 10_000_000, 2),
        "average_turnover_daily_cr": round(avg_turnover_cr, 2),
        "volume_ratio_20d": round(volume_ratio, 2),
        "direction": "ACCUMULATION" if flow_20_cr > 0 else "DISTRIBUTION" if flow_20_cr < 0 else "MIXED",
    }


def get_flow_watchlist(limit: int = 10, force_refresh: bool = False) -> Dict[str, Any]:
    """Return up to `limit` positive and negative flow-proxy ranks."""
    global _CACHE
    with _CACHE_LOCK:
        now = clock.monotonic()
        if not force_refresh and _CACHE and now - _CACHE[0] < _CACHE_SECONDS:
            data = dict(_CACHE[1])
            data["cached"] = True
            return {**data, "accumulation": data["accumulation"][:limit], "distribution": data["distribution"][:limit]}

        names: Dict[str, str] = {}
        try:
            stocks, _ = get_nse_equities()
            names = {stock["symbol"]: stock["name"] for stock in stocks}
        except Exception:
            logger.info("NSE company names unavailable for flow scan", exc_info=True)

        results: List[Dict[str, Any]] = []
        failures = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_score_symbol, symbol, names): symbol for symbol in DEFAULT_UNIVERSE}
            for future in as_completed(futures):
                try:
                    row = future.result()
                    if row and row["average_turnover_daily_cr"] >= 5:
                        results.append(row)
                except Exception as exc:
                    failures += 1
                    logger.info("Flow scan could not score %s: %s", futures[future], exc)

        if not results:
            raise MarketDataUnavailable("Flow scan could not load enough daily volume data.")
        results.sort(key=lambda row: row["flow_proxy_20d_cr"], reverse=True)
        data = {
            "as_of": max(row["as_of"] for row in results),
            "universe_count": len(DEFAULT_UNIVERSE),
            "scored_count": len(results),
            "failed_count": failures,
            "minimum_average_turnover_daily_cr": 5,
            "lookback_sessions": 20,
            "source": "Yahoo Finance daily OHLCV; turnover approximated as close × volume",
            "method_note": "Net flow proxy weights each session’s traded value by where it closed within that day’s high-low range. It is not identified institutional buying/selling or official delivery data.",
            "accumulation": [row for row in results if row["flow_proxy_20d_cr"] > 0][:limit],
            "distribution": sorted((row for row in results if row["flow_proxy_20d_cr"] < 0), key=lambda row: row["flow_proxy_20d_cr"])[:limit],
            "cached": False,
        }
        _CACHE = (clock.monotonic(), data)
        return data
