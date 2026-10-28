# 📈 MarketVoice (v2.0 Systematic Trading Platform)

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
MarketVoice/
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

## Multi-Factor Confluence strategy

The `multi_factor` screener option scores long setups using EMA trend structure and slope, relative strength versus Nifty, RSI and ADX, volume participation, a 20-session breakout, distance from the 20-day EMA, benchmark context, and stop/target geometry. The score is a checklist score, **not** a probability of profit.

The **Stock analysis** tab searches NSE's current main-board equity and SME symbol lists by ticker or company name, then shows a selected stock's price chart, technical indicators, company fundamentals, and recent headlines. The exchange symbol list refreshes daily. Its 1-month and 3-month price ranges are historical-volatility scenarios, not reliable predictions or trade recommendations. The screener continues to use the smaller configured liquid-stock universe.

The **History** tab records each Overview setup once per signal date, symbol, and strategy in PostgreSQL. Open setups are checked against completed daily candles until target 1, stop-loss, or the selected 15- or 30-session time exit. On first database connection, existing history in `backend/data/marketvoice_history.sqlite3` is imported once; the SQLite file is retained as a backup.

The **Volume flow** tab ranks up to 10 or 20 liquid-watchlist stocks by a 20-session price/volume accumulation and distribution proxy. It weights estimated turnover (`close × volume`) by where each candle closes within its range and applies a minimum average-turnover filter. This is not official delivery data and cannot identify institutional, FII, or DII trades.

Manual portfolio holdings are also saved in PostgreSQL; the browser copy is retained as a recovery fallback. Add, edit, and remove actions update the persistent portfolio. Configure `DATABASE_URL` in `backend/.env` using `backend/.env.example` as a template. Create the target PostgreSQL database before starting the backend. Any legacy portfolio SQLite file is imported once if present.

For live screening, recent Yahoo Finance headlines are fetched through `yfinance`. Headline keyword matches can flag possible event risk, and a failed news lookup is shown as a manual-review state. This is a limited headline screen: it does not understand context or replace exchange filings, earnings calendars, or a human reading the full story. The historical backtester uses price history only; it cannot replay historical news from this feed. Treat every setup as research for review, not an automatic trade instruction.

## 🚀 How to Run

### Quick Start (Single Command):
1. Install the backend dependencies: `python -m pip install -r backend/requirements.txt`.
2. Copy `backend/.env.example` to `backend/.env`, set `DATABASE_URL`, and create that PostgreSQL database.
3. Start the app:
```bash
python run_app.py
```
This runs the FastAPI server, serves the production-compiled frontend, and automatically opens **`http://127.0.0.1:8001`** in your browser.

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
