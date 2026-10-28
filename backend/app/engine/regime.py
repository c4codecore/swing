"""Market regime classification with explicit breadth data quality."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import Any, Dict

from app.core.config import DEFAULT_UNIVERSE, REGIME_COLORS
from app.core.data_fetcher import MarketDataUnavailable, fetch_benchmark, fetch_ohlcv
from app.core.indicators import atr, ema, rsi, sma
from app.engine.strategies import STRATEGY_REGISTRY

logger = logging.getLogger(__name__)


def calculate_market_breadth(sample_size: int = 15) -> Dict[str, Any]:
    sample_symbols = DEFAULT_UNIVERSE[:max(1, sample_size)]
    above_20 = above_50 = valid_count = 0
    failures = []

    def inspect(symbol):
        frame = fetch_ohlcv(symbol, period="6mo")
        if len(frame) < 50:
            raise MarketDataUnavailable(f"Insufficient history for {symbol}.")
        close = frame["Close"]
        return close.iloc[-1] > ema(close, 20).iloc[-1], close.iloc[-1] > ema(close, 50).iloc[-1]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(inspect, symbol): symbol for symbol in sample_symbols}
        for future in as_completed(futures):
            try:
                is_above_20, is_above_50 = future.result()
                valid_count += 1
                above_20 += bool(is_above_20)
                above_50 += bool(is_above_50)
            except Exception as exc:
                symbol = futures[future]
                failures.append(symbol)
                logger.warning("Breadth data unavailable for %s: %s", symbol, exc)

    return {
        "pct_above_20ema": round(above_20 / valid_count * 100, 1) if valid_count else None,
        "pct_above_50ema": round(above_50 / valid_count * 100, 1) if valid_count else None,
        "valid_symbols": valid_count,
        "requested_symbols": len(sample_symbols),
        "failed_symbols": failures,
        "data_status": "complete" if valid_count == len(sample_symbols) else "partial" if valid_count else "unavailable",
    }


def analyze_market_regime() -> Dict[str, Any]:
    nifty_df = fetch_benchmark(period="1y")
    if len(nifty_df) < 60:
        raise MarketDataUnavailable("Insufficient benchmark history to classify the market regime.")

    close = nifty_df["Close"]
    current_close = float(close.iloc[-1])
    e20 = float(ema(close, 20).iloc[-1])
    e50 = float(ema(close, 50).iloc[-1])
    e200 = float(ema(close, 200).iloc[-1]) if len(close) >= 200 else float(sma(close, min(len(close), 100)).iloc[-1])
    rsi_14 = float(rsi(close, 14).iloc[-1])
    atr_pct = float(atr(nifty_df, 14).iloc[-1] / current_close * 100)
    e20_series = ema(close, 20)
    e20_slope_5d = float((e20_series.iloc[-1] - e20_series.iloc[-5]) / e20_series.iloc[-5] * 100)
    dist_20ema = float((current_close - e20) / e20 * 100)
    breadth = calculate_market_breadth(sample_size=15)
    pct_above_50 = breadth["pct_above_50ema"]

    if rsi_14 < 30 and dist_20ema < -4.0:
        regime, title, color = "EXTREME_PANIC_OVERSOLD", "Heavy selling; prices are far below normal", REGIME_COLORS["EXTREME_PANIC_OVERSOLD"]
        description = "Prices have fallen sharply. A bounce may happen, but they can keep falling too. Extra care is needed."
        allowed = ["capitulation_reversal", "relative_strength"]
        action, exposure = "If you trade, keep the amount small and decide in advance how much loss you can accept.", 30
    elif current_close > e20 and e20 > e50 and current_close > e200 and e20_slope_5d > 0.3 and pct_above_50 is not None and pct_above_50 >= 60:
        regime, title, color = "STRONG_BULL", "Most tracked shares are rising", REGIME_COLORS["STRONG_BULL"]
        description = "Nifty and most tracked shares have been moving upward. A market-wide rise can still turn down."
        allowed = ["trend_pullback", "volatility_squeeze", "relative_strength"]
        action, exposure = "The market looks supportive, but plan an exit before buying and avoid using money you may need soon.", 100
    elif current_close >= e50 and current_close > e200 and rsi_14 >= 45:
        regime, title, color = "PULLBACK_BULL", "Longer trend is up; prices have dipped", REGIME_COLORS["PULLBACK_BULL"]
        description = "Nifty is still above its longer-term average, but prices have recently dipped. Wait to see if they turn back up."
        allowed = ["trend_pullback", "relative_strength"]
        action, exposure = "Be selective. Wait for the share price to steady before considering a trade.", 75
    elif current_close < e50 or e20_slope_5d < -0.8:
        regime, title, color = "BEARISH_CORRECTION", "The market is falling", REGIME_COLORS["BEARISH_CORRECTION"]
        description = "Nifty is below its recent average or falling quickly. New share purchases may carry extra risk."
        allowed = ["relative_strength", "capitulation_reversal"]
        action, exposure = "Consider keeping more money aside. If you trade, keep the amount small and set a clear exit price.", 25
    else:
        regime, title, color = "SIDEWAYS_CHOPPY", "The market has no clear direction", REGIME_COLORS["SIDEWAYS_CHOPPY"]
        description = "Nifty has not been moving clearly up or down. Sudden moves can reverse, so avoid rushing in."
        allowed = ["volatility_squeeze", "relative_strength"]
        action, exposure = "Wait for a clearer direction. If you trade, use only an amount you can afford to risk.", 50

    return {
        "regime": regime, "title": title, "color": color, "description": description,
        "recommended_action": action, "max_capital_exposure_pct": exposure,
        "allowed_strategies": [key for key in allowed if key in STRATEGY_REGISTRY],
        "data_status": "partial" if breadth["data_status"] != "complete" else "complete",
        "metrics": {
            "nifty_close": round(current_close, 2), "ema_20": round(e20, 2),
            "ema_50": round(e50, 2), "ema_200": round(e200, 2),
            "rsi_14": round(rsi_14, 1), "atr_pct": round(atr_pct, 2),
            "dist_20ema_pct": round(dist_20ema, 2),
            "breadth_above_50ema_pct": pct_above_50,
            "breadth_above_20ema_pct": breadth["pct_above_20ema"],
            "breadth_valid_symbols": breadth["valid_symbols"],
            "breadth_requested_symbols": breadth["requested_symbols"],
        },
    }
