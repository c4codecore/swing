"""On-demand stock news, daily technicals, and company fundamentals."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import yfinance as yf

from app.core.data_fetcher import MarketDataUnavailable, fetch_benchmark, fetch_ohlcv
from app.core.indicators import adx, atr, ema, relative_strength, rsi, sma
from app.core.news_fetcher import fetch_news_context

logger = logging.getLogger(__name__)


def _number(value: Any) -> Optional[float]:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _historical_scenarios(close: Any, last_price: float) -> Dict[str, Any]:
    """Build illustrative price ranges from recent log-return drift and volatility."""
    prices = [_number(value) for value in close.tail(253).tolist()]
    prices = [value for value in prices if value is not None and value > 0]
    log_returns = [math.log(current / previous) for previous, current in zip(prices, prices[1:]) if previous > 0]
    if len(log_returns) < 40:
        return {
            "status": "unavailable",
            "method": "Historical daily log-return drift and volatility; at least 40 observations are required.",
            "observations": len(log_returns),
            "scenarios": [],
        }

    daily_drift = sum(log_returns) / len(log_returns)
    daily_variance = sum((value - daily_drift) ** 2 for value in log_returns) / (len(log_returns) - 1)
    daily_volatility = math.sqrt(daily_variance)
    z80 = 1.281551565545
    scenarios = []
    for sessions, label in ((20, "About 1 month"), (60, "About 3 months")):
        expected_log_return = daily_drift * sessions
        range_width = z80 * daily_volatility * math.sqrt(sessions)
        base_price = last_price * math.exp(expected_log_return)
        low_price = last_price * math.exp(expected_log_return - range_width)
        high_price = last_price * math.exp(expected_log_return + range_width)
        scenarios.append({
            "sessions": sessions,
            "label": label,
            "base_price": round(base_price, 2),
            "low_price": round(low_price, 2),
            "high_price": round(high_price, 2),
            "base_return_pct": round((base_price / last_price - 1) * 100, 2),
            "low_return_pct": round((low_price / last_price - 1) * 100, 2),
            "high_return_pct": round((high_price / last_price - 1) * 100, 2),
        })
    return {
        "status": "available",
        "method": "Illustrative range from the last year of daily log-return drift and volatility; central 80% normal-model band, assuming market behavior stays similar.",
        "observations": len(log_returns),
        "daily_volatility_pct": round(daily_volatility * 100, 2),
        "scenarios": scenarios,
    }


def _technical_snapshot(symbol: str) -> Dict[str, Any]:
    try:
        frame = fetch_ohlcv(symbol, period="1y")
        if len(frame) < 20:
            raise MarketDataUnavailable(f"Insufficient daily price history for {symbol}.")

        close = frame["Close"]
        last = float(close.iloc[-1])
        ema20, ema50, ema200 = ema(close, 20), ema(close, 50), ema(close, 200)
        atr14, rsi14, adx14 = atr(frame, 14), rsi(close, 14), adx(frame, 14)
        volume20 = sma(frame["Volume"], 20)
        volume_ratio = float(frame["Volume"].iloc[-1] / volume20.iloc[-1]) if volume20.iloc[-1] else None
        try:
            bench = fetch_benchmark(period="1y")
            rs_series = relative_strength(close, bench["Close"], lookback=63) if len(bench) else None
        except Exception:
            logger.info("Nifty comparison unavailable for %s", symbol, exc_info=True)
            rs_series = None

        if len(frame) >= 200 and last > float(ema20.iloc[-1]) > float(ema50.iloc[-1]) > float(ema200.iloc[-1]):
            trend = "Bullish alignment"
        elif last > float(ema50.iloc[-1]):
            trend = "Above EMA 50"
        else:
            trend = "Below EMA 50"

        return {
            "status": "available" if rs_series is not None else "partial",
            "source": "Yahoo Finance daily OHLCV",
            "as_of": frame.index[-1].strftime("%Y-%m-%d"),
            "close": round(last, 2),
            "ema20": round(float(ema20.iloc[-1]), 2),
            "ema50": round(float(ema50.iloc[-1]), 2),
            "ema200": round(float(ema200.iloc[-1]), 2) if len(frame) >= 200 else None,
            "rsi14": round(float(rsi14.iloc[-1]), 1),
            "adx14": round(float(adx14.iloc[-1]), 1),
            "atr14_pct": round(float(atr14.iloc[-1]) / last * 100, 2) if last else None,
            "volume_ratio20": round(volume_ratio, 2) if volume_ratio is not None else None,
            "return20_pct": round((last / float(close.iloc[-21]) - 1) * 100, 2) if len(frame) >= 21 else None,
            "return63_pct": round((last / float(close.iloc[-64]) - 1) * 100, 2) if len(frame) >= 64 else None,
            "mansfield_rs63": round(float(rs_series.iloc[-1]), 2) if rs_series is not None and len(rs_series) else None,
            "trend": trend,
            "forecast": _historical_scenarios(close, last),
        }
    except Exception as exc:
        logger.info("Daily technical snapshot unavailable for %s: %s", symbol, exc)
        return {"status": "unavailable", "source": "Yahoo Finance daily OHLCV", "error": str(exc)}


def _fundamental_snapshot(symbol: str) -> Dict[str, Any]:
    try:
        info = yf.Ticker(symbol).get_info() or {}
        fields = {
            "market_cap": "marketCap",
            "trailing_pe": "trailingPE",
            "forward_pe": "forwardPE",
            "price_to_book": "priceToBook",
            "eps_ttm": "trailingEps",
            "dividend_yield": "dividendYield",
            "return_on_equity": "returnOnEquity",
            "revenue_growth": "revenueGrowth",
            "earnings_growth": "earningsGrowth",
            "debt_to_equity": "debtToEquity",
            "current_ratio": "currentRatio",
            "profit_margin": "profitMargins",
            "operating_margin": "operatingMargins",
            "beta": "beta",
            "total_revenue": "totalRevenue",
            "free_cash_flow": "freeCashflow",
            "currency": "financialCurrency",
            "sector": "sector",
            "industry": "industry",
            "company_name": "longName",
        }
        values: Dict[str, Any] = {}
        for key, provider_key in fields.items():
            raw = info.get(provider_key)
            values[key] = raw if key in {"currency", "sector", "industry", "company_name"} else _number(raw)
        numeric_fields = set(fields) - {"currency", "sector", "industry", "company_name"}
        populated = sum(values[key] is not None for key in numeric_fields)
        return {
            "status": "available" if populated >= 4 else "partial" if populated else "unavailable",
            "source": "Yahoo Finance company profile and summary",
            "as_of": None,
            **values,
        }
    except Exception as exc:
        logger.info("Fundamental snapshot unavailable for %s: %s", symbol, exc)
        return {"status": "unavailable", "source": "Yahoo Finance company profile and summary", "error": str(exc)}


def get_stock_research(symbol: str) -> Dict[str, Any]:
    """Collect on-demand stock context; partial provider failures do not hide other sections."""
    return {
        "symbol": symbol.replace(".NS", ""),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "news": fetch_news_context(symbol),
        "technical": _technical_snapshot(symbol),
        "fundamentals": _fundamental_snapshot(symbol),
    }
