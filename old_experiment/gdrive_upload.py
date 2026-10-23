"""
Upload / Update Markdown documents (like docs/Share_Market_Basics.md) to Google Drive.

Usage:
    python gdrive_upload.py
    python gdrive_upload.py --raw-md
    python gdrive_upload.py --file docs/Share_Market_Basics.md
"""

import os
import argparse
from integrations.gdrive import upload_or_update_file

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DOC = os.path.join(_HERE, "docs", "Share_Market_Basics.md")


def main():
    parser = argparse.ArgumentParser(description="Upload or update markdown on Google Drive")
    parser.add_argument("--file", default=_DEFAULT_DOC, help="Path to markdown file")
    parser.add_argument("--raw-md", action="store_true", help="Upload as raw .md file instead of converting to Google Doc")
    args = parser.parse_args()

    upload_or_update_file(args.file, as_google_doc=not args.raw_md)


if __name__ == "__main__":
    main()
