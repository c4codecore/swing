"""Deterministic, gap-free NSE regime classification with persisted hysteresis."""
from __future__ import annotations

from datetime import date, datetime, time
import logging
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.core import config
from app.core.config import REGIME_COLORS
from app.core.data_fetcher import MarketDataUnavailable, fetch_benchmark, fetch_daily_batch
from app.core.indicators import atr, ema, rsi
from app.core.regime_storage import get_regime_history, load_previous_regime, load_regime_on, save_regime_snapshot
from app.core.screening_universe import get_screening_universe
from app.engine.filters import filter_tradable_symbols
from app.engine.strategies import STRATEGY_REGISTRY

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
RISK_OFF_STATES = {"EXTREME_PANIC_OVERSOLD", "BEARISH_CORRECTION"}
REGIME_ORDER = (
    "EXTREME_PANIC_OVERSOLD", "BEARISH_CORRECTION", "STRONG_BULL",
    "PULLBACK_BULL", "SIDEWAYS_CHOPPY",
)


def _as_ist_date(value: Any) -> date:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize(IST)
    else:
        stamp = stamp.tz_convert(IST)
    return stamp.date()


def _completed_daily_bars(frame: pd.DataFrame, now: datetime) -> pd.DataFrame:
    data = frame.sort_index().copy()
    if data.empty:
        return data
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    else:
        now = now.astimezone(IST)
    if now.time() < time(15, 45):
        today = now.date()
        data = data[[_as_ist_date(value) < today for value in data.index]]
    return data


def compute_regime_metrics(frame: pd.DataFrame) -> Dict[str, float]:
    """Compute all benchmark inputs from daily closes through the final completed bar."""
    close = pd.to_numeric(frame["Close"], errors="coerce").dropna().astype(float)
    if len(close) < config.REGIME_EMA200_PERIOD + 1:
        raise MarketDataUnavailable("At least 201 completed NIFTY daily closes are required for regime metrics.")
    latest_close = float(close.iloc[-1])
    ema20 = ema(close, config.REGIME_EMA20_PERIOD)
    ema50 = ema(close, config.REGIME_EMA50_PERIOD)
    ema200 = ema(close, config.REGIME_EMA200_PERIOD)
    rsi_series = rsi(close, config.REGIME_RSI_PERIOD)
    return20 = (latest_close / float(close.iloc[-1 - config.REGIME_RETURN_20D_PERIOD]) - 1) * 100
    return50 = (latest_close / float(close.iloc[-1 - config.REGIME_RETURN_50D_PERIOD]) - 1) * 100
    slope_index = -1 - config.REGIME_EMA50_SLOPE_LOOKBACK
    slope50 = (float(ema50.iloc[-1]) / float(ema50.iloc[slope_index]) - 1) * 100

    bb_mid = close.rolling(config.REGIME_BOLLINGER_PERIOD).mean()
    bb_std = close.rolling(config.REGIME_BOLLINGER_PERIOD).std(ddof=0)
    bb_width = (2 * config.REGIME_BOLLINGER_STD_MULTIPLIER * bb_std / bb_mid) * 100
    bb_width_stats = bb_width.rolling(config.REGIME_BOLLINGER_STATS_WINDOW).agg(["mean", "std"])
    latest_std = float(bb_std.iloc[-1])
    bollinger_z = (latest_close - float(bb_mid.iloc[-1])) / latest_std if latest_std > 0 else 0.0
    width_stats = bb_width_stats.iloc[-1]
    atr_pct = float(atr(frame, config.REGIME_ATR_PERIOD).iloc[-1] / latest_close * 100)

    return {
        "nifty_close": latest_close,
        "ema_20": float(ema20.iloc[-1]), "ema_50": float(ema50.iloc[-1]),
        "ema_200": float(ema200.iloc[-1]),
        "return_20d_pct": return20, "return_50d_pct": return50,
        "rsi_14": float(rsi_series.iloc[-1]),
        "bollinger_width_pct": float(bb_width.iloc[-1]),
        "bollinger_width_20d_mean_pct": float(width_stats["mean"]),
        "bollinger_width_20d_std_pct": float(width_stats["std"]) if pd.notna(width_stats["std"]) else 0.0,
        "bollinger_z_score": float(bollinger_z),
        "ema_50_slope_5d_pct": float(slope50),
        "ema_50_slope_lookback": config.REGIME_EMA50_SLOPE_LOOKBACK,
        "atr_pct": atr_pct,
        "dist_20ema_pct": (latest_close / float(ema20.iloc[-1]) - 1) * 100,
    }


