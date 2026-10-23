"""
Google Drive integration helper for uploading and syncing documentation.
"""

import os
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.http import MediaFileUpload  # type: ignore
from integrations.gsheets import _get_credentials

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUTS_DIR = os.path.join(_ROOT_DIR, "outputs")
_DRIVE_DOC_URL_FILE = os.path.join(_OUTPUTS_DIR, "gdrive_share_market_basics_url.txt")
_DOC_ID_FILE = os.path.join(_OUTPUTS_DIR, "gdrive_doc_id.txt")


def upload_or_update_file(local_filepath, as_google_doc=True):
    """
    Uploads or updates a local markdown file on Google Drive.
    """
    from core.ui import (
        badge_drive, badge_error, bright_cyan, bright_yellow,
        bright_green, bright_white, dim, key_val
    )

    if not os.path.exists(local_filepath):
        print(f"  {badge_error('File')} Local file not found: {bright_yellow(local_filepath)}")
        return None

    filename = os.path.basename(local_filepath)
    creds = _get_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    existing_file_id = None
    if os.path.exists(_DOC_ID_FILE):
        try:
            with open(_DOC_ID_FILE, "r", encoding="utf-8") as f:
                saved_id = f.read().strip()
            if saved_id:
                drive_service.files().get(fileId=saved_id, fields="id, name, webViewLink").execute()
                existing_file_id = saved_id
        except Exception:
            existing_file_id = None

    if not existing_file_id:
        query = f"name = '{filename}' and trashed = false"
        if as_google_doc:
            doc_title = filename.replace(".md", "")
            query = f"(name = '{filename}' or name = '{doc_title}') and trashed = false"

        results = drive_service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, webViewLink)"
        ).execute()
        files = results.get("files", [])
        if files:
            existing_file_id = files[0]["id"]

    media = MediaFileUpload(local_filepath, mimetype="text/markdown", resumable=True)

    if existing_file_id:
        print(f"  {bright_cyan('Drive:')} Updating existing file on Google Drive {dim(f'(ID: {existing_file_id})')} ...")
        updated_file = drive_service.files().update(
            fileId=existing_file_id,
            media_body=media,
            fields="id, name, webViewLink"
        ).execute()
        web_link = updated_file.get("webViewLink")
        file_id = updated_file.get("id")
    else:
        print(f"  {bright_cyan('Drive:')} Uploading new file to Google Drive: {bright_yellow(filename)} ...")
        file_metadata = {"name": filename}
        if as_google_doc:
            file_metadata["mimeType"] = "application/vnd.google-apps.document"
            file_metadata["name"] = filename.replace(".md", "")

        created_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink"
        ).execute()
        web_link = created_file.get("webViewLink")
        file_id = created_file.get("id")

    os.makedirs(_OUTPUTS_DIR, exist_ok=True)
    with open(_DOC_ID_FILE, "w", encoding="utf-8") as f:
        f.write(file_id)

    with open(_DRIVE_DOC_URL_FILE, "w", encoding="utf-8") as f:
        f.write(web_link or "")

    print(f"\n  {badge_drive('Success')} Successfully uploaded/updated on Google Drive!")
    print(f"  {bright_cyan('Doc URL:')} {bright_yellow(web_link)}\n")
    return web_link
