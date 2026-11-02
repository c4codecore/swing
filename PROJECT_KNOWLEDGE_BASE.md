# MarketVoice: Comprehensive Project Knowledge Base & System Reference

> **Document Type:** Master System Architecture, Algorithmic Design & Knowledge Base  
> **Target Audience:** AI Assistants, Autonomous Agents, Core Engineering Team  
> **Status:** Active / Production-Ready (v2.0.0)  
> **Base Directory:** `c:\nnn\iifl\swing_trading`  
> **Primary Technology Stack:** Python 3.14 (FastAPI) + React 18 (Vite 8) + PostgreSQL (psycopg binary) + IIFL Securities Trading API (BridgePy) + Yahoo Finance (`yfinance`)

---

## 1. Executive Summary & Core Objectives

**MarketVoice** is an institutional-grade, quantitative swing trading and intraday market analytics platform tailored for the **National Stock Exchange of India (NSE)**. It bridges systematic mathematical screening, multi-factor market regime identification, live broker feeds (IIFL Securities), and defined-risk options structuring inside a bespoke, mobile-friendly pastel claymorphic user interface.

### Primary Objectives
1. **Systematic Regime Filtering:** Eliminate emotional bias by sizing positions and selecting strategies strictly based on mathematical market regime classification (Bull, Pullback, Choppy, Correction, Panic).
2. **High-Probability Swing & Intraday Filtering:** Scan the broader NSE universe (NSE Main-Board and SME equities) in seconds using high-confluence algorithmic models:
   - Daily Swing models (Trend Pullback, Relative Strength vs. NIFTY 50, Capitulation Reversals, Volatility Squeezes, Multi-Factor Confluence).
   - Real-time Intraday models (Gap + Volume Opening Drive, Squeeze Breakouts, Momentum Ignition, Mean Reversion Bounce, RS Surge).
3. **Institutional Flow & Breadth Tracking:** Gauge market health via Advance/Decline breadth, percentage of stocks above 20/50-day moving averages, and volume-weighted Accumulation/Distribution proxies.
4. **Defined-Risk Derivatives Architecture:** Automatically translate intraday directional biases into defined-risk, high-probability NIFTY 50 vertical debit spreads with live premiums, exact break-evens, and asymmetric risk-reward ratios.
5. **Zero-Order Risk Safety:** Operates as a transparent decision-support system. It reads broker quotes, ticks, and holdings via read-only channels without placing unconfirmed automated orders.
6. **Cross-Device Usability:** Provide a responsive trading experience via a desktop sidebar and a dedicated mobile bottom-dock and drawer navigation.

---

## 2. High-Level Architecture & Tech Stack

```
                                      +---------------------------------------------+
                                      |             NSE Market Data Sources          |
                                      +----------------------+----------------------+
                                                             |
                                   +-------------------------+-------------------------+
                                   |                                                   |
                                   v                                                   v
                    +------------------------------+                    +------------------------------+
                    |    IIFL Securities API       |                    |        Yahoo Finance         |
                    | (BridgePy / MQTT WebSocket)  |                    |      (`yfinance` engine)     |
                    | - Spot Quotes (NIFTY 50)     |                    | - Daily OHLCV Data (6mo-3y)  |
                    | - 5-min Intraday Candles     |                    | - Company News & Overview    |
                    | - F&O Option Chain Quotes    |                    | - 5-min Screener Cache (TTL) |
                    | - User Portfolio Holdings    |                    +--------------+---------------+
                    +--------------+---------------+                                   |
                                   |                                                   |
                                   +-------------------------+-------------------------+
                                                             |
                                                             v
+--------------------------------------------------------------------------------------------------------------------------+
|                                                  FastAPI Backend Core                                                    |
|                                                                                                                          |
|  +---------------------------+  +--------------------------+  +--------------------------+  +--------------------------+  |
|  |     Regime Classifier     |  |   Swing Screener Engine  |  |    Intraday Screener     |  |    Options Spread Lab    |  |
|  | (5 States, Breadth, ATR)  |  |  (5 Algorithmic Models)  |  |  (5 High-Frequency Setups|  |   (NIFTY Debit Spreads)  |  |
|  +---------------------------+  +--------------------------+  +--------------------------+  +--------------------------+  |
|  +---------------------------+  +--------------------------+  +--------------------------+  +--------------------------+  |
|  |    Institutional Flow     |  |  Backtester Engine (Walk)|  |   Signal History Store   |  |   Portfolio Reviewer     |  |
|  | (Accumulation/Dist. Score)|  |  (Max Drawdown, Win-Rate)|  | (15/30 Day Track Record) |  | (Technical Hold/Sell)   |  |
|  +---------------------------+  +--------------------------+  +--------------------------+  +--------------------------+  |
|                                                            |                                                             |
|                                  +-------------------------+-------------------------+                                   |
|                                  v                                                   v                                   |
|                    +---------------------------+                       +---------------------------+                     |
|                    |   PostgreSQL Production   |                       |    SQLite Local Fallback  |                     |
|                    |     Database Engine       |                       |  (Dual Legacy Migration)  |                     |
|                    +---------------------------+                       +---------------------------+                     |
+------------------------------------------------------------+-------------------------------------------------------------+
                                                             | JSON REST APIs (Port 8001)
                                                             v
+--------------------------------------------------------------------------------------------------------------------------+
|                                                  Frontend Client Layer                                                   |
|                                                                                                                          |
|  +--------------------------------------------------------------------------------------------------------------------+  |
|  | Modern React 18 SPA (Vite 8) + Vanilla CSS Claymorphic UI System                                                    |  |
|  | - Navigation: Adaptive Desktop Rail + Mobile Sliding Drawer + Mobile 5-Tab Persistent Bottom Dock                   |  |
|  | - Interactive Views: Screener, Intraday Engine, Options Lab, Flow Watch, Stock Research, Backtest, Portfolio       |  |
|  | - Visualizations: Lightweight Candlestick Charts (SVG/Canvas), Real-Time Breadth Gauges, Metric Badge Pills       |  |
|  +--------------------------------------------------------------------------------------------------------------------+  |
+--------------------------------------------------------------------------------------------------------------------------+
```

