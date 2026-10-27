"""IIFL live quote adapter. Credentials and daily session remain server-side."""
from __future__ import annotations

import asyncio
import json
import struct
from datetime import datetime, time as day_time, timedelta
from threading import Lock, Thread
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import hashlib
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class IIFLNotConfigured(RuntimeError):
    pass


class IIFLSessionRequired(RuntimeError):
    pass


class IIFLQuoteUnavailable(RuntimeError):
    pass


class IIFLPortfolioUnavailable(RuntimeError):
    pass


_lock = Lock()
_user_session: Optional[str] = None
_session_valid_until: Optional[datetime] = None
_cached_quote: Optional[Dict[str, Any]] = None
_quote_cached_at = 0.0
_closed_quote_checked_date = None
_stream_thread: Optional[Thread] = None
_stream_connected = False
_stream_error: Optional[str] = None
_holdings_cache: Optional[Dict[str, Any]] = None
_holdings_cached_at = 0.0
_fo_contracts_cache: Optional[list[Dict[str, Any]]] = None
_fo_contracts_cached_at = 0.0


def is_nse_regular_market_open(now: Optional[datetime] = None) -> bool:
    """Return whether NSE's regular equity session is open in India time.

    Optional NSE holiday dates can be configured as comma-separated YYYY-MM-DD
    values in NSE_MARKET_HOLIDAYS.
    """
    current = now.astimezone(IST) if now else datetime.now(IST)
    if current.weekday() >= 5 or not (day_time(9, 15) <= current.time().replace(tzinfo=None) < day_time(15, 30)):
        return False
    holidays = {item.strip() for item in os.getenv("NSE_MARKET_HOLIDAYS", "").split(",") if item.strip()}
    return current.date().isoformat() not in holidays


def next_nse_regular_open(now: Optional[datetime] = None) -> datetime:
    """Find the next configured regular-session open, skipping weekends/holidays."""
    current = now.astimezone(IST) if now else datetime.now(IST)
    holidays = {item.strip() for item in os.getenv("NSE_MARKET_HOLIDAYS", "").split(",") if item.strip()}
    candidate_date = current.date()
    if current.weekday() < 5 and candidate_date.isoformat() not in holidays and current.time().replace(tzinfo=None) < day_time(9, 15):
        return datetime.combine(candidate_date, day_time(9, 15), tzinfo=IST)
    for offset in range(1, 370):
        candidate_date = current.date() + timedelta(days=offset)
        if candidate_date.weekday() < 5 and candidate_date.isoformat() not in holidays:
            return datetime.combine(candidate_date, day_time(9, 15), tzinfo=IST)
    return datetime.combine(current.date() + timedelta(days=1), day_time(9, 15), tzinfo=IST)


def _settings() -> Dict[str, str]:
    return {
        "app_key": os.getenv("IIFL_APP_KEY", "").strip(),
        "app_secret": os.getenv("IIFL_APP_SECRET", "").strip(),
        "client_id": os.getenv("IIFL_CLIENT_ID", "").strip(),
        "base_url": os.getenv("IIFL_BASE_URL", "https://api.iiflcapital.com/v1").strip().rstrip("/"),
        "nifty_exchange": os.getenv("IIFL_NIFTY_EXCHANGE", "NSEEQ").strip().upper(),
        "nifty_instrument_id": os.getenv("IIFL_NIFTY_INSTRUMENT_ID", "").strip(),
        "redirect_url": os.getenv("IIFL_REDIRECT_URL", "http://127.0.0.1:8001/api/market/live/callback").strip(),
    }


def configuration_status() -> Dict[str, Any]:
    settings = _settings()
    configured = all(settings[key] for key in ("app_key", "app_secret", "client_id", "nifty_instrument_id"))
    with _lock:
        authenticated = bool(_user_session and _session_valid_until and datetime.now(IST) < _session_valid_until)
        stream_connected = _stream_connected
        stream_error = _stream_error
    market_open = is_nse_regular_market_open()
    return {"configured": configured, "authenticated": authenticated,
            "stream_connected": stream_connected, "stream_error": stream_error,
            "market_open": market_open,
            "next_market_open_at": None if market_open else next_nse_regular_open().isoformat(timespec="seconds"),
            "provider": "IIFL" if configured else None,
            "message": "Live quote connected" if authenticated else "Connect IIFL for live quotes" if configured else "IIFL credentials and NIFTY index instrument ID are not configured"}


