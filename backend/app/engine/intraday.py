"""Read-only NIFTY intraday analysis using IIFL candles and spot quotes."""
from __future__ import annotations

from datetime import datetime, time as day_time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from app.core.indicators import atr, ema
from app.core.iifl_market_data import get_iifl_intraday_candles, get_nifty_quote

IST = ZoneInfo("Asia/Kolkata")


def analyze_intraday() -> dict[str, Any]:
    """Calculate a 15-minute opening-range breakout with VWAP trend confirmation."""
    now = datetime.now(IST)
    raw = get_iifl_intraday_candles(interval="5 minutes", lookback_days=5)
    if not raw:
        return {
            "underlying": "NIFTY 50", "strategy": "15-minute Opening Range Breakout + VWAP",
            "signal": "WAIT", "reason": "IIFL has not returned intraday candles for the recent sessions.",
            "candles_as_of": None, "is_current_session": False, "spot": None,
        }

    frame = pd.DataFrame(raw)
    if frame.shape[1] < 6:
        raise ValueError("IIFL returned an invalid candle structure.")
    frame = frame.iloc[:, :6]
    frame.columns = ["timestamp", "Open", "High", "Low", "Close", "Volume"]
    parsed = pd.to_datetime(frame["timestamp"], errors="coerce")
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(IST, ambiguous="NaT", nonexistent="shift_forward")
    else:
        parsed = parsed.dt.tz_convert(IST)
    frame.index = parsed
    frame = frame[~frame.index.isna()]
    frame = frame.drop(columns=["timestamp"])
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    if frame.empty:
        raise ValueError("IIFL returned no valid NIFTY candles.")

    session_date = frame.index[-1].date()
    session = frame[frame.index.date == session_date].between_time("09:15", "15:30")
    if session.empty:
        raise ValueError("IIFL returned no NIFTY candles inside market hours.")
    today = now.date()
    is_current_session = session_date == today and now.weekday() < 5
    try:
        quote = get_nifty_quote()
        spot = float(quote["price"])
        quote_at = quote.get("tick_at") or quote.get("received_at")
    except Exception:
        quote = None
        spot = float(session["Close"].iloc[-1])
        quote_at = None

    first_15 = session.between_time("09:15", "09:29")
    session_time_started = now.time() >= day_time(9, 30) if is_current_session else True
    if len(first_15) >= 3:
        range_high = float(first_15["High"].max())
        range_low = float(first_15["Low"].min())
    else:
        range_high = range_low = None

    close = session["Close"]
    ema9 = float(ema(close, 9).iloc[-1])
    ema20 = float(ema(close, 20).iloc[-1])
    atr14 = float(atr(session, 14).iloc[-1]) if len(session) >= 14 else None
    volume = session["Volume"].fillna(0).clip(lower=0)
    typical = (session["High"] + session["Low"] + session["Close"]) / 3
    total_volume = float(volume.sum())
    vwap = float((typical * volume).sum() / total_volume) if total_volume > 0 else None
    candle_age_minutes = (now - session.index[-1].to_pydatetime()).total_seconds() / 60
    fresh = is_current_session and (not (now.time() >= day_time(9, 15)) or candle_age_minutes <= 15)

    signal = "WAIT"
    strategy_name = "15-minute Opening Range Breakout + VWAP"
    reasons = []
    entry = stop = target = None
    if not is_current_session:
        reasons.append(f"Latest IIFL candles are from {session_date.isoformat()}; no live-session setup is active.")
    elif not session_time_started or range_high is None:
        reasons.append("Wait for the first 15 minutes to complete before using the opening-range rule.")
    elif not fresh:
        reasons.append("The latest IIFL candle is stale; wait for a fresh feed before acting.")
    elif spot > range_high and ema9 > ema20 and (vwap is None or spot > vwap):
        signal = "LONG_CALL_BIAS"
        entry = spot
        stop = max(range_low, spot - (atr14 or (range_high - range_low)))
        reasons.extend(["Spot is above the first 15-minute range high.", "EMA 9 is above EMA 20 and spot is above VWAP when volume is available."])
    elif spot < range_low and ema9 < ema20 and (vwap is None or spot < vwap):
        signal = "LONG_PUT_BIAS"
        entry = spot
        stop = min(range_high, spot + (atr14 or (range_high - range_low)))
        reasons.extend(["Spot is below the first 15-minute range low.", "EMA 9 is below EMA 20 and spot is below VWAP when volume is available."])
    else:
        pullback_tolerance = max((atr14 or 0) * 0.35, 1.0)
        last_bar = session.iloc[-1]
        bullish_pullback = vwap is not None and spot > vwap and ema9 > ema20 and abs(spot - ema9) <= pullback_tolerance and float(last_bar["Close"]) >= float(last_bar["Open"])
        bearish_pullback = vwap is not None and spot < vwap and ema9 < ema20 and abs(spot - ema9) <= pullback_tolerance and float(last_bar["Close"]) <= float(last_bar["Open"])
        if bullish_pullback:
            signal = "LONG_CALL_BIAS"
            strategy_name = "VWAP Trend Pullback"
            entry = spot
            stop = spot - (atr14 or pullback_tolerance)
            reasons.extend(["Spot is above VWAP with EMA 9 above EMA 20.", "Latest candle confirms a pullback near EMA 9."])
        elif bearish_pullback:
            signal = "LONG_PUT_BIAS"
            strategy_name = "VWAP Trend Pullback"
            entry = spot
            stop = spot + (atr14 or pullback_tolerance)
            reasons.extend(["Spot is below VWAP with EMA 9 below EMA 20.", "Latest candle confirms a pullback near EMA 9."])
        else:
            reasons.append("No confirmed opening-range break or VWAP trend pullback; avoid forcing a directional entry.")
    if entry is not None and stop is not None:
        risk = abs(entry - stop)
        target = entry + 2 * risk if signal == "LONG_CALL_BIAS" else entry - 2 * risk

    return {
        "underlying": "NIFTY 50", "strategy": strategy_name,
        "signal": signal, "spot": round(spot, 2), "quote_at": quote_at,
        "entry": round(entry, 2) if entry is not None else None,
        "stop": round(stop, 2) if stop is not None else None,
        "target_2r": round(target, 2) if target is not None else None,
        "risk_points": round(abs(entry - stop), 2) if entry is not None and stop is not None else None,
        "opening_range_high": round(range_high, 2) if range_high is not None else None,
        "opening_range_low": round(range_low, 2) if range_low is not None else None,
        "ema9": round(ema9, 2), "ema20": round(ema20, 2),
        "vwap": round(vwap, 2) if vwap is not None else None,
        "atr14": round(atr14, 2) if atr14 is not None else None,
        "candles_as_of": session.index[-1].isoformat(timespec="minutes"),
        "session_date": session_date.isoformat(), "is_current_session": is_current_session,
        "fresh": fresh, "reasons": reasons,
        "data_source": "IIFL 5-minute candles + IIFL NIFTY spot quote",
        "disclaimer": "Read-only technical setup, not a trade instruction. Confirm data, slippage, costs and risk before trading; no orders are placed.",
    }
