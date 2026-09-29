"""
Trend Surfer: trend-following setup that needs seven filters to agree on the same day.

Filters (all seven must pass):
1. Weekly close above the 20-week EMA
2. Daily close above both the 20 EMA and the 50 EMA
3. Supertrend(10, 3) is green
4. RSI(14) between 45 and 70
5. MACD crossed above its signal line within the last 3 sessions
6. Volume at least 1.2x the 20-day average
7. Bullish candle (close above open)

Entry: today's close. Stop: entry - 1.5 x ATR(14). Target: entry + 3 x ATR(14), which is
always a 1:2 risk-reward. Most filters come from the same price series, so they overlap
heavily; use diagnostic.py to see how much each one actually removes.
"""

import pandas as pd

from core.indicators import ema, wilder_rsi, average_true_range, macd, supertrend_is_green


NAME = "Trend Surfer (7-Filter)"

EMA_FAST_PERIOD = 20
EMA_SLOW_PERIOD = 50
EMA_WEEKLY_PERIOD = 20
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0
ATR_PERIOD = 14
RSI_PERIOD = 14
RSI_MIN = 45
RSI_MAX = 70
MACD_CROSSOVER_WINDOW_DAYS = 3
VOLUME_LOOKBACK_DAYS = 20
VOLUME_MULTIPLIER = 1.2
ATR_STOPLOSS_MULTIPLIER = 1.5
ATR_TARGET_MULTIPLIER = 3.0
MIN_ROWS = EMA_SLOW_PERIOD + SUPERTREND_PERIOD + ATR_PERIOD + 10


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["EMA20"] = ema(df["Close"], EMA_FAST_PERIOD)
    df["EMA50"] = ema(df["Close"], EMA_SLOW_PERIOD)
    df["RSI"] = wilder_rsi(df["Close"], RSI_PERIOD)
    df["ATR"] = average_true_range(df, ATR_PERIOD)

    df["MACD_Line"], df["MACD_Signal"], df["MACD_Hist"] = macd(df["Close"])
    df["AvgVolume20"] = df["Volume"].rolling(VOLUME_LOOKBACK_DAYS).mean()
    df["SupertrendGreen"] = supertrend_is_green(df, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER)
    return df


def _weekly_uptrend(df):
    weekly_close = df["Close"].resample("W").last().dropna()
    # Too little history to judge: let the daily filters decide.
    if len(weekly_close) < EMA_WEEKLY_PERIOD + 2:
        return True
    return bool(weekly_close.iloc[-1] > ema(weekly_close, EMA_WEEKLY_PERIOD).iloc[-1])


def _macd_crossed_recently(df):
    for sessions_ago in range(1, MACD_CROSSOVER_WINDOW_DAYS + 1):
        current = df.iloc[-sessions_ago]
        previous = df.iloc[-sessions_ago - 1]
        if previous["MACD_Line"] < previous["MACD_Signal"] and current["MACD_Line"] >= current["MACD_Signal"]:
            return True
    return False


def _has_volume_surge(today):
    average_volume = today["AvgVolume20"]
    return bool(pd.notna(average_volume) and average_volume > 0
                and today["Volume"] >= average_volume * VOLUME_MULTIPLIER)


def _filters(df):
    today = df.iloc[-1]
    return [
        ("Weekly close above 20-week EMA", lambda: _weekly_uptrend(df)),
        ("Close above EMA20 and EMA50", lambda: bool(today["Close"] > today["EMA20"] and today["Close"] > today["EMA50"])),
        ("Supertrend green", lambda: bool(today["SupertrendGreen"])),
        ("RSI between 45 and 70", lambda: bool(RSI_MIN <= today["RSI"] <= RSI_MAX)),
        ("MACD crossover in last 3 sessions", lambda: _macd_crossed_recently(df)),
        ("Volume at least 1.2x average", lambda: _has_volume_surge(today)),
        ("Bullish candle", lambda: bool(today["Close"] > today["Open"])),
    ]


def evaluate_filters(price_data):
    if price_data is None or len(price_data) < MIN_ROWS:
        return None
    df = _prepare_indicators(price_data)
    return {name: check() for name, check in _filters(df)}


def generate_signal(price_data):
    if price_data is None or len(price_data) < MIN_ROWS:
        return None
    df = _prepare_indicators(price_data)
    if not all(check() for _, check in _filters(df)):
        return None

    today = df.iloc[-1]
    atr = float(today["ATR"])
    entry_price = round(float(today["Close"]), 2)
    stoploss_price = round(entry_price - ATR_STOPLOSS_MULTIPLIER * atr, 2)
    target_price = round(entry_price + ATR_TARGET_MULTIPLIER * atr, 2)
    risk_per_share = round(entry_price - stoploss_price, 2)
    if risk_per_share <= 0:
        return None

    return {
        "Entry": entry_price,
        "StopLoss": stoploss_price,
        "Target": target_price,
        "Risk_Rs": risk_per_share,
        "Reward_Rs": round(target_price - entry_price, 2),
        "ATR": round(atr, 2),
        "RSI": round(float(today["RSI"]), 2),
        "EMA20": round(float(today["EMA20"]), 2),
        "EMA50": round(float(today["EMA50"]), 2),
        "MACD_H": round(float(today["MACD_Hist"]), 4),
        "MACD_Line": round(float(today["MACD_Line"]), 4),
        "Volume": int(today["Volume"]),
        "AvgVol20": int(today["AvgVolume20"]),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    }
