# Google Sheets & Google Drive Setup Guide

This project supports automated synchronization to **Google Sheets** for watchlist signals and **Google Drive** for markdown documents/notes.

---

## 1. Prerequisites & Installation

Install the required Google client libraries:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## 2. Google Cloud Setup (One-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one (e.g., `Swing-Trading-Screener`).
3. Enable APIs:
   - **Google Sheets API**
   - **Google Drive API**
4. Set up the OAuth Consent Screen:
   - User Type: **External**
   - Add your email address under **Test Users**.
5. Create OAuth Credentials:
   - Go to **Credentials** -> **Create Credentials** -> **OAuth Client ID**.
   - Application Type: **Desktop Application**.
   - Download the credentials JSON file.
   - Rename the downloaded file to `client_secret.json` and save it to the project root directory (`swing_trading/client_secret.json`).

---

## 3. Usage & Automated Sync

### Google Sheets Watchlist Sync
Every time you run the screener:
```bash
python run.py
```
If `client_secret.json` is present, it will prompt for browser authentication on first run and store credentials in `outputs/token.json`. It will auto-create a spreadsheet named `Swing Trading Watchlist` on your Google Drive and log signals automatically!

The link to your sheet will be printed in the terminal and saved to:
`outputs/sheet_url.txt`

### Google Drive Documentation Sync
To upload or update `docs/Share_Market_Basics.md` to your Google Drive:
```bash
python gdrive_upload.py
```
- It uses the cached token in `outputs/token.json`.
- It converts markdown into a native Google Doc.
- It updates the existing document on subsequent runs without creating duplicates.
