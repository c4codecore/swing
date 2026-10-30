from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import app.engine.regime as regime
from app.engine.regime import (
    RISK_OFF_STATES,
    advance_hysteresis,
    classify_raw_regime,
    compute_regime_metrics,
)

IST = ZoneInfo("Asia/Kolkata")
NO_BREADTH = {"status": "unavailable", "universe_size": 50, "pct_above_50ema": None}


def _ohlcv(close):
    prices = np.asarray(close, dtype=float)
    index = pd.bdate_range("2025-01-01", periods=len(prices), tz=IST)
    return pd.DataFrame({
        "Open": prices, "High": prices * 1.005, "Low": prices * 0.995,
        "Close": prices, "Volume": np.full(len(prices), 1_000_000, dtype=int),
    }, index=index)


def _raw(prices, breadth=NO_BREADTH):
    return classify_raw_regime(compute_regime_metrics(_ohlcv(prices)), breadth)


def test_synthetic_nifty_series_cover_each_of_the_five_regimes():
    rng = np.random.default_rng(2)
    bearish_above_200 = np.r_[np.linspace(70, 160, 210), 160 + np.cumsum(rng.normal(-0.1, 0.4, 50))]
    rng = np.random.default_rng(3)
    pullback = np.r_[np.linspace(60, 150, 230), np.linspace(150, 145, 30) + rng.normal(0, 0.7, 30)]
    cases = {
        "panic": np.r_[np.linspace(60, 150, 240), np.linspace(150, 95, 20)],
        "bearish": bearish_above_200,
        "bull": np.linspace(80, 160, 260),
        "pullback": pullback,
        "sideways": np.full(260, 100.0),
    }
    expected = {
        "panic": "EXTREME_PANIC_OVERSOLD",
        "bearish": "BEARISH_CORRECTION",
        "bull": "STRONG_BULL",
        "pullback": "PULLBACK_BULL",
        "sideways": "SIDEWAYS_CHOPPY",
    }
    assert {name: _raw(prices) for name, prices in cases.items()} == expected
    bearish_metrics = compute_regime_metrics(_ohlcv(bearish_above_200))
    assert bearish_metrics["ema_200"] < bearish_metrics["nifty_close"] < bearish_metrics["ema_50"]
    assert bearish_metrics["return_20d_pct"] < 0


def test_early_recovery_with_fast_ema_below_slow_ema_maps_to_sideways():
    prices = np.r_[np.linspace(100, 75, 220), [76.0, 80.0]]
    metrics = compute_regime_metrics(_ohlcv(prices))
    assert metrics["nifty_close"] > metrics["ema_20"]
    assert metrics["nifty_close"] > metrics["ema_50"]
    assert metrics["ema_20"] < metrics["ema_50"]
    assert classify_raw_regime(metrics, NO_BREADTH, include_rule=True) == (
        "SIDEWAYS_CHOPPY", "SIDEWAYS_CHOPPY"
    )


def test_generated_series_always_maps_to_exactly_one_state():
    rng = np.random.default_rng(42)
    allowed = {
        "EXTREME_PANIC_OVERSOLD", "BEARISH_CORRECTION", "STRONG_BULL",
        "PULLBACK_BULL", "SIDEWAYS_CHOPPY",
    }
    for _ in range(100):
        steps = rng.normal(0.0002, 0.012, 260)
        prices = 100 * np.exp(np.cumsum(steps))
        state = _raw(prices)
        assert state in allowed
        assert isinstance(state, str)


def test_one_day_normal_crossover_stays_pending_until_second_close():
    prior = advance_hysteresis("STRONG_BULL", None)
    first = advance_hysteresis("PULLBACK_BULL", prior)
    assert first["confirmed_regime"] == "STRONG_BULL"
    assert first["pending_regime"] == "PULLBACK_BULL"
    assert first["pending_days"] == 1
    duplicate = advance_hysteresis("PULLBACK_BULL", first, is_new_day=False)
    assert duplicate["pending_days"] == 1
    second = advance_hysteresis("PULLBACK_BULL", duplicate)
    assert second["confirmed_regime"] == "PULLBACK_BULL"
    assert second["pending_regime"] is None


