import json

import app.core.regime_storage as storage


def _snapshot(day):
    return {
        "evaluated_on": day,
        "raw_regime": "PULLBACK_BULL",
        "confirmed_regime": "STRONG_BULL",
        "days_in_state": 3,
        "pending_regime": "PULLBACK_BULL",
        "pending_days": 1,
        "pending_required_days": 2,
        "sizing_weight": 1.0,
        "metrics": {"ema_20": 100.0},
        "breadth": {"status": "unavailable", "universe_size": 50},
        "created_at": "2026-10-30T16:00:00+05:30",
    }


def test_regime_history_sqlite_migration_is_idempotent_and_persistent(tmp_path, monkeypatch):
    db_path = tmp_path / "history.sqlite3"
    monkeypatch.setattr(storage, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "_SQLITE_PATH", db_path)
    monkeypatch.setattr(storage, "get_connection", lambda: (_ for _ in ()).throw(RuntimeError("no postgres")))

    assert storage.save_regime_snapshot(_snapshot("2026-10-29")) == "sqlite"
    # Upserting the same close updates that row instead of creating a duplicate.
    updated = _snapshot("2026-10-29")
    updated["days_in_state"] = 4
    storage.save_regime_snapshot(updated)
    storage.save_regime_snapshot(_snapshot("2026-10-30"))

    history = storage.get_regime_history(30)
    assert len(history) == 2
    assert history[0]["evaluated_on"] == "2026-10-30"
    assert history[1]["days_in_state"] == 4
    assert history[1]["metrics"] == {"ema_20": 100.0}
    assert storage.load_regime_on("2026-10-30")["confirmed_regime"] == "STRONG_BULL"
    previous = storage.load_previous_regime("2026-10-30")
    assert previous["evaluated_on"] == "2026-10-29"

    import sqlite3
    with sqlite3.connect(db_path) as connection:
        migration = connection.execute(
            "SELECT name FROM marketvoice_migrations WHERE name='regime_history_v1'"
        ).fetchone()
    assert migration == ("regime_history_v1",)
