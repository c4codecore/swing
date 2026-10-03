"""
Google Drive & Google Sheets Synchronizer for Outputs Folder.

This module:
1. Creates or finds a dedicated Google Drive folder (e.g. "Swing Trading Outputs").
2. Syncs all CSV files in outputs/ (watchlist, backtests, regime splits, etc.)
   into individual Google Sheets inside that Google Drive folder.
3. Formats header rows with a professional styling (freeze top row, bold headers, clean padding).
4. Provides continuous file watching (--watch mode) to auto-sync whenever outputs change.
"""

import os
import sys
import time
import glob
import pandas as pd
from datetime import datetime

try:
    from googleapiclient.discovery import build  # type: ignore
    from googleapiclient.http import MediaFileUpload  # type: ignore
except ImportError:
    build = None
    MediaFileUpload = None

from integrations.gsheets import _get_credentials

# Project root directory
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUTS_DIR = os.path.join(_ROOT_DIR, "outputs")
_FOLDER_ID_FILE = os.path.join(_OUTPUTS_DIR, "drive_folder_id.txt")
_SYNC_URLS_FILE = os.path.join(_OUTPUTS_DIR, "drive_sync_urls.txt")

DEFAULT_DRIVE_FOLDER_NAME = "Swing Trading Outputs"

# Mapping of file basenames to clean Google Sheet titles
SHEET_NAME_MAPPING = {
    "watchlist.csv": "Swing Trading Watchlist",
    "backtest_summary.csv": "Backtest Summary",
    "backtest_trades.csv": "Backtest Trades",
    "backtest_trades_with_regime.csv": "Backtest Trades (Regime Tagged)",
    "backtest_regime_summary.csv": "Backtest Regime Summary",
    "backtest_yearly.csv": "Backtest Yearly Breakdown",
    "backtest_monthly.csv": "Backtest Monthly Breakdown",
}


def get_or_create_drive_folder(drive_service, folder_name=DEFAULT_DRIVE_FOLDER_NAME):
    """
    Finds or creates a Google Drive folder by name.
    Returns (folder_id, folder_url).
    """
    # 1. Check if cached ID is still valid
    if os.path.exists(_FOLDER_ID_FILE):
        try:
            with open(_FOLDER_ID_FILE, "r", encoding="utf-8") as f:
                saved_id = f.read().strip()
            if saved_id:
                folder_obj = drive_service.files().get(
                    fileId=saved_id,
                    fields="id, name, webViewLink, trashed"
                ).execute()
                if not folder_obj.get("trashed"):
                    url = folder_obj.get("webViewLink", f"https://drive.google.com/drive/folders/{saved_id}")
                    return saved_id, url
        except Exception:
            pass

    # 2. Search Drive for folder with this name
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, webViewLink)"
    ).execute()
    files = results.get("files", [])

    if files:
        folder_id = files[0]["id"]
        folder_url = files[0].get("webViewLink", f"https://drive.google.com/drive/folders/{folder_id}")
    else:
        # 3. Create new folder
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = drive_service.files().create(
            body=folder_metadata,
            fields="id, webViewLink"
        ).execute()
        folder_id = folder["id"]
        folder_url = folder.get("webViewLink", f"https://drive.google.com/drive/folders/{folder_id}")
        print(f"[Drive] Created Google Drive folder: '{folder_name}'")

    os.makedirs(_OUTPUTS_DIR, exist_ok=True)
    with open(_FOLDER_ID_FILE, "w", encoding="utf-8") as f:
        f.write(folder_id)

    return folder_id, folder_url


def _get_or_create_sheet_in_folder(drive_service, sheets_service, folder_id, sheet_title):
    """
    Finds or creates a Google Spreadsheet inside a specific Drive folder.
    Returns (sheet_id, sheet_url, is_new).
    """
    query = f"'{folder_id}' in parents and name = '{sheet_title}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    results = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, webViewLink)"
    ).execute()
    files = results.get("files", [])

    if files:
        sheet_id = files[0]["id"]
        sheet_url = files[0].get("webViewLink", f"https://docs.google.com/spreadsheets/d/{sheet_id}")
        return sheet_id, sheet_url, False

    # Create new sheet inside folder
    file_metadata = {
        "name": sheet_title,
        "parents": [folder_id],
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }
    file = drive_service.files().create(
        body=file_metadata,
        fields="id, webViewLink"
    ).execute()
    sheet_id = file["id"]
    sheet_url = file.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{sheet_id}")

    return sheet_id, sheet_url, True


def _format_sheet_header(sheets_service, sheet_id):
    """Applies freezing and styling to the first row of a Google Sheet."""
    try:
        format_requests = [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 0,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True,
                                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                            },
                            "backgroundColor": {
                                "red": 0.12,
                                "green": 0.23,
                                "blue": 0.38,
                            },
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
        pass  # Non-fatal styling


