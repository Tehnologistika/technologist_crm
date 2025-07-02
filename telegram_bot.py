from modules.wizards.close import (
    CLOSE_FIO, CLOSE_PASSPORT, CLOSE_COMPANY_CONFIRM, CLOSE_COMPANY, CLOSE_DIRECTOR,
    CLOSE_TRUCK, CLOSE_TRAILER, CLOSE_INSURANCE, CLOSE_LICENSE,
    CLOSE_INN, CLOSE_KPP, BANK_NAME, BANK_RS, BANK_KS, BANK_BIC, CLOSE_PAY,
    CLOSE_ADDRESS,
    start_close_callback,
    close_get_fio, close_get_passport, close_get_company,
    close_confirm_company,
    close_get_director, close_get_truck, close_get_trailer,
    close_get_insurance, close_get_license, close_get_inn,
    close_get_kpp, close_get_bank_name, close_get_bank_rs,
    close_get_bank_ks, close_get_bank_bic, close_pay_choice, close_get_address
)

import random

GREETINGS = [
    "Привет, {name}! Отличного тебе дня 🚀",
    "Добро пожаловать, {name}! Всё получится!",
    "С возвращением, {name}! Ты на правильном пути.",
    "Рад тебя видеть, {name}! Готов к новым задачам?",
    "Здравствуйте, {name}! Пусть сегодняшний день принесёт только удачные сделки!",
]

ENCOURAGE = [
    "Отличная работа! Ваша заявка успешно опубликована 💪",
    "Молодец! Ещё один шаг к успеху 🚚",
    "Каждая заявка — это движение вперёд!",
    "Вы вдохновляете своей энергией. Так держать!",
    "Хороший результат — это всегда результат хороших решений.",
]

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from types import SimpleNamespace
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from pprint import pprint
import re
from telegram.constants import ChatAction
from typing import List, Dict
import requests
import aiohttp
import asyncio
import io
from modules.helpers import _http_get_json
from modules.helpers import _clean_optional, _norm_inn, fmt_money, BACK_PATTERN
from modules.wizards.publish import _clean_money
from sheets import update_request
from modules.wizards.publish import (
    # states
    PUB_CAR_COUNT, PUB_CAR_MODELS, PUB_VINS, PUB_L_ADDR, PUB_L_DATE, PUB_L_CONTACT, PUB_L_MORE,
    PUB_U_ADDR, PUB_U_DATE, PUB_U_CONTACT, PUB_U_MORE,
    PUB_BUDGET, PUB_PAY, PUB_PAY_TERMS, PUB_INN,
    PUB_COMPANY_NAME, PUB_COMPANY_KPP, PUB_COMPANY_ADDRESS, PUB_COMPANY_ACCOUNT, PUB_COMPANY_BANK, PUB_COMPANY_BIC,
    PUB_DIR, PUB_CONFIRM, PUB_COMPANY_CONFIRM,
    # handlers
    _init_order_lists, _ask_load_addr,
    pub_car_count,
    pub_cargo, pub_vins, pub_load_addr, pub_load_date,
    pub_load_contact, pub_load_more, pub_unload_addr, pub_unload_date,
    pub_unload_contact, pub_unload_more, pub_budget, pub_pay,
    pub_pay_terms,
    pub_inn, pub_company_name, pub_company_kpp, pub_company_address, pub_company_account, pub_company_bank, pub_company_bic,
    pub_dir, pub_confirm,
    back_from_route, back_from_budget, back_from_pay,
    back_from_contacts, back_from_date, back_to_publish_menu, pub_confirm_company,
    nav_cancel_order, pub_pay_choice
)


# --- Main menu publish label ---
TASKS_TEXT = "📦 Актуальные заявки"
# --- Admin panel labels ---
ADMIN_PANEL_LABEL    = "🛠 Админ‑панель"
ADMIN_CURRENT_LABEL  = "📦 Текущие"
ADMIN_ARCHIVE_LABEL  = "📚 Архив"
TOKEN_MENU_LABEL     = "🔑 Управление токенами"
TOKEN_CUST_LABEL     = "🧭 Token для Навигатора"
TOKEN_EXEC_LABEL     = "🚚 Token для Драйвера"
# --- Main menu publish label ---


PUBLISH_LABEL = "✏️ Опубликовать заявку"

# --- Bonus calculator ---
BONUS_CALC_LABEL  = "🧮 Калькулятор бонуса"
CUST_BONUS_RATE   = 0.05   # 5 % от стоимости перевозки
EXEC_BONUS_RATE   = 0.03   # 3 % от стоимости перевозки

# --- Registration wizard state constants ---
# Используются в ConversationHandler для начальной регистрации агента.
# Диапазон 400‑403 не пересекается с другими state‑id, объявленными ниже.
NAME, PHONE, ROLE, ASK_TOKEN = range(400, 404)

# --- Token conversation states ---
TOK_MENU, TOK_DONE = range(100, 102)

BACK_LABEL = "⬅️ Назад"

# --- Filter label and buttons ---
FILTER_LABEL = "🔎 Фильтр"
FILTER_OFF = "🔎 Фильтр ⚪️"
FILTER_ON  = "🔎 Фильтр 🟢"
RESET_LABEL = "🔄 Сброс"

# --- My Orders / History menu ---
MY_TASKS_LABEL = "📄 Мои заявки"
HISTORY_LABEL  = "📚 Архив"

STATUS_DOT = {
    "active":      "🟡",
    "confirmed":   "✅",
    "in_progress": "🔵",
    "done":        "🟢",
    "paid":        "💰",
}

# how many orders per page in cabinet view

CAB_PAGE_SIZE = 14
ARCH_PAGE_SIZE = 14

# --- Back keyboard helper for wizard steps ---
BACK_KB = ReplyKeyboardMarkup([[BACK_LABEL]], resize_keyboard=True)

# --- Admin settings ---
ADMINS = {6835069941, 7823236991}  # добавили второй TG‑ID админа


# --- Role display names ---
ROLE_LABEL = {
    "заказчик":    "Навигатор",
    "исполнитель": "Драйвер",
}
def _role_label(code: str) -> str:
    """Return human‑friendly role name."""
    return ROLE_LABEL.get(code, code)

# --- Per‑role welcome messages ---
WELCOME_ROLE_MSG = {
    "исполнитель": (
        "🚚 *Привет, Драйвер!* \n\n"
        "ТехноЛогистика рада видеть тебя в нашей команде. "
        "Твоя задача — брать подходящие заявки и качественно выполнять перевозки. "
        "За каждую успешно завершённую поездку ты получаешь 💰 *+3 %* к стоимости рейса.\n\n"
        "Поехали! 🏁"
    ),
    "заказчик": (
        "🧭 *Привет, Навигатор!* \n\n"
        "ТехноЛогистика рада видеть тебя в нашей команде. "
        "Твоя задача — публиковать заявки на перевозку и находить надёжных исполнителей. "
        "За каждую успешно закрытую сделку ты получаешь 💰 *+5 %* от стоимости перевозки.\n\n"
        "Вместе покорим логистику! 🚀"
    ),
}

# --- Menu/cabinet constants ---
MENU_CMD = "menu"                # команда
MENU_LABEL = "🏠 Мой кабинет"     # текст кнопки

# ID приватного канала‑хранилища, куда бот будет пересылать документы
STORAGE_CHANNEL_ID = -1002616739735   # ← замените на real id, формата -100...

# -------- CONFIG ----------
TOKEN = "7626649459:AAFYfJrC31GzZgEKNQUbhf11wbP8dN5mhgU"

# --- Allowed MIME types for signed contracts (.docx / .pdf / .rtf) ---
ALLOWED_MIME = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",                 # .doc
    "application/pdf",
    "application/rtf",                    # .rtf
    "text/rtf",
}

# --- global application holder for cross‑module notifications ---
APP = None

# --- Notification helper for cross-module use ---
async def send_notification_to_executor(tg_id: int, text: str, file_path: str | None = None):
    """
    Sends a message (and optionally a document) to the given Telegram user.

    • If file_path is provided → first send the document with caption,
      then отправляем дополнительную инструкцию о подписании (для договоров).
    • Else — обычное текстовое уведомление.
    """
    if APP is None:
        print("Notify error: bot instance not ready")
        return

    try:
        if file_path:
            # 1) send the document itself
            with open(file_path, "rb") as f:
                await APP.bot.send_document(
                    chat_id=tg_id,
                    document=f,
                    caption=text if text else "📑 Документ"
                )
            # 2) follow‑up instruction for contracts
            follow_up = (
                "✍️ Договор сформирован.\n"
                "Пожалуйста, подпишите документ и загрузите его обратно в систему для оформления сделки."
            )
            await APP.bot.send_message(chat_id=tg_id, text=follow_up)
        else:
            # simple text notification
            await APP.bot.send_message(chat_id=tg_id, text=text or "🔔 Уведомление")
    except Exception as e:
        print("Notify error:", e)


