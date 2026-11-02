"""
Backend Configuration and Constants
"""
from typing import List

# Legacy list retained for compatibility with older callers. Active stock scans
# must use get_screening_universe("nifty500") instead.
NIFTY50_UNIVERSE: List[str] = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BSE.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS",
    "BHARTIARTL.NS", "CIPLA.NS", "COALINDIA.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "ETERNAL.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS", "INFY.NS",
    "INDIGO.NS", "JSWSTEEL.NS", "JIOFIN.NS", "KOTAKBANK.NS", "LT.NS",
    "M&M.NS", "MARUTI.NS", "MAXHEALTH.NS", "NTPC.NS", "NESTLEIND.NS",
    "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SHRIRAMFIN.NS",
    "SBIN.NS", "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS", "TMPV.NS",
    "TATASTEEL.NS", "TECHM.NS", "TITAN.NS", "TRENT.NS", "ULTRACEMCO.NS"
]
DEFAULT_UNIVERSE: List[str] = NIFTY50_UNIVERSE  # Deprecated; do not use for stock scans.
SCREENING_UNIVERSE_MODE: str = "nifty500"  # nifty500 | nse_equities (legacy nifty50 redirects to nifty500)
INTRADAY_SCREENING_UNIVERSE_MODE: str = "nifty500"  # Broader liquid index universe for faster intraday scans.
USE_NIFTY50_ONLY: bool = False  # Deprecated; screening_universe redirects this to NIFTY 500.
USE_FULL_NSE_EQUITY_LIST: bool = False
NIFTY500_CONSTITUENTS_URL: str = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
UNIVERSE_CACHE_TTL_SECONDS: int = 24 * 60 * 60
DAILY_BATCH_SIZE: int = 100
DAILY_BATCH_RETRIES: int = 3
DAILY_BATCH_BACKOFF_SECONDS: float = 1.0
DAILY_BATCH_PAUSE_SECONDS: float = 0.15
INTRADAY_BATCH_SIZE: int = 50
MARKET_DATA_CACHE_MAX_ITEMS: int = 8192  # Full NSE screener needs room to retain all daily symbol frames.

BENCHMARK_INDEX: str = "^CRSLDX"  # Yahoo Finance symbol for the NIFTY 500 Index.
CACHE_TTL_SECONDS: int = 300   # 5 minutes cache for market data
DAILY_DATA_CACHE_TTL_SECONDS: int = 6 * 60 * 60  # Daily context changes slowly; live prices use 5-minute bars.
INTRADAY_DATA_TTL_SECONDS: int = 180  # Short cache for today's completed 5-minute candles
INTRADAY_PROFILE_PERIOD: str = "45d"  # Enough sessions for RVOL profiles with less history to download.
MIN_STOCK_PRICE: float = 50.0
SWING_MIN_AVG_TRADED_VALUE: float = 50_000_000.0  # ₹5 crore/day
INTRADAY_MIN_AVG_TRADED_VALUE: float = 100_000_000.0  # ₹10 crore/day
INCLUDE_SME_STOCKS: bool = False
CIRCUIT_BAND_PROXIMITY_PCT: float = 0.5
MIN_DAILY_BARS: int = 220
MAX_DAILY_BAR_AGE_TRADING_DAYS: int = 3
DAILY_AVG_TRADED_VALUE_LOOKBACK: int = 20
ASM_GSM_LIST_PATH: str | None = None  # Defaults to backend/data/asm_gsm.csv when present.

REGIME_COLORS = {
    "STRONG_BULL": "#10b981",       # Emerald Green
    "PULLBACK_BULL": "#06b6d4",     # Cyan
    "SIDEWAYS_CHOPPY": "#f59e0b",   # Amber
    "BEARISH_CORRECTION": "#f43f5e", # Rose Red
    "EXTREME_PANIC_OVERSOLD": "#8b5cf6" # Purple (Reversal Opportunity)
}

# Regime engine: indicator windows and classification thresholds.
REGIME_EMA20_PERIOD: int = 20
REGIME_EMA50_PERIOD: int = 50
REGIME_EMA200_PERIOD: int = 200
REGIME_RETURN_20D_PERIOD: int = 20
REGIME_RETURN_50D_PERIOD: int = 50
REGIME_RSI_PERIOD: int = 14
REGIME_BOLLINGER_PERIOD: int = 20
REGIME_BOLLINGER_STD_MULTIPLIER: float = 2.0
REGIME_BOLLINGER_STATS_WINDOW: int = 20
REGIME_EMA50_SLOPE_LOOKBACK: int = 5
REGIME_ATR_PERIOD: int = 14
REGIME_BREADTH_MIN_UNIVERSE: int = 200

REGIME_PANIC_RSI_MAX: float = 30.0
REGIME_PANIC_BOLLINGER_Z_MAX: float = -3.0
REGIME_BEARISH_RETURN_20D_MAX: float = 0.0
REGIME_BEARISH_RETURN_50D_MAX: float = 0.0
REGIME_STRONG_BULL_RETURN_20D_MIN: float = 0.0
REGIME_STRONG_BULL_RETURN_50D_MIN: float = 0.0
REGIME_STRONG_BULL_EMA50_SLOPE_MIN: float = 0.0
REGIME_STRONG_BULL_BREADTH_MIN: float = 60.0
REGIME_PULLBACK_RSI_MIN: float = 40.0
REGIME_PULLBACK_RSI_MAX: float = 50.0
REGIME_PULLBACK_EMA50_SLOPE_MIN: float = 0.0
REGIME_SIDEWAYS_EMA50_SLOPE_ABS_MAX: float = 0.25
REGIME_SIDEWAYS_BOLLINGER_WIDTH_STD_MULTIPLIER: float = 0.5
REGIME_SIDEWAYS_BREADTH_MIN: float = 45.0
REGIME_SIDEWAYS_BREADTH_MAX: float = 55.0

# Risk-scaling defaults, not tested optimum values.
REGIME_SIZING_WEIGHTS: dict[str, float] = {
    "EXTREME_PANIC_OVERSOLD": 0.30,
    "BEARISH_CORRECTION": 0.25,
    "STRONG_BULL": 1.00,
    "PULLBACK_BULL": 0.75,
    "SIDEWAYS_CHOPPY": 0.50,
}
REGIME_HYSTERESIS_DAYS: int = 2
REGIME_RISK_OFF_ENTRY_DAYS: int = 1
REGIME_RISK_OFF_EXIT_DAYS: int = 2
REGIME_BEARISH_EXIT_GUARD_ENABLED: bool = True
REGIME_BEARISH_EXIT_BREADTH_MIN: float = 40.0
REGIME_STRATEGY_GATING_ENABLED: bool = True