def sync_csv_to_drive_sheet(csv_path, drive_service=None, sheets_service=None, folder_id=None, folder_name=DEFAULT_DRIVE_FOLDER_NAME):
    """
    Syncs a local CSV file into its corresponding Google Sheet inside the Drive folder.
    """
    if not os.path.exists(csv_path):
        print(f"[!] File not found: {csv_path}")
        return None

    if build is None:
        print("[!] Google API client library not available. Skipping Google Drive sync.")
        return None

    filename = os.path.basename(csv_path)
    sheet_title = SHEET_NAME_MAPPING.get(filename, filename.replace(".csv", "").replace("_", " ").title())

    try:
        creds = _get_credentials()
        if drive_service is None:
            drive_service = build("drive", "v3", credentials=creds)
        if sheets_service is None:
            sheets_service = build("sheets", "v4", credentials=creds)
        if folder_id is None:
            folder_id, _ = get_or_create_drive_folder(drive_service, folder_name)

        # Read CSV data
        df = pd.read_csv(csv_path)
        if df.empty:
            headers = [list(pd.read_csv(csv_path, nrows=0).columns)]
            rows_data = headers
        else:
            headers = list(df.columns)
            rows_data = [headers]
            for _, row in df.iterrows():
                row_vals = []
                for val in row:
                    if pd.isna(val):
                        row_vals.append("")
                    elif isinstance(val, float):
                        import math
                        if math.isnan(val):
                            row_vals.append("")
                        elif math.isinf(val):
                            row_vals.append("Infinity" if val > 0 else "-Infinity")
                        else:
                            row_vals.append(val)
                    elif isinstance(val, int):
                        row_vals.append(val)
                    else:
                        row_vals.append(str(val))
                rows_data.append(row_vals)

        # Get or create spreadsheet
        sheet_id, sheet_url, is_new = _get_or_create_sheet_in_folder(drive_service, sheets_service, folder_id, sheet_title)

        # Clear existing content to avoid stale trailing rows
        try:
            sheets_service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range="A1:ZZ50000",
            ).execute()
        except Exception:
            pass

        # Write fresh data
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="A1",
            valueInputOption="USER_ENTERED",
            body={"values": rows_data},
        ).execute()

        if is_new:
            _format_sheet_header(sheets_service, sheet_id)

        print(f"  [Synced] {filename:<32} -> {sheet_title} ({len(rows_data)-1} rows)")
        return {
            "filename": filename,
            "title": sheet_title,
            "id": sheet_id,
            "url": sheet_url,
            "rows": len(rows_data) - 1,
        }

    except Exception as e:
        print(f"  [Error] Failed syncing {filename}: {e}")
        return None


def sync_all_outputs(outputs_dir=_OUTPUTS_DIR, folder_name=DEFAULT_DRIVE_FOLDER_NAME):
    """
    Syncs all CSV files in outputs/ directory to Google Drive folder as Google Sheets.
    """
    if build is None:
        print("[!] Google API libraries not installed. Skipping Google Drive sync.")
        return None

    if not os.path.exists(outputs_dir):
        print(f"[!] Outputs directory '{outputs_dir}' does not exist.")
        return None

    csv_files = sorted(glob.glob(os.path.join(outputs_dir, "*.csv")))
    if not csv_files:
        print("[!] No CSV files found in outputs/ directory.")
        return None

    print("\n" + "=" * 70)
    print(f"Google Drive & Google Sheets Sync: '{folder_name}'")
    print("=" * 70)

    creds = _get_credentials()
    drive_service = build("drive", "v3", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)

    folder_id, folder_url = get_or_create_drive_folder(drive_service, folder_name)
    print(f"Drive Folder: {folder_name}")
    print(f"Folder URL:   {folder_url}\n")

    synced_items = []
    for csv_file in csv_files:
        res = sync_csv_to_drive_sheet(
            csv_file,
            drive_service=drive_service,
            sheets_service=sheets_service,
            folder_id=folder_id,
            folder_name=folder_name,
        )
        if res:
            synced_items.append(res)

    # Save summary report to outputs/drive_sync_urls.txt
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(_SYNC_URLS_FILE, "w", encoding="utf-8") as f:
        f.write(f"Google Drive Outputs Folder & Google Sheets (Last Synced: {now_str})\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Main Drive Folder:\n{folder_url}\n\n")
        f.write("Individual Google Sheets:\n")
        f.write("-" * 80 + "\n")
        for item in synced_items:
            f.write(f"- {item['title']} ({item['filename']}):\n  {item['url']}\n")

    print("\n" + "-" * 70)
    print(f"Sync complete! {len(synced_items)} file(s) updated in Google Drive.")
    print(f"Drive Folder URL: {folder_url}")
    print(f"Full links list saved to: outputs/drive_sync_urls.txt")
    print("=" * 70 + "\n")

    return {
        "folder_url": folder_url,
        "folder_id": folder_id,
        "items": synced_items,
    }


def watch_outputs(outputs_dir=_OUTPUTS_DIR, folder_name=DEFAULT_DRIVE_FOLDER_NAME, poll_interval=3):
    """
    Watches the outputs directory and automatically syncs to Google Drive whenever
    any CSV file is modified or newly added.
    """
    print("\n" + "=" * 70)
    print(f"Starting real-time file watcher on: {outputs_dir}")
    print(f"Syncing target Google Drive folder: '{folder_name}'")
    print(f"Polling interval: {poll_interval} seconds. Press Ctrl+C to stop.")
    print("=" * 70)

    # Initial sync
    sync_all_outputs(outputs_dir=outputs_dir, folder_name=folder_name)

    file_timestamps = {}
    for f in glob.glob(os.path.join(outputs_dir, "*.csv")):
        file_timestamps[f] = os.path.getmtime(f)

    try:
        while True:
            time.sleep(poll_interval)
            current_files = glob.glob(os.path.join(outputs_dir, "*.csv"))
            changed = False

            for f in current_files:
                mtime = os.path.getmtime(f)
                if f not in file_timestamps or mtime > file_timestamps[f]:
                    changed = True
                    file_timestamps[f] = mtime

            if changed:
                now_str = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{now_str}] Changes detected in outputs/. Syncing to Google Drive...")
                sync_all_outputs(outputs_dir=outputs_dir, folder_name=folder_name)

    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    if "--watch" in sys.argv or "-w" in sys.argv:
        watch_outputs()
    else:
        sync_all_outputs()
