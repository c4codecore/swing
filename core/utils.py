"""
Shared Utility Functions for Swing Trading System.
=================================================

Provides essential helpers for:
1. NSE Tick Size price rounding (preventing order rejection by brokers).
2. Clean OHLCV dataframe preparation (MultiIndex flattening, type coercion, deduplication).
3. Intraday Forming-Candle handling (preventing premature signals & lookahead bias).
4. Timezone normalization (preventing timestamp mismatch in pandas merge/join).
"""

import pandas as pd
import numpy as np
from datetime import datetime, time as dtime, timedelta, timezone

# NSE cash equity standard tick size is 0.05 INR (5 paise).
DEFAULT_TICK_SIZE = 0.05

# NSE regular equity trading session closes at 15:30 IST.
DEFAULT_MARKET_CLOSE = dtime(15, 30)

# Indian Standard Time (UTC + 5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def round_tick(price, tick=DEFAULT_TICK_SIZE):
    """
    Round price to the nearest exchange tick size (default: 0.05 for NSE).
    
    Knowledge:
        - Indian exchanges (NSE & BSE) mandate prices to be multiples of the tick size (₹0.05).
        - If an order is sent with price ₹524.37 to broker APIs (IIFL, Zerodha, Upstox),
          the broker or exchange RMS will reject the order.
        - Rounding: 524.37 / 0.05 = 10487.4 -> round(10487) * 0.05 = ₹524.35.
    """
    if price is None or pd.isna(price):
        return None
    try:
        return round(round(float(price) / tick) * tick, 2)
    except (ValueError, TypeError):
        return None


def clean_ohlcv(df, required_columns=("Open", "High", "Low", "Close", "Volume")):
    """
    Standardize OHLCV dataframe for reliable indicator calculation.
    
    Knowledge & Steps:
        1. yfinance MultiIndex Flattening: Recent versions of yfinance return 2-level MultiIndex
           columns like ('Close', 'RELIANCE.NS'). This extracts the first level ('Close').
        2. Column Validation: Ensures all 5 essential columns exist.
        3. Numeric Coercion: Converts string or object types to float64, converting corrupted data to NaN.
        4. Outlier & NaN Cleaning: Drops missing rows and infinite values.
        5. Deduplication: Removes duplicate date index entries keeping the latest bar.
        6. Timezone Normalization: Strips tzinfo to ensure tz-naive datetime index.
    """
    if df is None or df.empty:
        return None

    data = df.copy()

    # Flatten MultiIndex columns (e.g. from yfinance download)
    if isinstance(data.columns, pd.MultiIndex):
        level_0 = data.columns.get_level_values(0)
        if all(col in level_0 for col in required_columns):
            data.columns = level_0
        else:
            return None

    # Check required columns
    for col in required_columns:
        if col not in data.columns:
            return None

    data = data[list(required_columns)].copy()

    # Numeric conversion
    for col in required_columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=list(required_columns))
    if data.empty:
        return None

    # Remove duplicate timestamps and sort chronologically
    data = data[~data.index.duplicated(keep="last")].sort_index()

    # Normalize timezone to tz-naive
    try:
        if getattr(data.index, "tz", None) is not None:
            data.index = data.index.tz_localize(None)
    except Exception:
        pass

    return data


def remove_forming_candle(data, market_close_time=DEFAULT_MARKET_CLOSE):
    """
    Remove today's daily candle if the market is currently open and the candle is incomplete.
    
    Knowledge (Why this is critical for swing trading):
        - Daily swing trading signals rely on COMPLETED daily candles (where Close is confirmed).
        - If a screener runs at 11:00 AM, today's candle is still forming:
          * The "Close" is just the instantaneous LTP (Last Traded Price).
          * The "Volume" is only partial volume, which will falsely fail or pass volume filters.
        - Backtesting Safety: Historical candles from past dates are NOT removed.
    """
    if data is None or data.empty:
        return data

    last_timestamp = data.index[-1]
    if not hasattr(last_timestamp, "date"):
        return data

    # Determine 'today' in the context of Indian Standard Time
    try:
        if getattr(last_timestamp, "tz", None) is not None:
            now_dt = pd.Timestamp.now(tz=last_timestamp.tz)
        else:
            now_dt = datetime.now(IST)
    except Exception:
        now_dt = datetime.now()

    last_date = last_timestamp.date()
    today_date = now_dt.date()

    # Only filter if the last candle is dated today
    if last_date == today_date:
        current_time = now_dt.time()
        # Before market close, today's candle is still forming
        if current_time < market_close_time:
            return data.iloc[:-1]

    return data


def normalize_date(value):
    """
    Normalize any datetime / timestamp object to a tz-naive pandas Timestamp.
    
    Knowledge:
        - Prevents dtype mismatch errors during pd.merge_asof or date indexing.
    """
    d = pd.Timestamp(value)
    try:
        if d.tzinfo is not None:
            d = d.tz_localize(None)
    except Exception:
        pass
    return d
