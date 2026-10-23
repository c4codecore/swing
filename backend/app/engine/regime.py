"""
Adaptive Multi-Factor Market Regime Engine
Addresses the fatal flaw of simple binary EMA20 > EMA50 filters.
Provides clear risk allocation, market breadth, and regime-tailored strategy rules.
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from app.core.data_fetcher import fetch_benchmark, fetch_ohlcv
from app.core.indicators import ema, sma, rsi, atr
from app.core.config import DEFAULT_UNIVERSE, REGIME_COLORS


def calculate_market_breadth(sample_size: int = 15) -> Dict[str, float]:
    """
    Computes percentage of representative stocks trading above their 20 EMA and 50 EMA.
    High breadth (>70%) confirms genuine market health; low breadth (<30%) warns of divergence.
    """
    sample_symbols = DEFAULT_UNIVERSE[:sample_size]
    above_20_count = 0
    above_50_count = 0
    valid_count = 0

    for sym in sample_symbols:
        try:
            df = fetch_ohlcv(sym, period="6mo")
            if len(df) >= 50:
                c = df['Close']
                e20 = ema(c, 20).iloc[-1]
                e50 = ema(c, 50).iloc[-1]
                cur_price = c.iloc[-1]

                if cur_price > e20:
                    above_20_count += 1
                if cur_price > e50:
                    above_50_count += 1
                valid_count += 1
        except Exception:
            continue

    if valid_count == 0:
        return {"pct_above_20ema": 50.0, "pct_above_50ema": 50.0}

    return {
        "pct_above_20ema": round((above_20_count / valid_count) * 100, 1),
        "pct_above_50ema": round((above_50_count / valid_count) * 100, 1)
    }


def analyze_market_regime() -> Dict[str, Any]:
    """
    Comprehensive Nifty 50 Market Regime Evaluation.
    """
    nifty_df = fetch_benchmark(period="1y")
    if len(nifty_df) < 60:
        return {
            "regime": "NEUTRAL_CHOPPY",
            "title": "Neutral / Sideways",
            "color": REGIME_COLORS["SIDEWAYS_CHOPPY"],
            "description": "Insufficient index data, defaulting to neutral regime.",
            "metrics": {},
            "allowed_strategies": ["RelativeStrengthBreakout", "MeanReversionBand"],
            "max_capital_exposure": 50
        }

    close = nifty_df['Close']
    current_close = float(close.iloc[-1])
    e20 = float(ema(close, 20).iloc[-1])
    e50 = float(ema(close, 50).iloc[-1])
    e200 = float(ema(close, 200).iloc[-1]) if len(close) >= 200 else float(sma(close, min(len(close), 100)).iloc[-1])

    rsi_14 = float(rsi(close, 14).iloc[-1])
    atr_14 = float(atr(nifty_df, 14).iloc[-1])
    atr_pct = (atr_14 / current_close) * 100

    # 5-day slope of 20 EMA
    e20_series = ema(close, 20)
    e20_slope_5d = ((e20_series.iloc[-1] - e20_series.iloc[-5]) / e20_series.iloc[-5]) * 100

    # Distance from 20 EMA
    dist_20ema = ((current_close - e20) / e20) * 100

    # Calculate Market Breadth
    breadth = calculate_market_breadth(sample_size=15)
    pct_above_50 = breadth["pct_above_50ema"]

    # --- Regime Decision Matrix ---
    # 1. Extreme Panic / Capitulation
    if rsi_14 < 30 and dist_20ema < -4.0:
        regime = "EXTREME_PANIC_OVERSOLD"
        title = "Extreme Panic / Capitulation"
        color = REGIME_COLORS["EXTREME_PANIC_OVERSOLD"]
        description = "Market is heavily oversold. High probability for sharp mean-reversion snapbacks. Do NOT short or panic-sell; look for capitulation volume reversal trades."
        allowed_strategies = ["CapitulationReversal", "RelativeStrengthBreakout"]
        recommended_action = "Trade high-conviction oversold bounces only. Use tight stops and take 1.5R - 2R profits quickly."
        max_capital_exposure = 30

    # 2. Strong Bullish Trend
    elif current_close > e20 and e20 > e50 and current_close > e200 and e20_slope_5d > 0.3 and pct_above_50 >= 60:
        regime = "STRONG_BULL"
        title = "Strong Bullish Trend"
        color = REGIME_COLORS["STRONG_BULL"]
        description = "Broad market rally confirmed by high market breadth. Momentum breakouts and trend pullbacks have the highest win rate."
        allowed_strategies = ["TrendPullback", "VolatilitySqueeze", "RelativeStrengthBreakout"]
        recommended_action = "Full position sizing (100% exposure allowed). Trail stop losses aggressively to ride big swings."
        max_capital_exposure = 100

    # 3. Pullback in Healthy Bull
    elif current_close >= e50 and current_close > e200 and rsi_14 >= 45:
        regime = "PULLBACK_BULL"
        title = "Pullback in Bull Market"
        color = REGIME_COLORS["PULLBACK_BULL"]
        description = "Healthy retracement in an overall uptrend. Best time for buying dips near key dynamic support (20/50 EMA)."
        allowed_strategies = ["TrendPullback", "SupportBounce", "RelativeStrengthBreakout"]
        recommended_action = "Deploy 60-80% capital on high-quality pullback setups with confirmed volume bounce."
        max_capital_exposure = 75

    # 4. Bearish Correction
    elif current_close < e50 or e20_slope_5d < -0.8:
        regime = "BEARISH_CORRECTION"
        title = "Bearish Correction / Downtrend"
        color = REGIME_COLORS["BEARISH_CORRECTION"]
        description = "Index in active downtrend. Classical long breakouts fail heavily here. Only trade stocks with extreme Relative Strength (decoupled from index) or oversold bounces."
        allowed_strategies = ["RelativeStrengthBreakout", "CapitulationReversal"]
        recommended_action = "High cash preservation mode (max 25% capital). Strict stops, fast profit-taking at 1.5R."
        max_capital_exposure = 25

    # 5. Sideways / Choppy
    else:
        regime = "SIDEWAYS_CHOPPY"
        title = "Sideways / Choppy Range"
        color = REGIME_COLORS["SIDEWAYS_CHOPPY"]
        description = "No clear trend in benchmark. Volatility squeeze setups and mean-reversion trades perform best."
        allowed_strategies = ["VolatilitySqueeze", "MeanReversionBand", "RelativeStrengthBreakout"]
        recommended_action = "Moderate risk (50% exposure). Avoid chasing breakouts; buy near range support."
        max_capital_exposure = 50

    return {
        "regime": regime,
        "title": title,
        "color": color,
        "description": description,
        "recommended_action": recommended_action,
        "max_capital_exposure_pct": max_capital_exposure,
        "allowed_strategies": allowed_strategies,
        "metrics": {
            "nifty_close": round(current_close, 2),
            "ema_20": round(e20, 2),
            "ema_50": round(e50, 2),
            "ema_200": round(e200, 2),
            "rsi_14": round(rsi_14, 1),
            "atr_pct": round(atr_pct, 2),
            "dist_20ema_pct": round(dist_20ema, 2),
            "breadth_above_50ema_pct": breadth["pct_above_50ema"],
            "breadth_above_20ema_pct": breadth["pct_above_20ema"]
        }
    }