### Backend Components
- **Language / Runtime:** Python 3.14.0 (Windows 64-bit).
- **Web Framework:** FastAPI with Starlette and Uvicorn.
- **Data Science & Math:** Pandas, NumPy, yfinance (for daily OHLCV caching and universe aggregation).
- **Broker Live Integration:** IIFL `BridgePy` SDK with OAuth authentication and MQTT WebSocket client for streaming market data.
- **Database Engine:** PostgreSQL via `psycopg` (binary) with fallback to SQLite (`marketvoice_history.sqlite3`, `marketvoice_portfolio.sqlite3`).
- **Static Assets:** Serves bundled React SPA directly from `frontend/dist` with client-side routing fallback.

### Frontend Components
- **Framework:** React 18.3.1 with Vite 8.0.0.
- **Styling:** Bespoke, zero-runtime Pure CSS (`src/index.css`) featuring a Pastel Claymorphic design language (soft 3D depth, dual drop shadows, pill badges).
- **Icons:** `lucide-react`.
- **Audio Feedback:** Synthesized Web Audio API sound effects for interactions.

---

## 3. Complete Directory Structure & File Inventory

```
c:\nnn\iifl\swing_trading\
├── .gitignore                      # Git exclusion rules (node_modules, venv, .env, DBs)
├── README.md                       # High-level introductory documentation
├── PROJECT_KNOWLEDGE_BASE.md       # MASTER SYSTEM DOCUMENT (This Document)
├── run_app.py                      # Master bootstrap launcher: builds frontend, checks ports, launches server & browser
├── start.bat                       # Windows double-click shortcut to launch run_app.py
├── stop.bat                        # Windows utility to cleanly kill dangling backend/frontend processes
│
├── backend\
│   ├── .env                        # Local secret configurations (IIFL credentials, DB URL, origins)
│   ├── .env.example                # Sanitized template for environment variables
│   ├── IIFL_LIVE_DATA.md           # IIFL API integration documentation & OAuth debugging notes
│   ├── requirements.txt            # Python dependencies (FastAPI, uvicorn, yfinance, psycopg, etc.)
│   └── app\
│       ├── __init__.py             # Package marker
│       ├── main.py                 # FastAPI application definition, CORS, routing, SPA static file server
│       │
│       ├── core\
│       │   ├── __init__.py         # Core package marker
│       │   ├── config.py           # Universe definitions, benchmark symbols, cache TTL constants
│       │   ├── database.py         # PostgreSQL connection pool with automated SQLite migration
│       │   ├── data_fetcher.py     # Thread-safe cached daily OHLCV fetcher using yfinance
│       │   ├── iifl_market_data.py # IIFL broker integration: OAuth login, session tokens, ticks, options master
│       │   ├── indicators.py       # Math library: EMA, SMA, RSI, ATR, Bollinger Bands, MACD, Stochastic
│       │   ├── news_fetcher.py     # RSS/Google News/Yahoo Finance headline aggregation & sentiment
│       │   ├── portfolio_storage.py# Persistent user portfolio storage (CRUD across PostgreSQL/SQLite)
│       │   ├── regime_storage.py  # PostgreSQL/SQLite regime-state persistence and migration
│       │   ├── signal_history.py   # Historical setup tracker: captures signals, monitors 15/30-day outcomes
│       │   ├── stock_research.py   # Aggregates technical indicators, valuation metrics, and recent news
│       │   └── stock_universe.py   # Scrapes official NSE Equity master list (EQUITY_L.csv) with 24h caching
│       │
│       └── engine\
│           ├── __init__.py         # Engine package marker
│           ├── backtester.py       # Realistic walk-forward simulation engine (equity curves, max drawdown)
│           ├── filters.py          # Shared swing/intraday tradability and data-quality filters
│           ├── institutional_flow.py # Accumulation/Distribution volume flow ranking algorithm
│           ├── intraday.py         # 15-minute Opening Range Breakout (ORB) + VWAP on NIFTY 50 (IIFL live)
│           ├── intraday_screener.py# Hybrid daily-context / completed 5-minute intraday screener
│           ├── options.py          # Defined-Risk NIFTY 50 vertical debit spread constructor
│           ├── regime.py           # Multi-Factor Market Regime Engine (5 states, breadth, moving averages)
│           ├── screener.py         # Multi-threaded daily swing screener across universe
│           └── strategies\
│               ├── __init__.py     # Registry exporting all active swing trading strategies
│               ├── base.py         # Abstract StrategyBase defining scoring, triggers, stops, targets
│               ├── capitulation_reversal.py # Extreme oversold exhaustion bounce strategy
│               ├── multi_factor.py # Comprehensive confluence strategy combining momentum and trend
│               ├── relative_strength.py     # RS leaders outperforming NIFTY 50 over 20-60 day spans
│               ├── trend_pullback.py        # Institutional dip-buying in established EMA20/50 uptrends
│               └── volatility_squeeze.py    # Bollinger Band inside Keltner Channel volatility expansion
│
├── frontend\
│   ├── index.html                  # HTML entry point with meta viewport configured for mobile
│   ├── package.json                # Frontend dependencies, scripts (vite build, dev)
│   ├── vite.config.js              # Vite configuration (proxying `/api` to `http://127.0.0.1:8001`)
│   ├── dist\                       # Production pre-compiled static assets served by FastAPI
│   │   ├── index.html
│   │   └── assets\                 # Minified JS, CSS, and SVG chunks
│   └── src\
│       ├── main.jsx                # React root mount
│       ├── App.jsx                 # Main layout, mobile drawer, bottom navigation, active tab coordinator
│       ├── index.css               # 1,700+ lines of bespoke pastel claymorphic CSS design system
│       ├── assets\
│       │   └── logo.png            # Application branding emblem
│       ├── utils\
│       │   └── soundFx.js          # Web Audio API synthetic notification synthesizer
│       └── components\
│           ├── BacktestLab.jsx     # Visual walk-forward strategy simulator with equity chart & trade logs
│           ├── CyberHUD.jsx        # Telemetry badges for live market status and latency
│           ├── CyberToast.jsx      # Non-intrusive floating alert notification banners
│           ├── InstitutionalFlowView.jsx # Visual table of top accumulated and distributed equities
│           ├── RegimeView.jsx      # Detailed market breadth analysis, gauge meters, and regime history
│           ├── SignalHistoryView.jsx    # Track record auditor showing resolved vs open signals & PnL
│           ├── StockAnalysisView.jsx    # Deep dive search tool for any NSE stock with live candlestick chart
│           ├── StockChart.jsx      # High-performance candlestick chart component with EMA overlays & RSI
│           ├── ThreeCanvas.jsx     # WebGL ambient visual canvas
│           └── TradingStrategiesView.jsx# Dual-mode view: Swing Strategies & Intraday Screener with grid cards
│
└── old_experiment\                 # Archived CLI & legacy research notebooks from early project phases
```

---

## 4. Quantitative Strategy Engines

### 4.1 Deterministic Market Regime Engine (`backend/app/engine/regime.py`)
The engine evaluates only completed NIFTY daily closes and uses first-match-wins rules. Its exact order is `EXTREME_PANIC_OVERSOLD → BEARISH_CORRECTION → STRONG_BULL → PULLBACK_BULL → SIDEWAYS_CHOPPY → CATCH_ALL_SIDEWAYS_CHOPPY`. Price below EMA50 but above EMA200 with negative 20-day momentum maps to `BEARISH_CORRECTION`. Early recovery above EMA20 and EMA50 while EMA20 remains below EMA50 maps to `SIDEWAYS_CHOPPY`: without a confirmed rising EMA20/50 structure, assigning the 0.75 pullback risk weight is not supported by the available evidence. Any remaining combination maps to sideways through the catch-all.

| State (first match wins) | Thresholds / rule | Configured risk weight |
|---|---|---:|
| `EXTREME_PANIC_OVERSOLD` | RSI(14) < 30 **or** close is ≤ 3 standard deviations below the 20-day Bollinger mean | 0.30 |
| `BEARISH_CORRECTION` | Close < EMA50 and 20-day return < 0, with either close ≥ EMA200 or 50-day return < 0 | 0.25 |
| `STRONG_BULL` | Close > EMA20/50/200; EMA20 > EMA50; 20- and 50-day returns > 0; 50 EMA slope > 0; if breadth is available, ≥60% above EMA50 | 1.00 |
| `PULLBACK_BULL` | Close ≥ EMA50 and > EMA200 but < EMA20; **or** RSI 40–50 with positive 50 EMA slope and close > EMA200 | 0.75 |
| `SIDEWAYS_CHOPPY` | Early recovery with close > EMA20/EMA50 while EMA20 < EMA50; **or** 50 EMA slope within ±0.25%, Bollinger width ≤ its 20-day mean + 0.5 standard deviations, and if breadth is available, 45–55% above EMA50 | 0.50 |
| Catch-all → `SIDEWAYS_CHOPPY` | Any remaining metric combination | 0.50 |

Weights are configurable risk-scaling defaults, not tested optimum values; Phase 7 backtesting will evaluate them. By default a non-risk-off state change needs 2 consecutive completed daily closes. Entries into panic/correction confirm after 1 close; exits from those risk-off states require 2. The confirmed state, raw state, pending streak, and days in state are persisted once per completed date in `regime_history`; repeat API calls for the same close do not advance hysteresis. PostgreSQL creates the table through the normal schema migration; SQLite fallback uses the same versioned table migration in `marketvoice_history.sqlite3`.

Inputs/windows and thresholds are in `backend/app/core/config.py`: EMA20/50/200, 20/50-day return lookbacks, RSI14, Bollinger period/multiplier plus 20-day width mean/std, 50 EMA slope lookback, and breadth thresholds. Breadth uses the configured, Phase 2 swing-liquidity-filtered, non-SME universe. It is unavailable below 200 valid symbols; then no breadth percentage is inferred and classification uses benchmark-only rules with a visible warning and the sample size. The response includes the rule match, whether the raw classification used a defined rule or catch-all, and the number of catch-all days among its last 30 history rows.

### Screening Universe and Fetching
`DEFAULT_UNIVERSE` in `backend/app/core/config.py` is a compatibility list. Swing and breadth use `SCREENING_UNIVERSE_MODE`, default `nifty500`, with choices `nifty50`, `nifty500`, and `nse_equities`. Intraday uses its own `INTRADAY_SCREENING_UNIVERSE_MODE`, currently `nifty500`, to scan NIFTY 500 constituents before the intraday tradability filter. Daily market-data cache capacity is configured by `MARKET_DATA_CACHE_MAX_ITEMS` to retain universe frames across rescans.

Daily history is retrieved through sequential, paced multi-symbol Yahoo downloads in configurable batches (`DAILY_BATCH_SIZE`, retry count, exponential backoff, and inter-batch pause) and cached per symbol by the existing thread-safe cache. The intraday screener reuses daily context for 6 hours; current price and VWAP still use completed 5-minute candles. Intraday 5-minute data is fetched only after daily liquidity/tradability filtering, in batched requests for surviving candidates plus NIFTY.

If `regime_history` is empty, the regime API bootstraps it by replaying the last 60 completed NIFTY daily bars through the same classifier and hysteresis state machine. The early-recovery case remains `SIDEWAYS_CHOPPY` until the bull structure is established; this avoids using the larger `PULLBACK_BULL` risk weight without evidence.

---

### 4.2 Daily Swing Trading Strategies (`backend/app/engine/strategies/`)
All swing strategies inherit from `StrategyBase` (`base.py`) and implement:
- `scan(symbol, df, benchmark_df) -> Optional[SignalResult]`
- Exact entry price, stop-loss price, 2R target price, risk-reward ratio, and quantitative scoring (0 to 100).

```
+--------------------------+----------------------------------------------------+--------------------------+
| Strategy ID              | Core Quantitative Filters                          | Target Market Regimes    |
+--------------------------+----------------------------------------------------+--------------------------+
| trend_pullback           | Close > 200 EMA; 20 EMA > 50 EMA;                  | STRONG_BULL,             |
|                          | Low <= 20 EMA * 1.01; Close > Low; RSI: 40-55;     | PULLBACK_BULL            |
|                          | Volume > 20-day Volume Average.                    |                          |
+--------------------------+----------------------------------------------------+--------------------------+
| relative_strength        | Mansfield RS > 0 vs NIFTY over 20, 40, and 60 days;| STRONG_BULL,             |
|                          | Stock making 20-day High while Index is not;       | PULLBACK_BULL,           |
|                          | Volume expansion > 1.5x 20-day average.            | SIDEWAYS_CHOPPY          |
+--------------------------+----------------------------------------------------+--------------------------+
| capitulation_reversal    | 5-day drop > 12%; Daily RSI(14) < 25;              | EXTREME_PANIC_OVERSOLD,  |
|                          | Close touches lower Bollinger Band (20, 2.5);      | BEARISH_CORRECTION       |
|                          | Bullish hammer/reversal candle with spike volume.  |                          |
+--------------------------+----------------------------------------------------+--------------------------+
| volatility_squeeze       | Bollinger Bands (20, 2.0) contract inside          | STRONG_BULL,             |
|                          | Keltner Channel (20, 1.5 ATR); Squeeze duration    | PULLBACK_BULL,           |
|                          | >= 5 bars; Momentum oscillator crosses above 0.    | SIDEWAYS_CHOPPY          |
+--------------------------+----------------------------------------------------+--------------------------+
| multi_factor             | Confluence scoring: Trend alignment (20/50/200),   | STRONG_BULL,             |
|                          | Momentum (RSI 55-68), Volume Flow (CMF > 0.10),   | PULLBACK_BULL            |
|                          | and RS score > 70. Requires total score >= 80/100. |                          |
+--------------------------+----------------------------------------------------+--------------------------+
```

---

### 4.2.1 Shared Tradability Filter (`backend/app/engine/filters.py`)
Both swing and intraday screeners apply `filter_tradable_symbols()` to daily OHLCV data before any strategy evaluates a symbol. It returns passed symbols plus first-applicable rejection counts; one symbol increments at most one reason. Both API responses include `filter_rejections`, and the screener UI shows counts for price, liquidity, history, staleness, SME, price bands, and ASM/GSM.

- Defaults in `backend/app/core/config.py`: minimum price ₹50; 20-day average traded value ₹5 crore/day for swing and ₹10 crore/day for intraday; 220 daily bars; maximum last-bar age of 3 weekdays; 0.5% circuit-band proximity; SME exclusions enabled (`INCLUDE_SME_STOCKS = False`).
- When available, SME classification uses the project's cached NSE SME listing; if unavailable, a symbol-suffix heuristic is used and `sme_source` identifies it. Set `INCLUDE_SME_STOCKS = True` to include SME symbols.
- Circuit bands are read from upper/lower band columns when supplied. Otherwise a heuristic looks for consecutive one-price sessions and a 2%, 5%, 10%, or 20% band-sized move; heuristic rejections have their own count.
- ASM/GSM entries are loaded from the optional `backend/data/asm_gsm.csv` (header `symbol`, `security`, or `ticker`). Set `ASM_GSM_LIST_PATH` to override the path. A missing file is explicitly reported as `asm_gsm: not configured`.
- Staleness counts weekdays because the data feed does not provide an exchange holiday calendar; a market holiday may therefore be counted as a trading day in this age estimate.

### 4.3 World-Class Intraday Stock Screener (`backend/app/engine/intraday_screener.py`)
Designed to solve the problem of missing intraday opportunities. Uses daily-bar context and completed 5-minute session bars. Daily bars provide EMA/ATR/resistance/average-volume context; 5-minute bars provide current-session price, VWAP, RSI, high/low and cumulative volume. The screener first applies the shared intraday tradability filter, then batch-downloads 45 calendar days of 5-minute data for survivors plus NIFTY (`INTRADAY_PROFILE_PERIOD`), enough history for its session-volume profile while keeping the download smaller.

#### The Core Problem & The Session-Aware RVOL Innovation
- **Traditional Screener Flaw:** Conventional screeners check `Current Volume >= 1.5 * 20-day Volume Average`. During the first 1-3 hours of trading (09:15 to 12:00), cumulative volume is naturally lower than a full 6.25-hour day. Consequently, screeners find 0 stocks until 14:30.
- **MarketVoice Solution:** For each stock, compute the median cumulative share of daily volume at each 5-minute point across up to 30 completed sessions. Expected volume is the average of the last 20 completed daily volumes (today's partial bar excluded) multiplied by that stock's cumulative intraday profile at the current completed candle. Session RVOL is current-session cumulative volume divided by expected volume. Profiles refresh once per IST date; today's 5-minute batch has a 180-second cache. If fewer than 15 full sessions are available, use a market-wide U-shaped default. Half-days and truncated sessions are excluded from the profile; all candle timestamps are normalized to IST.
- Only completed 5-minute candles are evaluated: Yahoo candle timestamps are treated as interval starts, and a bar is included only after its five-minute interval has ended. Signals expose `last_candle_at`, `data_delay_seconds`, and `stale`; the UI shows the candle time and delay.
- `INTRADAY_DATA_TTL_SECONDS` defaults to 180. Tradability thresholds and data-quality rules come from the shared filter configuration above.

#### The 8 Intraday Setups:
1. **Gap + Volume Opening Drive (`vwap_opening_drive`):**
   - Gap at open between $+0.75\%$ and $+4.0\%$.
   - Current price > Opening price and Current price > VWAP.
   - Session-aware RVOL $\ge 1.4\times$.
   - Setup: High momentum continuation. Stop at Day Low or VWAP $-0.3\%$. Target: $1.5\text{R}$ to $2.5\text{R}$.
2. **Breakout Setup / Tight Squeeze (`orb_prebreakout`):**
   - Intraday High within $0.6\%$ of the 5-day or 20-day resistance level.
   - Day range is compressed ($< 1.8\times\text{ATR}$), indicating an impending volatility explosion.
   - Session RVOL $\ge 1.0\times$ with positive intraday price gain ($+0.4\%$ to $+3.5\%$).
3. **Momentum Ignition (`momentum_ignition`):**
   - Day Change $> +2.0\%$ with massive volume surge (Session RVOL $\ge 1.8\times$).
   - Close in top $15\%$ of current day range (High minus Low).
   - Price above both 20-day EMA and 50-day EMA.
4. **Mean Reversion Bounce (`mean_reversion`):**
   - Stock down $-2.0\%$ to $-5.0\%$ in early trade, testing strong daily support (50 EMA or 200 EMA).
   - Intraday rebound of at least $+0.6\%$ off day low.
   - RSI(14) rebounding from oversold ($< 35$ turning upward).
5. **Relative Strength Surge vs NIFTY (`rs_surge`):**
   - Calculates 1-day alpha: $\alpha = \text{Stock \% Change} - \text{NIFTY 50 \% Change}$.
   - Triggers when $\alpha \ge +1.75\%$ with Session RVOL $\ge 1.3\times$.
   - Captures stocks displaying institutional accumulation regardless of broader market fluctuations.
6. **15-Min Opening Range Breakout (`opening_range_breakout`):** A completed move above/below the first 15-minute range, confirmed by VWAP, session RVOL, and RSI.
7. **VWAP Reclaim / Breakdown (`vwap_reclaim`):** A completed 5-minute close crosses session VWAP with volume and RSI confirmation.
8. **Trend Pullback Bounce (`trend_pullback`):** Daily EMA20 above EMA50, with a 5-minute recovery near VWAP and volume participation.

---

### 4.4 Defined-Risk NIFTY 50 Options Spreads (`backend/app/engine/options.py`)
Converts intraday directional signals on NIFTY 50 into vertical debit spreads:
- **Bullish Bias (ORB Breakout + VWAP):** Constructs a **Bull Call Spread** (Buy In-The-Money/At-The-Money Call, Sell Out-Of-The-Money Call at $+100$ or $+150$ points).
- **Bearish Bias (ORB Breakdown - VWAP):** Constructs a **Bear Put Spread** (Buy In-The-Money/At-The-Money Put, Sell Out-Of-The-Money Put at $-100$ or $-150$ points).
- **Analytics Computed with Live IIFL Premiums:**
  - Net Premium Paid (Max Loss).
  - Max Potential Profit ($\text{Strike Width} - \text{Net Premium}$).
  - Exact Breakeven Index Level.
  - Asymmetric Risk-Reward Ratio (typically $1:1.8$ to $1:2.6$).

---

## 5. Live Market Data Integration (IIFL Securities)

Detailed in `backend/IIFL_LIVE_DATA.md` and implemented in `backend/app/core/iifl_market_data.py`.

### 5.1 Authentication Flow
1. User clicks **"Connect IIFL Broker"** in the UI.
2. Frontend redirects to `GET /api/market/live/login`, generating IIFL OAuth SSO URL:
   `https://api.iiflsecurities.com/oauth2/authorize?client_id={IIFL_APP_KEY}&redirect_uri={CALLBACK_URL}`