# --- Handler for receiving signed contract documents (.docx/.pdf) ---
async def receive_signed_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receives a signed contract (.docx or .pdf) from Navigator/Driver,
    forwards it to the backend `/orders/{id}/signed_document`,
    and informs the user about the result.
    """
    if not update.message or not update.message.document:
        return

    doc = update.message.document
    if doc.mime_type not in ALLOWED_MIME:
        await update.message.reply_text(
            "❗️ Пришлите подписанный договор в формате .docx, .pdf или .rtf."
        )
        return

    # Order ID was saved in user_data right after генерации договора
    order_id = context.user_data.get("closing_order_id")
    if not order_id:
        await update.message.reply_text(
            "⚠️ Не удалось понять, к какой заявке относится этот файл. "
            "Загрузите документ из карточки заявки."
        )
        return

    role = context.user_data.get("role", "исполнитель")

    # Download document into memory
    tg_file = await doc.get_file()
    buf = io.BytesIO()
    await tg_file.download(out=buf)
    buf.seek(0)

    try:
        resp = requests.post(
            f"{SERVER_URL}/orders/{order_id}/signed_document",
            params={"role": role, "filename": doc.file_name},
            files={"file": (doc.file_name, buf, doc.mime_type)},
            timeout=15
        )
    except requests.exceptions.RequestException as exc:
        print("signed_document request error:", exc)
        await update.message.reply_text(
            "❌ Не удалось связаться с сервером. Попробуйте позже."
        )
        return

    if resp.status_code != 200:
        await update.message.reply_text(
            f"❌ Сервер вернул ошибку: {resp.status_code}"
        )
        return

    resp_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp_data.get("status") == "in_progress":
        await update.message.reply_text(
            "🎉 Оба подписанных экземпляра получены. Заявка перешла в статус «В работе»!"
        )
    else:
        await update.message.reply_text(
            "✅ Ваш подписанный договор сохранён. Ждём вторую сторону."
        )

async def upload_contract_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split("_")[2])
    context.user_data["closing_order_id"] = order_id

    await query.message.reply_text(
        "📑 Пожалуйста, загрузите подписанный договор (PDF, DOCX или RTF)."
    )



# -------- CONFIG ----------
import os
SERVER_URL = "http://147.45.232.245:8000"  # default actual backend


# --------- Welcome image ----------
WELCOME_FILE_ID = "AgACAgIAAxkBAAIafmghqtnEsHE_Hb3kwynDDIndkjxxAAJy8DEbRyQQSXr4VtiHUh1HAQADAgADeQADNgQ"   # ← замените на полученный file_id
WELCOME_TEXT = (
    "🤖 *Автоматизированная CRM‑платформа компании «ТехноЛогистика»*\n"
    "Для эффективной совместной работы Навигаторов и Драйверов."
)

# --------- Publish banner ----------
PUBLISH_BANNER_FILE_ID = "AgACAgIAAxkBAAIahWghrEJNmnChOIoumbOu6G4ltTxnAAJw8DEbRyQQSRj5AhmIHc24AQADAgADeAADNgQ"   # ← put real file_id here
PUBLISH_BANNER_TEXT = (
    "✏️ *Опубликовать заявку*\n"
    "Заполните анкету, и мы отправим её исполнителям."
)

# --------- Cabinet banner ----------
CABINET_BANNER_FILE_ID = "AgACAgIAAxkBAAIaimghrLdLGOgS0GEBQfr0u-ojyr9NAAIq9jEbSMkISZjAvK9eYjJeAQADAgADeQADNgQ"   # ← replace with real file_id
CABINET_BANNER_TEXT = "🏠 *Мой кабинет*"

# --------- Bonus calculator banner ----------
BONUS_BANNER_FILE_ID = "AgACAgIAAxkBAAJFhWgze6OaDrUFR067uHA8ZZT8lmAxAAK78TEbaVSYSfBsRDypLVo0AQADAgADeAADNgQ"  # ← замените на свой file_id!
BONUS_BANNER_TEXT = (
    "🏆 *Калькулятор бонуса*\n"
    "Рассчитайте свой бонус за перевозку автомобиля прямо здесь."
)
 

# -------- Main menu keyboard helper ----------
async def send_main_menu(bot, chat_id: int, role: str | None = None):
    """Отправляет постоянную клавиатуру Меню + Актуальные заявки."""
    rows: list[list[str]] = [[MENU_LABEL]]

    # --- Общие кнопки, которые нужны всем ---
    # rows.append([HISTORY_LABEL])  # "Архив" не отображается в главном меню
    rows.append([BONUS_CALC_LABEL])
    rows.append(["💰 Мой кошелёк"])

    # --- Ролевые кнопки ---
    if role in ("заказчик", "admin"):
        # Навигатор и Админ: могут публиковать заявки
        rows.insert(1, [PUBLISH_LABEL])          # «Опубликовать» после меню
    else:
        # Исполнитель: актуальные заявки
        rows.insert(1, [TASKS_TEXT])             # «Актуальные заявки» после меню

    # админ-панель вставляется ниже, ничего менять не нужно
    if chat_id in ADMINS:
        rows.insert(0, [ADMIN_PANEL_LABEL])        # админ-кнопка первой строкой

    kb = ReplyKeyboardMarkup(rows, resize_keyboard=True)
    last = await bot.send_message(
        chat_id=chat_id,
        text="📲 Меню доступно через кнопки ниже.",
        reply_markup=kb
    )
    return last

# ----------- Back to main menu -----------
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к главному меню и выйти из текущего мастера/состояния."""
    # Remove last bot message, if any
    last = context.user_data.pop("last_bot_msg", None)
    if last:
        try:
            await last.delete()
        except:
            pass
    # Remove last bot message banner, if any
    banner = context.user_data.pop("last_bot_msg_banner", None)
    if banner:
        try:
            await banner.delete()
        except:
            pass
    # Delete triggering user message (e.g., "⬅️ Назад") if present
    if update.message:
        try:
            await update.message.delete()
        except:
            pass
    # Удаляем предыдущее (inline-)сообщение с кнопками или подсказкой
    if update.callback_query:
        try:
            await update.callback_query.message.delete()
        except:
            pass

    tg_id = update.effective_user.id
    try:
        role = requests.get(f"{SERVER_URL}/agent/{tg_id}", timeout=4).json().get("agent_type")
    except Exception:
        role = context.user_data.get("role")
    last = await send_main_menu(context.bot, tg_id, role)
    context.user_data["last_bot_msg"] = last
    return ConversationHandler.END

# ----------- Cancel helper -----------
async def cancel_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отменить текущий мастер и вернуться в главное меню.
    Срабатывает на «Назад» или /cancel из любого шага close/publish.
    """
    # Remove last bot message, if any
    last = context.user_data.pop("last_bot_msg", None)
    if last:
        try:
            await last.delete()
        except:
            pass
    last = await update.message.reply_text("🚫 Операция отменена.")
    context.user_data["last_bot_msg"] = last
    return await back_to_main(update, context)
# ----------- Показать подменю публикации -----------
async def show_publish_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает выбор режима публикации."""
    # Remove last bot message, if any
    last = context.user_data.pop("last_bot_msg", None)
    if last:
        try:
            await last.delete()
        except:
            pass
    # Also remove wallet banner if present
    banner = context.user_data.pop("last_bot_msg_banner", None)
    if banner:
        try:
            await banner.delete()
        except:
            pass
    # Если это текстовое сообщение-триггер («✏️ Опубликовать заявку»), удаляем его
    if update.message and update.message.text:
        try:
            await update.message.delete()
        except:
            pass

    tg_id = update.effective_user.id
    try:
        prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
        role = prof.get("agent_type")
        if role not in ("заказчик", "admin"):
            last = await update.message.reply_text("📌 Публиковать заявки может только Навигатор или Администратор.")
            context.user_data["last_bot_msg"] = last
            return
    except Exception:
        last = await update.message.reply_text("📌 Публиковать заявки может только Навигатор или Администратор.")
        context.user_data["last_bot_msg"] = last
        return

    # --- publish banner ---
    try:
        last = await context.bot.send_photo(
            chat_id=tg_id,
            photo=PUBLISH_BANNER_FILE_ID,
            caption=PUBLISH_BANNER_TEXT,
            parse_mode="Markdown"
        )
        context.user_data["last_bot_msg"] = last
    except Exception as e:
        # banner is optional; log and continue
        print("Publish banner error:", e)

    kb = ReplyKeyboardMarkup(
        [["✨ Заполнить анкету"],
         [BACK_LABEL]],
        resize_keyboard=True
    )
    last = await update.message.reply_text(
        "Нажмите «✨ Заполнить анкету», чтобы создать заявку:",
        reply_markup=kb
    )
    context.user_data["last_bot_msg"] = last
