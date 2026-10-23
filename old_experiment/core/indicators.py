"""
Shared Technical Indicators Library for Swing Trading System.
============================================================

This module provides high-performance, mathematically accurate implementations of
core technical indicators (EMA, SMA, Wilder's RSI, ATR, MACD, ADX, SuperTrend,
Bollinger Bands, Keltner Channels).

Knowledge & Design Notes:
-------------------------
1. Vectorization: Computations use Pandas .ewm() and NumPy vectorized operations
   instead of slow Python for-loops wherever possible.
2. Wilder's Smoothing: Indicators like RSI, ATR, and ADX use Wilder's exponential smoothing
   (alpha = 1 / period), which matches TradingView, Zerodha Kite, and official formulas.
3. Zero-Division Safety: Ratios (e.g. Gain/Loss in RSI, DI sum in ADX) handle zero values safely
   to prevent ZeroDivisionError and NaN propagation.
"""

import pandas as pd
import numpy as np


def ema(series, period, min_periods=None):
    """
    Exponential Moving Average (EMA).
    
    Formula:
        EMA_today = (Price_today * Multiplier) + (EMA_yesterday * (1 - Multiplier))
        where Multiplier (alpha) = 2 / (period + 1)
        
    Knowledge:
        - Giving adjust=False ensures standard recursive EMA calculation used in financial markets.
        - Reacts faster to recent price changes than SMA (Simple Moving Average).
        - Used for dynamic trend direction (e.g. 20 EMA short-term pullback, 50 EMA medium trend, 200 EMA long-term trend).
    """
    return series.ewm(span=period, adjust=False, min_periods=min_periods).mean()


def sma(series, period, min_periods=None):
    """
    Simple Moving Average (SMA).
    
    Formula:
        SMA = Sum(Price over N days) / N
        
    Knowledge:
        - Gives equal weight to all days in the lookback window.
        - Often used for long-term institutional benchmarks (e.g. 200-day SMA for bull/bear market definition).
    """
    return series.rolling(window=period, min_periods=min_periods).mean()


