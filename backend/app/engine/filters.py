"""Shared tradability and data-quality filters for stock screeners."""
from __future__ import annotations

import csv
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple
from zoneinfo import ZoneInfo

import pandas as pd

from app.core.config import (
    ASM_GSM_LIST_PATH,
    CIRCUIT_BAND_PROXIMITY_PCT,
    DAILY_AVG_TRADED_VALUE_LOOKBACK,
    INCLUDE_SME_STOCKS,
    MAX_DAILY_BAR_AGE_TRADING_DAYS,
    MIN_DAILY_BARS,
    MIN_STOCK_PRICE,
    SWING_MIN_AVG_TRADED_VALUE,
    INTRADAY_MIN_AVG_TRADED_VALUE,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
DEFAULT_ASM_GSM_PATH = Path(__file__).resolve().parents[2] / "data" / "asm_gsm.csv"
REJECTION_REASONS = (
    "missing_data", "insufficient_history", "stale_data", "min_price",
    "avg_traded_value", "sme", "circuit_band", "circuit_band_heuristic", "asm_gsm",
)


def _as_ist_date(value: Any) -> date:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize(IST)
    else:
        stamp = stamp.tz_convert(IST)
    return stamp.date()


def _trading_days_between(start: date, end: date) -> int:
    """Weekday-based age; exchange holidays are not available in the data source."""
    if end <= start:
        return 0
    return sum(1 for day in pd.date_range(start + timedelta(days=1), end, freq="D") if day.weekday() < 5)


def _canonical_symbol(symbol: str) -> str:
    return re.sub(r"\.NS$", "", str(symbol).strip(), flags=re.IGNORECASE).upper()


def _load_asm_gsm(path: Path) -> Optional[set[str]]:
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            return set()
        columns = {column.strip().lower(): column for column in rows[0] if column}
        symbol_column = next((columns[name] for name in ("symbol", "security", "ticker") if name in columns), None)
        if symbol_column is None:
            logger.warning("ASM/GSM CSV has no symbol/security/ticker column: %s", path)
            return set()
        return {_canonical_symbol(row.get(symbol_column, "")) for row in rows if row.get(symbol_column)}
    except (OSError, csv.Error):
        logger.exception("Unable to read ASM/GSM list %s", path)
        return set()


def _find_band_column(frame: pd.DataFrame, names: Iterable[str]) -> Optional[str]:
    wanted = {re.sub(r"[^a-z0-9]", "", name.lower()) for name in names}
    for column in frame.columns:
        normalized = re.sub(r"[^a-z0-9]", "", str(column).lower())
        if normalized in wanted:
            return str(column)
    return None


def _band_proximity(frame: pd.DataFrame, close: float) -> Optional[bool]:
    upper_col = _find_band_column(frame, ("upper_band", "upper circuit", "upper_circuit_limit", "upper price band", "upperband"))
    lower_col = _find_band_column(frame, ("lower_band", "lower circuit", "lower_circuit_limit", "lower price band", "lowerband"))
    if not upper_col and not lower_col:
        return None
    latest = frame.iloc[-1]
    proximity = CIRCUIT_BAND_PROXIMITY_PCT / 100.0
    valid_band_found = False
    for column, side in ((upper_col, "upper"), (lower_col, "lower")):
        if not column:
            continue
        band = pd.to_numeric(pd.Series([latest[column]]), errors="coerce").iloc[0]
        if pd.isna(band) or band <= 0:
            continue
        valid_band_found = True
        if side == "upper" and close >= float(band) * (1 - proximity):
            return True
        if side == "lower" and close <= float(band) * (1 + proximity):
            return True
    return False if valid_band_found else None


def _heuristic_circuit_lock(frame: pd.DataFrame) -> bool:
    """Flag repeated one-price sessions followed by a common NSE band-sized move."""
    if len(frame) < 2:
        return False
    rows = frame.tail(2)
    try:
        locked = [
            abs(float(row["High"]) - float(row["Low"])) <= 0.01
            and abs(float(row["Close"]) - float(row["High"])) <= 0.01
            for _, row in rows.iterrows()
        ]
        if not all(locked):
            return False
        closes = pd.to_numeric(rows["Close"], errors="coerce").to_numpy(dtype=float)
        if closes[0] <= 0:
            return False
        move_pct = abs(closes[1] / closes[0] - 1) * 100
        return any(abs(move_pct - band) <= 0.15 for band in (2, 5, 10, 20))
    except (KeyError, TypeError, ValueError):
        return False


def _is_sme_symbol(symbol: str) -> bool:
    canonical = _canonical_symbol(symbol)
    return canonical.endswith(("-SM", "-ST", ".SM", ".SME"))


def _official_sme_symbols() -> Tuple[Optional[set[str]], str]:
    """Use the project's cached NSE listing source when its SME CSV is available."""
    try:
        from app.core.stock_universe import get_nse_equities
        rows, metadata = get_nse_equities()
        if "NSE SME" in metadata.get("sources", []):
            return {
                _canonical_symbol(row.get("symbol", ""))
                for row in rows if row.get("segment") == "NSE SME"
            }, "NSE SME listing"
    except Exception:
        logger.debug("Official SME listing unavailable; using symbol suffix heuristic", exc_info=True)
    return None, "symbol suffix heuristic (official list unavailable)"


def filter_tradable_symbols(
    symbols: Iterable[str],
    daily_data: Mapping[str, pd.DataFrame],
    *,
    market: str = "swing",
    as_of: Optional[datetime] = None,
    asm_gsm_path: Optional[Path] = None,
) -> Tuple[list[str], Dict[str, Any]]:
    """Return symbols that pass data-quality, liquidity, listing and band filters.

    Only the first applicable rejection reason is counted for any symbol. `market`
    selects the configured average traded-value floor (`swing` or `intraday`).
    """
    if market not in {"swing", "intraday"}:
        raise ValueError("market must be 'swing' or 'intraday'")
    now = as_of or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    else:
        now = now.astimezone(IST)
    today = now.date()
    threshold = SWING_MIN_AVG_TRADED_VALUE if market == "swing" else INTRADAY_MIN_AVG_TRADED_VALUE
    configured_path = asm_gsm_path if asm_gsm_path is not None else ASM_GSM_LIST_PATH
    list_path = Path(configured_path) if configured_path else DEFAULT_ASM_GSM_PATH
    restricted = _load_asm_gsm(list_path)
    rejections: Dict[str, Any] = {reason: 0 for reason in REJECTION_REASONS}
    if restricted is None:
        rejections["asm_gsm"] = "not configured"
    sme_symbols, sme_source = (None, "included by config") if INCLUDE_SME_STOCKS else _official_sme_symbols()
    rejections["sme_source"] = sme_source
    passed: list[str] = []

    for symbol in dict.fromkeys(symbols):
        frame = daily_data.get(symbol)
        if frame is None:
            frame = daily_data.get(_canonical_symbol(symbol))
        if frame is None or frame.empty:
            rejections["missing_data"] += 1
            continue
        frame = frame.sort_index()
        if len(frame) < MIN_DAILY_BARS:
            rejections["insufficient_history"] += 1
            continue
        last_date = _as_ist_date(frame.index[-1])
        if _trading_days_between(last_date, today) > MAX_DAILY_BAR_AGE_TRADING_DAYS:
            rejections["stale_data"] += 1
            continue
        close = pd.to_numeric(frame["Close"], errors="coerce")
        if close.empty or pd.isna(close.iloc[-1]) or close.iloc[-1] < MIN_STOCK_PRICE:
            rejections["min_price"] += 1
            continue
        complete = frame[[ _as_ist_date(stamp) != today for stamp in frame.index ]].tail(DAILY_AVG_TRADED_VALUE_LOOKBACK)
        if complete.empty:
            rejections["avg_traded_value"] += 1
            continue
        traded_value = pd.to_numeric(complete["Close"], errors="coerce") * pd.to_numeric(complete["Volume"], errors="coerce")
        avg_value = float(traded_value.dropna().mean()) if not traded_value.dropna().empty else 0.0
        if avg_value < threshold:
            rejections["avg_traded_value"] += 1
            continue
        if not INCLUDE_SME_STOCKS and (_canonical_symbol(symbol) in (sme_symbols or set()) or _is_sme_symbol(symbol)):
            rejections["sme"] += 1
            continue
        band_result = _band_proximity(frame, float(close.iloc[-1]))
        if band_result is True:
            rejections["circuit_band"] += 1
            continue
        if band_result is None and _heuristic_circuit_lock(frame):
            rejections["circuit_band_heuristic"] += 1
            continue
        if restricted is not None and _canonical_symbol(symbol) in restricted:
            rejections["asm_gsm"] += 1
            continue
        passed.append(symbol)

    return passed, rejections
