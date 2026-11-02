"""Persistent daily snapshots for intraday and derivatives research signals."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from app.core.database import get_connection

_IST = ZoneInfo("Asia/Kolkata")


def capture_market_signals(market_type: str, signals: List[Dict[str, Any]]) -> Dict[str, int]:
    """Upsert the latest daily snapshot per symbol and strategy for a market tab."""
    if market_type not in {"intraday", "options"}:
        raise ValueError("Unsupported market history type.")
    now = datetime.now(_IST)
    captured_at = now.isoformat(timespec="seconds")
    inserted = 0
    updated = 0
    with get_connection() as connection:
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            symbol = str(signal.get("symbol") or signal.get("underlying") or "").strip().upper()
            strategy = str(signal.get("strategy") or "current_plan").strip()
            if not symbol:
                continue
            try:
                signal_date = str(signal.get("signal_date") or now.date().isoformat())[:10]
                datetime.strptime(signal_date, "%Y-%m-%d")
            except ValueError:
                signal_date = now.date().isoformat()
            title = str(signal.get("strategy_title") or signal.get("strategy") or signal.get("status") or market_type.title())
            snapshot_json = json.dumps(signal, ensure_ascii=False, default=str, sort_keys=True)
            cursor = connection.execute("""
                INSERT INTO market_signal_history (
                    market_type, signal_date, captured_at, symbol, strategy, strategy_title, snapshot_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (market_type, signal_date, symbol, strategy)
                DO UPDATE SET captured_at = EXCLUDED.captured_at,
                              strategy_title = EXCLUDED.strategy_title,
                              snapshot_json = EXCLUDED.snapshot_json
                WHERE market_signal_history.snapshot_json IS DISTINCT FROM EXCLUDED.snapshot_json
            """, (market_type, signal_date, captured_at, symbol, strategy, title, snapshot_json))
            if cursor.rowcount == 1:
                inserted += 1
            elif cursor.rowcount > 1:
                updated += cursor.rowcount
    return {"received": len(signals), "inserted_or_updated": inserted + updated}


def get_market_signal_history() -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, market_type, signal_date, captured_at, symbol, strategy, strategy_title, snapshot_json
            FROM market_signal_history
            ORDER BY signal_date DESC, captured_at DESC, id DESC
        """).fetchall()
    records = []
    for row in rows:
        record = dict(row)
        try:
            record["snapshot"] = json.loads(record.pop("snapshot_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            record["snapshot"] = {}
        records.append(record)
    return records
