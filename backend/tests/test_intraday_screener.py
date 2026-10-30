import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.engine.intraday_screener import (
    _build_volume_profile,
    _completed_session_bars,
    _daily_average_volume,
    _fallback_u_profile,
    _profile_share,
    _session_metrics,
)

IST = ZoneInfo("Asia/Kolkata")
TODAY = date(2026, 10, 30)


def _session(day, volumes=None):
    index = pd.date_range(f"{day} 09:15", periods=75, freq="5min", tz=IST)
    if volumes is None:
        weights = np.array([1.0 + 0.55 * np.cos(2 * np.pi * ((i + 0.5) / 75.0)) for i in range(75)])
        volumes = (weights * 1000).astype(int)
    close = np.linspace(100, 101, 75)
    return pd.DataFrame({
        "Open": close, "High": close + .1, "Low": close - .1,
        "Close": close, "Volume": volumes,
    }, index=index)


def _history():
    days = pd.bdate_range(end="2026-10-29", periods=20)
    return pd.concat([_session(day.strftime("%Y-%m-%d")) for day in days])


def test_0945_profile_rvol_is_not_inflated_vs_old_linear_formula():
    profile, sessions = _build_volume_profile(_history(), TODAY)
    assert sessions == 20
    today_bars = _session(TODAY.isoformat()).iloc[:6]
    metrics = _session_metrics(today_bars, avg_daily_volume=75_000, profile=profile)
    old_linear_rvol = metrics["volume"] / (75_000 * (30 / 375))
    assert metrics["rvol"] <= old_linear_rvol


def test_partial_current_day_is_excluded_from_daily_average():
    index = pd.DatetimeIndex(["2026-10-28", "2026-10-29", "2026-10-30"]).tz_localize(IST)
    daily = pd.DataFrame({"Close": [100, 200, 300], "Volume": [1000, 2000, 900_000]}, index=index)
    avg_volume, avg_value = _daily_average_volume(daily, TODAY, lookback=20)
    assert avg_volume == 1500
    assert avg_value == 250_000


def test_forming_candle_is_excluded_without_lookahead():
    bars = _session(TODAY.isoformat())
    now = datetime(2026, 10, 30, 9, 45, tzinfo=IST)
    completed = _completed_session_bars(bars, now)
    assert completed.index[-1] == pd.Timestamp("2026-10-30 09:40", tz=IST)
    assert len(completed) == 6


def test_forming_candle_is_excluded_at_1007_ist():
    bars = _session(TODAY.isoformat())
    now = datetime(2026, 10, 30, 10, 7, tzinfo=IST)
    completed = _completed_session_bars(bars, now)
    assert completed.index[-1] == pd.Timestamp("2026-10-30 10:00", tz=IST)
    assert pd.Timestamp("2026-10-30 10:05", tz=IST) not in completed.index


def test_missing_profile_history_uses_market_wide_u_shape():
    profile, sessions = _build_volume_profile(pd.DataFrame(), TODAY)
    assert sessions == 0
    assert profile == _fallback_u_profile()
    assert _profile_share(profile, 10) > 0


def test_volume_profile_is_non_decreasing_and_ends_at_one():
    profile, sessions = _build_volume_profile(_history(), TODAY)
    values = list(profile.values())
    assert sessions == 20
    assert values == sorted(values)
    assert values[-1] == 1.0
