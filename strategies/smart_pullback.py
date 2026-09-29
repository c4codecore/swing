"""
Smart Pullback — Regime-Filtered Swing Strategy (Long only, 1:2 Risk Reward)

Entry Conditions:
    1. REQUIRED_REGIME: Bullish (checked by runner/backtester)
    2. EMA alignment: EMA20 > EMA50 > EMA200
    3. EMA200 rising (> value 10 days ago)
    4. Pullback zone: In last 6 days, Low touched EMA20 (within 1.5%)
    5. Pullback held: Structure intact above EMA50
    6. Recovery candle: Bullish candle + Close > EMA20
    7. Momentum break: Close > yesterday's High
    8. RSI: 42 to 68
    9. Volume: >= 1.2x 20-day average
   10. Liquidity: Avg daily turnover >= Rs 5 crore
   11. Not extended: Close <= 1.5 ATR above EMA20
"""

import pandas as pd
from core.utils import round_tick, remove_forming_candle, clean_ohlcv
from core.indicators import ema, wilder_rsi, average_true_range

NAME = "Smart Pullback"
REQUIRED_REGIME = "Bullish"
DATA_PERIOD = "2y"

# Parameters
EMA_FAST = 20
EMA_MID = 50
EMA_SLOW = 200
EMA_SLOPE_LOOKBACK = 10

PULLBACK_LOOKBACK = 6
PULLBACK_ZONE_PCT = 1.5

RSI_PERIOD = 14
RSI_MIN = 42
RSI_MAX = 68

VOLUME_PERIOD = 20
VOLUME_MULTIPLIER = 1.2

ATR_PERIOD = 14
MAX_EXTENSION_ATR = 1.5
MIN_RISK_ATR = 0.5
MAX_RISK_ATR = 2.5
STOP_BUFFER_ATR = 0.15
RISK_REWARD = 2.0

MIN_AVG_TURNOVER = 5_00_00_000
MIN_WARMUP_BARS = 250


def generate_signal(price_data):
    df = clean_ohlcv(price_data)
    if df is None or df.empty:
        return None

    df = remove_forming_candle(df)
    if df is None or len(df) < MIN_WARMUP_BARS:
        return None

    # Calculate indicators
    df["EMA20"] = ema(df["Close"], EMA_FAST)
    df["EMA50"] = ema(df["Close"], EMA_MID)
    df["EMA200"] = ema(df["Close"], EMA_SLOW)
    df["ATR"] = average_true_range(df, ATR_PERIOD)
    df["RSI"] = wilder_rsi(df["Close"], RSI_PERIOD)
    df["AvgVol20"] = df["Volume"].shift(1).rolling(VOLUME_PERIOD, min_periods=VOLUME_PERIOD).mean()

    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    pullback = df.iloc[-(PULLBACK_LOOKBACK + 1):-1]

    need = [
        today["Close"], today["Open"], today["High"], today["EMA20"], today["EMA50"], today["EMA200"],
        today["ATR"], today["RSI"], today["AvgVol20"], today["Volume"], yesterday["High"],
        df["EMA200"].iloc[-1 - EMA_SLOPE_LOOKBACK],
    ]
    if any(pd.isna(v) for v in need):
        return None

    close = float(today["Close"])
    atr = float(today["ATR"])
    if atr <= 0 or float(today["AvgVol20"]) <= 0:
        return None

    # Filter 1: Liquidity
    avg_turnover = float(today["AvgVol20"]) * close
    if avg_turnover < MIN_AVG_TURNOVER:
        return None

    # Filter 2: Uptrend
    e20 = float(today["EMA20"])
    e50 = float(today["EMA50"])
    e200 = float(today["EMA200"])
    if not (e20 > e50 > e200):
        return None

    # Filter 3: EMA200 rising
    e200_old = float(df["EMA200"].iloc[-1 - EMA_SLOPE_LOOKBACK])
    if e200 <= e200_old:
        return None

    # Filter 4: Pullback touched EMA20 zone
    if len(pullback) < 2:
        return None
    pb_ema20 = df["EMA20"].iloc[-(PULLBACK_LOOKBACK + 1):-1]
    dist_pct = ((pullback["Low"].values - pb_ema20.values) / pb_ema20.values) * 100
    if not ((dist_pct >= -PULLBACK_ZONE_PCT) & (dist_pct <= PULLBACK_ZONE_PCT)).any():
        return None

    # Filter 5: Pullback held above EMA50
    pb_ema50 = df["EMA50"].iloc[-(PULLBACK_LOOKBACK + 1):-1]
    below_e50_pct = ((pullback["Close"].values - pb_ema50.values) / pb_ema50.values) * 100
    if (below_e50_pct < -1.0).any():
        return None

    # Filter 6 & 7: Recovery candle & High breakout
    if close <= float(today["Open"]) or close <= e20 or close <= float(yesterday["High"]):
        return None

    # Filter 8: RSI in recovery zone
    rsi = float(today["RSI"])
    if not (RSI_MIN <= rsi <= RSI_MAX):
        return None

    # Filter 9: Volume confirmation
    vol_ratio = float(today["Volume"]) / float(today["AvgVol20"])
    if vol_ratio < VOLUME_MULTIPLIER:
        return None

    # Filter 10: Not extended
    extension = (close - e20) / atr
    if extension > MAX_EXTENSION_ATR:
        return None

    # Stop Loss & Target
    swing_low = float(pullback["Low"].min())
    stop_loss = swing_low - (STOP_BUFFER_ATR * atr)
    risk = close - stop_loss

    if risk > MAX_RISK_ATR * atr:
        return None
    if risk < MIN_RISK_ATR * atr:
        stop_loss = close - (MIN_RISK_ATR * atr)
        risk = close - stop_loss

    if stop_loss <= 0 or risk <= 0:
        return None

    target = close + (risk * RISK_REWARD)
    entry_r = round_tick(close)
    stop_r = round_tick(stop_loss)
    target_r = round_tick(target)
    if not entry_r or not stop_r or not target_r:
        return None

    risk_r = round(entry_r - stop_r, 2)
    reward_r = round(target_r - entry_r, 2)
    if stop_r <= 0 or risk_r <= 0:
        return None

    sig_ts = df.index[-1]
    date_val = sig_ts.strftime("%Y-%m-%d") if hasattr(sig_ts, "strftime") else str(sig_ts)

    return {
        "Date": date_val,
        "Entry": entry_r,
        "StopLoss": stop_r,
        "Target": target_r,
        "Risk_Rs": risk_r,
        "Reward_Rs": reward_r,
        "EMA20": round(e20, 2),
        "EMA50": round(e50, 2),
        "EMA200": round(e200, 2),
        "RSI": round(rsi, 2),
        "ATR14": round(atr, 2),
        "VolumeRatio": round(vol_ratio, 2),
        "Extension": round(extension, 2),
        "SwingLow": round(swing_low, 2),
        "TurnoverCr": round(avg_turnover / 1e7, 2),
    }
