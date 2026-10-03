"""
Walk-Forward Backtesting Engine for Swing Trading System.
=========================================================

Features:
1. Zero Lookahead Bias (Walk-Forward Design):
   - Signal generation on day N uses strictly data available up to day N's Close.
   - Actual trade entry occurs on day N+1's Open (9:15 AM IST).
2. Realistic Friction & Gap Handling:
   - Overnight gaps breaching Stop or Target skip the trade.
   - Executable RR < 1.95 skips the trade.
   - 0.10% round-trip friction applied to every trade.
3. Persistent Cumulative Logging:
   - Backtest results and trade records are appended with `RunDate` and `RunTime` timestamps.
4. Integrated Market Regime Analysis:
   - Automatically runs `regime_split` analysis on completion and appends regime-tagged
     trades and regime summaries to `outputs/`.
"""

import argparse
import importlib
import itertools
import os
import pkgutil
import zlib
from datetime import datetime

import pandas as pd

import strategies
from core.ohlcv_data import fetch_price_history, get_nifty50_symbols, get_nifty100_symbols
from core.market_regime import compute_daily_regime
from regime_split import tag_trades_with_regime, print_regime_breakdown, compute_regime_summary


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
    Deterministic pseudo-random baseline strategy to prove trading edge.
    """

    def __init__(self, name, uptrend_only, probability=BASELINE_ENTRY_PROBABILITY):
        self.NAME = name
        self.uptrend_only = uptrend_only
        self.probability = probability

    def generate_signal(self, price_data):
        if len(price_data) < BASELINE_TREND_PERIOD:
            return None

        close = float(price_data["Close"].iloc[-1])
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
    Returns (exit_index, exit_price, exit_reason).
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
        signal = strategy_module.generate_signal(price_data.iloc[:index + 1])

        if not signal:
            index += 1
            continue

        # Market Regime Filter: If strategy requires 'Bullish', skip trades on non-matching days
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
            "PlannedRMultiple": round(pnl / planned_risk, 2),  # Planned risk based
        })

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


def append_dataframe_to_csv(df, filepath):
    """
    Appends a DataFrame to a CSV file safely.
    If the file exists with the same schema, appends rows.
    If the existing file has an older schema, concatenates and aligns columns cleanly.
    """
    if df is None or df.empty:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.isfile(filepath):
        try:
            existing_df = pd.read_csv(filepath)
            if list(existing_df.columns) == list(df.columns):
                df.to_csv(filepath, mode="a", header=False, index=False)
            else:
                combined = pd.concat([existing_df, df], ignore_index=True)
                combined.to_csv(filepath, mode="w", index=False)
        except Exception:
            df.to_csv(filepath, mode="a", header=False, index=False)
    else:
        df.to_csv(filepath, mode="w", header=True, index=False)


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
    parser.add_argument("--min-rr", "--target-rr", dest="min_rr", type=float, default=MIN_ACTUAL_RR,
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

    # Timestamp for this backtesting run
    now = datetime.now()
    run_date = now.strftime("%Y-%m-%d")
    run_time = now.strftime("%H:%M:%S")

    # Pre-compute Nifty regime series
    print("\nFetching Nifty regime data ...")
    try:
        nifty_data = fetch_price_history("^NSEI", period="3y")
        nifty_regime = compute_daily_regime(nifty_data) if nifty_data is not None else None
        if nifty_regime is not None:
            nifty_regime.index = pd.to_datetime(nifty_regime.index).normalize()
            print(f"  Nifty regime series: {len(nifty_regime)} days")
    except Exception as e:
        nifty_regime = None
        print(f"  [!] Could not fetch Nifty regime: {e}")

    # Load price histories ONCE for all strategies
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

    # ---------------------------------------------------------------------------
    # Persistent Saving (Append with Date & Time)
    # ---------------------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Summary CSV (Append with RunDate, RunTime)
    if not summary_df.empty:
        summary_to_save = summary_df.copy()
        summary_to_save.insert(0, "RunDate", run_date)
        summary_to_save.insert(1, "RunTime", run_time)
        summary_to_save.insert(2, "TestDays", args.days)
        summary_to_save.insert(3, "Universe", args.universe)
        append_dataframe_to_csv(summary_to_save, os.path.join(output_dir, "backtest_summary.csv"))

    if trade_frames:
        all_trades = pd.concat(trade_frames, ignore_index=True)
        all_trades_to_save = all_trades.copy()
        all_trades_to_save.insert(0, "RunDate", run_date)
        all_trades_to_save.insert(1, "RunTime", run_time)
        append_dataframe_to_csv(all_trades_to_save, os.path.join(output_dir, "backtest_trades.csv"))

        # 2. Yearly & Monthly breakdowns (Append with RunDate, RunTime)
        yearly_frames, monthly_frames = [], []
        for name, group in all_trades.groupby("Strategy"):
            yearly = yearly_performance(group)
            if not yearly.empty:
                yearly.insert(0, "Strategy", name)
                yearly.insert(0, "RunTime", run_time)
                yearly.insert(0, "RunDate", run_date)
                yearly_frames.append(yearly)
            monthly = monthly_performance(group)
            if not monthly.empty:
                monthly.insert(0, "Strategy", name)
                monthly.insert(0, "RunTime", run_time)
                monthly.insert(0, "RunDate", run_date)
                monthly_frames.append(monthly)

        if yearly_frames:
            append_dataframe_to_csv(pd.concat(yearly_frames, ignore_index=True),
                                    os.path.join(output_dir, "backtest_yearly.csv"))
        if monthly_frames:
            append_dataframe_to_csv(pd.concat(monthly_frames, ignore_index=True),
                                    os.path.join(output_dir, "backtest_monthly.csv"))

        # -----------------------------------------------------------------------
        # 3. Automatic Regime Split Execution
        # -----------------------------------------------------------------------
        if nifty_regime is not None:
            print("\n" + "=" * 70)
            print("AUTOMATIC MARKET REGIME BREAKDOWN ANALYSIS")
            print("=" * 70)
            tagged_trades = tag_trades_with_regime(all_trades, nifty_regime)
            print_regime_breakdown(tagged_trades)

            tagged_to_save = tagged_trades.copy()
            tagged_to_save.insert(0, "RunDate", run_date)
            tagged_to_save.insert(1, "RunTime", run_time)
            append_dataframe_to_csv(tagged_to_save, os.path.join(output_dir, "backtest_trades_with_regime.csv"))

            regime_summary_df = compute_regime_summary(tagged_trades)
            if not regime_summary_df.empty:
                regime_summary_df.insert(0, "RunDate", run_date)
                regime_summary_df.insert(1, "RunTime", run_time)
                regime_summary_df.insert(2, "TestDays", args.days)
                append_dataframe_to_csv(regime_summary_df, os.path.join(output_dir, "backtest_regime_summary.csv"))

    print(f"\nAppended backtest results to {output_dir}:")
    print("  backtest_summary.csv             — Cumulative per-strategy summaries with timestamps")
    print("  backtest_trades.csv              — All simulated individual trade logs")
    print("  backtest_trades_with_regime.csv  — Trades tagged with Bullish/Neutral/Bearish regime")
    print("  backtest_regime_summary.csv      — Performance breakdown by market regime")
    print("  backtest_yearly.csv              — Year-by-year performance")
    print("  backtest_monthly.csv             — Month-by-month performance")

    # Auto-sync all results to Google Drive folder
    try:
        from integrations.drive_sync import sync_all_outputs
        sync_all_outputs()
    except Exception as e:
        print(f"\n[Google Drive] Sync skipped: {e}")


if __name__ == "__main__":
    main()
