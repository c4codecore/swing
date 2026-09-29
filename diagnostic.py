"""
Filter funnel diagnostic: shows how often each strategy filter passes and how many
stock-days survive after each one, over the last N trading days.

Usage:
    python3 diagnostic.py                                  all strategies, Nifty 100, last 250 days
    python3 diagnostic.py trend_surfer                     one strategy
    python3 diagnostic.py --universe nifty50 --stocks 30 --days 120

"Alone" is the pass rate of a filter by itself. "Cumulative" is the share of stock-days
still passing after that filter and every filter above it. A filter flagged
"adds little" removes fewer than 5% of what earlier filters already let through.
"""

import argparse
from collections import Counter

from core.ohlcv_data import fetch_price_history, get_nifty50_symbols, get_nifty100_symbols
from run import discover_strategies


HISTORY_PERIOD = "2y"
DEFAULT_DAYS = 250
MIN_WARMUP_ROWS = 60
ADDS_LITTLE_RATIO = 0.95


def load_price_histories(symbols, period):
    histories = {}
    for position, symbol in enumerate(symbols, start=1):
        price_data = fetch_price_history(symbol, period=period)
        if price_data is not None and len(price_data) > MIN_WARMUP_ROWS + 20:
            histories[symbol] = price_data
        print(f"  Downloaded {position}/{len(symbols)}: {symbol}", end="\r")
    print(f"\nUsable history for {len(histories)} of {len(symbols)} stocks.\n")
    return histories


def measure_funnel(strategy_module, price_histories, days):
    filter_names = []
    checks = 0
    passed_alone = Counter()
    passed_cumulative = Counter()
    errors = Counter()

    for price_data in price_histories.values():
        first_index = max(MIN_WARMUP_ROWS, len(price_data) - days)
        for index in range(first_index, len(price_data)):
            try:
                results = strategy_module.evaluate_filters(price_data.iloc[: index + 1])
            except Exception as error:
                errors[f"{type(error).__name__}: {error}"] += 1
                continue
            if results is None:
                continue

            filter_names = list(results)
            checks += 1
            all_passed_so_far = True
            for name, passed in results.items():
                if passed:
                    passed_alone[name] += 1
                all_passed_so_far = all_passed_so_far and passed
                if all_passed_so_far:
                    passed_cumulative[name] += 1

    return filter_names, checks, passed_alone, passed_cumulative, errors


def print_funnel(strategy_name, filter_names, checks, passed_alone, passed_cumulative, errors):
    print("\n" + "=" * 80)
    print(f"{strategy_name}  ({checks:,} stock-days checked)")
    print("=" * 80)

    if checks:
        print(f"  {'Filter':<44}{'Alone':>8}{'Cumulative':>12}{'Count':>9}")
        previous_count = checks
        for position, name in enumerate(filter_names, start=1):
            count = passed_cumulative[name]
            note = "  <- adds little" if count >= ADDS_LITTLE_RATIO * previous_count else ""
            print(f"  {position}. {name:<41}{passed_alone[name] / checks * 100:>7.1f}%"
                  f"{count / checks * 100:>11.1f}%{count:>9,}{note}")
            previous_count = count
        print(f"\n  Signals (all filters passed): {previous_count:,} "
              f"({previous_count / checks * 100:.2f}% of stock-days)")

    for message, occurrences in errors.most_common(3):
        print(f"\n  [!] {occurrences:,} evaluations failed: {message}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Strategy filter funnel diagnostic")
    parser.add_argument("strategy", nargs="?", default="all", help="strategy key, or 'all'")
    parser.add_argument("--universe", choices=["nifty50", "nifty100"], default="nifty100")
    parser.add_argument("--stocks", type=int, default=None, help="limit number of stocks (quick test)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="trading days to examine")
    return parser.parse_args()


def main():
    args = parse_arguments()
    available = discover_strategies()

    if args.strategy == "all":
        selected = available
    elif args.strategy in available:
        selected = {args.strategy: available[args.strategy]}
    else:
        print(f"Unknown strategy '{args.strategy}'. Available: {list(available.keys())}")
        return

    symbols = get_nifty50_symbols() if args.universe == "nifty50" else get_nifty100_symbols()
    if args.stocks:
        symbols = symbols[: args.stocks]

    for key, strategy_module in selected.items():
        if not hasattr(strategy_module, "evaluate_filters"):
            print(f"\nSkipping {strategy_module.NAME}: no evaluate_filters() function.")
            continue
        period = getattr(strategy_module, "DATA_PERIOD", HISTORY_PERIOD)
        print(f"Loading price data for {strategy_module.NAME} (period={period}) ...")
        price_histories = load_price_histories(symbols, period)
        print(f"Measuring {strategy_module.NAME} ...")
        print_funnel(strategy_module.NAME, *measure_funnel(strategy_module, price_histories, args.days))


if __name__ == "__main__":
    main()
