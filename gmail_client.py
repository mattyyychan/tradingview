"""Gmail client for reading and searching emails."""

import base64
from email.utils import parsedate_to_datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def get_gmail_service(creds: Credentials):
    """Build and return a Gmail API service instance."""
    return build("gmail", "v1", credentials=creds)


def search_emails(service, query: str = "is:unread", max_results: int = 10) -> list[dict]:
    """Search Gmail and return a list of parsed email summaries.

    Args:
        service: Gmail API service instance.
        query: Gmail search query string (same syntax as the Gmail search bar).
        max_results: Maximum number of emails to return.

    Returns:
        List of dicts with keys: id, subject, from, date, snippet, body.
    """
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )

    messages = results.get("messages", [])
    if not messages:
        return []

    emails = []
    for msg_ref in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_ref["id"], format="full")
            .execute()
        )
        emails.append(_parse_message(msg))

    return emails


def _parse_message(msg: dict) -> dict:
    """Extract useful fields from a raw Gmail API message."""
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

    body = _get_body(msg["payload"])

    return {
        "id": msg["id"],
        "subject": headers.get("subject", "(no subject)"),
        "from": headers.get("from", ""),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "body": body,
    }


def _get_body(payload: dict) -> str:
    """Recursively extract the plain-text body from a message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _get_body(part)
        if text:
            return text

    return ""
