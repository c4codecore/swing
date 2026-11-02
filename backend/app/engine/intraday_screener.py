"""Intraday stock screener using daily context and completed 5-minute candles."""
from __future__ import annotations

import logging
import threading
import time
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.core.config import (
    BENCHMARK_INDEX, DAILY_DATA_CACHE_TTL_SECONDS, INTRADAY_DATA_TTL_SECONDS,
    INTRADAY_PROFILE_PERIOD, INTRADAY_SCREENING_UNIVERSE_MODE,
)
from app.core.data_fetcher import MarketDataUnavailable, fetch_daily_batch, fetch_benchmark, fetch_intraday_batch
from app.core.screening_universe import get_screening_universe
from app.core.indicators import ema, rsi, atr, macd, bollinger_bands
from app.engine.filters import filter_tradable_symbols

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _as_ist_index(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    idx = pd.DatetimeIndex(result.index)
    if idx.tz is None:
        idx = idx.tz_localize(IST)
    else:
        idx = idx.tz_convert(IST)
    result.index = idx
    return result


def _session_date(value) -> date:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize(IST)
    else:
        stamp = stamp.tz_convert(IST)
    return stamp.date()


def _completed_session_bars(frame: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """Return only completed 5-minute regular-session bars, including today."""
    data = _as_ist_index(frame)
    if data.empty:
        return data
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    else:
        now = now.astimezone(IST)
    # Yahoo timestamps each candle at its start; the candle is usable only after its end.
    data = data[(data.index + pd.Timedelta(minutes=5)) <= pd.Timestamp(now)]
    minutes = data.index.hour * 60 + data.index.minute
    data = data[(minutes >= 9 * 60 + 15) & (minutes < 15 * 60 + 30)]
    return data


def _current_session(frame: pd.DataFrame, now: datetime) -> pd.DataFrame:
    bars = _completed_session_bars(frame, now)
    if bars.empty:
        return bars
    # During market hours, use today's completed bars only. After hours/weekends,
    # keep the latest available session so the result can be explicitly marked stale.
    today = now.astimezone(IST).date() if now.tzinfo else now.date()
    if today in {_session_date(v) for v in bars.index}:
        return bars[[ _session_date(v) == today for v in bars.index ]]
    latest = _session_date(bars.index[-1])
    return bars[[ _session_date(v) == latest for v in bars.index ]]


def _daily_average_volume(daily: pd.DataFrame, today: date, lookback: int = 20) -> Tuple[float, float]:
    """Average completed daily volume and traded value, excluding today's partial bar."""
    if daily.empty:
        return 0.0, 0.0
    bars = daily.copy()
    bars = bars[[ _session_date(v) != today for v in bars.index ]].tail(lookback)
    if bars.empty:
        return 0.0, 0.0
    return float(bars["Volume"].mean()), float((bars["Close"] * bars["Volume"]).mean())


def _fallback_u_profile() -> Dict[int, float]:
    """Market-wide U-shaped cumulative volume share by 5-minute session minute."""
    weights = np.array([1.0 + 0.55 * np.cos(2 * np.pi * ((i + 0.5) / 75.0)) for i in range(75)])
    cumulative = np.cumsum(weights) / weights.sum()
    profile = {5 * (i + 1): float(cumulative[i]) for i in range(75)}
    profile[375] = 1.0
    return profile


_DEFAULT_PROFILE = _fallback_u_profile()
_profile_cache: Dict[str, Tuple[date, Dict[int, float], int]] = {}
_profile_lock = threading.Lock()


def _build_volume_profile(history: pd.DataFrame, today: date) -> Tuple[Dict[int, float], int]:
    """Median per-stock cumulative volume share, indexed by minutes after 09:15."""
    bars = _as_ist_index(history)
    if bars.empty:
        return dict(_DEFAULT_PROFILE), 0
    bars = bars[[ _session_date(v) < today for v in bars.index ]]
    profiles: List[Dict[int, float]] = []
    for session_day, session in bars.groupby([_session_date(v) for v in bars.index]):
        # NSE weekend special sessions are not regular continuous sessions.
        if session_day.weekday() >= 5:
            continue
        session = session.sort_index()
        mins = session.index.hour * 60 + session.index.minute
        session = session[(mins >= 555) & (mins < 930)]
        # Exclude half-days/special sessions and truncated provider history.
        if (len(session) < 65 or float(session["Volume"].sum()) <= 0
                or session.index[0].hour * 60 + session.index[0].minute > 560
                or session.index[-1].hour * 60 + session.index[-1].minute < 915):
            continue
        cumulative = session["Volume"].cumsum() / float(session["Volume"].sum())
        profile: Dict[int, float] = {}
        for stamp, share in cumulative.items():
            minute = int(stamp.hour * 60 + stamp.minute - 555 + 5)
            profile[minute] = float(share)
        profiles.append(profile)
    profiles = profiles[-30:]
    if len(profiles) < 15:
        return dict(_DEFAULT_PROFILE), 0
    keys = sorted({minute for profile in profiles for minute in profile})
    result = {}
    for minute in keys:
        values = [profile[minute] for profile in profiles if minute in profile]
        if values:
            result[minute] = float(np.median(values))
    # Fill missing intervals by interpolation, retaining sensible endpoints.
    out = pd.Series(result, dtype=float).reindex(range(5, 376, 5)).interpolate(limit_direction="both")
    out = out.clip(0.001, 1.0).cummax()
    if len(out):
        out /= max(float(out.iloc[-1]), 1e-9)
        out = pd.Series(np.maximum.accumulate(out.to_numpy()), index=out.index)
        out.iloc[-1] = 1.0
    return {int(k): float(v) for k, v in out.items()}, len(profiles)


def _get_volume_profile(symbol: str, history: pd.DataFrame, today: date) -> Tuple[Dict[int, float], int, bool]:
    with _profile_lock:
        cached = _profile_cache.get(symbol)
        if cached and cached[0] == today:
            return dict(cached[1]), cached[2], cached[2] == 0
    profile, sessions = _build_volume_profile(history, today)
    with _profile_lock:
        _profile_cache[symbol] = (today, dict(profile), sessions)
    return profile, sessions, sessions == 0


def _profile_share(profile: Dict[int, float], elapsed_minutes: int) -> float:
    minute = min(375, max(5, int(np.ceil(elapsed_minutes / 5.0) * 5)))
    keys = sorted(profile)
    prior = [key for key in keys if key <= minute]
    return float(profile[prior[-1]]) if prior else float(profile[keys[0]])


def _session_metrics(session: pd.DataFrame, avg_daily_volume: float, profile: Dict[int, float]) -> Dict[str, float]:
    if session.empty:
        return {}
    close = session["Close"].astype(float)
    vol = session["Volume"].astype(float)
    typical = (session["High"] + session["Low"] + session["Close"]) / 3.0
    total_vol = float(vol.sum())
    vwap = float((typical * vol).sum() / total_vol) if total_vol > 0 else float(close.iloc[-1])
    stamp = session.index[-1]
    elapsed = int(stamp.hour * 60 + stamp.minute - 555 + 5)
    expected_fraction = _profile_share(profile, elapsed)
    expected_volume = avg_daily_volume * expected_fraction
    return {
        "price": float(close.iloc[-1]), "open": float(session["Open"].iloc[0]),
        "high": float(session["High"].max()), "low": float(session["Low"].min()),
        "volume": total_vol, "vwap": vwap,
        "rvol": total_vol / expected_volume if expected_volume > 0 else 0.0,
        "elapsed_minutes": float(elapsed),
    }


def _safe_rsi(values: pd.Series) -> float:
    result = rsi(values, 14)
    return float(result.iloc[-1]) if len(result) and pd.notna(result.iloc[-1]) else 50.0


def _evaluate_strategy(strategy: str, daily: pd.DataFrame, session: pd.DataFrame,
                       benchmark_daily: pd.DataFrame, benchmark_session: pd.DataFrame,
                       metrics: Dict[str, float], avg_volume: float,
                       profile_fallback: bool) -> Optional[Dict[str, Any]]:
    if len(daily) < 55 or len(session) < 3 or not metrics:
        return None
    daily_today = datetime.now(IST).date()
    completed_daily = daily[[ _session_date(v) != daily_today for v in daily.index ]]
    if len(completed_daily) < 55:
        return None
    dc = completed_daily["Close"].astype(float)
    dh, dl = completed_daily["High"].astype(float), completed_daily["Low"].astype(float)
    close = metrics["price"]
    opn, high, low, vwap = metrics["open"], metrics["high"], metrics["low"], metrics["vwap"]
    rvol = metrics["rvol"]
    day_change = (close / float(dc.iloc[-1]) - 1) * 100
    # Current daily bar may be partial: use the last completed daily close as reference.
    prev_close = float(dc.iloc[-1])
    day_change = (close / prev_close - 1) * 100
    gap_pct = (opn / prev_close - 1) * 100
    daily_ema20 = float(ema(dc, 20).iloc[-1]); daily_ema50 = float(ema(dc, 50).iloc[-1]); daily_ema200 = float(ema(dc, 200).iloc[-1]) if len(dc) >= 200 else daily_ema50
    daily_atr = float(atr(completed_daily, 14).iloc[-1])
    daily_rsi = _safe_rsi(dc)
    intraday_rsi = _safe_rsi(session["Close"].astype(float))
    bb_upper, bb_mid, bb_lower, bb_width = bollinger_bands(dc, 20, 2.0)
    resistance5 = float(dh.iloc[-5:].max()); resistance20 = float(dh.iloc[-20:].max())
    day_range = max(high - low, 0.01)
    location = (close - low) / day_range
    atr_value = max(daily_atr, close * 0.004)
    signal = None

    if strategy == "vwap_opening_drive":
        if rvol >= 1.0 and (abs(gap_pct) >= 0.35 or abs(day_change) >= 0.65) and abs(day_change) >= 0.2:
            direction = "BUY" if day_change > 0 else "SHORT"
            if (direction == "BUY" and close >= vwap and intraday_rsi >= 45) or (direction == "SHORT" and close <= vwap and intraday_rsi <= 55):
                signal = (direction, "Gap + Volume Opening Drive", [f"{day_change:+.2f}% move with {gap_pct:+.2f}% opening gap (daily reference)", f"5-minute session RVOL {rvol:.2f}x; 5-minute price is {'above' if direction == 'BUY' else 'below'} VWAP", f"5-minute RSI is {intraday_rsi:.1f}"])
    elif strategy == "orb_prebreakout":
        near_resistance = min(abs(close / resistance5 - 1), abs(close / resistance20 - 1)) <= 0.012
        compressed = day_range <= 1.8 * atr_value
        if (near_resistance or compressed) and close >= daily_ema20 * 0.97 and rvol >= 0.7 and intraday_rsi >= 45:
            signal = ("BUY", "Breakout Setup (Tight Squeeze)", [f"Price is near 5/20-day resistance (₹{min(resistance5, resistance20):.2f}) or in a compressed range", f"Daily ATR ₹{daily_atr:.2f}; 5-minute session RVOL {rvol:.2f}x", f"5-minute RSI is {intraday_rsi:.1f}; daily EMA20 is ₹{daily_ema20:.2f}"])
    elif strategy == "momentum_ignition":
        _, _, hist = macd(dc)
        if day_change >= 1.0 and rvol >= 1.2 and location >= 0.7 and close >= daily_ema20 and intraday_rsi >= 55 and float(hist.iloc[-1]) > 0:
            signal = ("BUY", "Momentum Ignition", [f"Daily move {day_change:+.2f}% and close is in the top part of the session range", f"5-minute RVOL {rvol:.2f}x; 5-minute RSI {intraday_rsi:.1f}", f"Daily EMA20/50/200 context: ₹{daily_ema20:.2f} / ₹{daily_ema50:.2f} / ₹{daily_ema200:.2f}"])
    elif strategy == "mean_reversion":
        if len(session) >= 15 and intraday_rsi <= 42 and close > opn and close >= vwap and low <= float(bb_lower.iloc[-1]) * 1.03:
            signal = ("BUY", "Mean Reversion Bounce", [f"Price tested daily lower Bollinger band (₹{float(bb_lower.iloc[-1]):.2f})", f"5-minute RSI is recovering from oversold at {intraday_rsi:.1f}; price is above 5-minute VWAP", f"Daily RSI is {daily_rsi:.1f}; daily ATR is ₹{daily_atr:.2f}"])
    elif strategy == "rs_surge":
        if benchmark_session is not None and not benchmark_session.empty and not benchmark_daily.empty:
            bench_prior = benchmark_daily[[ _session_date(v) != daily_today for v in benchmark_daily.index ]]
            if len(bench_prior):
                bench_change = (float(benchmark_session["Close"].iloc[-1]) / float(bench_prior["Close"].iloc[-1]) - 1) * 100
                alpha = day_change - bench_change
                if alpha >= 0.8 and rvol >= 1.0 and close >= daily_ema20 and intraday_rsi >= 48 and close >= vwap:
                    signal = ("BUY", "Relative Strength Surge", [f"Intraday relative strength vs NIFTY: {alpha:+.2f}% (stock {day_change:+.2f}%, NIFTY {bench_change:+.2f}%)", f"5-minute RVOL {rvol:.2f}x; 5-minute RSI {intraday_rsi:.1f}", f"Price is above 5-minute VWAP and daily EMA20 ₹{daily_ema20:.2f}"])
    elif strategy == "opening_range_breakout":
        session_minutes = session.index.hour * 60 + session.index.minute
        opening_range = session[(session_minutes >= 555) & (session_minutes < 570)]
        if len(opening_range) >= 3 and session_minutes[-1] >= 570:
            range_high = float(opening_range["High"].max())
            range_low = float(opening_range["Low"].min())
            if close > range_high * 1.001 and close >= vwap and rvol >= 1.0 and intraday_rsi >= 52:
                signal = ("BUY", "15-Min Opening Range Breakout", [f"Price cleared the first 15-minute high at ₹{range_high:.2f}", f"Price is above VWAP with session RVOL {rvol:.2f}x", f"5-minute RSI confirms upward momentum at {intraday_rsi:.1f}"])
            elif close < range_low * 0.999 and close <= vwap and rvol >= 1.0 and intraday_rsi <= 48:
                signal = ("SHORT", "15-Min Opening Range Breakdown", [f"Price fell below the first 15-minute low at ₹{range_low:.2f}", f"Price is below VWAP with session RVOL {rvol:.2f}x", f"5-minute RSI confirms downward momentum at {intraday_rsi:.1f}"])
    elif strategy == "vwap_reclaim":
        typical = (session["High"].astype(float) + session["Low"].astype(float) + session["Close"].astype(float)) / 3.0
        volume = session["Volume"].astype(float)
        cumulative_volume = volume.cumsum().replace(0, np.nan)
        session_vwap = (typical * volume).cumsum() / cumulative_volume
        if len(session_vwap) >= 2 and pd.notna(session_vwap.iloc[-2]) and pd.notna(session_vwap.iloc[-1]):
            reclaimed = float(session["Close"].iloc[-2]) <= float(session_vwap.iloc[-2]) and close > float(session_vwap.iloc[-1])
            lost = float(session["Close"].iloc[-2]) >= float(session_vwap.iloc[-2]) and close < float(session_vwap.iloc[-1])
            if reclaimed and rvol >= 1.0 and intraday_rsi >= 48:
                signal = ("BUY", "VWAP Reclaim", ["Latest completed 5-minute candle moved back above session VWAP", f"Session RVOL {rvol:.2f}x and 5-minute RSI {intraday_rsi:.1f}", "A possible intraday trend recovery; confirm price and risk before acting"])
            elif lost and rvol >= 1.0 and intraday_rsi <= 52:
                signal = ("SHORT", "VWAP Breakdown", ["Latest completed 5-minute candle moved below session VWAP", f"Session RVOL {rvol:.2f}x and 5-minute RSI {intraday_rsi:.1f}", "A possible intraday trend weakening; confirm price and risk before acting"])
    elif strategy == "trend_pullback":
        candle_open = float(session["Open"].iloc[-1])
        vwap_distance = abs(close / vwap - 1) if vwap > 0 else 1.0
        if (daily_ema20 > daily_ema50 and close >= daily_ema20 * 0.99 and close >= vwap
                and vwap_distance <= 0.0075 and close >= candle_open
                and rvol >= 0.8 and 48 <= intraday_rsi <= 68):
            signal = ("BUY", "Trend Pullback Bounce", [f"Daily uptrend: EMA20 ₹{daily_ema20:.2f} is above EMA50 ₹{daily_ema50:.2f}", f"Price is holding near/above VWAP with session RVOL {rvol:.2f}x", f"Latest 5-minute candle is recovering; RSI {intraday_rsi:.1f}"])

    if not signal:
        return None
    direction, title, reasons = signal
    entry = close
    if direction == "BUY":
        stop = max(low - close * 0.001, entry - 1.0 * atr_value)
        risk = entry - stop
        if risk <= 0 or risk / entry > 0.012:
            risk = entry * 0.012; stop = entry - risk
        target1, target2 = entry + 1.5 * risk, entry + 2.5 * risk
    else:
        stop = min(high + close * 0.001, entry + 1.0 * atr_value)
        risk = stop - entry
        if risk <= 0 or risk / entry > 0.012:
            risk = entry * 0.012; stop = entry + risk
        target1, target2 = entry - 1.5 * risk, entry - 2.5 * risk
    confidence = min(95, 60 + min(20, rvol * 8) + (8 if close >= vwap else 0) + (5 if close >= daily_ema20 else 0))
    reasons.append(f"Context uses daily EMA/ATR/RSI; current price, VWAP and RSI use completed 5-minute candles.")
    if profile_fallback:
        reasons.append("RVOL uses the market-wide U-shaped profile because this stock lacks 20 complete sessions of 5-minute history.")
    return {
        "strategy": strategy, "strategy_title": title, "signal": direction,
        "direction": "BULLISH" if direction == "BUY" else "BEARISH",
        "entry_price": round(entry, 2), "stop_loss": round(stop, 2),
        "target_1": round(target1, 2), "target_2": round(target2, 2),
        "risk_reward": 1.5, "risk_per_share": round(risk, 2),
        "risk_pct": round(risk / entry * 100, 2), "confidence_score": round(confidence),
        "rvol": round(rvol, 2), "reasons": reasons,
    }


INTRADAY_STRATEGIES = [
    "vwap_opening_drive", "orb_prebreakout", "momentum_ignition", "mean_reversion", "rs_surge",
    "opening_range_breakout", "vwap_reclaim", "trend_pullback",
]


def _compute_composite_score(signal: Dict[str, Any], metrics: Dict[str, float], avg_traded_value: float) -> float:
    liquidity = min(100.0, np.log10(max(avg_traded_value, 1.0) / 1e7 + 1) * 50)
    rvol_score = min(100.0, metrics.get("rvol", 0.0) * 40)
    distance_vwap = abs(metrics.get("price", 0) / metrics.get("vwap", 1) - 1) * 100
    vwap_score = max(0.0, 100.0 - distance_vwap * 35)
    return round(signal["confidence_score"] * 0.4 + rvol_score * 0.25 + vwap_score * 0.2 + liquidity * 0.15, 1)


_intraday_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_intraday_cache_lock = threading.Lock()


def run_intraday_screener(symbols: Optional[List[str]] = None, strategy_filter: Optional[str] = None,
                          force_refresh: bool = False) -> Dict[str, Any]:
    scan_started = perf_counter()
    if symbols is None:
        selected_symbols, universe_metadata = get_screening_universe(INTRADAY_SCREENING_UNIVERSE_MODE)
    else:
        selected_symbols, universe_metadata = list(symbols), {"mode": "explicit", "count": len(symbols)}
    scan_symbols = list(dict.fromkeys(selected_symbols))
    cache_key = f"{','.join(scan_symbols)}|{strategy_filter or 'all'}"
    with _intraday_cache_lock:
        cached = _intraday_cache.get(cache_key)
        if not force_refresh and cached and time.time() - cached[0] < INTRADAY_DATA_TTL_SECONDS:
            result = deepcopy(cached[1]); result["cached"] = True
            return result

    now = datetime.now(IST)
    today = now.date()
    # Daily context and liquidity pre-filter run before the batched 5-minute request.
    daily_fetch_started = perf_counter()
    daily_frames, daily_failures = fetch_daily_batch(
        scan_symbols, period="1y", cache_ttl_seconds=DAILY_DATA_CACHE_TTL_SECONDS
    )
    failures: List[Dict[str, str]] = [
        {"symbol": item["symbol"].replace(".NS", ""), "reason": item["reason"]}
        for item in daily_failures
    ]
    try:
        benchmark_daily = fetch_benchmark(period="1y")
    except Exception:
        benchmark_daily = pd.DataFrame()
    daily_fetch_seconds = perf_counter() - daily_fetch_started

    filter_started = perf_counter()
    candidates, filter_rejections = filter_tradable_symbols(
        scan_symbols, daily_frames, market="intraday", as_of=now
    )
    daily_stats = {symbol: _daily_average_volume(daily_frames[symbol], today) for symbol in candidates}
    filter_seconds = perf_counter() - filter_started

    intraday_symbols = candidates + [BENCHMARK_INDEX]
    intraday_fetch_started = perf_counter()
    try:
        intraday_frames = fetch_intraday_batch(intraday_symbols, period=INTRADAY_PROFILE_PERIOD, interval="5m", ttl_seconds=INTRADAY_DATA_TTL_SECONDS) if candidates else {}
    except Exception as exc:
        intraday_frames = {}
        batch_error = str(exc)[:160]
    else:
        batch_error = "No 5-minute candles returned"
    intraday_fetch_seconds = perf_counter() - intraday_fetch_started

    for symbol in candidates:
        if symbol not in intraday_frames and not any(
            failure["symbol"] == symbol.replace(".NS", "") for failure in failures
        ):
            failures.append({"symbol": symbol.replace(".NS", ""), "reason": batch_error})
    benchmark_session = _current_session(intraday_frames.get(BENCHMARK_INDEX, pd.DataFrame()), now)
    all_signals: List[Dict[str, Any]] = []
    strategy_eval_started = perf_counter()
    for symbol in candidates:
        if symbol not in intraday_frames:
            continue
        completed_daily = daily_frames[symbol][[ _session_date(v) != today for v in daily_frames[symbol].index ]]
        hist = _as_ist_index(intraday_frames[symbol])
        session = _current_session(hist, now)
        if len(session) < 3:
            continue
        avg_volume, avg_value = daily_stats[symbol]
        profile, profile_sessions, fallback = _get_volume_profile(symbol, hist, today)
        metrics = _session_metrics(session, avg_volume, profile)
        for strat in ([strategy_filter] if strategy_filter else INTRADAY_STRATEGIES):
            if strat not in INTRADAY_STRATEGIES:
                continue
            try:
                signal = _evaluate_strategy(strat, daily_frames[symbol], session, benchmark_daily, benchmark_session,
                                            metrics, avg_volume, fallback)
            except Exception:
                logger.debug("Intraday strategy %s failed for %s", strat, symbol, exc_info=True)
                continue
            if not signal:
                continue
            candle_start = session.index[-1]
            candle_as_of = candle_start + pd.Timedelta(minutes=5)
            as_of = candle_as_of.to_pydatetime()
            age_seconds = max(0.0, (now - as_of).total_seconds())
            signal.update({
                "symbol": symbol.replace(".NS", ""), "raw_symbol": symbol,
                "current_price": round(metrics["price"], 2),
                "change_pct": round((metrics["price"] / float(completed_daily["Close"].iloc[-1]) - 1) * 100, 2),
                "signal_date": today.isoformat(), "timestamp": as_of.isoformat(),
                "last_candle_at": as_of.isoformat(), "data_delay_seconds": int(age_seconds),
                "stale": age_seconds > INTRADAY_DATA_TTL_SECONDS,
                "data_source": "Yahoo Finance 5-minute candles; daily context from Yahoo Finance",
                "profile_sessions": profile_sessions, "profile_fallback": fallback,
                "composite_score": _compute_composite_score(signal, metrics, avg_value),
            })
            all_signals.append(signal)
    strategy_eval_seconds = perf_counter() - strategy_eval_started

    best_per_symbol: Dict[str, Dict[str, Any]] = {}
    for signal in all_signals:
        sym = signal["symbol"]
        if sym not in best_per_symbol or signal["composite_score"] > best_per_symbol[sym]["composite_score"]:
            best_per_symbol[sym] = signal
    unique_signals = sorted(best_per_symbol.values(), key=lambda s: s["composite_score"], reverse=True)
    succeeded = len(daily_frames)
    if succeeded == 0 and scan_symbols:
        raise MarketDataUnavailable("Market data is unavailable for all scanned symbols.")
    strat_counts: Dict[str, int] = {}
    for signal in unique_signals:
        strat_counts[signal["strategy"]] = strat_counts.get(signal["strategy"], 0) + 1
    result = {
        "count": len(unique_signals), "signals": unique_signals,
        "cached": False, "timestamp": now.isoformat(),
        "data_status": "complete" if not failures else "partial",
        "scan_summary": {"requested": len(scan_symbols), "succeeded": succeeded, "failed": len(failures),
                         "failed_symbols": [item["symbol"] for item in failures],
                         "universe": universe_metadata,
                         "duration_seconds": round(perf_counter() - scan_started, 3),
                         "timings_seconds": {
                             "daily_data": round(daily_fetch_seconds, 3),
                             "tradability_filter": round(filter_seconds, 3),
                             "five_minute_data": round(intraday_fetch_seconds, 3),
                             "strategy_calculation": round(strategy_eval_seconds, 3),
                         },
                         "daily_fetch_method": "paced Yahoo Finance multi-symbol batches",
                         "candidate_5m_requests": len(candidates), "total_setups": len(unique_signals),
                         "filter_rejections": filter_rejections},
        "filter_rejections": filter_rejections,
        "strategy_distribution": strat_counts, "errors": failures[:10],
        "strategies_available": [
            {"id": "vwap_opening_drive", "title": "Gap + Volume Opening Drive", "description": "Daily gap context with completed 5-minute price, VWAP, RSI and RVOL"},
            {"id": "orb_prebreakout", "title": "Breakout Setup (Tight Squeeze)", "description": "Daily resistance and ATR with completed 5-minute confirmation"},
            {"id": "momentum_ignition", "title": "Momentum Ignition", "description": "Daily trend and MACD context with completed 5-minute RSI and RVOL"},
            {"id": "mean_reversion", "title": "Mean Reversion Bounce", "description": "Daily Bollinger support with completed 5-minute VWAP and RSI"},
            {"id": "rs_surge", "title": "Relative Strength Surge", "description": "Completed 5-minute stock performance relative to the NIFTY 500 benchmark"},
            {"id": "opening_range_breakout", "title": "15-Min Opening Range Breakout", "description": "Confirmed move beyond the first 15-minute high/low with VWAP and volume checks"},
            {"id": "vwap_reclaim", "title": "VWAP Reclaim / Breakdown", "description": "Latest completed 5-minute candle crosses session VWAP with volume confirmation"},
            {"id": "trend_pullback", "title": "Trend Pullback Bounce", "description": "Daily uptrend with a 5-minute pullback holding around VWAP"},
        ],
        "disclaimer": "Decision-support only. Not investment advice. Past performance does not guarantee future results. No orders are placed.",
    }
    with _intraday_cache_lock:
        _intraday_cache[cache_key] = (time.time(), deepcopy(result))
        if len(_intraday_cache) > 16:
            for key in sorted(_intraday_cache, key=lambda k: _intraday_cache[k][0])[:8]:
                _intraday_cache.pop(key, None)
    return result
