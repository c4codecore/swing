"""
Core Vectorized Technical Indicators for Quantitative Swing Trading
"""
import pandas as pd
import numpy as np


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average using pandas ewm."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=1).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder's Smoothed Relative Strength Index (TradingView standard).
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # First value is simple mean
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_vals = 100.0 - (100.0 / (1.0 + rs))
    return rsi_vals.fillna(50.0)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range using Wilder's smoothing.
    """
    high = df['High']
    low = df['Low']
    prev_close = df['Close'].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    return atr_series


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Moving Average Convergence Divergence.
    Returns: macd_line, signal_line, histogram
    """
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    """
    Bollinger Bands: upper, middle, lower, bandwidth
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    return upper, middle, lower, bandwidth


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average Directional Index (Trend Strength).
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    
    up_move = high - prev_high
    down_move = prev_low - low
    
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr = atr(df, period)
    
    pos_di = 100 * pd.Series(pos_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / tr.replace(0, np.nan)
    neg_di = 100 * pd.Series(neg_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / tr.replace(0, np.nan)
    
    dx = (pos_di - neg_di).abs() / (pos_di + neg_di).replace(0, np.nan) * 100
    adx_series = dx.ewm(alpha=1.0/period, adjust=False).mean()
    return adx_series.fillna(20.0)


def relative_strength(stock_close: pd.Series, benchmark_close: pd.Series, lookback: int = 63) -> pd.Series:
    """
    Mansfield-style Relative Strength ratio vs Benchmark.
    lookback = 63 (~3 months trading days).
    A rising RS line indicates the stock is outperforming the index.
    """
    # Align dates
    combined = pd.DataFrame({'stock': stock_close, 'bench': benchmark_close}).dropna()
    if combined.empty:
        return pd.Series(0.0, index=stock_close.index)
    
    raw_ratio = combined['stock'] / combined['bench']
    base_ratio_ma = sma(raw_ratio, lookback)
    rs_mansfield = ((raw_ratio / base_ratio_ma.replace(0, np.nan)) - 1.0) * 100.0
    return rs_mansfield.reindex(stock_close.index).fillna(0.0)
