class DummySheet:
    def __init__(self):
        self.rows = []

    def append_row(self, row):
        self.rows.append(list(row))

    def get_all_values(self):
        return [list(map(str, r)) for r in self.rows]

    def update_cell(self, row, col, value):
        while len(self.rows) < row:
            self.rows.append([""] * max(col, 1))
        if len(self.rows[row - 1]) < col:
            self.rows[row - 1].extend([""] * (col - len(self.rows[row - 1])))
        self.rows[row - 1][col - 1] = value

    def update(self, rng, values):
        row = int(rng.split(":")[0][1:])
        while len(self.rows) < row:
            self.rows.append([""] * len(values[0]))
        self.rows[row - 1] = list(values[0])


class Client:
    def __init__(self, sheet=None):
        self.sheet = sheet or DummySheet()

    def open_by_key(self, key):
        return type("Obj", (), {"worksheet": lambda self2, name: self.sheet})()


def authorize(_):
    return Client()

