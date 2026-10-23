"""
High-Speed Stock Screener Engine
Scans NSE universe against active strategies with regime matching.
"""
from typing import List, Dict, Any, Optional
import time
from concurrent.futures import ThreadPoolExecutor

from app.core.config import DEFAULT_UNIVERSE
from app.core.data_fetcher import fetch_ohlcv, fetch_benchmark
from app.engine.regime import analyze_market_regime
from app.engine.strategies import STRATEGY_REGISTRY, get_all_strategies


class ScreenerEngine:
    def __init__(self):
        self._last_run_time: float = 0.0
        self._cached_results: List[Dict[str, Any]] = []

    def scan_symbol(self, symbol: str, active_strategies: List[str], benchmark_df) -> List[Dict[str, Any]]:
        results = []
        try:
            df = fetch_ohlcv(symbol, period="1y")
            if len(df) < 60:
                return results

            cur_price = float(df['Close'].iloc[-1])
            prev_price = float(df['Close'].iloc[-2])
            change_pct = round(((cur_price - prev_price) / prev_price) * 100, 2)

            clean_symbol = symbol.replace(".NS", "")

            for strat_key in active_strategies:
                strategy = STRATEGY_REGISTRY.get(strat_key)
                if not strategy:
                    continue

                signal = strategy.evaluate(df, benchmark_df=benchmark_df)
                if signal:
                    signal["symbol"] = clean_symbol
                    signal["raw_symbol"] = symbol
                    signal["current_price"] = cur_price
                    signal["change_pct"] = change_pct
                    signal["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    results.append(signal)
        except Exception:
            pass
        return results

    def run_screener(self, 
                     symbols: Optional[List[str]] = None, 
                     strategy_filter: Optional[List[str]] = None,
                     force_refresh: bool = False) -> Dict[str, Any]:
        """
        Executes parallel screening of the stock universe.
        """
        now = time.time()
        # 3 minute cache
        if not force_refresh and self._cached_results and (now - self._last_run_time < 180):
            return {
                "count": len(self._cached_results),
                "signals": self._cached_results,
                "cached": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._last_run_time))
            }

        scan_symbols = symbols or DEFAULT_UNIVERSE
        active_strats = strategy_filter or list(STRATEGY_REGISTRY.keys())

        # Regime context
        regime_info = analyze_market_regime()
        cur_regime = regime_info["regime"]
        allowed_strats = regime_info.get("allowed_strategies", [])

        bench_df = fetch_benchmark(period="1y")

        all_signals: List[Dict[str, Any]] = []

        # Run in parallel threads for maximum speed
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self.scan_symbol, sym, active_strats, bench_df)
                for sym in scan_symbols
            ]
            for f in futures:
                res = f.result()
                if res:
                    for sig in res:
                        # Tag regime alignment
                        strat_name = sig["strategy"]
                        strat_obj = STRATEGY_REGISTRY.get(strat_name)
                        is_target_regime = cur_regime in getattr(strat_obj, "target_regimes", [])

                        if is_target_regime:
                            sig["regime_status"] = "OPTIMAL"
                            sig["regime_badge_color"] = "#10b981"
                        else:
                            sig["regime_status"] = "CAUTION"
                            sig["regime_badge_color"] = "#f59e0b"

                        all_signals.append(sig)

        # Sort by confidence and regime optimality
        all_signals.sort(key=lambda x: (x.get("regime_status") == "OPTIMAL", x.get("confidence_score", 0)), reverse=True)

        self._cached_results = all_signals
        self._last_run_time = now

        return {
            "count": len(all_signals),
            "signals": all_signals,
            "regime": regime_info,
            "cached": False,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        }


screener_engine = ScreenerEngine()
