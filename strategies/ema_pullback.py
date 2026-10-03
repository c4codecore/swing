"""
EMA Trend + Pullback: buy the first bounce after a dip to the 20 EMA inside a full uptrend.

Filters (all must pass):
1. EMA20 above EMA50 above EMA200
2. Close within 3% of the 20 EMA
3. Bounce: close above yesterday's high
4. Volume above the average of the previous 10 sessions
5. Average daily turnover of at least Rs 5 crore

Entry: today's close. Stop: lowest low of the last 6 sessions, widened to at least 1.5 ATR.
Target: 2x the risk. Only runs while the Nifty regime is Bullish.
"""

from core.indicators import ema, average_true_range
from core.trade_levels import build_long_levels, average_turnover

NAME = "EMA Trend + Pullback"
REQUIRED_REGIME = "Bullish"
DATA_PERIOD = "2y"

PULLBACK_TOLERANCE_PCT = 3.0
VOLUME_LOOKBACK_DAYS = 10
STOPLOSS_LOOKBACK_DAYS = 6
ATR_PERIOD = 14
RISK_REWARD_RATIO = 2.0
MIN_AVG_TURNOVER_RS = 5_00_00_000
MIN_ROWS = 215


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["EMA20"] = ema(df["Close"], 20)
    df["EMA50"] = ema(df["Close"], 50)
    df["EMA200"] = ema(df["Close"], 200)
    df["ATR"] = average_true_range(df, ATR_PERIOD)
    df["AvgVolumePrev"] = df["Volume"].shift(1).rolling(VOLUME_LOOKBACK_DAYS).mean()
    return df


def _filters(df):
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    distance_from_ema20_pct = abs(today["Close"] - today["EMA20"]) / today["EMA20"] * 100
    return [
        ("Uptrend (EMA20 > EMA50 > EMA200)",
         lambda: bool(today["EMA20"] > today["EMA50"] > today["EMA200"])),
        ("Price within 3% of EMA20", lambda: bool(distance_from_ema20_pct <= PULLBACK_TOLERANCE_PCT)),
        ("Close above yesterday's high", lambda: bool(today["Close"] > yesterday["High"])),
        ("Volume above 10-day average", lambda: bool(today["Volume"] > today["AvgVolumePrev"])),
        ("Turnover at least Rs 5 crore", lambda: average_turnover(df) >= MIN_AVG_TURNOVER_RS),
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
    swing_low = float(df["Low"].tail(STOPLOSS_LOOKBACK_DAYS).min())
    levels = build_long_levels(float(today["Close"]), swing_low, atr, RISK_REWARD_RATIO)
    if levels is None:
        return None

    levels.update({
        "EMA20": round(float(today["EMA20"]), 2),
        "EMA50": round(float(today["EMA50"]), 2),
        "ATR": round(atr, 2),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    })
    return levels
