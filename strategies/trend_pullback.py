"""
Trend Pullback (High-Probability) Strategy - Long only, 1:2 Risk Reward

Rules:
    1. Strong uptrend: Close > EMA200, EMA20 > EMA50 > EMA200, EMA50 & EMA200 rising
    2. Trend strength: ADX(14) >= 20
    3. Real pullback: Last 5 days low touched EMA20, close held EMA50, RSI dipped <= 50
    4. Trigger candle: Bullish candle + Close > yesterday's High + Close > EMA20
    5. RSI recovery: RSI improving and 45-65
    6. Volume: >= 1.0x 20-day average
    7. Not extended: (Close - EMA20) <= 1.5 ATR
    8. Liquidity: Average daily turnover >= Rs 5 crore
    9. Stop: Pullback swing low - 0.2 ATR (0.8 - 2.0 ATR buffer)
   10. Target: 1:2 RR
"""

import pandas as pd
from core.utils import round_tick, remove_forming_candle, clean_ohlcv
from core.indicators import ema, wilder_rsi, average_true_range, adx

NAME = "Trend Pullback"
DATA_PERIOD = "3y"

# Parameters
EMA_FAST = 20
EMA_MID = 50
EMA_SLOW = 200
MIN_WARMUP_BARS = 400

ADX_PERIOD = 14
MIN_ADX = 20

PULLBACK_LOOKBACK = 5
RSI_PERIOD = 14
RSI_PULLBACK_MAX = 50
RSI_TRIGGER_MIN = 45
RSI_TRIGGER_MAX = 65

VOLUME_PERIOD = 20
VOLUME_MULTIPLIER = 1.0
MAX_EXTENSION_ATR = 1.5
MIN_AVG_TURNOVER_RS = 5_00_00_000

ATR_PERIOD = 14
STOP_BUFFER_ATR = 0.2
MIN_RISK_ATR = 0.8
MAX_RISK_ATR = 2.0
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
    data["EMA50"] = ema(data["Close"], EMA_MID)
    data["EMA200"] = ema(data["Close"], EMA_SLOW)
    data["ATR"] = average_true_range(data, ATR_PERIOD)
    data["RSI"] = wilder_rsi(data["Close"], RSI_PERIOD)
    data["ADX"], _, _ = adx(data, ADX_PERIOD)
    data["AvgVolume20"] = data["Volume"].shift(1).rolling(VOLUME_PERIOD, min_periods=VOLUME_PERIOD).mean()

    today = data.iloc[-1]
    yesterday = data.iloc[-2]
    ema50_before = data["EMA50"].iloc[-11]
    ema200_before = data["EMA200"].iloc[-21]
    recent = data.iloc[-PULLBACK_LOOKBACK:]

    check_values = [
        today["Close"], today["Open"], today["Volume"], today["EMA20"], today["EMA50"], today["EMA200"],
        today["ATR"], today["RSI"], yesterday["RSI"], today["ADX"], today["AvgVolume20"],
        ema50_before, ema200_before
    ]
    if any(pd.isna(v) for v in check_values):
        return None

    close = float(today["Close"])
    atr = float(today["ATR"])
    if atr <= 0 or today["AvgVolume20"] <= 0:
        return None

    # Liquidity check
    avg_turnover = float(today["AvgVolume20"]) * close
    if avg_turnover < MIN_AVG_TURNOVER_RS:
        return None

    # 1. Strong uptrend
    if not (close > today["EMA200"] and today["EMA20"] > today["EMA50"] > today["EMA200"]):
        return None
    if not (today["EMA50"] > ema50_before and today["EMA200"] > ema200_before):
        return None

    # 2. Trend strength
    if today["ADX"] < MIN_ADX:
        return None

    # 3. Pullback check
    touched_ema20 = (recent["Low"] <= recent["EMA20"]).any()
    held_ema50 = (recent["Close"] >= recent["EMA50"]).all()
    rsi_dipped = recent["RSI"].min() <= RSI_PULLBACK_MAX
    if not (touched_ema20 and held_ema50 and rsi_dipped):
        return None

    # 4. Trigger candle
    if not (close > float(today["Open"]) and close > float(yesterday["High"]) and close > today["EMA20"]):
        return None

    # 5. RSI recovery
    if not (today["RSI"] > yesterday["RSI"] and RSI_TRIGGER_MIN <= today["RSI"] <= RSI_TRIGGER_MAX):
        return None

    # 6. Volume
    volume_ratio = float(today["Volume"]) / float(today["AvgVolume20"])
    if volume_ratio < VOLUME_MULTIPLIER:
        return None

    # 7. Not extended
    extension_atr = (close - float(today["EMA20"])) / atr
    if extension_atr > MAX_EXTENSION_ATR:
        return None

    # 9. Stop Loss
    swing_low = float(recent["Low"].min())
    stop_loss = swing_low - (STOP_BUFFER_ATR * atr)
    risk = close - stop_loss

    if risk > MAX_RISK_ATR * atr:
        return None
    if risk < MIN_RISK_ATR * atr:
        stop_loss = close - (MIN_RISK_ATR * atr)
        risk = close - stop_loss

    if stop_loss <= 0 or risk <= 0:
        return None

    # 10. Target
    target = close + (risk * RISK_REWARD)
    entry_r = round_tick(close)
    stop_r = round_tick(stop_loss)
    target_r = round_tick(target)
    if not entry_r or not stop_r or not target_r:
        return None

    risk_r = round(entry_r - stop_r, 2)
    reward_r = round(target_r - entry_r, 2)
    if risk_r <= 0 or reward_r <= 0:
        return None

    signal_date = data.index[-1]
    date_val = signal_date.strftime("%Y-%m-%d") if hasattr(signal_date, "strftime") else str(signal_date)

    return {
        "Date": date_val,
        "Entry": entry_r,
        "StopLoss": stop_r,
        "Target": target_r,
        "Risk_Rs": risk_r,
        "Reward_Rs": reward_r,
        "EMA20": round(float(today["EMA20"]), 2),
        "EMA50": round(float(today["EMA50"]), 2),
        "EMA200": round(float(today["EMA200"]), 2),
        "RSI": round(float(today["RSI"]), 2),
        "ADX": round(float(today["ADX"]), 2),
        "ATR14": round(atr, 2),
        "VolumeRatio": round(volume_ratio, 2),
        "ExtensionATR": round(float(extension_atr), 2),
        "SwingLow": round(swing_low, 2),
        "AvgTurnoverCr": round(avg_turnover / 1e7, 2),
    }