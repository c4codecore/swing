import numpy as np
import pandas as pd

from app.core import config, data_fetcher


def _download_frame(symbols):
    index = pd.bdate_range("2025-01-01", periods=3)
    fields = ["Open", "High", "Low", "Close", "Volume"]
    columns = pd.MultiIndex.from_product([symbols, fields])
    values = np.tile([10, 11, 9, 10, 1000], (len(index), len(symbols)))
    return pd.DataFrame(values, index=index, columns=columns)


def test_daily_fetch_uses_chunks_retries_missing_symbols_and_caches(monkeypatch):
    monkeypatch.setattr(config, "DAILY_BATCH_SIZE", 2)
    monkeypatch.setattr(config, "DAILY_BATCH_RETRIES", 2)
    monkeypatch.setattr(config, "DAILY_BATCH_BACKOFF_SECONDS", 0)
    monkeypatch.setattr(config, "DAILY_BATCH_PAUSE_SECONDS", 0)
    calls = []

    def download(tickers, **kwargs):
        calls.append(tuple(tickers))
        # Simulate a partial response once; the missing symbol is retried alone.
        returned = list(tickers)
        if "B.NS" in returned and len(calls) == 1:
            returned.remove("B.NS")
        return _download_frame(returned)

    monkeypatch.setattr(data_fetcher.yf, "download", download)
    with data_fetcher._CACHE_LOCK:
        for key in list(data_fetcher._CACHE):
            if key[0] in {"A.NS", "B.NS", "C.NS"}:
                data_fetcher._CACHE.pop(key)
    frames, failures = data_fetcher.fetch_daily_batch(["A.NS", "B.NS", "C.NS"], period="fixture")
    assert not failures
    assert set(frames) == {"A.NS", "B.NS", "C.NS"}
    assert str(frames["A.NS"].index.tz) == "Asia/Kolkata"
    assert calls == [("A.NS", "B.NS"), ("B.NS",), ("C.NS",)]
    calls.clear()
    cached, failures = data_fetcher.fetch_daily_batch(["A.NS", "B.NS", "C.NS"], period="fixture")
    assert not failures and len(cached) == 3
    assert calls == []


def test_intraday_batch_splits_only_requested_candidates(monkeypatch):
    monkeypatch.setattr(config, "INTRADAY_BATCH_SIZE", 2)
    calls = []

    def batch(symbols, period, interval, ttl_seconds):
        calls.append(tuple(symbols))
        return {symbol: pd.DataFrame({"Close": [1]}) for symbol in symbols}

    monkeypatch.setattr(data_fetcher, "_fetch_intraday_batch_chunk", batch)
    result = data_fetcher.fetch_intraday_batch(["A.NS", "B.NS", "C.NS"], ttl_seconds=5)
    assert calls == [("A.NS", "B.NS"), ("C.NS",)]
    assert set(result) == {"A.NS", "B.NS", "C.NS"}
