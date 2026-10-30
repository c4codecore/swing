"""Parallel stock screener with request-scoped, thread-safe result caching."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import logging
import threading
import time
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from app.core import config
from app.core.data_fetcher import MarketDataUnavailable, fetch_benchmark, fetch_daily_batch, fetch_ohlcv
from app.core.screening_universe import get_screening_universe
from app.core.news_fetcher import fetch_news_context
from app.engine.filters import filter_tradable_symbols
from app.engine.regime import analyze_market_regime
from app.engine.strategies import STRATEGY_REGISTRY

logger = logging.getLogger(__name__)


class ScreenerEngine:
    def __init__(self):
        self._cache: Dict[Tuple[Tuple[str, ...], Tuple[str, ...]], Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def scan_symbol(self, symbol: str, active_strategies: List[str], benchmark_df,
                    force_refresh: bool = False, daily_df=None):
        df = daily_df if daily_df is not None else fetch_ohlcv(symbol, period="1y")
        if len(df) < 60:
            raise ValueError(f"Insufficient history for {symbol}.")
        cur_price = float(df["Close"].iloc[-1])
        prev_price = float(df["Close"].iloc[-2])
        change_pct = round((cur_price - prev_price) / prev_price * 100, 2)
        results = []
        for strat_key in active_strategies:
            signal = STRATEGY_REGISTRY[strat_key].evaluate(df, benchmark_df=benchmark_df)
            if signal:
                signal.update({
                    "symbol": symbol.replace(".NS", ""), "raw_symbol": symbol,
                    "current_price": cur_price, "change_pct": change_pct,
                    "signal_date": df.index[-1].strftime("%Y-%m-%d"),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                if strat_key == "multi_factor":
                    news = fetch_news_context(symbol, force_refresh=force_refresh)
                    signal["news"] = news
                    if news["status"] == "unavailable":
                        signal["trade_status"] = "REVIEW_NEWS_UNAVAILABLE"
                        signal["overall_score"] = min(signal["overall_score"], 60)
                    elif news["event_risk"]:
                        signal["trade_status"] = "AVOID_PENDING_EVENT_REVIEW"
                        signal["overall_score"] = min(signal["overall_score"], 50)
                    else:
                        signal["trade_status"] = "REVIEW_HEADLINES"
                    signal["review_required"] = True
                results.append(signal)
        return results

    def run_screener(self, symbols: Optional[List[str]] = None,
                     strategy_filter: Optional[List[str]] = None,
                     force_refresh: bool = False) -> Dict[str, Any]:
        scan_started = perf_counter()
        if symbols is None:
            selected_symbols, universe_metadata = get_screening_universe()
        else:
            selected_symbols, universe_metadata = list(symbols), {"mode": "explicit", "count": len(symbols)}
        scan_symbols = tuple(dict.fromkeys(selected_symbols))
        requested_strats = tuple(strategy_filter if strategy_filter is not None else STRATEGY_REGISTRY.keys())
        cache_key = (scan_symbols, requested_strats)
        with self._lock:
            now = time.time()
            cached = self._cache.get(cache_key)
            if not force_refresh and cached and now - cached[0] < 180:
                result = deepcopy(cached[1])
                result["cached"] = True
                return result

            regime_info = analyze_market_regime()
            if config.REGIME_STRATEGY_GATING_ENABLED:
                active_strats = tuple(
                    key for key in requested_strats
                    if key in STRATEGY_REGISTRY
                    and regime_info["confirmed_regime"] in STRATEGY_REGISTRY[key].target_regimes
                )
                strategies_skipped = [
                    {"id": key, "reason": f"Target regimes do not include confirmed regime {regime_info['confirmed_regime']}."}
                    for key in requested_strats if key in STRATEGY_REGISTRY and key not in active_strats
                ]
            else:
                active_strats = requested_strats
                strategies_skipped = []
            bench_df = fetch_benchmark(period="1y")
            all_signals: List[Dict[str, Any]] = []
            daily_frames, fetch_failures = fetch_daily_batch(scan_symbols, period="1y")
            normalized_fetch_failures = [
                {"symbol": item["symbol"].replace(".NS", ""), "reason": item["reason"]}
                for item in fetch_failures
            ]
            failures = list(normalized_fetch_failures)
            strategy_failures = []

            passed_symbols, filter_rejections = filter_tradable_symbols(
                scan_symbols, daily_frames, market="swing"
            )
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {
                    executor.submit(self.scan_symbol, symbol, list(active_strats), bench_df,
                                    force_refresh, daily_frames[symbol]): symbol
                    for symbol in passed_symbols
                }
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        signals = future.result()
                    except Exception as exc:
                        logger.warning("Screener strategy failure for %s: %s", symbol, exc)
                        failure = {"symbol": symbol.replace(".NS", ""), "reason": str(exc)[:160]}
                        failures.append(failure)
                        strategy_failures.append(failure)
                        continue
                    for signal in signals:
                        strategy = STRATEGY_REGISTRY[signal["strategy"]]
                        optimal = regime_info["regime"] in strategy.target_regimes
                        signal["regime_status"] = "OPTIMAL" if optimal else "CAUTION"
                        signal["regime_badge_color"] = "#10b981" if optimal else "#f59e0b"
                        all_signals.append(signal)

            all_signals.sort(key=lambda item: (item.get("regime_status") == "OPTIMAL", item.get("overall_score", item.get("confidence_score", 0))), reverse=True)
            succeeded = len(daily_frames)
            if not daily_frames:
                raise MarketDataUnavailable("Market data is unavailable for every requested scan symbol.")
            result = {
                "count": len(all_signals), "signals": all_signals, "regime": regime_info,
                "cached": False, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                "data_status": "complete" if not failures else "partial" if succeeded else "unavailable",
                "filter_rejections": filter_rejections,
                "strategy_gating_enabled": config.REGIME_STRATEGY_GATING_ENABLED,
                "strategies_run": list(active_strats),
                "strategies_skipped": strategies_skipped,
                "scan_summary": {"requested": len(scan_symbols), "succeeded": succeeded,
                                 "failed": len(normalized_fetch_failures),
                                 "failed_symbols": [item["symbol"] for item in normalized_fetch_failures],
                                 "strategy_failures": len(strategy_failures),
                                 "tradable_candidates": len(passed_symbols), "universe": universe_metadata,
                                 "duration_seconds": round(perf_counter() - scan_started, 3),
                                 "daily_fetch_method": "paced Yahoo Finance multi-symbol batches"},
                "errors": failures[:10],
            }
            self._cache[cache_key] = (now, deepcopy(result))
            return result


screener_engine = ScreenerEngine()
