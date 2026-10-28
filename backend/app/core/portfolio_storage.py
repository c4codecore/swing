"""Local persistent storage for the user's manually tracked portfolio."""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.database import get_connection


def get_manual_holdings() -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT symbol, quantity, average_price FROM manual_portfolio ORDER BY symbol"
        ).fetchall()
    return [dict(row) for row in rows]


def replace_manual_holdings(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = {}
    for holding in holdings:
        symbol = str(holding["symbol"]).strip().upper().removesuffix(".NS")
        normalized[symbol] = {
            "symbol": symbol,
            "quantity": float(holding["quantity"]),
            "average_price": float(holding["average_price"]),
        }
    with get_connection() as connection:
        connection.execute("DELETE FROM manual_portfolio")
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO manual_portfolio (symbol, quantity, average_price) VALUES (%s, %s, %s)",
                [(item["symbol"], item["quantity"], item["average_price"]) for item in normalized.values()],
            )
    return list(normalized.values())
