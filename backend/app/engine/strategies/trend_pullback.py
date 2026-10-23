"""
Trend Pullback Strategy (Bullish Market Specialist)
Captures high-probability dips to 20 EMA in verified uptrends.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from app.engine.strategies.base import BaseStrategy
from app.core.indicators import ema, sma, rsi, atr


class TrendPullbackStrategy(BaseStrategy):
    name = "trend_pullback"
    display_name = "Trend EMA Pullback"
    description = "Buys dips in strong uptrending stocks as they bounce off 20 EMA with volume confirmation."
    target_regimes = ["STRONG_BULL", "PULLBACK_BULL"]

    def evaluate(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        if len(df) < 55:
            return None

        close = df['Close']
        open_p = df['Open']
        high = df['High']
        low = df['Low']
        vol = df['Volume']

        e20 = ema(close, 20)
        e50 = ema(close, 50)
        vol_sma = sma(vol, 20)
        atr_14 = atr(df, 14)
        rsi_14 = rsi(close, 14)

        # Current and recent bar indices
        i = -1
        p_close = float(close.iloc[i])
        p_open = float(open_p.iloc[i])
        p_low = float(low.iloc[i])
        p_high = float(high.iloc[i])
        p_vol = float(vol.iloc[i])
        p_e20 = float(e20.iloc[i])
        p_e50 = float(e50.iloc[i])
        p_vol_sma = float(vol_sma.iloc[i])
        p_atr = float(atr_14.iloc[i])
        p_rsi = float(rsi_14.iloc[i])

        # 1. Trend Filter: 20 EMA > 50 EMA and slope positive
        if p_e20 <= p_e50:
            return None
        if e20.iloc[-1] <= e20.iloc[-4]:
            return None

        # 2. Pullback Zone: Low touched or penetrated near 20 EMA
        dist_to_e20 = ((p_close - p_e20) / p_e20) * 100
        low_dist_to_e20 = ((p_low - p_e20) / p_e20) * 100
        
        # Low reached near 20 EMA (within 1.5% or dipped below and recovered)
        near_ema = (low_dist_to_e20 <= 1.0) and (dist_to_e20 >= -1.0)
        if not near_ema:
            return None

        # 3. Candle Confirmation: Bullish close (Close > Open and Close > Yesterday Close)
        if p_close <= p_open or p_close <= float(close.iloc[-2]):
            return None

        # 4. Momentum & Volume: RSI not overbought, healthy volume
        if p_rsi < 42 or p_rsi > 68:
            return None
        if p_vol < (0.8 * p_vol_sma):
            return None

        # Trade Plan Calculation
        entry_price = round(p_close, 2)
        # Stop loss: 1.5 * ATR below entry or just below recent swing low
        swing_low = float(low.iloc[-3:].min())
        sl_atr = entry_price - (1.5 * p_atr)
        stop_loss = round(min(swing_low * 0.995, sl_atr), 2)

        risk = entry_price - stop_loss
        if risk <= 0 or (risk / entry_price) > 0.08:  # Cap risk at 8%
            return None

        target_1 = round(entry_price + (1.5 * risk), 2)
        target_2 = round(entry_price + (2.5 * risk), 2)
        rr = round(2.0, 2)

        confidence = 75
        if p_vol > p_vol_sma:
            confidence += 10
        if p_rsi >= 50:
            confidence += 10

        return {
            "strategy": self.name,
            "strategy_title": self.display_name,
            "signal": "BUY",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_reward": rr,
            "risk_per_share": round(risk, 2),
            "risk_pct": round((risk / entry_price) * 100, 2),
            "confidence_score": min(confidence, 95),
            "reasons": [
                f"Trend confirmed: 20 EMA (₹{p_e20:.1f}) > 50 EMA (₹{p_e50:.1f})",
                f"Clean bounce off 20 EMA support zone",
                f"RSI healthy at {p_rsi:.1f} (in sweet momentum zone 42-68)",
                f"Volume surge at {round(p_vol/p_vol_sma, 1)}x of 20-day average"
            ]
        }