def wilder_rsi(series, period=14, min_periods=None):
    """
    Wilder's Relative Strength Index (RSI).
    
    Formula:
        RS = Smoothed_Gain / Smoothed_Loss
        RSI = 100 - (100 / (1 + RS))
        where smoothing uses Wilder's method: alpha = 1 / period (span = 2 * period - 1).
        
    Knowledge:
        - Oscillates between 0 and 100.
        - Standard Momentum interpretation:
            * > 70: Overbought (momentum strong, but risk of exhaustion).
            * < 30: Oversold (selling climax, but don't catch falling knives).
            * 50-65: Bullish swing zone (momentum active without being overly stretched).
        - .replace(0, np.nan) prevents ZeroDivisionError when there are no losing candles.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    min_p = min_periods if min_periods is not None else period
    # Wilder smoothing: alpha = 1 / period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=min_p).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=min_p).mean()
    
    # Safe division avoiding divide by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    return rsi_series


def true_range(price_data):
    """
    True Range (TR) calculation.
    
    Formula:
        TR = Max(
            High - Low,                  # Today's entire candle range
            Abs(High - Previous_Close),  # Accounts for overnight gap-up
            Abs(Low - Previous_Close)    # Accounts for overnight gap-down
        )
        
    Knowledge:
        - Plain (High - Low) misses overnight gap risk. True Range accurately captures full price volatility.
    """
    high = price_data["High"]
    low = price_data["Low"]
    prev_close = price_data["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr


def average_true_range(price_data, period=14, min_periods=None):
    """
    Average True Range (ATR) with Wilder Smoothing.
    
    Knowledge:
        - Measures market volatility in absolute rupee (currency) terms, not percentage.
        - Essential for:
            1. Volatility-adjusted Stop Loss (e.g. Stop = Entry - 1.5 * ATR).
            2. Anti-chasing extension filters (e.g. skip if Price is > 1.5 ATR away from 20 EMA).
            3. Position sizing: High ATR = smaller position size to keep total rupee risk constant.
    """
    tr = true_range(price_data)
    min_p = min_periods if min_periods is not None else period
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=min_p).mean()


def macd(series, fast=12, slow=26, signal=9):
    """
    Moving Average Convergence Divergence (MACD).
    
    Formula:
        MACD Line = EMA(Close, fast=12) - EMA(Close, slow=26)
        Signal Line = EMA(MACD Line, signal=9)
        Histogram = MACD Line - Signal Line
        
    Knowledge:
        - MACD Line above Signal Line (Histogram > 0) = Bullish momentum.
        - MACD Line crossing above Signal Line from below 0 = High probability reversal/expansion setup.
    """
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def adx(price_data, period=14, min_periods=None):
    """
    Average Directional Index (ADX) along with +DI and -DI.
    
    Formula:
        +DM (Directional Movement) = Today's High - Yesterday's High (if positive and > -DM)
        -DM = Yesterday's Low - Today's Low (if positive and > +DM)
        +DI = 100 * WilderSmooth(+DM) / ATR
        -DI = 100 * WilderSmooth(-DM) / ATR
        DX = 100 * Abs(+DI - -DI) / (+DI + -DI)
        ADX = WilderSmooth(DX)
        
    Knowledge:
        - ADX measures TREND STRENGTH regardless of direction (0 to 100).
        - ADX < 20: Weak / Choppy / Sideways market (avoid trend-following breakouts).
        - ADX > 20 or 25: Strong trending market (favorable for swing breakout & trend pullback).
        - +DI > -DI: Bullish dominance; -DI > +DI: Bearish dominance.
    """
    high = price_data["High"]
    low = price_data["Low"]
    
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    min_p = min_periods if min_periods is not None else period
    atr = average_true_range(price_data, period, min_periods=min_p)
    safe_atr = atr.replace(0, np.nan)
    
    plus_di = 100 * pd.Series(plus_dm, index=price_data.index).ewm(alpha=1 / period, adjust=False, min_periods=min_p).mean() / safe_atr
    minus_di = 100 * pd.Series(minus_dm, index=price_data.index).ewm(alpha=1 / period, adjust=False, min_periods=min_p).mean() / safe_atr
    
    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx_series = dx.ewm(alpha=1 / period, adjust=False, min_periods=min_p).mean()
    return adx_series, plus_di, minus_di


def supertrend(price_data, period=10, multiplier=3.0):
    """
    SuperTrend Indicator.
    
    Returns:
        (super_trend_series, trend_direction_series)
        trend_direction: +1 for Bullish (Green), -1 for Bearish (Red).
        
    Knowledge:
        - SuperTrend acts as a dynamic trailing stop based on ATR distance from median price (H+L)/2.
        - Ratchet Rule:
            In an uptrend (trend == 1), Lower Band is only allowed to move UP, never down.
            In a downtrend (trend == -1), Upper Band is only allowed to move DOWN, never up.
        - If Close crosses above Upper Band -> Trend flips to +1.
        - If Close crosses below Lower Band -> Trend flips to -1.
        - Implemented with writable NumPy arrays (copy=True) for ultra-fast loop execution.
    """
    atr = average_true_range(price_data, period)
    hl2 = (price_data["High"] + price_data["Low"]) / 2
    upper_band = (hl2 + (multiplier * atr)).to_numpy(dtype=np.float64, copy=True)
    lower_band = (hl2 - (multiplier * atr)).to_numpy(dtype=np.float64, copy=True)
    close = price_data["Close"].to_numpy(dtype=np.float64)

    n = len(price_data)
    trend = np.ones(n, dtype=np.int32)
    super_trend = np.zeros(n, dtype=np.float64)

    for i in range(1, n):
        if close[i] > upper_band[i - 1]:
            trend[i] = 1
        elif close[i] < lower_band[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
            # Ratchet rule: Trailing stop must not loosen against the trend
            if trend[i] == 1 and lower_band[i] < lower_band[i - 1]:
                lower_band[i] = lower_band[i - 1]
            if trend[i] == -1 and upper_band[i] > upper_band[i - 1]:
                upper_band[i] = upper_band[i - 1]

        super_trend[i] = lower_band[i] if trend[i] == 1 else upper_band[i]

    return pd.Series(super_trend, index=price_data.index), pd.Series(trend, index=price_data.index)


def supertrend_is_green(price_data, period=10, multiplier=3.0):
    """Helper: Returns True if the latest completed candle is in a SuperTrend Buy (Bullish) state."""
    _, trend = supertrend(price_data, period, multiplier)
    return bool(trend.iloc[-1] == 1)


def bollinger_bands(series, period=20, num_std=2.0, min_periods=None):
    """
    Bollinger Bands (Upper, Middle, Lower).
    
    Formula:
        Middle Band = 20-period SMA
        Upper Band = Middle Band + (num_std * Standard Deviation)
        Lower Band = Middle Band - (num_std * Standard Deviation)
        
    Knowledge:
        - Statistically, ~95% of price action stays within 2 Standard Deviations.
        - Bandwidth = (Upper - Lower) / Middle * 100.
        - When Bandwidth contracts to multi-month lows (Volatility Squeeze), an explosive breakout is imminent.
    """
    min_p = min_periods if min_periods is not None else period
    rolling = series.rolling(window=period, min_periods=min_p)
    mid = rolling.mean()
    std = rolling.std()
    upper = mid + (std * num_std)
    lower = mid - (std * num_std)
    return upper, mid, lower


def keltner_channels(price_data, ema_period=20, atr_period=10, atr_multiplier=1.5):
    """
    Keltner Channels (Upper, Middle, Lower).
    
    Formula:
        Middle Line = 20 EMA of Close
        Upper Channel = 20 EMA + (atr_multiplier * ATR)
        Lower Channel = 20 EMA - (atr_multiplier * ATR)
        
    Knowledge:
        - Unlike Bollinger Bands (which use Standard Deviation), Keltner Channels use ATR.
        - TTM Squeeze Strategy: When Bollinger Bands move inside Keltner Channels, market is in a squeeze.
    """
    mid = ema(price_data["Close"], ema_period)
    atr = average_true_range(price_data, atr_period)
    upper = mid + (atr_multiplier * atr)
    lower = mid - (atr_multiplier * atr)
    return upper, mid, lower
