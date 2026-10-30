from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import app.engine.filters as filters
from app.engine.filters import filter_tradable_symbols

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 10, 30, 16, 0, tzinfo=IST)


def _daily(close=100.0, volume=600_000, periods=230, end="2026-10-30"):
    index = pd.bdate_range(end=end, periods=periods, tz=IST)
    values = np.full(periods, close, dtype=float)
    volumes = np.full(periods, volume, dtype=int)
    return pd.DataFrame({"Open": values, "High": values, "Low": values,
                         "Close": values, "Volume": volumes}, index=index)


def test_filter_reasons_cover_all_exclusion_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(filters, "_official_sme_symbols", lambda: ({"ABC-SM", "OFFICIAL_SME"}, "fixture NSE SME list"))
    data = {
        "SHORT.NS": _daily(periods=219),
        "OLD.NS": _daily(end="2026-10-26"),
        "CHEAP.NS": _daily(close=40),
        "ILLIQ.NS": _daily(volume=1_000),
        "ABC-SM.NS": _daily(),
        "OFFICIAL_SME.NS": _daily(),
        "BANDED.NS": _daily(),
        "LOCKED.NS": _daily(),
        "RESTRICTED.NS": _daily(),
        "PASS.NS": _daily(),
    }
    data["BANDED.NS"]["upper_band"] = 100.0
    data["BANDED.NS"]["lower_band"] = 90.0
    data["BANDED.NS"].loc[data["BANDED.NS"].index[-1], "Close"] = 99.6
    data["LOCKED.NS"].loc[data["LOCKED.NS"].index[-2], ["Open", "High", "Low", "Close"]] = 100.0
    data["LOCKED.NS"].loc[data["LOCKED.NS"].index[-1], ["Open", "High", "Low", "Close"]] = 105.0
    asm_path = tmp_path / "asm_gsm.csv"
    asm_path.write_text("symbol,stage\nRESTRICTED,ASM\n", encoding="utf-8")

    passed, rejected = filter_tradable_symbols(
        ["MISSING.NS", *data], data, market="swing", as_of=AS_OF, asm_gsm_path=asm_path
    )
    assert passed == ["PASS.NS"]
    assert rejected["missing_data"] == 1
    assert rejected["insufficient_history"] == 1
    assert rejected["stale_data"] == 1
    assert rejected["min_price"] == 1
    assert rejected["avg_traded_value"] == 1
    assert rejected["sme"] == 2
    assert rejected["circuit_band"] == 1
    assert rejected["circuit_band_heuristic"] == 1
    assert rejected["asm_gsm"] == 1


def test_first_applicable_reason_counts_symbol_once(monkeypatch):
    monkeypatch.setattr(filters, "_official_sme_symbols", lambda: (set(), "fixture NSE SME list"))
    frame = _daily(close=40, volume=1_000)
    passed, rejected = filter_tradable_symbols(
        ["DUAL_FAIL.NS"], {"DUAL_FAIL.NS": frame}, market="swing", as_of=AS_OF,
        asm_gsm_path=Path("missing-asm-list.csv"),
    )
    assert passed == []
    assert rejected["min_price"] == 1
    assert rejected["avg_traded_value"] == 0
    assert sum(value for key, value in rejected.items() if isinstance(value, int)) == 1


def test_missing_asm_gsm_file_is_explicitly_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(filters, "_official_sme_symbols", lambda: (set(), "fixture NSE SME list"))
    _, rejected = filter_tradable_symbols(
        ["PASS.NS"], {"PASS.NS": _daily()}, market="swing", as_of=AS_OF,
        asm_gsm_path=tmp_path / "does-not-exist.csv",
    )
    assert rejected["asm_gsm"] == "not configured"


def test_swing_and_intraday_use_distinct_liquidity_floors(monkeypatch):
    monkeypatch.setattr(filters, "_official_sme_symbols", lambda: (set(), "fixture NSE SME list"))
    symbol = "SEVEN_CRORE.NS"
    frame = _daily(volume=700_000)  # ₹7 crore at ₹100/share
    swing_pass, swing_counts = filter_tradable_symbols(
        [symbol], {symbol: frame}, market="swing", as_of=AS_OF,
        asm_gsm_path=Path("missing-asm-list.csv"),
    )
    intraday_pass, intraday_counts = filter_tradable_symbols(
        [symbol], {symbol: frame}, market="intraday", as_of=AS_OF,
        asm_gsm_path=Path("missing-asm-list.csv"),
    )
    assert swing_pass == [symbol]
    assert swing_counts["avg_traded_value"] == 0
    assert intraday_pass == []
    assert intraday_counts["avg_traded_value"] == 1
