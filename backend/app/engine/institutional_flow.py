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

from app.core.data_fetcher import MarketDataUnavailable, fetch_ohlcv
from app.core.screening_universe import get_screening_universe
from app.core.stock_universe import get_nse_equities

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")
_CACHE_SECONDS = 300
_FLOW_PERIODS = (1, 2, 5, 10, 20)
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
    periods = {}
    for sessions in _FLOW_PERIODS:
        period_flow = float(signed_value.iloc[-sessions:].sum())
        period_turnover = float(traded_value.iloc[-sessions:].sum())
        periods[str(sessions)] = {
            "flow_proxy_cr": round(period_flow / 10_000_000, 2),
            "pressure_pct": round(period_flow / period_turnover * 100, 1) if period_turnover else 0.0,
        }
    flow_20_cr = periods["20"]["flow_proxy_cr"]
    flow_5_cr = periods["5"]["flow_proxy_cr"]
    pressure_20 = periods["20"]["pressure_pct"]
    pressure_5 = periods["5"]["pressure_pct"]
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
        "flow_periods": periods,
        "turnover_20d_cr": round(float(traded_value.sum()) / 10_000_000, 2),
        "average_turnover_daily_cr": round(avg_turnover_cr, 2),
        "volume_ratio_20d": round(volume_ratio, 2),
        "direction": "ACCUMULATION" if flow_20_cr > 0 else "DISTRIBUTION" if flow_20_cr < 0 else "MIXED",
    }


def _rank_results(metadata: Dict[str, Any], results: List[Dict[str, Any]], days: int, limit: int, cached: bool) -> Dict[str, Any]:
    flow_key = str(days)
    accumulation = sorted(
        (row for row in results if row["flow_periods"][flow_key]["flow_proxy_cr"] > 0),
        key=lambda row: row["flow_periods"][flow_key]["flow_proxy_cr"], reverse=True,
    )[:limit]
    distribution = sorted(
        (row for row in results if row["flow_periods"][flow_key]["flow_proxy_cr"] < 0),
        key=lambda row: row["flow_periods"][flow_key]["flow_proxy_cr"],
    )[:limit]
    return {
        **metadata,
        "lookback_sessions": days,
        "accumulation": accumulation,
        "distribution": distribution,
        "cached": cached,
    }


def get_flow_watchlist(limit: int = 10, days: int = 1, force_refresh: bool = False) -> Dict[str, Any]:
    """Return flow-proxy leaders and laggards over the latest completed sessions."""
    global _CACHE
    if days not in _FLOW_PERIODS:
        raise ValueError(f"days must be one of {_FLOW_PERIODS}")
    with _CACHE_LOCK:
        now = clock.monotonic()
        if not force_refresh and _CACHE and now - _CACHE[0] < _CACHE_SECONDS:
            cached_data = _CACHE[1]
            return _rank_results(cached_data["metadata"], cached_data["results"], days, limit, True)

        names: Dict[str, str] = {}
        try:
            stocks, _ = get_nse_equities()
            names = {stock["symbol"]: stock["name"] for stock in stocks}
        except Exception:
            logger.info("NSE company names unavailable for flow scan", exc_info=True)

        universe, universe_metadata = get_screening_universe("nifty500")
        results: List[Dict[str, Any]] = []
        failures = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_score_symbol, symbol, names): symbol for symbol in universe}
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
        metadata = {
            "as_of": max(row["as_of"] for row in results),
            "universe_count": len(universe),
            "universe": "NIFTY 500",
            "universe_source": universe_metadata.get("source"),
            "scored_count": len(results),
            "failed_count": failures,
            "minimum_average_turnover_daily_cr": 5,
            "source": "Yahoo Finance daily OHLCV; turnover approximated as close × volume",
            "method_note": "Net flow proxy weights each session’s traded value by where it closed within that day’s high-low range. It is not identified institutional buying/selling or official delivery data.",
        }
        _CACHE = (clock.monotonic(), {"metadata": metadata, "results": results})
        return _rank_results(metadata, results, days, limit, False)
