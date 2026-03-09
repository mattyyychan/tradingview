# tradingview

Gmail + Google Sheets integration — reads emails from Gmail and writes summaries to a Google Sheet.

## Setup

### 1. Create Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API** and **Google Sheets API**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Choose **Desktop app** as the application type
6. Download the JSON file and save it as `credentials.json` in this directory

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set:
- `SPREADSHEET_ID` — the ID from your Google Sheet URL (`https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`)
- `GMAIL_QUERY` — Gmail search query (default: `is:unread`)
- `GMAIL_MAX_RESULTS` — max emails to fetch per run (default: `10`)

### 4. Run

```bash
python main.py
```

On first run, a browser window will open for Google OAuth consent. After authorizing, a `token.json` file is saved locally so you won't need to log in again.

## Project structure

| File | Description |
|---|---|
| `auth.py` | OAuth 2.0 authentication and token management |
| `gmail_client.py` | Gmail API client — search and read emails |
| `sheets_client.py` | Google Sheets API client — read, write, and append data |
| `main.py` | Main script that ties Gmail reading to Sheets writing |
