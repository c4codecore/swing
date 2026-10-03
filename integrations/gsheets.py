"""
Google Sheets sync helper.

- OAuth 2.0 authentication (token cached in outputs/token.json after first login).
- Auto-creates a sheet named SHEET_TITLE if it does not already exist.
- Appends rows in the same column order as watchlist.csv.
- Prints the sheet URL on first run and saves it to outputs/sheet_url.txt.
"""

import os
import pandas as pd

SHEET_TITLE = "Swing Trading Watchlist"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Project root directory
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUTS_DIR = os.path.join(_ROOT_DIR, "outputs")
_CREDS_FILE = os.path.join(_ROOT_DIR, "client_secret.json")
_TOKEN_FILE = os.path.join(_OUTPUTS_DIR, "token.json")
_SHEET_URL_FILE = os.path.join(_OUTPUTS_DIR, "sheet_url.txt")


def _get_credentials():
    """
    Return valid OAuth2 credentials.
    - Loads cached token from token.json if it exists and is valid.
    - Refreshes automatically if the token is expired.
    - Runs the browser OAuth flow on first use.
    """
    try:
        from google.oauth2.credentials import Credentials  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    except ImportError:
        raise ImportError(
            "Google auth libraries not found.\n"
            "Run:  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )

    creds = None

    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(_CREDS_FILE):
                raise FileNotFoundError(
                    f"OAuth credentials file not found: {_CREDS_FILE}\n"
                    "See the setup guide in docs/google_sheets_setup.md"
                )
            flow = InstalledAppFlow.from_client_secrets_file(_CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(_OUTPUTS_DIR, exist_ok=True)
        with open(_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def _get_or_create_sheet(sheets_service, drive_service, headers):
    """
    Look for an existing spreadsheet named SHEET_TITLE.
    If found, return its ID and URL.
    If not found, create a new one, write the header row, format it, and return ID and URL.
    """
    results = (
        drive_service.files()
        .list(
            q=f"name = '{SHEET_TITLE}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
            spaces="drive",
            fields="files(id, name, webViewLink)",
        )
        .execute()
    )
    files = results.get("files", [])

    if files:
        sheet_id = files[0]["id"]
        sheet_url = files[0].get(
            "webViewLink", f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        )
        return sheet_id, sheet_url, False

    # Create new sheet
    spreadsheet_body = {
        "properties": {"title": SHEET_TITLE},
        "sheets": [{"properties": {"title": "Watchlist"}}],
    }
    sheet = sheets_service.spreadsheets().create(body=spreadsheet_body).execute()
    sheet_id = sheet["spreadsheetId"]
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

    # Write header row
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Watchlist!A1",
        valueInputOption="RAW",
        body={"values": [headers]},
    ).execute()

    # Format header: bold, dark background, light text, freeze row 1
    try:
        format_requests = [
            # Freeze row 1
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 0,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            # Bold + background color on row 1
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "backgroundColor": {"red": 0.15, "green": 0.25, "blue": 0.45},
                        }
                    },
                    "fields": "userEnteredFormat(textFormat,backgroundColor)",
                }
            },
        ]
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": format_requests},
        ).execute()
    except Exception:
        pass  # Formatting is nice-to-have, never break on it

    return sheet_id, sheet_url, True


def append_to_sheet(watchlist_df):
    """
    Append rows from watchlist_df into the Google Sheet.
    - Safe to call even if libraries are missing or credentials are absent (prints warning, does not crash).
    - Writes header row only when creating a new sheet.
    - Appends data rows to the bottom of the existing sheet.
    """
    if watchlist_df.empty:
        return

    try:
        from googleapiclient.discovery import build  # type: ignore
    except ImportError:
        print("\n[!] Google API libraries not installed. Skipping Google Sheets sync.")
        print("    Install with: pip install google-auth google-auth-oauthlib google-api-python-client")
        return

    try:
        creds = _get_credentials()
        sheets_service = build("sheets", "v4", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        headers = list(watchlist_df.columns)
        sheet_id, sheet_url, is_new = _get_or_create_sheet(sheets_service, drive_service, headers)

        # Save URL locally so the user can easily find it
        os.makedirs(_OUTPUTS_DIR, exist_ok=True)
        with open(_SHEET_URL_FILE, "w") as f:
            f.write(sheet_url)

        # Convert DataFrame rows to primitive types (strings / numbers) for JSON serialization
        rows_to_append = []
        for _, row in watchlist_df.iterrows():
            formatted_row = []
            for val in row:
                if pd.isna(val):
                    formatted_row.append("")
                elif isinstance(val, (int, float)):
                    formatted_row.append(val)
                else:
                    formatted_row.append(str(val))
            rows_to_append.append(formatted_row)

        sheets_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Watchlist!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows_to_append},
        ).execute()

        print(f"\n[Google Sheets] {len(rows_to_append)} row(s) synced successfully!")
        print(f"               Sheet URL: {sheet_url}")

    except FileNotFoundError as e:
        print(f"\n[Google Sheets] {e}")
        print("                Skipping Google Sheets sync. Local CSV was written successfully.")
    except Exception as e:
        print(f"\n[Google Sheets] Sync failed: {e}")
        print("                Local CSV was written successfully.")