# ----------- Пояснения к режимам публикации -----------
async def publish_text_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пояснение к быстрому способу публикации."""
    await update.message.reply_text(
        "✏️ *Быстрый способ*\n"
        "Отправьте одним сообщением: название и характеристики груза, затем маршрут и сумму.\n"
        "_Пример_: `3 паллеты плитки, 2.4 т, Москва — Казань, 120 000 руб`",
        parse_mode="Markdown"
    )

async def publish_form_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт мастера публикации (шаг 1). Спрашиваем количество авто."""
    # Remove last bot message, if any
    last = context.user_data.pop("last_bot_msg", None)
    if last:
        try:
            await last.delete()
        except:
            pass
    # Remove triggering user message ("✨ Заполнить анкету") if present
    if update.message and update.message.text:
        try:
            await update.message.delete()
        except:
            pass
    # инициализируем контейнер для новой заявки
    context.user_data["new_order"] = {}

    last = await update.message.reply_text(
        "📝 *Шаг 1 / 11*\n"
        "Сколько автомобилей вы планируете перевезти? (числом):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    context.user_data["last_bot_msg"] = last
    return PUB_CAR_COUNT

# --- Filter conversation states ---
FILT_ORIGIN, FILT_DEST, FILT_CARGO, FILT_REWARD = range(13, 17)
BONUS_INPUT = 34    # одно новое состояние, номер вне других диапазонов
# ----------- Bonus Calculator -----------
async def bonus_calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Remove triggering user message ("🧮 Калькулятор бонуса") if present
    if update.message and update.message.text:
        try:
            await update.message.delete()
        except:
            pass
    """Запрос стоимости перевозки."""
    tg_id = update.effective_user.id
    # --- bonus banner ---
    try:
        last_banner = await context.bot.send_photo(
            chat_id=tg_id,
            photo=BONUS_BANNER_FILE_ID,
            caption=BONUS_BANNER_TEXT,
            parse_mode="Markdown"
        )
        context.user_data["last_bot_msg_banner"] = last_banner
    except Exception as e:
        print("Bonus banner error:", e)
    # определяем роль
    try:
        prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
        role = prof.get("agent_type")
    except Exception:
        role = context.user_data.get("role")
    context.user_data["calc_role"] = role or "исполнитель"
    last = await update.message.reply_text(
        "💡 Данный расчёт производится *без учёта налогов*.\n"
        "🔔 Если оплата производится *с НДС*, ваш бонус будет составлять результат расчёта минус *20 %* ― тем самым вы сохраняете прозрачность и стимулируете сотрудничество! 🚀\n\n"
        "📊 Введите предполагаемую стоимость перевозки, ₽ (числом):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    context.user_data["last_bot_msg"] = last
    return BONUS_INPUT

async def bonus_calc_compute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитывает бонус и выводит результат."""
    raw = update.message.text.strip().replace(" ", "").replace(" ", "")
    try:
        cost = int(float(raw))
    except ValueError:
        await update.message.reply_text("❗️ Введите число, например 120000")
        return BONUS_INPUT
    role = context.user_data.get("calc_role", "исполнитель")
    if role == "исполнитель":
        # Драйвер получает ровно 3 % от введённой суммы
        bonus = int(round(cost * EXEC_BONUS_RATE))
    else:
        # Навигатор получает 5 % от введённой суммы
        bonus = int(round(cost * CUST_BONUS_RATE))
    await update.message.reply_text(
        f"🏆 Ваш бонус составит: *{fmt_money(bonus)} ₽*",
        parse_mode="Markdown"
    )
    # показать меню обратно
    await send_main_menu(context.bot, update.effective_user.id, role)
    return ConversationHandler.END
# ----------- Filter wizard functions -----------
async def filter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запускает мастер фильтра. Вызывается по inline‑кнопке,
    поэтому используем callback_query, а не update.message.
    """
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "🔎 Фильтр\nГород отправления? (или «любой»)",
        reply_markup=BACK_KB
    )
    context.user_data["flt"] = {}
    return FILT_ORIGIN

async def filt_origin(update, context):
    raw = update.message.text.strip()
    txt_lc = raw.lower()
    if txt_lc == "-" or txt_lc.startswith("любо"):
        # skip: no origin filter
        pass
    else:
        context.user_data.setdefault("flt", {})["origin"] = raw
    await update.message.reply_text(
        "Город назначения? (или «любой»)",
        reply_markup=BACK_KB
    )
    return FILT_DEST

async def filt_dest(update, context):
    raw = update.message.text.strip()
    txt_lc = raw.lower()
    if txt_lc == "-" or txt_lc.startswith("любо"):
        pass
    else:
        context.user_data.setdefault("flt", {})["dest"] = raw
    await update.message.reply_text(
        "Ключевое слово по грузу? (или «любой»)",
        reply_markup=BACK_KB
    )
    return FILT_CARGO

async def filt_cargo(update, context):
    raw = update.message.text.strip()
    txt_lc = raw.lower()
    if txt_lc == "-" or txt_lc.startswith("любо"):
        pass
    else:
        context.user_data.setdefault("flt", {})["cargo_kw"] = raw
    await update.message.reply_text(
        "Мин. бонус исполнителю? (0 — «любой»)",
        reply_markup=BACK_KB
    )
    return FILT_REWARD

async def filt_reward(update, context):
    try:
        r = int(update.message.text.strip())
    except ValueError:
        r = 0
    if r:
        context.user_data["flt"]["min_reward"] = r
    await update.message.reply_text("✅ Фильтр применён.")
    return ConversationHandler.END

# ---------- Back handlers for filter wizard ----------
async def filt_back_to_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 Фильтр\nГород отправления? (или «любой»)",
        reply_markup=BACK_KB
    )
    return FILT_ORIGIN

async def filt_back_to_dest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Город назначения? (или «любой»)",
        reply_markup=BACK_KB
    )
    return FILT_DEST

async def filt_back_to_cargo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ключевое слово по грузу? (или «любой»)",
        reply_markup=BACK_KB
    )
    return FILT_CARGO

async def filt_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Фильтр отменён.")
    return ConversationHandler.END

# -------- MULTI‑POINT wizard helpers --------
def _init_order_lists(ctx):
    ctx.user_data.setdefault("new_order", {}).setdefault("loads", [])
    ctx.user_data["new_order"].setdefault("unloads", [])

async def _ask_load_addr(update, ctx):
    _init_order_lists(ctx)
    await update.message.reply_text(
        f"📝 *Погрузка #{len(ctx.user_data['new_order']['loads'])+1}*\n"
        "Адрес погрузки (город, улица):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_L_ADDR


# ---------- Conversation handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    On /start:
    • Claim one‑time token if passed: /start <TOKEN>
    • If profile exists – show menu
    • Else auto‑register using claimed role
    """
    tg_id = update.effective_user.id
    # --- welcome banner ---
    try:
        await context.bot.send_photo(
            chat_id=tg_id,
            photo=WELCOME_FILE_ID,
            caption=WELCOME_TEXT,
            parse_mode="Markdown"
        )
    except Exception as e:
        # if the image fails (e.g., wrong file_id) we simply ignore
        print("Welcome image error:", e)
    token_arg = context.args[0] if context.args else None

    # ---------- 1. Claim token ----------
    if token_arg:
        resp = requests.post(
            f"{SERVER_URL}/invite/claim",
            json={"telegram_id": tg_id, "token": token_arg},
            timeout=4
        )
        if resp.status_code != 200:
            await update.message.reply_text(
                "🚫 Токен недействителен, просрочен или уже использован.\n"
                "Попросите менеджера выдать новый."
            )
            return ConversationHandler.END

        role_from_token = resp.json()["role"]
        context.user_data["role"] = role_from_token
        # --- Персонализированное приветствие при первой авторизации ---
        role_label = _role_label(role_from_token)
        role_intro = {
            "Навигатор": "Ваша задача — находить и публиковать заявки на перевозку автомобилей, помогать заказчикам и связывать их с лучшими Драйверами. За каждую успешно завершённую перевозку вы получаете свой бонус.",
            "Драйвер": "Ваша задача — просматривать актуальные заявки, откликаться и выполнять перевозки с максимальным качеством и скоростью. За успешно выполненные заказы вы получаете премиальные выплаты.",
            "admin": "Ваша задача — контролировать процесс, помогать пользователям и следить за качеством работы системы.",
        }
        mountain = "Эльбрус"
        msg = (
            f"🏔️ Добро пожаловать в компанию «ТехноЛогистика»!\n\n"
            "Это новая эпоха в сфере логистики. Мы запускаем уникальную CRM‑платформу, созданную для оптимизации, ускорения и упрощения вашей работы.\n"
            "Вы стоите у истоков перемен — и именно вам предстоит освоить новые вершины эффективности.\n\n"
            f"*Ваша роль*: {role_label}\n"
            f"{role_intro.get(role_label, '')}\n\n"
            f"С этого момента начинается ваше восхождение на вершину самой красивой и высокой горы — {mountain}! ⛰️"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    # ---------- 2. Fetch profile ----------
    try:
        r = requests.get(f"{SERVER_URL}/agent/{tg_id}", timeout=4)
        profile = r.json() if r.status_code == 200 else None
    except Exception:
        profile = None

    # ---------- 3. Auto‑register if no profile but role cached ----------
    if (not profile or "agent_type" not in profile) and context.user_data.get("role"):
        reg_payload = {
            "telegram_id": tg_id,
            "name": update.effective_user.full_name,
            "agent_type": context.user_data["role"],
            "phone": ""
        }
        try:
            requests.post(f"{SERVER_URL}/register_agent", json=reg_payload, timeout=4)
            profile = reg_payload
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка регистрации: {e}")
            return ConversationHandler.END

    # ---------- 4. Deny if still no profile ----------
    if not profile or "agent_type" not in profile:
        # --- ask for token interactively ---
        context.user_data["await_token"] = True
        await update.message.reply_text(
            "🚫 У вас нет доступа.\n"
            "Отправьте персональный токен, выданный менеджером."
        )
        return ASK_TOKEN

    # ---------- 5. Show main menu ----------
    role = profile["agent_type"]
    context.user_data["role"] = role
    # --- Персонализированное приветствие при первой авторизации ---
    role_label = _role_label(role)
    role_intro = {
        "Навигатор": "Ваша задача — находить и публиковать заявки на перевозку автомобилей, помогать заказчикам и связывать их с лучшими Драйверами. За каждую успешно завершённую перевозку вы получаете свой бонус.",
        "Драйвер": "Ваша задача — просматривать актуальные заявки, откликаться и выполнять перевозки с максимальным качеством и скоростью. За успешно выполненные заказы вы получаете премиальные выплаты.",
        "admin": "Ваша задача — контролировать процесс, помогать пользователям и следить за качеством работы системы.",
    }
    mountain = "Эльбрус"
    msg = (
        f"🏔️ Добро пожаловать в компанию «ТехноЛогистика»!\n\n"
        "Это новая эпоха в сфере логистики. Мы запускаем уникальную CRM‑платформу, созданную для оптимизации, ускорения и упрощения вашей работы.\n"
        "Вы стоите у истоков перемен — и именно вам предстоит освоить новые вершины эффективности.\n\n"
        f"*Ваша роль*: {role_label}\n"
        f"{role_intro.get(role_label, '')}\n\n"
        f"С этого момента начинается ваше восхождение на вершину самой красивой и высокой горы — {mountain}! ⛰️"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    # Удалить или закомментировать старое приветствие, связанное с ролью
    # await update.message.reply_text(
    #     WELCOME_ROLE_MSG.get(role,
    #                          f"🎉 Добро пожаловать! Ваша роль: *{_role_label(role)}*"),
    #     parse_mode="Markdown"
    # )
    await send_main_menu(context.bot, tg_id, role)
    return ConversationHandler.END


# --- token input handler for interactive token request (/start without args) ---
async def token_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles plain-text token when user was asked to provide it after /start.
    """
    if not context.user_data.get("await_token"):
        return ConversationHandler.END  # not our flow

    token_arg = update.message.text.strip()
    tg_id = update.effective_user.id

    # try claim
    resp = requests.post(
        f"{SERVER_URL}/invite/claim",
        json={"telegram_id": tg_id, "token": token_arg},
        timeout=4
    )
    if resp.status_code != 200:
        await update.message.reply_text(
            "🚫 Токен недействителен, просрочен или уже использован.\n"
            "Попросите менеджера выдать новый."
        )
        return ASK_TOKEN

    role_from_token = resp.json()["role"]
    context.user_data["role"] = role_from_token
    context.user_data.pop("await_token", None)

    # try autologin again
    await update.message.reply_text(
        WELCOME_ROLE_MSG.get(role_from_token,
                             f"🎉 Добро пожаловать! Ваша роль: *{_role_label(role_from_token)}*"),
        parse_mode="Markdown"
    )
    # mimic /start without args to finish registration/login
    return await start(update, context)


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: ask phone contact."""
    context.user_data["full_name"] = update.message.text.strip()

    kb_phone = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        "2️⃣ Нажмите кнопку ниже, чтобы отправить номер телефона.",
        reply_markup=kb_phone
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3: choose role."""
    if update.message.contact is None:
        await update.message.reply_text("Используйте кнопку «Поделиться номером».")
        return PHONE

    context.user_data["phone"] = update.message.contact.phone_number

    # убираем клавиатуру «Поделиться номером»
    await update.message.reply_text(
        "☎️ Спасибо, номер получен.",
        reply_markup=ReplyKeyboardRemove()
    )

    kb_role = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Навигатор", callback_data="role_заказчик"),
          InlineKeyboardButton("Драйвер",   callback_data="role_исполнитель")]]
    )
    await update.message.reply_text(
        "3️⃣ Выберите вашу роль:",
        reply_markup=kb_role
    )
    return ROLE

