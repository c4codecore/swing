"""
Resistance Breakout: buy a close above the 20-day high on heavy volume.

Filters (all must pass):
1. Close above the highest high of the previous 20 sessions
2. Volume above 1.5x the 20-day average (the average includes today)

Entry: today's close. Stop: 2% below the broken resistance. Target: 2x the risk.
"""

NAME = "Resistance Breakout"

LOOKBACK_DAYS = 20
VOLUME_LOOKBACK_DAYS = 20
VOLUME_MULTIPLIER = 1.5
STOPLOSS_BUFFER_PCT = 2.0
RISK_REWARD_RATIO = 2.0
MIN_ROWS = LOOKBACK_DAYS + 5


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["AvgVolume"] = df["Volume"].rolling(VOLUME_LOOKBACK_DAYS).mean()
    return df


def _filters(df):
    today = df.iloc[-1]
    resistance_level = df.iloc[-(LOOKBACK_DAYS + 1):-1]["High"].max()
    return resistance_level, [
        ("Close above 20-day high", lambda: bool(today["Close"] > resistance_level)),
        ("Volume above 1.5x average", lambda: bool(today["Volume"] > today["AvgVolume"] * VOLUME_MULTIPLIER)),
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
    entry_price = round(float(today["Close"]), 2)
    stoploss_price = round(float(resistance_level) * (1 - STOPLOSS_BUFFER_PCT / 100), 2)
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
        "ResistanceLevel": round(float(resistance_level), 2),
        "Volume": int(today["Volume"]),
        "AvgVolume": int(today["AvgVolume"]),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    }
