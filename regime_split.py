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
    """
    Tags each trade in trades_df with the corresponding Nifty regime on its EntryDate.
    Uses merge_asof backward match on datetime index.
    """
    if trades_df.empty:
        return trades_df

    trades_df = trades_df.copy()
    # Normalize to seconds — ensures exact timestamp matching
    trades_df["EntryDate_DT"] = pd.to_datetime(trades_df["EntryDate"]).astype("datetime64[s]")

    regime_df = regime_series.rename("Regime").reset_index()
    regime_df.columns = ["RegimeDate", "Regime"]
    regime_df["RegimeDate"] = pd.to_datetime(regime_df["RegimeDate"]).astype("datetime64[s]")
    regime_df = regime_df.sort_values("RegimeDate")

    tagged = pd.merge_asof(
        trades_df.sort_values("EntryDate_DT"), regime_df,
        left_on="EntryDate_DT", right_on="RegimeDate", direction="backward",
    )
    tagged = tagged.drop(columns=["EntryDate_DT", "RegimeDate"], errors="ignore")
    # Place 'Regime' right next to 'Strategy' or 'Stock' if possible
    return tagged


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
    Prints a clean console report showing per-regime performance for each strategy.
    """
    from backtest import summarize
    for strategy_name, strategy_trades in tagged_trades.groupby("Strategy"):
        print("\n" + "=" * 70)
        print(f"Strategy: {strategy_name} — Regime Breakdown")
        print("=" * 70)

        overall = summarize(strategy_name, strategy_trades)
        print(f"  {'ALL REGIMES':<12} Trades={overall['Trades']:>4}  "
              f"Expectancy%={overall.get('Expectancy%', 0):>6}  "
              f"ProfitFactor={overall.get('ProfitFactor', 0):>5}  "
              f"WinRate%={overall.get('WinRate%', 0):>5}%")

        for regime_name in ["Bullish", "Neutral", "Bearish"]:
            regime_trades = strategy_trades[strategy_trades["Regime"] == regime_name]
            if regime_trades.empty:
                continue
            row = summarize(strategy_name, regime_trades)
            confidence_flag = "" if row["Trades"] >= MIN_TRADES_FOR_CONFIDENCE else "  (small sample)"
            print(f"  {regime_name:<12} Trades={row['Trades']:>4}  "
                  f"Expectancy%={row.get('Expectancy%', 0):>6}  "
                  f"ProfitFactor={row.get('ProfitFactor', 0):>5}  "
                  f"WinRate%={row.get('WinRate%', 0):>5}%{confidence_flag}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Split backtest trades by Nifty regime")
    parser.add_argument("--trades-csv", default=DEFAULT_TRADES_CSV)
    return parser.parse_args()


def main():
    args = parse_arguments()
    if not os.path.isfile(args.trades_csv):
        print(f"Trades file not found: {args.trades_csv}")
        print("Run backtest.py first to generate outputs/backtest_trades.csv.")
        return

    trades_df = pd.read_csv(args.trades_csv)
    print(f"Loaded {len(trades_df)} trades from {args.trades_csv}")

    nifty_price_data = fetch_price_history(NIFTY_INDEX_SYMBOL, period=NIFTY_FETCH_PERIOD)
    if nifty_price_data is None:
        print("Could not fetch Nifty index history - cannot compute regime.")
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
    print(f"\nAppended regime-tagged trades to {output_path}")

    # Regime Summary
    regime_summary_df = compute_regime_summary(tagged_trades)
    if not regime_summary_df.empty:
        regime_summary_df.insert(0, "RunDate", run_date)
        regime_summary_df.insert(1, "RunTime", run_time)
        summary_out = os.path.join(output_dir, "backtest_regime_summary.csv")
        s_exists = os.path.isfile(summary_out)
        regime_summary_df.to_csv(summary_out, mode="a", header=not s_exists, index=False)
        print(f"Appended regime summary to {summary_out}")

    # Auto-sync all results to Google Drive folder
    try:
        from integrations.drive_sync import sync_all_outputs
        sync_all_outputs()
    except Exception as e:
        print(f"\n[Google Drive] Sync skipped: {e}")


if __name__ == "__main__":
    main()