def _breadth_available(breadth: Optional[Dict[str, Any]]) -> bool:
    return bool(
        breadth and breadth.get("status") == "available"
        and breadth.get("universe_size", 0) >= config.REGIME_BREADTH_MIN_UNIVERSE
        and breadth.get("pct_above_50ema") is not None
    )


def classify_raw_regime(metrics: Dict[str, float], breadth: Optional[Dict[str, Any]] = None,
                        *, include_rule: bool = False) -> str | tuple[str, str]:
    """Apply ordered, mutually exclusive conditions; final fallback is sideways."""
    price = metrics["nifty_close"]
    e20, e50, e200 = metrics["ema_20"], metrics["ema_50"], metrics["ema_200"]
    ret20, ret50 = metrics["return_20d_pct"], metrics["return_50d_pct"]
    rsi_value = metrics["rsi_14"]
    slope50 = metrics["ema_50_slope_5d_pct"]
    bb_width = metrics["bollinger_width_pct"]
    bb_mean = metrics["bollinger_width_20d_mean_pct"]
    bb_std = metrics["bollinger_width_20d_std_pct"]
    breadth_ok = _breadth_available(breadth)
    breadth50 = breadth.get("pct_above_50ema") if breadth_ok and breadth else None

    # First match wins. Panic is intentionally evaluated before every trend state.
    rules = (
        ("EXTREME_PANIC_OVERSOLD", lambda: (
            rsi_value < config.REGIME_PANIC_RSI_MAX
            or metrics["bollinger_z_score"] <= config.REGIME_PANIC_BOLLINGER_Z_MAX
        )),
        ("BEARISH_CORRECTION", lambda: (
            price < e50 and ret20 < config.REGIME_BEARISH_RETURN_20D_MAX
            and (price >= e200 or ret50 < config.REGIME_BEARISH_RETURN_50D_MAX)
        )),
        ("STRONG_BULL", lambda: (
            price > e20 and price > e50 and price > e200 and e20 > e50
            and ret20 > config.REGIME_STRONG_BULL_RETURN_20D_MIN
            and ret50 > config.REGIME_STRONG_BULL_RETURN_50D_MIN
            and slope50 > config.REGIME_STRONG_BULL_EMA50_SLOPE_MIN
            and (not breadth_ok or breadth50 >= config.REGIME_STRONG_BULL_BREADTH_MIN)
        )),
        ("PULLBACK_BULL", lambda: (
        # A pullback needs the established trend structure; early recovery is
        # assigned to sideways below until stronger evidence supports higher risk.
            (price >= e50 and price > e200 and price < e20)
            or (config.REGIME_PULLBACK_RSI_MIN <= rsi_value <= config.REGIME_PULLBACK_RSI_MAX
                and price > e200 and slope50 > config.REGIME_PULLBACK_EMA50_SLOPE_MIN)
        )),
        ("SIDEWAYS_CHOPPY", lambda: (
            (price > e20 and price > e50 and e20 < e50)
            or (abs(slope50) <= config.REGIME_SIDEWAYS_EMA50_SLOPE_ABS_MAX
                and bb_width <= bb_mean + config.REGIME_SIDEWAYS_BOLLINGER_WIDTH_STD_MULTIPLIER * bb_std
                and (not breadth_ok or config.REGIME_SIDEWAYS_BREADTH_MIN <= breadth50 <= config.REGIME_SIDEWAYS_BREADTH_MAX))
        )),
    )
    for state, predicate in rules:
        if predicate():
            return (state, state) if include_rule else state
    # The ordered bearish and sideways rules explicitly absorb the two former
    # gaps; every other combination is assigned to this catch-all.
    return ("SIDEWAYS_CHOPPY", "CATCH_ALL_SIDEWAYS_CHOPPY") if include_rule else "SIDEWAYS_CHOPPY"


