import numpy as np

from core.indicators import average_true_range


def chandelier_stop_levels(price_data, entry_index, initial_stop, atr_multiple, atr_period):
    """
    Stop level in force on each bar from entry_index onward. The stop for bar d is
    computed from data up to bar d-1, so it never uses information from bar d itself.
    The stop only moves up. Returns (stop_in_force_per_bar, stop_for_next_bar).
    """
    highs = price_data["High"].to_numpy(dtype=float)
    atr_values = average_true_range(price_data, atr_period).to_numpy(dtype=float)

    stops = np.full(len(price_data), np.nan)
    current_stop = float(initial_stop)
    running_high = -np.inf

    for day in range(entry_index, len(price_data)):
        stops[day] = current_stop
        running_high = max(running_high, highs[day])
        if not np.isnan(atr_values[day]):
            current_stop = max(current_stop, running_high - atr_multiple * atr_values[day])

    return stops, current_stop
