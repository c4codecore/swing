"""
Volatility Squeeze Breakout Strategy

Concept:
    Volatility contraction -> Strong higher-timeframe trend -> Price breaks recent resistance
    -> Volume expansion confirms breakout -> Momentum confirmation -> ATR Stop -> Fixed 1:2 R:R
"""

import pandas as pd
from core.utils import round_tick, remove_forming_candle, clean_ohlcv
from core.indicators import ema, wilder_rsi, average_true_range, bollinger_bands

NAME = "Volatility Squeeze Breakout"

# Parameters
EMA_FAST = 50
EMA_SLOW = 200
EMA_SLOPE_LOOKBACK = 20
BREAKOUT_LOOKBACK = 20

BB_PERIOD = 20
BB_STD = 2.0
SQUEEZE_LOOKBACK = 120
SQUEEZE_PERCENTILE = 30

VOLUME_LOOKBACK = 20
VOLUME_MULTIPLIER = 1.5

RSI_PERIOD = 14
RSI_MIN = 55
RSI_MAX = 72

ATR_PERIOD = 14
RISK_REWARD_RATIO = 2.0
MAX_STOP_DISTANCE_PCT = 5.5
MIN_STOP_DISTANCE_PCT = 1.0
MIN_ROWS = 260


def generate_signal(price_data):
    df = clean_ohlcv(price_data)
    if df is None or df.empty:
        return None

    df = remove_forming_candle(df)
    if df is None or len(df) < MIN_ROWS:
        return None

    # Calculate indicators
    df["EMA50"] = ema(df["Close"], EMA_FAST)
    df["EMA200"] = ema(df["Close"], EMA_SLOW)
    df["RSI"] = wilder_rsi(df["Close"], RSI_PERIOD)
    df["ATR"] = average_true_range(df, ATR_PERIOD)

    bb_upper, bb_middle, bb_lower = bollinger_bands(df["Close"], BB_PERIOD, BB_STD)
    df["BBWidth"] = ((bb_upper - bb_lower) / bb_middle.replace(0, pd.NA)) * 100
    df["Resistance"] = df["High"].rolling(BREAKOUT_LOOKBACK).max().shift(1)
    df["AvgVolume"] = df["Volume"].rolling(VOLUME_LOOKBACK).mean().shift(1)
    df["SqueezeThreshold"] = df["BBWidth"].rolling(SQUEEZE_LOOKBACK).quantile(SQUEEZE_PERCENTILE / 100).shift(1)

    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    required_values = [
        today["EMA50"], today["EMA200"], today["RSI"], today["ATR"],
        today["Resistance"], today["AvgVolume"], today["BBWidth"], today["SqueezeThreshold"]
    ]
    if any(pd.isna(v) for v in required_values):
        return None

    # Filter 1: Strong trend
    ema50, ema200 = float(today["EMA50"]), float(today["EMA200"])
    if ema50 <= ema200:
        return None

    # Filter 2: EMA200 rising
    ema200_prev = float(df["EMA200"].iloc[-1 - EMA_SLOPE_LOOKBACK])
    if ema200 <= ema200_prev:
        return None

    # Filter 3: Price above EMA50
    close_price = float(today["Close"])
    if close_price <= ema50:
        return None

    # Filter 4: Volatility squeeze
    if float(today["BBWidth"]) > float(today["SqueezeThreshold"]):
        return None

    # Filter 5: Breakout above resistance
    resistance = float(today["Resistance"])
    if close_price <= resistance:
        return None

    # Filter 6: Extension filter
    if ((close_price - resistance) / resistance) * 100 > 5.0:
        return None

    # Filter 7: Volume expansion
    curr_vol = float(today["Volume"])
    avg_vol = float(today["AvgVolume"])
    if avg_vol <= 0 or curr_vol < (avg_vol * VOLUME_MULTIPLIER):
        return None

    # Filter 8: RSI momentum
    if not (RSI_MIN <= float(today["RSI"]) <= RSI_MAX):
        return None

    # Filter 9: Strong bullish candle
    c_high, c_low, c_open = float(today["High"]), float(today["Low"]), float(today["Open"])
    c_range = c_high - c_low
    if c_range <= 0 or ((close_price - c_low) / c_range) < 0.65 or close_price <= c_open:
        return None

    # Filter 10: Previous candle not already breakout
    prev_resistance = df["High"].iloc[:-1].tail(BREAKOUT_LOOKBACK).max()
    if float(yesterday["Close"]) > prev_resistance:
        return None

    # Filter 11: ATR sanity check
    atr = float(today["ATR"])
    atr_pct = (atr / close_price) * 100
    if atr_pct < 1.0 or atr_pct > 6.0:
        return None

    # Entry, Stop, Target
    recent_swing_low = float(df["Low"].iloc[:-1].tail(10).min())
    stoploss = recent_swing_low - (0.25 * atr)
    if stoploss >= close_price or stoploss <= 0:
        return None

    risk = close_price - stoploss
    risk_pct = (risk / close_price) * 100
    if risk_pct > MAX_STOP_DISTANCE_PCT or risk_pct < MIN_STOP_DISTANCE_PCT:
        return None

    target = close_price + (risk * RISK_REWARD_RATIO)

    entry_rnd = round_tick(close_price)
    stop_rnd = round_tick(stoploss)
    target_rnd = round_tick(target)
    if not entry_rnd or not stop_rnd or not target_rnd:
        return None

    final_risk = round(entry_rnd - stop_rnd, 2)
    final_reward = round(target_rnd - entry_rnd, 2)
    if final_risk <= 0 or final_reward <= 0:
        return None

    signal_date = df.index[-1]
    date_val = signal_date.strftime("%Y-%m-%d") if hasattr(signal_date, "strftime") else str(signal_date)

    return {
        "Date": date_val,
        "Entry": entry_rnd,
        "StopLoss": stop_rnd,
        "Target": target_rnd,
        "Risk_Rs": final_risk,
        "Reward_Rs": final_reward,
        "EMA50": round(ema50, 2),
        "EMA200": round(ema200, 2),
        "ResistanceLevel": round(resistance, 2),
        "BBWidth": round(float(today["BBWidth"]), 2),
        "SqueezeThreshold": round(float(today["SqueezeThreshold"]), 2),
        "Volume": int(curr_vol),
        "AvgVolume": round(avg_vol, 2),
        "RSI": round(float(today["RSI"]), 2),
        "ATR": round(atr, 2),
    }