def advance_hysteresis(raw_state: str, previous: Optional[Dict[str, Any]], *, is_new_day: bool = True) -> Dict[str, Any]:
    """Advance daily confirmation state; same-day refreshes never add a streak day."""
    if previous is None:
        return {
            "confirmed_regime": raw_state, "days_in_state": 1,
            "pending_regime": None, "pending_days": 0, "pending_required_days": 0,
        }
    confirmed = previous["confirmed_regime"]
    days_in_state = int(previous.get("days_in_state", 1))
    pending = previous.get("pending_regime")
    pending_days = int(previous.get("pending_days", 0))
    required = int(previous.get("pending_required_days", 0))
    if not is_new_day:
        return {
            "confirmed_regime": confirmed, "days_in_state": days_in_state,
            "pending_regime": pending, "pending_days": pending_days,
            "pending_required_days": required,
        }
    if raw_state == confirmed:
        return {
            "confirmed_regime": confirmed, "days_in_state": days_in_state + 1,
            "pending_regime": None, "pending_days": 0, "pending_required_days": 0,
        }
    if raw_state in RISK_OFF_STATES:
        required = config.REGIME_RISK_OFF_ENTRY_DAYS
    elif confirmed in RISK_OFF_STATES:
        required = config.REGIME_RISK_OFF_EXIT_DAYS
    else:
        required = config.REGIME_HYSTERESIS_DAYS
    pending_days = pending_days + 1 if pending == raw_state else 1
    if pending_days >= required:
        return {
            "confirmed_regime": raw_state, "days_in_state": 1,
            "pending_regime": None, "pending_days": 0, "pending_required_days": 0,
        }
    return {
        "confirmed_regime": confirmed, "days_in_state": days_in_state + 1,
        "pending_regime": raw_state, "pending_days": pending_days,
        "pending_required_days": required,
    }


def _state_copy(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "confirmed_regime": row["confirmed_regime"],
        "days_in_state": row["days_in_state"],
        "pending_regime": row.get("pending_regime"),
        "pending_days": row.get("pending_days", 0),
        "pending_required_days": row.get("pending_required_days", 0),
    }


