# IIFL live NIFTY feed

The app requests IIFL's market quote endpoint from the backend and refreshes the overview quote every few seconds. The IIFL session token stays in backend memory and expires at midnight IST; sign in again on each trading day. No order APIs are called by this live quote integration.

## One-time setup

1. Treat credentials that were pasted into a chat as exposed. Rotate the IIFL app secret and discard the pasted authorization code before connecting this app.
2. Sign in to the IIFL developer portal with the IIFL trading account, create an individual/personal application, and confirm with IIFL that live market data and the NIFTY 50 index are enabled.
3. Register this exact redirect URL on the IIFL app: `http://127.0.0.1:8001/api/market/live/callback`. The app now relies on the redirect URL registered in the IIFL Developer Portal; the URL in `IIFL_REDIRECT_URL` must match it exactly. A successful login should land on `127.0.0.1:8001/api/market/live/callback` with `authCode` and `clientId` query parameters. If the browser stays on `markets.iiflcapital.com`, the registered redirect URL is missing or not being honored by IIFL.
4. Copy `.env.example` to `.env` in this `backend` folder. Add the newly issued app key, app secret, IIFL client ID, and NIFTY index instrument ID from IIFL's `INDICES` instrument master. Do not put an auth code or session token in this file; the app obtains the daily session through the IIFL login callback.
5. Install backend requirements and start the app. On the overview, choose **Connect IIFL** and finish IIFL's own login and OTP/TOTP page. The browser returns to the app after successful login.

Keep `backend/.env` private and never commit or share it. If IIFL requires an HTTPS or pre-registered redirect URL for the account, use the exact URL supplied by IIFL and update both the app configuration and `IIFL_REDIRECT_URL`.
