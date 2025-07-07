import os
import json
import sqlite3
import httpx
DB_PATH = os.path.join(os.path.dirname(__file__), "companies.sqlite")

# Regex pattern that matches "Загрузить договор" button
UPLOAD_CONTRACT_PATTERN = r'^📑 Загрузить договор$'

def _ensure_db():
    """Создаёт SQLite‑таблицу companies(inn TEXT PK, data JSON) при первом обращении."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(
            "CREATE TABLE IF NOT EXISTS companies ("
            "inn TEXT PRIMARY KEY, "
            "data TEXT NOT NULL)"
        )
        cx.commit()
def format_company_requisites(company: dict) -> str:
    """Собирает единую строку реквизитов для договора.

    Формат:
        ИНН …, КПП … | ОГРНИП …, р/с …, в банке …, БИК …, Юридический адрес: …

    • Если в поле kpp 15 цифр — считаем это ОГРНИП.
    • Если в kpp уже присутствует метка «КПП»/«ОГРНИП», повторно не добавляем.
    • Если bank уже содержит слово «банк» — не дублируем «в банке».
    • Пропускаем пустые поля.
    """
    import re

    inn   = str(company.get("inn", "")).strip()
    kpp   = str(company.get("kpp", "")).strip()
    rs    = str(company.get("bank_rs", "")).strip()
    bank  = str(company.get("bank_name", "")).strip()
    bic   = str(company.get("bank_bic", "")).strip()
    addr  = str(company.get("address", "") or company.get("company_address", "")).strip()

    parts = []

    # --- INN ---
    if inn:
        parts.append(f"ИНН {inn}" if "ИНН" not in inn.upper() else inn)

    # --- KPP / OGRNIP ---
    if kpp:
        upper = kpp.upper()
        if "КПП" in upper or "ОГРНИП" in upper:
            parts.append(kpp)
        else:
            digits = re.sub(r"\D", "", kpp)
            label = "ОГРНИП" if len(digits) == 15 else "КПП"
            parts.append(f"{label} {kpp}")

    # --- Settlement account ---
    if rs:
        parts.append(f"р/с {rs}" if "р/С" not in rs.lower() and "р/С" not in rs.upper() else rs)

    # --- Bank name ---
    if bank:
        if "банк" in bank.lower():
            parts.append(bank)
        else:
            parts.append(f"в банке {bank}")

    # --- BIC ---
    if bic:
        parts.append(f"БИК {bic}" if "БИК" not in bic.upper() else bic)

    # --- Address ---
    if addr:
        parts.append(f"Юридический адрес: {addr}")

    return ", ".join(parts)

# ----------------------------------------------------------------------
# Helper: safely clean optional string (strip or return empty string)
# ----------------------------------------------------------------------
def _clean_optional(value: str | None) -> str:
    """
    Возвращает строку без начальных и конечных пробелов
    или пустую строку, если value is None.

    Используется визардами для безопасного чтения
    опциональных полей при закрытии заявки.
    """
    return value.strip() if isinstance(value, str) else ""

# ----------------------------------------------------------------------
# Helper: clean human‑readable free‑text field (FIO, bank name etc.)
# Leaves letters, spaces, dots and dashes; trims extra spaces.
# ----------------------------------------------------------------------
import re as _re

def _clean_human_field(value: str | None) -> str:
    """
    Очищает строку: оставляет буквы, пробелы, точки, дефисы.
    Схлопывает повторяющиеся пробелы и обрезает по краям.
    """
    if not isinstance(value, str):
        return ""
    clean = _re.sub(r"[^А-ЯA-Zа-яa-zёЁ .\\-]", " ", value)
    clean = _re.sub(r"\s{2,}", " ", clean)
    return clean.strip()

# ----------------------------------------------------------------------
# Helper: extract city name from free‑form address
# ----------------------------------------------------------------------
_city_bad_words = {"ул", "улица", "д", "дом", "house", "street"}

def _city_from(addr: str) -> str:
    """
    Пытается выделить название города из произвольной строки адреса.
    • Берёт подстроку до первой запятой / длинного тире / дефиса
    • Отбрасывает служебные слова («ул.», «д.» ...)
    • Возвращает первое «похожее» слово длиной ≥ 2 символа
    """
    if not isinstance(addr, str):
        return ""
    # split by first comma, em‑dash or hyphen
    cut = _re.split(r"[,—\-]", addr, maxsplit=1)[0].strip()
    # remove bad prefixes
    for bad in _city_bad_words:
        if cut.lower().startswith(bad):
            cut = cut[len(bad):].strip()
    # first adequate token
    for tok in cut.split():
        if len(tok) >= 2 and tok.lower() not in _city_bad_words:
            return tok.strip()
    return ""

# ----------------------------------------------------------------------
# Normalizers for INN / KPP used in wizards
# ----------------------------------------------------------------------
def _norm_inn(value: str | None) -> str:
    """Оставляет только цифры ИНН (10 или 12), иначе возвращает пустую строку."""
    import re
    digits = re.sub(r"\D", "", value or "")
    return digits if len(digits) in (10, 12) else ""

def _norm_kpp(value: str | None) -> str:
    """Оставляет только цифры KPP (9), иначе пустая строка."""
    import re
    digits = re.sub(r"\D", "", value or "")
    return digits if len(digits) == 9 else ""
 # ----------------------------------------------------------------------
# Regex pattern that matches user’s “Back” message in wizards
# Used by MessageHandler(filters.Regex(BACK_PATTERN), ...)
# ----------------------------------------------------------------------
BACK_PATTERN = r'^(?:Назад|↩️ Назад|🔙 Назад|⬅️ Назад)$'

# ----------------------------------------------------------------------
# Reply keyboard with a single «Назад» button (used in wizards)
# ----------------------------------------------------------------------
from telegram import ReplyKeyboardMarkup

BACK_KB = ReplyKeyboardMarkup(
    [["Назад"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ----------------------------------------------------------------------
# Helper: format money value with thousands separator and «руб.» suffix
# ----------------------------------------------------------------------
def fmt_money(amount: float | int | str) -> str:
    """
    Преобразует число (int/float/str) в строку вида «120 000 руб.»
    с пробелом‑разделителем тысяч (узкий неразрывный пробел).
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return str(amount)

    # форматируем с разделителем тысяч, без знаков после запятой
    text = f"{amount:,.0f}".replace(",", " ")  # узкий неразрывный пробел U+202F
    return f"{text} руб."

