"""
Backend Configuration and Constants
"""
from typing import List

# Universe of top liquid NSE stocks (Nifty 50 + prominent swing trading stocks)
DEFAULT_UNIVERSE: List[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "INFY.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS", "SBIN.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS",
    "KOTAKBANK.NS", "NTPC.NS", "AXISBANK.NS", "TITAN.NS", "ONGC.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "POWERGRID.NS", "TATASTEEL.NS", "COALINDIA.NS",
    "BAJAJFINSV.NS", "ASIANPAINT.NS", "M&M.NS", "JSWSTEEL.NS", "ULTRACEMCO.NS",
    "TECHM.NS", "WIPRO.NS", "GRASIM.NS", "NESTLEIND.NS", "CIPLA.NS",
    "HINDALCO.NS", "DRREDDY.NS", "APOLLOHOSP.NS", "TRENT.NS", "BEL.NS",
    "HEROMOTOCO.NS", "INDUSINDBK.NS", "DIVISLAB.NS", "SBILIFE.NS", "EICHERMOT.NS",
    "BPCL.NS", "BRITANNIA.NS", "TATACONSUM.NS", "SHRIRAMFIN.NS", "HAL.NS"
]

BENCHMARK_INDEX: str = "^NSEI"  # Nifty 50 Index
CACHE_TTL_SECONDS: int = 300   # 5 minutes cache for market data

REGIME_COLORS = {
    "STRONG_BULL": "#10b981",       # Emerald Green
    "PULLBACK_BULL": "#06b6d4",     # Cyan
    "SIDEWAYS_CHOPPY": "#f59e0b",   # Amber
    "BEARISH_CORRECTION": "#f43f5e", # Rose Red
    "EXTREME_PANIC_OVERSOLD": "#8b5cf6" # Purple (Reversal Opportunity)
}
