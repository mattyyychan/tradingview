"""Google API authentication helper.

Handles OAuth 2.0 flow for Gmail and Google Sheets access.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

TOKEN_FILE = "token.json"


def get_credentials(credentials_file: str = "credentials.json") -> Credentials:
    """Get valid Google API credentials, prompting login if needed.

    On first run, opens a browser for OAuth consent. Subsequent runs reuse
    the saved token, refreshing it automatically when expired.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds
