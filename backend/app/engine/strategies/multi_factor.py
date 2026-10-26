"""Regime-aware, multi-factor swing breakout strategy.

This is a transparent technical setup score, not a probability of profit.
Live news context is attached by the screener and remains a separate review gate.
"""
from typing import Any, Dict, Optional

import pandas as pd

from app.core.indicators import adx, atr, ema, relative_strength, rsi, sma
from app.engine.strategies.base import BaseStrategy


class MultiFactorStrategy(BaseStrategy):
    name = "multi_factor"
    display_name = "Multi-Factor Confluence"
    description = "Scores trend, relative strength, momentum, volume, breakout quality, market context, and trade risk."
    target_regimes = ["STRONG_BULL", "PULLBACK_BULL", "SIDEWAYS_CHOPPY"]
    default_holding_days = 15

    def evaluate(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        if len(df) < 210 or not {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns):
            return None

        close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]
        e20, e50, e200 = ema(close, 20), ema(close, 50), ema(close, 200)
        atr14, rsi14, adx14 = atr(df, 14), rsi(close, 14), adx(df, 14)
        vol20 = sma(volume, 20)
        i = -1
        price = float(close.iloc[i])
        if not all(pd.notna(series.iloc[i]) for series in (e20, e50, e200, atr14, rsi14, adx14, vol20)):
            return None
        current_atr = float(atr14.iloc[i])
        if price <= 0 or current_atr <= 0 or float(vol20.iloc[i]) <= 0:
            return None

        score = 0
        reasons = []
        evidence = {}

        # Long-term structure and trend slope.
        aligned = price > float(e20.iloc[i]) > float(e50.iloc[i]) > float(e200.iloc[i])
        if aligned:
            score += 20
            reasons.append("Price and 20/50/200-day EMAs are aligned bullishly")
        elif price > float(e50.iloc[i]) > float(e200.iloc[i]):
            score += 12
            reasons.append("Price is above rising medium/long-term trend support")
        slope50 = (float(e50.iloc[i]) / float(e50.iloc[-6]) - 1) * 100 if float(e50.iloc[-6]) else 0
        if slope50 > 0:
            score += 8
            reasons.append(f"50-day EMA is rising ({slope50:.1f}% over 5 sessions)")

        # Relative performance must be positive and improving vs the benchmark.
        rs_63 = rs_126 = None
        if benchmark_df is not None and len(benchmark_df) >= 130:
            rs = relative_strength(close, benchmark_df["Close"], lookback=63)
            rs_63 = float(rs.iloc[-1])
            rs_126 = float(rs.iloc[-1] - rs.iloc[-21]) if len(rs) >= 22 else 0.0
            if rs_63 > 0:
                score += 15
                reasons.append(f"Mansfield relative-strength reading is positive versus Nifty ({rs_63:+.1f}%)")
            if rs_126 > 0:
                score += 5
                reasons.append("Relative strength is improving over the last month")
        evidence["relative_strength_63d"] = round(rs_63, 2) if rs_63 is not None else None
        evidence["relative_strength_change_21d"] = round(rs_126, 2) if rs_126 is not None else None

        # Momentum and participation.
        current_rsi = float(rsi14.iloc[i])
        current_adx = float(adx14.iloc[i])
        if 52 <= current_rsi <= 68:
            score += 10
            reasons.append(f"RSI momentum is constructive at {current_rsi:.1f}, without an overbought reading")
        elif 48 <= current_rsi < 52 or 68 < current_rsi <= 72:
            score += 5
        if current_adx >= 20:
            score += 10
            reasons.append(f"Trend strength is established (ADX {current_adx:.1f})")
        volume_ratio = float(volume.iloc[i]) / float(vol20.iloc[i])
        if volume_ratio >= 1.5:
            score += 12
            reasons.append(f"Breakout participation is strong ({volume_ratio:.1f}x 20-day volume)")
        elif volume_ratio >= 1.2:
            score += 8
            reasons.append(f"Volume confirms the move ({volume_ratio:.1f}x 20-day average)")

        # Require a close through a 20-session high and reject extended/chasing entries.
        prior_high = float(high.iloc[-21:-1].max())
        breakout_pct = (price / prior_high - 1) * 100 if prior_high else 0
        extension_atr = (price - float(e20.iloc[i])) / current_atr
        if price > prior_high:
            score += 15
            reasons.append(f"Close cleared the prior 20-session high (₹{prior_high:.2f})")
        elif price >= prior_high * 0.99:
            score += 8
            reasons.append("Price is within 1% of the prior 20-session high")
        if 0 <= extension_atr <= 2.0:
            score += 5
        elif extension_atr > 2.5:
            score -= 10
            reasons.append("Entry is extended more than 2.5 ATR above the 20-day EMA")

        # Benchmark context reduces score in a weak tape; it never overrides bad stock risk.
        market_context = "unknown"
        if benchmark_df is not None and len(benchmark_df) >= 50:
            bench_close = benchmark_df["Close"]
            bench20, bench50 = ema(bench_close, 20), ema(bench_close, 50)
            if float(bench_close.iloc[-1]) > float(bench20.iloc[-1]) > float(bench50.iloc[-1]):
                score += 10
                market_context = "supportive"
                reasons.append("Nifty is above its rising 20/50-day trend")
            elif float(bench_close.iloc[-1]) < float(bench50.iloc[-1]):
                score -= 12
                market_context = "weak"
                reasons.append("Nifty is below its 50-day EMA; long setups face a weak-market penalty")
            else:
                market_context = "mixed"
                score += 4
        evidence["market_context"] = market_context
        evidence["adx_14"] = round(current_adx, 1)
        evidence["rsi_14"] = round(current_rsi, 1)
        evidence["volume_ratio_20d"] = round(volume_ratio, 2)
        evidence["breakout_pct"] = round(breakout_pct, 2)
        evidence["extension_atr_from_ema20"] = round(extension_atr, 2)

        # Invalidate broken structure, illiquid inputs, and oversized/poor-R multiple risk.
        recent_swing_low = float(low.iloc[-10:].min())
        stop = min(recent_swing_low - 0.25 * current_atr, price - 1.25 * current_atr)
        risk = price - stop
        risk_pct = risk / price * 100
        if risk <= 0 or risk_pct > 8 or risk_pct < 0.8:
            return None
        target1, target2 = price + 2 * risk, price + 3 * risk
        resistance = float(high.iloc[-253:-1].max()) if len(high) > 253 else float(high.iloc[:-1].max())
        if resistance > price and (resistance - price) / risk < 1.8:
            return None
        if score < 68 or not (price > float(e50.iloc[i])) or current_rsi > 72 or volume_ratio < 1.0:
            return None

        return {
            "strategy": self.name,
            "strategy_title": self.display_name,
            "signal": "BUY",
            "entry_price": round(price, 2),
            "stop_loss": round(stop, 2),
            "target_1": round(target1, 2),
            "target_2": round(target2, 2),
            "risk_reward": 2.0,
            "risk_per_share": round(risk, 2),
            "risk_pct": round(risk_pct, 2),
            "confidence_score": min(max(int(score), 0), 100),
            "overall_score": min(max(int(score), 0), 100),
            "score_label": "technical confluence score; not a win probability",
            "reasons": reasons,
            "analysis": evidence,
            "review_required": True,
            "trade_status": "PENDING_NEWS_REVIEW",
        }