# ---------- choose role ----------
# ---------- choose role ----------
async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish registration, save to backend."""
    query = update.callback_query
    await query.answer()

    # --- данные из callback / user_data ---
    role = query.data.split("_")[1]
    name = context.user_data.get("full_name", "Агент")
    telegram_id = query.from_user.id
    phone = context.user_data.get("phone", "")

    # --- пытаемся зарегистрировать или обновить профиль ---
    r = requests.post(
        f"{SERVER_URL}/register_agent",
        json={
            "telegram_id": telegram_id,
            "name": name,
            "agent_type": role,
            "phone": phone
        },
        timeout=4
    )

    # --- обработка случая «уже зарегистрирован» через 400 ---
    if r.status_code == 400 and r.json().get("detail") == "Агент уже зарегистрирован":
        # cчитаем это нормальной ситуацией — просто покажем меню
        await query.edit_message_text("✅ Профиль уже существует, меню показано.",
                                      parse_mode="Markdown")
        await send_main_menu(context.bot, telegram_id, role)
        return ConversationHandler.END

    # --- анализ ответа ---
    if r.status_code == 200:
        result = r.json().get("status", "ok")
        if result == "ok":
            header = "✅ Профиль создан!"
        elif result == "exists":
            header = "✅ Профиль обновлён!"
        else:   # неизвестный, но успешный ответ
            header = "✅ Готово!"

        # финальный текст с подсказкой
        body = WELCOME_ROLE_MSG.get(role,
            "Готово! Пользуйтесь главным меню ниже.")
        await query.edit_message_text(f"{header}\n\n{body}",
                                      parse_mode="Markdown")
        await send_main_menu(context.bot, telegram_id, role)
        return ConversationHandler.END
    elif r.status_code == 400 and r.json().get("detail") == "Агент уже зарегистрирован":
        # профиль существовал: просто покажем меню
        await send_main_menu(context.bot, telegram_id, role)
        await query.edit_message_text("✅ Профиль уже был создан, меню показано.",
                                      parse_mode="Markdown")
        return ConversationHandler.END
    else:
        # --- подробный вывод ошибки ---
        try:
            err_data = r.json()
            err_detail = err_data.get("detail", "")
        except ValueError:
            err_detail = ""
        err_msg = err_detail or r.text
        print("Registration error:", r.status_code, err_msg)
        await query.edit_message_text(f"❌ Ошибка регистрации: {err_msg}",
                                      parse_mode="Markdown")
        return ConversationHandler.END
# -------------------------------------------

def _short_route(message: str, limit: int = 25) -> str:
    route = message.split(",")[0].strip()
    return (route[:limit] + "…") if len(route) > limit else route

# --- Cabinet orders keyboard helper ---
def _cab_keyboard(rows: list[dict], page: int = 0) -> InlineKeyboardMarkup:
    """
    Builds inline keyboard for 'Мой кабинет'
    • 2 buttons per row
    • CAB_PAGE_SIZE items per page (must be even)
    """
    start = page * CAB_PAGE_SIZE
    subset = rows[start:start + CAB_PAGE_SIZE]

    buttons: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(subset), 2):
        pair = subset[i:i+2]
        row: list[InlineKeyboardButton] = []
        for o in pair:
            # Используем краткий маршрут из поля message вместо номера
            message_text = o.get("message", "") or ""
            summary = message_text[:25] + ("…" if len(message_text) > 25 else "")
            caption = f"{STATUS_DOT.get(o.get('status'),'•')} {summary}"
            row.append(
                InlineKeyboardButton(
                    caption,
                    callback_data=f"task_{o['id']}"
                )
            )
        buttons.append(row)

    # navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"cab_{page-1}"))
    if start + CAB_PAGE_SIZE < len(rows):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"cab_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(buttons)

# --------- ARCHIVE keyboard helper ----------
def _arch_keyboard(rows: list[dict], page: int = 0) -> InlineKeyboardMarkup:
    """
    Inline keyboard for archive list, two buttons per row.
    """
    start = page * ARCH_PAGE_SIZE
    subset = rows[start:start + ARCH_PAGE_SIZE]

    buttons: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(subset), 2):
        pair = subset[i:i+2]
        row: list[InlineKeyboardButton] = []
        for o in pair:
            caption = f"{STATUS_DOT.get(o.get('status'), '•')} #{o['id']}"
            row.append(
                InlineKeyboardButton(
                    caption,
                    callback_data=f"arch_{o['id']}"
                )
            )
        buttons.append(row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"cab_arch_{page-1}"))
    if start + ARCH_PAGE_SIZE < len(rows):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"cab_arch_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(buttons)

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список *актуальных* заявок.
    ...
    """
    # Если пользователь нажал текстовую кнопку TASKS_TEXT, удаляем его сообщение-кнопку
    if update.message and update.message.text == TASKS_TEXT:
        try:
            await update.message.delete()
        except:
            pass

    # Remove last bot message, if any
    last = context.user_data.pop("last_bot_msg", None)
    if last:
        try:
            await last.delete()
        except:
            pass
    # Also remove wallet banner if present
    banner = context.user_data.pop("last_bot_msg_banner", None)
    if banner:
        try:
            await banner.delete()
        except:
            pass

    print(f"[DEBUG show_tasks] called with message.text={update.message.text!r}")
    if update.message.text != TASKS_TEXT:
        return

    tg_id = update.effective_user.id
    # … остальной код …
    is_admin = tg_id in ADMINS
    # determine role
    try:
        prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
        role = prof.get("agent_type")
    except Exception:
        role = None

    print(f"[DEBUG show_tasks] tg_id={tg_id}, is_admin={is_admin}, role={role}")

    # fetch orders based on admin status or role
    if is_admin and role == "admin":
        # Admin: fetch open and confirmed orders via paginated admin endpoint
        url = f"{SERVER_URL}/admin/orders?limit=15"
        print(f"[DEBUG show_tasks] fetching URL: {url}")
        all_orders = await _http_get_json(url)
        # filter out paid orders only
        rows = [
            o for o in all_orders
            if not (("paid" in str(o.get("status","")).lower()) or ("оплач" in str(o.get("status","")).lower()))
        ]
        print(f"[DEBUG show_tasks] fetched rows count: {len(rows)}; rows: {rows}")
    elif role == "заказчик":
        url = f"{SERVER_URL}/orders/by_customer_open/{tg_id}"
        print(f"[DEBUG show_tasks] fetching URL: {url}")
        rows = await _http_get_json(url)
        print(f"[DEBUG show_tasks] fetched rows count: {len(rows)}; rows: {rows}")
    elif role == "исполнитель":
        url = f"{SERVER_URL}/open_orders?limit=15"
        print(f"[DEBUG show_tasks] fetching URL: {url}")
        rows = await _http_get_json(url)
        # Оставляем только заявки со статусом "active"
        rows = [
            o for o in rows
            if (o.get("status") or "").lower().strip() == "active"
        ]
        print(f"[DEBUG show_tasks] filtered driver rows count: {len(rows)}; rows: {rows}")
    else:
        url = f"{SERVER_URL}/open_orders?limit=15"
        print(f"[DEBUG show_tasks] fetching URL: {url}")
        rows = await _http_get_json(url)
        print(f"[DEBUG show_tasks] fetched rows count: {len(rows)}; rows: {rows}")

    if not rows:
        last = await update.message.reply_text("✅ Нет текущих заявок.")
        # Re-display the main ReplyKeyboard at the bottom
        menu = await send_main_menu(context.bot, tg_id, role)
        context.user_data["last_bot_msg"] = menu
        return

    buttons = []
    for o in rows:
        # Use the order message as route summary
        message_text = o.get("message", "") or ""
        # Truncate to 25 characters if necessary
        summary = message_text[:25] + ("…" if len(message_text) > 25 else "")
        caption = f"{STATUS_DOT.get(o.get('status'),'•')} {summary}"
        buttons.append([
            InlineKeyboardButton(
                caption,
                callback_data=f"{'admin_order' if is_admin and role == 'admin' else 'task'}_{o.get('id')}"
            )
        ])
    back_cb = "admin_back_main" if is_admin else "back_to_cabinet"
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=back_cb)])
    last = await update.message.reply_text("Текущие заявки:", reply_markup=InlineKeyboardMarkup(buttons))
    # Re-display the main ReplyKeyboard at the bottom
    menu = await send_main_menu(context.bot, tg_id, role)
    context.user_data["last_bot_msg"] = menu

