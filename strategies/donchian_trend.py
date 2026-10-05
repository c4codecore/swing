"""
Trend Following: Donchian breakout with a chandelier trailing exit.

Idea: buy a stock that has just made a new 55-day high while its long-term trend, trend
strength and volume all agree, then stay in until the trend gives back 3 ATR from its
highest high. Losses are cut early at 2.5 ATR; there is no profit target. Expect a low
win rate (30-40%) with a few large winners paying for many small losers.

Entry filters (all must pass):
1. Close above EMA50, EMA50 above EMA200, EMA200 higher than 20 sessions ago
2. ADX(14) at least 22 with +DI above -DI
3. Close above the highest high of the previous 55 sessions
4. Not chasing: close no more than 1 ATR above that 55-day high
5. Strong close: in the top 40% of the day's range
6. Volume at least 1.2x the average of the previous 20 sessions
7. 6-month return of at least 10%
8. ATR between 1.2% and 5% of the price
9. Close no more than 25% above EMA50 (skips parabolic moves)
10. Average daily turnover of at least Rs 5 crore

Exit (handled by backtest.py when EXIT_MODE is "trailing", and by manage_open_position
for live trades):
- Initial stop: entry - 2.5 ATR
- Trailing stop: highest high since entry - 3.0 ATR, only ever moves up, checked daily
- Time stop: close of day 90 if still open
Only runs while the Nifty regime is Bullish.
"""

from core.indicators import ema, adx, average_true_range
from core.trailing import chandelier_stop_levels
from core.utils import round_tick

NAME = "Trend Following (Donchian + Chandelier)"
REQUIRED_REGIME = "Bullish"
DATA_PERIOD = "2y"

EXIT_MODE = "trailing"
TRAIL_ATR_MULTIPLE = 3.0
TRAIL_ATR_PERIOD = 20
MAX_HOLD_DAYS = 90
MAX_RISK_EXPANSION = 1.25

BREAKOUT_LOOKBACK_DAYS = 55
MAX_EXTENSION_ATR = 1.0
MIN_CLOSE_POSITION_IN_RANGE = 0.6
VOLUME_LOOKBACK_DAYS = 20
MIN_VOLUME_RATIO = 1.2
EMA200_SLOPE_LOOKBACK_DAYS = 20
ADX_PERIOD = 14
MIN_ADX = 22
MOMENTUM_LOOKBACK_DAYS = 126
MIN_MOMENTUM_PCT = 10.0
MIN_ATR_PCT = 1.2
MAX_ATR_PCT = 5.0
MAX_DISTANCE_FROM_EMA50_PCT = 25.0
INITIAL_STOP_ATR_MULTIPLE = 2.5
REFERENCE_RISK_REWARD = 3.0
MIN_AVG_TURNOVER_RS = 5_00_00_000
MIN_ROWS = 215


def _prepare_indicators(price_data):
    df = price_data.copy()
    df["EMA50"] = ema(df["Close"], 50)
    df["EMA200"] = ema(df["Close"], 200)
    df["ATR"] = average_true_range(df, TRAIL_ATR_PERIOD)
    df["ADX"], df["PlusDI"], df["MinusDI"] = adx(df, ADX_PERIOD)
    df["AvgVolumePrev"] = df["Volume"].shift(1).rolling(VOLUME_LOOKBACK_DAYS).mean()
    return df


def _breakout_level(df):
    return float(df["High"].iloc[-(BREAKOUT_LOOKBACK_DAYS + 1):-1].max())


