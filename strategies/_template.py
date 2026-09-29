"""
Template for a new strategy. Copy this file to strategies/<name>.py and fill it in.

A strategy module must expose:
- NAME: str
- generate_signal(price_data) -> dict | None
    price_data has columns Open, High, Low, Close, Volume indexed by date.
    Return a dict with at least Entry, StopLoss, Target, Risk_Rs, Reward_Rs when all
    filters pass on the latest row, otherwise None.

Optional but recommended:
- evaluate_filters(price_data) -> dict | None
    Returns {filter name: passed} for every filter, so diagnostic.py can show which
    filters block signals. Keep generate_signal and evaluate_filters on the same list.
"""

from core.indicators import ema

NAME = "Template Strategy"


MIN_ROWS = 60


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["EMA20"] = ema(df["Close"], 20)
    return df


def _filters(df):
    today = df.iloc[-1]
    return [
        ("Close above EMA20", lambda: bool(today["Close"] > today["EMA20"])),
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
    return None
