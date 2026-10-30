from app.core import screening_universe as universe


def test_bundled_nifty500_fallback_is_complete(monkeypatch, tmp_path):
    monkeypatch.setattr(universe, "_symbols_cache", None)
    monkeypatch.setattr(universe, "_cache_time", 0.0)
    monkeypatch.setattr(universe, "_CACHE_CSV", tmp_path / "missing-cache.csv")
    monkeypatch.setattr(universe, "_download_nifty500", lambda: (_ for _ in ()).throw(OSError("offline")))
    symbols, metadata = universe.get_nifty500_symbols(force_refresh=True)
    assert len(symbols) >= 500
    assert symbols[0].endswith(".NS")
    assert metadata["status"] == "fallback"


def test_all_configured_universe_modes(monkeypatch):
    monkeypatch.setattr(universe.config, "SCREENING_UNIVERSE_MODE", "nifty50")
    nifty50, meta50 = universe.get_screening_universe()
    assert len(nifty50) == len(universe.config.NIFTY50_UNIVERSE)
    assert meta50["mode"] == "nifty50"

    monkeypatch.setattr(universe, "get_nifty500_symbols", lambda force_refresh=False: (["AAA.NS"] * 500, {"status": "cached"}))
    nifty500, meta500 = universe.get_screening_universe("nifty500")
    assert len(nifty500) == 500
    assert meta500["mode"] == "nifty500"

    monkeypatch.setattr(universe, "get_nse_equities", lambda force_refresh=False: ([
        {"symbol": "AAA", "series": "EQ"}, {"symbol": "SME", "series": "SM"},
    ], {"list_status": "available"}))
    full, meta_full = universe.get_screening_universe("nse_equities")
    assert full == ["AAA.NS"]
    assert meta_full["mode"] == "nse_equities"


def test_explicit_universe_switches_and_mutual_exclusion(monkeypatch):
    monkeypatch.setattr(universe.config, "USE_NIFTY50_ONLY", True)
    monkeypatch.setattr(universe.config, "USE_FULL_NSE_EQUITY_LIST", False)
    symbols, meta = universe.get_screening_universe()
    assert len(symbols) == 50 and meta["mode"] == "nifty50"

    monkeypatch.setattr(universe.config, "USE_NIFTY50_ONLY", False)
    monkeypatch.setattr(universe.config, "USE_FULL_NSE_EQUITY_LIST", True)
    monkeypatch.setattr(universe, "get_nse_equities", lambda force_refresh=False: ([
        {"symbol": "AAA", "series": "EQ"},
    ], {}))
    symbols, meta = universe.get_screening_universe()
    assert symbols == ["AAA.NS"] and meta["mode"] == "nse_equities"

    monkeypatch.setattr(universe.config, "USE_NIFTY50_ONLY", True)
    try:
        universe.get_screening_universe()
    except ValueError as exc:
        assert "only one universe override" in str(exc)
    else:
        raise AssertionError("simultaneous universe overrides must be rejected")
