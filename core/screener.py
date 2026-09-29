"""
Generic screener engine.
Iterates over a stock universe, fetches appropriate historical data (concurrently),
and queries strategy modules to evaluate swing trading signals.
"""

from core.ohlcv_data import fetch_price_histories_batch


def screen_stocks(strategy_module, stock_universe, price_histories=None, max_workers=8):
    """
    Screens a universe of stock symbols against a given strategy module.
    If price_histories is provided, reuses existing data without redundant network calls.
    """
    signals = []
    print(f"Screening {len(stock_universe)} stocks with strategy: {strategy_module.NAME}\n")

    if price_histories is not None:
        histories = price_histories
    else:
        data_period = getattr(strategy_module, "DATA_PERIOD", "3y")
        histories = fetch_price_histories_batch(stock_universe, period=data_period, max_workers=max_workers)

    for symbol, price_data in histories.items():
        signal = strategy_module.generate_signal(price_data)
        if signal:
            signal["Ticker"] = symbol.replace(".NS", "")
            signal["Strategy"] = strategy_module.NAME
            signals.append(signal)
            print(f"  [MATCH] {signal['Ticker']:12s} Entry={signal.get('Entry')} "
                  f"SL={signal.get('StopLoss')} Target={signal.get('Target')}")

    return signals
