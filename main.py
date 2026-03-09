"""Main script: read emails from Gmail and write summaries to Google Sheets."""

import os
from dotenv import load_dotenv

from auth import get_credentials
from gmail_client import get_gmail_service, search_emails
from sheets_client import get_sheets_service, append_rows, write_header

load_dotenv()

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GMAIL_QUERY = os.getenv("GMAIL_QUERY", "is:unread")
GMAIL_MAX_RESULTS = int(os.getenv("GMAIL_MAX_RESULTS", "10"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

HEADERS = ["Date", "From", "Subject", "Snippet"]


def main():
    if not SPREADSHEET_ID:
        print("Error: Set SPREADSHEET_ID in your .env file.")
        return

    creds = get_credentials(CREDENTIALS_FILE)

    # --- Gmail ---
    gmail = get_gmail_service(creds)
    print(f"Searching Gmail with query: {GMAIL_QUERY}")
    emails = search_emails(gmail, query=GMAIL_QUERY, max_results=GMAIL_MAX_RESULTS)
    print(f"Found {len(emails)} email(s).")

    if not emails:
        print("No emails to write.")
        return

    # --- Sheets ---
    sheets = get_sheets_service(creds)
    write_header(sheets, SPREADSHEET_ID, HEADERS, sheet_name=SHEET_NAME)

    rows = [[e["date"], e["from"], e["subject"], e["snippet"]] for e in emails]
    result = append_rows(sheets, SPREADSHEET_ID, rows, sheet_name=SHEET_NAME)

    updated = result.get("updates", {}).get("updatedRows", 0)
    print(f"Wrote {updated} row(s) to spreadsheet.")


if __name__ == "__main__":
    main()
