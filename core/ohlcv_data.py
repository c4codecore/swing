"""
Shared Data Layer for Price and Universe Retrieval.
===================================================

Knowledge & Architecture:
-------------------------
1. Stock Universes:
   - Fetches official active constituents of Nifty 50 and Nifty 100 directly from NSE India archives.
   - Yahoo Finance requires the '.NS' suffix for National Stock Exchange of India tickers (e.g. 'RELIANCE.NS').
2. Network I/O Parallelization:
   - Downloading 100 stocks sequentially takes ~40-60 seconds due to network latency.
   - Using Python's `concurrent.futures.ThreadPoolExecutor` allows 10 simultaneous downloads,
     slashing download time to ~5-8 seconds without CPU overload.
3. In-Memory TTL Session Caching:
   - Avoids hammering Yahoo Finance with redundant requests when backtesting or screening
     multiple strategies in the same session.
"""

import os
import time
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
import yfinance as yf
from core.utils import clean_ohlcv

# Official NSE India CSV Archives
NIFTY100_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv"
NIFTY50_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
ALL_NSE_EQUITY_CSV_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

# Fallback list used if NSE website blocks live scraping or is temporarily offline
NIFTY50_FALLBACK = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS", "BHARTIARTL.NS",
    "CIPLA.NS", "COALINDIA.NS", "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS",
    "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
    "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS", "INDUSINDBK.NS", "INFY.NS",
    "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS", "M&M.NS", "MARUTI.NS",
    "NESTLEIND.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS",
    "SBILIFE.NS", "SBIN.NS", "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS",
    "TATAMOTORS.NS", "TATASTEEL.NS", "TECHM.NS", "TITAN.NS", "TRENT.NS",
    "ULTRACEMCO.NS", "WIPRO.NS", "TMPV.NS",
]

# In-memory session cache: {(symbol, period): (timestamp, df)}
_MEMORY_CACHE = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes in-memory cache TTL


def fetch_nse_symbol_list(csv_url, index_label, fallback_list):
    """
    Fetch official ticker list from NSE India CSV archives with browser emulation headers.
    
    Knowledge:
        - NSE India blocks requests with default Python-requests user-agents (returns HTTP 403).
        - We emulate a real Chrome browser session and visit nseindia.com first to acquire session cookies.
    """
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/live-equity-market",
    }
    try:
        with requests.Session() as session:
            session.headers.update(headers)
            session.get("https://www.nseindia.com", timeout=5)
            response = session.get(csv_url, timeout=10)
            response.raise_for_status()
            listing_df = pd.read_csv(StringIO(response.text))
            col = "Symbol" if "Symbol" in listing_df.columns else "SYMBOL"
            symbols = [f"{symbol.strip()}.NS" for symbol in listing_df[col]]
            print(f"Fetched {len(symbols)} tickers live from NSE {index_label} list.\n")
            return symbols
    except Exception as e:
        print(f"[!] Could not fetch live {index_label} list from NSE ({e}).")
        print("    Falling back to hardcoded list.\n")
        return fallback_list


def get_nifty100_symbols():
    """Returns tickers for Nifty 100 universe (Large + Mid Cap leaders)."""
    return fetch_nse_symbol_list(NIFTY100_CSV_URL, "Nifty 100", NIFTY50_FALLBACK)


def get_nifty50_symbols():
    """Returns tickers for Nifty 50 universe (Blue-chip Large Caps)."""
    return fetch_nse_symbol_list(NIFTY50_CSV_URL, "Nifty 50", NIFTY50_FALLBACK)


def get_all_nse_symbols(limit=None):
    """Returns all active equity tickers listed on the National Stock Exchange."""
    symbols = fetch_nse_symbol_list(ALL_NSE_EQUITY_CSV_URL, "All NSE Equity", [])
    if limit:
        symbols = symbols[:limit]
    return symbols


def fetch_price_history(symbol, period="3y", use_cache=True):
    """
    Downloads historical daily OHLCV data for a ticker using yfinance.
    
    Knowledge:
        - Cleans data through clean_ohlcv() to guarantee timezone-naive, numeric columns.
        - Checks minimum length (55 bars) so short-lived IPOs don't cause index errors.
        - Uses fast memory cache to eliminate redundant downloads within 5 minutes.
    """
    cache_key = (symbol, period)
    now = time.time()
    if use_cache and cache_key in _MEMORY_CACHE:
        cache_time, cached_df = _MEMORY_CACHE[cache_key]
        if now - cache_time < _CACHE_TTL_SECONDS:
            return cached_df.copy()

    try:
        raw_data = yf.download(symbol, period=period, interval="1d", progress=False, threads=False)
        cleaned = clean_ohlcv(raw_data)
        if cleaned is None or len(cleaned) < 55:
            return None

        if use_cache:
            _MEMORY_CACHE[cache_key] = (now, cleaned)
        return cleaned.copy()
    except Exception as e:
        print(f"  [!] Could not fetch {symbol}: {e}")
        return None


def fetch_price_histories_batch(symbols, period="3y", max_workers=10, show_progress=True):
    """
    Downloads historical data for multiple symbols concurrently using a ThreadPoolExecutor.
    
    Knowledge:
        - Parallel I/O: Since downloading is network bound, multiple worker threads wait
          for Yahoo Finance responses simultaneously, speeding up data loading by 5x-10x.
    """
    histories = {}
    total = len(symbols)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_price_history, symbol, period): symbol for symbol in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            completed += 1
            try:
                data = future.result()
                if data is not None and len(data) >= 55:
                    histories[symbol] = data
            except Exception:
                pass

            if show_progress:
                print(f"  Downloaded {completed}/{total} stocks ...", end="\r")

    if show_progress:
        print(f"\nUsable price histories fetched for {len(histories)} of {total} stocks.\n")

    return histories
