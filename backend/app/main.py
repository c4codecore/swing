"""
FastAPI Server - Modern Quantitative Swing Trading Engine
"""
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Query, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import RedirectResponse


def _load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


_load_local_env(Path(__file__).resolve().parents[1] / ".env")

from app.core.config import BENCHMARK_INDEX, DEFAULT_UNIVERSE
from app.core.data_fetcher import MarketDataUnavailable, fetch_ohlcv
from app.core.indicators import ema, rsi
from app.core.stock_research import get_stock_research
from app.core.stock_universe import get_nse_equities, is_supported_nse_equity
from app.core.signal_history import capture_signals, get_signal_history
from app.core.portfolio_storage import get_manual_holdings, replace_manual_holdings
from app.engine.regime import analyze_market_regime
from app.engine.intraday import analyze_intraday
from app.engine.intraday_screener import run_intraday_screener
from app.engine.options import build_nifty_options_plan
from app.engine.strategies import STRATEGY_REGISTRY
from app.engine.screener import screener_engine
from app.engine.institutional_flow import get_flow_watchlist
from app.engine.backtester import run_strategy_backtest
from app.core.iifl_market_data import (
    IIFLNotConfigured,
    IIFLPortfolioUnavailable,
    IIFLQuoteUnavailable,
    IIFLSessionRequired,
    build_login_url,
    complete_login,
    configuration_status,
    get_nifty_quote,
    get_portfolio_holdings,
)

app = FastAPI(
    title="MarketVoice API",
    description="Systematic NSE Screener, Adaptive Regime Classifier & Backtesting Engine",
    version="2.0.0"
)
logger = logging.getLogger(__name__)


def _iifl_error_detail(error: Exception) -> str:
    message = str(error)
    if "ip address not authorized" in message.lower():
        return (
            "IIFL rejected this API request because the backend's public IP is not authorized. "
            "Ask IIFL API support/RM to authorize the public egress IP for this API app/account, "
            "and confirm that read-only holdings and market-data requests are covered."
        )
    return message

configured_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")
allowed_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]

# Enable CORS for frontend Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "marketvoice-api", "version": "2.0.0"}


@app.get("/api/market/live/status")
def live_market_status():
    return configuration_status()


@app.get("/api/market/live/login")
def iifl_live_login():
    try:
        return RedirectResponse(build_login_url(), status_code=302)
    except IIFLNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/market/live/callback")
def iifl_live_callback(request: Request):
    # IIFL's callback has been observed using lower-case parameter names.
    # Treat OAuth query parameter names case-insensitively.
    callback_params = {key.lower(): value for key, value in request.query_params.items()}
    auth_code = callback_params.get("authcode")
    client_id = callback_params.get("clientid")
    if not auth_code or not client_id:
        raise HTTPException(status_code=400, detail="IIFL callback is missing authCode or clientId. Check the app's registered redirect URL.")
    try:
        complete_login(client_id, auth_code)
        return RedirectResponse("/", status_code=303)
    except IIFLNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except IIFLSessionRequired as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.get("/api/market/live/nifty")
