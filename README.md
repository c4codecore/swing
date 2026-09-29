# 📈 NSE Swing Trading System

A plug-and-play Python screener + backtester that scans **Nifty 100 stocks** against multiple swing-trading strategies, filters by market regime, and saves matched signals to CSV + Google Sheets.

> **Disclaimer:** This is a **screening tool only** — it surfaces candidates for further research. It does **not** constitute financial advice or buy/sell recommendations.

---

## 🧭 How It Works (End-to-End Flow)

```
                    ┌──────────────┐
                    │   run.py     │ ← Entry point
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │market_regime │ ← Check Nifty EMA20/EMA50 → Bullish / Neutral / Bearish
                    └──────┬───────┘
                           │
             ┌─────────────▼──────────────┐
             │ For each strategy module:  │
             │   Is REQUIRED_REGIME met?  │
             │   Yes → screen stocks      │
             │   No  → [SKIPPED]         │
             └─────────────┬──────────────┘
                           │
                    ┌──────▼───────┐
                    │ screener.py  │ ← Fetch OHLCV → call generate_signal() → collect matches
                    └──────┬───────┘
                           │
            ┌──────────────▼──────────────┐
            │  Save signals to:           │
            │  1. outputs/watchlist.csv    │
            │  2. Google Sheets (optional) │
            └─────────────────────────────┘
```

**Daily workflow:**
1. Market close ke baad `python run.py` run karo
2. System Nifty ka regime check karega (Bullish/Neutral/Bearish)
3. Har strategy jo current regime mein allowed hai, uske liye Nifty 100 screen hoga
4. Matched stocks watchlist.csv mein append honge + Google Sheet mein sync honge
5. Next day open pe entry evaluate karo (signals are end-of-day, entry is next-day-open)

---

## 🗂️ Project Structure

```
swing_trading/
│
├── core/                      # 🧠 Core trading engine & data layer
│   ├── __init__.py
│   ├── ohlcv_data.py          # 📊 Data layer — NSE symbol lists + yfinance price history
│   ├── indicators.py          # 📐 Shared indicator library (EMA, RSI, ATR, MACD, ADX, SuperTrend)
│   ├── market_regime.py       # 🌡️ Nifty regime detection (Bullish/Neutral/Bearish)
│   └── screener.py            # 🔍 Generic screener engine
│
├── integrations/              # ☁️ Cloud integrations & sync services
│   ├── __init__.py
│   ├── gsheets.py             # 📋 Google Sheets OAuth + auto-sync
│   └── gdrive.py              # ☁️ Google Drive document uploader & auto-updater
│
├── strategies/                # 📦 Plugin-based strategy modules (auto-discovered)
│   ├── __init__.py
│   ├── _template.py           # Blueprint for new strategies (not loaded at runtime)
│   ├── smart_pullback.py      # ⭐ Smart Pullback (regime-filtered, best PF)
│   ├── ema_pullback.py        # EMA Trend + Pullback
│   ├── breakout.py            # Resistance Breakout
│   ├── golden_cross.py        # Golden Cross (EMA50/EMA200)
│   ├── momentum_confluence.py # Multi-Confluence Momentum
│   ├── precision_2r.py        # Precision 2R V2
│   ├── regime_rs_breakout.py  # Regime + Relative Strength Breakout
│   ├── rsi_reversal.py        # RSI Reversal
│   ├── trend_pullback.py      # Trend Pullback
│   ├── trend_surfer.py        # Trend Surfer (7-Filter)
│   └── volatility_squeeze.py  # Volatility Squeeze Breakout
│
├── docs/                      # 📚 Project guides & learning notes
│   ├── Share_Market_Basics.md # Beginner's guide to share market + strategy theory
│   └── google_sheets_setup.md # Google Sheets & Drive OAuth configuration guide
│
├── outputs/                   # 📁 Generated files (auto-created)
│   ├── watchlist.csv          # Cumulative signal log
│   ├── backtest_summary.csv   # Per-strategy backtest summary
│   ├── backtest_trades.csv    # Every individual backtest trade
│   ├── backtest_yearly.csv    # Year-by-year breakdown
│   ├── backtest_monthly.csv   # Month-by-month breakdown
│   └── backtest_trades_with_regime.csv # Trades tagged with Nifty regime
│
├── run.py                     # 🚀 Main entry point — live screening
├── backtest.py                # 🧪 Walk-forward backtester with regime filter
├── regime_split.py            # 📊 Splits backtest trades by Nifty regime for analysis
├── diagnostic.py              # 🔬 Filter funnel analyzer — shows where signals get blocked
├── gdrive_upload.py           # ☁️ Quick CLI to upload/update docs to Google Drive
├── README.md                  # Project overview & quickstart
└── .gitignore
```

