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
from core.ui import (
    banner_box, badge_success, badge_error, badge_warn, badge_info,
    bright_cyan, bright_yellow, bright_green, bright_red,
    bright_white, dim, Fore, Style
)
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
        print(f"  {bright_cyan('Downloaded:')} {bright_yellow(str(position))}/{len(symbols)}: {bright_white(symbol)}", end="\r")
    print(f"\n  {badge_success('History')} Usable history ready for {bright_green(str(len(histories)))} of {len(symbols)} stocks.\n")
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
    print(banner_box(f"FILTER FUNNEL: {strategy_name}",
                     subtitle=f"{checks:,} stock-days evaluated",
                     width=84))

    if checks:
        hdr = (f"  {Fore.LIGHTCYAN_EX}{Style.BRIGHT}{'#':<4}{'Filter':<44}{'Alone':>8}{'Cumulative':>13}{'Count':>10}{Style.RESET_ALL}")
        sep = f"  {Fore.LIGHTBLACK_EX}{'-' * 79}{Style.RESET_ALL}"
        print(hdr)
        print(sep)

        previous_count = checks
        for position, name in enumerate(filter_names, start=1):
            count = passed_cumulative[name]
            note = f"  {bright_yellow('<- adds little')}" if count >= ADDS_LITTLE_RATIO * previous_count else ""
            pos_str = dim(f"{position:<4}")
            name_str = bright_white(f"{name:<44}")
            alone_str = bright_cyan(f"{passed_alone[name] / checks * 100:>7.1f}%")
            cum_str = bright_yellow(f"{count / checks * 100:>12.1f}%")
            cnt_str = bright_white(f"{count:>9,}")
            print(f"  {pos_str}{name_str}{alone_str}{cum_str}{cnt_str}{note}")
            previous_count = count

        sig_pct = previous_count / checks * 100
        print(f"\n  {bright_green('Signals (all filters passed):')} {bright_white(f'{previous_count:,}')} "
              f"({bright_yellow(f'{sig_pct:.2f}%')} {dim('of stock-days')})\n")

    for message, occurrences in errors.most_common(3):
        print(f"  {badge_error('Evaluation')} {occurrences:,} evaluations failed: {dim(message)}")


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
        print(f"\n  {badge_error('Strategy')} Unknown strategy '{bright_yellow(args.strategy)}'. Available: {list(available.keys())}\n")
        return

    symbols = get_nifty50_symbols() if args.universe == "nifty50" else get_nifty100_symbols()
    if args.stocks:
        symbols = symbols[: args.stocks]

    for key, strategy_module in selected.items():
        if not hasattr(strategy_module, "evaluate_filters"):
            print(f"\n  {badge_info('Skipped')} {bright_yellow(strategy_module.NAME)}: no evaluate_filters() function.")
            continue
        period = getattr(strategy_module, "DATA_PERIOD", HISTORY_PERIOD)
        print(f"\n  {bright_cyan('Measuring')} {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{strategy_module.NAME}{Style.RESET_ALL} (period={period}) ...")
        price_histories = load_price_histories(symbols, period)
        print_funnel(strategy_module.NAME, *measure_funnel(strategy_module, price_histories, args.days))


if __name__ == "__main__":
    main()
