import importlib, sys, types

class DummySheet:
    def __init__(self):
        # header row to mimic real sheet
        self.rows = [[
            'id', 'date', 'navigator', 'customer_company', 'route', 'cargo',
            'orig_price', 'driver', 'carrier_company', 'carrier_price', 'status'
        ]]

    def append_row(self, row):
        self.rows.append(list(row))

    def get_all_values(self):
        return [list(map(str, r)) for r in self.rows]

    def update_cell(self, row, col, value):
        while len(self.rows) < row:
            self.rows.append([""] * 11)
        row_data = self.rows[row - 1]
        while len(row_data) < col:
            row_data.append("")
        row_data[col - 1] = value

    def update(self, rng, values):
        # range like "A2:K2"
        row = int(rng.split(':')[0][1:])
        while len(self.rows) < row:
            self.rows.append([""] * 11)
        row_values = values[0]
        if len(row_values) < 11:
            row_values = row_values + [""] * (11 - len(row_values))
        self.rows[row - 1] = list(row_values[:11])


def setup_sheets(monkeypatch, tmp_path):
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
    dummy_key = tmp_path / 'dummy.json'
    dummy_key.write_text('{}')
    monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', str(dummy_key))
    monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', service_account)
    spec = importlib.util.spec_from_file_location('sheets', 'sheets.py')
    sheets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sheets)
    monkeypatch.setattr(sheets, 'sheet', fake_sheet, raising=False)
    return sheets, fake_sheet


def test_add_and_update(monkeypatch, tmp_path):
    sheets, fake = setup_sheets(monkeypatch, tmp_path)
    sheets.add_request_row({
        'id': 9999,
        'date': '2024-01-01',
        'navigator': 'Nav',
        'customer_company': 'CustCo',
        'route': 'A-B',
        'cargo': '3 cars',
        'orig_price': '100000'
    })
    sheets.add_request_row({
        'id': 8888,
        'date': '2024-01-02',
        'navigator': 'Nav2',
        'customer_company': 'Cust2',
        'route': 'B-C',
        'cargo': '2 cars',
        'orig_price': '200000'
    })
    # first row (sheet row 2) should match first request
    assert fake.rows[1][:7] == [
        9999, '2024-01-01', 'Nav', 'CustCo', 'A-B', '3 cars', '100000'
    ]
    # second row (sheet row 3) should contain second request
    assert fake.rows[2][:7] == [
        8888, '2024-01-02', 'Nav2', 'Cust2', 'B-C', '2 cars', '200000'
    ]
    # update first request and check
    sheets.update_request(9999, {
        'driver': 'Driver',
        'carrier_company': 'Carrier',
        'carrier_price': '90000',
        'status': 'Подтверждена'
    })
    assert fake.rows[1] == [
        9999, '2024-01-01', 'Nav', 'CustCo', 'A-B', '3 cars', '100000',
        'Driver', 'Carrier', '90000', 'Подтверждена'
    ]