---

## ⚙️ Setup

### 1. Clone / download

```bash
git clone <repo-url>
cd swing_trading
```

### 2. Install dependencies

```bash
pip install yfinance pandas requests
```

**Optional** (for Google Sheets sync):
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

> Python **3.10+** recommended.

### 3. Google Sheets setup (optional)

1. Create OAuth 2.0 credentials in [Google Cloud Console](https://console.cloud.google.com/)
2. Download `client_secret.json` to the project root
3. First run will open browser for OAuth consent
4. Sheet URL is saved to `outputs/sheet_url.txt`

---

## 🚀 Usage

### Daily Screening

```bash
python run.py                    # Run ALL strategies (regime-filtered)
python run.py smart_pullback     # Run one specific strategy
python run.py menu               # Interactive numbered menu
```

### Backtesting

```bash
python backtest.py                           # All strategies, Nifty 100, 250 days
python backtest.py smart_pullback --baseline # One strategy vs random-entry baselines
python backtest.py --days 500 --universe nifty50  # Custom parameters
python backtest.py all --min-rr 1.5          # Override minimum R:R filter
```

### Regime Analysis

```bash
python regime_split.py             # Split backtest trades by Bullish/Neutral/Bearish
```

### Filter Diagnostic

```bash
python diagnostic.py               # Shows which filters block the most signals
python diagnostic.py trend_surfer   # One strategy
```

### Sync Notes to Google Drive

```bash
python gdrive_upload.py            # Upload / Update Share_Market_Basics.md as Google Doc
python gdrive_upload.py --raw-md   # Upload / Update as raw .md file
```


---

## 🌡️ Market Regime System

The regime system is the **#1 insight from backtesting** — it determines whether to trade or sit.

| Regime | Condition | Action |
|--------|-----------|--------|
| **Bullish** | Nifty Close > EMA50 AND EMA20 > EMA50 | ✅ Trade long strategies |
| **Neutral** | Neither Bullish nor Bearish | ⚠️ Trade with caution |
| **Bearish** | Nifty Close < EMA50 AND EMA20 < EMA50 | 🛑 Skip long strategies |

Strategies can declare `REQUIRED_REGIME = "Bullish"` to auto-skip in wrong regimes.

---

## 📊 Strategy Overview

### Backtest-Proven (with regime filter)

| Strategy | Regime | Trades | WinRate | PF | Expectancy |
|----------|--------|--------|---------|------|------------|
| **Smart Pullback** ⭐ | Bullish only | 29 | 62.1% | **2.20** | **+1.34%** |
| EMA Trend + Pullback | Bullish only | 122 | ??? | 1.05 | +0.09% |

### Other Available Strategies

| Strategy | Description | Signals/250d |
|----------|-------------|-------------|
| Resistance Breakout | 20-day high breakout + volume | ~230 |
| RSI Reversal | RSI oversold bounce | ~160 |
| Trend Surfer | 7-filter trend following | ~110 |
| Multi-Confluence Momentum | MACD + ADX + RSI + Volume + Trend | ~80 |
| Golden Cross | EMA50/EMA200 crossover | Very few |
| Regime RS Breakout | Relative strength vs Nifty + consolidation breakout | ~30-60 |

> **Note:** Most strategies have negative expectancy in raw (all-regime) backtest. Use the regime filter or trade only in Bullish market.

---

## 📁 Output Format

Signals are appended to `outputs/watchlist.csv`:

| Column | Description |
|--------|-------------|
| `Date` | Date the screen was run |
| `Time` | Time the screen was run |
| `Strategy` | Strategy name |
| `Stock` | NSE ticker (without `.NS`) |
| `Entry` | Suggested entry price (last close) |
| `StopLoss` | Calculated stop-loss |
| `Target` | Calculated target (usually 2× risk) |
| `Risk_Rs` | Risk per share (₹) |
| `Reward_Rs` | Reward per share (₹) |
| `Indicators` | Strategy-specific values (RSI, EMA, Volume etc.) |

---

## 🧩 Adding a New Strategy

1. Copy `strategies/_template.py` → `strategies/my_strategy.py`
2. Set these constants:

```python
NAME = "My Strategy"                  # Human-readable name (required)
DATA_PERIOD = "2y"                    # yfinance period (optional, default "6mo")
REQUIRED_REGIME = "Bullish"           # Skip in wrong regime (optional, default None)
```

3. Implement `generate_signal(price_data)`:
   - `price_data`: pandas DataFrame with `Open, High, Low, Close, Volume`, indexed by date
   - Return `dict` with `Entry, StopLoss, Target, Risk_Rs, Reward_Rs` if signal fires
   - Return `None` if no signal

4. **That's it.** Auto-discovered in `run.py`, `backtest.py`, and the menu.

```python
# strategies/my_strategy.py

NAME = "My Custom Strategy"
REQUIRED_REGIME = "Bullish"    # only trade in bull market
DATA_PERIOD = "2y"             # need 2 years of data for EMA200

def generate_signal(price_data):
    # ... your logic here ...
    if all_filters_pass:
        return {
            "Entry": entry_price,
            "StopLoss": stop_price,
            "Target": target_price,
            "Risk_Rs": entry_price - stop_price,
            "Reward_Rs": target_price - entry_price,
        }
    return None
```

---

## 🧪 Backtest Methodology

The backtester uses realistic assumptions:

| Setting | Value | Why |
|---------|-------|-----|
| Entry price | Next day's **Open** | Signal fires at close, you enter next morning |
| Round-trip cost | 0.1% | Brokerage + STT + slippage |
| Max hold | 15 days | Swing trading, not investing |
| Min actual R:R | 1.95 | Gap destroys R:R → skip trade |
| Regime filter | Per-strategy | REQUIRED_REGIME respected during backtest |

**Baseline comparison** (`--baseline`): Random-entry baselines using same stop/target/cost rules. A strategy must beat the baseline to prove it has real edge.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `yfinance` | Historical OHLCV data from Yahoo Finance |
| `pandas` | Data manipulation + CSV |
| `requests` | Live NSE symbol lists |
| `numpy` | Numerical operations |
| `google-auth` + `google-api-python-client` | *(Optional)* Google Sheets sync |

---

## ⚠️ Important Notes

- **Run after market close** for end-of-day signals on completed candles
- **Entry is next-day open** — signals tell you *what* to watch, entry happens next morning
- **Regime matters most** — backtest proves strategies only work in Bullish Nifty regime
- **Rate limiting** — 0.2s delay between stock fetches to avoid throttling
- **No order routing** — this is a screening/analysis tool, not a trading bot
- **Survivorship bias** — backtest uses today's Nifty 100 constituents for the entire period

---

## 📚 Learning Resources

See [`Share_Market_Basics.md`](docs/Share_Market_Basics.md) for:
- Share market fundamentals (Hindi + English)
- Investing vs Trading concepts
- 5 swing trading strategies explained
- Technical indicator glossary
- Risk management rules

---
