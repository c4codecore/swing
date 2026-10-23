"""
Splits backtest trades by Nifty's regime on each trade's entry date.
Evaluates whether a strategy only wins when the broader index is rising.

Regimes:
- Bullish: Nifty Close > 50 EMA and 20 EMA > 50 EMA
- Bearish: Nifty Close < 50 EMA and 20 EMA < 50 EMA
- Neutral: Anything else
"""

import argparse
import os
from datetime import datetime
import pandas as pd

from core.market_regime import NIFTY_INDEX_SYMBOL, compute_daily_regime
from core.ohlcv_data import fetch_price_history


DEFAULT_TRADES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "backtest_trades.csv")
NIFTY_FETCH_PERIOD = "3y"
MIN_TRADES_FOR_CONFIDENCE = 30


def tag_trades_with_regime(trades_df, regime_series):
    if trades_df.empty:
        return trades_df
    if "Regime" in trades_df.columns:
        return trades_df.copy()

    date_column = "SignalDate" if "SignalDate" in trades_df.columns else "EntryDate"
    trades_df = trades_df.copy()
    trades_df["TradeDate_DT"] = pd.to_datetime(trades_df[date_column]).astype("datetime64[s]")

    regime_df = regime_series.rename("Regime").reset_index()
    regime_df.columns = ["RegimeDate", "Regime"]
    regime_df["RegimeDate"] = pd.to_datetime(regime_df["RegimeDate"]).astype("datetime64[s]")
    regime_df = regime_df.sort_values("RegimeDate")

    tagged = pd.merge_asof(
        trades_df.sort_values("TradeDate_DT"), regime_df,
        left_on="TradeDate_DT", right_on="RegimeDate", direction="backward",
    )
    return tagged.drop(columns=["TradeDate_DT", "RegimeDate"], errors="ignore")


def compute_regime_summary(tagged_trades):
    """
    Computes summary performance metrics grouped by Strategy and Market Regime.
    Returns a DataFrame.
    """
    from backtest import summarize
    rows = []
    for strategy_name, strategy_trades in tagged_trades.groupby("Strategy"):
        # All regimes row
        overall = summarize(strategy_name, strategy_trades)
        overall["Regime"] = "ALL REGIMES"
        rows.append(overall)

        for regime_name in ["Bullish", "Neutral", "Bearish"]:
            regime_trades = strategy_trades[strategy_trades["Regime"] == regime_name]
            if regime_trades.empty:
                continue
            row = summarize(strategy_name, regime_trades)
            row["Regime"] = regime_name
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Reorder columns with Strategy & Regime first
    cols = ["Strategy", "Regime", "Trades", "WinRate%", "AvgWin%", "AvgLoss%", "Expectancy%", "AvgR",
            "ProfitFactor", "TotalReturn%", "MaxDrawdown%", "MaxLossStreak", "AvgHoldDays", "AvgActualRR",
            "StopHit%", "TargetHit%", "TimeExit%"]
    existing_cols = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]
    return df[existing_cols]


