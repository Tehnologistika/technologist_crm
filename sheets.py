import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/home/a777/keys/prod-sa.json")
SPREADSHEET_ID   = '1y4Gtr_Urqdf7OFWLXfPIowT03kMIX6poTerwXiypabs'      # <-- вставь свой ID
SHEET_NAME       = 'Заявки'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
sheet  = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

# Возможные статусы: confirmed | in_progress | done | paid
def add_record(agent_type: str, name: str, tg_id: int,
               message: str, original_amt: int, final_amt: int,
               driver_fio: str = '',
               status: str = '') -> None:
    """Записывает строку в Google-таблицу (добавлены driver_fio и новые статусы)."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sheet.append_row([
        now, agent_type, name, tg_id, message,
        original_amt, final_amt, driver_fio, status
    ])