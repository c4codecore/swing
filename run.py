"""
Live Daily Screener Runner & Watchlist Generator.
=================================================

Knowledge & Workflow:
---------------------
1. Strategy Discovery:
   - Automatically scans `strategies/` directory and registers all strategies with `generate_signal()`.
2. Market Regime Filter:
   - Fetches Nifty 50 trend first. If market is Bearish, strategies marked `REQUIRED_REGIME = "Bullish"`
     are automatically skipped to protect trading capital from bear traps.
3. Fast Parallel Batch Scanning:
   - Downloads 3-year price histories for the stock universe once upfront via ThreadPoolExecutor.
   - Evaluates all strategies against pre-loaded in-memory data in sub-second time.
4. Schema Normalization & Google Sheets Sync:
   - Normalizes diverse strategy signal dicts into standard columns (Stock, Entry, StopLoss, Target, Risk, Reward).
   - Appends matching setups to local `outputs/watchlist.csv` and syncs live to Google Sheets.
"""

import sys
import os
import pkgutil
import importlib
import pandas as pd
from datetime import datetime

from core.ohlcv_data import get_nifty50_symbols, get_nifty100_symbols, get_all_nse_symbols, fetch_price_histories_batch
from core.screener import screen_stocks
from core.market_regime import get_market_regime, print_regime_banner
from integrations.gsheets import append_to_sheet
import strategies


def get_stock_list():
    """Default universe: Nifty 100 constituents."""
    stock_list = get_nifty100_symbols()
    # stock_list = get_all_nse_symbols()
    return stock_list


def discover_strategies():
    """
    Scans the strategies/ package and auto-imports every valid strategy module.
    Excludes blueprints (_template.py) and __init__.py.
    """
    found = {}
    for _, module_name, _ in pkgutil.iter_modules(strategies.__path__):
        if module_name.startswith("_"):
            continue
        module = importlib.import_module(f"strategies.{module_name}")
        if hasattr(module, "NAME") and hasattr(module, "generate_signal"):
            found[module_name] = module
    return found


STRATEGIES = discover_strategies()


def show_menu():
    """Interactive CLI menu for single-strategy execution."""
    print("\nAvailable strategies:")
    print("-" * 40)
    keys = list(STRATEGIES.keys())
    for i, key in enumerate(keys, start=1):
        print(f"  {i}. {STRATEGIES[key].NAME}  [{key}]")
    print("-" * 40)

    choice = input("Choose a strategy (number): ").strip()
    try:
        index = int(choice) - 1
        if 0 <= index < len(keys):
            return keys[index]
    except ValueError:
        pass

    print("Invalid choice. Please enter a valid number.")
    return None


CORE_COLUMNS = ["Date", "Time", "Strategy", "Stock",
                 "Entry", "StopLoss", "Target", "Risk_Rs", "Reward_Rs"]


def normalize_signal(signal, run_date, run_time):
    """
    Standardizes signal output into a consistent tabular CSV/Google Sheets schema.
    Extra strategy-specific indicators are compressed into an 'Indicators' string.
    """
    row = {"Date": run_date, "Time": run_time}
    extras = []
    for key, value in signal.items():
        if key == "Ticker":
            row["Stock"] = value
        elif key == "Date":
            continue
        elif key in CORE_COLUMNS:
            row[key] = value
        elif isinstance(value, dict):
            for k, v in value.items():
                extras.append(f"{k}={v}")
        else:
            extras.append(f"{key}={value}")
    row["Indicators"] = "; ".join(extras)
    return row


def save_watchlist(strategy_key, strategy_module, signals):
    """
    Displays matched swing setups, saves to local CSV, and syncs to Google Sheets.
    """
    print("\n" + "=" * 60)
    if signals:
        now = datetime.now()
        run_date = now.strftime("%Y-%m-%d")
        run_time = now.strftime("%H:%M:%S")

        rows = [normalize_signal(s, run_date, run_time) for s in signals]
        watchlist_df = pd.DataFrame(rows)
        column_order = CORE_COLUMNS + ["Indicators"]
        watchlist_df = watchlist_df[column_order]

        print(f"{len(signals)} stock(s) matched today:\n")
        print(watchlist_df.to_string(index=False))

        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "watchlist.csv")

        file_exists = os.path.isfile(output_path)
        watchlist_df.to_csv(output_path, mode="a", header=not file_exists, index=False)
        print(f"\nAppended to {output_path}")

        # Sync to Google Sheets inside Google Drive folder (non-fatal — local CSV is already safely stored)
        try:
            from integrations.drive_sync import sync_csv_to_drive_sheet
            sync_csv_to_drive_sheet(output_path)
        except Exception:
            append_to_sheet(watchlist_df)
    else:
        print(f"No stocks matched '{strategy_module.NAME}' today.")
    print("=" * 60)


