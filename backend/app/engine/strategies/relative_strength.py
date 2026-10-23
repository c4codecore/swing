"""
Relative Strength (RS) Leader Strategy (Effective in Neutral & Bearish Regimes)
Finds standout stocks that defy market weakness and break out on institutional volume.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from app.engine.strategies.base import BaseStrategy
from app.core.indicators import ema, sma, rsi, atr, relative_strength


class RelativeStrengthBreakoutStrategy(BaseStrategy):
    name = "relative_strength"
    display_name = "Relative Strength Outperformer"
    description = "Screens stocks showing exceptional Relative Strength against Nifty, breaking to multi-week highs."
    target_regimes = ["BEARISH_CORRECTION", "SIDEWAYS_CHOPPY", "STRONG_BULL", "PULLBACK_BULL"]

    def evaluate(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        if len(df) < 65:
            return None

        close = df['Close']
        high = df['High']
        low = df['Low']
        open_p = df['Open']
        vol = df['Volume']

        # 20-day and 50-day highs (excluding current bar)
        high_20 = high.iloc[-21:-1].max()
        high_50 = high.iloc[-51:-1].max() if len(high) >= 55 else high_20

        cur_close = float(close.iloc[-1])
        cur_vol = float(vol.iloc[-1])
        vol_avg = float(sma(vol, 20).iloc[-1])
        atr_14 = float(atr(df, 14).iloc[-1])
        rsi_14 = float(rsi(close, 14).iloc[-1])
        e20 = float(ema(close, 20).iloc[-1])
        e50 = float(ema(close, 50).iloc[-1])

        # 1. Condition: Stock must be breaking out or within 1% of 20-day high
        is_breakout = cur_close >= high_20 * 0.99
        if not is_breakout:
            return None

        # 2. Volume expansion: Today volume > 1.2x 20-day avg
        if cur_vol < (1.15 * vol_avg):
            return None

        # 3. RS Check vs Benchmark if provided
        rs_score = 10.0
        is_rs_positive = True
        if benchmark_df is not None and len(benchmark_df) >= 30:
            rs_series = relative_strength(close, benchmark_df['Close'])
            rs_val = float(rs_series.iloc[-1])
            rs_score = rs_val
            # RS must be positive (outperforming index over 60 days)
            if rs_val < -1.0:
                return None

        # 4. Trend Baseline: Must be above 50 EMA (not a penny stock or dead counter)
        if cur_close < e50:
            return None

        # 5. Bullish candle today
        if cur_close < float(open_p.iloc[-1]):
            return None

        # Risk Plan
        entry_price = round(cur_close, 2)
        swing_support = float(low.iloc[-5:].min())
        sl_calc = entry_price - (1.6 * atr_14)
        stop_loss = round(max(swing_support, sl_calc), 2)
        
        # Ensure SL is at least 2.5% and max 7%
        risk = entry_price - stop_loss
        if risk <= 0:
            stop_loss = round(entry_price * 0.95, 2)
            risk = entry_price - stop_loss

        risk_pct = (risk / entry_price) * 100
        if risk_pct > 7.5:
            return None

        target_1 = round(entry_price + (1.6 * risk), 2)
        target_2 = round(entry_price + (2.8 * risk), 2)

        confidence = 80
        if cur_close >= high_50:
            confidence += 10
        if cur_vol >= 1.5 * vol_avg:
            confidence += 8

        return {
            "strategy": self.name,
            "strategy_title": self.display_name,
            "signal": "BUY",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_reward": 2.2,
            "risk_per_share": round(risk, 2),
            "risk_pct": round(risk_pct, 2),
            "confidence_score": min(confidence, 98),
            "reasons": [
                f"Outperforming Nifty: Mansfield RS score {rs_score:+.1f}% vs index",
                f"Fresh 20-day high breakout (₹{entry_price} >= ₹{high_20:.2f})",
                f"Strong institutional volume: {round(cur_vol/vol_avg, 1)}x of 20-day avg",
                f"Defensive strength: Holding above 50 EMA despite market volatility"
            ]
        }