def test_risk_off_entry_is_fast_but_exit_needs_two_closes():
    prior = advance_hysteresis("STRONG_BULL", None)
    entered = advance_hysteresis("BEARISH_CORRECTION", prior)
    assert entered["confirmed_regime"] == "BEARISH_CORRECTION"
    assert entered["pending_regime"] is None
    assert "BEARISH_CORRECTION" in RISK_OFF_STATES

    recovery = {"nifty_close": 110.0, "ema_50": 100.0}
    first_exit = advance_hysteresis("STRONG_BULL", entered, metrics=recovery, breadth=NO_BREADTH)
    assert first_exit["confirmed_regime"] == "BEARISH_CORRECTION"
    assert first_exit["pending_regime"] == "STRONG_BULL"
    assert first_exit["pending_days"] == 1
    second_exit = advance_hysteresis("STRONG_BULL", first_exit, metrics=recovery, breadth=NO_BREADTH)
    assert second_exit["confirmed_regime"] == "STRONG_BULL"


def test_bearish_exit_guard_needs_ema50_or_breadth_recovery(monkeypatch):
    prior = advance_hysteresis("BEARISH_CORRECTION", None)
    below_ema = {"nifty_close": 100.0, "ema_50": 105.0}
    no_breadth = {"status": "unavailable", "universe_size": 50, "pct_above_50ema": None}
    first = advance_hysteresis("SIDEWAYS_CHOPPY", prior, metrics=below_ema, breadth=no_breadth)
    second = advance_hysteresis("SIDEWAYS_CHOPPY", first, metrics=below_ema, breadth=no_breadth)
    assert first["pending_days"] == second["pending_days"] == 0
    assert second["confirmed_regime"] == "BEARISH_CORRECTION"

    recovered_breadth = {"status": "available", "universe_size": 200, "pct_above_50ema": 41.0}
    qualifying_first = advance_hysteresis("SIDEWAYS_CHOPPY", second, metrics=below_ema, breadth=recovered_breadth)
    qualifying_second = advance_hysteresis("SIDEWAYS_CHOPPY", qualifying_first, metrics=below_ema, breadth=recovered_breadth)
    assert qualifying_first["pending_days"] == 1
    assert qualifying_second["confirmed_regime"] == "SIDEWAYS_CHOPPY"


def test_bearish_exit_guard_can_be_disabled(monkeypatch):
    monkeypatch.setattr(regime.config, "REGIME_BEARISH_EXIT_GUARD_ENABLED", False)
    prior = advance_hysteresis("BEARISH_CORRECTION", None)
    first = advance_hysteresis("SIDEWAYS_CHOPPY", prior)
    second = advance_hysteresis("SIDEWAYS_CHOPPY", first)
    assert second["confirmed_regime"] == "SIDEWAYS_CHOPPY"


def test_breadth_below_200_is_unavailable_and_uses_benchmark_fallback(monkeypatch):
    frame = _ohlcv(np.linspace(80, 160, 260))
    symbols = [f"S{i:03d}.NS" for i in range(199)]
    monkeypatch.setattr(regime, "fetch_daily_batch", lambda symbols, period: ({symbol: frame for symbol in symbols}, []))
    monkeypatch.setattr(
        regime, "filter_tradable_symbols",
        lambda symbols, frames, market, as_of: (list(symbols), {"asm_gsm": "not configured"}),
    )
    breadth = regime.calculate_market_breadth(symbols, as_of=datetime(2026, 10, 30, 16, tzinfo=IST))
    assert breadth["status"] == "unavailable"
    assert breadth["universe_size"] == 199
    assert breadth["pct_above_50ema"] is None
    assert "benchmark-only rules" in breadth["warning"]

    metrics = compute_regime_metrics(frame)
    assert classify_raw_regime(metrics, breadth) == classify_raw_regime(metrics, NO_BREADTH)


def test_empty_regime_history_bootstraps_last_60_completed_sessions(monkeypatch):
    frame = _ohlcv(np.linspace(80, 180, 280))
    written = []
    monkeypatch.setattr(regime, "save_regime_snapshot", lambda snapshot: written.append(snapshot) or "sqlite")
    state, raw, backend = regime.bootstrap_regime_history(frame, {
        "status": "unavailable", "universe_size": 0, "pct_above_50ema": None,
    }, lookback=60)
    assert len(written) == 60
    assert written[0]["evaluated_on"] == frame.index[-60].date().isoformat()
    assert written[-1]["evaluated_on"] == frame.index[-1].date().isoformat()
    assert state["confirmed_regime"] == raw == "STRONG_BULL"
    assert state["days_in_state"] == 60
    assert backend == "sqlite"