3. User logs in on the IIFL gateway and is redirected back to:
   `GET /api/market/live/callback?authCode={CODE}&clientId={CLIENT_ID}`
4. Backend captures parameters (case-insensitively), exchanges `authCode` for a JWT user session token via BridgePy, and writes active session state to memory.
5. User is redirected back to the dashboard with active live telemetry.

### 5.2 Real-Time Tick & Quote Engine
- Uses IIFL's MQTT WebSocket infrastructure (`BridgePy`).
- Subscribes to NIFTY 50 spot price (Instrument Token `1` on exchange segment `1` for NSE Cash).
- Downloads 5-minute historical intraday candles for the last 5 sessions to establish the 15-minute Opening Range (High/Low) and calculate session VWAP.
- Downloads F&O contract master for weekly/monthly NIFTY option strikes.

### 5.3 Safety & Read-Only Governance
- MarketVoice contains **no automated order-execution loops**.
- It interacts exclusively with:
  - `/market/quotes`
  - `/market/instruments`
  - `/portfolio/holdings`
- Any future trade automation requires explicit manual trade confirmation dialogs.

---

## 6. Persistence, Database Schema & Data Flow

Managed in `backend/app/core/database.py` with automatic table creation and legacy SQLite migration.

### 6.1 Database Configuration
- Configured via `DATABASE_URL` in `backend/.env`.
  - Production default: `postgresql://postgres:postgres@localhost:5432/swing_trading`
  - Automatic Fallback: If PostgreSQL is offline or credentials fail, the system initializes SQLite local files:
    - `marketvoice_history.sqlite3`
    - `marketvoice_portfolio.sqlite3`

