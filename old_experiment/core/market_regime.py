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
    Prints a formatted status banner showing current Nifty trend and risk advisory with colorama.
    """
    from core.ui import (
        badge_regime, bright_cyan, bright_green, bright_red, bright_yellow,
        bright_white, dim, Fore, Style
    )

    border = f"{Fore.LIGHTBLUE_EX}{'═' * 66}{Style.RESET_ALL}"
    print(f"\n{border}")

    if regime is None:
        print(f"  {bright_yellow('Nifty Regime:')} {Fore.LIGHTRED_EX}UNKNOWN (could not fetch index data){Style.RESET_ALL}")
    else:
        trend = regime["trend"]
        regime_badge = badge_regime(trend)

        stats = (
            f"{dim('(')}"
            f"{bright_white('Close:')} {bright_cyan(str(regime['close']))}  "
            f"{bright_white('20EMA:')} {Fore.LIGHTYELLOW_EX}{regime['ema20']}{Style.RESET_ALL}  "
            f"{bright_white('50EMA:')} {Fore.LIGHTMAGENTA_EX}{regime['ema50']}{Style.RESET_ALL}"
            f"{dim(')')}"
        )

        print(f"  {bright_cyan('Market Trend:')} {regime_badge}  {stats}")

        if regime.get("breadth") is not None:
            b_val = regime["breadth"]
            b_color = Fore.LIGHTGREEN_EX if b_val >= 50.0 else Fore.LIGHTRED_EX
            print(f"  {bright_white('Market Breadth:')} {b_color}{Style.BRIGHT}{b_val}%{Style.RESET_ALL} {dim('of universe stocks above their 50 EMA')}")

        print(f"  {Fore.LIGHTBLACK_EX}{'─' * 62}{Style.RESET_ALL}")
        if trend == "Bearish":
            print(f"  {bright_red('ADVISORY:')} Nifty is in a downtrend. Long-only swing setups")
            print(f"            are {bright_red('HIGH RISK')} right now (breakouts/bounces prone to fail).")
        elif trend == "Bullish":
            print(f"  {bright_green('ADVISORY:')} Nifty is in a healthy uptrend. Long-only swing setups")
            print(f"            have {bright_green('HIGH PROBABILITY')} of sustained momentum.")
        else:
            print(f"  {bright_yellow('ADVISORY:')} Market is range-bound / neutral. Maintain strict risk")
            print(f"            management and consider conservative position sizing.")

    print(f"{border}\n")
