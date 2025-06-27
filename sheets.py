import os
import json

import gspread
from google.oauth2 import service_account


KEY_ENV = "GOOGLE_APPLICATION_CREDENTIALS"
DEFAULT_KEY = os.path.join(os.path.dirname(__file__), "keys", "prod-sa.json")
_warned = False


def safe_gspread_client() -> "gspread.Client | None":
    """Return authorized gspread client or ``None`` if key missing."""
    global _warned
    key_path = os.getenv(KEY_ENV, DEFAULT_KEY)
    if not os.path.isfile(key_path):
        if not _warned:
            print(
                f"\u26A0\ufe0f  Service-account json not found: {key_path}. "
                "Google Sheets features disabled."
            )
            _warned = True
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=scopes
    )
    return gspread.authorize(creds)


SPREADSHEET_ID = "1oZaOlgU9gX4IwAPaa_Cl2eXVKbLeSvSPtt0oAG4nKO0"
SHEET_NAME = "Заявки"

gspread_client = safe_gspread_client()
sheet = (
    gspread_client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    if gspread_client
    else None
)

COL_IDX = {
    'id': 1,
    'date': 2,
    'navigator': 3,
    'customer_company': 4,
    'route': 5,
    'cargo': 6,
    'orig_price': 7,
    'driver': 8,
    'carrier_company': 9,
    'carrier_price': 10,
    'status': 11,
}


def add_request_row(data: dict) -> None:
    """Append new request row to the Google Sheet."""
    if sheet is None:
        return
    row = [
        data.get('id', ''),
        data.get('date', ''),
        data.get('navigator', ''),
        data.get('customer_company', ''),
        data.get('route', ''),
        data.get('cargo', ''),
        data.get('orig_price', ''),
        '',
        '',
        '',
        'Активна',
    ]
    # determine next empty row starting from column A
    target = len(sheet.get_all_values()) + 1
    sheet.update(f"A{target}:K{target}", [row])


def update_request(request_id: int, updates: dict) -> None:
    """Update selected columns for a request found by its ID."""
    if sheet is None:
        return
    rows = sheet.get_all_values()
    target = None
    for idx, r in enumerate(rows, start=1):
        if r and str(r[0]) == str(request_id):
            target = idx
            break
    if not target:
        return
    for field, value in updates.items():
        col = COL_IDX.get(field)
        if col:
            sheet.update_cell(target, col, value)