### 6.2 Table Schemas

#### 1. `signal_history`
Persists identified swing and screener setups to audit algorithmic performance over 15-day and 30-day holding horizons.
```sql
CREATE TABLE IF NOT EXISTS signal_history (
    id SERIAL PRIMARY KEY,
    signal_date DATE NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    strategy VARCHAR(64) NOT NULL,
    entry_price NUMERIC(12, 2) NOT NULL,
    stop_loss NUMERIC(12, 2) NOT NULL,
    target_price NUMERIC(12, 2) NOT NULL,
    max_holding_days INTEGER NOT NULL DEFAULT 15,
    outcome VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    exit_price NUMERIC(12, 2),
    exit_date DATE,
    return_pct NUMERIC(8, 2),
    meta JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_signal UNIQUE (signal_date, symbol, strategy)
);
```

#### 2. `manual_portfolio`
Stores persistent manual holdings for users who track holdings without connecting an IIFL live account.
```sql
CREATE TABLE IF NOT EXISTS manual_portfolio (
    symbol VARCHAR(32) PRIMARY KEY,
    quantity NUMERIC(14, 4) NOT NULL,
    average_price NUMERIC(14, 2) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. `marketvoice_migrations`
Tracks completed schema migrations and SQLite-to-Postgres data ingestion.

---

## 7. Frontend Architecture & Claymorphic UI System

### 7.1 Design Philosophy: Pastel Claymorphism
Defined in `frontend/src/index.css`. Uses soft, tactile 3D realism without dark-mode eye strain or stark flat surfaces:
- **Clay Depth:** Dual soft inner and outer box shadows:
  `box-shadow: 6px 6px 14px rgba(166, 175, 195, 0.45), -6px -6px 14px rgba(255, 255, 255, 0.85);`
- **Pastel Palette:**
  - Base Background: `#f3f4f8` / `#eceae3`
  - Deep Accents: Royal Violet (`#4b309e` / `#7958dc`), Emerald Green (`#16a34a`), Crimson Rose (`#e11d48`)
  - Typography: `#1f1b2b` (Deep ink for high readability)

