"""
RSI Reversal (dip buy inside an uptrend): RSI dips into the low zone and turns back up.

Filters (all must pass):
1. Close above the 200 EMA and the 50 EMA above the 200 EMA
2. RSI(14) was at or below 35 at some point in the last 5 sessions
3. RSI crossed back above 40 today
4. Bullish candle that closes above yesterday's close
5. Average daily turnover of at least Rs 5 crore

Entry: today's close. Stop: lowest low of the last 5 sessions, widened to at least 1.5 ATR.
Target: 2x the risk. Only runs while the Nifty regime is Bullish.
"""

from core.indicators import ema, wilder_rsi, average_true_range
from core.trade_levels import build_long_levels, average_turnover

NAME = "RSI Reversal"
REQUIRED_REGIME = "Bullish"
DATA_PERIOD = "2y"

RSI_PERIOD = 14
RSI_DIP_LEVEL = 35
RSI_DIP_LOOKBACK_DAYS = 5
RSI_RECOVERY_LEVEL = 40
STOPLOSS_LOOKBACK_DAYS = 5
ATR_PERIOD = 14
RISK_REWARD_RATIO = 2.0
MIN_AVG_TURNOVER_RS = 5_00_00_000
MIN_ROWS = 215


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["RSI"] = wilder_rsi(df["Close"], RSI_PERIOD)
    df["ATR"] = average_true_range(df, ATR_PERIOD)
    df["EMA50"] = ema(df["Close"], 50)
    df["EMA200"] = ema(df["Close"], 200)
    return df


def _filters(df):
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    recent_rsi_low = df["RSI"].iloc[-(RSI_DIP_LOOKBACK_DAYS + 1):].min()
    return [
        ("Uptrend (close > EMA200, EMA50 > EMA200)",
         lambda: bool(today["Close"] > today["EMA200"] and today["EMA50"] > today["EMA200"])),
        ("RSI dipped to 35 or lower recently", lambda: bool(recent_rsi_low <= RSI_DIP_LEVEL)),
        ("RSI crossed back above 40",
         lambda: bool(yesterday["RSI"] < RSI_RECOVERY_LEVEL <= today["RSI"])),
        ("Bullish candle above yesterday's close",
         lambda: bool(today["Close"] > today["Open"] and today["Close"] > yesterday["Close"])),
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
        "RSI": round(float(today["RSI"]), 2),
        "ATR": round(atr, 2),
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    })
    return levels
