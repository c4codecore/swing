import numpy as np
import pandas as pd

import app.engine.screener as screener_module
from app.core import config
from app.engine.screener import ScreenerEngine


class FakeStrategy:
    def __init__(self, target_regimes, calls):
        self.target_regimes = target_regimes
        self.calls = calls

    def evaluate(self, df, benchmark_df=None):
        self.calls.append(self.target_regimes)
        return None


def _daily_frame():
    close = np.linspace(80, 120, 230)
    return pd.DataFrame({
        "Open": close, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": np.full(len(close), 1_000_000),
    }, index=pd.bdate_range("2025-01-01", periods=len(close)))


def test_swing_screener_runs_only_confirmed_regime_targets(monkeypatch):
    calls = []
    strategies = {
        "bear_strategy": FakeStrategy(["BEARISH_CORRECTION"], calls),
        "bull_strategy": FakeStrategy(["STRONG_BULL"], calls),
    }
    monkeypatch.setattr(screener_module, "STRATEGY_REGISTRY", strategies)
    monkeypatch.setattr(screener_module, "analyze_market_regime", lambda: {
        "regime": "BEARISH_CORRECTION", "confirmed_regime": "BEARISH_CORRECTION",
    })
    monkeypatch.setattr(screener_module, "fetch_benchmark", lambda period: _daily_frame())
    monkeypatch.setattr(screener_module, "fetch_daily_batch", lambda symbols, period: ({symbol: _daily_frame() for symbol in symbols}, []))
    monkeypatch.setattr(screener_module, "filter_tradable_symbols", lambda symbols, frames, market: (list(symbols), {}))
    monkeypatch.setattr(config, "REGIME_STRATEGY_GATING_ENABLED", True)

    result = ScreenerEngine().run_screener(symbols=["TEST.NS"], force_refresh=True)
    assert len(calls) == 1
    assert result["strategies_run"] == ["bear_strategy"]
    assert result["strategies_skipped"] == [{
        "id": "bull_strategy", "reason": "Target regimes do not include confirmed regime BEARISH_CORRECTION."
    }]


def test_strategy_gating_can_be_overridden(monkeypatch):
    calls = []
    strategies = {
        "bear_strategy": FakeStrategy(["BEARISH_CORRECTION"], calls),
        "bull_strategy": FakeStrategy(["STRONG_BULL"], calls),
    }
    monkeypatch.setattr(screener_module, "STRATEGY_REGISTRY", strategies)
    monkeypatch.setattr(screener_module, "analyze_market_regime", lambda: {
        "regime": "BEARISH_CORRECTION", "confirmed_regime": "BEARISH_CORRECTION",
    })
    monkeypatch.setattr(screener_module, "fetch_benchmark", lambda period: _daily_frame())
    monkeypatch.setattr(screener_module, "fetch_daily_batch", lambda symbols, period: ({symbol: _daily_frame() for symbol in symbols}, []))
    monkeypatch.setattr(screener_module, "filter_tradable_symbols", lambda symbols, frames, market: (list(symbols), {}))
    monkeypatch.setattr(config, "REGIME_STRATEGY_GATING_ENABLED", False)

    result = ScreenerEngine().run_screener(symbols=["TEST.NS"], force_refresh=True)
    assert len(calls) == 2
    assert result["strategies_run"] == ["bear_strategy", "bull_strategy"]
    assert result["strategies_skipped"] == []
