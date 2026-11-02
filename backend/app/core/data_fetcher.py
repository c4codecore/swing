"""Market data access with normalization, bounded caching, and explicit failures."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Dict, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from app.core import config
from app.core.config import BENCHMARK_INDEX, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)


class MarketDataUnavailable(RuntimeError):
    """Raised when a provider cannot supply usable market data."""


_CACHE: Dict[Tuple[str, str, str], Tuple[float, pd.DataFrame]] = {}
_CACHE_LOCK = threading.Lock()
_INTRADAY_BATCH_CACHE: Dict[Tuple[Tuple[str, ...], str, str], Tuple[float, Dict[str, pd.DataFrame]]] = {}
_INTRADAY_HISTORY_CACHE: Dict[Tuple[Tuple[str, ...], str], Tuple[object, Dict[str, pd.DataFrame]]] = {}


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
        if len(_CACHE) > config.MARKET_DATA_CACHE_MAX_ITEMS:
            oldest = sorted(_CACHE, key=lambda cache_key: _CACHE[cache_key][0])[:max(128, config.MARKET_DATA_CACHE_MAX_ITEMS // 16)]
            for cache_key in oldest:
                _CACHE.pop(cache_key, None)
    return frame.copy()


def fetch_benchmark(period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    return fetch_ohlcv(BENCHMARK_INDEX, period=period, interval=interval)


def _split_yf_download(raw: pd.DataFrame, tickers: tuple[str, ...]) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return frames
    if isinstance(raw.columns, pd.MultiIndex):
        for ticker in tickers:
            try:
                part = raw[ticker] if ticker in raw.columns.get_level_values(0) else raw.xs(ticker, axis=1, level=1)
            except (KeyError, ValueError):
                continue
            frame = _normalize_ohlcv(part)
            if not frame.empty:
                if frame.index.tz is None:
                    frame.index = frame.index.tz_localize(ZoneInfo("Asia/Kolkata"))
                frames[ticker] = frame
    elif len(tickers) == 1:
        frame = _normalize_ohlcv(raw)
        if not frame.empty:
            if frame.index.tz is None:
                frame.index = frame.index.tz_localize(ZoneInfo("Asia/Kolkata"))
            frames[tickers[0]] = frame
    return frames


def fetch_daily_batch(symbols, period: str = "1y", interval: str = "1d",
                      cache_ttl_seconds: int = CACHE_TTL_SECONDS) -> tuple[Dict[str, pd.DataFrame], list[dict[str, str]]]:
    """Fetch daily OHLCV in paced multi-symbol Yahoo requests and populate the shared cache.

    Returns `(frames_by_symbol, failures)` so a screener can summarize missing symbols.
    Batches are intentionally sequential; yfinance itself handles request concurrency
    within each bounded batch, while retries use exponential backoff between requests.
    """
    symbols_tuple = tuple(dict.fromkeys(str(symbol).upper() for symbol in symbols if symbol))
    if not symbols_tuple:
        return {}, []
    now = time.monotonic()
    frames: Dict[str, pd.DataFrame] = {}
    missing = []
    with _CACHE_LOCK:
        for symbol in symbols_tuple:
            cached = _CACHE.get((symbol, period, interval))
            if cached and now - cached[0] < cache_ttl_seconds:
                frames[symbol] = cached[1].copy()
            else:
                missing.append(symbol)

    failures: list[dict[str, str]] = []
    batch_size = max(1, int(config.DAILY_BATCH_SIZE))
    for start in range(0, len(missing), batch_size):
        batch = tuple(missing[start:start + batch_size])
        last_error = "Yahoo returned no usable daily bars"
        batch_frames: Dict[str, pd.DataFrame] = {}
        remaining = batch
        for attempt in range(max(1, config.DAILY_BATCH_RETRIES)):
            try:
                raw = yf.download(
                    tickers=list(remaining), period=period, interval=interval,
                    auto_adjust=True, group_by="ticker", progress=False,
                    threads=True, prepost=False,
                )
                batch_frames.update(_split_yf_download(raw, remaining))
                remaining = tuple(symbol for symbol in remaining if symbol not in batch_frames)
                if not remaining:
                    break
                last_error = "Yahoo returned no usable daily bars for: " + ", ".join(remaining)
            except Exception as exc:
                last_error = str(exc)[:180]
                logger.warning("Yahoo daily batch failed (attempt %s/%s, %s symbols): %s",
                               attempt + 1, config.DAILY_BATCH_RETRIES, len(batch), last_error)
            if attempt + 1 < max(1, config.DAILY_BATCH_RETRIES):
                delay = config.DAILY_BATCH_BACKOFF_SECONDS * (2 ** attempt)
                time.sleep(delay)

        with _CACHE_LOCK:
            for symbol, frame in batch_frames.items():
                _CACHE[(symbol, period, interval)] = (time.monotonic(), frame.copy())
        frames.update(batch_frames)
        for symbol in remaining:
            if symbol not in batch_frames:
                failures.append({"symbol": symbol, "reason": last_error})
        if start + batch_size < len(missing) and config.DAILY_BATCH_PAUSE_SECONDS > 0:
            time.sleep(config.DAILY_BATCH_PAUSE_SECONDS)

    with _CACHE_LOCK:
        if len(_CACHE) > config.MARKET_DATA_CACHE_MAX_ITEMS:
            oldest = sorted(_CACHE, key=lambda cache_key: _CACHE[cache_key][0])[:max(128, config.MARKET_DATA_CACHE_MAX_ITEMS // 16)]
            for cache_key in oldest:
                _CACHE.pop(cache_key, None)
    return {symbol: frame.copy() for symbol, frame in frames.items()}, failures


def _fetch_intraday_batch_chunk(symbols, period: str = "60d", interval: str = "5m",
                                ttl_seconds: int = 180) -> Dict[str, pd.DataFrame]:
    """Fetch 5-minute bars for multiple symbols in one Yahoo request.

    Yahoo only retains roughly 60 days of 5-minute history. Raw historical
    sessions are cached per IST date; today's bars are refreshed on a short TTL.
    """
    tickers = tuple(sorted({str(symbol).upper() for symbol in symbols if symbol}))
    if not tickers:
        return {}
    cache_key = (tickers, period, interval)
    history_key = (tickers, interval)
    now = time.monotonic()
    today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    with _CACHE_LOCK:
        cached = _INTRADAY_BATCH_CACHE.get(cache_key)
        if cached and now - cached[0] < ttl_seconds:
            return {key: frame.copy() for key, frame in cached[1].items()}
        historical = _INTRADAY_HISTORY_CACHE.get(history_key)

    # Download the longer lookback only once per IST date. Between those
    # refreshes, update today's bars using a much smaller one-day batch.
    refresh_period = period if not historical or historical[0] != today_ist else "1d"

    raw = yf.download(
        tickers=list(tickers), period=refresh_period, interval=interval,
        auto_adjust=True, group_by="ticker", progress=False, threads=True,
        prepost=False,
    )
    frames: Dict[str, pd.DataFrame] = {}
    if raw is not None and not raw.empty:
        if isinstance(raw.columns, pd.MultiIndex):
            top = {str(v).upper() for v in raw.columns.get_level_values(0)}
            bottom = {str(v).upper() for v in raw.columns.get_level_values(1)}
            for ticker in tickers:
                if ticker in top:
                    part = raw[ticker]
                elif ticker in bottom:
                    part = raw.xs(ticker, axis=1, level=1)
                else:
                    continue
                normalized = _normalize_ohlcv(part)
                if not normalized.empty:
                    frames[ticker] = normalized
        elif len(tickers) == 1:
            normalized = _normalize_ohlcv(raw)
            if not normalized.empty:
                frames[tickers[0]] = normalized

    if refresh_period != period and historical:
        merged = {key: frame.copy() for key, frame in historical[1].items()}
        for ticker, fresh in frames.items():
            prior = merged.get(ticker)
            combined = pd.concat([prior, fresh]).sort_index() if prior is not None else fresh
            merged[ticker] = combined.loc[~combined.index.duplicated(keep="last")]
        frames = merged
    with _CACHE_LOCK:
        _INTRADAY_HISTORY_CACHE[history_key] = (today_ist, {key: frame.copy() for key, frame in frames.items()})
        _INTRADAY_BATCH_CACHE[cache_key] = (time.monotonic(), {key: frame.copy() for key, frame in frames.items()})
        if len(_INTRADAY_BATCH_CACHE) > 32:
            oldest = sorted(_INTRADAY_BATCH_CACHE, key=lambda key: _INTRADAY_BATCH_CACHE[key][0])[:8]
            for key in oldest:
                _INTRADAY_BATCH_CACHE.pop(key, None)
        if len(_INTRADAY_HISTORY_CACHE) > 32:
            for key in list(_INTRADAY_HISTORY_CACHE)[:8]:
                _INTRADAY_HISTORY_CACHE.pop(key, None)
    return {key: frame.copy() for key, frame in frames.items()}


def fetch_intraday_batch(symbols, period: str = "60d", interval: str = "5m",
                         ttl_seconds: int = 180) -> Dict[str, pd.DataFrame]:
    """Fetch 5-minute data only for supplied candidates, in bounded Yahoo batches."""
    tickers = tuple(sorted({str(symbol).upper() for symbol in symbols if symbol}))
    if not tickers:
        return {}
    size = max(1, int(config.INTRADAY_BATCH_SIZE))
    merged: Dict[str, pd.DataFrame] = {}
    for offset in range(0, len(tickers), size):
        chunk = tickers[offset:offset + size]
        merged.update(_fetch_intraday_batch_chunk(chunk, period, interval, ttl_seconds))
    return merged
