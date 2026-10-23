"""
Google Drive & Google Sheets Sync CLI for Swing Trading Outputs.

Usage:
    # 1. Sync all output files to Google Drive right now:
    python sync_outputs.py

    # 2. Watch outputs/ folder in real-time and auto-update Google Drive on any changes:
    python sync_outputs.py --watch

    # 3. Specify a custom Google Drive folder name:
    python sync_outputs.py --folder "My Swing Trading Results"
"""

import argparse
from integrations.drive_sync import sync_all_outputs, watch_outputs, DEFAULT_DRIVE_FOLDER_NAME


def main():
    parser = argparse.ArgumentParser(description="Sync outputs folder to Google Drive & Google Sheets")
    parser.add_argument(
        "--folder",
        default=DEFAULT_DRIVE_FOLDER_NAME,
        help=f"Target Google Drive folder name (default: '{DEFAULT_DRIVE_FOLDER_NAME}')"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Run live watcher that auto-syncs whenever outputs/ files change"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3,
        help="Polling interval in seconds for --watch mode (default: 3)"
    )
    args = parser.parse_args()

    if args.watch:
        watch_outputs(folder_name=args.folder, poll_interval=args.interval)
    else:
        sync_all_outputs(folder_name=args.folder)


if __name__ == "__main__":
    main()