def calculate_market_breadth(symbols: Optional[Iterable[str]] = None, *, as_of: Optional[datetime] = None,
                             daily_data: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, Any]:
    """Calculate breadth only after the shared Phase 2 liquidity/listing filter."""
    sample_symbols = list(dict.fromkeys(symbols or get_screening_universe()[0]))
    frames = dict(daily_data or {})
    missing = [symbol for symbol in sample_symbols if symbol not in frames]
    fetch_failures = []
    if missing:
        fetched, fetch_failures = fetch_daily_batch(missing, period="1y")
        frames.update(fetched)
    failures = [item["symbol"] for item in fetch_failures]

    passed, filter_rejections = filter_tradable_symbols(sample_symbols, frames, market="swing", as_of=as_of)
    if len(passed) < config.REGIME_BREADTH_MIN_UNIVERSE:
        warning = (
            f"Breadth unavailable: {len(passed)} liquidity-filtered, non-SME symbols; "
            f"at least {config.REGIME_BREADTH_MIN_UNIVERSE} are required. Classification uses benchmark-only rules."
        )
        return {
            "status": "unavailable", "universe_size": len(passed),
            "eligible_universe_size": len(passed),
            "minimum_universe_size": config.REGIME_BREADTH_MIN_UNIVERSE,
            "pct_above_20ema": None, "pct_above_50ema": None,
            "valid_symbols": len(passed), "requested_symbols": len(sample_symbols),
            "failed_symbols": failures, "filter_rejections": filter_rejections,
            "warning": warning, "data_status": "unavailable",
        }
    above_20 = above_50 = valid_count = 0
    for symbol in passed:
        frame = frames[symbol]
        completed = _completed_daily_bars(frame, as_of or datetime.now(IST))
        close = completed["Close"].astype(float)
        if len(close) < config.REGIME_EMA200_PERIOD:
            continue
        valid_count += 1
        above_20 += bool(close.iloc[-1] > ema(close, config.REGIME_EMA20_PERIOD).iloc[-1])
        above_50 += bool(close.iloc[-1] > ema(close, config.REGIME_EMA50_PERIOD).iloc[-1])

    available = valid_count >= config.REGIME_BREADTH_MIN_UNIVERSE
    warning = None if available else (
        f"Breadth unavailable: {valid_count} liquidity-filtered, non-SME symbols; "
        f"at least {config.REGIME_BREADTH_MIN_UNIVERSE} are required. Classification uses benchmark-only rules."
    )
    return {
        "status": "available" if available else "unavailable",
        "universe_size": valid_count,
        "eligible_universe_size": len(passed),
        "minimum_universe_size": config.REGIME_BREADTH_MIN_UNIVERSE,
        "pct_above_20ema": round(above_20 / valid_count * 100, 1) if available else None,
        "pct_above_50ema": round(above_50 / valid_count * 100, 1) if available else None,
        "valid_symbols": valid_count,
        "requested_symbols": len(sample_symbols),
        "failed_symbols": failures,
        "filter_rejections": filter_rejections,
        "warning": warning,
        "data_status": "complete" if available and not failures else "partial" if available else "unavailable",
    }


def _state_presentation(state: str) -> Dict[str, Any]:
    copy = {
        "EXTREME_PANIC_OVERSOLD": ("Heavy selling; prices are far below normal", "Prices have fallen sharply. A bounce may happen, but they can keep falling too. Extra care is needed.", "If you trade, keep the amount small and decide in advance how much loss you can accept."),
        "BEARISH_CORRECTION": ("The market is falling", "Nifty is below its 50-day average with negative momentum. New share purchases may carry extra risk.", "Consider keeping more money aside. If you trade, keep the amount small and set a clear exit price."),
        "STRONG_BULL": ("Most tracked shares are rising", "Nifty's trend and momentum are positive. A market-wide rise can still turn down.", "The market looks supportive, but plan an exit before buying and avoid using money you may need soon."),
        "PULLBACK_BULL": ("Longer trend is up; prices have pulled back", "Nifty remains above its longer-term trend and meets the configured pullback or momentum-pause rule.", "Be selective. Wait for the share price to steady before considering a trade."),
        "SIDEWAYS_CHOPPY": ("The market has no clear direction", "Nifty has not met a directional rule. Sudden moves can reverse, so avoid rushing in.", "Wait for a clearer direction. If you trade, use only an amount you can afford to risk."),
    }
    title, description, action = copy[state]
    weight = config.REGIME_SIZING_WEIGHTS[state]
    return {
        "title": title, "description": description, "recommended_action": action,
        "color": REGIME_COLORS[state], "sizing_weight": weight,
        "max_capital_exposure_pct": round(weight * 100),
    }


def _strategy_lists(confirmed: str) -> tuple[list[str], list[Dict[str, str]]]:
    active, skipped = [], []
    for key, strategy in STRATEGY_REGISTRY.items():
        if not config.REGIME_STRATEGY_GATING_ENABLED or confirmed in strategy.target_regimes:
            active.append(key)
        else:
            skipped.append({"id": key, "reason": f"Target regimes do not include confirmed regime {confirmed}."})
    return active, skipped


