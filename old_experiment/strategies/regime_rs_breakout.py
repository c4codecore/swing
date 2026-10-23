"""Regime + Relative Strength Breakout — Balanced Candidate.

Practical first-backtest version. Signal uses only information through the
signal candle; execution belongs to the next-day-open backtest engine.
"""
import numpy as np
import pandas as pd
from core.utils import round_tick, clean_ohlcv, normalize_date
from core.indicators import ema, wilder_rsi, average_true_range
from core.ohlcv_data import fetch_price_history

NAME = "Regime RS Breakout"
DATA_PERIOD = "3y"
RISK_REWARD_RATIO = 2.0
MIN_PLANNED_RR = 1.90
NIFTY_SYMBOL = "^NSEI"
NIFTY_PERIOD = "5y"

EMA_FAST, EMA_MID, EMA_SLOW = 20, 50, 200
EMA200_RISE_LOOKBACK = 20
MOMENTUM_20D_MIN = 0.02
MOMENTUM_60D_MIN = 0.05
RSI_PERIOD, RSI_MIN, RSI_MAX = 14, 50, 75
RS_20D_MIN = 0.00
RS_60D_MIN = 0.00
CONSOLIDATION_DAYS = 10
MAX_CONSOLIDATION_RANGE = 0.14
MAX_BREAKOUT_EXTENSION_PCT = 0.07
MAX_BREAKOUT_RANGE_ATR = 2.5
VOLUME_LOOKBACK = 20
BREAKOUT_VOLUME_MULTIPLIER = 1.20
ATR_PERIOD = 14
STOP_LOOKBACK = 10
STOP_ATR_BUFFER = 0.20
MIN_STOP_PCT, MAX_STOP_PCT = 0.01, 0.08
MAX_NEXT_OPEN_GAP_PCT = 0.03
_NIFTY_CACHE = None


def _fetch_nifty():
    global _NIFTY_CACHE
    if _NIFTY_CACHE is not None:
        return _NIFTY_CACHE
    nifty = fetch_price_history(NIFTY_SYMBOL, period=NIFTY_PERIOD)
    if nifty is None or len(nifty) < 250:
        return None
    _NIFTY_CACHE = nifty
    return _NIFTY_CACHE


def _nifty_snapshot(signal_date):
    nifty = _fetch_nifty()
    if nifty is None:
        return None
    return nifty.loc[nifty.index <= normalize_date(signal_date)]


def _market_regime(signal_date):
    nifty = _nifty_snapshot(signal_date)
    if nifty is None or len(nifty) < 60:
        return None
    c = nifty["Close"]
    e20, e50 = ema(c, 20), ema(c, 50)
    close, ema20_val, ema50_val = float(c.iloc[-1]), float(e20.iloc[-1]), float(e50.iloc[-1])
    old50 = float(ema50_val if len(e50) < 22 else e50.iloc[-21])
    if close > ema50_val and ema20_val > ema50_val and ema50_val > old50:
        return "Bullish"
    if close < ema50_val and ema20_val < ema50_val and ema50_val < old50:
        return "Bearish"
    return "Neutral"


def _aligned_relative_strength(stock):
    nifty = _nifty_snapshot(stock.index[-1])
    if nifty is None:
        return None
    aligned = pd.concat([stock["Close"].rename("Stock"),
                         nifty["Close"].rename("Nifty")], axis=1,
                        join="inner").dropna()
    if len(aligned) < 61:
        return None
    s, n = aligned["Stock"], aligned["Nifty"]
    sr20, nr20 = float(s.iloc[-1] / s.iloc[-21] - 1), float(n.iloc[-1] / n.iloc[-21] - 1)
    sr60, nr60 = float(s.iloc[-1] / s.iloc[-61] - 1), float(n.iloc[-1] / n.iloc[-61] - 1)
    return {
        "StockReturn20D": sr20, "NiftyReturn20D": nr20,
        "RelativeStrength20D": sr20 - nr20,
        "StockReturn60D": sr60, "NiftyReturn60D": nr60,
        "RelativeStrength60D": sr60 - nr60,
        "RSRatio": float(s.iloc[-1] / n.iloc[-1]),
    }