async def task_details_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # --- определяем роль пользователя ---
    tg_id = query.from_user.id
    try:
        prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
        role = prof.get("agent_type")
    except Exception:
        role = None

    order_id = int(query.data.split("_")[1])

    resp = requests.get(f"{SERVER_URL}/order/{order_id}")
    if resp.status_code != 200:
        await query.edit_message_text("❌ Заявка не найдена или уже закрыта.")
        return
    detail = resp.json()

    # --- status label ---
    STATUS_LABELS = {
        "active":      "🆕 Активна",
        "confirmed":   "✅ Подтверждена",
        "in_progress": "🚚 В работе",
        "done":        "📦 Исполнена",
        "paid":        "💰 Оплачена",
        "new":         "🆕 В ожидании",
        "completed":   "📦 Исполнена",
        "archived":    "📂 Архив",
        "cancelled":   "❌ Отменена",
    }
    status = detail.get("status", "")
    status_line = f"📋 Статус: {STATUS_LABELS.get(status, status)}\n"
    header = f"[#{detail['id']}] {detail['message']}"
    sections = [status_line + header]

    # Пункты погрузки
    if detail.get("loads"):
        sections.append("📍 Пункты погрузки:")
        for i, l in enumerate(detail["loads"], start=1):
            sections.append(f"  {i}. {l.get('place','')} ({l.get('date','')})")
        sections.append("")

    # Пункты выгрузки
    if detail.get("unloads"):
        sections.append("📍 Пункты выгрузки:")
        for i, u in enumerate(detail["unloads"], start=1):
            sections.append(f"  {i}. {u.get('place','')} ({u.get('date','')})")
        sections.append("")

    # Список машин
    cars = detail.get("cars", [])
    if cars:
        car_strings = []
        for car in cars:
            b = car.get("brand", "").strip()
            m = car.get("model", "").strip()
            name = f"{b} {m}".strip()
            car_strings.append(f"1×{name}")
        sections.append(f"🚚 Груз: {'; '.join(car_strings)}")
    else:
        # Fallback: если нет массива cars, показать car_count и car_models
        car_count = detail.get("car_count")
        car_models = detail.get("car_models", "").strip()
        if car_count and car_models:
            sections.append(f"🚚 Груз: {car_count}×{car_models}")

    # Ставки и бонусы
    budget_text = detail.get("budget", "")
    if budget_text:
        # Ставка для заказчика
        sections.append(f"💵 Ставка (заказчик): {budget_text}")

        # Преобразуем текст, например "100 000 руб", в число 100000
        customer_amt = _clean_money(budget_text)
        # Цена для исполнителя: минус 12%
        exec_amt = int(customer_amt * 0.88)
        # Бонус навигатора: 3%
        nav_bonus = int(customer_amt * 0.03)

        # Выводим с разделением пробелами тысяч
        sections.append(f"💵 Ставка (исполнитель): {exec_amt:,} руб".replace(",", " "))
        sections.append(f"🏆 Бонус навигатора: +{nav_bonus:,} ₽".replace(",", " "))

    pay_terms_text = (detail.get("pay_terms") or "").strip()
    vat_flag = detail.get("vat", True)

    if pay_terms_text:
        sections.append(f"💳 Условия оплаты: {pay_terms_text}")
    else:
        # fallback: показываем, с НДС или без, если явных условий нет
        sections.append("💳 Оплата с НДС" if vat_flag else "💳 Оплата без НДС")

    # Бонусы
    bonus_exec = detail.get("reward_exec") or 0
    bonus_cust = detail.get("reward_cust") or 0
    if role == "исполнитель":
        sections.append(f"🏆 Ваш бонус: +{fmt_money(bonus_exec)} ₽")
        sections.append(f"🏆 Бонус заказчика: +{fmt_money(bonus_cust)} ₽")
    elif role == "заказчик":
        sections.append(f"🏆 Ваш бонус: +{fmt_money(bonus_cust)} ₽")
        sections.append(f"🏆 Бонус исполнителя: +{fmt_money(bonus_exec)} ₽")
    else:
        sections.append(f"🏆 Бонус заказчика: +{fmt_money(bonus_cust)} ₽")
        sections.append(f"🏆 Бонус исполнителя: +{fmt_money(bonus_exec)} ₽")

    text = "\n".join(sections)

    # кнопки по ролям:
    if role == "исполнитель" and status == "active":
        kb_buttons = [
            [InlineKeyboardButton("Закрыть", callback_data=f"close_{order_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_tasks")]
        ]
    elif role == "исполнитель" and status == "confirmed":
        kb_buttons = [
            [InlineKeyboardButton("📑 Загрузить договор", callback_data=f"upload_contract_{order_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_tasks")]
        ]
    elif role == "заказчик" and status == "confirmed":
        kb_buttons = [
            [InlineKeyboardButton("📑 Загрузить договор", callback_data=f"upload_contract_{order_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"nv_cancel_{order_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_cabinet")]
        ]
    elif role == "заказчик" and status not in ("cancelled", "paid"):
        kb_buttons = [
            [InlineKeyboardButton("❌ Отменить", callback_data=f"nv_cancel_{order_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_cabinet")]
        ]
    elif role == "admin":
        kb_buttons = [
            [InlineKeyboardButton("Сменить статус", callback_data=f"admin_change_{order_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_cabinet")]
        ]
    else:
        kb_buttons = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_cabinet")]
        ]

    kb = InlineKeyboardMarkup(kb_buttons)

    await query.edit_message_text(text, reply_markup=kb)


# ----------- Show cabinet/profile helper -----------
async def show_cabinet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображает профиль и список заявок пользователя."""
    # Remove previously sent bot message (last_bot_msg), if any
    last = context.user_data.pop("last_bot_msg", None)
    if last:
        try:
            await last.delete()
        except:
            pass
    # Also remove wallet banner if present
    banner = context.user_data.pop("last_bot_msg_banner", None)
    if banner:
        try:
            await banner.delete()
        except:
            pass
    # 1) Если это текстовое сообщение-триггер («Мой кабинет»), удаляем его
    if update.message and update.message.text:
        try:
            await update.message.delete()
        except:
            pass

    # 2) Если это callback (⬅️ Назад), удаляем его и уходим в главное меню
    if hasattr(update, "callback_query") and update.callback_query is not None:
        try:
            await update.callback_query.message.delete()
        except:
            pass
        await back_to_main(update, context)
        return

    tg_id = update.effective_user.id

    # --- cabinet banner ---
    try:
        last = await context.bot.send_photo(
            chat_id=tg_id,
            photo=CABINET_BANNER_FILE_ID,
            caption=CABINET_BANNER_TEXT,
            parse_mode="Markdown"
        )
        context.user_data["last_bot_msg"] = last
    except Exception as e:
        print("Cabinet banner error:", e)

    # --- профиль ---
    prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
    if not prof or not isinstance(prof, dict) or "agent_type" not in prof:
        last = await update.message.reply_text("❌ Профиль не найден. Зарегистрируйтесь сначала /start")
        context.user_data["last_bot_msg"] = last
        return

    name = prof.get("name", "").split()[0] or "друг"
    greeting = random.choice(GREETINGS).format(name=name)
    last = await context.bot.send_message(chat_id=tg_id, text=greeting)
    role = prof["agent_type"]

    text = (f"*Профиль*\n"
            f"*ФИО:* {prof['name']}\n"
            f"*Телефон:* {prof.get('phone','—')}\n"
            f"*Роль:* {_role_label(role)}\n\n")

    if role in ("заказчик", "customer", "admin"):
        # открытые и архивные заявки Навигатора: берём готовые эндпоинты
        url_open   = f"{SERVER_URL}/orders/by_customer_open/{tg_id}"
        url_closed = f"{SERVER_URL}/orders/by_customer_closed/{tg_id}"
        orders_open   = await _fetch_orders(url_open)
        orders_closed = await _fetch_orders(url_closed)

    else:  # исполнитель
        url_open   = f"{SERVER_URL}/orders/by_executor_open/{tg_id}"
        url_closed = f"{SERVER_URL}/orders/by_executor/{tg_id}"      # закрытые (done/paid)
        orders_open   = await _fetch_orders(url_open)
        orders_closed = await _fetch_orders(url_closed)

    # --- DEBUG: показать заявки исполнителя в orders_closed с ключевыми полями ---
    if role == "исполнитель":
        pass

    # send profile first, then orders list as buttons
    last = await context.bot.send_message(
        chat_id=tg_id,
        text=text,
        parse_mode="Markdown"
    )
    context.user_data["last_bot_msg"] = last


    # --- предварительно очищаем старые списки
    context.user_data.pop("cab_orders", None)
    context.user_data.pop("arch_rows",  None)
    # --- сохраняем списки для кнопок «Заявки в работе» и «Архив» ---
    if role in ("заказчик", "customer"):
        # заказчик: в работе = все открытые; архив = все закрытые
        if orders_open:
            context.user_data["cab_orders"] = orders_open
        if orders_closed:
            context.user_data["arch_rows"] = orders_closed
    else:
        # --- собираем списки для исполнителя ---
        work_rows = []
        arch_rows = []
        seen_ids  = set()

        # Сначала проходим закрытые заявки, чтобы статус “paid” имел приоритет.
        for o in orders_closed + orders_open:        # closed → open
            oid = o.get("id")
            if oid in seen_ids:
                continue
            seen_ids.add(oid)

            st = (o.get("status") or "").replace("\u00a0", " ").strip().lower()
            # Всё, что имеет корень «оплач» или содержит «paid»,
            # относится к уже оплаченным заявкам → архив.
            if ("paid" in st) or ("оплач" in st):
                arch_rows.append(o)
            else:
                work_rows.append(o)

        if work_rows:
            context.user_data["cab_orders"] = work_rows
        if arch_rows:
            context.user_data["arch_rows"] = arch_rows

    kb_main = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📄 Мои заявки", callback_data="cab_work")],
         [InlineKeyboardButton("📚 Архив",       callback_data="cab_arch_0")]]
    )

    last = await context.bot.send_message(
        chat_id=tg_id,
        text="Выберите раздел:",
        parse_mode="Markdown",
        reply_markup=kb_main
    )
    context.user_data["last_bot_msg"] = last
    # Re-display the main ReplyKeyboard at the bottom
    # Ensure role is available for send_main_menu
    if "role" in locals():
        pass
    else:
        role = prof.get("agent_type")
    menu = await send_main_menu(context.bot, tg_id, role)
    context.user_data["last_bot_msg"] = menu
    # Re-display the main ReplyKeyboard at the bottom
    last_menu = await send_main_menu(context.bot, tg_id, role)
    context.user_data["last_bot_msg"] = last_menu
async def cabinet_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles ◀️ / ▶️ navigation in cabinet orders list."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[1])
    rows = context.user_data.get("cab_orders") or []
    if not rows:
        # Показываем обычное сообщение вместо короткого alert,
        # чтобы пользователь видел текст в чате.
        await query.answer()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="✅ Нет заявок в работе."
        )
        return
    kb = _cab_keyboard(rows, page)
    await query.edit_message_reply_markup(reply_markup=kb)


# ----------- Archive pagination callback -----------
async def cabinet_arch_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pagination for archive inside cabinet."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[2])
    rows = context.user_data.get("arch_rows") or []
    if not rows:
        await query.answer()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="📂 Архив пуст."
        )
        return
    kb = _arch_keyboard(rows, page)
    await query.edit_message_reply_markup(reply_markup=kb)


# ----------- Show current orders from cabinet button -----------
async def cabinet_work_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Opens list of current (unpaid) orders from cabinet button."""
    query = update.callback_query
    await query.answer()
    rows = context.user_data.get("cab_orders") or []
    if not rows:
        # Показываем обычное сообщение вместо короткого alert,
        # чтобы пользователь видел текст в чате.
        await query.answer()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="✅ Нет заявок в работе."
        )
        return
    kb = _cab_keyboard(rows, page=0)
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Заявки в работе:",
        reply_markup=kb
    )