def _snapshot(evaluated_on: date, raw: str, metrics: Dict[str, Any], breadth: Dict[str, Any],
              state: Dict[str, Any], matching_rule: str) -> Dict[str, Any]:
    confirmed = state["confirmed_regime"]
    stored_metrics = dict(metrics)
    stored_metrics["_classification"] = {
        "matching_rule": matching_rule,
        "classification_source": "catch_all" if matching_rule.startswith("CATCH_ALL") else "defined_rule",
    }
    return {
        "evaluated_on": evaluated_on.isoformat(), "raw_regime": raw,
        "confirmed_regime": confirmed, "days_in_state": state["days_in_state"],
        "pending_regime": state.get("pending_regime"), "pending_days": state.get("pending_days", 0),
        "pending_required_days": state.get("pending_required_days", 0),
        "sizing_weight": config.REGIME_SIZING_WEIGHTS[confirmed],
        "metrics": stored_metrics, "breadth": breadth,
        "created_at": datetime.now(IST).isoformat(timespec="seconds"),
    }


def _process_new_daily_closes(
    completed: pd.DataFrame,
    previous: Dict[str, Any],
    current_date: date,
    current_metrics: Dict[str, float],
    current_breadth: Dict[str, Any],
) -> tuple[Dict[str, Any], str, str]:
    """Replay unseen completed sessions so persistence survives server downtime."""
    previous_date = date.fromisoformat(str(previous["evaluated_on"])[:10])
    new_days = sorted({
        _as_ist_date(stamp) for stamp in completed.index
        if previous_date < _as_ist_date(stamp) <= current_date
    })
    if not new_days:
        return _state_copy(previous), classify_raw_regime(current_metrics, current_breadth), "persisted"

    state: Dict[str, Any] = _state_copy(previous)
    raw_today = ""
    backend = ""
    for day in new_days:
        daily_to_day = completed[[_as_ist_date(stamp) <= day for stamp in completed.index]]
        if day == current_date:
            metrics, breadth = current_metrics, current_breadth
        else:
            metrics = compute_regime_metrics(daily_to_day)
            breadth = {"status": "unavailable", "universe_size": 0, "pct_above_50ema": None}
        raw, matching_rule = classify_raw_regime(metrics, breadth, include_rule=True)
        state = advance_hysteresis(raw, state, is_new_day=True)
        snapshot = _snapshot(day, raw, metrics, breadth, state, matching_rule)
        backend = save_regime_snapshot(snapshot)
        raw_today = raw
    return state, raw_today, backend


def bootstrap_regime_history(
    completed: pd.DataFrame, current_breadth: Dict[str, Any], *, lookback: int = 60,
) -> tuple[Dict[str, Any], str, str]:
    """Seed empty persistence by replaying recent completed closes through hysteresis."""
    first = max(0, len(completed) - max(1, lookback))
    state: Optional[Dict[str, Any]] = None
    raw_today = ""
    backend = ""
    for position in range(first, len(completed)):
        day_frame = completed.iloc[:position + 1]
        metrics = compute_regime_metrics(day_frame)
        evaluated_on = _as_ist_date(day_frame.index[-1])
        is_today = position == len(completed) - 1
        breadth = current_breadth if is_today else {
            "status": "unavailable", "universe_size": 0, "pct_above_50ema": None,
        }
        raw, matching_rule = classify_raw_regime(metrics, breadth, include_rule=True)
        state = advance_hysteresis(raw, state, is_new_day=True)
        backend = save_regime_snapshot(_snapshot(evaluated_on, raw, metrics, breadth, state, matching_rule))
        raw_today = raw
    if state is None:
        raise MarketDataUnavailable("No completed NIFTY daily bars available to bootstrap regime history.")
    return state, raw_today, backend