def print_regime_breakdown(tagged_trades):
    """
    Prints a clean, colorful console report showing per-regime performance for each strategy.
    """
    from backtest import summarize
    from core.ui import (
        banner_box, bright_cyan, bright_yellow, bright_green, bright_red,
        bright_white, dim, Fore, Style
    )

    for strategy_name, strategy_trades in tagged_trades.groupby("Strategy"):
        print(banner_box(f"STRATEGY: {strategy_name} — REGIME BREAKDOWN", width=70))

        overall = summarize(strategy_name, strategy_trades)
        exp_val = overall.get("Expectancy%", 0)
        exp_col = bright_green if exp_val > 0 else bright_red
        pf_val = overall.get("ProfitFactor", 0)
        pf_col = bright_green if pf_val >= 1.5 else (bright_yellow if pf_val >= 1.0 else bright_red)
        wr_val = overall.get("WinRate%", 0)
        wr_col = bright_green if wr_val >= 50 else bright_red

        overall_trades = overall["Trades"]
        print(f"  {bright_cyan('ALL REGIMES :'):<14} Trades={bright_white(f'{overall_trades:>4}')}  "
              f"Expectancy%={exp_col(f'{exp_val:>6}')}  "
              f"ProfitFactor={pf_col(f'{pf_val:>5}')}  "
              f"WinRate%={wr_col(f'{wr_val:>5}%')}")

        for regime_name in ["Bullish", "Neutral", "Bearish"]:
            regime_trades = strategy_trades[strategy_trades["Regime"] == regime_name]
            if regime_trades.empty:
                continue
            row = summarize(strategy_name, regime_trades)
            r_exp = row.get("Expectancy%", 0)
            r_exp_col = bright_green if r_exp > 0 else bright_red
            r_pf = row.get("ProfitFactor", 0)
            r_pf_col = bright_green if r_pf >= 1.5 else (bright_yellow if r_pf >= 1.0 else bright_red)
            r_wr = row.get("WinRate%", 0)
            r_wr_col = bright_green if r_wr >= 50 else bright_red

            if regime_name == "Bullish":
                lbl = bright_green(f"{regime_name:<12}")
            elif regime_name == "Bearish":
                lbl = bright_red(f"{regime_name:<12}")
            else:
                lbl = bright_yellow(f"{regime_name:<12}")

            confidence_flag = "" if row["Trades"] >= MIN_TRADES_FOR_CONFIDENCE else f"  {bright_yellow('(small sample)')}"
            row_trades = row["Trades"]
            print(f"  {lbl} Trades={bright_white(f'{row_trades:>4}')}  "
                  f"Expectancy%={r_exp_col(f'{r_exp:>6}')}  "
                  f"ProfitFactor={r_pf_col(f'{r_pf:>5}')}  "
                  f"WinRate%={r_wr_col(f'{r_wr:>5}%')}{confidence_flag}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Split backtest trades by Nifty regime")
    parser.add_argument("--trades-csv", default=DEFAULT_TRADES_CSV)
    return parser.parse_args()


def main():
    from core.ui import (
        banner_box, badge_success, badge_error, badge_warn,
        bright_yellow, bright_cyan, dim
    )

    args = parse_arguments()
    if not os.path.isfile(args.trades_csv):
        print(f"\n  {badge_error('File')} Trades file not found: {bright_yellow(args.trades_csv)}")
        print("  Run backtest.py first to generate outputs/backtest_trades.csv.\n")
        return

    trades_df = pd.read_csv(args.trades_csv)
    print(f"\n  {badge_success('Trades')} Loaded {bright_yellow(str(len(trades_df)))} trades from {bright_cyan(args.trades_csv)}")

    nifty_price_data = fetch_price_history(NIFTY_INDEX_SYMBOL, period=NIFTY_FETCH_PERIOD)
    if nifty_price_data is None:
        print(f"  {badge_error('Nifty')} Could not fetch Nifty index history — cannot compute regime.\n")
        return
    regime_series = compute_daily_regime(nifty_price_data)

    tagged_trades = tag_trades_with_regime(trades_df, regime_series)
    print_regime_breakdown(tagged_trades)

    now = datetime.now()
    run_date = now.strftime("%Y-%m-%d")
    run_time = now.strftime("%H:%M:%S")

    if "RunDate" not in tagged_trades.columns:
        tagged_trades.insert(0, "RunDate", run_date)
        tagged_trades.insert(1, "RunTime", run_time)

    output_dir = os.path.dirname(args.trades_csv)
    output_path = os.path.join(output_dir, "backtest_trades_with_regime.csv")
    exists = os.path.isfile(output_path)
    tagged_trades.to_csv(output_path, mode="a", header=not exists, index=False)
    print(f"\n  {badge_success('CSV')} Appended regime-tagged trades to {bright_yellow(output_path)}")

    # Regime Summary
    regime_summary_df = compute_regime_summary(tagged_trades)
    if not regime_summary_df.empty:
        regime_summary_df.insert(0, "RunDate", run_date)
        regime_summary_df.insert(1, "RunTime", run_time)
        summary_out = os.path.join(output_dir, "backtest_regime_summary.csv")
        s_exists = os.path.isfile(summary_out)
        regime_summary_df.to_csv(summary_out, mode="a", header=not s_exists, index=False)
        print(f"  {badge_success('CSV')} Appended regime summary to {bright_yellow(summary_out)}\n")

    # Auto-sync all results to Google Drive folder
    try:
        from integrations.drive_sync import sync_all_outputs
        sync_all_outputs()
    except Exception as e:
        print(f"\n  {badge_warn('Google Drive')} Sync skipped: {dim(str(e))}")


if __name__ == "__main__":
    main()