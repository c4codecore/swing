"""IIFL live quote adapter. Credentials and daily session remain server-side."""
from __future__ import annotations

from datetime import datetime, time as day_time, timedelta
from threading import Lock
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


_lock = Lock()
_user_session: Optional[str] = None
_session_valid_until: Optional[datetime] = None
_cached_quote: Optional[Dict[str, Any]] = None
_quote_cached_at = 0.0


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
    return {"configured": configured, "authenticated": authenticated,
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
    global _user_session, _session_valid_until, _cached_quote, _quote_cached_at
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


def get_nifty_quote() -> Dict[str, Any]:
    global _cached_quote, _quote_cached_at
    settings = _settings()
    if not settings["nifty_instrument_id"]:
        raise IIFLNotConfigured("Set IIFL_NIFTY_INSTRUMENT_ID to the NIFTY 50 index ID from IIFL's INDICES instrument master.")

    with _lock:
        if not _user_session or not _session_valid_until or datetime.now(IST) >= _session_valid_until:
            raise IIFLSessionRequired("Sign in to IIFL to start the live market feed.")
        if _cached_quote and time.monotonic() - _quote_cached_at < 1.0:
            return dict(_cached_quote)
        session = _user_session

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
        result = {
            "symbol": "NIFTY 50", "price": price,
            "change": round(price - previous_close, 2),
            "change_pct": round((price - previous_close) / previous_close * 100, 2) if previous_close else None,
            "open": row.get("open"), "high": row.get("high"), "low": row.get("low"),
            "previous_close": previous_close,
            "tick_time": row.get("tickTimestamp"),
            "received_at": datetime.now(IST).isoformat(timespec="seconds"),
            "source": "IIFL live market quote",
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
        raise IIFLQuoteUnavailable("IIFL live quote is temporarily unavailable. Check the feed configuration.") from exc

    with _lock:
        _cached_quote = result
        _quote_cached_at = time.monotonic()
    return dict(result)
