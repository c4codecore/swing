from core.utils import round_tick


def build_long_levels(entry_price, swing_low, atr, risk_reward,
                      min_stop_atr=1.5, max_stop_atr=3.0, stop_buffer_atr=0.15):
    if entry_price is None or atr is None or entry_price <= 0 or atr <= 0:
        return None

    stop_price = swing_low - stop_buffer_atr * atr
    risk = entry_price - stop_price
    if risk > max_stop_atr * atr:
        return None
    if risk < min_stop_atr * atr:
        risk = min_stop_atr * atr
        stop_price = entry_price - risk

    entry_rounded = round_tick(entry_price)
    stop_rounded = round_tick(stop_price)
    target_rounded = round_tick(entry_price + risk * risk_reward)
    if entry_rounded is None or stop_rounded is None or target_rounded is None:
        return None

    risk_rupees = round(entry_rounded - stop_rounded, 2)
    reward_rupees = round(target_rounded - entry_rounded, 2)
    if stop_rounded <= 0 or risk_rupees <= 0 or reward_rupees <= 0:
        return None

    return {
        "Entry": entry_rounded,
        "StopLoss": stop_rounded,
        "Target": target_rounded,
        "Risk_Rs": risk_rupees,
        "Reward_Rs": reward_rupees,
    }


def average_turnover(price_data, window=20):
    return float((price_data["Close"] * price_data["Volume"]).tail(window).mean())
