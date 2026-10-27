# IIFL live NIFTY feed

The backend subscribes to IIFL's BridgePy market feed for NIFTY ticks and keeps the latest tick in memory; the overview reads that value once per second. The IIFL session token stays in backend memory and expires at midnight IST; sign in again on each trading day. No order APIs are called by this live quote integration.

## One-time setup

1. Treat credentials that were pasted into a chat as exposed. Rotate the IIFL app secret and discard the pasted authorization code before connecting this app.
2. Sign in to the IIFL developer portal with the IIFL trading account, create an individual/personal application, and confirm with IIFL that live market data and the NIFTY 50 index are enabled.
3. Register this exact redirect URL on the IIFL app: `http://127.0.0.1:8001/api/market/live/callback`. The app now relies on the redirect URL registered in the IIFL Developer Portal; the URL in `IIFL_REDIRECT_URL` must match it exactly. A successful login should land on `127.0.0.1:8001/api/market/live/callback` with `authCode` and `clientId` query parameters. If the browser stays on `markets.iiflcapital.com`, the registered redirect URL is missing or not being honored by IIFL.
4. Copy `.env.example` to `.env` in this `backend` folder. Add the newly issued app key, app secret, IIFL client ID, and NIFTY index instrument ID from IIFL's `INDICES` instrument master. Do not put an auth code or session token in this file; the app obtains the daily session through the IIFL login callback.
5. Install backend requirements with `python -m pip install -r backend/requirements.txt` and start the app. On the overview, choose **Connect IIFL** and finish IIFL's own login and OTP/TOTP page. The browser returns to the app after successful login.

The NIFTY card shows the timestamp of the latest market tick. If the card says **IIFL quote delayed**, check the stream error shown below the price and verify that `IIFL_NIFTY_EXCHANGE` and `IIFL_NIFTY_INSTRUMENT_ID` match the `INDICES` instrument master.

The dashboard polls IIFL NIFTY quotes only during NSE's regular equity session (09:15–15:30 IST, Monday to Friday). The local live-status check runs every five seconds during that session, then sleeps until the next scheduled open. After hours the dashboard shows the latest daily close from the daily market-data source, and makes at most one authenticated IIFL quote request per calendar day if the page is opened while the market is closed. NSE holidays are not inferred automatically; add them as comma-separated `YYYY-MM-DD` dates in `NSE_MARKET_HOLIDAYS` in `backend/.env` so the status also treats those dates as closed.

Keep `backend/.env` private and never commit or share it. If IIFL requires an HTTPS or pre-registered redirect URL for the account, use the exact URL supplied by IIFL and update both the app configuration and `IIFL_REDIRECT_URL`.

## IIFL portfolio review

The current dashboard **Portfolio** page uses manual entries, so it does not need IIFL holdings authorization. Add an NSE ticker, quantity, and average buy price; the list is saved in that browser's local storage. The backend analyzes each ticker using Yahoo Finance daily history with EMA 20/50, RSI 14, and 20-session return. The page labels the results **Hold**, **Review for sale**, or **Insufficient data**, shows the indicators and reasons, and never places orders. Manual entries stay on that browser and are not synced to IIFL or other devices. The read-only IIFL `/api/portfolio` endpoint remains available in the backend but is not used by this screen.

## Intraday and options modules

The Intraday page uses IIFL's 5-minute NIFTY candles and live spot quote for a 15-minute opening-range breakout with VWAP/EMA confirmation. The Options page waits for that directional setup, reads the public IIFL NSEFO contract master, then prices a one-lot bull-call or bear-put debit spread from IIFL option quotes. Both views refresh every 30 seconds while open. They are read-only, do not place orders, and may show **Wait** when the market/data is stale or no setup is confirmed.

If an API response says **IP address not authorized for trading**, the request reached IIFL but was denied for the backend's outgoing public IP. Ask IIFL API support/RM which static public IP must be authorized for the API application and whether the allowlist applies to read-only holdings and market-data calls. A localhost/private LAN address is not the public IP IIFL sees.
