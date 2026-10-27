"""Defined-risk, read-only NIFTY debit-spread planner."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.core.iifl_market_data import get_iifl_fo_contracts, get_iifl_market_quotes


def _value(row: dict[str, Any], *keys: str) -> Any:
    normalized = {str(key).lower(): value for key, value in row.items()}
    return next((normalized[key.lower()] for key in keys if normalized.get(key.lower()) is not None), None)


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        raw = str(int(value))
        if len(raw) == 8:
            try:
                return datetime.strptime(raw, "%Y%m%d").date()
            except ValueError:
                return None
    raw = str(value).strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw[:11], fmt).date()
        except ValueError:
            continue
    return None


def _nifty_options(master: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    selected = []
    for row in master:
        option_type = str(_value(row, "optionType", "option_type") or "").upper()
        if option_type in {"CALL", "C"}:
            option_type = "CE"
        elif option_type in {"PUT", "P"}:
            option_type = "PE"
        if option_type not in {"CE", "PE"}:
            continue
        underlying = " ".join(str(_value(row, key) or "") for key in (
            "name", "symbol", "underlying", "underlyingSymbol", "underlyingIndexName", "displayName", "tradingSymbol", "description",
        )).upper()
        if "NIFTY" not in underlying or "BANKNIFTY" in underlying or "FINNIFTY" in underlying:
            continue
        expiry = _parse_date(_value(row, "expiry", "expiryDate", "contractExpiration", "expirationDate"))
        strike = _value(row, "strikePrice", "strike_price", "strike")
        instrument_id = _value(row, "instrumentId", "instrumentID", "token", "exchangeInstrumentId")
        try:
            strike = float(strike)
        except (TypeError, ValueError):
            continue
        # Skip same-day expiry contracts; their intraday gamma/settlement risk is not modeled here.
        if not expiry or expiry <= today or strike <= 0 or instrument_id is None:
            continue
        selected.append({
            "option_type": option_type, "expiry": expiry,
            "strike": strike, "instrument_id": str(instrument_id),
            "symbol": str(_value(row, "tradingSymbol", "description", "displayName") or f"NIFTY {expiry} {strike:g} {option_type}"),
            "lot_size": _value(row, "lotSize", "marketLot", "market_lot"),
        })
    return selected


def build_nifty_options_plan(intraday: dict[str, Any]) -> dict[str, Any]:
    spot = intraday.get("spot")
    signal = intraday.get("signal")
    base = {
        "underlying": "NIFTY 50", "spot": spot, "bias": signal,
        "strategy": None, "expiry": None, "legs": [],
        "data_source": "IIFL NSEFO contract master + IIFL live option quotes",
        "disclaimer": "Research scenario only; premiums can move quickly and the full debit is at risk. This screen does not place orders.",
    }
    if signal not in {"LONG_CALL_BIAS", "LONG_PUT_BIAS"} or spot is None:
        return {**base, "status": "WAIT", "reason": "Wait for a confirmed NIFTY intraday direction before selecting an options structure."}

    contracts = _nifty_options(get_iifl_fo_contracts())
    if not contracts:
        return {**base, "status": "UNAVAILABLE", "reason": "No current NIFTY option contracts were found in IIFL's NSEFO contract master."}
    expiry = min(item["expiry"] for item in contracts)
    chain = [item for item in contracts if item["expiry"] == expiry]
    available_strikes = sorted({item["strike"] for item in chain})
    atm = min(available_strikes, key=lambda strike: abs(strike - float(spot)))
    strike_step = min((right - left for left, right in zip(available_strikes, available_strikes[1:]) if right > left), default=50)
    width = max(2 * strike_step, 50)

    if signal == "LONG_CALL_BIAS":
        option_type = "CE"
        long_strike = atm
        short_candidates = [strike for strike in available_strikes if strike >= long_strike + width]
        short_strike = min(short_candidates, key=lambda strike: abs(strike - (long_strike + width))) if short_candidates else None
        strategy = "Bull call debit spread"
        breakeven_direction = 1
    else:
        option_type = "PE"
        long_strike = min((strike for strike in available_strikes if strike >= atm), key=lambda strike: abs(strike - atm), default=atm)
        short_candidates = [strike for strike in available_strikes if strike <= long_strike - width]
        short_strike = max(short_candidates, key=lambda strike: strike) if short_candidates else None
        strategy = "Bear put debit spread"
        breakeven_direction = -1
    if short_strike is None:
        return {**base, "status": "UNAVAILABLE", "reason": "IIFL's current option chain has no suitable spread strikes for the selected expiry."}

    long_contract = next((item for item in chain if item["option_type"] == option_type and item["strike"] == long_strike), None)
    short_contract = next((item for item in chain if item["option_type"] == option_type and item["strike"] == short_strike), None)
    if not long_contract or not short_contract:
        return {**base, "status": "UNAVAILABLE", "reason": "Could not map the selected strikes to IIFL option contracts."}

    quote_rows = get_iifl_market_quotes([
        {"exchange": "NSEFO", "instrumentId": long_contract["instrument_id"]},
        {"exchange": "NSEFO", "instrumentId": short_contract["instrument_id"]},
    ])
    quotes = {str(_value(row, "instrumentId", "instrumentID")): row for row in quote_rows if isinstance(row, dict)}

    def premium(contract: dict[str, Any]) -> Optional[float]:
        row = quotes.get(contract["instrument_id"])
        if not row:
            return None
        try:
            value = float(_value(row, "ltp", "lastTradedPrice", "lastPrice"))
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None

    long_premium, short_premium = premium(long_contract), premium(short_contract)
    if long_premium is None or short_premium is None:
        return {**base, "status": "UNAVAILABLE", "reason": "IIFL did not return usable live premiums for both option legs."}
    lot_size = long_contract.get("lot_size") or short_contract.get("lot_size")
    try:
        lot_size = int(float(lot_size))
    except (TypeError, ValueError):
        return {**base, "status": "UNAVAILABLE", "reason": "IIFL did not provide a valid lot size for the selected option contracts."}
    if lot_size <= 0:
        return {**base, "status": "UNAVAILABLE", "reason": "IIFL did not provide a positive lot size for the selected option contracts."}
    debit = long_premium - short_premium
    spread_width = abs(short_strike - long_strike)
    if debit <= 0 or debit >= spread_width:
        return {**base, "status": "NO_TRADE", "reason": "The live premiums do not form a valid positive-debit, defined-risk spread at these strikes."}
    max_loss = debit * lot_size
    max_profit = (spread_width - debit) * lot_size
    breakeven = long_strike + breakeven_direction * debit
    return {
        **base,
        "status": "SETUP_READY",
        "strategy": strategy,
        "expiry": expiry.isoformat(),
        "lot_size": lot_size,
        "spread_width": spread_width,
        "net_debit": round(debit, 2),
        "max_loss_one_lot": round(max_loss, 2),
        "max_profit_one_lot": round(max_profit, 2),
        "breakeven": round(breakeven, 2),
        "legs": [
            {"side": "BUY", "symbol": long_contract["symbol"], "option_type": option_type, "strike": long_strike, "premium": round(long_premium, 2), "instrument_id": long_contract["instrument_id"]},
            {"side": "SELL", "symbol": short_contract["symbol"], "option_type": option_type, "strike": short_strike, "premium": round(short_premium, 2), "instrument_id": short_contract["instrument_id"]},
        ],
        "reason": "The spread follows the confirmed NIFTY intraday bias. Both legs use the nearest listed expiry and live IIFL premiums.",
    }
