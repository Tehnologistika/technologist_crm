import importlib, sys, types

class DummySheet:
    def __init__(self):
        self.rows = []
    def append_row(self, row):
        self.rows.append(list(row))
    def get_all_values(self):
        return [list(map(str, r)) for r in self.rows]
    def update_cell(self, row, col, value):
        while len(self.rows) < row:
            self.rows.append([""] * 11)
        row_data = self.rows[row-1]
        while len(row_data) < col:
            row_data.append("")
        row_data[col-1] = value


def setup_sheets(monkeypatch):
    fake_sheet = DummySheet()
    fake_client = types.SimpleNamespace(open_by_key=lambda key: types.SimpleNamespace(worksheet=lambda name: fake_sheet))
    fake_gspread = types.SimpleNamespace(authorize=lambda creds: fake_client)
    fake_creds = types.SimpleNamespace(from_service_account_file=lambda *a, **k: None)
    service_account = types.ModuleType('service_account')
    service_account.Credentials = fake_creds
    oauth2 = types.ModuleType('oauth2')
    oauth2.service_account = service_account
    google = types.ModuleType('google')
    google.oauth2 = oauth2
    monkeypatch.setitem(sys.modules, 'gspread', fake_gspread)
    monkeypatch.setitem(sys.modules, 'google', google)
    monkeypatch.setitem(sys.modules, 'google.oauth2', oauth2)
    monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', service_account)
    spec = importlib.util.spec_from_file_location('sheets', 'sheets.py')
    sheets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sheets)
    monkeypatch.setattr(sheets, 'sheet', fake_sheet, raising=False)
    return sheets, fake_sheet


def test_add_and_update(monkeypatch):
    sheets, fake = setup_sheets(monkeypatch)
    sheets.add_request_row({
        'id': 9999,
        'date': '2024-01-01',
        'navigator': 'Nav',
        'customer_company': 'CustCo',
        'route': 'A-B',
        'cargo': '3 cars',
        'orig_price': '100000'
    })
    sheets.update_request(9999, {
        'driver': 'Driver',
        'carrier_company': 'Carrier',
        'carrier_price': '90000',
        'status': 'Подтверждена'
    })
    assert fake.rows == [[
        9999, '2024-01-01', 'Nav', 'CustCo', 'A-B', '3 cars', '100000',
        'Driver', 'Carrier', '90000', 'Подтверждена'
    ]]