def live_nifty_quote(response: Response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    try:
        return get_nifty_quote()
    except IIFLNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except IIFLSessionRequired as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except IIFLQuoteUnavailable as exc:
        raise HTTPException(status_code=502, detail=_iifl_error_detail(exc))


@app.get("/api/intraday")
def intraday_analysis():
    """Read-only NIFTY opening-range/VWAP setup using IIFL live market data."""
    try:
        return analyze_intraday()
    except IIFLSessionRequired as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except IIFLQuoteUnavailable as exc:
        raise HTTPException(status_code=502, detail=_iifl_error_detail(exc))
    except Exception:
        logger.exception("Intraday analysis failed")
        raise HTTPException(status_code=502, detail="IIFL intraday analysis could not be calculated.")


@app.get("/api/intraday/screener")
def intraday_stock_screener(
    force_refresh: bool = False,
    strategy: Optional[str] = None,
):
    """Scan NSE stocks for world-class intraday setups using multi-signal analysis."""
    try:
        valid_strategies = {
            "vwap_opening_drive", "orb_prebreakout", "momentum_ignition",
            "mean_reversion", "rs_surge",
        }
        strat_filter = strategy if isinstance(strategy, str) and strategy.strip() else None
        if strat_filter and strat_filter not in valid_strategies:
            raise HTTPException(status_code=422, detail=f"Unknown intraday strategy. Available: {', '.join(sorted(valid_strategies))}")
        return run_intraday_screener(
            strategy_filter=strat_filter,
            force_refresh=bool(force_refresh),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except MarketDataUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Intraday screener request failed")
        raise HTTPException(status_code=500, detail="Unable to complete intraday market scan.")


@app.get("/api/options")
def options_analysis():
    """Build a live-premium NIFTY debit-spread scenario from an intraday bias."""
    try:
        intraday = analyze_intraday()
        return build_nifty_options_plan(intraday)
    except IIFLSessionRequired as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except IIFLQuoteUnavailable as exc:
        raise HTTPException(status_code=502, detail=_iifl_error_detail(exc))
    except Exception:
        logger.exception("Options analysis failed")
        raise HTTPException(status_code=502, detail="IIFL options analysis could not be calculated.")


def _analyze_portfolio_holding(holding: dict) -> dict:
    raw_symbol = str(holding.get("symbol") or "").strip().upper()
    clean_symbol = re.sub(r"-(EQ|BE|BZ)$", "", raw_symbol)
    yf_symbol = clean_symbol if clean_symbol.startswith("^") or clean_symbol.endswith(".NS") else f"{clean_symbol}.NS"
    quantity = _number(holding.get("quantity"))
    average_price = _number(holding.get("average_price"))
    last_price = _number(holding.get("last_price"))
    try:
        frame = fetch_ohlcv(yf_symbol, period="6mo")
        closes = frame["Close"].dropna()
        if len(closes) < 50:
            raise ValueError("not enough price history")
        e20 = float(ema(closes, 20).iloc[-1])
        e50 = float(ema(closes, 50).iloc[-1])
        rsi_now = float(rsi(closes, 14).iloc[-1])
        close = float(closes.iloc[-1])
        last_price = last_price or close
        return20 = (close / float(closes.iloc[-21]) - 1) * 100 if len(closes) >= 21 else None
        trend_broken = close < e50 and e20 < e50
        weak_momentum = rsi_now < 30 and return20 is not None and return20 < 0
        if trend_broken or weak_momentum:
            action = "REVIEW_SELL"
            reasons = []
            if trend_broken:
                reasons.append("The latest share price is below its 50-day average, and its recent average is also falling.")
            if weak_momentum:
                reasons.append("The share price has been especially weak over the past month.")
        else:
            action = "HOLD"
            reasons = []
            if close >= e50:
                reasons.append("The latest share price is at or above its 50-day average.")
            if e20 >= e50:
                reasons.append("The recent average price is at or above the 50-day average.")
            if rsi_now >= 30:
                reasons.append("The recent price check has not shown an especially sharp fall.")
            if not reasons:
                reasons.append("This daily price check did not find a strong reason to exit.")
        invested_value = quantity * average_price if quantity is not None and average_price is not None else None
        current_value = quantity * last_price if quantity is not None and last_price is not None else None
        unrealized_pnl = (last_price - average_price) * quantity if last_price is not None and average_price is not None and quantity is not None else _number(holding.get("pnl"))
        pnl_pct = ((last_price - average_price) / average_price * 100) if last_price is not None and average_price else None
        if action == "REVIEW_SELL":
            trend_summary = "Share ka daam pichhle 50 din ke ausat se neeche hai aur haal ka rukh bhi kamzor hai." if trend_broken else "Share ka daam pichhle mahine kamzor raha hai; price ko dhyan se dekhein."
            position_summary = f"Average buy price ke muqable abhi lagbhag ₹{abs(unrealized_pnl):,.0f} {'loss' if unrealized_pnl < 0 else 'profit'} ({pnl_pct:+.1f}%). " if unrealized_pnl is not None and pnl_pct is not None else ""
            beginner_verdict = f"{trend_summary} {position_summary}Ghabra kar faisla na karein aur bina plan ke aur shares na jodein. Apni pehle se tay loss-limit aur investment ka time-horizon check karein; limit toot gayi ho ya yeh short-term trade tha, toh position kam karne ya bechne par vichaar karein."
        elif action == "HOLD":
            beginner_verdict = "Is review ke rules ne abhi exit warning nahi di. Yeh risk-free hone ki guarantee nahi hai. Agar share kharidne ki aapki wajah aur time-horizon abhi bhi theek hain, toh hold karna consider karein; apni loss-limit tay rakhein aur agle daily close par dobara review karein."
        else:
            beginner_verdict = "Is share ke liye bharosemand daily data nahi mila. Is report ke basis par buy ya sell ka faisla na karein; symbol/data check karke baad me dobara review karein."
        return {
            **holding,
            "display_symbol": clean_symbol,
            "last_price": round(last_price, 2),
            "invested_value": round(invested_value, 2) if invested_value is not None else None,
            "current_value": round(current_value, 2) if current_value is not None else None,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "analysis": {
                "action": action,
                "as_of": str(frame.index[-1].date()),
                "close": round(close, 2),
                "ema20": round(e20, 2), "ema50": round(e50, 2),
                "rsi14": round(rsi_now, 1),
                "return20_pct": round(return20, 2) if return20 is not None else None,
                "reasons": reasons,
                "beginner_verdict": beginner_verdict,
            },
        }
    except Exception as exc:
        logger.info("Daily portfolio analysis unavailable for %s: %s", raw_symbol, exc)
        return {
            **holding,
            "display_symbol": clean_symbol,
            "last_price": last_price,
            "invested_value": round(quantity * average_price, 2) if quantity is not None and average_price is not None else None,
            "current_value": round(quantity * last_price, 2) if quantity is not None and last_price is not None else None,
            "unrealized_pnl": _number(holding.get("pnl")),
            "analysis": {"action": "INSUFFICIENT_DATA", "as_of": None, "reasons": ["Reliable daily price history was unavailable, so no hold/sell signal was generated."], "beginner_verdict": "Is share ke liye bharosemand daily data nahi mila. Is report ke basis par buy ya sell ka faisla na karein; symbol/data check karke baad me dobara review karein."},
        }


def _number(value):
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


class ManualHolding(BaseModel):
    symbol: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9&._-]+$")
    quantity: float = Field(gt=0, le=100000000)
    average_price: float = Field(gt=0, le=1000000000)


class ManualPortfolioRequest(BaseModel):
    holdings: list[ManualHolding] = Field(max_length=100)


@app.get("/api/portfolio/manual")
def read_manual_portfolio():
    """Return the user's locally persisted manual portfolio entries."""
    try:
        holdings = get_manual_holdings()
        return {"holdings": holdings, "count": len(holdings), "source": "Local persistent portfolio"}
    except Exception:
        logger.exception("Unable to load saved manual portfolio")
        raise HTTPException(status_code=500, detail="Unable to load saved portfolio.")


@app.put("/api/portfolio/manual")
def save_manual_portfolio(request: ManualPortfolioRequest):
    """Replace the saved manual holdings after an add, edit, or delete."""
    try:
        holdings = replace_manual_holdings([holding.model_dump() for holding in request.holdings])
        return {"holdings": holdings, "count": len(holdings), "source": "Local persistent portfolio"}
    except Exception:
        logger.exception("Unable to save manual portfolio")
        raise HTTPException(status_code=500, detail="Unable to save portfolio changes.")


@app.post("/api/portfolio/manual-review")
def manual_portfolio_review(request: ManualPortfolioRequest):
    """Review user-entered holdings without calling IIFL account endpoints."""
    manual_rows = [
        {
            "symbol": holding.symbol.strip().upper(),
            "quantity": holding.quantity,
            "average_price": holding.average_price,
            "record_type": "manual",
            "exchange": "Manual entry",
        }
        for holding in request.holdings
    ]
    analyzed = [_analyze_portfolio_holding(row) for row in manual_rows]
    return {
        "holdings": analyzed,
        "source": "Manual entries",
        "analysis_as_of": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds"),
            "method": "Daily check: today's price and recent price changes compared with usual prices.",
        "disclaimer": "Technical research screen only, not personalized financial advice. Signals do not place orders; consider your own risk limits, costs, taxes, and investment horizon.",
    }


@app.get("/api/portfolio")
def portfolio_analysis(force_refresh: bool = Query(False, description="Refresh holdings and rerun daily analysis")):
    """Read IIFL holdings and return a transparent daily technical review."""
    try:
        portfolio = get_portfolio_holdings(force_refresh=force_refresh)
        analyzed = [_analyze_portfolio_holding(row) for row in portfolio["holdings"]]
        return {
            **portfolio,
            "holdings": analyzed,
            "analysis_as_of": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds"),
            "method": "Daily check: today's price and recent price changes compared with usual prices.",
            "disclaimer": "Research signal only. It is not personalized financial advice and does not place orders. Review costs, taxes, time horizon, and your own risk limits before trading.",
        }
    except IIFLNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except IIFLSessionRequired as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except IIFLPortfolioUnavailable as exc:
        raise HTTPException(status_code=502, detail=_iifl_error_detail(exc))


@app.get("/api/regime")
def get_market_regime():
    """Returns current multi-factor market regime, breadth, and strategy guidance."""
    try:
        return analyze_market_regime()
    except MarketDataUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Market regime request failed")
        raise HTTPException(status_code=500, detail="Unable to calculate market regime.")


@app.get("/api/strategies")
def list_strategies():
    """Lists all registered strategies with metadata and target regimes."""
    strats = []
    for k, v in STRATEGY_REGISTRY.items():
        strats.append({
            "id": k,
            "title": v.display_name,
            "description": v.description,
            "target_regimes": v.target_regimes
        })
    return strats


@app.get("/api/screener/run")
def run_screener(
    force_refresh: bool = Query(False, description="Bypass cache and force fresh scan"),
    strategy: Optional[str] = Query(None, description="Optional single strategy filter")
):
    """Executes high-speed screener across the NSE universe."""
    try:
        if strategy and strategy not in STRATEGY_REGISTRY:
            raise HTTPException(status_code=422, detail="Unknown strategy filter.")
        strat_filter = [strategy] if strategy else None
        return screener_engine.run_screener(force_refresh=force_refresh, strategy_filter=strat_filter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except MarketDataUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Screener request failed")
        raise HTTPException(status_code=500, detail="Unable to complete market scan.")


@app.get("/api/flow-watchlist")
def read_flow_watchlist(
    limit: int = Query(10, ge=10, le=20, description="Number of leaders and laggards to return per side"),
    refresh: bool = False,
):
    """Rank the liquid watch universe by daily OHLCV accumulation/distribution proxy."""
    try:
        return get_flow_watchlist(limit=limit, force_refresh=refresh)
    except Exception as exc:
        logger.exception("Unable to build the volume flow watchlist")
        raise HTTPException(status_code=503, detail="Volume flow scan is unavailable. Try again when daily market data is available.") from exc


class SignalHistoryCaptureRequest(BaseModel):
    signals: List[Dict[str, Any]] = Field(default_factory=list, max_length=500)
    max_holding_days: Literal[15, 30] = 15


@app.post("/api/history/capture")
def capture_signal_history(req: SignalHistoryCaptureRequest):
    """Persist scan setups once per signal date, stock, and strategy."""
    try:
        return capture_signals(req.signals, req.max_holding_days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Unable to save signal history")
        raise HTTPException(status_code=500, detail="Unable to save signal history.")


@app.get("/api/history")
def read_signal_history():
    """Refresh open setups using completed daily candles and return date-sorted outcomes."""
    try:
        return get_signal_history()
    except Exception:
        logger.exception("Unable to load signal history")
        raise HTTPException(status_code=500, detail="Unable to load signal history.")


class BacktestRequest(BaseModel):
    strategy: str = Field(default="trend_pullback", pattern=r"^[a-z_]+$")
    period: Literal["6mo", "1y", "2y", "3y"] = "2y"
    max_holding_days: int = Field(default=15, ge=1, le=90)
    risk_per_trade_pct: float = Field(default=1.5, ge=0.1, le=5)
    initial_capital: float = Field(default=100000, gt=0, le=1000000000)
    max_open_positions: int = Field(default=5, ge=1, le=20)


@app.post("/api/backtest/run")
def execute_backtest(req: BacktestRequest):
    """Runs walk-forward backtest simulation for a strategy."""
    try:
        return run_strategy_backtest(
            strategy_name=req.strategy,
            period=req.period,
            max_holding_days=req.max_holding_days,
            risk_per_trade_pct=req.risk_per_trade_pct,
            initial_capital=req.initial_capital,
            max_open_positions=req.max_open_positions,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Backtest request failed")
        raise HTTPException(status_code=500, detail="Unable to run backtest.")


@app.get("/api/symbols")
def get_universe_symbols():
    """Returns the latest NSE main-board and SME equity symbol list."""
    stocks, metadata = get_nse_equities()
    return {
        "count": len(stocks),
        "symbols": [stock["symbol"] for stock in stocks],
        "stocks": stocks,
        **metadata,
    }


@app.get("/api/chart/{symbol}")
def get_chart_data(symbol: str, period: Literal["1mo", "3mo", "6mo", "1y", "2y", "3y"] = "6mo", history: bool = False):
    """
    Returns candlestick data and computed indicators for charting.
    """
    try:
        if not re.fullmatch(r"[A-Za-z0-9&._^-]{1,24}", symbol):
            raise HTTPException(status_code=422, detail="Invalid symbol format.")
        ns_symbol = symbol.upper() if symbol.startswith("^") else (symbol.upper() if symbol.upper().endswith(".NS") else f"{symbol.upper()}.NS")
        if ns_symbol != BENCHMARK_INDEX and not is_supported_nse_equity(ns_symbol):
            raise HTTPException(status_code=404, detail="Symbol is not in the supported universe.")
        df = fetch_ohlcv(ns_symbol, period=period)
        if df.empty or len(df) < 20:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")

        c = df['Close']
        e20 = ema(c, 20)
        e50 = ema(c, 50)
        rsi_series = rsi(c, 14)

        candles = []
        for idx, row in df.iterrows():
            candles.append({
                "time": idx.strftime("%Y-%m-%d"),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume']),
                "ema20": round(float(e20.loc[idx]), 2) if idx in e20.index else None,
                "ema50": round(float(e50.loc[idx]), 2) if idx in e50.index else None,
                "rsi": round(float(rsi_series.loc[idx]), 1) if idx in rsi_series.index else None
            })

        return {
            "symbol": symbol.replace(".NS", ""),
            "candles": candles if history else candles[-120:]  # Full range on demand; charts stay lightweight by default.
        }
    except HTTPException:
        raise
    except MarketDataUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Chart request failed for %s", symbol)
        raise HTTPException(status_code=500, detail="Unable to load chart data.")


@app.get("/api/stock/{symbol}/research")
def get_stock_research_data(symbol: str):
    """Returns recent headlines, daily technicals, and available company fundamentals."""
    if not re.fullmatch(r"[A-Za-z0-9&._^-]{1,24}", symbol):
        raise HTTPException(status_code=422, detail="Invalid symbol format.")
    ns_symbol = symbol.upper() if symbol.upper().endswith(".NS") else f"{symbol.upper()}.NS"
    if not is_supported_nse_equity(ns_symbol):
        raise HTTPException(status_code=404, detail="Symbol is not in the supported universe.")
    try:
        return get_stock_research(ns_symbol)
    except Exception:
        logger.exception("Stock research request failed for %s", ns_symbol)
        raise HTTPException(status_code=500, detail="Unable to load stock research details.")


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve built frontend if dist directory exists
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
