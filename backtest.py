"""
Walk-Forward Backtesting Engine for Swing Trading System.
=========================================================

Knowledge & Quantitative Trading Principles:
--------------------------------------------
1. Zero Lookahead Bias (Walk-Forward Design):
   - Signal generation on day N uses strictly data available up to day N's Close (price_data.iloc[:index + 1]).
   - Actual trade entry occurs on day N+1's Open (9:15 AM IST).
   - This accurately models real-life trading where an algorithm scans after market close (3:30 PM)
     and places market/limit orders for the next morning.

2. Realistic Friction & Gap Handling:
   - Gap-Up / Gap-Down Protection:
     * If next-day Open >= Target: Gap has already captured the move -> Trade skipped.
     * If next-day Open <= StopLoss: Gap broke the support invalidating the setup -> Trade skipped.
   - Dynamic Risk/Reward Check:
     * If a mild gap-up increases actual risk (Actual_Entry - StopLoss) such that
       Executable R:R drops below MIN_ACTUAL_RR (1.95), the trade is skipped.
   - Conservative Intraday Resolution:
     * If both Target and Stop-Loss are breached within the same daily candle (Low <= Stop and High >= Target),
       the engine conservatively assumes the Stop-Loss was hit first.
   - Transaction Costs:
     * 0.10% round-trip friction applied to every trade (covers STT, brokerage, exchange fees, SEBI, GST, stamp duty).

3. Statistical Confidence & Metrics:
   - R-Multiple (R): PnL / Actual Initial Rupee Risk. An R of +2.0 means profit was 2x the amount risked.
   - Expectancy (%): Mathematical average return expected per trade: (Win% * AvgWin%) - (Loss% * AvgLoss%).
   - Profit Factor: Gross Wins / Gross Losses (PF > 1.5 indicates a robust statistical edge).
   - Random Baselines: Compares strategy results against random entries to prove the strategy has real edge.
"""

import argparse
import importlib
import itertools
import os
import pkgutil
import zlib

import pandas as pd

import strategies
from core.ohlcv_data import fetch_price_history, get_nifty50_symbols, get_nifty100_symbols
from core.market_regime import compute_daily_regime


HISTORY_PERIOD = "3y"
DEFAULT_BACKTEST_DAYS = 250
MIN_WARMUP_ROWS = 60
MAX_HOLD_DAYS = 15
ROUND_TRIP_COST_PCT = 0.10
MIN_TRADES_FOR_CONFIDENCE = 30
MIN_ACTUAL_RR = 1.95            # Trades where overnight gap shrinks actual RR below this are skipped

# Random-entry baseline settings (used only with --baseline)
BASELINE_ENTRY_PROBABILITY = 0.02   # 2% chance of entry on any stock-day
BASELINE_ATR_STOP = 2.0             # Stop = Entry - 2 x ATR
BASELINE_RISK_REWARD = 2.0
BASELINE_ATR_PERIOD = 14
BASELINE_TREND_PERIOD = 200         # "Uptrend" baseline: Close > 200-day SMA


# ---------------------------------------------------------------------------
# Strategy Discovery
# ---------------------------------------------------------------------------

def discover_strategies():
    """
    Dynamically scans the strategies/ package and auto-imports all valid strategy modules.
    Skips blueprints/templates starting with '_'.
    """
    found = {}
    for _, module_name, _ in pkgutil.iter_modules(strategies.__path__):
        if module_name.startswith("_"):
            continue
        module = importlib.import_module(f"strategies.{module_name}")
        if hasattr(module, "NAME") and hasattr(module, "generate_signal"):
            found[module_name] = module
    return found


# ---------------------------------------------------------------------------
# Random-Entry Baseline (Null-Hypothesis Testing)
# ---------------------------------------------------------------------------

