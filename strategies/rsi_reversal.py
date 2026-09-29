"""
RSI Reversal: buy when RSI climbs back above the oversold line.

Filters (all must pass):
1. RSI(14) was below 30 yesterday and is at or above 30 today
2. Bounce: close above yesterday's close

Entry: today's close. Stop: lowest low of the last 5 sessions. Target: 2x the risk.
This is a counter-trend setup and performs poorly while the broader market is falling.
"""

from core.indicators import wilder_rsi

NAME = "RSI Reversal"


RSI_PERIOD = 14
RSI_OVERSOLD_LEVEL = 30
STOPLOSS_LOOKBACK_DAYS = 5
RISK_REWARD_RATIO = 2.0
MIN_ROWS = RSI_PERIOD + 5


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["RSI"] = wilder_rsi(df["Close"], RSI_PERIOD)
    return df


def _filters(df):
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    return [
        ("RSI crossed back above 30",
         lambda: bool(yesterday["RSI"] < RSI_OVERSOLD_LEVEL and today["RSI"] >= RSI_OVERSOLD_LEVEL)),
        ("Close above yesterday's close", lambda: bool(today["Close"] > yesterday["Close"])),
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
    stoploss_price = round(float(df["Low"].tail(STOPLOSS_LOOKBACK_DAYS).min()), 2)
    risk_per_share = entry_price - stoploss_price
    if risk_per_share <= 0:
        return None
    target_price = round(entry_price + risk_per_share * RISK_REWARD_RATIO, 2)

    return {
        "Entry": entry_price,
        "StopLoss": stoploss_price,
        "Target": target_price,
        "Risk_Rs": round(risk_per_share, 2),
        "Reward_Rs": round(target_price - entry_price, 2),
        "RSI": round(float(today["RSI"]), 2),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    }
