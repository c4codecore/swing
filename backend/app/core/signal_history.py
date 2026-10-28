"""Persistent scan-signal history and outcome tracking using completed daily candles."""
from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from app.core.database import get_connection
from app.core.data_fetcher import fetch_ohlcv

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")


def capture_signals(signals: List[Dict[str, Any]], max_holding_days: int = 15) -> Dict[str, int]:
    """Store each symbol/strategy once per signal date; repeated scans are idempotent."""
    if max_holding_days not in (15, 30):
        raise ValueError("The tracking horizon must be 15 or 30 sessions.")
    now = datetime.now(_IST).isoformat(timespec="seconds")
    inserted = 0
    with get_connection() as connection:
        for signal in signals:
            try:
                symbol = str(signal.get("symbol") or "").strip().upper().removesuffix(".NS")
                strategy = str(signal.get("strategy") or "").strip()
                entry = float(signal["entry_price"])
                stop = float(signal["stop_loss"])
                target = float(signal["target_1"])
                signal_date = str(signal.get("signal_date") or datetime.now(_IST).date().isoformat())[:10]
                date.fromisoformat(signal_date)
                if not symbol or not strategy or not all(math.isfinite(value) for value in (entry, stop, target)):
                    continue
                cursor = connection.execute("""
                    INSERT INTO signal_history (
                        signal_date, captured_at, symbol, strategy, strategy_title,
                        entry_price, stop_loss, target_1, target_2, risk_reward,
                        confidence_score, overall_score, max_holding_days, snapshot_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (signal_date, symbol, strategy) DO NOTHING
                """, (
                    signal_date, now, symbol, strategy,
                    str(signal.get("strategy_title") or strategy), entry, stop, target,
                    _optional_float(signal.get("target_2")),
                    _optional_float(signal.get("risk_reward")),
                    _optional_float(signal.get("confidence_score")),
                    _optional_float(signal.get("overall_score")),
                    max_holding_days, json.dumps(signal, ensure_ascii=False, default=str),
                ))
                inserted += cursor.rowcount
            except (KeyError, TypeError, ValueError) as exc:
                logger.info("Ignoring malformed history signal: %s", exc)
    return {"received": len(signals), "inserted": inserted, "duplicates": max(0, len(signals) - inserted)}


def _optional_float(value: Any):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _completed_through() -> str:
    now = datetime.now(_IST)
    # Do not evaluate today's still-forming daily candle before the NSE close.
    completed_day = now.date() if now.time() >= time(15, 45) else now.date() - timedelta(days=1)
    return completed_day.isoformat()


def _check_symbol_rows(symbol: str, rows: List[Dict[str, Any]], completed_through: str) -> List[Dict[str, Any]]:
    try:
        frame = fetch_ohlcv(f"{symbol}.NS", period="3mo")
    except Exception:
        logger.info("Could not refresh history for %s", symbol, exc_info=True)
        return []
    if frame.empty:
        return []

    updates = []
    bars = []
    for index, candle in frame.iterrows():
        bar_date = index.strftime("%Y-%m-%d")
        if bar_date <= completed_through:
            bars.append((bar_date, float(candle["Open"]), float(candle["High"]), float(candle["Low"]), float(candle["Close"])))

    for item in rows:
        signal_date = item["signal_date"]
        future_bars = [bar for bar in bars if bar[0] > signal_date]
        if not future_bars:
            continue
        sessions = 0
        outcome = "OPEN"
        exit_date = None
        exit_price = None
        for bar_date, open_price, high, low, close in future_bars:
            sessions += 1
            # When both levels are crossed in one daily candle, use the conservative stop-first rule.
            if low <= item["stop_loss"]:
                outcome = "STOP_LOSS"
                exit_date = bar_date
                exit_price = min(open_price, item["stop_loss"])
                break
            if high >= item["target_1"]:
                outcome = "TARGET_HIT"
                exit_date = bar_date
                exit_price = max(open_price, item["target_1"])
                break
            if sessions >= item["max_holding_days"]:
                outcome = "TIME_EXIT"
                exit_date = bar_date
                exit_price = close
                break

        last_bar = next((bar for bar in reversed(future_bars) if bar[0] <= (exit_date or completed_through)), future_bars[-1])
        updates.append({
            "id": item["id"], "outcome": outcome,
            "exit_date": exit_date, "exit_price": exit_price,
            "holding_sessions": sessions,
            "last_price": exit_price if exit_price is not None else last_bar[4],
            "last_checked_date": last_bar[0],
        })
    return updates


def _refresh_open_signals() -> None:
    completed_through = _completed_through()
    with get_connection() as connection:
        pending = connection.execute(
            "SELECT * FROM signal_history WHERE outcome = 'OPEN' AND signal_date < %s AND (last_checked_date IS NULL OR last_checked_date < %s)",
            (completed_through, completed_through),
        ).fetchall()
    by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for row in pending:
        by_symbol.setdefault(row["symbol"], []).append(row)
    updates = []
    for symbol, rows in by_symbol.items():
        updates.extend(_check_symbol_rows(symbol, rows, completed_through))
    if updates:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany("""
                UPDATE signal_history
                SET outcome = %s, exit_date = %s, exit_price = %s, holding_sessions = %s,
                    last_price = %s, last_checked_date = %s
                WHERE id = %s AND outcome = 'OPEN'
            """, [(
                item["outcome"], item["exit_date"], item["exit_price"],
                item["holding_sessions"], item["last_price"], item["last_checked_date"], item["id"],
            ) for item in updates])


def get_signal_history() -> Dict[str, Any]:
    """Refresh open records from completed daily candles, then return date-sorted history."""
    _refresh_open_signals()
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM signal_history ORDER BY signal_date DESC, id DESC").fetchall()
    records = []
    for row in rows:
        record = dict(row)
        entry = record["entry_price"]
        mark = record["exit_price"] if record["exit_price"] is not None else record["last_price"]
        record["return_pct"] = round((mark / entry - 1) * 100, 2) if mark is not None and entry else None
        record["snapshot"] = json.loads(record.pop("snapshot_json") or "{}")
        records.append(record)
    return {
        "count": len(records),
        "open_count": sum(record["outcome"] == "OPEN" for record in records),
        "target_count": sum(record["outcome"] == "TARGET_HIT" for record in records),
        "stop_count": sum(record["outcome"] == "STOP_LOSS" for record in records),
        "time_exit_count": sum(record["outcome"] == "TIME_EXIT" for record in records),
        "checked_through": _completed_through(),
        "records": records,
    }
