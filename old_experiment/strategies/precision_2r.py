"""
Precision 2R V2 - Pullback Breakout Strategy

Concept:
    Strong trend -> Controlled pullback -> Volume contraction -> Support near EMA20/50
    -> Momentum recovery -> High-volume breakout -> Fixed 1:2 Risk/Reward
"""

import pandas as pd
from core.utils import round_tick, remove_forming_candle, clean_ohlcv
from core.indicators import ema, wilder_rsi, average_true_range, adx

NAME = "Precision 2R V2"

# Parameters
EMA_FAST = 20
EMA_MIDDLE = 50
EMA_SLOW = 200
EMA_SLOPE_LOOKBACK = 10
MIN_WARMUP_BARS = 400

PULLBACK_LOOKBACK = 8
EMA20_MAX_DISTANCE_PCT = 2.5
EMA50_MAX_DISTANCE_PCT = 3.5
PULLBACK_VOLUME_MAX_RATIO = 0.95

RSI_PERIOD = 14
RSI_MIN = 50
RSI_MAX = 68

ADX_PERIOD = 14
ADX_MIN = 20

VOLUME_PERIOD = 20
BREAKOUT_VOLUME_MULTIPLIER = 1.5

ATR_PERIOD = 14
ATR_BUFFER_MULTIPLIER = 0.20
MAX_RISK_PCT = 5.0
RISK_REWARD = 2.0


def generate_signal(price_data):
    data = clean_ohlcv(price_data)
    if data is None or data.empty:
        return None

    data = remove_forming_candle(data)
    if data is None or len(data) < MIN_WARMUP_BARS:
        return None

    # Calculate indicators
    data["EMA20"] = ema(data["Close"], EMA_FAST)
    data["EMA50"] = ema(data["Close"], EMA_MIDDLE)
    data["EMA200"] = ema(data["Close"], EMA_SLOW)
    data["RSI"] = wilder_rsi(data["Close"], RSI_PERIOD)
    data["ATR"] = average_true_range(data, ATR_PERIOD)
    data["ADX"], data["+DI"], data["-DI"] = adx(data, ADX_PERIOD)
    data["AvgVolume20"] = data["Volume"].shift(1).rolling(VOLUME_PERIOD, min_periods=VOLUME_PERIOD).mean()

    today = data.iloc[-1]
    yesterday = data.iloc[-2]

    # Null checks
    required_values = [
        today["Close"], today["Volume"], today["EMA20"], today["EMA50"], today["EMA200"],
        today["RSI"], today["ATR"], today["ADX"], today["+DI"], today["-DI"], today["AvgVolume20"],
        yesterday["High"], yesterday["RSI"]
    ]
    if any(pd.isna(v) for v in required_values):
        return None

    # Filter 1: Strong Primary Trend
    if not (today["EMA20"] > today["EMA50"] > today["EMA200"]):
        return None

    # Filter 2: Price above EMA20
    if today["Close"] <= today["EMA20"]:
        return None

    # Filter 3: EMA200 rising
    ema200_old = data["EMA200"].iloc[-1 - EMA_SLOPE_LOOKBACK]
    if pd.isna(ema200_old) or today["EMA200"] <= ema200_old:
        return None

    # Filter 4 & 5: Controlled Pullback
    pullback = data.iloc[-(PULLBACK_LOOKBACK + 1):-1]
    if len(pullback) < PULLBACK_LOOKBACK:
        return None

    pullback_ema20 = data["EMA20"].iloc[-(PULLBACK_LOOKBACK + 1):-1]
    pullback_ema50 = data["EMA50"].iloc[-(PULLBACK_LOOKBACK + 1):-1]

    ema20_dist = ((pullback["Low"].values - pullback_ema20.values) / pullback_ema20.values) * 100
    touched_ema20 = ((ema20_dist >= -EMA20_MAX_DISTANCE_PCT) & (ema20_dist <= EMA20_MAX_DISTANCE_PCT)).any()

    ema50_dist = ((pullback["Low"].values - pullback_ema50.values) / pullback_ema50.values) * 100
    touched_ema50 = ((ema50_dist >= -EMA50_MAX_DISTANCE_PCT) & (ema50_dist <= EMA50_MAX_DISTANCE_PCT)).any()

    if not (touched_ema20 or touched_ema50):
        return None

    close_vs_ema50 = ((pullback["Close"].values - pullback_ema50.values) / pullback_ema50.values) * 100
    if (close_vs_ema50 < -EMA50_MAX_DISTANCE_PCT).any():
        return None

    # Filter 6: Volume Contraction during Pullback
    pullback_avg_vol = pullback["Volume"].mean()
    benchmark_avg = data["AvgVolume20"].iloc[-(PULLBACK_LOOKBACK + 1):-1].mean()
    if pd.isna(benchmark_avg) or benchmark_avg <= 0:
        return None

    pullback_vol_ratio = pullback_avg_vol / benchmark_avg
    if pullback_vol_ratio > PULLBACK_VOLUME_MAX_RATIO:
        return None

    # Filter 7: RSI Momentum
    if not (RSI_MIN <= today["RSI"] <= RSI_MAX) or today["RSI"] <= yesterday["RSI"]:
        return None

    # Filter 8 & 9: ADX & +DI
    if today["ADX"] < ADX_MIN or today["+DI"] <= today["-DI"]:
        return None

    # Filter 10 & 11: Breakout Candle & High Break
    if today["Close"] <= today["Open"] or today["Close"] <= yesterday["High"]:
        return None

    # Filter 12: Breakout Volume
    avg_vol = today["AvgVolume20"]
    curr_vol = today["Volume"]
    if pd.isna(avg_vol) or avg_vol <= 0 or (curr_vol / avg_vol) < BREAKOUT_VOLUME_MULTIPLIER:
        return None

    # Entry, Stop, Target
    entry = float(today["Close"])
    swing_low = float(pullback["Low"].min())
    atr_val = float(today["ATR"])

    stop_loss = swing_low - (atr_val * ATR_BUFFER_MULTIPLIER)
    if stop_loss <= 0 or stop_loss >= entry:
        return None

    risk = entry - stop_loss
    risk_pct = (risk / entry) * 100
    if risk_pct > MAX_RISK_PCT:
        return None

    target = entry + (risk * RISK_REWARD)

    entry_rnd = round_tick(entry)
    stop_rnd = round_tick(stop_loss)
    target_rnd = round_tick(target)
    if not entry_rnd or not stop_rnd or not target_rnd:
        return None

    risk_final = round(entry_rnd - stop_rnd, 2)
    reward_final = round(target_rnd - entry_rnd, 2)
    if risk_final <= 0 or reward_final <= 0 or (reward_final / risk_final) < 1.95:
        return None

    signal_date = data.index[-1]
    date_val = signal_date.strftime("%Y-%m-%d") if hasattr(signal_date, "strftime") else str(signal_date)

    return {
        "Date": date_val,
        "Entry": entry_rnd,
        "StopLoss": stop_rnd,
        "Target": target_rnd,
        "Risk_Rs": risk_final,
        "Reward_Rs": reward_final,
        "EMA20": round(float(today["EMA20"]), 2),
        "EMA50": round(float(today["EMA50"]), 2),
        "EMA200": round(float(today["EMA200"]), 2),
        "RSI14": round(float(today["RSI"]), 2),
        "ADX14": round(float(today["ADX"]), 2),
        "ATR14": round(float(today["ATR"]), 2),
        "VolumeRatio": round(float(curr_vol / avg_vol), 2),
    }