class RandomEntryBaseline:
    """
    Deterministic pseudo-random baseline strategy.
    
    Knowledge:
        - In quantitative finance, a strategy is only proven to have an 'Alpha Edge'
          if it consistently beats a random coin-toss entry with identical ATR stops,
          2R targets, maximum holding periods, and cost frictions.
        - If a trend strategy cannot beat Random (Close > SMA200), its entry rules
          provide no real timing edge over simple market beta.
    """

    def __init__(self, name, uptrend_only, probability=BASELINE_ENTRY_PROBABILITY):
        self.NAME = name
        self.uptrend_only = uptrend_only
        self.probability = probability

    def generate_signal(self, price_data):
        if len(price_data) < BASELINE_TREND_PERIOD:
            return None

        close = float(price_data["Close"].iloc[-1])
        # Deterministic hash draw based on date + price
        key = f"{price_data.index[-1]}-{close:.2f}"
        draw = zlib.crc32(key.encode()) / 2 ** 32

        if draw >= self.probability:
            return None

        if self.uptrend_only:
            sma = price_data["Close"].tail(BASELINE_TREND_PERIOD).mean()
            if close <= sma:
                return None

        recent = price_data.tail(BASELINE_ATR_PERIOD + 1)
        prev_close = recent["Close"].shift(1)
        tr = pd.concat([
            recent["High"] - recent["Low"],
            (recent["High"] - prev_close).abs(),
            (recent["Low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = float(tr.iloc[1:].mean())

        if pd.isna(atr) or atr <= 0:
            return None

        risk = BASELINE_ATR_STOP * atr
        stop = close - risk

        if stop <= 0:
            return None

        return {
            "Entry": close,
            "StopLoss": round(stop, 2),
            "Target": round(close + risk * BASELINE_RISK_REWARD, 2),
        }


# ---------------------------------------------------------------------------
# Trade Simulation
# ---------------------------------------------------------------------------

def simulate_trade(price_data, entry_index, stoploss, target):
    """
    Simulates forward price action bar-by-bar starting at day N+1 (entry_index).
    
    Returns:
        (exit_index, exit_price, exit_reason)
        exit_reasons: 'stop', 'target', 'stop_gap', 'target_gap', 'time_exit'
    """
    opens = price_data["Open"].values
    highs = price_data["High"].values
    lows = price_data["Low"].values
    closes = price_data["Close"].values

    entry = float(opens[entry_index])
    last = min(entry_index + MAX_HOLD_DAYS - 1, len(price_data) - 1)

    # If opening gap on entry day blows past levels, reject trade
    if entry <= stoploss:
        return entry_index, entry, "gap_below_stop"
    if entry >= target:
        return entry_index, entry, "gap_above_target"

    for day in range(entry_index, last + 1):
        if day > entry_index:
            # Check overnight gap openings on subsequent holding days
            if opens[day] <= stoploss:
                return day, float(opens[day]), "stop_gap"
            if opens[day] >= target:
                return day, float(opens[day]), "target_gap"
        
        # Intraday level breach check (Conservative: Stop assumes hit first)
        if lows[day] <= stoploss:
            return day, stoploss, "stop"
        if highs[day] >= target:
            return day, target, "target"

    if last - entry_index + 1 < MAX_HOLD_DAYS:
        return None   # Incomplete holding window at end of dataset

    # Time-based exit (15-day swing time stop)
    return last, float(closes[last]), "time_exit"


# ---------------------------------------------------------------------------
# Per-Symbol Walk-Forward Loop
# ---------------------------------------------------------------------------

def backtest_symbol(strategy_module, symbol, price_data, backtest_days, nifty_regime=None):
    """
    Walk-forward backtest for one individual stock symbol.
    """
    required_regime = getattr(strategy_module, "REQUIRED_REGIME", None)
    trades = []
    index = max(MIN_WARMUP_ROWS, len(price_data) - backtest_days)
    last_signal_index = len(price_data) - 2

    while index <= last_signal_index:
        # Generate signal strictly with data up to current day's Close
        signal = strategy_module.generate_signal(price_data.iloc[:index + 1])

        if not signal:
            index += 1
            continue

        # Market Regime Filter: If strategy requires 'Bullish', skip trades on Bearish/Neutral days
        if required_regime is not None and nifty_regime is not None:
            signal_date = price_data.index[index]
            signal_date_norm = pd.Timestamp(signal_date).normalize()
            day_regime = nifty_regime.get(signal_date_norm)
            if day_regime is None:
                try:
                    day_regime = nifty_regime.iloc[
                        nifty_regime.index.get_indexer([signal_date_norm], method="pad")[0]
                    ]
                except Exception:
                    day_regime = None
            if day_regime != required_regime:
                index += 1
                continue

        signal_entry = float(signal["Entry"])
        stop = float(signal["StopLoss"])
        target = float(signal["Target"])

        planned_risk = signal_entry - stop
        planned_reward = target - signal_entry

        if planned_risk <= 0 or planned_reward <= 0:
            index += 1
            continue

        entry_index = index + 1
        actual_entry = float(price_data["Open"].iloc[entry_index])

        # Skip if overnight opening gap destroys the risk/reward geometry
        if actual_entry <= stop or actual_entry >= target:
            index += 1
            continue

        actual_risk = actual_entry - stop
        actual_reward = target - actual_entry

        if actual_risk <= 0 or actual_reward <= 0:
            index += 1
            continue

        actual_rr = actual_reward / actual_risk

        # Strategy-level override of the minimum acceptable executable RR
        min_rr = float(getattr(strategy_module, "MIN_ACTUAL_RR", MIN_ACTUAL_RR))
        if actual_rr < min_rr:
            index += 1
            continue

        outcome = simulate_trade(price_data, entry_index, stop, target)
        if outcome is None:
            index += 1
            continue

        exit_index, exit_price, reason = outcome
        cost = actual_entry * ROUND_TRIP_COST_PCT / 100
        pnl = exit_price - actual_entry - cost

        trades.append({
            "Strategy": strategy_module.NAME,
            "Stock": symbol.replace(".NS", ""),
            "SignalDate": price_data.index[index].strftime("%Y-%m-%d"),
            "EntryDate": price_data.index[entry_index].strftime("%Y-%m-%d"),
            "SignalPrice": round(signal_entry, 2),
            "EntryPrice": round(actual_entry, 2),
            "GapPct": round((actual_entry / signal_entry - 1) * 100, 2),
            "StopLoss": round(stop, 2),
            "Target": round(target, 2),
            "PlannedRR": round(planned_reward / planned_risk, 2),
            "ActualRR": round(actual_rr, 2),
            "ExitDate": price_data.index[exit_index].strftime("%Y-%m-%d"),
            "ExitPrice": round(exit_price, 2),
            "ExitReason": reason,
            "HoldingDays": exit_index - entry_index + 1,
            "RiskPerShare": round(actual_risk, 2),
            "RewardPerShare": round(actual_reward, 2),
            "ReturnPct": round(pnl / actual_entry * 100, 2),
            "RMultiple": round(pnl / actual_risk, 2),          # Actual risk based R-multiple
            "PlannedRMultiple": round(pnl / planned_risk, 2),  # Planned risk based (for comparison)
        })

        # Avoid overlapping trades on the same stock
        index = max(exit_index, index + 1)

    return trades


# ---------------------------------------------------------------------------
# Statistics & Performance Metrics
# ---------------------------------------------------------------------------

def max_consecutive_losses(df):
    """Calculates the maximum consecutive losing streak in trade history."""
    ordered = df.sort_values("EntryDate")["ReturnPct"] <= 0
    longest = 0
    for is_loss, group in itertools.groupby(ordered):
        if is_loss:
            longest = max(longest, len(list(group)))
    return longest


def max_drawdown(df):
    """Calculates peak-to-trough maximum drawdown on cumulative percentage returns."""
    if df.empty:
        return 0.0
    ordered = df.sort_values("EntryDate")
    equity = (1 + ordered["ReturnPct"] / 100).cumprod()
    drawdown = (equity / equity.cummax() - 1) * 100
    return round(float(drawdown.min()), 2)


def yearly_performance(df):
    """Generates annual performance breakdown."""
    if df.empty:
        return pd.DataFrame()
    x = df.copy()
    x["EntryDate"] = pd.to_datetime(x["EntryDate"])
    x["Year"] = x["EntryDate"].dt.year
    return (
        x.groupby("Year")
        .agg(
            Trades=("ReturnPct", "size"),
            WinRate=("ReturnPct", lambda s: round((s > 0).mean() * 100, 1)),
            ReturnPct=("ReturnPct", "sum"),
            AvgR=("RMultiple", "mean"),
        )
        .reset_index()
        .round(2)
    )


def monthly_performance(df):
    """Generates monthly performance breakdown."""
    if df.empty:
        return pd.DataFrame()
    x = df.copy()
    x["EntryDate"] = pd.to_datetime(x["EntryDate"])
    x["Month"] = x["EntryDate"].dt.to_period("M").astype(str)
    return (
        x.groupby("Month")
        .agg(
            Trades=("ReturnPct", "size"),
            ReturnPct=("ReturnPct", "sum"),
            WinRate=("ReturnPct", lambda s: round((s > 0).mean() * 100, 1)),
        )
        .reset_index()
        .round(2)
    )


def summarize(name, df):
    """
    Computes key executive metrics across all backtest trades for a strategy.
    """
    if df.empty:
        return {"Strategy": name, "Trades": 0}

    wins = df[df["ReturnPct"] > 0]
    losses = df[df["ReturnPct"] <= 0]
    gross_loss = abs(losses["ReturnPct"].sum())
    reasons = df["ExitReason"]

    return {
        "Strategy": name,
        "Trades": len(df),
        "WinRate%": round(len(wins) / len(df) * 100, 1),
        "AvgWin%": round(wins["ReturnPct"].mean(), 2) if len(wins) else 0.0,
        "AvgLoss%": round(losses["ReturnPct"].mean(), 2) if len(losses) else 0.0,
        "Expectancy%": round(df["ReturnPct"].mean(), 2),
        "AvgR": round(df["RMultiple"].mean(), 2),
        "ProfitFactor": round(wins["ReturnPct"].sum() / gross_loss, 2) if gross_loss else float("inf"),
        "TotalReturn%": round(df["ReturnPct"].sum(), 1),
        "MaxDrawdown%": max_drawdown(df),
        "MaxLossStreak": max_consecutive_losses(df),
        "AvgHoldDays": round(df["HoldingDays"].mean(), 1),
        "AvgActualRR": round(df["ActualRR"].mean(), 2),
        "AvgGap%": round(df["GapPct"].mean(), 2),
        "StopHit%": round(reasons.str.startswith("stop").mean() * 100, 1),
        "TargetHit%": round(reasons.str.startswith("target").mean() * 100, 1),
        "TimeExit%": round((reasons == "time_exit").mean() * 100, 1),
    }


# ---------------------------------------------------------------------------
# Runner & Batch Loader
# ---------------------------------------------------------------------------

def run_backtest(strategy_module, histories, days, nifty_regime=None):
    """Runs walk-forward backtest across all loaded stock price histories."""
    trades = []
    for symbol, data in histories.items():
        trades.extend(backtest_symbol(strategy_module, symbol, data, days, nifty_regime))
    return pd.DataFrame(trades)


def load_price_histories(symbols, period):
    """
    Downloads historical price data concurrently for the entire stock universe.
    """
    from core.ohlcv_data import fetch_price_histories_batch
    histories = fetch_price_histories_batch(symbols, period=period, max_workers=10, show_progress=True)
    return {k: v for k, v in histories.items() if len(v) > MIN_WARMUP_ROWS + 20}


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(description="Backtest swing trading strategies")
    parser.add_argument("strategy", nargs="?", default="all", help="strategy key, or 'all'")
    parser.add_argument("--universe", choices=["nifty50", "nifty100"], default="nifty100")
    parser.add_argument("--stocks", type=int, default=None, help="limit number of stocks (quick test)")
    parser.add_argument("--days", type=int, default=DEFAULT_BACKTEST_DAYS, help="trading days to test")
    parser.add_argument("--baseline", action="store_true",
                        help="also run random-entry baselines (same stop/target/hold/cost rules)")
    parser.add_argument("--min-rr", type=float, default=MIN_ACTUAL_RR,
                        help="minimum executable RR to accept a trade (default: %(default)s)")
    return parser.parse_args()


def main():
    global MIN_ACTUAL_RR

    args = parse_arguments()
    MIN_ACTUAL_RR = args.min_rr

    available = discover_strategies()

    if args.strategy == "all":
        selected = dict(available)
    elif args.strategy in available:
        selected = {args.strategy: available[args.strategy]}
    else:
        print(f"Unknown strategy '{args.strategy}'. Available: {list(available.keys())}")
        return

    if args.baseline:
        selected["baseline_random"] = RandomEntryBaseline("Baseline: Random Entry", uptrend_only=False)
        selected["baseline_random_uptrend"] = RandomEntryBaseline(
            "Baseline: Random (Close > SMA200)", uptrend_only=True)

    symbols = get_nifty50_symbols() if args.universe == "nifty50" else get_nifty100_symbols()
    if args.stocks:
        symbols = symbols[:args.stocks]

    summaries = []
    trade_frames = []

    # Pre-compute Nifty regime series (used to filter regime-specific strategies)
    print("\nFetching Nifty regime data ...")
    try:
        nifty_data = fetch_price_history("^NSEI", period="3y")
        nifty_regime = compute_daily_regime(nifty_data) if nifty_data is not None else None
        if nifty_regime is not None:
            # Normalize index to midnight for clean date matching
            nifty_regime.index = pd.to_datetime(nifty_regime.index).normalize()
            print(f"  Nifty regime series: {len(nifty_regime)} days")
    except Exception as e:
        nifty_regime = None
        print(f"  [!] Could not fetch Nifty regime: {e}")

    # Pre-compute price histories ONCE for all strategies (3y covers all EMA/ATR warmup requirements)
    print(f"\nLoading price data for {len(symbols)} stocks (shared across all strategies) ...")
    histories = load_price_histories(symbols, "3y")

    for _, strategy_module in selected.items():
        print(f"\nBacktesting {strategy_module.NAME} ...")
        req = getattr(strategy_module, "REQUIRED_REGIME", None)
        if req:
            print(f"  (Regime filter active: only '{req}' days counted)")
        trades_df = run_backtest(strategy_module, histories, args.days, nifty_regime)
        summaries.append(summarize(strategy_module.NAME, trades_df))
        if not trades_df.empty:
            trade_frames.append(trades_df)

    summary_df = pd.DataFrame(summaries)

    print("\n" + "=" * 110)
    print(f"Backtest: last {args.days} trading days, {len(symbols)} stocks, "
          f"max hold {MAX_HOLD_DAYS} days, cost {ROUND_TRIP_COST_PCT}% round trip, "
          f"min actual RR {MIN_ACTUAL_RR}")
    print("=" * 110)
    if not summary_df.empty:
        print(summary_df.to_string(index=False))

    for row in summaries:
        if row["Trades"] < MIN_TRADES_FOR_CONFIDENCE:
            print(f"\n[!] {row['Strategy']}: only {row['Trades']} trades — sample too small to trust.")

    print("\nNote: today's index constituents are used for the whole period (survivorship bias),")
    print("so real results are usually somewhat worse than this.")

    if args.baseline:
        print("\nA strategy is only interesting if it clearly beats the 'Baseline' rows")
        print("(especially 'Random (Close > SMA200)') on Expectancy%, AvgR and ProfitFactor.")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    summary_df.to_csv(os.path.join(output_dir, "backtest_summary.csv"), index=False)

    if trade_frames:
        all_trades = pd.concat(trade_frames, ignore_index=True)
        all_trades.to_csv(os.path.join(output_dir, "backtest_trades.csv"), index=False)

        yearly_frames, monthly_frames = [], []
        for name, group in all_trades.groupby("Strategy"):
            yearly = yearly_performance(group)
            if not yearly.empty:
                yearly.insert(0, "Strategy", name)
                yearly_frames.append(yearly)
            monthly = monthly_performance(group)
            if not monthly.empty:
                monthly.insert(0, "Strategy", name)
                monthly_frames.append(monthly)

        if yearly_frames:
            pd.concat(yearly_frames, ignore_index=True).to_csv(
                os.path.join(output_dir, "backtest_yearly.csv"), index=False)
        if monthly_frames:
            pd.concat(monthly_frames, ignore_index=True).to_csv(
                os.path.join(output_dir, "backtest_monthly.csv"), index=False)

    print(f"\nSaved results to {output_dir}")
    print("  backtest_summary.csv  — per-strategy summary")
    print("  backtest_trades.csv   — every individual trade")
    print("  backtest_yearly.csv   — year-by-year breakdown")
    print("  backtest_monthly.csv  — month-by-month breakdown")


if __name__ == "__main__":
    main()
