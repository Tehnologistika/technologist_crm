import gspread
from google.oauth2.service_account import Credentials
import os, io, json

key_path = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(__file__), "keys", "prod-sa.json"),
)
if not os.path.isfile(key_path):
    raise RuntimeError(
        "Service account key not found. "
        "Set GOOGLE_APPLICATION_CREDENTIALS or place prod-sa.json"
    )

with io.open(key_path, "r", encoding="utf-8") as f:
    sa_config = json.load(f)
SPREADSHEET_ID = '1oZaOlgU9gX4IwAPaa_Cl2eXVKbLeSvSPtt0oAG4nKO0'
SHEET_NAME = 'Заявки'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_info(sa_config, scopes=SCOPES)
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

