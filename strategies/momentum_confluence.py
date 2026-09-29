"""
Multi-Confluence Momentum: a fresh MACD crossover inside a strong, non-overbought uptrend.

Filters (all five must pass):
1. Close above the 50 EMA
2. MACD line crossed above its signal line today
3. ADX(14) at least 20
4. RSI(14) between 50 and 70
5. Volume at least 1.2x the 20-day average

Entry: today's close. Stop: lowest low of the last 5 sessions. Target: 2.5x the risk.
"""

from core.indicators import ema, macd, wilder_rsi, adx
from core.utils import round_tick

NAME = "Multi-Confluence Momentum"

EMA_TREND_PERIOD = 50
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ADX_PERIOD = 14
ADX_MIN_STRENGTH = 20
RSI_PERIOD = 14
RSI_MIN = 50
RSI_MAX = 70
VOLUME_LOOKBACK_DAYS = 20
VOLUME_MULTIPLIER = 1.2
STOPLOSS_LOOKBACK_DAYS = 5
RISK_REWARD_RATIO = 2.5
MIN_ROWS = MACD_SLOW + MACD_SIGNAL + ADX_PERIOD + 5


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["EMA50"] = ema(df["Close"], EMA_TREND_PERIOD)
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = macd(df["Close"], MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    df["RSI"] = wilder_rsi(df["Close"], RSI_PERIOD)
    df["ADX"], _, _ = adx(df, ADX_PERIOD)
    df["AvgVolume"] = df["Volume"].rolling(VOLUME_LOOKBACK_DAYS).mean()
    return df


def _filters(df):
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    return [
        ("Close above EMA50", lambda: bool(today["Close"] > today["EMA50"])),
        ("MACD crossed above signal today",
         lambda: bool(yesterday["MACD"] < yesterday["MACD_Signal"] and today["MACD"] >= today["MACD_Signal"])),
        ("ADX at least 20", lambda: bool(today["ADX"] >= ADX_MIN_STRENGTH)),
        ("RSI between 50 and 70", lambda: bool(RSI_MIN <= today["RSI"] <= RSI_MAX)),
        ("Volume at least 1.2x average", lambda: bool(today["Volume"] >= today["AvgVolume"] * VOLUME_MULTIPLIER)),
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
    entry_price = round_tick(today["Close"])
    stoploss_price = round_tick(df["Low"].tail(STOPLOSS_LOOKBACK_DAYS).min())
    if not entry_price or not stoploss_price:
        return None

    risk_per_share = round(entry_price - stoploss_price, 2)
    if risk_per_share <= 0:
        return None
    target_price = round_tick(entry_price + risk_per_share * RISK_REWARD_RATIO)
    if not target_price:
        return None

    return {
        "Entry": entry_price,
        "StopLoss": stoploss_price,
        "Target": target_price,
        "Risk_Rs": risk_per_share,
        "Reward_Rs": round(target_price - entry_price, 2),
        "EMA50": round(float(today["EMA50"]), 2),
        "MACD": round(float(today["MACD"]), 4),
        "MACD_Sig": round(float(today["MACD_Signal"]), 4),
        "RSI": round(float(today["RSI"]), 2),
        "ADX": round(float(today["ADX"]), 2),
        "Volume": int(today["Volume"]),
        "AvgVol20": int(today["AvgVolume"]),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    }