### 7.2 Responsive & Mobile Architecture
Supports both Desktop and Mobile viewports (< 768px):
1. **Sliding Drawer Navigation:**
   - Desktop: Persistent vertical left rail (`.side-rail`).
   - Mobile: Sidebar collapses off-screen (`left: -100%`). Triggered by topbar hamburger icon (`Menu`). Slides out smoothly with an ambient frosted backdrop (`.mobile-drawer-backdrop`).
2. **5-Tab Mobile Bottom Dock (`.mobile-bottom-nav`):**
   - Persistent bottom dock on mobile devices with touch targets:
     - **Overview** (Screener)
     - **Intraday** (Intraday Multi-Strategy Hub)
     - **Options** (NIFTY Options Lab)
     - **Portfolio** (Holdings Tracker)
     - **Menu** (Toggles full drawer for Research, Flow, History, and Backtest)
3. **Card-View Contrast Protection:**
   - `.intraday-card-reasons` uses pure white background (`#ffffff`), dark charcoal text (`#1f1b2b`), bold font-weight (600), and vibrant violet bullet markers (`#7958dc`) to ensure readability under all lighting conditions.

---

## 8. Complete API Endpoint Reference

All endpoints are hosted at `http://localhost:8001` (or local network IP).

### System & Health
- `GET /api/health`: Returns API status, microservice name, and current version (`2.0.0`).
- `GET /api/symbols`: Returns list of valid NSE main-board and SME equity tickers.

