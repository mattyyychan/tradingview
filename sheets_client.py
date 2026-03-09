"""Google Sheets client for writing data."""

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def get_sheets_service(creds: Credentials):
    """Build and return a Google Sheets API service instance."""
    return build("sheets", "v4", credentials=creds)


def append_rows(service, spreadsheet_id: str, rows: list[list[str]], sheet_name: str = "Sheet1"):
    """Append rows of data to a Google Sheet.

    Args:
        service: Sheets API service instance.
        spreadsheet_id: The ID from the spreadsheet URL.
        rows: List of rows, where each row is a list of cell values.
        sheet_name: Name of the tab/sheet to write to.

    Returns:
        The API response dict with update metadata.
    """
    body = {"values": rows}
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    return result


def write_header(service, spreadsheet_id: str, headers: list[str], sheet_name: str = "Sheet1"):
    """Write a header row to cell A1 if the sheet is empty.

    Args:
        service: Sheets API service instance.
        spreadsheet_id: The ID from the spreadsheet URL.
        headers: List of column header strings.
        sheet_name: Name of the tab/sheet.
    """
    existing = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:A1")
        .execute()
    )
    if not existing.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()


def read_sheet(service, spreadsheet_id: str, range_name: str = "Sheet1") -> list[list[str]]:
    """Read all data from a sheet range.

    Args:
        service: Sheets API service instance.
        spreadsheet_id: The ID from the spreadsheet URL.
        range_name: A1 notation range (e.g. "Sheet1" or "Sheet1!A1:D10").

    Returns:
        List of rows, where each row is a list of cell values.
    """
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    return result.get("values", [])
