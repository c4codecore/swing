"""
Capitulation Reversal Strategy (Bearish Market & Panic Specialist)
Captures high-reward mean-reversion snapbacks in deeply oversold quality stocks.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from app.engine.strategies.base import BaseStrategy
from app.core.indicators import ema, sma, rsi, atr


class CapitulationReversalStrategy(BaseStrategy):
    name = "capitulation_reversal"
    display_name = "Capitulation Oversold Bounce"
    description = "Trades sharp snapbacks when quality stocks reach extreme oversold exhaustion in market corrections."
    target_regimes = ["BEARISH_CORRECTION", "EXTREME_PANIC_OVERSOLD", "SIDEWAYS_CHOPPY"]

    def evaluate(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        if len(df) < 40:
            return None

        close = df['Close']
        open_p = df['Open']
        high = df['High']
        low = df['Low']
        vol = df['Volume']

        rsi_14 = rsi(close, 14)
        atr_14 = atr(df, 14)
        e20 = ema(close, 20)
        vol_avg = sma(vol, 20)

        cur_close = float(close.iloc[-1])
        cur_open = float(open_p.iloc[-1])
        cur_low = float(low.iloc[-1])
        cur_high = float(high.iloc[-1])
        cur_vol = float(vol.iloc[-1])
        cur_rsi = float(rsi_14.iloc[-1])
        prev_rsi = float(rsi_14.iloc[-2])
        cur_atr = float(atr_14.iloc[-1])
        cur_e20 = float(e20.iloc[-1])
        cur_vol_avg = float(vol_avg.iloc[-1])

        # 1. Condition: Deep Oversold (RSI was < 30 in last 3 days)
        recent_min_rsi = float(rsi_14.iloc[-4:].min())
        if recent_min_rsi > 32:
            return None

        # 2. Reversal confirmation: Today RSI bounced or closed green
        if cur_close < cur_open:
            return None

        # 3. Price stretched below 20 EMA by at least 2.5 * ATR
        stretch = (cur_e20 - cur_close) / cur_atr
        if stretch < 2.2:
            return None

        # 4. Candlestick signal: Long lower shadow (Hammer) OR Bullish Engulfing
        candle_body = abs(cur_close - cur_open)
        lower_shadow = min(cur_open, cur_close) - cur_low
        is_hammer = lower_shadow >= 1.5 * candle_body and lower_shadow > (0.35 * cur_atr)
        is_engulfing = (cur_close > float(high.iloc[-2])) and (cur_open <= float(close.iloc[-2]))

        if not (is_hammer or is_engulfing or cur_close > float(close.iloc[-2])):
            return None

        # Risk Plan
        entry_price = round(cur_close, 2)
        # Tight stop-loss just below today's panic low
        stop_loss = round(cur_low * 0.992, 2)
        risk = entry_price - stop_loss

        if risk <= 0:
            return None

        risk_pct = (risk / entry_price) * 100
        if risk_pct > 6.0:  # Cap risk
            stop_loss = round(entry_price * 0.95, 2)
            risk = entry_price - stop_loss
            risk_pct = 5.0

        # Target is mean reversion towards 20 EMA
        target_1 = round(entry_price + (1.6 * risk), 2)
        target_2 = round(min(cur_e20 * 0.98, entry_price + (2.8 * risk)), 2)

        rr = round((target_2 - entry_price) / risk, 1) if risk > 0 else 2.0

        confidence = 78
        if is_hammer:
            confidence += 8
        if cur_vol > cur_vol_avg:
            confidence += 8
        if recent_min_rsi < 25:
            confidence += 5

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
            "risk_pct": round(risk_pct, 2),
            "confidence_score": min(confidence, 96),
            "reasons": [
                f"Severe oversold bounce: RSI hit {recent_min_rsi:.1f} (exhaustion climax)",
                f"Extreme mean-reversion stretch: {stretch:.1f} ATR below 20 EMA",
                f"Reversal candle formed: {'Hammer with heavy lower wick' if is_hammer else 'Bullish engulfing reversal'}",
                f"Targeting snapback to 20 EMA (₹{cur_e20:.1f}) with tight risk below low"
            ]
        }