# ----------------------------------------------------------------------
# SQLite helpers: fetch / upsert saved companies
# ----------------------------------------------------------------------
def _get_company(inn: str) -> dict:
    """Возвращает dict данных компании по ИНН или {}."""
    _ensure_db()
    with sqlite3.connect(DB_PATH) as cx:
        row = cx.execute("SELECT data FROM companies WHERE inn = ?", (inn,)).fetchone()
    if not row:
        return {}
    data = json.loads(row[0])
    # unify address key
    addr = data.get("address") or data.get("company_address") or ""
    data["address"] = addr
    data.pop("company_address", None)
    return data


def _save_company(obj: dict):
    """Upsert компании в SQLite.  Ожидает dict с ключами inn, name, kpp, address, bank_*."""
    _ensure_db()
    inn = str(obj.get("inn", "")).strip()
    if not inn:
        return
    # normalize key names
    if "company_address" in obj and not obj.get("address"):
        obj["address"] = obj.pop("company_address")
    # json dump (ensure address exists)
    dumped = json.dumps(obj, ensure_ascii=False)
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(
            "INSERT INTO companies(inn, data) VALUES(?, ?) "
            "ON CONFLICT(inn) DO UPDATE SET data = excluded.data",
            (inn, dumped)
        )
        cx.commit()
# ----------------------------------------------------------------------
# Async HTTP helper: GET JSON
# ----------------------------------------------------------------------
async def _http_get_json(url: str) -> dict:
    """
    Asynchronous HTTP GET returning parsed JSON.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
# (Export utilities if __all__ is present)
try:
    __all__.append("DB_PATH")
    __all__.append("_get_company")
    __all__.append("_save_company")
    __all__.append("UPLOAD_CONTRACT_PATTERN")
    __all__.append("_city_from")
except Exception:
    pass