### Market Regime & Screener
- `GET /api/regime`: Confirmed/raw regime, pending hysteresis, configurable metrics, filtered breadth/sample warning, sizing weight, strategy gating lists, and 30-row persisted history.
- `GET /api/strategies`: Lists registered swing strategies and their optimal regime environments.
- `GET /api/screener/run?force_refresh=false&strategy={id}`: Runs swing scanner across NSE stocks and includes `filter_rejections` counts.
- `GET /api/intraday/screener?strategy={id}&force_refresh=false`: Runs the NIFTY 500 intraday screener with 8 strategies and includes universe metadata and `filter_rejections` counts.

### Live IIFL Broker Integration
- `GET /api/market/live/status`: Returns current IIFL connection status (configured, logged in, session expiry).
- `GET /api/market/live/login`: Initiates OAuth authorization redirect to IIFL login gateway.
- `GET /api/market/live/callback`: OAuth callback endpoint receiving `authCode` and `clientId`.
- `GET /api/market/live/nifty`: Current live spot tick of NIFTY 50 with timestamp.
- `GET /api/intraday`: 15-minute Opening Range Breakout (ORB) and VWAP analysis on NIFTY 50.
- `GET /api/options`: Defined-risk NIFTY 50 vertical debit spread options plan.
- `GET /api/portfolio`: Fetches user holdings from IIFL with automated daily technical hold/sell reviews.

