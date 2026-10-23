# ⚡ QUANTUM SWING (v2.0 Systematic Platform)

A full-stack, institutional-grade quantitative swing trading platform for the **NSE Nifty 100 universe**, engineered from the ground up to solve the fatal flaws of traditional naive trend-following screeners.

---

## 💡 Previous Failures Addressed (What Changed?)

In previous iterations, two major problems plagued the system:
1. **The Blunt "Bullish Filter" Flaw:** A binary `EMA 20 > EMA 50` condition caused the system to either miss early reversal opportunities or enter at the exact overextended top of market moves.
2. **"Bearish Market Me Koi Strategy Kaam Nahi Karti":** Traditional long-only trend strategies bleed heavily in downtrends.

### The New Architecture Solution:
* **Adaptive Multi-Factor Regime Engine (`backend/app/engine/regime.py`):**
  Instead of a blunt yes/no check, the engine continuously monitors **Nifty 50 Trend Alignment**, **5-day EMA Slopes**, **Market Breadth (% of stocks > 20 & 50 EMA)**, and **Volatility (ATR & Bollinger Bandwidth)** across 5 distinct cycles:
  1. `STRONG_BULL`: Momentum breakouts & trend pullbacks (100% Capital Exposure).
  2. `PULLBACK_BULL`: Healthy dips to 20/50 EMA (75% Capital Exposure).
  3. `SIDEWAYS_CHOPPY`: Volatility Squeezes & Range mean-reversion (50% Capital Exposure).
  4. `BEARISH_CORRECTION`: **Strictly forbids generic long breakouts!** Activates **Relative Strength Outperformers** (stocks decoupling from index) and recommends 75% Cash Preservation (25% max exposure).
  5. `EXTREME_PANIC_OVERSOLD`: Deep Capitulation Mean-Reversion snapback trades targeting 2R-4R bounces to the 20 EMA.

---

## 🏗️ Project Architecture

```
swing_trading/
│
├── run_app.py                   # 🚀 One-click unified application launcher
├── README.md                    # Platform documentation
│
├── backend/                     # 🐍 High-Performance Python FastAPI Backend
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # REST API & static web serving
│       ├── core/
│       │   ├── config.py        # Liquid NSE stock universe & constants
│       │   ├── indicators.py    # Vectorized pandas indicators (EMA, RSI, ATR, RS)
│       │   └── data_fetcher.py  # Resilient yfinance fetcher with TTL cache
│       └── engine/
│           ├── regime.py        # Multi-Factor Adaptive Market Regime Engine
│           ├── screener.py      # High-speed parallel stock screener
│           ├── backtester.py    # Walk-forward backtester with Regime Breakdown
│           └── strategies/
│               ├── base.py
│               ├── trend_pullback.py       # Bullish specialist
│               ├── relative_strength.py    # Bearish / Neutral leader specialist
│               ├── capitulation_reversal.py# Panic / Oversold bounce specialist
│               └── volatility_squeeze.py   # Compression breakout specialist
│
├── frontend/                    # ⚛️ Modern React + Vite Web Dashboard
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.jsx              # Main dashboard with live tabs & modals
│   │   ├── index.css            # Custom Vanilla CSS design system (Dark obsidian fintech)
│   │   └── components/
│   │       ├── StockChart.jsx   # Interactive SVG candlestick, EMA & RSI chart
│   │       ├── RegimeView.jsx   # Market Regime, Breadth gauge & Strategy radar
│   │       └── BacktestLab.jsx  # Walk-forward backtest simulator & equity curve
│
└── old_experiment/              # 📦 Preserved legacy scripts, CSVs, and docs
```

---

## 🚀 How to Run

### Quick Start (Single Command):
```bash
python run_app.py
```
This runs the FastAPI server, serves the production-compiled frontend, and automatically opens **`http://127.0.0.1:8000`** in your browser.

### Development Mode (Concurrent):
If you want to edit frontend code with live hot-reloading:
1. **Terminal 1 (Backend):**
   ```bash
   python run_app.py
   ```
2. **Terminal 2 (Frontend):**
   ```bash
   cd frontend
   npm run dev
   ```
   Open **`http://localhost:5173`**.
