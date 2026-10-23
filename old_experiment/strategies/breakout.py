"""
Resistance Breakout: a fresh close above the 20-day high, on heavy volume, inside an uptrend.

Filters (all must pass):
1. Close above the 50 EMA and the 50 EMA above the 200 EMA
2. Close above the highest high of the previous 20 sessions
3. Not chasing: close no more than 1 ATR above that resistance level
4. Volume at least 1.5x the average of the previous 20 sessions
5. Bullish candle closing in the top 40% of its day range
6. Average daily turnover of at least Rs 5 crore

Entry: today's close. Stop: below the broken resistance, widened to at least 1.5 ATR.
Target: 2x the risk. Only runs while the Nifty regime is Bullish.
"""

from core.indicators import ema, average_true_range
from core.trade_levels import build_long_levels, average_turnover

NAME = "Resistance Breakout"
REQUIRED_REGIME = "Bullish"
DATA_PERIOD = "2y"

LOOKBACK_DAYS = 20
VOLUME_MULTIPLIER = 1.5
MAX_EXTENSION_ATR = 1.0
MIN_CLOSE_POSITION_IN_RANGE = 0.6
ATR_PERIOD = 14
RISK_REWARD_RATIO = 2.0
MIN_AVG_TURNOVER_RS = 5_00_00_000
MIN_ROWS = 215


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["EMA50"] = ema(df["Close"], 50)
    df["EMA200"] = ema(df["Close"], 200)
    df["ATR"] = average_true_range(df, ATR_PERIOD)
    df["AvgVolumePrev"] = df["Volume"].shift(1).rolling(LOOKBACK_DAYS).mean()
    return df


def _filters(df):
    today = df.iloc[-1]
    resistance_level = float(df.iloc[-(LOOKBACK_DAYS + 1):-1]["High"].max())
    day_range = float(today["High"] - today["Low"])
    close_position = (float(today["Close"] - today["Low"]) / day_range) if day_range > 0 else 0.0
    return resistance_level, [
        ("Uptrend (close > EMA50 > EMA200)",
         lambda: bool(today["Close"] > today["EMA50"] > today["EMA200"])),
        ("Close above 20-day high", lambda: bool(today["Close"] > resistance_level)),
        ("Not extended (within 1 ATR of resistance)",
         lambda: bool(today["Close"] - resistance_level <= MAX_EXTENSION_ATR * today["ATR"])),
        ("Volume at least 1.5x previous 20-day average",
         lambda: bool(today["Volume"] >= today["AvgVolumePrev"] * VOLUME_MULTIPLIER)),
        ("Strong bullish candle",
         lambda: bool(today["Close"] > today["Open"] and close_position >= MIN_CLOSE_POSITION_IN_RANGE)),
        ("Turnover at least Rs 5 crore", lambda: average_turnover(df) >= MIN_AVG_TURNOVER_RS),
    ]


def evaluate_filters(price_data):
    if price_data is None or len(price_data) < MIN_ROWS:
        return None
    _, filters = _filters(_prepare_indicators(price_data))
    return {name: check() for name, check in filters}


def generate_signal(price_data):
    if price_data is None or len(price_data) < MIN_ROWS:
        return None
    df = _prepare_indicators(price_data)
    resistance_level, filters = _filters(df)
    if not all(check() for _, check in filters):
        return None

    today = df.iloc[-1]
    atr = float(today["ATR"])
    levels = build_long_levels(float(today["Close"]), resistance_level, atr, RISK_REWARD_RATIO)
    if levels is None:
        return None

    levels.update({
        "ResistanceLevel": round(resistance_level, 2),
        "VolumeRatio": round(float(today["Volume"] / today["AvgVolumePrev"]), 2),
        "ATR": round(atr, 2),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    })
    return levels