### Manual Portfolio & Signal Tracking
- `GET /api/portfolio/manual`: Returns locally persisted manual holdings.
- `PUT /api/portfolio/manual`: Replaces or updates manual holdings.
- `POST /api/portfolio/manual-review`: Performs algorithmic review on custom holding rows without broker sync.
- `POST /api/history/capture`: Persists active scanner setups to track performance.
- `GET /api/history`: Returns historical setup track records with resolved/open trade PnL.

### Research, Charting & Backtesting
- `GET /api/chart/{symbol}?period=6mo&history=false`: Delivers candlestick data, volume, EMA20/50, and RSI14.
- `GET /api/stock/{symbol}/research`: Aggregates news sentiment, valuation metrics, and technical setup.
- `GET /api/flow-watchlist?limit=10`: Top accumulated and distributed equities by volume-weighted proxy.
- `POST /api/backtest/run`: Runs walk-forward backtest simulation with user-defined risk parameters.

---

## 9. Configuration & Environment Variables

Stored in `backend/.env`:

```ini
# ==========================================
# MarketVoice Environment Configuration
# ==========================================

# Broker Integration (IIFL Securities)
IIFL_APP_KEY="your_iifl_app_key_here"
IIFL_APP_SECRET="your_iifl_app_secret_here"
IIFL_USER_KEY="your_iifl_user_key_here"
IIFL_USER_ID="your_iifl_client_id_here"
IIFL_PASSWORD="your_iifl_password_here"
IIFL_API_BASE_URL="https://api.iiflsecurities.com"
IIFL_REDIRECT_URL="http://localhost:8001/api/market/live/callback"

# Database Configuration
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/swing_trading"

# Web Server & Security
PORT=8001
FRONTEND_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:8001,http://127.0.0.1:8001"
```

