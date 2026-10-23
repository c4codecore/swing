"""
Generic screener engine.
Iterates over a stock universe, fetches appropriate historical data (concurrently),
and queries strategy modules to evaluate swing trading signals.
"""

from core.ohlcv_data import fetch_price_histories_batch


MOMENTUM_LOOKBACK_DAYS = 60


def trailing_return_pct(price_data, lookback=MOMENTUM_LOOKBACK_DAYS):
    close = price_data["Close"]
    if len(close) <= lookback:
        return None
    return round((float(close.iloc[-1]) / float(close.iloc[-1 - lookback]) - 1) * 100, 2)


def screen_stocks(strategy_module, stock_universe, price_histories=None, max_workers=8):
    """
    Screens a universe of stock symbols against a given strategy module.
    If price_histories is provided, reuses existing data without redundant network calls.
    """
    from core.ui import (
        badge_match, bright_cyan, bright_yellow, bright_white,
        bright_green, bright_red, dim, Fore, Style
    )

    signals = []
    print(f"\n{bright_cyan('Screening')} {bright_yellow(str(len(stock_universe)))} stocks with strategy: "
          f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{strategy_module.NAME}{Style.RESET_ALL}\n")

    if price_histories is not None:
        histories = price_histories
    else:
        data_period = getattr(strategy_module, "DATA_PERIOD", "3y")
        histories = fetch_price_histories_batch(stock_universe, period=data_period, max_workers=max_workers)

    for symbol, price_data in histories.items():
        signal = strategy_module.generate_signal(price_data)
        if signal:
            ticker = symbol.replace(".NS", "")
            signal["Ticker"] = ticker
            signal["Strategy"] = strategy_module.NAME
            signal["Momentum60D"] = trailing_return_pct(price_data)
            signals.append(signal)

            entry_str = f"Entry={bright_white(str(signal.get('Entry')))}"
            sl_str = f"SL={bright_red(str(signal.get('StopLoss')))}"
            target_str = f"Target={bright_green(str(signal.get('Target')))}"
            mom = signal.get("Momentum60D")
            mom_str = f"Mom60D={bright_cyan(f'{mom}%')}" if mom is not None else ""

            print(f"  {badge_match()} {bright_yellow(f'{ticker:<10}')} {entry_str}  {sl_str}  {target_str}  {mom_str}")

    signals.sort(key=lambda item: item.get("Momentum60D") or float("-inf"), reverse=True)
    return signals
