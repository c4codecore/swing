"""
EMA Trend + Pullback: buy the first bounce after a dip to the 20 EMA inside an uptrend.

Filters (all must pass):
1. Uptrend: 20 EMA above 50 EMA
2. Price within 3% of the 20 EMA
3. Bounce: close above yesterday's high
4. Volume above the 10-day average

Entry: today's close. Stop: 5% below entry. Target: 2x the risk.
"""

from core.indicators import ema

NAME = "EMA Trend + Pullback"


EMA_SHORT_PERIOD = 20
EMA_LONG_PERIOD = 50
PULLBACK_TOLERANCE_PCT = 3.0
VOLUME_LOOKBACK_DAYS = 10
STOPLOSS_PCT = 5.0
RISK_REWARD_RATIO = 2.0
MIN_ROWS = EMA_LONG_PERIOD + 2


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["EMA20"] = ema(df["Close"], EMA_SHORT_PERIOD)
    df["EMA50"] = ema(df["Close"], EMA_LONG_PERIOD)
    df["AvgVolume10"] = df["Volume"].rolling(VOLUME_LOOKBACK_DAYS).mean()
    return df


def _filters(df):
    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    def distance_from_ema20_pct():
        return abs(today["Close"] - today["EMA20"]) / today["EMA20"] * 100

    return [
        ("Uptrend (EMA20 above EMA50)", lambda: bool(today["EMA20"] > today["EMA50"])),
        ("Price within 3% of EMA20", lambda: bool(distance_from_ema20_pct() <= PULLBACK_TOLERANCE_PCT)),
        ("Close above yesterday's high", lambda: bool(today["Close"] > yesterday["High"])),
        ("Volume above 10-day average", lambda: bool(today["Volume"] > today["AvgVolume10"])),
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
    entry_price = round(float(today["Close"]), 2)
    stoploss_price = round(entry_price * (1 - STOPLOSS_PCT / 100), 2)
    risk_per_share = entry_price - stoploss_price
    target_price = round(entry_price + risk_per_share * RISK_REWARD_RATIO, 2)

    return {
        "Entry": entry_price,
        "StopLoss": stoploss_price,
        "Target": target_price,
        "Risk_Rs": round(risk_per_share, 2),
        "Reward_Rs": round(target_price - entry_price, 2),
        "EMA20": round(float(today["EMA20"]), 2),
        "EMA50": round(float(today["EMA50"]), 2),
        "Volume": int(today["Volume"]),
        "AvgVolume10": int(today["AvgVolume10"]),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    }
