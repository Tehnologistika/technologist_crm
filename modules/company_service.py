import json
import re
import os
import sqlite3
import requests

# In-memory cache for companies
COMP_CACHE = {}

# Path to local SQLite cache
DB_PATH = os.path.join(os.path.dirname(__file__), "companies.sqlite")

# Ensure the SQLite database and table exist
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.execute("""
    CREATE TABLE IF NOT EXISTS company (
        inn  TEXT PRIMARY KEY,
        data TEXT NOT NULL
    )
""")
_conn.commit()

# Remote API endpoint (same as in telegram_bot.py)
COMPANY_API = "http://147.45.232.245:8000/company"

def _norm_inn(inn: str) -> str:
    """Normalize INN by stripping non-digits."""
    return re.sub(r"\D", "", inn or "")

async def _save_company(data: dict) -> None:
    """
    Save company data to local cache (SQLite + in-memory) and remote service.
    """
    inn = _norm_inn(data.get("inn", ""))
    if inn:
        # Update in-memory cache
        COMP_CACHE[inn] = data
        # Persist to SQLite
        _conn.execute(
            "INSERT OR REPLACE INTO company (inn, data) VALUES (?,?)",
            (inn, json.dumps(data, ensure_ascii=False))
        )
        _conn.commit()
    # Attempt to persist to remote API (best-effort)
    try:
        # Explicitly map all relevant fields so remote API always receives bank details
        payload = {
            "inn":       inn,
            "kpp":       data.get("kpp", ""),
            "name":      data.get("name", ""),
            "director":  data.get("director", ""),
            "address":   data.get("address", ""),
            # bank details
            "bank_name": data.get("bank_name", ""),
            "bank_rs":   data.get("bank_rs", ""),
            "bank_bic":  data.get("bank_bic", ""),
        }
        requests.post(f"{COMPANY_API}", json=payload, timeout=5)
    except Exception:
        pass

async def _get_company(inn: str) -> dict | None:
    """
    Retrieve company data by INN from cache, local SQLite, or remote API.
    """
    inn_clean = _norm_inn(inn)
    # In-memory cache
    if inn_clean in COMP_CACHE:
        return COMP_CACHE[inn_clean]
    # Local SQLite cache
    cur = _conn.execute(
        "SELECT data FROM company WHERE inn = ?",
        (inn_clean,)
    )
    row = cur.fetchone()
    if row:
        data = json.loads(row[0])
        COMP_CACHE[inn_clean] = data
        return data
    # Remote API
    try:
        resp = requests.get(f"{COMPANY_API}/{inn_clean}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            COMP_CACHE[inn_clean] = data
            return data
    except Exception:
        pass
    return None