def run_one(strategy_key, stock_universe, current_regime=None, price_histories=None):
    """Runs a single strategy against the stock universe."""
    if strategy_key not in STRATEGIES:
        print(f"Unknown strategy '{strategy_key}'. Available: {list(STRATEGIES.keys())}")
        return

    strategy_module = STRATEGIES[strategy_key]

    # Market Regime Check: Skip long-only setup if overall market is hostile
    required = getattr(strategy_module, "REQUIRED_REGIME", None)
    if required is not None:
        regime_trend = current_regime["trend"] if current_regime else None
        if regime_trend != required:
            print(f"\n{'=' * 60}")
            print(f"[SKIPPED] {strategy_module.NAME}")
            print(f"  Requires Nifty: {required} | Current: {regime_trend or 'UNKNOWN'}")
            print(f"  This strategy only trades in {required} markets.")
            print(f"{'=' * 60}")
            return

    signals = screen_stocks(strategy_module, stock_universe, price_histories=price_histories)
    save_watchlist(strategy_key, strategy_module, signals)


CONSENSUS_MIN_STRATEGIES = 2


def run_consensus(stock_universe, current_regime, price_histories):
    regime_trend = current_regime["trend"] if current_regime else None
    hits_by_ticker = {}
    for strategy_key, strategy_module in STRATEGIES.items():
        required = getattr(strategy_module, "REQUIRED_REGIME", None)
        if required is not None and regime_trend != required:
            continue
        for signal in screen_stocks(strategy_module, stock_universe, price_histories=price_histories):
            hits_by_ticker.setdefault(signal["Ticker"], []).append(signal)

    rows = []
    for ticker, signals in hits_by_ticker.items():
        if len(signals) < CONSENSUS_MIN_STRATEGIES:
            continue
        rows.append({
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Stock": ticker,
            "StrategyCount": len(signals),
            "Strategies": "; ".join(sorted(signal["Strategy"] for signal in signals)),
            "Entry": max(signal["Entry"] for signal in signals),
            "StopLoss": max(signal["StopLoss"] for signal in signals),
            "Momentum60D": signals[0].get("Momentum60D"),
        })

    print("\n" + "=" * 60)
    if not rows:
        print(f"No stock was flagged by {CONSENSUS_MIN_STRATEGIES} or more strategies today.")
        print("=" * 60)
        return

    consensus_df = pd.DataFrame(rows).sort_values(
        ["StrategyCount", "Momentum60D"], ascending=[False, False])
    print(f"{len(consensus_df)} stock(s) flagged by {CONSENSUS_MIN_STRATEGIES}+ strategies:\n")
    print(consensus_df.to_string(index=False))

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "consensus_watchlist.csv")
    consensus_df.to_csv(output_path, mode="a", header=not os.path.isfile(output_path), index=False)
    print(f"\nAppended to {output_path}")
    print("=" * 60)


def load_universe_and_regime():
    stock_universe = get_stock_list()
    print(f"\nLoading price histories for {len(stock_universe)} stocks ...")
    price_histories = fetch_price_histories_batch(stock_universe, period="3y", max_workers=10)
    current_regime = get_market_regime(price_histories=price_histories)
    print_regime_banner(current_regime)
    return stock_universe, price_histories, current_regime


def run_all():
    """
    High-performance batch runner:
    Loads price data once for the universe, then evaluates all strategies in memory.
    """
    stock_universe, price_histories, current_regime = load_universe_and_regime()

    for strategy_key in STRATEGIES:
        print("\n" + "#" * 60)
        print(f"# Running strategy: {strategy_key}")
        print("#" * 60)
        run_one(strategy_key, stock_universe, current_regime, price_histories=price_histories)


if __name__ == "__main__":
    print("\nReminder: This is a screening tool, not a buy/sell signal.")

    if len(sys.argv) > 1 and sys.argv[1] == "consensus":
        stock_universe, price_histories, current_regime = load_universe_and_regime()
        run_consensus(stock_universe, current_regime, price_histories)
    elif len(sys.argv) > 1 and sys.argv[1] != "menu":
        stock_universe, price_histories, current_regime = load_universe_and_regime()
        run_one(sys.argv[1], stock_universe, current_regime, price_histories)
    elif len(sys.argv) > 1 and sys.argv[1] == "menu":
        selected_key = show_menu()
        if selected_key:
            stock_universe, price_histories, current_regime = load_universe_and_regime()
            run_one(selected_key, stock_universe, current_regime, price_histories)
    else:
        run_all()