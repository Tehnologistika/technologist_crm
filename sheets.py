import gspread
from google.oauth2.service_account import Credentials
import os

CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/home/a777/keys/prod-sa.json")
SPREADSHEET_ID = '1oZaOlgU9gX4IwAPaa_Cl2eXVKbLeSvSPtt0oAG4nKO0'
SHEET_NAME = 'Заявки'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

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