# ----------- archive details callback -----------
async def archive_details_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенную карточку закрытой заявки (архив)."""
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    try:
        prof = requests.get(f"{SERVER_URL}/agent/{tg_id}", timeout=4).json()
        role = prof.get("agent_type")
    except Exception:
        role = None
    order_id = int(query.data.split("_")[1])

    r = requests.get(f"{SERVER_URL}/order/{order_id}", timeout=4)
    if r.status_code != 200:
        await query.edit_message_text("❌ Не удалось получить данные заявки.")
        return
    o: Dict = r.json()
    msg         = o.get("message", "—")
    final_amt   = o.get("final_amt") or 0
    bonus_cust  = o.get("reward_cust") or 0
    bonus_exec  = o.get("reward_exec") or 0
    driver_fio  = o.get("driver_fio") or "—"

    text = (f"*#{o['id']}*  {msg}\n"
            f"💰 *Стоимость для перевозчика:* {fmt_money(final_amt)} ₽\n"
            f"🏆 *Бонус заказчика:* {fmt_money(bonus_cust)} ₽\n"
            f"🏆 *Бонус исполнителя:* {fmt_money(bonus_exec)} ₽")
    # Cargo and route
    text += f"\n📦 Груз/Маршрут: {o.get('message', '—')}\n"
    # Количество и марки автомобилей
    car_count = o.get("car_count")
    car_models = o.get("car_models", "").strip()
    if car_count:
        text += f"🚚 Груз: {car_count} × {car_models}\n"
    if role == "исполнитель":
        text += f"\n👤 *Водитель:* {driver_fio}"
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_cabinet")]]
        )
    )

async def filter_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear stored filter and refresh button caption."""
    query = update.callback_query
    await query.answer("Фильтр сброшен")
    context.user_data.pop("flt", None)
    await query.message.delete()

# ---------- async HTTP helper ----------
async def _http_get_json(url: str, *, data: dict | None = None, timeout: int = 6):
    """
    Asynchronously GET (or POST if data given) JSON from backend using aiohttp.
    Falls back to {} on error.
    """
    method = "POST" if data else "GET"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as sess:
            if method == "POST":
                async with sess.post(url, json=data) as resp:
                    return await resp.json(content_type=None)
            else:
                async with sess.get(url) as resp:
                    return await resp.json(content_type=None)
    except Exception as e:
        print("HTTP error", method, url, ":", e)
        return {}

async def _fetch_orders(url: str) -> list[dict]:
    data = await _http_get_json(url)
    if isinstance(data, dict):
        data = data.get("orders") or data.get("items") or data.get("data") or []
    return data if isinstance(data, list) else []

