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

import pandas as pd
from core.ohlcv_data import fetch_price_history

# Yahoo Finance symbol for NSE Nifty 50 Benchmark Index
NIFTY_INDEX_SYMBOL = "^NSEI"


def compute_daily_regime(nifty_price_data):
    """
    Computes historical daily market regime across the entire Nifty price series.
    
    Returns:
        pd.Series indexed by date with categorical values: 'Bullish', 'Neutral', or 'Bearish'.
        Used by backtest.py and regime_split.py to tag trades without lookahead bias.
    """
    close = nifty_price_data["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    is_bullish = (close > ema50) & (ema20 > ema50)
    is_bearish = (close < ema50) & (ema20 < ema50)

    regime = pd.Series("Neutral", index=nifty_price_data.index)
    regime[is_bullish] = "Bullish"
    regime[is_bearish] = "Bearish"
    return regime


def get_market_regime():
    """
    Fetches the latest live Nifty 50 index prices and calculates current market regime.
    
    Returns:
        dict: {
            "trend": "Bullish" | "Neutral" | "Bearish",
            "close": latest_close_price,
            "ema20": latest_20_ema,
            "ema50": latest_50_ema
        }
    """
    price_data = fetch_price_history(NIFTY_INDEX_SYMBOL, period="6mo")
    if price_data is None:
        return None

    close = price_data["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    latest_close = float(close.iloc[-1])
    latest_ema20 = float(ema20.iloc[-1])
    latest_ema50 = float(ema50.iloc[-1])

    if latest_close > latest_ema50 and latest_ema20 > latest_ema50:
        trend = "Bullish"
    elif latest_close < latest_ema50 and latest_ema20 < latest_ema50:
        trend = "Bearish"
    else:
        trend = "Neutral"

    return {
        "trend": trend,
        "close": round(latest_close, 2),
        "ema20": round(latest_ema20, 2),
        "ema50": round(latest_ema50, 2),
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
        if regime["trend"] == "Bearish":
            print("Nifty itself is in a downtrend - long-only swing setups")
            print("are higher risk right now (bounces are more likely to fail).")
        elif regime["trend"] == "Bullish":
            print("Nifty is in a healthy uptrend - long-only swing setups")
            print("have higher probability of follow-through.")
    print("=" * 60)
