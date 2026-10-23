"""
FastAPI Server - Modern Quantitative Swing Trading Engine
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.core.config import DEFAULT_UNIVERSE
from app.core.data_fetcher import fetch_ohlcv, fetch_benchmark
from app.core.indicators import ema, sma, rsi, atr
from app.engine.regime import analyze_market_regime
from app.engine.strategies import STRATEGY_REGISTRY, get_all_strategies
from app.engine.screener import screener_engine
from app.engine.backtester import run_strategy_backtest

app = FastAPI(
    title="Quantitative Swing Trading Engine",
    description="Systematic NSE Screener, Adaptive Regime Classifier & Backtesting Engine",
    version="2.0.0"
)

# Enable CORS for frontend Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "swing-trading-engine", "version": "2.0.0"}


@app.get("/api/regime")
def get_market_regime():
    """Returns current multi-factor market regime, breadth, and strategy guidance."""
    try:
        return analyze_market_regime()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        strat_filter = [strategy] if strategy and strategy in STRATEGY_REGISTRY else None
        return screener_engine.run_screener(force_refresh=force_refresh, strategy_filter=strat_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BacktestRequest(BaseModel):
    strategy: str = "trend_pullback"
    period: str = "2y"
    max_holding_days: int = 15
    risk_per_trade_pct: float = 1.5


@app.post("/api/backtest/run")
def execute_backtest(req: BacktestRequest):
    """Runs walk-forward backtest simulation for a strategy."""
    try:
        return run_strategy_backtest(
            strategy_name=req.strategy,
            period=req.period,
            max_holding_days=req.max_holding_days,
            risk_per_trade_pct=req.risk_per_trade_pct
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/symbols")
def get_universe_symbols():
    """Returns list of supported liquid symbols."""
    clean = [s.replace(".NS", "") for s in DEFAULT_UNIVERSE]
    return {"count": len(clean), "symbols": clean}


@app.get("/api/chart/{symbol}")
def get_chart_data(symbol: str, period: str = "6mo"):
    """
    Returns candlestick data and computed indicators for charting.
    """
    try:
        ns_symbol = symbol if symbol.endswith(".NS") or symbol.startswith("^") else f"{symbol}.NS"
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
            "candles": candles[-120:]  # Send last 120 bars for smooth performance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import os
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
