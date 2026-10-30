"""
World-class Intraday Stock Screener — Multi-signal filtering engine.

Scans the liquid NSE stock universe using OHLCV data and
produces high-conviction intraday setups across 5 proven strategies:

1. VWAP Magnet + Opening Drive  — High relative volume (RVOL) with directional gap or session drive
2. Breakout Setup (ORB/Squeeze) — Narrow range consolidation coiled near moving averages (energy release)
3. Momentum Ignition            — RSI momentum band + MACD bullish acceleration + Volume expansion
4. Mean Reversion Snap          — Oversold bounce off Bollinger lower bands with reversal confirmation
5. Relative Strength Surge      — Strong alpha outperformance against NIFTY 50 benchmark

Features:
- Session-aware Relative Volume (RVOL): Accurately normalizes intraday volume during active market hours
  so morning scans are not penalized by partial daily candle volumes.
- Precise risk-reward trade plans: Entry price, Stop loss (ATR/Swing low), Target 1, Target 2.
- Confidence scoring and directional classification (BULLISH vs BEARISH).
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, time as dtime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.core.config import DEFAULT_UNIVERSE, BENCHMARK_INDEX
from app.core.data_fetcher import MarketDataUnavailable, fetch_ohlcv, fetch_benchmark
from app.core.indicators import ema, sma, rsi, atr, macd, bollinger_bands, relative_strength

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _get_session_fraction() -> float:
    """
    Returns the fraction of the regular NSE equity market day (9:15 to 15:30)
    that has elapsed so far. Used to calculate Relative Volume (RVOL) without
    penalizing partial daily candles during market hours.
    """
    now = datetime.now(IST)
    market_open = dtime(9, 15)
    market_close = dtime(15, 30)
    current_time = now.time()

    if market_open <= current_time <= market_close and now.weekday() < 5:
        minutes_elapsed = (now.hour - 9) * 60 + (now.minute - 15)
        # Minimum 5% to avoid divide-by-zero during the first minute
        return max(0.05, min(1.0, minutes_elapsed / 375.0))
    return 1.0


# ---------------------------------------------------------------------------
# 5 World-Class Intraday Strategy Evaluators
# ---------------------------------------------------------------------------

def _vwap_opening_drive(df: pd.DataFrame, session_fraction: float = 1.0) -> Optional[Dict[str, Any]]:
    """
    Strategy 1: VWAP Magnet + Opening Drive

    Professional Concept:
    Stocks opening with a directional gap or strong opening drive accompanied
    by institutional relative volume (RVOL >= 0.85x) continue trending in that direction.
    """
    if len(df) < 55:
        return None

    close = df["Close"]
    opn = df["Open"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    cur_close = float(close.iloc[-1])
    cur_open = float(opn.iloc[-1])
    prev_close = float(close.iloc[-2])
    cur_vol = float(vol.iloc[-1])
    vol_avg = float(sma(vol, 20).iloc[-1])

    if vol_avg <= 0:
        return None

    # Session-normalized Relative Volume
    rvol = cur_vol / (vol_avg * session_fraction) if session_fraction > 0 else 1.0
    if rvol < 0.80:
        return None

    gap_pct = ((cur_open - prev_close) / prev_close) * 100
    day_change_pct = ((cur_close - prev_close) / prev_close) * 100
    has_gap = abs(gap_pct) >= 0.35
    has_drive = abs(day_change_pct) >= 0.75

    if not (has_gap or has_drive):
        return None

    direction = "BUY" if day_change_pct >= 0 else "SHORT"
    rsi_val = float(rsi(close, 14).iloc[-1])
    ema9 = float(ema(close, 9).iloc[-1])

    if direction == "BUY":
        if rsi_val < 42 or rsi_val > 80:
            return None
        if cur_close < ema9 * 0.992:
            return None
    else:
        if rsi_val > 58 or rsi_val < 20:
            return None
        if cur_close > ema9 * 1.008:
            return None

    atr_val = float(atr(df, 14).iloc[-1])

    if direction == "BUY":
        entry = cur_close
        swing_low = float(low.iloc[-3:].min())
        stop = round(max(swing_low * 0.996, entry - 1.25 * atr_val), 2)
        risk = entry - stop
        if risk <= 0 or (risk / entry) > 0.055:
            stop = round(entry * 0.985, 2)
            risk = entry - stop
        target_1 = round(entry + 1.5 * risk, 2)
        target_2 = round(entry + 2.5 * risk, 2)
    else:
        entry = cur_close
        swing_high = float(high.iloc[-3:].max())
        stop = round(min(swing_high * 1.004, entry + 1.25 * atr_val), 2)
        risk = stop - entry
        if risk <= 0 or (risk / entry) > 0.055:
            stop = round(entry * 1.015, 2)
            risk = stop - entry
        target_1 = round(entry - 1.5 * risk, 2)
        target_2 = round(entry - 2.5 * risk, 2)

    confidence = 72
    if rvol >= 1.2:
        confidence += 8
    if rvol >= 1.8:
        confidence += 6
    if 50 <= rsi_val <= 68:
        confidence += 5

    return {
        "strategy": "vwap_opening_drive",
        "strategy_title": "Gap + Volume Opening Drive",
        "signal": direction,
        "direction": "BULLISH" if direction == "BUY" else "BEARISH",
        "entry_price": round(entry, 2),
        "stop_loss": round(stop, 2),
        "target_1": target_1,
        "target_2": target_2,
        "risk_reward": round(1.5, 2),
        "risk_per_share": round(risk, 2),
        "risk_pct": round((risk / entry) * 100, 2),
        "confidence_score": min(confidence, 94),
        "reasons": [
            f"{'Bullish' if direction == 'BUY' else 'Bearish'} drive: {day_change_pct:+.2f}% with gap {gap_pct:+.2f}%",
            f"Relative Volume (RVOL) at {rvol:.2f}x expected volume for this time of day",
            f"RSI positioned at {rsi_val:.1f} — active trend momentum",
            f"Price {'holding above' if direction == 'BUY' else 'breaking below'} short-term 9-EMA (₹{ema9:.1f})",
        ],
    }


def _orb_prebreakout(df: pd.DataFrame, session_fraction: float = 1.0) -> Optional[Dict[str, Any]]:
    """
    Strategy 2: Breakout Setup (Tight Squeeze / ORB Coiling)

    Professional Concept:
    Identifies stocks undergoing consolidation (narrow daily range / Bollinger Band squeeze)
    coiled near 20-EMA support, building energy for a clean opening-range breakout.
    """
    if len(df) < 55:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    atr_val = float(atr(df, 14).iloc[-1])
    if atr_val <= 0:
        return None

    # Current bar range
    bar_range = float(high.iloc[-1] - low.iloc[-1])
    is_narrow_bar = bar_range <= 1.05 * atr_val

    # 3-day range
    recent_3d_range = float(high.iloc[-3:].max() - low.iloc[-3:].min())
    is_tight_3d = recent_3d_range <= 2.2 * atr_val

    _, _, _, bw = bollinger_bands(close, 20, 2.0)
    bw_now = float(bw.iloc[-1]) if pd.notna(bw.iloc[-1]) else 999
    bw_history = bw.dropna().iloc[-40:]
    bw_pctile = float((bw_history < bw_now).mean()) if len(bw_history) >= 20 else 0.5
    is_bb_squeeze = bw_pctile <= 0.40 or bw_now <= 0.09

    if not (is_narrow_bar or is_tight_3d or is_bb_squeeze):
        return None

    ema20 = ema(close, 20)
    p_close = float(close.iloc[-1])
    p_ema20 = float(ema20.iloc[-1])
    dist_ema20 = abs(p_close - p_ema20) / p_ema20 * 100
    if dist_ema20 > 4.0:
        return None

    vol_avg = float(sma(vol, 20).iloc[-1])
    if vol_avg <= 0:
        return None
    rvol = float(vol.iloc[-1]) / (vol_avg * session_fraction) if session_fraction > 0 else 1.0
    if rvol < 0.65:
        return None

    rsi_val = float(rsi(close, 14).iloc[-1])
    if rsi_val < 42 or rsi_val > 75:
        return None

    entry = p_close
    swing_low = float(low.iloc[-3:].min())
    stop = round(min(swing_low * 0.997, entry - 1.0 * atr_val), 2)
    risk = entry - stop
    if risk <= 0 or (risk / entry) > 0.05:
        stop = round(entry * 0.985, 2)
        risk = entry - stop

    target_1 = round(entry + 1.8 * risk, 2)
    target_2 = round(entry + 2.8 * risk, 2)

    confidence = 74
    if bw_pctile <= 0.25:
        confidence += 8
    if rvol >= 1.0:
        confidence += 6
    if p_close >= p_ema20:
        confidence += 5

    return {
        "strategy": "orb_prebreakout",
        "strategy_title": "Breakout Setup (Tight Squeeze)",
        "signal": "BUY",
        "direction": "BULLISH",
        "entry_price": round(entry, 2),
        "stop_loss": stop,
        "target_1": target_1,
        "target_2": target_2,
        "risk_reward": round(1.8, 2),
        "risk_per_share": round(risk, 2),
        "risk_pct": round((risk / entry) * 100, 2),
        "confidence_score": min(confidence, 93),
        "reasons": [
            f"Tight price coil: current range ₹{bar_range:.1f} vs daily ATR ₹{atr_val:.1f}",
            f"Bollinger Bandwidth at {bw_now:.3f} — energy consolidation",
            f"Coiled near 20-EMA base (₹{p_ema20:.1f}, dist {dist_ema20:.1f}%)",
            f"RSI healthy at {rsi_val:.1f} — prime setup for breakout continuation",
        ],
    }


def _momentum_ignition(df: pd.DataFrame, session_fraction: float = 1.0) -> Optional[Dict[str, Any]]:
    """
    Strategy 3: Momentum Ignition (Triple Confirmation)

    Professional Concept:
    RSI in healthy momentum acceleration zone (50-76) + MACD bullish acceleration
    + session RVOL confirming institutional buying pressure.
    """
    if len(df) < 55:
        return None

    close = df["Close"]
    vol = df["Volume"]

    rsi_series = rsi(close, 14)
    rsi_now = float(rsi_series.iloc[-1])
    if rsi_now < 50 or rsi_now > 76:
        return None

    _, _, hist = macd(close)
    hist_now = float(hist.iloc[-1])
    hist_prev = float(hist.iloc[-2])
    is_macd_bullish = hist_now > 0 or (hist_now > hist_prev and hist_now > -0.75)
    if not is_macd_bullish:
        return None

    vol_avg = float(sma(vol, 20).iloc[-1])
    if vol_avg <= 0:
        return None
    rvol = float(vol.iloc[-1]) / (vol_avg * session_fraction) if session_fraction > 0 else 1.0
    if rvol < 0.75:
        return None

    ema9 = float(ema(close, 9).iloc[-1])
    ema20 = float(ema(close, 20).iloc[-1])
    p_close = float(close.iloc[-1])
    if p_close < ema20 * 0.985:
        return None

    atr_val = float(atr(df, 14).iloc[-1])
    entry = p_close
    swing_low = float(df["Low"].iloc[-3:].min())
    stop = round(max(swing_low * 0.996, entry - 1.2 * atr_val), 2)
    risk = entry - stop
    if risk <= 0 or (risk / entry) > 0.05:
        stop = round(entry * 0.985, 2)
        risk = entry - stop

    target_1 = round(entry + 1.8 * risk, 2)
    target_2 = round(entry + 2.8 * risk, 2)

    confidence = 76
    if rvol >= 1.2:
        confidence += 8
    if 55 <= rsi_now <= 68:
        confidence += 6
    if ema9 >= ema20:
        confidence += 4

    return {
        "strategy": "momentum_ignition",
        "strategy_title": "Momentum Ignition (Triple Confirm)",
        "signal": "BUY",
        "direction": "BULLISH",
        "entry_price": round(entry, 2),
        "stop_loss": stop,
        "target_1": target_1,
        "target_2": target_2,
        "risk_reward": round(1.8, 2),
        "risk_per_share": round(risk, 2),
        "risk_pct": round((risk / entry) * 100, 2),
        "confidence_score": min(confidence, 95),
        "reasons": [
            f"RSI in prime momentum acceleration band at {rsi_now:.1f} (50-76)",
            f"MACD histogram positive/rising at {hist_now:+.2f} — upward acceleration",
            f"Relative volume (RVOL) at {rvol:.2f}x expected pace",
            f"Price trading constructively above moving average trendline (₹{ema20:.1f})",
        ],
    }


def _mean_reversion_snap(df: pd.DataFrame, session_fraction: float = 1.0) -> Optional[Dict[str, Any]]:
    """
    Strategy 4: Mean Reversion Bounce

    Professional Concept:
    Overextended pullback near lower Bollinger Band forming a bounce
    with oversold RSI snapping back toward the 20-day moving average.
    """
    if len(df) < 55:
        return None

    close = df["Close"]
    opn = df["Open"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    _, mid, lower, _ = bollinger_bands(close, 20, 2.0)
    p_close = float(close.iloc[-1])
    p_low = float(low.iloc[-1])
    p_open = float(opn.iloc[-1])
    cur_lower = float(lower.iloc[-1])
    cur_mid = float(mid.iloc[-1])

    rsi_series = rsi(close, 14)
    rsi_now = float(rsi_series.iloc[-1])
    rsi_prev = float(rsi_series.iloc[-2])

    near_lower_band = (p_low <= cur_lower * 1.025) or (float(low.iloc[-2]) <= float(lower.iloc[-2]) * 1.025)
    oversold_rsi = rsi_now <= 44 or rsi_prev <= 40
    if not (near_lower_band or oversold_rsi):
        return None

    # Reversal confirmation: close above open or close above intraday midpoint
    is_reversal = (p_close >= p_open) or ((p_close - p_low) >= 0.40 * (float(high.iloc[-1]) - p_low))
    if not is_reversal:
        return None

    vol_avg = float(sma(vol, 20).iloc[-1])
    if vol_avg <= 0:
        return None
    rvol = float(vol.iloc[-1]) / (vol_avg * session_fraction) if session_fraction > 0 else 1.0
    if rvol < 0.60:
        return None

    atr_val = float(atr(df, 14).iloc[-1])
    entry = p_close
    swing_low = min(p_low, float(low.iloc[-3:].min()))
    stop = round(min(swing_low * 0.996, entry - 1.1 * atr_val), 2)
    risk = entry - stop
    if risk <= 0 or (risk / entry) > 0.05:
        stop = round(entry * 0.985, 2)
        risk = entry - stop

    target_1 = round(max(cur_mid, entry + 1.5 * risk), 2)
    target_2 = round(entry + 2.5 * risk, 2)
    rr = round((target_1 - entry) / risk, 2) if risk > 0 else 1.5

    confidence = 72
    if rsi_prev <= 36:
        confidence += 8
    if p_close > p_open:
        confidence += 6
    if rvol >= 0.95:
        confidence += 5

    return {
        "strategy": "mean_reversion",
        "strategy_title": "Mean Reversion Bounce",
        "signal": "BUY",
        "direction": "BULLISH",
        "entry_price": round(entry, 2),
        "stop_loss": stop,
        "target_1": target_1,
        "target_2": target_2,
        "risk_reward": max(rr, 1.5),
        "risk_per_share": round(risk, 2),
        "risk_pct": round((risk / entry) * 100, 2),
        "confidence_score": min(confidence, 92),
        "reasons": [
            f"Price tested lower Bollinger Band (₹{cur_lower:.1f}) support zone",
            f"RSI recovering from oversold reading ({rsi_now:.1f})",
            f"Intraday bounce confirmation: price holding above candle low",
            f"Mean reversion target: 20-SMA at ₹{cur_mid:.1f}",
        ],
    }


def _relative_strength_surge(
    df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None,
    session_fraction: float = 1.0,
) -> Optional[Dict[str, Any]]:
    """
    Strategy 5: Relative Strength Surge

    Professional Concept:
    Stock outperforming NIFTY 50 benchmark (Mansfield RS > 0 and healthy momentum)
    representing smart-money alpha flow.
    """
    if len(df) < 55 or benchmark_df is None or len(benchmark_df) < 55:
        return None

    close = df["Close"]
    vol = df["Volume"]

    rs = relative_strength(close, benchmark_df["Close"], lookback=63)
    rs_now = float(rs.iloc[-1])
    rs_5ago = float(rs.iloc[-5]) if len(rs) >= 5 else rs_now

    if rs_now < 0.5:
        return None
    if rs_now < rs_5ago - 1.2:
        return None

    vol_avg = float(sma(vol, 20).iloc[-1])
    if vol_avg <= 0:
        return None
    rvol = float(vol.iloc[-1]) / (vol_avg * session_fraction) if session_fraction > 0 else 1.0
    if rvol < 0.70:
        return None

    ema20_val = float(ema(close, 20).iloc[-1])
    p_close = float(close.iloc[-1])
    if p_close < ema20_val * 0.985:
        return None

    rsi_val = float(rsi(close, 14).iloc[-1])
    if rsi_val < 48 or rsi_val > 78:
        return None

    atr_val = float(atr(df, 14).iloc[-1])
    entry = p_close
    swing_low = float(df["Low"].iloc[-3:].min())
    stop = round(max(swing_low * 0.996, entry - 1.25 * atr_val), 2)
    risk = entry - stop
    if risk <= 0 or (risk / entry) > 0.05:
        stop = round(entry * 0.985, 2)
        risk = entry - stop

    target_1 = round(entry + 1.8 * risk, 2)
    target_2 = round(entry + 2.8 * risk, 2)

    confidence = 75
    if rs_now >= 4.0:
        confidence += 8
    if rs_now >= rs_5ago:
        confidence += 5
    if rvol >= 1.1:
        confidence += 5

    return {
        "strategy": "rs_surge",
        "strategy_title": "Relative Strength Surge",
        "signal": "BUY",
        "direction": "BULLISH",
        "entry_price": round(entry, 2),
        "stop_loss": stop,
        "target_1": target_1,
        "target_2": target_2,
        "risk_reward": round(1.8, 2),
        "risk_per_share": round(risk, 2),
        "risk_pct": round((risk / entry) * 100, 2),
        "confidence_score": min(confidence, 94),
        "reasons": [
            f"Mansfield Relative Strength vs NIFTY positive at {rs_now:+.1f}%",
            f"Alpha momentum sustained (prior 5-day RS: {rs_5ago:+.1f}%)",
            f"RVOL at {rvol:.2f}x expected pace",
            f"Price above 20-EMA trend support (₹{ema20_val:.1f})",
        ],
    }


INTRADAY_STRATEGIES = [
    ("vwap_opening_drive", _vwap_opening_drive, False),
    ("orb_prebreakout", _orb_prebreakout, False),
    ("momentum_ignition", _momentum_ignition, False),
    ("mean_reversion", _mean_reversion_snap, False),
    ("rs_surge", _relative_strength_surge, True),
]


def _compute_composite_score(signal: Dict[str, Any]) -> float:
    conf = signal.get("confidence_score", 70)
    rr = signal.get("risk_reward", 1.5)
    risk_pct = signal.get("risk_pct", 3.0)
    risk_factor = max(0, 100 - risk_pct * 15)
    return conf * 0.55 + min(rr * 12, 25) + risk_factor * 0.2


def _scan_symbol_intraday(
    symbol: str,
    benchmark_df: Optional[pd.DataFrame],
    session_fraction: float,
) -> List[Dict[str, Any]]:
    df = fetch_ohlcv(symbol, period="6mo")
    if len(df) < 55:
        return []

    cur_price = float(df["Close"].iloc[-1])
    prev_price = float(df["Close"].iloc[-2])
    change_pct = round((cur_price - prev_price) / prev_price * 100, 2)

    results: List[Dict[str, Any]] = []
    for strat_key, strat_fn, needs_bench in INTRADAY_STRATEGIES:
        try:
            if needs_bench:
                signal = strat_fn(df, benchmark_df, session_fraction)
            else:
                signal = strat_fn(df, session_fraction)
        except Exception:
            logger.debug("Intraday strategy %s failed for %s", strat_key, symbol, exc_info=True)
            continue

        if signal:
            signal["symbol"] = symbol.replace(".NS", "")
            signal["raw_symbol"] = symbol
            signal["current_price"] = cur_price
            signal["change_pct"] = change_pct
            signal["signal_date"] = df.index[-1].strftime("%Y-%m-%d")
            signal["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            signal["composite_score"] = round(_compute_composite_score(signal), 1)
            results.append(signal)

    return results


_intraday_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_intraday_cache_lock = threading.Lock()


def run_intraday_screener(
    symbols: Optional[List[str]] = None,
    strategy_filter: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    scan_symbols = list(dict.fromkeys(symbols or DEFAULT_UNIVERSE))
    cache_key = f"{','.join(scan_symbols)}|{strategy_filter or 'all'}"

    with _intraday_cache_lock:
        now = time.time()
        cached = _intraday_cache.get(cache_key)
        if not force_refresh and cached and now - cached[0] < 180:
            result = deepcopy(cached[1])
            result["cached"] = True
            return result

    try:
        benchmark_df = fetch_benchmark(period="6mo")
    except Exception:
        benchmark_df = None

    session_fraction = _get_session_fraction()
    all_signals: List[Dict[str, Any]] = []
    failures: List[Dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_scan_symbol_intraday, sym, benchmark_df, session_fraction): sym
            for sym in scan_symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                signals = future.result()
            except Exception as exc:
                logger.warning("Intraday scan failed for %s: %s", symbol, exc)
                failures.append({"symbol": symbol.replace(".NS", ""), "reason": str(exc)[:160]})
                continue

            for signal in signals:
                if strategy_filter and signal["strategy"] != strategy_filter:
                    continue
                all_signals.append(signal)

    # Pick the best signal per symbol for primary list
    best_per_symbol: Dict[str, Dict[str, Any]] = {}
    for signal in all_signals:
        sym = signal["symbol"]
        if sym not in best_per_symbol or signal["composite_score"] > best_per_symbol[sym]["composite_score"]:
            best_per_symbol[sym] = signal

    unique_signals = sorted(
        best_per_symbol.values(),
        key=lambda s: s.get("composite_score", 0),
        reverse=True,
    )

    succeeded = len(scan_symbols) - len(failures)
    if succeeded == 0 and scan_symbols:
        raise MarketDataUnavailable("Market data is unavailable for all scanned symbols.")

    strat_counts: Dict[str, int] = {}
    for s in unique_signals:
        strat_counts[s["strategy"]] = strat_counts.get(s["strategy"], 0) + 1

    bullish_count = sum(1 for s in unique_signals if s.get("direction") == "BULLISH")
    bearish_count = sum(1 for s in unique_signals if s.get("direction") == "BEARISH")

    result = {
        "count": len(unique_signals),
        "signals": unique_signals,
        "all_signals": all_signals,
        "cached": False,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data_status": "complete" if not failures else "partial",
        "scan_summary": {
            "requested": len(scan_symbols),
            "succeeded": succeeded,
            "failed": len(failures),
            "total_setups": len(unique_signals),
            "bullish": bullish_count,
            "bearish": bearish_count,
        },
        "strategy_distribution": strat_counts,
        "errors": failures[:10],
        "strategies_available": [
            {"id": "vwap_opening_drive", "title": "Gap + Volume Opening Drive", "description": "High relative volume with directional gap or session drive"},
            {"id": "orb_prebreakout", "title": "Breakout Setup (Tight Squeeze)", "description": "Consolidation compression coiled near moving averages"},
            {"id": "momentum_ignition", "title": "Momentum Ignition (Triple Confirm)", "description": "RSI momentum + MACD bullish acceleration + Volume surge"},
            {"id": "mean_reversion", "title": "Mean Reversion Bounce", "description": "Oversold bounce from Bollinger lower band support"},
            {"id": "rs_surge", "title": "Relative Strength Surge", "description": "Strong alpha outperformance against NIFTY 50 benchmark"},
        ],
        "disclaimer": "Intraday setups based on quantitative technical momentum analysis. Not financial advice. No orders are placed. Confirm risk and live market execution.",
    }

    with _intraday_cache_lock:
        _intraday_cache[cache_key] = (time.time(), deepcopy(result))
        if len(_intraday_cache) > 16:
            oldest = sorted(_intraday_cache, key=lambda k: _intraday_cache[k][0])[:8]
            for k in oldest:
                _intraday_cache.pop(k, None)

    return result