def generate_signal(price_data):
    """Generate a long-only signal using only completed signal-candle data."""
    min_rows = EMA_SLOW + 70
    if price_data is None or len(price_data) < min_rows:
        return None
    df = clean_ohlcv(price_data)
    if df is None or len(df) < min_rows:
        return None

    df["EMA20"] = ema(df["Close"], EMA_FAST)
    df["EMA50"] = ema(df["Close"], EMA_MID)
    df["EMA200"] = ema(df["Close"], EMA_SLOW)
    df["ATR"] = average_true_range(df, ATR_PERIOD)
    df["RSI"] = wilder_rsi(df["Close"], RSI_PERIOD)
    df["AvgVolume20Prev"] = df["Volume"].rolling(VOLUME_LOOKBACK).mean().shift(1)
    t, y = df.iloc[-1], df.iloc[-2]

    regime = _market_regime(df.index[-1])
    if regime is None or regime == "Bearish":
        return None

    if not (t["Close"] > t["EMA20"] > t["EMA50"] > t["EMA200"]):
        return None
    if float(df["EMA200"].iloc[-1]) <= float(df["EMA200"].iloc[-1 - EMA200_RISE_LOOKBACK]):
        return None

    stock20 = float(df["Close"].iloc[-1] / df["Close"].iloc[-21] - 1)
    stock60 = float(df["Close"].iloc[-1] / df["Close"].iloc[-61] - 1)
    if stock20 < MOMENTUM_20D_MIN or stock60 < MOMENTUM_60D_MIN:
        return None

    rs = _aligned_relative_strength(df)
    if rs is None or rs["RelativeStrength20D"] < RS_20D_MIN or rs["RelativeStrength60D"] < RS_60D_MIN:
        return None

    base = df.iloc[-(CONSOLIDATION_DAYS + 1):-1]
    if len(base) != CONSOLIDATION_DAYS:
        return None
    base_high, base_low = float(base["High"].max()), float(base["Low"].min())
    if base_low <= 0:
        return None
    base_range = (base_high - base_low) / base_low
    if base_range > MAX_CONSOLIDATION_RANGE:
        return None

    atr_now = float(t["ATR"])
    if not np.isfinite(atr_now) or atr_now <= 0:
        return None
    prev_atr = float(df["ATR"].iloc[-6:-1].mean())
    atr_ratio = atr_now / prev_atr if prev_atr > 0 else np.nan
    base_vol = float(base["Volume"].mean())
    recent_vol = float(base["Volume"].tail(5).mean())
    base_vol_ratio = recent_vol / base_vol if base_vol > 0 else np.nan

    if float(t["Close"]) <= base_high:
        return None
    breakout_extension = float(t["Close"] / base_high - 1)
    if breakout_extension > MAX_BREAKOUT_EXTENSION_PCT:
        return None
    if float(t["Close"]) <= float(y["High"]):
        return None

    avg_vol = float(t["AvgVolume20Prev"])
    if not np.isfinite(avg_vol) or avg_vol <= 0:
        return None
    volume_ratio = float(t["Volume"] / avg_vol)
    if volume_ratio < BREAKOUT_VOLUME_MULTIPLIER:
        return None

    rsi = float(t["RSI"])
    if not (RSI_MIN <= rsi <= RSI_MAX):
        return None
    day_range = float(t["High"] - t["Low"])
    if day_range <= 0 or float((t["Close"] - t["Low"]) / day_range) < 0.50:
        return None
    if float(t["Close"]) <= float(t["Open"]):
        return None
    if day_range > atr_now * MAX_BREAKOUT_RANGE_ATR:
        return None

    entry = round_tick(t["Close"])
    swing_low = float(df["Low"].iloc[-STOP_LOOKBACK:].min())
    sl = round_tick(swing_low - STOP_ATR_BUFFER * atr_now)
    risk = entry - sl
    if risk <= 0:
        return None
    stop_pct = risk / entry
    if not (MIN_STOP_PCT <= stop_pct <= MAX_STOP_PCT):
        return None

    target = round_tick(entry + risk * RISK_REWARD_RATIO)
    reward = target - entry
    if reward <= 0:
        return None
    planned_rr = reward / risk
    if planned_rr < MIN_PLANNED_RR:
        return None

    return {
        "Entry": entry, "StopLoss": sl, "Target": target,
        "Risk_Rs": round(risk, 2), "Reward_Rs": round(reward, 2),
        "PlannedRR": round(planned_rr, 2), "MarketRegime": regime,
        "StockReturn20D": round(rs["StockReturn20D"] * 100, 2),
        "NiftyReturn20D": round(rs["NiftyReturn20D"] * 100, 2),
        "RelativeStrength20D": round(rs["RelativeStrength20D"] * 100, 2),
        "StockReturn60D": round(rs["StockReturn60D"] * 100, 2),
        "NiftyReturn60D": round(rs["NiftyReturn60D"] * 100, 2),
        "RelativeStrength60D": round(rs["RelativeStrength60D"] * 100, 2),
        "RSRatio": round(rs["RSRatio"], 6),
        "EMA20": round(float(t["EMA20"]), 2),
        "EMA50": round(float(t["EMA50"]), 2),
        "EMA200": round(float(t["EMA200"]), 2),
        "ATR": round(atr_now, 2), "RSI": round(rsi, 2),
        "ConsolidationRangePct": round(base_range * 100, 2),
        "BaseVolumeRatio": round(base_vol_ratio, 2) if np.isfinite(base_vol_ratio) else None,
        "ATRvsPrevious5D": round(atr_ratio, 2) if np.isfinite(atr_ratio) else None,
        "VolumeRatio": round(volume_ratio, 2),
        "BreakoutLevel": round(base_high, 2),
        "BreakoutExtensionPct": round(breakout_extension * 100, 2),
        "StopDistancePct": round(stop_pct * 100, 2),
        "ExecutionModel": "NextDayOpen",
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    }
