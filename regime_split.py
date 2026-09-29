"""
Splits an existing backtest_trades.csv by Nifty's own trend on each trade's entry
date, so you can see whether a strategy only wins when the index itself is rising.

Usage:
    python3 regime_split.py                                 outputs/backtest_trades.csv
    python3 regime_split.py --trades-csv path/to/trades.csv

Nifty regime on a given day, using the same EMA20/EMA50 rule as market_regime.py:
- Bullish: close above 50 EMA and 20 EMA above 50 EMA
- Bearish: close below 50 EMA and 20 EMA below 50 EMA
- Neutral: anything else
"""

import argparse
import os

import pandas as pd

from backtest import summarize
from core.market_regime import NIFTY_INDEX_SYMBOL, compute_daily_regime
from core.ohlcv_data import fetch_price_history


DEFAULT_TRADES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "backtest_trades.csv")
NIFTY_FETCH_PERIOD = "3y"
MIN_TRADES_FOR_CONFIDENCE = 30



def tag_trades_with_regime(trades_df, regime_series):
    trades_df = trades_df.copy()
    # Normalize to seconds — yfinance timestamps are 's', pd.to_datetime gives 'us'.
    # merge_asof requires both keys to be the same dtype resolution.
    trades_df["EntryDate"] = pd.to_datetime(trades_df["EntryDate"]).astype("datetime64[s]")

    regime_df = regime_series.rename("Regime").reset_index()
    regime_df.columns = ["RegimeDate", "Regime"]
    regime_df["RegimeDate"] = pd.to_datetime(regime_df["RegimeDate"]).astype("datetime64[s]")
    regime_df = regime_df.sort_values("RegimeDate")

    tagged = pd.merge_asof(
        trades_df.sort_values("EntryDate"), regime_df,
        left_on="EntryDate", right_on="RegimeDate", direction="backward",
    )
    return tagged.drop(columns="RegimeDate")


def print_regime_breakdown(tagged_trades):
    for strategy_name, strategy_trades in tagged_trades.groupby("Strategy"):
        print("\n" + "=" * 70)
        print(strategy_name)
        print("=" * 70)

        overall = summarize(strategy_name, strategy_trades)
        print(f"  {'ALL REGIMES':<12} Trades={overall['Trades']:>4}  "
              f"Expectancy%={overall.get('Expectancy%', 0):>6}  "
              f"ProfitFactor={overall.get('ProfitFactor', 0):>5}")

        for regime_name in ["Bullish", "Neutral", "Bearish"]:
            regime_trades = strategy_trades[strategy_trades["Regime"] == regime_name]
            if regime_trades.empty:
                continue
            row = summarize(strategy_name, regime_trades)
            confidence_flag = "" if row["Trades"] >= MIN_TRADES_FOR_CONFIDENCE else "  (small sample)"
            print(f"  {regime_name:<12} Trades={row['Trades']:>4}  "
                  f"Expectancy%={row.get('Expectancy%', 0):>6}  "
                  f"ProfitFactor={row.get('ProfitFactor', 0):>5}{confidence_flag}")


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

    output_path = os.path.join(os.path.dirname(args.trades_csv), "backtest_trades_with_regime.csv")
    tagged_trades.to_csv(output_path, index=False)
    print(f"\nSaved regime-tagged trades to {output_path}")


if __name__ == "__main__":
    main()