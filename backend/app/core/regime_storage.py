"""PostgreSQL/SQLite storage and schema migration for regime state history."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from app.core.database import get_connection

logger = logging.getLogger(__name__)
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_SQLITE_PATH = _DATA_DIR / "marketvoice_history.sqlite3"
_SCHEMA_LOCK = threading.RLock()
_MIGRATION_NAME = "regime_history_v1"


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS regime_history (
    evaluated_on TEXT PRIMARY KEY,
    raw_regime TEXT NOT NULL,
    confirmed_regime TEXT NOT NULL,
    days_in_state INTEGER NOT NULL,
    pending_regime TEXT,
    pending_days INTEGER NOT NULL DEFAULT 0,
    pending_required_days INTEGER NOT NULL DEFAULT 0,
    sizing_weight DOUBLE PRECISION NOT NULL,
    metrics_json TEXT NOT NULL,
    breadth_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_regime_history_date ON regime_history(evaluated_on DESC);
CREATE TABLE IF NOT EXISTS marketvoice_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO marketvoice_migrations (name) VALUES (?) ON CONFLICT (name) DO NOTHING;
"""


@contextmanager
def _connection() -> Iterator[Tuple[Any, str]]:
    try:
        if not os.getenv("DATABASE_URL", "").strip():
            raise RuntimeError("DATABASE_URL is not configured; using SQLite.")
        connection = get_connection()
    except Exception as exc:
        if os.getenv("DATABASE_URL", "").strip():
            logger.warning("Regime history PostgreSQL unavailable; using SQLite fallback: %s", exc)
        else:
            logger.debug("PostgreSQL is not configured; using SQLite regime history.")
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(_SQLITE_PATH, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            with _SCHEMA_LOCK:
                connection.executescript(_SQLITE_SCHEMA.replace("VALUES (?)", "VALUES ('regime_history_v1')"))
            with connection:
                yield connection, "sqlite"
        finally:
            connection.close()
    else:
        with connection:
            yield connection, "postgresql"


def load_regime_on(evaluated_on: str) -> Optional[Dict[str, Any]]:
    with _connection() as (connection, dialect):
        placeholder = "?" if dialect == "sqlite" else "%s"
        row = connection.execute(
            f"SELECT * FROM regime_history WHERE evaluated_on = {placeholder}", (evaluated_on,)
        ).fetchone()
    return dict(row) if row else None


def load_previous_regime(evaluated_on: str) -> Optional[Dict[str, Any]]:
    with _connection() as (connection, dialect):
        placeholder = "?" if dialect == "sqlite" else "%s"
        row = connection.execute(
            f"SELECT * FROM regime_history WHERE evaluated_on < {placeholder} ORDER BY evaluated_on DESC LIMIT 1",
            (evaluated_on,),
        ).fetchone()
    return dict(row) if row else None


def save_regime_snapshot(snapshot: Dict[str, Any]) -> str:
    values = (
        snapshot["evaluated_on"], snapshot["raw_regime"], snapshot["confirmed_regime"],
        int(snapshot["days_in_state"]), snapshot.get("pending_regime"),
        int(snapshot.get("pending_days", 0)), int(snapshot.get("pending_required_days", 0)),
        float(snapshot["sizing_weight"]), json.dumps(snapshot.get("metrics", {}), ensure_ascii=False),
        json.dumps(snapshot.get("breadth", {}), ensure_ascii=False), snapshot["created_at"],
    )
    columns = "evaluated_on, raw_regime, confirmed_regime, days_in_state, pending_regime, pending_days, pending_required_days, sizing_weight, metrics_json, breadth_json, created_at"
    placeholders = ", ".join(["?"] * len(values))
    update_columns = "raw_regime=excluded.raw_regime, confirmed_regime=excluded.confirmed_regime, days_in_state=excluded.days_in_state, pending_regime=excluded.pending_regime, pending_days=excluded.pending_days, pending_required_days=excluded.pending_required_days, sizing_weight=excluded.sizing_weight, metrics_json=excluded.metrics_json, breadth_json=excluded.breadth_json, created_at=excluded.created_at"
    with _connection() as (connection, dialect):
        if dialect == "postgresql":
            placeholders = ", ".join(["%s"] * len(values))
        connection.execute(
            f"INSERT INTO regime_history ({columns}) VALUES ({placeholders}) ON CONFLICT (evaluated_on) DO UPDATE SET {update_columns}",
            values,
        )
        return dialect


def get_regime_history(limit: int = 30) -> list[Dict[str, Any]]:
    bounded = max(1, min(30, int(limit)))
    with _connection() as (connection, dialect):
        placeholder = "?" if dialect == "sqlite" else "%s"
        rows = connection.execute(
            f"SELECT * FROM regime_history ORDER BY evaluated_on DESC LIMIT {placeholder}",
            (bounded,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
        item["breadth"] = json.loads(item.pop("breadth_json") or "{}")
        classification = item["metrics"].pop("_classification", {})
        item["matching_rule"] = classification.get("matching_rule")
        item["classification_source"] = classification.get("classification_source", "unknown")
        result.append(item)
    return result
