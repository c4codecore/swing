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

import numpy as np
import pandas as pd

import strategies
from core.ohlcv_data import fetch_price_history, get_nifty50_symbols, get_nifty100_symbols
from core.market_regime import compute_daily_regime, compute_market_breadth
from core.screener import MOMENTUM_LOOKBACK_DAYS
from core.trailing import chandelier_stop_levels
from core.ui import (
    Fore, Style, banner_box, header, sub_header, divider,
    badge_success, badge_error, badge_warn, badge_info, badge_match,
    bright_cyan, bright_yellow, bright_green, bright_red,
    bright_white, bright_magenta, dim, render_table, format_pct
)
from portfolio import simulate_portfolio
from regime_split import tag_trades_with_regime, print_regime_breakdown, compute_regime_summary


DEFAULT_HISTORY_PERIOD = "5y"
DEFAULT_BACKTEST_DAYS = 750
MIN_WARMUP_ROWS = 60
MAX_HOLD_DAYS = 15
ROUND_TRIP_COST_PCT = 0.30
MIN_TRADES_FOR_CONFIDENCE = 30
MIN_ACTUAL_RR = 1.95            # Trades where overnight gap shrinks actual RR below this are skipped
BOOTSTRAP_RESAMPLES = 2000
OUT_OF_SAMPLE_FRACTION = 0.3

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

def simulate_trailing_trade(price_data, entry_index, initial_stop, atr_multiple, atr_period, max_hold_days):
    opens = price_data["Open"].to_numpy(dtype=float)
    lows = price_data["Low"].to_numpy(dtype=float)
    closes = price_data["Close"].to_numpy(dtype=float)

    stops, _ = chandelier_stop_levels(price_data, entry_index, initial_stop, atr_multiple, atr_period)
    last = min(entry_index + max_hold_days - 1, len(price_data) - 1)

    for day in range(entry_index, last + 1):
        stop_in_force = float(stops[day])
        if day > entry_index and opens[day] <= stop_in_force:
            return day, float(opens[day]), "stop_gap"
        if lows[day] <= stop_in_force:
            reason = "stop_trailing" if stop_in_force > initial_stop else "stop"
            return day, stop_in_force, reason

    if last - entry_index + 1 < max_hold_days:
        return last, float(closes[last]), "end_of_data"

    return last, float(closes[last]), "time_exit"


def trade_excursions(price_data, entry_index, exit_index, entry_price, risk_per_share):
    window = price_data.iloc[entry_index:exit_index + 1]
    lowest_low = float(window["Low"].min())
    highest_high = float(window["High"].max())
    return (
        round((entry_price - lowest_low) / risk_per_share, 2),
        round((highest_high - entry_price) / risk_per_share, 2),
    )


def lookup_regime(nifty_regime, signal_date):
    if nifty_regime is None:
        return None
    signal_date_norm = pd.Timestamp(signal_date).normalize()
    day_regime = nifty_regime.get(signal_date_norm)
    if day_regime is not None:
        return day_regime
    try:
        position = nifty_regime.index.get_indexer([signal_date_norm], method="pad")[0]
        return nifty_regime.iloc[position] if position >= 0 else None
    except Exception:
        return None


# Maximum bars passed to generate_signal on each walk-forward step.
# EWM/EMA/MACD indicators converge within ~3x their span, so a 600-bar window
# gives < 0.5% error on EMA(200) while keeping each call O(600) not O(N).
# This converts the inner loop from O(N²) to O(N) for every strategy.
SIGNAL_WINDOW = 600