def _filters(df):
    today = df.iloc[-1]
    breakout_level = _breakout_level(df)
    day_range = float(today["High"] - today["Low"])
    close_position = (float(today["Close"] - today["Low"]) / day_range) if day_range > 0 else 0.0
    ema200_earlier = float(df["EMA200"].iloc[-(EMA200_SLOPE_LOOKBACK_DAYS + 1)])
    close_earlier = float(df["Close"].iloc[-(MOMENTUM_LOOKBACK_DAYS + 1)])
    momentum_pct = (float(today["Close"]) / close_earlier - 1) * 100
    atr_pct = float(today["ATR"]) / float(today["Close"]) * 100
    distance_from_ema50_pct = (float(today["Close"]) / float(today["EMA50"]) - 1) * 100
    turnover = float((df["Close"] * df["Volume"]).tail(20).mean())

    return [
        ("Uptrend (close > EMA50 > EMA200)",
         lambda: bool(today["Close"] > today["EMA50"] > today["EMA200"])),
        ("EMA200 rising", lambda: bool(today["EMA200"] > ema200_earlier)),
        ("ADX at least 22 and +DI above -DI",
         lambda: bool(today["ADX"] >= MIN_ADX and today["PlusDI"] > today["MinusDI"])),
        ("Close above 55-day high", lambda: bool(today["Close"] > breakout_level)),
        ("Not extended (within 1 ATR of breakout level)",
         lambda: bool(today["Close"] - breakout_level <= MAX_EXTENSION_ATR * today["ATR"])),
        ("Close in top 40% of day's range",
         lambda: bool(close_position >= MIN_CLOSE_POSITION_IN_RANGE)),
        ("Volume at least 1.2x previous 20-day average",
         lambda: bool(today["Volume"] >= today["AvgVolumePrev"] * MIN_VOLUME_RATIO)),
        ("6-month return at least 10%", lambda: bool(momentum_pct >= MIN_MOMENTUM_PCT)),
        ("ATR between 1.2% and 5% of price",
         lambda: bool(MIN_ATR_PCT <= atr_pct <= MAX_ATR_PCT)),
        ("Not parabolic (close within 25% of EMA50)",
         lambda: bool(distance_from_ema50_pct <= MAX_DISTANCE_FROM_EMA50_PCT)),
        ("Turnover at least Rs 5 crore", lambda: turnover >= MIN_AVG_TURNOVER_RS),
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
    entry = round_tick(float(today["Close"]))
    stop = round_tick(float(today["Close"]) - INITIAL_STOP_ATR_MULTIPLE * atr)
    if entry is None or stop is None or stop <= 0 or entry <= stop:
        return None

    risk = round(entry - stop, 2)
    reference_target = round_tick(entry + REFERENCE_RISK_REWARD * risk)

    return {
        "Entry": entry,
        "StopLoss": stop,
        "Target": reference_target,
        "Risk_Rs": risk,
        "Reward_Rs": round(reference_target - entry, 2),
        "BreakoutLevel": round(_breakout_level(df), 2),
        "ADX": round(float(today["ADX"]), 1),
        "VolumeRatio": round(float(today["Volume"] / today["AvgVolumePrev"]), 2),
        "ATR": round(atr, 2),
        "ExitRule": f"trail highest high - {TRAIL_ATR_MULTIPLE} ATR, no target, time stop {MAX_HOLD_DAYS}d",
        "Date": df.index[-1].strftime("%Y-%m-%d"),
    }


def manage_open_position(price_data, entry_date, initial_stop):
    entry_index = price_data.index.get_indexer([entry_date], method="bfill")[0]
    if entry_index < 0:
        return None

    stops, next_stop = chandelier_stop_levels(
        price_data, entry_index, initial_stop, TRAIL_ATR_MULTIPLE, TRAIL_ATR_PERIOD)
    opens = price_data["Open"].to_numpy(dtype=float)
    lows = price_data["Low"].to_numpy(dtype=float)
    days_held = int(len(price_data) - entry_index)

    status = "HOLD"
    for day in range(entry_index, len(price_data)):
        if lows[day] <= stops[day]:
            exit_price = min(opens[day], stops[day]) if day > entry_index else stops[day]
            status = f"EXIT: stop hit on {price_data.index[day].strftime('%Y-%m-%d')} near {round(float(exit_price), 2)}"
            break
        if day - entry_index + 1 >= MAX_HOLD_DAYS:
            status = f"EXIT: time stop reached on {price_data.index[day].strftime('%Y-%m-%d')}"
            break

    return {
        "Status": status,
        "LastClose": round(float(price_data["Close"].iloc[-1]), 2),
        "StopForTomorrow": round_tick(next_stop),
        "DaysHeld": days_held,
        "HighestHighSinceEntry": round(float(price_data["High"].iloc[entry_index:].max()), 2),
    }