async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Remove wallet banner if present
    banner = context.user_data.pop("last_bot_msg_banner", None)
    if banner:
        try:
            await banner.delete()
        except:
            pass
    tg_id = update.effective_user.id
    # определяем роль
    try:
        prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
        role = prof.get("agent_type")
    except Exception:
        role = None

    if role in ("заказчик", "customer", "admin"):
        url = f"{SERVER_URL}/orders/by_customer_open/{tg_id}"
        rows = await _fetch_orders(url)
        # Показываем все, кроме оплаченных, отменённых, архивных
        rows = [o for o in rows if o.get("status") not in ("paid", "cancelled", "archived")]
    elif role == "исполнитель":
        # Берём ВСЕ заявки этого драйвера
        url = f"{SERVER_URL}/orders/by_executor_open/{tg_id}"
        rows = await _fetch_orders(url)
        # эндпоинт уже исключает active и paid, дополнительный фильтр не нужен
        # если хотите подстраховаться:
        rows = [o for o in rows if (o.get("status") or "").lower() != "paid"]
    else:
        url = f"{SERVER_URL}/orders/by_executor_open/{tg_id}"
        rows = await _fetch_orders(url)

    if not rows:
        await update.message.reply_text("✅ Нет заявок в работе.")
        return

        for o in rows[:30]:
            oid = o["id"]
            dot = STATUS_DOT.get(o.get("status", ""), "•")
            raw_msg = o.get("message", "") or ""
            # Берём только маршрут (часть после '|') без ставки
            parts = raw_msg.split("|", 1)
            route_and_budget = parts[1].strip() if len(parts) > 1 else raw_msg
            m = re.match(r"(.+?)\s+\d", route_and_budget)
            route = m.group(1) if m else route_and_budget
            summary = route.strip()[:25] + ("…" if len(route.strip()) > 25 else "")
            caption = f"{dot} {summary}"
            buttons.append([InlineKeyboardButton(caption, callback_data=f"task_{oid}")])
    await update.message.reply_text(
        "Ваши заявки:" if role == "заказчик" else "Мои заявки:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Remove wallet banner if present
    banner = context.user_data.pop("last_bot_msg_banner", None)
    if banner:
        try:
            await banner.delete()
        except:
            pass
    tg_id = update.effective_user.id
    is_admin = tg_id in ADMINS
    # determine role
    try:
        prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
        role = prof.get("agent_type")
    except Exception:
        role = None

    # fetch all orders for admin, else per user
    if is_admin:
        # Admin: fetch only paid orders via paginated admin endpoint
        url = f"{SERVER_URL}/admin/orders?status=paid&limit=15"
        rows = await _fetch_orders(url)
    elif role in ("заказчик", "customer", "admin"):
        # Берём только закрытые (архивные) заявки пользователя
        rows = await _fetch_orders(f"{SERVER_URL}/orders/by_customer_closed/{tg_id}")
    elif role == "исполнитель":
        # fetch closed (done/paid) orders for driver
        rows = await _fetch_orders(f"{SERVER_URL}/orders/by_executor/{tg_id}")
        rows = [
            o for o in rows
            if o.get("executor_id") == tg_id
            and (o.get("status") or "").lower() == "paid"
        ]
    else:
        rows = await _fetch_orders(f"{SERVER_URL}/open_orders?limit=15")

    if not rows:
        await update.message.reply_text("📂 Архив пуст.")
        return

    buttons = [
        [InlineKeyboardButton(
            f"{STATUS_DOT.get(o.get('status'),'•')} #{o.get('id')}",
            callback_data=f"{'arch' if is_admin else 'arch'}_{o.get('id')}"
        )]
        for o in rows[:30]
    ]
    # Add a back button to return to the admin panel
    if is_admin:
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_main")])
    await update.message.reply_text("📂 Архив заявок:", reply_markup=InlineKeyboardMarkup(buttons))

def main() -> None:
    async def wallet_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Remove last bot message, if any
        last = context.user_data.pop("last_bot_msg", None)
        if last:
            try:
                await last.delete()
            except:
                pass
        # Delete triggering user message ("💰 Мой кошелёк") if present
        if update.message:
            try:
                await update.message.delete()
            except:
                pass

        tg_id = update.effective_user.id
        try:
            prof = await _http_get_json(f"{SERVER_URL}/agent/{tg_id}")
            role = prof.get("agent_type")
        except Exception:
            role = None

        if role == "исполнитель":
            url = f"{SERVER_URL}/orders/by_executor/{tg_id}"
            reward_field = "reward_exec"
        else:
            url = f"{SERVER_URL}/orders/by_customer/{tg_id}"
            reward_field = "reward_cust"

        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            orders = resp.json()
        else:
            orders = []

        bonus_vat = 0
        bonus_no_vat = 0
        for o in orders:
            if o.get("vat"):
                bonus_vat += o.get(reward_field, 0) or 0
            else:
                bonus_no_vat += o.get(reward_field, 0) or 0

        total_no_vat = int(bonus_vat * 0.8 + bonus_no_vat)

        text = (
            f"💰 Бонусы с НДС: {bonus_vat:,} ₽\n"
            f"💰 Бонусы без НДС: {bonus_no_vat:,} ₽\n"
            f"💰 Общая сумма бонусов без НДС: {total_no_vat:,} ₽"
        )
        # Send wallet info and save as banner to delete later
        wallet_msg = await update.message.reply_text(text)
        context.user_data["last_bot_msg_banner"] = wallet_msg

        # Then re-show main menu keyboard below
        last = await send_main_menu(context.bot, tg_id, role)
        context.user_data["last_bot_msg"] = last
    # Handler to go back to Active Tasks list for drivers
    async def back_to_tasks_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        # Удаляем текущее сообщение-карточку заявки
        try:
            await query.message.delete()
        except:
            pass

        tg_id = query.from_user.id
        # Иммитируем отправку TASKS_TEXT, чтобы показать список заявок заново
        from types import SimpleNamespace
        fake_msg = SimpleNamespace(
            text=TASKS_TEXT,
            chat=SimpleNamespace(id=tg_id),
            reply_text=query.message.reply_text
        )
        fake_update = SimpleNamespace(message=fake_msg, effective_user=query.from_user)
        await show_tasks(fake_update, context)
    app = ApplicationBuilder().token(TOKEN).build()
    global APP
    APP = app

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            ROLE:  [CallbackQueryHandler(choose_role, pattern=r"^role_")],
            ASK_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_input)],
        },
        fallbacks=[],
        per_message=True,
    )

    tok_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_token_menu, pattern=r"^admin_token_menu$")],
        states={
            TOK_MENU: [
                CallbackQueryHandler(admin_token_generate_cb, pattern=r"^admin_token_(?:cust|exec)$")
            ],
            TOK_DONE: [
                CallbackQueryHandler(admin_token_menu, pattern=r"^admin_token_menu$")
            ],
        },
        fallbacks=[],
        per_message=True,
    )

    # handler for closing flow
    close_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_close_callback, pattern=r"^close_\d+$")],
        states={
            # 1) Transport-related questions first
            CLOSE_FIO: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_fio)
            ],
            CLOSE_PASSPORT: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_passport)
            ],
            CLOSE_LICENSE: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_license)
            ],
            CLOSE_TRUCK: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_truck)
            ],
            CLOSE_TRAILER: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_trailer)
            ],
            CLOSE_INSURANCE: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_insurance)
            ],

            # 2) Then company-related questions
            CLOSE_INN: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_inn)
            ],
            CLOSE_COMPANY_CONFIRM: [
                CallbackQueryHandler(close_confirm_company, pattern=r"^cmp_yes$"),
                CallbackQueryHandler(close_confirm_company, pattern=r"^cmp_no$"),
                MessageHandler(filters.Regex(r"^(?i:да|нет)$"), close_confirm_company)
            ],
            CLOSE_COMPANY: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_company)
            ],
            CLOSE_KPP: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_kpp)
            ],
            BANK_NAME: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_bank_name)
            ],
            BANK_RS: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_bank_rs)
            ],
            BANK_KS: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_bank_ks)
            ],
            BANK_BIC: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_bank_bic)
            ],
            CLOSE_PAY: [
                CallbackQueryHandler(close_pay_choice, pattern=r"^pay_(?:vat|novat)$")
            ],
            CLOSE_ADDRESS: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_address)
            ],
            CLOSE_DIRECTOR: [
                MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
                MessageHandler(filters.TEXT, close_get_director)
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex(BACK_PATTERN), cancel_wizard),
            CommandHandler("cancel", cancel_wizard)
        ],
        per_user=True,
        per_message=True,
    )

    pub_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✨ Заполнить анкету$"), publish_form_intro)],
        states={
            PUB_CAR_COUNT: [
                MessageHandler(filters.Regex(BACK_PATTERN), back_to_publish_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, pub_car_count)
            ],
            PUB_CAR_MODELS: [
                MessageHandler(filters.Regex(BACK_PATTERN), back_from_route),
                MessageHandler(filters.TEXT & ~filters.COMMAND, pub_cargo)
            ],
            PUB_VINS: [
                MessageHandler(filters.Regex(BACK_PATTERN), back_from_route),
                MessageHandler(filters.TEXT & ~filters.COMMAND, pub_vins)
            ],
            PUB_L_ADDR:   [MessageHandler(filters.Regex(BACK_PATTERN), back_from_route),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, pub_load_addr)],
            PUB_L_DATE:   [MessageHandler(filters.Regex(BACK_PATTERN), back_from_route),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, pub_load_date)],
            PUB_L_CONTACT:[MessageHandler(filters.Regex(BACK_PATTERN), back_from_route),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, pub_load_contact)],
            PUB_L_MORE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_load_more)],

            PUB_U_ADDR:   [MessageHandler(filters.Regex(BACK_PATTERN), back_from_contacts),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, pub_unload_addr)],
            PUB_U_DATE:   [MessageHandler(filters.Regex(BACK_PATTERN), back_from_contacts),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, pub_unload_date)],
            PUB_U_CONTACT:[MessageHandler(filters.Regex(BACK_PATTERN), back_from_contacts),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, pub_unload_contact)],
            PUB_U_MORE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_unload_more)],
            PUB_BUDGET:[MessageHandler(filters.Regex(BACK_PATTERN), back_from_contacts),
                         MessageHandler(filters.TEXT & ~filters.COMMAND, pub_budget)],
            PUB_PAY:    [
                CallbackQueryHandler(pub_pay_choice, pattern=r"^pay_(?:vat|novat)$"),
                MessageHandler(filters.Regex(BACK_PATTERN), back_from_budget),
                MessageHandler(filters.TEXT & ~filters.COMMAND, pub_pay)
            ],
            PUB_PAY_TERMS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_pay_terms)],
            PUB_INN:   [MessageHandler(filters.Regex(BACK_PATTERN), back_from_pay),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, pub_inn)],
            PUB_COMPANY_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_company_name)],
            PUB_COMPANY_KPP:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_company_kpp)],
            PUB_COMPANY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_company_address)],
            PUB_COMPANY_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_company_account)],
            PUB_COMPANY_BANK:    [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_company_bank)],
            PUB_COMPANY_BIC:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pub_company_bic)],
            PUB_DIR:   [MessageHandler(filters.Regex(BACK_PATTERN), back_from_pay),
                         MessageHandler(filters.TEXT & ~filters.COMMAND, pub_dir)],
            PUB_CONFIRM:[CallbackQueryHandler(pub_confirm, pattern=r"^pub_")],
            PUB_COMPANY_CONFIRM: [CallbackQueryHandler(pub_confirm_company, pattern=r"^cmp_")],
        },
        fallbacks=[
            MessageHandler(filters.Regex(r"^/cancel$"), cancel_wizard),
            CommandHandler("cancel", cancel_wizard)
        ],
        per_message=True,
        # per_message=True — track CallbackQueryHandler states
    )

    # --- Filter conversation handler ---
    filter_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(filter_start, pattern="^flt_open$")],
        states={
            FILT_ORIGIN:[
                MessageHandler(filters.Regex(BACK_PATTERN), filt_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, filt_origin)
            ],
            FILT_DEST:[
                MessageHandler(filters.Regex(BACK_PATTERN), filt_back_to_origin),
                MessageHandler(filters.TEXT & ~filters.COMMAND, filt_dest)
            ],
            FILT_CARGO:[
                MessageHandler(filters.Regex(BACK_PATTERN), filt_back_to_dest),
                MessageHandler(filters.TEXT & ~filters.COMMAND, filt_cargo)
            ],
            FILT_REWARD:[
                MessageHandler(filters.Regex(BACK_PATTERN), filt_back_to_cargo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, filt_reward)
            ],
        },
        fallbacks=[],
    )
    app.add_handler(tok_conv)
    app.add_handler(filter_conv)

    # --- Top‑level text buttons ---
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{MENU_LABEL}$"), show_cabinet))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{PUBLISH_LABEL}$"), show_publish_menu))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{TASKS_TEXT}$"), show_tasks))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{HISTORY_LABEL}$"), show_history))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{ADMIN_PANEL_LABEL}$"), show_admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💰 Мой кошелёк$"), wallet_cb))

    # --- Global "Назад" from publish submenu ---
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{BACK_LABEL}$"), back_to_main))

    # --- Callback for returning to tasks list ---
    app.add_handler(CallbackQueryHandler(back_to_tasks_cb, pattern="^back_to_tasks$"))

    # --- Bonus calculator conversation ---
    calc_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(f"^{BONUS_CALC_LABEL}$"), bonus_calc_start)],
        states={
            BONUS_INPUT:[
                MessageHandler(filters.Regex(BACK_PATTERN), back_to_main),
                MessageHandler(filters.TEXT & ~filters.COMMAND, bonus_calc_compute)
            ]
        },
        fallbacks=[]
    )
    app.add_handler(calc_conv)
    app.add_handler(CallbackQueryHandler(filter_reset, pattern="^flt_reset$"))
    # standalone handler — создаёт разговор, если он ещё не активен
    app.add_handler(pub_wizard)
    app.add_handler(close_conv)

    # --- Signed contract upload handler ---
    app.add_handler(
        MessageHandler(
            filters.Document.ALL & ~filters.FORWARDED,
            receive_signed_doc
        )
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(task_details_cb, pattern=r"^task_\d+"))
    app.add_handler(CallbackQueryHandler(upload_contract_cb, pattern=r"^upload_contract_\d+$"))

    # --- Admin order details & status ---
    app.add_handler(CallbackQueryHandler(admin_order_card,   pattern=r"^admin_order_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_list_status, pattern=r"^admin_change_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_set_status, pattern=r"^setstat_[a-z_]+_\d+$"))
        # --- Navigator cancels own order ---
    app.add_handler(CallbackQueryHandler(nav_cancel_order, pattern=r"^nv_cancel_\d+$"))
    # --- Cabinet & navigation callbacks ---
    app.add_handler(CallbackQueryHandler(show_cabinet, pattern="^back_to_cabinet$"))
    app.add_handler(CallbackQueryHandler(cabinet_work_cb, pattern="^cab_work$"))
    app.add_handler(CallbackQueryHandler(cabinet_page_cb, pattern=r"^cab_\d+$"))
    app.add_handler(CallbackQueryHandler(cabinet_arch_page_cb, pattern=r"^cab_arch_\d+$"))
    app.add_handler(CallbackQueryHandler(archive_details_cb, pattern=r"^arch_\d+$"))

    # --- Admin category navigation ---
    app.add_handler(CallbackQueryHandler(admin_choose_category, pattern=r"^admin_cat_(?:current|archive)$"))
    app.add_handler(CallbackQueryHandler(show_admin_panel, pattern="^admin_back_main$"))

    # --- Start the bot ---
    print("🤖 Бот запущен и ждёт сообщений...")
    app.run_polling()