---

## 10. Setup, Execution & Deployment

### Quick Start (Windows)
The repository includes a self-healing bootstrap script `run_app.py`:

```bash
# Double-click or run from PowerShell:
python run_app.py
```

### What `run_app.py` Automates:
1. Validates Python environment and dependencies (`backend/requirements.txt`).
2. Checks if frontend static build (`frontend/dist/`) exists. If missing, runs `npm install` and `npm run build`.
3. Verifies port availability on `8001` (terminating dangling instances if necessary).
4. Detects local LAN IPv4 address (e.g. `http://192.168.1.5:8001`) and outputs a QR/access link for mobile device testing.
5. Launches FastAPI via Uvicorn.
6. Automatically opens the default web browser to `http://localhost:8001`.

---

## 11. Key Historical Decisions, Challenges & Solutions

### 1. The Zero-Intraday Filter Problem (Reworked)
- **Challenge:** The Intraday Screener returned 0 stocks during morning and early afternoon sessions.
- **Root Cause:** Volume filters checked against full 20-day daily volume averages.
- **Solution:** Replaced the linear `_get_session_fraction()` approximation with a per-stock cumulative 5-minute volume profile. Intraday strategies now use completed session candles and daily indicators only for longer-term context. Profile history falls back to an explicit market-wide U-shaped profile when fewer than 15 full sessions are available.

### 2. Low Text Contrast on Mobile/Cards (Solved)
- **Challenge:** The "Why this setup" analysis section on cards was difficult to read due to muted grey text on a clay background.
- **Solution:** Refactored `.intraday-card-reasons` in `frontend/src/index.css` to use high-contrast dark charcoal text (`#1f1b2b`, 600 weight) inside a pure white background card with vivid violet bullet markers.

### 3. Mobile Navigation Ergonomics (Solved)
- **Challenge:** Desktop sidebar took up half the viewport on smartphones.
- **Solution:** Developed an adaptive layout with a sliding drawer for deep features and a sticky 5-tab bottom dock for primary trading workflows.

### 4. Database Resilience: PostgreSQL with SQLite Fallback (Solved)
- **Challenge:** Standalone users without a local PostgreSQL instance could encounter startup failures.
- **Solution:** Implemented dual-engine persistence in `backend/app/core/database.py`. The app attempts a PostgreSQL connection pool; if unavailable, it seamlessly falls back to local SQLite databases with automated migration.

### 5. IIFL Case-Insensitive OAuth Callback Handling (Solved)
- **Challenge:** IIFL servers periodically alternate between uppercase (`authCode`) and lowercase (`authcode`) query parameters in callbacks, leading to 400 Bad Request errors.
- **Solution:** Normalized all incoming callback query parameters to lowercase (`{k.lower(): v}`) before credential exchange.

---

## 12. Pending Tasks & Future Roadmap

1. **Automated Order Execution Gateway (Semi-Automated):**
   - Implement an order modal allowing one-click order placement to IIFL after reviewing calculated lot sizes and stop-losses.
2. **WebSocket Streaming to Frontend (SSE or WS):**
   - Transition frontend polling (5-second intervals) to a single Server-Sent Events (SSE) or WebSocket connection for live NIFTY ticks.
3. **Multi-Asset Derivatives Chain:**
   - Expand the defined-risk Options Engine to support BANKNIFTY, FINNIFTY, and top liquid single-stock F&O options.
4. **Alert Notifications:**
   - Add Telegram and Discord webhook notifications when a new high-confluence Intraday setup triggers during market hours.
5. **Intraday Strategy Backtesting:**
   - Extend `backend/app/engine/backtester.py` to support 5-minute candle walk-forward backtesting using historical tick archives.

---
*End of Knowledge Base Document. Updated October 2026 for MarketVoice v2.0.*

