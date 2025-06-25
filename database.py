from sqlalchemy import create_engine, MetaData, Table, Column, BigInteger, Integer, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from databases import Database
import datetime
import os

# ---------- PostgreSQL connection strings (from environment) ----------
DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://gpt:Techno2025_test@127.0.0.1:5432/technologist_crm"
)
DATABASE_URL_SYNC = DEFAULT_DATABASE_URL
DATABASE_URL_ASYNC = DATABASE_URL_SYNC.replace(
    "postgresql://",
    "postgresql+asyncpg://",
    1
)
# ---------------------------------------------------

# async Database instance (used in FastAPI endpoints)
database = Database(DATABASE_URL_ASYNC)

metadata = MetaData()

# ------------------- Table definitions -------------------
orders = Table(
    "orders",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("telegram_id", BigInteger),                 # кто отправил заявку
    Column("message", String, index=True),
    Column("original_amt", BigInteger),                # исходная сумма
    Column("final_amt", BigInteger),                   # сумма с маржой
    Column("reward_cust", BigInteger),                 # вознаграждение агенту‑заказчику
    Column("reward_exec", BigInteger),                 # вознаграждение агенту‑исполнителю
    Column("fee_platform", BigInteger),               # комиссия площадки
    Column("cust_requisites", String, nullable=True),   # реквизиты контрагента‑заказчика
    Column("cust_company_name", String, nullable=True),  # наименование контрагента‑заказчика
    Column("cust_director",     String, nullable=True),  # ФИО директора контрагента‑заказчика
    Column("carrier_requisites", String, nullable=True),   # реквизиты контрагента‑перевозчика
    Column("cars",            String, nullable=True),   # JSON‑строка со списком авто
    Column("loads",           String, nullable=True),   # JSON‑строка: точки погрузки
    Column("unloads",         String, nullable=True),   # JSON‑строка: точки выгрузки
    Column("pay_terms",       String, nullable=True),   # форма и срок оплаты
    Column("insurance_policy", String, nullable=True),   # номер страхового полиса
    Column("executor_id", BigInteger),                 # кто закрыл заявку
    Column("driver_fio", String, nullable=True),       # ФИО водителя (видно исполнителю)
    Column("driver_passport", String, nullable=True),   # паспорт водителя
    Column("truck_reg",       String, nullable=True),   # гос‑номер тягача
    Column("trailer_reg",     String, nullable=True),   # гос‑номер прицепа
    Column("driver_license",  String, nullable=True),   # номер ВУ водителя
    Column("truck_model",     String, nullable=True),   # марка тягача
    Column("trailer_model",   String, nullable=True),   # марка прицепа
    # --- подписи договора ---
    Column("signed_exec_path", String, nullable=True),   # файл, подписанный исполнителем (драйвером)
    Column("signed_cust_path", String, nullable=True),   # файл, подписанный заказчиком (навигатором)
    Column("signed_uploaded_at", DateTime, nullable=True),  # обе подписи получены
    Column("is_signed_complete", Boolean, server_default="false"),  # True, когда оба файла получены
    Column("vat", Boolean, server_default="true"),      # True = с НДС (ООО); False = без НДС (ИП)
    Column("status", String, default="confirmed"),     # confirmed | in_progress | done | paid
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
    Column(
        "updated_at",   
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    ),  # время изменения статуса / последнего изменения
)

agents = Table(
    "agents",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("telegram_id", BigInteger, unique=True),
    Column("name", String),
    Column("phone", String, nullable=True),          # телефон, если передан
    Column("agent_type", String),  # 'заказчик' или 'исполнитель'
    Column("registered_at", DateTime, default=datetime.datetime.utcnow),
)
# Companies table definition
companies = Table(
    "companies",
    metadata,
    Column("inn", String, primary_key=True),
    Column("data", JSONB, nullable=False)
)
# ----------------------------------------------------------

# Create tables in PostgreSQL (once at startup)
engine = create_engine(DATABASE_URL_SYNC, echo=False)
metadata.create_all(engine)