def build_login_url() -> str:
    settings = _settings()
    if not settings["app_key"] or not settings["app_secret"] or not settings["client_id"]:
        raise IIFLNotConfigured("IIFL app credentials are not configured on this server.")
    # Use the redirect URL registered on the IIFL application. Passing a
    # localhost URL as the optional dynamic override can be treated as a
    # relative path by IIFL's login page, leaving the user on markets.iiflcapital.com.
    return "https://markets.iiflcapital.com/?" + urlencode({
        "v": "1", "appkey": settings["app_key"],
    })


def complete_login(client_id: str, auth_code: str) -> None:
    global _user_session, _session_valid_until, _cached_quote, _quote_cached_at, _holdings_cache, _holdings_cached_at
    settings = _settings()
    if not all(settings[key] for key in ("app_key", "app_secret", "client_id")):
        raise IIFLNotConfigured("IIFL app credentials are not configured on this server.")
    if client_id.strip().upper() != settings["client_id"].upper():
        raise IIFLSessionRequired("IIFL login returned a different client ID than configured.")

    checksum = hashlib.sha256(f"{client_id}{auth_code}{settings['app_secret']}".encode("utf-8")).hexdigest()
    try:
        response = requests.post(f"{settings['base_url']}/getusersession", json={"checkSum": checksum}, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.exception("IIFL session creation failed")
        raise IIFLSessionRequired("IIFL login could not be completed. Please sign in again.") from exc

    session = payload.get("userSession")
    if payload.get("status") != "Ok" or not session:
        raise IIFLSessionRequired("IIFL did not issue a market-data session. Please sign in again.")

    now = datetime.now(IST)
    expiry = datetime.combine(now.date() + timedelta(days=1), day_time.min, tzinfo=IST)
    with _lock:
        _user_session = session
        _session_valid_until = expiry
        _cached_quote = None
        _quote_cached_at = 0.0
        _holdings_cache = None
        _holdings_cached_at = 0.0
    _start_nifty_stream(session, settings)


def _stream_quote(data: bytearray, topic: str, expected_topic: str) -> None:
    """Decode IIFL's 188-byte market-feed packet and cache the NIFTY tick."""
    if topic.lower() != expected_topic:
        return
    try:
        packet = bytes(data)
        if len(packet) < 66:
            raise ValueError(f"IIFL market-feed packet was too short ({len(packet)} bytes).")

        def int32(offset: int) -> int:
            return struct.unpack_from("<i", packet, offset)[0]

        price_divisor = int32(58)
        if price_divisor <= 0:
            raise ValueError("IIFL market-feed packet has an invalid price divisor.")
        price = int32(0) / price_divisor
        previous_close = int32(24) / price_divisor
        traded_at = int32(62)
        tick_at = datetime.fromtimestamp(traded_at, IST).isoformat(timespec="seconds") if traded_at > 0 else None
        result = {
            "symbol": "NIFTY 50", "price": price,
            "change": round(price - previous_close, 2),
            "change_pct": round((price - previous_close) / previous_close * 100, 2) if previous_close else None,
            "open": int32(20) / price_divisor,
            "high": int32(12) / price_divisor,
            "low": int32(16) / price_divisor,
            "previous_close": previous_close,
            "tick_time": tick_at,
            "tick_at": tick_at,
            "received_at": datetime.now(IST).isoformat(timespec="seconds"),
            "source": "IIFL live market stream",
        }
    except Exception:
        logger.exception("Could not decode IIFL NIFTY stream packet")
        return

    global _cached_quote, _quote_cached_at
    with _lock:
        current_tick_at = None
        if _cached_quote:
            try:
                current_tick_at = datetime.fromisoformat(_cached_quote.get("tick_at"))
            except (TypeError, ValueError):
                pass
        incoming_tick_at = datetime.fromisoformat(tick_at) if tick_at else None
        if current_tick_at and (incoming_tick_at is None or incoming_tick_at < current_tick_at):
            logger.warning(
                "Ignoring out-of-order or untimestamped IIFL NIFTY stream tick (%s; latest is %s)",
                incoming_tick_at.isoformat() if incoming_tick_at else "no timestamp",
                current_tick_at.isoformat(),
            )
            return
        _cached_quote = result
        _quote_cached_at = time.monotonic()


def _start_nifty_stream(session: str, settings: Dict[str, str]) -> None:
    """Connect to IIFL BridgePy in a background thread and subscribe to NIFTY."""
    global _stream_thread, _stream_connected, _stream_error
    exchange = settings["nifty_exchange"].lower()
    instrument_id = settings["nifty_instrument_id"]
    expected_topic = f"{exchange}/{instrument_id}".lower()

    with _lock:
        if _stream_thread and _stream_thread.is_alive():
            return
        _stream_connected = False
        _stream_error = None

    def connect_and_subscribe() -> None:
        global _stream_connected, _stream_error
        try:
            from bridgePy import connector

            connection = connector.Connect()
            connection.on_feed_data_received = lambda data, topic: _stream_quote(data, topic, expected_topic)
            connection.on_error = lambda code, message: _set_stream_error(f"IIFL stream error {code}: {message}")

            def acknowledge(response: str) -> None:
                logger.info("IIFL stream: %s", response)
                try:
                    if json.loads(response).get("packetName") == "DISCONNECT":
                        _set_stream_error("IIFL market stream disconnected. Reconnect to resume live updates.")
                except (TypeError, ValueError):
                    pass

            connection.on_acknowledge_response = acknowledge

            async def start() -> None:
                connect_result = json.loads(await connection.connect_host(json.dumps({
                    "host": "bridge.iiflcapital.com", "port": 8883, "token": session,
                })))
                if connect_result.get("status") != 0 and not connection.is_host_connected:
                    raise RuntimeError(connect_result.get("message") or "Could not connect to IIFL market stream.")
                subscribe_result = json.loads(await connection.subscribe_feed(json.dumps({
                    "subscriptionList": [expected_topic],
                })))
                failed_topics = subscribe_result.get("failedTopics") or []
                if subscribe_result.get("status") != 0 or failed_topics:
                    raise RuntimeError("IIFL rejected the NIFTY stream subscription. Check the exchange and instrument ID in backend/.env.")

            asyncio.run(start())
            with _lock:
                _stream_connected = True
                _stream_error = None
        except Exception as exc:
            logger.exception("Unable to start IIFL NIFTY market stream")
            _set_stream_error(str(exc))

    _stream_thread = Thread(target=connect_and_subscribe, name="iifl-nifty-stream", daemon=True)
    _stream_thread.start()


def _set_stream_error(message: str) -> None:
    global _stream_connected, _stream_error
    with _lock:
        _stream_connected = False
        _stream_error = message


def get_nifty_quote() -> Dict[str, Any]:
    global _cached_quote, _quote_cached_at, _closed_quote_checked_date
    settings = _settings()
    if not settings["nifty_instrument_id"]:
        raise IIFLNotConfigured("Set IIFL_NIFTY_INSTRUMENT_ID to the NIFTY 50 index ID from IIFL's INDICES instrument master.")

    market_open = is_nse_regular_market_open()
    today = datetime.now(IST).date()
    with _lock:
        if not _user_session or not _session_valid_until or datetime.now(IST) >= _session_valid_until:
            raise IIFLSessionRequired("Sign in to IIFL to start the live market feed.")
        if not market_open and _closed_quote_checked_date == today:
            if _cached_quote:
                return dict(_cached_quote)
            raise IIFLQuoteUnavailable("Market is closed. No IIFL quote is cached yet; the daily close remains available in the market summary.")
        if _cached_quote and _cached_quote.get("source") == "IIFL live market stream":
            tick_at = _cached_quote.get("tick_at")
            try:
                tick_age = (datetime.now(IST) - datetime.fromisoformat(tick_at)).total_seconds()
            except (TypeError, ValueError):
                tick_age = float("inf")
            if 0 <= tick_age < 10:
                return dict(_cached_quote)
        if _cached_quote and time.monotonic() - _quote_cached_at < 1.0:
            return dict(_cached_quote)
        session = _user_session
        if not market_open:
            # After close, request one final/last quote per calendar day. This
            # also covers a page opened after the session without polling IIFL.
            _closed_quote_checked_date = today

    try:
        response = requests.post(
            f"{settings['base_url']}/marketdata/marketquotes",
            headers={"Authorization": f"Bearer {session}"},
            json=[{"exchange": settings["nifty_exchange"], "instrumentId": settings["nifty_instrument_id"]}],
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        records = payload.get("result") or []
        if payload.get("status") != "Ok" or not records:
            raise IIFLQuoteUnavailable("IIFL returned no NIFTY quote. Check the index instrument ID and account permissions.")
        row = records[0]
        price = float(row["ltp"])
        previous_close = float(row["close"])
        raw_tick_time = row.get("tickTimestamp")
        try:
            tick_at = datetime.strptime(raw_tick_time, "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST).isoformat(timespec="seconds") if raw_tick_time else None
        except (TypeError, ValueError):
            tick_at = None
        result = {
            "symbol": "NIFTY 50", "price": price,
            "change": round(price - previous_close, 2),
            "change_pct": round((price - previous_close) / previous_close * 100, 2) if previous_close else None,
            "open": row.get("open"), "high": row.get("high"), "low": row.get("low"),
            "previous_close": previous_close,
            "tick_time": raw_tick_time,
            "tick_at": tick_at,
            "received_at": datetime.now(IST).isoformat(timespec="seconds"),
            "source": "IIFL live market quote" if market_open else "IIFL day-end quote",
        }
    except (IIFLNotConfigured, IIFLSessionRequired, IIFLQuoteUnavailable):
        raise
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 401:
            raise IIFLSessionRequired("IIFL session expired. Please sign in again.") from exc
        logger.exception("IIFL quote provider returned an HTTP error")
        raise IIFLQuoteUnavailable("IIFL live quote is temporarily unavailable.") from exc
    except Exception as exc:
        logger.exception("IIFL live quote request failed")
        if not market_open:
            with _lock:
                if _cached_quote:
                    return dict(_cached_quote)
        raise IIFLQuoteUnavailable("IIFL live quote is temporarily unavailable. Check the feed configuration.") from exc

    with _lock:
        _cached_quote = result
        _quote_cached_at = time.monotonic()
    return dict(result)


def _authenticated_session() -> str:
    with _lock:
        if not _user_session or not _session_valid_until or datetime.now(IST) >= _session_valid_until:
            raise IIFLSessionRequired("Sign in to IIFL to access live trading data.")
        return _user_session


def get_iifl_intraday_candles(interval: str = "5 minutes", lookback_days: int = 4) -> list[list[Any]]:
    """Fetch recent NIFTY intraday candles from IIFL's historical-data API."""
    settings = _settings()
    session = _authenticated_session()
    today = datetime.now(IST).date()
    from_date = today - timedelta(days=max(lookback_days, 1))
    try:
        response = requests.post(
            f"{settings['base_url']}/marketdata/historicaldata",
            headers={"Authorization": f"Bearer {session}"},
            json={
                "exchange": settings["nifty_exchange"],
                "instrumentId": settings["nifty_instrument_id"],
                "interval": interval,
                "fromDate": from_date.strftime("%d-%b-%Y"),
                "toDate": today.strftime("%d-%b-%Y"),
            },
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict) or payload.get("status") != "Ok":
            message = payload.get("message") if isinstance(payload, dict) else "Unexpected candle response."
            raise IIFLQuoteUnavailable(f"IIFL intraday history is unavailable: {message}")
        result = payload.get("result") or []
        if isinstance(result, str):
            result = json.loads(result)
        if isinstance(result, dict):
            result = [result]
        candles = []
        for item in result:
            if isinstance(item, dict):
                candles.extend(item.get("candles") or [])
        return candles
    except IIFLQuoteUnavailable:
        raise
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 401:
            raise IIFLSessionRequired("IIFL session expired. Please sign in again.") from exc
        logger.warning("IIFL intraday history returned HTTP %s", exc.response.status_code if exc.response is not None else "unknown")
        raise IIFLQuoteUnavailable("IIFL intraday candles could not be fetched.") from exc
    except Exception as exc:
        logger.exception("IIFL intraday history request failed")
        raise IIFLQuoteUnavailable("IIFL intraday candles could not be parsed.") from exc


def get_iifl_market_quotes(instruments: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Fetch a small bulk quote set such as the two legs of an options spread."""
    if not instruments:
        return []
    settings = _settings()
    session = _authenticated_session()
    try:
        response = requests.post(
            f"{settings['base_url']}/marketdata/marketquotes",
            headers={"Authorization": f"Bearer {session}"},
            json=instruments,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "Ok":
            raise IIFLQuoteUnavailable(str(payload.get("message") or "IIFL option quotes are unavailable."))
        rows = payload.get("result") or []
        if isinstance(rows, str):
            rows = json.loads(rows)
        return rows if isinstance(rows, list) else [rows]
    except IIFLQuoteUnavailable:
        raise
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 401:
            raise IIFLSessionRequired("IIFL session expired. Please sign in again.") from exc
        logger.warning("IIFL bulk quote request returned HTTP %s", exc.response.status_code if exc.response is not None else "unknown")
        raise IIFLQuoteUnavailable("IIFL option quotes are temporarily unavailable.") from exc
    except Exception as exc:
        logger.exception("IIFL bulk quote request failed")
        raise IIFLQuoteUnavailable("IIFL option quotes are temporarily unavailable.") from exc


def get_iifl_fo_contracts() -> list[Dict[str, Any]]:
    """Read IIFL's public NSEFO contract master (cached for one trading day)."""
    global _fo_contracts_cache, _fo_contracts_cached_at
    if _fo_contracts_cache and time.monotonic() - _fo_contracts_cached_at < 3600:
        return json.loads(json.dumps(_fo_contracts_cache))
    settings = _settings()
    try:
        response = requests.get(f"{settings['base_url']}/contractfiles/NSEFO.json", timeout=15)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, str):
            payload = json.loads(payload)
        records: list[Dict[str, Any]] = []

        def visit(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                lowered = {str(key).lower() for key in value}
                if lowered.intersection({"optiontype", "option_type"}) and lowered.intersection({"strikeprice", "strike_price", "strike"}):
                    records.append(value)
                else:
                    for child in value.values():
                        if isinstance(child, (dict, list)):
                            visit(child)

        visit(payload)
        if not records:
            raise IIFLQuoteUnavailable("IIFL NSEFO contract master did not contain option contracts.")
    except IIFLQuoteUnavailable:
        raise
    except Exception as exc:
        logger.exception("Could not load IIFL NSEFO contract master")
        raise IIFLQuoteUnavailable("IIFL NSEFO contract master is temporarily unavailable.") from exc
    with _lock:
        _fo_contracts_cache = records
        _fo_contracts_cached_at = time.monotonic()
    return json.loads(json.dumps(records))


def _extract_iifl_holding_rows(payload: Any) -> tuple[list[Dict[str, Any]], bool]:
    """Unwrap holdings/positions arrays and common IIFL result envelopes."""
    row_fields = {
        "tradingsymbol", "symbol", "scripname", "companyname", "nsetradingsymbol",
        "bsetradingsymbol", "formattedinstrumentname", "isin", "nseinstrumentid", "bseinstrumentid",
    }
    containers = {"result", "data", "holdings", "holding", "holdinglist", "rmsholdinglist", "positions", "positionlist"}

    def walk(value: Any) -> tuple[list[Dict[str, Any]], bool]:
        if isinstance(value, list):
            if not value:
                return [], True
            collected: list[Dict[str, Any]] = []
            recognized = False
            for item in value:
                found, item_recognized = walk(item)
                collected.extend(found)
                recognized = recognized or item_recognized
            return collected, recognized
        if not isinstance(value, dict):
            return [], False
        if any(str(key).lower() in row_fields for key in value):
            return [value], True
        collected = []
        recognized = False
        for key, child in value.items():
            if str(key).lower() in containers:
                found, child_recognized = walk(child)
                collected.extend(found)
                # An explicit empty holdings/result list is a valid empty response.
                recognized = recognized or child_recognized
        return collected, recognized

    return walk(payload)


def _find_iifl_api_error(payload: Any) -> tuple[str, str] | None:
    """Find per-result EC errors without mistaking a holding row for an envelope."""
    row_fields = {
        "tradingsymbol", "symbol", "scripname", "companyname", "nsetradingsymbol",
        "bsetradingsymbol", "formattedinstrumentname", "isin", "nseinstrumentid", "bseinstrumentid",
    }
    containers = {"result", "data", "holdings", "holding", "holdinglist", "rmsholdinglist", "positions", "positionlist"}

    def walk(value: Any) -> tuple[str, str] | None:
        if isinstance(value, list):
            for item in value:
                error = walk(item)
                if error:
                    return error
            return None
        if not isinstance(value, dict):
            return None
        if any(str(key).lower() in row_fields for key in value):
            return None
        status = str(value.get("status") or "").upper()
        code = str(value.get("code") or "").upper()
        error_id = code if code.startswith("EC") else status
        message = str(value.get("message") or value.get("description") or "")
        if error_id.startswith("EC") or status in {"ERROR", "FAILED", "NOT_OK"}:
            return error_id or status, message
        for key, child in value.items():
            if str(key).lower() in containers:
                error = walk(child)
                if error:
                    return error
        return None

    return walk(payload)


def _normalize_iifl_holding(row: Dict[str, Any], *, record_type: str = "holding") -> Optional[Dict[str, Any]]:
    values = {str(key).lower(): value for key, value in row.items()}

    def first(*keys: str) -> Any:
        return next((values[key.lower()] for key in keys if values.get(key.lower()) is not None), None)

    nse_symbol = first("nseTradingSymbol")
    bse_symbol = first("bseTradingSymbol")
    symbol = first("tradingSymbol", "symbol", "scripName", "companyName") or nse_symbol or bse_symbol
    if not symbol:
        return None
    exchange = first("exchange", "exchangeSegment") or ("NSEEQ" if nse_symbol else "BSEEQ" if bse_symbol else "NSEEQ")
    is_nse = str(exchange).upper() == "NSEEQ"
    return {
        "symbol": str(symbol).strip(),
        "name": first("formattedInstrumentName", "companyName"),
        "exchange": exchange,
        "instrument_id": first("instrumentId", "nseInstrumentId" if is_nse else "bseInstrumentId", "token", "scripCode"),
        "quantity": first("netQuantity" if record_type == "position" else "totalQuantity", "holdingQuantity", "quantity", "netQuantity", "totalQuantity", "dpQuantity", "qty"),
        "average_price": first("netAveragePrice" if record_type == "position" else "averageTradedPrice", "averagePrice", "averageTradedPrice", "netAveragePrice", "buyAveragePrice", "costPrice", "avgPrice"),
        "last_price": first("lastTradedPrice", "ltp", "lastPrice", "marketPrice", "close", "previousDayClose"),
        "invested_value": first("investedValue", "costValue"),
        "pnl": first("pnl", "profitLoss", "unrealizedPnl", "unrealisedProfitLoss", "unrealizedProfitLoss"),
        "record_type": record_type,
        "product": first("product"),
    }


def get_portfolio_holdings(force_refresh: bool = False) -> Dict[str, Any]:
    """Fetch read-only equity holdings from the authenticated IIFL session."""
    global _holdings_cache, _holdings_cached_at
    settings = _settings()
    with _lock:
        if not _user_session or not _session_valid_until or datetime.now(IST) >= _session_valid_until:
            raise IIFLSessionRequired("Sign in to IIFL to view your holdings.")
        if not force_refresh and _holdings_cache and time.monotonic() - _holdings_cached_at < 60:
            return json.loads(json.dumps(_holdings_cache))
        session = _user_session

    try:
        response = requests.get(
            f"{settings['base_url']}/holdings",
            headers={"Authorization": f"Bearer {session}"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, (dict, list)):
            raise IIFLPortfolioUnavailable("IIFL returned an unsupported holdings response.")
        api_error = _find_iifl_api_error(payload)
        status = payload.get("status") if isinstance(payload, dict) else None
        empty_holdings_response = False
        if api_error:
            error_code, error_message = api_error
            if error_code == "EC922" or "EC922" in error_message or "no holdings found" in error_message.lower():
                empty_holdings_response = True
            else:
                raise IIFLPortfolioUnavailable(error_message or f"IIFL holdings API returned {error_code}.")
        elif status not in (None, "Ok"):
            message = str(payload.get("message") or "IIFL could not return portfolio holdings.")
            code = str(payload.get("code") or "").upper()
            if code == "EC922" or "EC922" in message or "no holdings found" in message.lower():
                empty_holdings_response = True
            else:
                raise IIFLPortfolioUnavailable(message)
        rows, recognized_shape = _extract_iifl_holding_rows(payload)
        if empty_holdings_response:
            rows, recognized_shape = [], True
        if not recognized_shape:
            top_keys = sorted(str(key) for key in payload) if isinstance(payload, dict) else []
            logger.warning("IIFL returned a successful but unrecognized holdings response shape (top-level keys: %s)", top_keys)
            raise IIFLPortfolioUnavailable("IIFL returned holdings data in an unexpected format. Check the backend log for the response field names.")
        holdings = [item for row in rows if isinstance(row, dict) if (item := _normalize_iifl_holding(row))]
        if not holdings:
            # A same-day delivery buy may still be an open cash position until it settles into DEMAT.
            try:
                positions_response = requests.get(
                    f"{settings['base_url']}/positions",
                    headers={"Authorization": f"Bearer {session}"},
                    timeout=10,
                )
                positions_response.raise_for_status()
                positions_payload = positions_response.json()
                position_rows, positions_shape = _extract_iifl_holding_rows(positions_payload)
                if positions_shape:
                    for row in position_rows:
                        if not isinstance(row, dict):
                            continue
                        item = _normalize_iifl_holding(row, record_type="position")
                        if not item or str(item["exchange"]).upper() not in {"NSEEQ", "BSEEQ"}:
                            continue
                        try:
                            if float(item["quantity"] or 0) <= 0:
                                continue
                        except (TypeError, ValueError):
                            continue
                        holdings.append(item)
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 401:
                    raise IIFLSessionRequired("IIFL session expired. Please sign in again.") from exc
                logger.warning("Could not read IIFL open positions for empty holdings (HTTP %s)", exc.response.status_code if exc.response is not None else "unknown")
            except Exception:
                logger.exception("Could not read IIFL open positions for empty holdings")
        data = {"holdings": holdings, "as_of": datetime.now(IST).isoformat(timespec="seconds"), "source": "IIFL"}
    except IIFLPortfolioUnavailable:
        raise
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 401:
            raise IIFLSessionRequired("IIFL session expired. Please sign in again.") from exc
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        # Some IIFL gateways return the useful authorization message in the
        # HTTP error body instead of a normal JSON API response.
        if exc.response is not None:
            try:
                body = exc.response.text or ""
            except Exception:
                body = ""
            if "ip address not authorized" in body.lower():
                raise IIFLPortfolioUnavailable("IP address not authorized for trading.") from exc
        logger.warning("IIFL holdings endpoint returned HTTP %s", status_code)
        raise IIFLPortfolioUnavailable(f"IIFL holdings API returned HTTP {status_code}. Please refresh; if it repeats, verify the API access and session.") from exc
    except Exception as exc:
        logger.exception("IIFL portfolio request failed")
        raise IIFLPortfolioUnavailable("Could not read holdings from IIFL. Check the API response and session.") from exc

    with _lock:
        _holdings_cache = data
        _holdings_cached_at = time.monotonic()
    return json.loads(json.dumps(data))