# --- Admin token menu handlers ---
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Remove wallet banner if present
    banner = context.user_data.pop("last_bot_msg_banner", None)
    if banner:
        try:
            await banner.delete()
        except:
            pass
    """
    Show the main admin panel, usable from both direct messages and callback queries.
    """
    # Determine user and chat based on update type
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        user = q.from_user
        chat_id = q.message.chat.id
    else:
        msg = update.message
        user = msg.from_user
        chat_id = msg.chat.id

    # Only admins allowed
    if user.id not in ADMINS:
        return

    # Fetch overview data
    try:
        ov = requests.get(f"{SERVER_URL}/admin/overview", timeout=4).json()
        txt = "*Статистика системы*\n"
        txt += f"🧭 Навигаторы: {ov.get('cust_agents', 0)}\n"
        txt += f"🚚 Драйверы: {ov.get('exec_agents', 0)}\n"
        txt += f"📦 Всего заявок: {ov.get('orders_total', 0)}\n"
        txt += f"💸 Прибыль (сутки): {ov.get('profit_day', 0)} ₽\n\n"
        txt += "Выберите категорию заявок:"
    except Exception:
        txt = "❌ Не удалось получить статистику.\n\nВыберите категорию заявок:"

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(ADMIN_CURRENT_LABEL, callback_data="admin_cat_current")],
            [InlineKeyboardButton(ADMIN_ARCHIVE_LABEL,  callback_data="admin_cat_archive")],
            [InlineKeyboardButton(TOKEN_MENU_LABEL,     callback_data="admin_token_menu")],
        ]
    )

    # First, show the standard bottom ReplyKeyboard (главное меню)
    try:
        # Determine role for main menu
        try:
            prof = await _http_get_json(f"{SERVER_URL}/agent/{user.id}")
            role = prof.get("agent_type")
        except Exception:
            role = context.user_data.get("role")
        main_menu = await send_main_menu(context.bot, user.id, role)
        context.user_data["last_bot_msg"] = main_menu
    except Exception:
        pass

    # Then display the admin panel text with inline buttons
    if update.callback_query:
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb)
    else:
        await context.bot.send_message(chat_id, txt, parse_mode="Markdown", reply_markup=kb)


async def admin_token_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(TOKEN_CUST_LABEL, callback_data="admin_token_cust")],
            [InlineKeyboardButton(TOKEN_EXEC_LABEL, callback_data="admin_token_exec")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back_main")],
        ]
    )
    await q.edit_message_text("Выберите тип токена:", reply_markup=kb)

async def admin_token_generate_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate one-time invite token for selected role."""
    query = update.callback_query
    await query.answer()

    role_code = query.data.split("_")[-1]
    role = "заказчик" if role_code == "cust" else "исполнитель"

    txt = "❌ Не удалось создать токен."
    try:
        resp = requests.post(
            f"{SERVER_URL}/admin/invite",
            json={"role": role},
            timeout=4,
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            link = data.get("deep_link")
            txt = (
                f"<b>Токен для {_role_label(role)}</b>:\n"
                f"<code>{token}</code>\n\n"
                f"{link}"
            )
    except Exception as e:
        print("admin_token_generate error:", e)

    await query.edit_message_text(
        txt,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="admin_token_menu")]]
        ),
    )
    return TOK_DONE

# --- Stub admin handlers (to be implemented) -------------------------------
async def admin_choose_category(update, context):
    """Handle "Current" and "Archive" admin buttons by invoking list views."""
    q = update.callback_query
    await q.answer()
    cat = q.data.split("_")[-1]  # "current" or "archive"
    chat_id = q.message.chat.id

    from types import SimpleNamespace
    # Build a fake message object for downstream handlers
    fake_msg = SimpleNamespace(
        text = TASKS_TEXT if cat == "current" else HISTORY_LABEL,
        chat = SimpleNamespace(id=chat_id),
        reply_text = q.message.reply_text
    )
    fake_update = SimpleNamespace(message=fake_msg, effective_user=q.from_user)

    if cat == "current":
        await show_tasks(fake_update, context)
    else:
        await show_history(fake_update, context)

async def admin_list_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список возможных статусов для заявки."""
    q = update.callback_query
    await q.answer()
    order_id = int(q.data.split("_")[-1])

    # Текущий статус (чтобы не предлагать выбрать тот же)
    try:
        cur = requests.get(f"{SERVER_URL}/orders/{order_id}", timeout=4).json().get("status", "")
    except Exception:
        cur = ""

    STATUSES = [
        ("active",      "🆕 Активна"),
        ("confirmed",   "✅ Подтверждена"),
        ("in_progress", "🚚 В работе"),
        ("done",        "📦 Исполнена"),
        ("paid",        "💰 Оплачена"),
        ("cancelled",   "❌ Отменена"),
    ]

    buttons = [
        [InlineKeyboardButton(label, callback_data=f"setstat_{code}_{order_id}")]
        for code, label in STATUSES if code != cur
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_order_{order_id}")])

    await q.edit_message_text(
        f"Выберите новый статус для заявки #{order_id}:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def admin_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # Parse callback: setstat_<status>_<order_id>
    payload = q.data[len("setstat_"):]          # "in_progress_120"
    status, order_id_str = payload.rsplit("_", 1)
    order_id = int(order_id_str)

    # Call backend
    ok = False
    try:
        resp = requests.patch(
            f"{SERVER_URL}/admin/order/{order_id}/status/{status}",
            timeout=6
        )
        ok = resp.status_code == 200
    except Exception as e:
        print("admin_set_status request error:", e)

    if ok:
        status_ru = {
            "active": "Активна",
            "confirmed": "Подтверждена",
            "in_progress": "В работе",
            "done": "Исполнена",
            "paid": "Оплачена",
            "cancelled": "Отменена",
        }.get(status, status)
        try:
            update_request(order_id, {"status": status_ru})
        except Exception as e:
            print("Sheets update_request error:", e)

    await q.answer("✅ Обновлено." if ok else "❌ Не удалось изменить статус.")

    # Refresh order card without mutating original CallbackQuery
    from types import SimpleNamespace
    fake_q = SimpleNamespace(
        data=f"admin_order_{order_id}",
        message=q.message,
        from_user=q.from_user,
        answer=q.answer,
        edit_message_text=q.edit_message_text
    )
    fake_update = SimpleNamespace(callback_query=fake_q)
    await admin_order_card(fake_update, context)

async def admin_order_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает карточку заявки для админа с кнопкой смены статуса."""
    q = update.callback_query
    # CallbackQuery may have already been answered upstream (e.g., after a status change).
    # A repeated answer() call on the *same* query raises `BadRequest: query is too old or invalid`.
    # Wrap in try/except to avoid crashing the handler.
    try:
        await q.answer()
    except Exception:
        pass
    parts = q.data.split("_")
    # Extract order ID as the last segment of callback_data
    order_id = int(parts[-1])
    try:
        r = requests.get(f"{SERVER_URL}/orders/{order_id}", timeout=4)
        if r.status_code != 200:
            await q.edit_message_text("❌ Заявка не найдена или уже закрыта.")
            return
        detail = r.json()
    except Exception as e:
        await q.edit_message_text(f"❌ Ошибка при получении данных: {e}")
        return
    # --- Build details text and keyboard (unchanged logic) ---
    STATUS_LABELS = {
        "active":      "🆕 Активна",
        "confirmed":   "✅ Подтверждена",
        "in_progress": "🚚 В работе",
        "done":        "📦 Исполнена",
        "paid":        "💰 Оплачена",
        "new":         "🆕 В ожидании",
        "completed":   "📦 Исполнена",
        "archived":    "📂 Архив",
        "cancelled":   "❌ Отменена",
    }
    status = detail.get("status", "")
    status_line = f"📋 Статус: {STATUS_LABELS.get(status, status)}\n"
    header = f"[#{detail['id']}] {detail['message']}"
    sections = [status_line + header]
    if detail.get("loads"):
        sections.append("📍 Пункты погрузки:")
        for i, l in enumerate(detail["loads"], start=1):
            sections.append(f"  {i}. {l.get('place','')} ({l.get('date','')})")
        sections.append("")
    if detail.get("unloads"):
        sections.append("📍 Пункты выгрузки:")
        for i, u in enumerate(detail["unloads"], start=1):
            sections.append(f"  {i}. {u.get('place','')} ({u.get('date','')})")
        sections.append("")
    cars = detail.get("cars", [])
    if cars:
        car_strings = []
        for car in cars:
            b = car.get("brand", "").strip()
            m = car.get("model", "").strip()
            name = f"{b} {m}".strip()
            car_strings.append(f"1×{name}")
        sections.append(f"🚚 Груз: {'; '.join(car_strings)}")
    else:
        car_count = detail.get("car_count")
        car_models = detail.get("car_models", "").strip()
        if car_count and car_models:
            sections.append(f"🚚 Груз: {car_count}×{car_models}")
    budget_text = detail.get("budget", "")
    if budget_text:
        sections.append(f"💵 Ставка (заказчик): {budget_text}")
        customer_amt = _clean_money(budget_text)
        exec_amt = int(customer_amt * 0.88)
        nav_bonus = int(customer_amt * 0.03)
        sections.append(f"💵 Ставка (исполнитель): {exec_amt:,} руб".replace(",", " "))
        sections.append(f"🏆 Бонус навигатора: +{nav_bonus:,} ₽".replace(",", " "))
    pay_terms_text = detail.get("pay_terms", "")
    if pay_terms_text:
        sections.append(f"💳 Условия оплаты: {pay_terms_text}")
    bonus_exec = detail.get("reward_exec") or 0
    bonus_cust = detail.get("reward_cust") or 0
    sections.append(f"🏆 Бонус заказчика: +{fmt_money(bonus_cust)} ₽")
    sections.append(f"🏆 Бонус исполнителя: +{fmt_money(bonus_exec)} ₽")
    text = "\n".join(sections)
    kb_buttons = [
        [InlineKeyboardButton("Сменить статус", callback_data=f"admin_change_{order_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_cabinet")]
    ]
    kb = InlineKeyboardMarkup(kb_buttons)
    # --- send details, but fall back if text is too long or edit fails ---
    try:
        if len(text) > 4000:
            # Telegram edit limit is 4096; safer to delete and send a fresh message
            await q.message.delete()
            await context.bot.send_message(
                chat_id=q.from_user.id,
                text=text[:4090],
                reply_markup=kb
            )
        else:
            await q.edit_message_text(text, reply_markup=kb)
    except Exception as e:
        # Any failure (e.g., BadRequest), send as new message
        try:
            await context.bot.send_message(
                chat_id=q.from_user.id,
                text=text[:4090],
                reply_markup=kb
            )
        except Exception as ex:
            print("admin_order_card send error:", ex)

# ---------- entrypoint ----------
if __name__ == "__main__":
    main()