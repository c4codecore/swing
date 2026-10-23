"""
Volatility Squeeze Breakout Strategy (Ideal for Sideways & Pre-Breakout Markets)
Detects energy compression in Bollinger Bands and catches high-velocity explosive expansions.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from app.engine.strategies.base import BaseStrategy
from app.core.indicators import ema, sma, atr, bollinger_bands, macd


class VolatilitySqueezeStrategy(BaseStrategy):
    name = "volatility_squeeze"
    display_name = "Volatility Squeeze Expansion"
    description = "Identifies tight consolidation ranges (squeeze) and enters as volatility expands upwards."
    target_regimes = ["SIDEWAYS_CHOPPY", "STRONG_BULL", "PULLBACK_BULL"]

    def evaluate(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        if len(df) < 50:
            return None

        close = df['Close']
        high = df['High']
        low = df['Low']
        vol = df['Volume']

        bb_up, bb_mid, bb_low, bb_width = bollinger_bands(close, period=20, num_std=2.0)
        atr_14 = atr(df, 14)
        vol_avg = sma(vol, 20)
        _, _, macd_hist = macd(close)

        cur_close = float(close.iloc[-1])
        cur_open = float(df['Open'].iloc[-1])
        cur_vol = float(vol.iloc[-1])
        cur_vol_avg = float(vol_avg.iloc[-1])
        cur_bb_up = float(bb_up.iloc[-1])
        cur_bb_mid = float(bb_mid.iloc[-1])
        cur_atr = float(atr_14.iloc[-1])
        
        # Squeeze detection: was bandwidth at multi-week low in recent 5 days?
        recent_bandwidth_min = float(bb_width.iloc[-6:-1].min())
        cur_bandwidth = float(bb_width.iloc[-1])

        # Squeeze release condition:
        # Bandwidth was tight (< 0.10 or expanding from recent low), price breaks out above upper BB
        is_breakout = cur_close >= cur_bb_up * 0.995 and cur_close > cur_open
        is_expanding = cur_bandwidth > recent_bandwidth_min * 1.05
        is_momentum_green = float(macd_hist.iloc[-1]) > 0 and float(macd_hist.iloc[-1]) > float(macd_hist.iloc[-2])

        if not (is_breakout and is_expanding and is_momentum_green):
            return None

        if cur_vol < (1.1 * cur_vol_avg):
            return None

        entry_price = round(cur_close, 2)
        stop_loss = round(cur_bb_mid, 2)  # Middle BB (20 SMA) acts as trailing stop
        risk = entry_price - stop_loss

        risk_pct = (risk / entry_price) * 100
        if risk_pct > 7.0 or risk <= 0:
            stop_loss = round(entry_price * 0.95, 2)
            risk = entry_price - stop_loss
            risk_pct = 5.0

        target_1 = round(entry_price + (1.5 * risk), 2)
        target_2 = round(entry_price + (2.5 * risk), 2)

        return {
            "strategy": self.name,
            "strategy_title": self.display_name,
            "signal": "BUY",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_reward": 2.0,
            "risk_per_share": round(risk, 2),
            "risk_pct": round(risk_pct, 2),
            "confidence_score": 85,
            "reasons": [
                f"Bollinger Band squeeze released with bandwidth expanding to {cur_bandwidth:.3f}",
                f"Close (₹{entry_price}) breaking above upper volatility band (₹{cur_bb_up:.1f})",
                f"MACD histogram accelerating positive momentum",
                f"Volume expansion: {round(cur_vol/cur_vol_avg, 1)}x of 20-day average"
            ]
        }
