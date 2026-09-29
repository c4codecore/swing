"""
Core module for swing trading system.
Provides data retrieval, technical indicators, market regime detection, screening engine, and utilities.
"""

from core.ohlcv_data import (
    fetch_price_history,
    fetch_price_histories_batch,
    get_nifty50_symbols,
    get_nifty100_symbols,
    get_all_nse_symbols,
)
from core.market_regime import (
    NIFTY_INDEX_SYMBOL,
    compute_daily_regime,
    get_market_regime,
    print_regime_banner,
)
from core.screener import screen_stocks
from core.utils import (
    round_tick,
    clean_ohlcv,
    remove_forming_candle,
    normalize_date,
)
from core.indicators import (
    ema,
    sma,
    wilder_rsi,
    true_range,
    average_true_range,
    macd,
    adx,
    supertrend,
    supertrend_is_green,
    bollinger_bands,
    keltner_channels,
)

__all__ = [
    "fetch_price_history",
    "fetch_price_histories_batch",
    "get_nifty50_symbols",
    "get_nifty100_symbols",
    "get_all_nse_symbols",
    "NIFTY_INDEX_SYMBOL",
    "compute_daily_regime",
    "get_market_regime",
    "print_regime_banner",
    "screen_stocks",
    "round_tick",
    "clean_ohlcv",
    "remove_forming_candle",
    "normalize_date",
    "ema",
    "sma",
    "wilder_rsi",
    "true_range",
    "average_true_range",
    "macd",
    "adx",
    "supertrend",
    "supertrend_is_green",
    "bollinger_bands",
    "keltner_channels",
]