def backtest_symbol(strategy_module, symbol, price_data, backtest_days, nifty_regime=None, target_rr=None):
    required_regime = getattr(strategy_module, "REQUIRED_REGIME", None)
    is_trailing = getattr(strategy_module, "EXIT_MODE", "fixed") == "trailing"
    trades = []
    index = max(MIN_WARMUP_ROWS, len(price_data) - backtest_days)
    last_signal_index = len(price_data) - 2
    closes = price_data["Close"].to_numpy()

    # Build a fast numpy regime lookup array to avoid per-bar dict access.
    regime_array = None
    if nifty_regime is not None:
        dates_norm = pd.to_datetime(price_data.index).normalize()
        positions = nifty_regime.index.get_indexer(dates_norm, method="pad")
        regime_array = np.where(
            positions >= 0,
            nifty_regime.iloc[np.maximum(positions, 0)].to_numpy(),
            None,
        )

    while index <= last_signal_index:
        # ── Fix 1: regime pre-filter ────────────────────────────────────────
        # Check regime BEFORE calling generate_signal so we skip the expensive
        # indicator recomputation on days the strategy can never trade anyway.
        # For Bullish-gated strategies this skips ~49% of all bar iterations.
        day_regime = regime_array[index] if regime_array is not None else None
        if required_regime is not None and nifty_regime is not None and day_regime != required_regime:
            index += 1
            continue

        # ── Fix 2: sliding window ────────────────────────────────────────────
        # Pass a fixed-size tail instead of a growing slice starting at bar 0.
        # Prevents EWM/MACD/ADX from recomputing on an ever-longer series
        # (O(N²) → O(N × SIGNAL_WINDOW)).
        window_start = max(0, index + 1 - SIGNAL_WINDOW)
        signal = strategy_module.generate_signal(price_data.iloc[window_start:index + 1])

        if not signal:
            index += 1
            continue

        signal_entry = float(signal["Entry"])
        stop = float(signal["StopLoss"])
        planned_risk = signal_entry - stop
        if planned_risk <= 0:
            index += 1
            continue

        target = signal_entry + planned_risk * target_rr if target_rr and not is_trailing else float(signal["Target"])
        planned_reward = target - signal_entry
        if planned_reward <= 0:
            index += 1
            continue

        entry_index = index + 1
        actual_entry = float(price_data["Open"].iloc[entry_index])

        if actual_entry <= stop or (not is_trailing and actual_entry >= target):
            index += 1
            continue

        actual_risk = actual_entry - stop
        actual_reward = target - actual_entry
        if actual_risk <= 0 or (not is_trailing and actual_reward <= 0):
            index += 1
            continue

        if is_trailing:
            max_risk_expansion = float(getattr(strategy_module, "MAX_RISK_EXPANSION", 1.25))
            if actual_risk > planned_risk * max_risk_expansion:
                index += 1
                continue
            actual_rr = float("nan")
            outcome = simulate_trailing_trade(
                price_data, entry_index, stop,
                float(strategy_module.TRAIL_ATR_MULTIPLE),
                int(strategy_module.TRAIL_ATR_PERIOD),
                int(strategy_module.MAX_HOLD_DAYS),
            )
        else:
            actual_rr = actual_reward / actual_risk
            min_rr = float(getattr(strategy_module, "MIN_ACTUAL_RR", MIN_ACTUAL_RR))
            if actual_rr < min_rr:
                index += 1
                continue
            outcome = simulate_trade(price_data, entry_index, stop, target)

        if outcome is None:
            index += 1
            continue

        exit_index, exit_price, reason = outcome
        mae_r, mfe_r = trade_excursions(price_data, entry_index, exit_index, actual_entry, actual_risk)
        cost = actual_entry * ROUND_TRIP_COST_PCT / 100
        pnl = exit_price - actual_entry - cost
        momentum_60d = None
        if index >= MOMENTUM_LOOKBACK_DAYS:
            momentum_60d = round((closes[index] / closes[index - MOMENTUM_LOOKBACK_DAYS] - 1) * 100, 2)

        trades.append({
            "Strategy": strategy_module.NAME,
            "Stock": symbol.replace(".NS", ""),
            "SignalDate": price_data.index[index].strftime("%Y-%m-%d"),
            "EntryDate": price_data.index[entry_index].strftime("%Y-%m-%d"),
            "SignalPrice": round(signal_entry, 2),
            "EntryPrice": round(actual_entry, 2),
            "GapPct": round((actual_entry / signal_entry - 1) * 100, 2),
            "StopLoss": round(stop, 2),
            "Target": float("nan") if is_trailing else round(target, 2),
            "PlannedRR": float("nan") if is_trailing else round(planned_reward / planned_risk, 2),
            "ActualRR": float("nan") if is_trailing else round(actual_rr, 2),
            "ExitDate": price_data.index[exit_index].strftime("%Y-%m-%d"),
            "ExitPrice": round(exit_price, 2),
            "ExitReason": reason,
            "HoldingDays": exit_index - entry_index + 1,
            "RiskPerShare": round(actual_risk, 2),
            "RewardPerShare": float("nan") if is_trailing else round(actual_reward, 2),
            "ReturnPct": round(pnl / actual_entry * 100, 2),
            "RMultiple": round(pnl / actual_risk, 2),
            "PlannedRMultiple": round(pnl / planned_risk, 2),
            "MaeR": mae_r,
            "MfeR": mfe_r,
            "Momentum60D": momentum_60d,
            "Regime": day_regime,
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


def bootstrap_expectancy_ci(trades_df, resamples=BOOTSTRAP_RESAMPLES, seed=7):
    if len(trades_df) < 5:
        return None, None
    week_keys = pd.to_datetime(trades_df["SignalDate"]).dt.to_period("W").astype(str)
    weekly_returns = [group.to_numpy() for _, group in trades_df["ReturnPct"].groupby(week_keys)]
    rng = np.random.default_rng(seed)
    sample_means = []
    for _ in range(resamples):
        picks = rng.integers(0, len(weekly_returns), len(weekly_returns))
        sample_means.append(np.concatenate([weekly_returns[i] for i in picks]).mean())
    low, high = np.percentile(sample_means, [2.5, 97.5])
    return round(float(low), 2), round(float(high), 2)


def apply_daily_cap(trades_df, max_per_day):
    if trades_df.empty or not max_per_day:
        return trades_df
    ranked = trades_df.sort_values("Momentum60D", ascending=False, na_position="last")
    capped = ranked.groupby(["Strategy", "SignalDate"], sort=False).head(max_per_day)
    return capped.sort_values(["Strategy", "SignalDate"]).reset_index(drop=True)


def split_in_and_out_of_sample(trades_df, out_of_sample_fraction=OUT_OF_SAMPLE_FRACTION):
    signal_dates = sorted(trades_df["SignalDate"].unique())
    if len(signal_dates) < 4:
        return trades_df, trades_df.iloc[0:0]
    cutoff = signal_dates[int(len(signal_dates) * (1 - out_of_sample_fraction))]
    return trades_df[trades_df["SignalDate"] < cutoff], trades_df[trades_df["SignalDate"] >= cutoff]


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
    ci_low, ci_high = bootstrap_expectancy_ci(df)

    return {
        "Strategy": name,
        "Trades": len(df),
        "WinRate%": round(len(wins) / len(df) * 100, 1),
        "AvgWin%": round(wins["ReturnPct"].mean(), 2) if len(wins) else 0.0,
        "AvgLoss%": round(losses["ReturnPct"].mean(), 2) if len(losses) else 0.0,
        "Expectancy%": round(df["ReturnPct"].mean(), 2),
        "Exp%CI95Low": ci_low,
        "Exp%CI95High": ci_high,
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

def run_backtest(strategy_module, histories, days, nifty_regime=None, target_rr=None,
                 max_workers=None):
    """Runs walk-forward backtest across all loaded stock price histories.
    Stocks are independent so we process them in parallel with a thread pool.
    ThreadPoolExecutor is safe here because pandas/numpy release the GIL during
    most numerical operations, giving real concurrency on multi-core machines.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import os

    if max_workers is None:
        max_workers = min(8, (os.cpu_count() or 2))

    all_trades = []
    symbols = list(histories.keys())

    def _worker(sym):
        return backtest_symbol(strategy_module, sym, histories[sym], days, nifty_regime, target_rr)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_worker, sym): sym for sym in symbols}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                all_trades.extend(result)

    return pd.DataFrame(all_trades)


def load_price_histories(symbols, period):
    """
    Downloads historical price data concurrently for the entire stock universe.
    Pre-cleans every DataFrame once so strategies never need to call clean_ohlcv again.
    """
    from core.ohlcv_data import fetch_price_histories_batch
    from core.utils import clean_ohlcv
    raw = fetch_price_histories_batch(symbols, period=period, max_workers=10, show_progress=True)
    histories = {}
    for k, v in raw.items():
        if len(v) <= MIN_WARMUP_ROWS + 20:
            continue
        cleaned = clean_ohlcv(v)
        histories[k] = cleaned if cleaned is not None and len(cleaned) > MIN_WARMUP_ROWS + 20 else v
    return histories


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
    parser.add_argument("--period", default=DEFAULT_HISTORY_PERIOD,
                        help="yfinance history to download; must cover --days plus ~250 warmup bars (default: %(default)s)")
    parser.add_argument("--regime", choices=["basic", "strict"], default="strict",
                        help="basic: Nifty EMA20/EMA50 only. strict: also rising EMA50 and market breadth >= 50%%")
    parser.add_argument("--max-per-day", type=int, default=None,
                        help="keep only the N highest 60-day-momentum signals per strategy per day")
    parser.add_argument("--force-rr", type=float, default=None,
                        help="replace each strategy's target with entry + RR x risk (test 1.5 vs 2.0 vs 3.0)")
    parser.add_argument("--capital", type=float, default=1_000_000, help="starting capital for the portfolio simulation")
    parser.add_argument("--risk-pct", type=float, default=1.0, help="percent of equity risked per trade in the portfolio simulation")
    parser.add_argument("--max-positions", type=int, default=6, help="maximum simultaneous positions in the portfolio simulation")
    parser.add_argument("--max-hold", type=int, default=MAX_HOLD_DAYS, help="maximum holding days (default: %(default)s)")
    parser.add_argument("--baseline", action="store_true",
                        help="also run random-entry baselines (same stop/target/hold/cost rules)")
    parser.add_argument("--min-rr", "--target-rr", dest="min_rr", type=float, default=None,
                        help="minimum executable RR to accept a trade (default: 1.95, or 97.5%% of --force-rr)")
    return parser.parse_args()


def print_excursion_report(trade_frames):
    print(banner_box("STOP & TARGET DIAGNOSTICS (MAE/MFE in R Multiples)", width=100))
    for trades_df in trade_frames:
        name = trades_df["Strategy"].iloc[0]
        stopped = trades_df[trades_df["ExitReason"].str.startswith("stop")]
        timed = trades_df[trades_df["ExitReason"] == "time_exit"]
        reached_one_r = (stopped["MfeR"] >= 1.0).mean() * 100 if len(stopped) else 0.0
        median_mae_winners = trades_df[trades_df["ReturnPct"] > 0]["MaeR"].median()
        time_mfe = timed["MfeR"].median() if len(timed) else float("nan")

        name_str = f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}{name:<28}{Style.RESET_ALL}"
        stopped_str = f"stopped={bright_red(f'{len(stopped):>4}')}"
        r1_color = bright_yellow if reached_one_r > 30 else bright_green
        reached_str = f"reached-1R={r1_color(f'{reached_one_r:>5.1f}%')}"
        mae_str = f"med-MAE-winners={bright_cyan(f'{median_mae_winners:>5.2f}R')}"
        mfe_str = f"time-exit-med-MFE={bright_green(f'{time_mfe:>5.2f}R')}"
        print(f"  {name_str}  {stopped_str}  {reached_str}  {mae_str}  {mfe_str}")


def print_confluence_report(trade_frames):
    all_trades = pd.concat(trade_frames, ignore_index=True)
    if all_trades["Strategy"].nunique() < 2:
        return
    strategies_per_signal = all_trades.groupby(["Stock", "SignalDate"])["Strategy"].transform("nunique")
    print(banner_box("MULTI-STRATEGY CONFLUENCE REPORT (Signals Fired by Multiple Strategies Concurrently)", width=100))
    for label, subset in (
        ("Fired by 1 strategy", all_trades[strategies_per_signal == 1]),
        ("Fired by 2+ strategies", all_trades[strategies_per_signal >= 2]),
    ):
        if subset.empty:
            continue
        wins = subset[subset["ReturnPct"] > 0]["ReturnPct"].sum()
        losses = abs(subset[subset["ReturnPct"] <= 0]["ReturnPct"].sum())
        profit_factor = round(wins / losses, 2) if losses else float("inf")
        winrate = (subset["ReturnPct"] > 0).mean() * 100
        exp = subset["ReturnPct"].mean()

        lbl_str = f"{bright_cyan(f'{label:<24}')}"
        trades_str = f"Trades={bright_white(f'{len(subset):>5}')}"
        wr_color = bright_green if winrate >= 50 else bright_red
        wr_str = f"WinRate%={wr_color(f'{winrate:>5.1f}')}"
        exp_color = bright_green if exp > 0 else bright_red
        exp_str = f"Expectancy%={exp_color(f'{exp:>6.2f}')}"
        pf_color = bright_green if profit_factor >= 1.5 else (bright_yellow if profit_factor >= 1.0 else bright_red)
        pf_str = f"ProfitFactor={pf_color(f'{profit_factor:>5}')}"
        print(f"  {lbl_str}  {trades_str}  {wr_str}  {exp_str}  {pf_str}")


def print_portfolio_report(trade_frames, args):
    print(banner_box("PORTFOLIO SIMULATION",
                     subtitle=f"Starting Capital: Rs {args.capital:,.0f} | Risk: {args.risk_pct}% per trade | Max Positions: {args.max_positions} | Ranking: 60D Momentum",
                     width=100))
    rows = []
    for trades_df in trade_frames:
        summary, equity_curve = simulate_portfolio(
            trades_df, args.capital, args.risk_pct, args.max_positions)
        if summary.empty:
            continue
        summary.insert(0, "Strategy", trades_df["Strategy"].iloc[0])
        rows.append(summary)
    if not rows:
        return None
    portfolio_summary = pd.concat(rows, ignore_index=True)
    print(render_table(portfolio_summary))
    return portfolio_summary


def print_in_and_out_of_sample(trade_frames):
    print(banner_box("IN-SAMPLE (Older Signals) vs OUT-OF-SAMPLE (Recent Signals)", width=100))
    for trades_df in trade_frames:
        name = trades_df["Strategy"].iloc[0]
        in_sample, out_of_sample = split_in_and_out_of_sample(trades_df)
        for label, part in (("in-sample ", in_sample), ("out-sample", out_of_sample)):
            if part.empty:
                continue
            row = summarize(name, part)
            name_str = f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}{name:<28}{Style.RESET_ALL}"
            lbl_str = f"{bright_cyan(label)}"
            trades_count = row["Trades"]
            t_str = f"Trades={bright_white(f'{trades_count:>4}')}"
            wr_val = row["WinRate%"]
            wr_color = bright_green if wr_val >= 50 else bright_red
            wr_str = f"WinRate%={wr_color(f'{wr_val:>5}')}"
            exp_val = row["Expectancy%"]
            exp_color = bright_green if exp_val > 0 else bright_red
            exp_str = f"Expectancy%={exp_color(f'{exp_val:>6}')}"
            pf_val = row["ProfitFactor"]
            pf_color = bright_green if pf_val >= 1.5 else (bright_yellow if pf_val >= 1.0 else bright_red)
            pf_str = f"ProfitFactor={pf_color(f'{pf_val:>5}')}"
            print(f"  {name_str} {lbl_str}  {t_str}  {wr_str}  {exp_str}  {pf_str}")


def main():
    global MIN_ACTUAL_RR, MAX_HOLD_DAYS

    args = parse_arguments()
    if args.min_rr is not None:
        MIN_ACTUAL_RR = args.min_rr
    elif args.force_rr:
        MIN_ACTUAL_RR = round(0.975 * args.force_rr, 3)
    MAX_HOLD_DAYS = args.max_hold

    available = discover_strategies()

    if args.strategy == "all":
        selected = dict(available)
    elif args.strategy in available:
        selected = {args.strategy: available[args.strategy]}
    else:
        print(f"\n  {badge_error('Strategy')} Unknown strategy '{bright_yellow(args.strategy)}'. Available: {list(available.keys())}\n")
        return

    print(banner_box("SWING TRADING SYSTEM - STRATEGY BACKTESTER",
                     subtitle=f"Strategy: {args.strategy} | Universe: {args.universe} | Test Days: {args.days} | Max Hold: {MAX_HOLD_DAYS}d | Cost: {ROUND_TRIP_COST_PCT}%",
                     width=100))

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

    print(f"\n  {bright_cyan('Universe:')} Loading price data for {bright_yellow(str(len(symbols)))} stocks (shared across all strategies) ...")
    histories = load_price_histories(symbols, args.period)

    print(f"\n  {bright_cyan('Regime:')} Building Nifty regime series ...")
    nifty_regime = None
    try:
        nifty_data = fetch_price_history("^NSEI", period=args.period)
        if nifty_data is not None:
            breadth = compute_market_breadth(histories) if args.regime == "strict" else None
            nifty_regime = compute_daily_regime(nifty_data, breadth)
            nifty_regime.index = pd.to_datetime(nifty_regime.index).normalize()
            counts = nifty_regime.tail(args.days).value_counts().to_dict()
            print(f"  {bright_white('Regime mode:')} {bright_yellow(args.regime)}. Days in test window: {Fore.LIGHTMAGENTA_EX}{counts}{Style.RESET_ALL}")
    except Exception as e:
        print(f"  {badge_warn('Regime')} Could not build Nifty regime: {dim(str(e))}")

    needs_regime = [m.NAME for m in selected.values() if getattr(m, "REQUIRED_REGIME", None)]
    if needs_regime and nifty_regime is None:
        print(f"\n  {badge_error('Regime')} Nifty regime data is unavailable, but these strategies need it:")
        for name in needs_regime:
            print(f"    - {bright_yellow(name)}")
        print("  Stopping instead of silently running them on every market day. Check the network and rerun.\n")
        return

    import time
    for _, strategy_module in selected.items():
        print(f"\n  {bright_cyan('Backtesting')} {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{strategy_module.NAME}{Style.RESET_ALL} ...")
        
        # Performance: apply monkey-patch directly to the strategy module's namespace
        # because 'from core.utils import clean_ohlcv' binds locally in each strategy.
        if hasattr(strategy_module, "clean_ohlcv"):
            strategy_module.clean_ohlcv = lambda df, *a, **kw: df
        if hasattr(strategy_module, "remove_forming_candle"):
            strategy_module.remove_forming_candle = lambda data, *a, **kw: data

        req = getattr(strategy_module, "REQUIRED_REGIME", None)
        if req:
            regime_note = f"(Regime filter active: only '{req}' days counted)"
            print(f"    {dim(regime_note)}")
        
        start_time = time.time()
        trades_df = run_backtest(strategy_module, histories, args.days, nifty_regime, args.force_rr)
        elapsed = time.time() - start_time
        print(f"    {bright_green('Completed')} in {bright_white(f'{elapsed:.2f}')} seconds")
        
        trades_df = apply_daily_cap(trades_df, args.max_per_day)
        summaries.append(summarize(strategy_module.NAME, trades_df))
        if not trades_df.empty:
            trade_frames.append(trades_df)

    summary_df = pd.DataFrame(summaries)

    print(banner_box("BACKTEST PERFORMANCE SUMMARY",
                     subtitle=f"Last {args.days} trading days | {len(symbols)} stocks | Max hold {MAX_HOLD_DAYS}d | Cost {ROUND_TRIP_COST_PCT}% | Min RR {MIN_ACTUAL_RR}",
                     width=100))
    if not summary_df.empty:
        print(render_table(summary_df))

    for row in summaries:
        if row["Trades"] < MIN_TRADES_FOR_CONFIDENCE:
            print(f"\n  {badge_warn('Sample Size')} {bright_yellow(row['Strategy'])}: only {row['Trades']} trades - sample too small to trust.")
        elif row.get("Exp%CI95Low") is not None and row["Exp%CI95Low"] <= 0:
            print(f"\n  {badge_warn('Statistical Edge')} {bright_yellow(row['Strategy'])}: expectancy 95% CI includes zero "
                  f"({row['Exp%CI95Low']}% to {row['Exp%CI95High']}%) - edge not statistically proven.")

    print_in_and_out_of_sample(trade_frames)
    portfolio_summary = None
    if trade_frames:
        print_excursion_report(trade_frames)
        print_confluence_report(trade_frames)
        portfolio_summary = print_portfolio_report(trade_frames, args)

    bias_note = "Note: today's index constituents are used for the whole period (survivorship bias), so live performance may vary."
    print(f"\n  {dim(bias_note)}")

    if args.baseline:
        print(f"  {bright_cyan('A strategy is only interesting if it clearly beats the \"Baseline\" rows on Expectancy%, AvgR, and ProfitFactor.')}\n")

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
            print(banner_box("AUTOMATIC MARKET REGIME BREAKDOWN ANALYSIS", width=80))
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

    if portfolio_summary is not None and not portfolio_summary.empty:
        portfolio_to_save = portfolio_summary.copy()
        portfolio_to_save.insert(0, "RunDate", run_date)
        portfolio_to_save.insert(1, "RunTime", run_time)
        append_dataframe_to_csv(portfolio_to_save, os.path.join(output_dir, "backtest_portfolio_summary.csv"))

    print(banner_box("PERSISTENT EXPORT ARTIFACTS", subtitle=f"Appended backtest results to: {output_dir}", width=80))
    artifacts = [
        ("backtest_summary.csv", "Cumulative per-strategy summaries with timestamps"),
        ("backtest_trades.csv", "All simulated individual trade logs"),
        ("backtest_trades_with_regime.csv", "Trades tagged with Bullish/Neutral/Bearish regime"),
        ("backtest_regime_summary.csv", "Performance breakdown by market regime"),
        ("backtest_yearly.csv", "Year-by-year performance"),
        ("backtest_monthly.csv", "Month-by-month performance"),
        ("backtest_portfolio_summary.csv", "Capital-limited portfolio simulation per strategy"),
    ]
    for filename, desc in artifacts:
        print(f"  {bright_cyan(f'{filename:<34}')} {dim(desc)}")

    # Auto-sync all results to Google Drive folder
    try:
        from integrations.drive_sync import sync_all_outputs
        sync_all_outputs()
    except Exception as e:
        print(f"\n  {badge_warn('Google Drive')} Sync skipped: {dim(str(e))}")


if __name__ == "__main__":
    main()
