"""
Nifty 50 Market Regime Detection Module.
========================================

Knowledge (Why Market Regime Filter is the #1 Edge in Swing Trading):
--------------------------------------------------------------------
- "A rising tide lifts all boats." Statistically, 75-80% of individual stocks move in the
  same direction as the broader benchmark index (Nifty 50).
- In a BEARISH market regime:
  * Breakouts tend to fail and form bull traps.
  * Pullback bounces fail to sustain momentum.
  * Long-only win rates drop drastically from ~55% down to ~25-30%.
- In a BULLISH market regime:
  * Trend continuations, pullbacks to 20 EMA, and breakouts produce high Profit Factors.
  
Regime Classification Rules (Based on Nifty 50 Daily):
------------------------------------------------------
1. Bullish: Nifty Close > 50 EMA AND 20 EMA > 50 EMA (Clear Uptrend)
2. Bearish: Nifty Close < 50 EMA AND 20 EMA < 50 EMA (Clear Downtrend - Cash is King)
3. Neutral: Price in transition / Choppy / Range-bound (Trade with reduced position size)
"""

import numpy as np
import pandas as pd
from core.ohlcv_data import fetch_price_history

# Yahoo Finance symbol for NSE Nifty 50 Benchmark Index
NIFTY_INDEX_SYMBOL = "^NSEI"
STRICT_MIN_BREADTH_PCT = 50.0
STRICT_SLOPE_LOOKBACK_DAYS = 10
BREADTH_EMA_PERIOD = 50


def compute_market_breadth(price_histories, ema_period=BREADTH_EMA_PERIOD):
    flags_by_symbol = {}
    for symbol, price_data in price_histories.items():
        close = price_data["Close"]
        trend_line = close.ewm(span=ema_period, adjust=False).mean()
        flags = (close > trend_line).astype(float)
        flags.iloc[:ema_period] = np.nan
        flags_by_symbol[symbol] = flags
    if not flags_by_symbol:
        return pd.Series(dtype=float)
    breadth = pd.DataFrame(flags_by_symbol).mean(axis=1) * 100
    breadth.index = pd.to_datetime(breadth.index).normalize()
    return breadth[~breadth.index.duplicated(keep="last")].sort_index()


def compute_daily_regime(nifty_price_data, breadth=None,
                         min_breadth=STRICT_MIN_BREADTH_PCT,
                         slope_lookback=STRICT_SLOPE_LOOKBACK_DAYS):
    """
    Daily Nifty regime: 'Bullish', 'Neutral' or 'Bearish'.
    With breadth=None the original EMA20/EMA50 rule is used. With a breadth series
    (percent of stocks above their 50 EMA) Bullish also needs a rising EMA50 and
    breadth at or above min_breadth.
    """
    close = nifty_price_data["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    is_bullish = (close > ema50) & (ema20 > ema50)
    is_bearish = (close < ema50) & (ema20 < ema50)

    if breadth is not None:
        nifty_dates = pd.to_datetime(nifty_price_data.index).normalize()
        breadth_on_nifty_dates = breadth.reindex(nifty_dates, method="pad").to_numpy()
        breadth_ok = pd.Series(breadth_on_nifty_dates >= min_breadth, index=nifty_price_data.index)
        ema50_rising = ema50 > ema50.shift(slope_lookback)
        is_bullish = is_bullish & ema50_rising & breadth_ok

    regime = pd.Series("Neutral", index=nifty_price_data.index)
    regime[is_bullish] = "Bullish"
    regime[is_bearish] = "Bearish"
    return regime


def get_market_regime(price_histories=None):
    """
    Latest Nifty regime. Pass the stock price histories to use the strict rule
    (rising EMA50 plus market breadth), matching backtest.py --regime strict.
    """
    price_data = fetch_price_history(NIFTY_INDEX_SYMBOL, period="1y")
    if price_data is None:
        return None

    close = price_data["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    breadth = compute_market_breadth(price_histories) if price_histories else None
    regime_series = compute_daily_regime(price_data, breadth)
    latest_breadth = None
    if breadth is not None and not breadth.empty:
        latest_breadth = round(float(breadth.iloc[-1]), 1)

    return {
        "trend": str(regime_series.iloc[-1]),
        "close": round(float(close.iloc[-1]), 2),
        "ema20": round(float(ema20.iloc[-1]), 2),
        "ema50": round(float(ema50.iloc[-1]), 2),
        "breadth": latest_breadth,
    }


def print_regime_banner(regime):
    """
    Prints a formatted status banner showing current Nifty trend and risk advisory.
    """
    print("\n" + "=" * 60)
    if regime is None:
        print("Nifty regime: UNKNOWN (could not fetch index data)")
    else:
        print(f"Nifty regime: {regime['trend']}  "
              f"(Close={regime['close']}, 20EMA={regime['ema20']}, 50EMA={regime['ema50']})")
        if regime.get("breadth") is not None:
            print(f"Market breadth: {regime['breadth']}% of stocks above their 50 EMA")
        if regime["trend"] == "Bearish":
            print("Nifty itself is in a downtrend - long-only swing setups")
            print("are higher risk right now (bounces are more likely to fail).")
        elif regime["trend"] == "Bullish":
            print("Nifty is in a healthy uptrend - long-only swing setups")
            print("have higher probability of follow-through.")
    print("=" * 60)