def analyze_market_regime() -> Dict[str, Any]:
    now = datetime.now(IST)
    nifty_df = fetch_benchmark(period="2y")
    completed = _completed_daily_bars(nifty_df, now)
    minimum_bars = max(config.REGIME_EMA200_PERIOD + 1, config.REGIME_RETURN_50D_PERIOD + 1)
    if len(completed) < minimum_bars:
        raise MarketDataUnavailable(f"At least {minimum_bars} completed NIFTY daily bars are required to classify the market regime.")

    metrics = compute_regime_metrics(completed)
    universe, universe_metadata = get_screening_universe()
    breadth = calculate_market_breadth(universe, as_of=now)
    raw_today, matching_rule_today = classify_raw_regime(metrics, breadth, include_rule=True)
    evaluation_date = _as_ist_date(completed.index[-1])
    same_day_row = load_regime_on(evaluation_date.isoformat())
    previous_row = load_previous_regime(evaluation_date.isoformat())

    if same_day_row:
        # Same completed close may be requested by several API consumers; do not
        # count duplicate reads as additional confirming days.
        state = _state_copy(same_day_row)
        state["raw_regime"] = raw_today
        snapshot = _snapshot(evaluation_date, raw_today, metrics, breadth, state, matching_rule_today)
        backend = save_regime_snapshot(snapshot)
    elif previous_row:
        state, raw_today, backend = _process_new_daily_closes(
            completed, previous_row, evaluation_date, metrics, breadth
        )
    else:
        state, raw_today, backend = bootstrap_regime_history(completed, breadth, lookback=60)

    confirmed = state["confirmed_regime"]
    presentation = _state_presentation(confirmed)
    active, skipped = _strategy_lists(confirmed)
    warnings = [breadth["warning"]] if breadth.get("warning") else []
    history = get_regime_history(30)
    for item in history:
        if item.get("classification_source") == "unknown" and item.get("metrics"):
            historical_raw, historical_rule = classify_raw_regime(
                item["metrics"], item.get("breadth"), include_rule=True
            )
            item["matching_rule"] = historical_rule
            item["classification_source"] = "catch_all" if historical_rule.startswith("CATCH_ALL") else "defined_rule"
    catch_all_days = sum(item.get("classification_source") == "catch_all" for item in history)
    logger.info("Regime %s on %s matched %s; catch-all used on %s/%s of the last 30 closes",
                raw_today, evaluation_date, matching_rule_today, catch_all_days, len(history))
    metrics_out = {
        **{key: round(value, 4) for key, value in metrics.items()},
        # Existing names remain for frontend and API compatibility.
        "breadth_above_50ema_pct": breadth.get("pct_above_50ema"),
        "breadth_above_20ema_pct": breadth.get("pct_above_20ema"),
        "breadth_valid_symbols": breadth.get("valid_symbols", 0),
        "breadth_requested_symbols": breadth.get("requested_symbols", 0),
        "breadth_universe_size": breadth.get("universe_size", 0),
    }
    return {
        "regime": confirmed, "confirmed_regime": confirmed, "raw_regime": raw_today,
        "evaluation_order": [*REGIME_ORDER, "CATCH_ALL_SIDEWAYS_CHOPPY"],
        "matching_rule": matching_rule_today,
        "classification_source": "catch_all" if matching_rule_today.startswith("CATCH_ALL") else "defined_rule",
        "catch_all_days_last_30": catch_all_days,
        "evaluation_date": evaluation_date.isoformat(), "days_in_state": state["days_in_state"],
        "pending_regime": state.get("pending_regime"), "pending_days": state.get("pending_days", 0),
        "pending_required_days": state.get("pending_required_days", 0),
        **presentation,
        "sizing_weight": presentation["sizing_weight"],
        "sizing_weight_note": "Risk-scaling default, not a tested optimum. The backtester will evaluate these weights in Phase 7.",
        "allowed_strategies": active,
        "active_strategies": active,
        "skipped_strategies": skipped,
        "strategy_gating_enabled": config.REGIME_STRATEGY_GATING_ENABLED,
        "breadth": breadth, "warnings": warnings,
        "data_status": breadth.get("data_status", "complete" if breadth["status"] == "available" else "partial"),
        "storage_backend": backend,
        "metrics": metrics_out,
        "regime_history": history,
        "universe": universe_metadata,
    }
