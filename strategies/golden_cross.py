"""
Golden Cross Strategy - Improved Version

Strategy:
1. Fresh EMA 50 / EMA 200 Golden Cross
2. Price above EMA 200
3. EMA 200 rising over a longer period
4. Price not excessively extended from EMA 200
5. Volume >= 1.5x previous 20-day average volume
6. Bullish candle confirmation
7. Wilder ATR(14) based Stop Loss
8. Target = 2R

Notes:
- Latest forming daily candle is ignored when the market is open.
- Actual trade execution handled by backtester on next trading day Open.
"""

import pandas as pd
from core.utils import round_tick, remove_forming_candle, clean_ohlcv
from core.indicators import ema, average_true_range

NAME = "Golden Cross"

# =========================
# Strategy Parameters
# =========================

EMA_FAST = 50
EMA_SLOW = 200
MIN_WARMUP_BARS = 400

VOLUME_PERIOD = 20
VOLUME_MULTIPLIER = 1.5

EMA_SLOPE_LOOKBACK = 10
MAX_EMA200_DISTANCE_PCT = 8.0

ATR_PERIOD = 14
ATR_MULTIPLIER = 2.0
RISK_REWARD = 2.0
DATA_PERIOD = "3y"


# =========================
# Signal Generator
# =========================

def generate_signal(price_data):
    data = clean_ohlcv(price_data)
    if data is None or data.empty:
        return None

    data = remove_forming_candle(data)
    if data is None or len(data) < max(MIN_WARMUP_BARS, EMA_SLOW + EMA_SLOPE_LOOKBACK, EMA_SLOW + VOLUME_PERIOD):
        return None

    # Calculate indicators
    data["EMA50"] = ema(data["Close"], EMA_FAST)
    data["EMA200"] = ema(data["Close"], EMA_SLOW)
    data["AvgVolume20"] = data["Volume"].shift(1).rolling(VOLUME_PERIOD, min_periods=VOLUME_PERIOD).mean()
    data["ATR"] = average_true_range(data, ATR_PERIOD, min_periods=ATR_PERIOD)

    today = data.iloc[-1]
    yesterday = data.iloc[-2]
    ema200_previous = data["EMA200"].iloc[-1 - EMA_SLOPE_LOOKBACK]

    # Required non-null check
    required_vals = [today["Close"], today["EMA50"], today["EMA200"], today["AvgVolume20"], today["ATR"],
                     yesterday["EMA50"], yesterday["EMA200"], ema200_previous]
    if any(pd.isna(v) for v in required_vals):
        return None

    # 1. Fresh Golden Cross
    if not (yesterday["EMA50"] <= yesterday["EMA200"] and today["EMA50"] > today["EMA200"]):
        return None

    # 2. Price above EMA200
    if today["Close"] <= today["EMA200"]:
        return None

    # 3. EMA200 rising
    if today["EMA200"] <= ema200_previous:
        return None

    # 4. Price extension filter
    ema200_distance_pct = ((today["Close"] - today["EMA200"]) / today["EMA200"]) * 100
    if ema200_distance_pct > MAX_EMA200_DISTANCE_PCT:
        return None

    # 5. Volume confirmation
    avg_vol = today["AvgVolume20"]
    curr_vol = today["Volume"]
    if avg_vol <= 0 or curr_vol <= 0 or (curr_vol / avg_vol) < VOLUME_MULTIPLIER:
        return None

    # 6. Bullish candle confirmation
    if today["Close"] <= today["Open"]:
        return None

    # 7. ATR & Price Levels
    atr = today["ATR"]
    if atr <= 0:
        return None

    entry = float(today["Close"])
    stop_loss = entry - (ATR_MULTIPLIER * float(atr))
    if stop_loss <= 0 or stop_loss >= entry:
        return None

    risk_per_share = entry - stop_loss
    target = entry + (risk_per_share * RISK_REWARD)

    entry_rounded = round_tick(entry)
    stop_loss_rounded = round_tick(stop_loss)
    target_rounded = round_tick(target)
    if not entry_rounded or not stop_loss_rounded or not target_rounded:
        return None

    final_risk = round(entry_rounded - stop_loss_rounded, 2)
    final_reward = round(target_rounded - entry_rounded, 2)
    if final_risk <= 0 or final_reward <= 0:
        return None

    signal_date = data.index[-1]
    date_val = signal_date.strftime("%Y-%m-%d") if hasattr(signal_date, "strftime") else str(signal_date)

    return {
        "Date": date_val,
        "Entry": entry_rounded,
        "StopLoss": stop_loss_rounded,
        "Target": target_rounded,
        "Risk_Rs": final_risk,
        "Reward_Rs": final_reward,
        "EMA50": round(float(today["EMA50"]), 2),
        "EMA200": round(float(today["EMA200"]), 2),
        "EMA200DistancePct": round(float(ema200_distance_pct), 2),
        "VolumeRatio": round(float(curr_vol / avg_vol), 2),
        "ATR14": round(float(atr), 2),
    }