from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from pprint import pprint
import requests
import os
import re

# Platform (TechnoЛогистика) company details for driver contracts
PLATFORM_COMPANY_NAME      = os.getenv("TECH_COMPANY_NAME", "ООО «ТехноЛогистика»")
PLATFORM_COMPANY_DIRECTOR  = os.getenv("TECH_COMPANY_DIRECTOR", "")
PLATFORM_COMPANY_REQUISITES= os.getenv("TECH_COMPANY_REQUISITES", "")

from modules.helpers import (
    _clean_optional,
    BACK_PATTERN,
    format_company_requisites,
    _clean_human_field
)

# --- Клавиатура «Назад» для close_wizard ---
BACK_KB = ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True, one_time_keyboard=True)
from modules.company_service import _get_company, _save_company

# --- Close (executor) states ---
CLOSE_FIO, CLOSE_PASSPORT, CLOSE_INN, CLOSE_COMPANY_CONFIRM, CLOSE_COMPANY, CLOSE_DIRECTOR, \
CLOSE_TRUCK, CLOSE_TRAILER, CLOSE_INSURANCE, CLOSE_LICENSE, \
CLOSE_KPP, BANK_NAME, BANK_RS, BANK_KS, BANK_BIC, CLOSE_ADDRESS, \
CLOSE_L1_POINT, CLOSE_L1_DATE, CLOSE_U1_POINT, CLOSE_U1_DATE, CLOSE_PAY = range(21)

async def close_get_fio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] close_get_fio called with text: '{update.message.text}'")
    # --- кнопка «Назад» ---
    if update.message.text.strip() == BACK_PATTERN:
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END

    # --- сохраняем ФИО водителя ---
    fio = update.message.text.strip()
    context.user_data["driver_fio"] = fio

    # --- спрашиваем паспорт ---
    await update.message.reply_text(
        "Введите серию и номер паспорта водителя:",
        reply_markup=BACK_KB
    )
    print(">>> returned CLOSE_PASSPORT")
    return CLOSE_PASSPORT

async def close_get_passport(update, context):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    # сохраняем паспорт
    context.user_data["driver_passport"] = update.message.text.strip()
    # спрашиваем марку и номер тягача
    await update.message.reply_text(
        "Тягач: марка и гос‑номер (например «Volvo FH, О123АА 77»):",
        reply_markup=BACK_KB
    )
    return CLOSE_TRUCK

# --- step: company name ---
async def close_get_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    context.user_data["carrier_company"] = update.message.text.strip()
    await update.message.reply_text(
        "Введите КПП перевозчика (если нет — напишите «нет»):",
        reply_markup=ReplyKeyboardRemove()
    )
    return CLOSE_KPP

# --- step: director ---
async def close_get_director(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    raw = update.message.text.strip()
    fio = _clean_human_field(raw)

    # Разрешаем «Фамилия И.» либо «Фамилия И.О.»
    pattern = r"^[A-Za-zА-Яа-яЁё][-A-Za-zА-Яа-яЁё'\\- ]+ [A-Za-zА-ЯЁ]\.(?: ?[A-Za-zА-ЯЁ]\.)?$"
    if not re.match(pattern, fio):
        await update.message.reply_text(
            "Пожалуйста, введите Фамилию и инициалы директора, например «Иванов И.»"
            " или «Иванов И.О.» (инициалы через точку).",
            reply_markup=ReplyKeyboardRemove()
        )
        return CLOSE_DIRECTOR

    # --- valid FIO, сохраняем ---
    context.user_data["carrier_director"] = fio

    # Если нет выбора НДС/без НДС – спрашиваем
    if "vat" not in context.user_data:
        kb_vat = InlineKeyboardMarkup([
            [InlineKeyboardButton("С НДС", callback_data="pay_vat"),
             InlineKeyboardButton("Без НДС", callback_data="pay_novat")]
        ])
        await update.message.reply_text(
            "Выберите форму оплаты (с НДС или без НДС):",
            reply_markup=kb_vat
        )
        return CLOSE_PAY

    return await _finish_close(update, context)


# --- step: truck info ---
async def close_get_truck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем марку и гос‑номер тягача и спрашиваем прицеп."""
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    context.user_data["truck_info"] = update.message.text.strip()
    await update.message.reply_text(
        "Прицеп: марка и гос‑номер:",
        reply_markup=BACK_KB
    )
    return CLOSE_TRAILER


# --- step: trailer info ---
async def close_get_trailer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем данные прицепа и переходим к страховому полису."""
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    context.user_data["trailer_info"] = update.message.text.strip()
    await update.message.reply_text(
        "Введите серию и номер страхового полиса ОСАГО/CМR (если полиса нет — напишите «нет»):",
        reply_markup=BACK_KB
    )
    return CLOSE_INSURANCE

# --- step: insurance policy ---
async def close_get_insurance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")

    # Сохраняем серию/номер страхового полиса и спрашиваем ИНН перевозчика.
    context.user_data["insurance_policy"] = _clean_optional(update.message.text)
    await update.message.reply_text(
        "Введите ИНН перевозчика:",
        reply_markup=BACK_KB
    )
    return CLOSE_INN

# --- step: driver license ---
async def close_get_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")

    # сохраняем ВУ
    context.user_data["driver_license"] = _clean_optional(update.message.text)
    await update.message.reply_text(
        "Тягач: марка и гос‑номер (например «Volvo FH, О123АА 77»):",
        reply_markup=BACK_KB
    )
    return CLOSE_TRUCK

# --- step: load / unload contacts ---
async def close_get_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["load_contacts"] = update.message.text.strip()
    await update.message.reply_text(
        "Место погрузки №1 (город / адрес):",
        reply_markup=BACK_KB
    )
    return CLOSE_L1_POINT

# --- step: load point ---
async def close_get_load_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["load1_point"] = update.message.text.strip()
    await update.message.reply_text(
        "Дата первой погрузки?  (например 12.05.2025)",
        reply_markup=BACK_KB
    )
    return CLOSE_L1_DATE

# --- step: load date ---
async def close_get_load_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["load1_date"] = update.message.text.strip()
    await update.message.reply_text(
        "Место выгрузки №1 (город / адрес):",
        reply_markup=BACK_KB
    )
    return CLOSE_U1_POINT

# --- step: unload point ---
async def close_get_unload_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["unload1_point"] = update.message.text.strip()
    await update.message.reply_text(
        "Дата выгрузки №1:",
        reply_markup=BACK_KB
    )
    return CLOSE_U1_DATE

# --- step: unload date ---
async def close_get_unload_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем дату выгрузки
    context.user_data["unload1_date"] = update.message.text.strip()
    await update.message.reply_text(
        "Введите ИНН перевозчика:",
        reply_markup=BACK_KB
    )
    return CLOSE_INN


# --- step: ИНН ---
async def close_get_inn(update: Update, ctx):
    # --- DEBUG ------------------------------------------
    import re
    inn_raw = update.message.text
    print(f"[DEBUG] Введён ИНН: '{inn_raw}'")
    # Оставляем только цифры из введённого
    raw_digits = re.sub(r"\D", "", inn_raw)
    # Всегда используем raw_digits в качестве ключа (поддерживая 8,9,10,12 цифр)
    inn = raw_digits
    print(f"[DEBUG] Используемый ИНН: '{inn}'")
    # ----------------------------------------------------
    ctx.user_data["inn"] = inn
    company = await _get_company(inn)
    ctx.user_data["company_obj"] = company or {}
    if company:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="cmp_yes"),
             InlineKeyboardButton("✏️ Нет", callback_data="cmp_no")]
        ])
        comp_name = company.get('name', '')
        await update.message.reply_text(
            f"🏢 Компания «{comp_name}» найдена.\n"
            "Использовать сохранённые реквизиты?",
            reply_markup=kb
        )
        return CLOSE_COMPANY_CONFIRM

    await update.message.reply_text(
        "Введите название компании-перевозчика:",
        reply_markup=ReplyKeyboardRemove()
    )
    return CLOSE_COMPANY

# --- step: confirm company usage (inline) ---
async def close_confirm_company(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    if q.data == "cmp_yes":
        o = ctx.user_data.get("company_obj", {})
        # auto-fill all company fields
        ctx.user_data["carrier_company"]    = o.get("name", "")
        ctx.user_data["carrier_requisites"] = format_company_requisites(o)
        ctx.user_data["carrier_inn"]        = o.get("inn", "")
        ctx.user_data["carrier_kpp"]        = o.get("kpp", "")
        # duplicate INN/KPP into generic keys so they propagate to the contract
        ctx.user_data["inn"] = ctx.user_data["carrier_inn"]
        ctx.user_data["kpp"] = ctx.user_data["carrier_kpp"]
        ctx.user_data["carrier_address"]    = o.get("address", "")
        ctx.user_data["carrier_address_exists"] = bool(ctx.user_data["carrier_address"])
        # director may be missing in DB
        ctx.user_data["carrier_director"]   = (o.get("director") or "").strip()
        ctx.user_data["bank_name"] = o.get("bank_name", "").strip()
        ctx.user_data["bank_rs"]   = o.get("bank_rs", "").strip()
        ctx.user_data["bank_bic"]  = o.get("bank_bic", "").strip()
        # if no director, ask the driver
        if not ctx.user_data["carrier_director"]:
            await q.message.edit_text(
                "Введите ФИО директора (подписанта) компании-перевозчика:",
                reply_markup=ReplyKeyboardRemove()
            )
            return CLOSE_DIRECTOR

        # спрашиваем форму оплаты всегда
        kb_vat = InlineKeyboardMarkup([
            [InlineKeyboardButton("С НДС",  callback_data="pay_vat"),
             InlineKeyboardButton("Без НДС", callback_data="pay_novat")]
        ])
        await q.message.reply_text(
            "Выберите форму оплаты (с НДС или без НДС):",
            reply_markup=kb_vat
        )
        return CLOSE_PAY

    else:
        # очистить авто-подставленные реквизиты
        for key in ("carrier_company", "carrier_director",
                    "kpp", "bank_name", "bank_rs", "bank_ks", "bank_bic"):
            ctx.user_data.pop(key, None)
        ctx.user_data["skip_bank"] = False
        await q.message.edit_text("Введите название компании-перевозчика:", reply_markup=ReplyKeyboardRemove())
        return CLOSE_COMPANY

# --- step: КПП ---
async def close_get_kpp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Skip all requisites and transport detail questions if company was auto-filled
    if context.user_data.get("skip_bank"):
        # proceed directly to load/unload contacts
        return await close_get_contacts(update, context)
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    context.user_data["kpp"] = update.message.text.strip()
    await update.message.reply_text(
        "Название банка:",
        reply_markup=BACK_KB
    )
    return BANK_NAME

# --- step: bank name ---
async def close_get_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    if "🏢 Компания" in update.message.text:
        await update.message.reply_text(
            "Пожалуйста, введите только наименование банка.",
            reply_markup=ReplyKeyboardRemove()
        )
        return BANK_NAME
    context.user_data["bank_name"] = _clean_human_field(update.message.text.strip())
    await update.message.reply_text(
        "Расчётный счёт (р/с):",
        reply_markup=BACK_KB
    )
    return BANK_RS

# --- step: bank rs ---
async def close_get_bank_rs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    import re
    clean_rs = re.sub(r"\D", "", update.message.text)
    if "🏢 Компания" in update.message.text:
        await update.message.reply_text(
            "Пожалуйста, введите только номер расчётного счёта.",
            reply_markup=ReplyKeyboardRemove()
        )
        return BANK_RS
    if len(clean_rs) < 15 or len(clean_rs) > 26:
        await update.message.reply_text(
            "Расчётный счёт должен содержать 15–26 цифр. Попробуйте ещё раз:",
            reply_markup=ReplyKeyboardRemove()
        )
        return BANK_RS
    context.user_data["bank_rs"] = clean_rs
    await update.message.reply_text(
        "Корреспондентский счёт (к/с):",
        reply_markup=BACK_KB
    )
    return BANK_KS

# --- step: bank ks ---
async def close_get_bank_ks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        print(f"[DEBUG] user input: '{update.message.text}' BACK_PATTERN: '{BACK_PATTERN}'")
    context.user_data["bank_ks"] = update.message.text.strip()
    await update.message.reply_text(
        "БИК:",
        reply_markup=BACK_KB
    )
    return BANK_BIC


# --- step: bank bic (before address) ----------------------------------------
async def close_get_bank_bic(update: Update, ctx):
    if update.message.text == BACK_PATTERN:
        # handle back as in other steps
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    import re
    clean_bic = re.sub(r"\D", "", update.message.text)
    print(f"[DEBUG] close_get_bank_bic raw: '{update.message.text}', clean: '{clean_bic}', len: {len(clean_bic)}")
    # clean_bic = _clean_human_field(clean_bic)
    if "🏢 Компания" in update.message.text:
        await update.message.reply_text(
            "Пожалуйста, введите только БИК, без лишних строк.",
            reply_markup=ReplyKeyboardRemove()
        )
        return BANK_BIC
    if len(clean_bic) not in (8, 9):
        await update.message.reply_text(
            "БИК должен содержать 8 или 9 цифр. Введите корректный БИК:",
            reply_markup=ReplyKeyboardRemove()
        )
        return BANK_BIC
    ctx.user_data["bank_bic"] = clean_bic

    # --- ask for VAT option ---
    kb_vat = InlineKeyboardMarkup([
        [InlineKeyboardButton("С НДС",  callback_data="pay_vat"),
         InlineKeyboardButton("Без НДС", callback_data="pay_novat")]
    ])
    await update.message.reply_text(
        "Выберите форму оплаты (с НДС или без НДС):",
        reply_markup=kb_vat
    )
    return CLOSE_PAY
# --- callback: choose VAT / no‑VAT ------------------------------------------
async def close_pay_choice(update: Update, ctx):
    """Inline buttons «С НДС / Без НДС»"""
    q = update.callback_query
    await q.answer()

    vat = q.data == "pay_vat"       # True = с НДС
    ctx.user_data["vat"] = vat
    ctx.user_data["pay_terms"] = "Безнал с НДС" if vat else "Безнал без НДС"

    await q.edit_message_reply_markup(reply_markup=None)

    if vat:
        # При С НДС не меняем перевозчика, только назначаем заказчика в _finish_close
        await q.message.reply_text("✅ Реквизиты платформы применены (С НДС).")
        return await _finish_close(update, ctx)

    # если адрес уже сохранён
    if ctx.user_data.get("carrier_address"):
        # если директор тоже указан – завершаем
        if ctx.user_data.get("carrier_director"):
            return await _finish_close(update, ctx)

        # иначе спросим директора
        await q.message.reply_text(
            "Введите ФИО директора (подписанта) компании-перевозчика:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CLOSE_DIRECTOR
    await q.message.reply_text(
        "Введите юридический адрес перевозчика (например, г. Москва, ул. Ленина, д. 1):",
        reply_markup=ReplyKeyboardRemove()
    )
    return CLOSE_ADDRESS

# ---------- CALLBACK close_<ID> ----------
async def start_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «Закрыть» под заявкой."""
    print(f"[DEBUG] start_close_callback called with data: '{update.callback_query.data}'")
    query = update.callback_query
    # instant answer to remove Telegram “loading…” spinner
    try:
        await query.answer()
    except Exception:
        # ignore if already answered
        pass

    # id заявки закодирован в callback_data: close_123
    order_id = int(query.data.split("_")[1])
    context.user_data["closing_order_id"] = order_id
    context.user_data.pop("vat", None)  # <<< сброс для нового цикла

    context.user_data["origin_message"] = query.message           # для дальнейшего edit

    # помечаем кнопку как уже нажатую
    await query.edit_message_reply_markup(reply_markup=None)

    await query.message.reply_text(
        "Введите пожалуйста *Фамилию, Имя и Отчество (если есть) водителя*.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return CLOSE_FIO

# ----------------------------------------------------------------------
# helper: finish close wizard
async def _finish_close(update: Update, ctx):
    """Отправляет payload на /close_order, кэширует компанию и завершает диалог."""
    import os, requests
    SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")

    inn  = ctx.user_data.get("inn", "-")
    kpp  = ctx.user_data.get("kpp", "-")
    # формируем строку банковских реквизитов
    # ----- build full carrier_requisites string (ИНН, КПП, р/с, банк, БИК, адрес) -----
    carrier_reqs_parts = [
        f"ИНН {inn}",
        f"КПП {kpp}"
    ]
    if ctx.user_data.get("bank_rs"):
        carrier_reqs_parts.append(f"р/с {ctx.user_data['bank_rs']}")
    if ctx.user_data.get("bank_name"):
        carrier_reqs_parts.append(f"в банке {ctx.user_data['bank_name']}")
    if ctx.user_data.get("bank_bic"):
        carrier_reqs_parts.append(f"БИК {ctx.user_data['bank_bic']}")
    if ctx.user_data.get("carrier_address"):
        carrier_reqs_parts.append(f"Юридический адрес: {ctx.user_data['carrier_address']}")

    # save back to user_data so payload can use it
    ctx.user_data["carrier_requisites"] = ", ".join(carrier_reqs_parts)
    print("[DBG] bank_name =", ctx.user_data.get("bank_name"))
    print("[DBG] bank_rs   =", ctx.user_data.get("bank_rs"))
    print("[DBG] bank_bic  =", ctx.user_data.get("bank_bic"))
    print("[DBG] carrier_requisites =", ctx.user_data["carrier_requisites"])
    # --- синхронизируем раздельные поля для шаблона ---
    ctx.user_data["carrier_account"]   = ctx.user_data.get("bank_rs", "")
    ctx.user_data["carrier_bank_name"] = ctx.user_data.get("bank_name", "")
    ctx.user_data["carrier_bic"]       = ctx.user_data.get("bank_bic", "")
    
    parts = []
    if ctx.user_data.get("bank_name"):
        parts.append(ctx.user_data["bank_name"])
    if ctx.user_data.get("bank_rs"):
        parts.append(f"р/с {ctx.user_data['bank_rs']}")
    if ctx.user_data.get("bank_ks"):
        parts.append(f"к/с {ctx.user_data['bank_ks']}")
    if ctx.user_data.get("bank_bic"):
        parts.append(f"БИК {ctx.user_data['bank_bic']}")

    # если раздельных полей нет – используем старое поле bank
    bank = "; ".join(parts) or ctx.user_data.get("bank", "")

    # fetch existing order details to get customer requisites
    order_id = ctx.user_data.get("closing_order_id")
    try:
        detail_resp = requests.get(f"{SERVER_URL}/orders/{order_id}", timeout=4)
        if detail_resp.status_code == 200:
            detail = detail_resp.json()
            # Try both keys used by API for customer requisites
            cust_reqs = (
                detail.get("cust_requisites")
                or detail.get("customer_requisites")
                or ""
            )
        else:
            detail = {}
            cust_reqs = ""
    except Exception:
        detail = {}
        cust_reqs = ""

    # fetch customer director and company name from order details
    cust_dir = detail.get("cust_director") or detail.get("customer_director") or ""
    cust_company = detail.get("cust_company_name") or detail.get("customer_company") or ""

    # --- override customer (заказчик) based on VAT choice ---
    if ctx.user_data.get("vat"):
        # С НДС: заказчик – ООО "ТехноЛогистика"
        cust_company_name = PLATFORM_COMPANY_NAME
        cust_dir = PLATFORM_COMPANY_DIRECTOR
        # For individual requisites, parse PLATFORM_COMPANY_REQUISITES if needed
        # Assuming PLATFORM_COMPANY_REQUISITES is full string
        cust_reqs = PLATFORM_COMPANY_REQUISITES
    else:
        # Без НДС: заказчик – ИП Хейгетян Е.В.
        cust_company_name = os.getenv("IP_NAME", "ИП Хейгетян Е.В.")
        cust_dir = os.getenv("IP_DIRECTOR", "Хейгетян Е.В.")
        # Build cust_reqs from environment variables for IP:
        ip_inn = os.getenv("IP_INN", "")
        ip_kpp = os.getenv("IP_KPP", "")
        ip_bank_rs = os.getenv("IP_BANK_RS", "")
        ip_bank_name = os.getenv("IP_BANK_NAME", "")
        ip_bic = os.getenv("IP_BIC", "")
        ip_address = os.getenv("IP_ADDRESS", "")
        # Assemble requisites for IP
        parts_ip = []
        if ip_inn:
            parts_ip.append(f"ИНН {ip_inn}")
        if ip_kpp:
            parts_ip.append(f"КПП {ip_kpp}")
        if ip_bank_rs:
            parts_ip.append(f"р/с {ip_bank_rs}")
        if ip_bank_name:
            parts_ip.append(ip_bank_name)
        if ip_bic:
            parts_ip.append(f"БИК {ip_bic}")
        if ip_address:
            parts_ip.append(f"Юридический адрес: {ip_address}")
        cust_reqs = ", ".join(parts_ip)
    # synchronize into ctx.user_data for template compatibility
    ctx.user_data["cust_company_name"] = cust_company_name
    ctx.user_data["cust_director"] = cust_dir
    ctx.user_data["cust_reqs_override"] = cust_reqs
    ctx.user_data["cust_sign_name"] = cust_dir

    payload = {
        "order_id":        ctx.user_data.get("closing_order_id"),
        "executor_id":     update.effective_user.id,
        "driver_fio":      ctx.user_data.get("driver_fio", "-"),
        "carrier_company": ctx.user_data.get("carrier_company", ""),
        "carrier_director":ctx.user_data.get("carrier_director", ""),
        # combined requisites for executor (сохранённые реквизиты перевозчика)
        "carrier_requisites": ctx.user_data.get("carrier_requisites", f"ИНН {inn}; КПП {kpp}; {bank}"),
        # duplicate under the key expected for executor in the contract template
        "executor_requisites": ctx.user_data.get("carrier_requisites", f"ИНН {inn}; КПП {kpp}; {bank}"),
        # include customer requisites for the contract template
        "cust_requisites": ctx.user_data.get("cust_reqs_override", cust_reqs),

        # --- customer fields (override based on VAT) ---
        "cust_company_name": ctx.user_data.get("cust_company_name", ""),
        "cust_inn": os.getenv("IP_INN", "") if not ctx.user_data.get("vat") else os.getenv("TECH_COMPANY_INN", ""),
        "cust_kpp": os.getenv("IP_KPP", "") if not ctx.user_data.get("vat") else os.getenv("TECH_COMPANY_KPP", ""),
        "cust_account": os.getenv("IP_BANK_RS", "") if not ctx.user_data.get("vat") else os.getenv("TECH_BANK_RS", ""),
        "cust_bank_name": os.getenv("IP_BANK_NAME", "") if not ctx.user_data.get("vat") else os.getenv("TECH_BANK_NAME", ""),
        "cust_bic": os.getenv("IP_BIC", "") if not ctx.user_data.get("vat") else os.getenv("TECH_BANK_BIC", ""),
        "cust_address": os.getenv("IP_ADDRESS", "") if not ctx.user_data.get("vat") else PLATFORM_COMPANY_REQUISITES.split(";", 1)[-1].strip(),
        "cust_sign_name": ctx.user_data.get("cust_sign_name", ""),

        # also explicit customer keys for template compatibility
        "customer_requisites": ctx.user_data.get("cust_reqs_override", cust_reqs),
        "customer_director": ctx.user_data.get("cust_director", cust_dir),
        "customer_company": ctx.user_data.get("cust_company_name", cust_company),
        # duplicate executor/company keys if template uses them
        "executor_company": ctx.user_data.get("carrier_company", ""),
        "executor_director": ctx.user_data.get("carrier_director", ""),
        "company_requisites": ctx.user_data.get("carrier_requisites", f"ИНН {inn}; КПП {kpp}; {bank}"),
        "company_director": ctx.user_data.get("carrier_director", ""),
        "vat": ctx.user_data.get("vat", True),
        "pay_terms": ctx.user_data.get("pay_terms", ""),

        "VAT_FLAG":   "с НДС" if ctx.user_data.get("vat") else "без НДС",
        "PAY_TERMS":  ctx.user_data.get("pay_terms", ""),

        # Individual fields for executor (driver's company)
        "executor_inn":         inn,
        "executor_kpp":         kpp,
        "executor_address":     ctx.user_data.get("carrier_address", ""),
        "executor_bank_name":   ctx.user_data.get("bank_name", ""),
        "executor_bank_rs":     ctx.user_data.get("bank_rs", ""),
        "executor_bank_ks":     ctx.user_data.get("bank_ks", ""),
        "executor_bank_bic":    ctx.user_data.get("bank_bic", ""),

        # --- carrier duplicates for template ---
        "carrier_company":    ctx.user_data.get("carrier_company", ""),
        "carrier_inn":        inn,
        "carrier_kpp":        kpp,
        "carrier_account":    ctx.user_data.get("bank_rs", ""),
        "carrier_bank_name":  ctx.user_data.get("bank_name", ""),
        "carrier_bic":        ctx.user_data.get("bank_bic", ""),

        # Individual fields for customer (TechnoЛогистика)
        "customer_inn":         detail.get("cust_inn") or detail.get("customer_inn") or "",
        "customer_kpp":         detail.get("cust_kpp") or detail.get("customer_kpp") or "",
        "customer_address":     detail.get("cust_address") or detail.get("customer_address") or "",
        "customer_bank_name":   detail.get("cust_bank_name") or detail.get("customer_bank_name") or "",
        "customer_bank_rs":     detail.get("cust_bank_rs") or detail.get("customer_bank_rs") or "",
        "customer_bank_ks":     detail.get("cust_bank_ks") or detail.get("customer_bank_ks") or "",
        "customer_bank_bic":    detail.get("cust_bank_bic") or detail.get("customer_bank_bic") or "",

        # --- реквизиты отдельными полями для шаблона договора ---
        "inn":             inn,
        "kpp":             kpp,
        "bank_name":       ctx.user_data.get("bank_name", ""),
        "bank_rs":         ctx.user_data.get("bank_rs", ""),
        "bank_ks":         ctx.user_data.get("bank_ks", ""),
        "bank_bic":        ctx.user_data.get("bank_bic", ""),
        # ---------------------------------------------------------

        "driver_passport": ctx.user_data.get("driver_passport", ""),
        "truck_info":      ctx.user_data.get("truck_info", ""),
        "trailer_info":    ctx.user_data.get("trailer_info", ""),
        "insurance_policy":ctx.user_data.get("insurance_policy", ""),
        "driver_license":  ctx.user_data.get("driver_license", ""),
    }


        # --- отправляем данные на /close_order ----
    try:
        resp = requests.post(f"{SERVER_URL}/close_order", json=payload, timeout=5)
    except requests.exceptions.RequestException as exc:
        print("close_order request error:", exc)
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Не удалось связаться с сервером и сформировать договор. "
                 "Реквизиты сохранены, попробуйте ещё раз позже."
        )
        return ConversationHandler.END

    # кешируем перевозчика
    await _save_company({
        "inn": inn,
        "kpp": kpp,
        "name": ctx.user_data.get("carrier_company", ""),
        "director": ctx.user_data.get("carrier_director", ""),
        "bank": bank,
        "bank_name": ctx.user_data.get("bank_name", ""),
        "bank_rs": ctx.user_data.get("bank_rs", ""),
        "bank_ks": ctx.user_data.get("bank_ks", ""),
        "bank_bic": ctx.user_data.get("bank_bic", ""),
        "address":  ctx.user_data.get("carrier_address", ""),
    })

    # ---------- ответ сервера ----------
    if resp.status_code == 200:
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Данные отправлены, спасибо!"
        )
        # попытка отправить сформированные договоры
        try:
            import io, os, requests
            data = resp.json()
            cust_tg = data.get("customer_tg")
            exec_tg = data.get("executor_tg")

            for field in ("cust_path",):
                path = data.get(field)
                if not path:
                    continue

                # сначала пробуем локальный файл
                if os.path.isfile(path):
                    file_obj = open(path, "rb")
                else:
                    # скачиваем с сервера
                    dl = requests.get(
                        f"{SERVER_URL}/file",
                        params={"path": path},
                        timeout=10
                    )
                    if dl.status_code != 200:
                        print("Download error:", dl.text)
                        continue
                    file_obj = io.BytesIO(dl.content)
                    file_obj.name = os.path.basename(path)

                tgt = cust_tg
                if tgt:
                    await ctx.bot.send_document(
                        chat_id=tgt,
                        document=file_obj,
                        filename=os.path.basename(path),
                        caption="📄 Договор для подписания"
                    )

            # также отправим файл договора исполнителю (водителю), а не только ссылку
            exec_tg = data.get("executor_tg")
            exec_path = data.get("exec_path")
            if exec_tg and exec_path:
                try:
                    if os.path.isfile(exec_path):
                        with open(exec_path, "rb") as f:
                            await ctx.bot.send_document(chat_id=exec_tg, document=f, caption="📄 Ваш договор")
                    else:
                        dl2 = requests.get(f"{SERVER_URL}/file", params={"path": exec_path}, timeout=10)
                        if dl2.status_code == 200:
                            import io
                            buf = io.BytesIO(dl2.content)
                            buf.name = os.path.basename(exec_path)
                            await ctx.bot.send_document(chat_id=exec_tg, document=buf, caption="📄 Ваш договор")
                except Exception as e2:
                    print("Send executor contract error:", e2)
        except Exception as e:
            print("Send contract error:", e)

    else:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text

        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Не удалось закрыть заявку: {detail}"
        )

    return ConversationHandler.END


# ----------------------------------------------------------------------

# --- step: юридический адрес перевозчика ---
async def close_get_address(update: Update, ctx):
    """Сохраняем юридический адрес перевозчика и завершаем диалог."""
    if update.message.text == BACK_PATTERN:
        print(f"[DEBUG] Кнопка Назад нажата! BACK_PATTERN: '{BACK_PATTERN}'")
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
        )
        return ConversationHandler.END
    addr = update.message.text.strip()
    if not addr:
        await update.message.reply_text(
            "Пожалуйста, введите только юридический адрес компании.",
            reply_markup=ReplyKeyboardRemove()
        )
        return CLOSE_ADDRESS
    ctx.user_data["carrier_address"] = addr
    await update.message.reply_text(
        "Введите ФИО директора (подписанта):",
        reply_markup=BACK_KB
    )
    return CLOSE_DIRECTOR

__all__ = (
    # states
    "CLOSE_FIO", "CLOSE_PASSPORT", "CLOSE_INN", "CLOSE_COMPANY_CONFIRM",
    "CLOSE_COMPANY", "CLOSE_DIRECTOR",
    "CLOSE_TRUCK", "CLOSE_TRAILER", "CLOSE_INSURANCE", "CLOSE_LICENSE",
    "CLOSE_KPP", "BANK_NAME", "BANK_RS", "BANK_KS", "BANK_BIC", "CLOSE_ADDRESS",
    "CLOSE_L1_POINT", "CLOSE_L1_DATE", "CLOSE_U1_POINT", "CLOSE_U1_DATE", "CLOSE_PAY",
    # handlers
    "start_close_callback",
    "close_get_fio", "close_get_passport", "close_get_company",
    "close_get_director", "close_get_truck", "close_get_trailer",
    "close_get_insurance", "close_get_license", "close_get_inn",
    "close_confirm_company",
    "close_get_kpp", "close_get_bank_name", "close_get_bank_rs",
    "close_get_bank_ks", "close_get_bank_bic", "close_pay_choice", "close_get_address"
)

from telegram.ext import CallbackQueryHandler, MessageHandler, CommandHandler, ConversationHandler, filters

def register_close_conversation(application, start_handler):
    """
    Registers the ConversationHandler for closing orders.
    - application: the telegram.ext Application instance.
    - start_handler: the handler (e.g., CommandHandler) to call on fallback (/start).
    """
    close_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_close_callback, pattern=r"^close_\d+$"),
        ],
        states={
            CLOSE_FIO: [
                MessageHandler(filters.TEXT, close_get_fio),
            ],
            CLOSE_PASSPORT: [
                MessageHandler(filters.TEXT, close_get_passport),
            ],
            CLOSE_INN: [
                MessageHandler(filters.TEXT, close_get_inn),
            ],
            CLOSE_COMPANY_CONFIRM: [
                CallbackQueryHandler(close_confirm_company, pattern=r"^cmp_(yes|no)$"),
            ],
            CLOSE_COMPANY: [
                MessageHandler(filters.TEXT, close_get_company),
            ],
            CLOSE_DIRECTOR: [
                MessageHandler(filters.TEXT, close_get_director),
            ],
            CLOSE_TRUCK: [
                MessageHandler(filters.TEXT, close_get_truck),
            ],
            CLOSE_TRAILER: [
                MessageHandler(filters.TEXT, close_get_trailer),
            ],
            CLOSE_INSURANCE: [
                MessageHandler(filters.TEXT, close_get_insurance),
            ],
            CLOSE_LICENSE: [
                MessageHandler(filters.TEXT, close_get_license),
            ],
            CLOSE_KPP: [
                MessageHandler(filters.TEXT, close_get_kpp),
            ],
            BANK_NAME: [
                MessageHandler(filters.TEXT, close_get_bank_name),
            ],
            BANK_RS: [
                MessageHandler(filters.TEXT, close_get_bank_rs),
            ],
            BANK_KS: [
                MessageHandler(filters.TEXT, close_get_bank_ks),
            ],
            BANK_BIC: [
                MessageHandler(filters.TEXT, close_get_bank_bic),
            ],
            CLOSE_ADDRESS: [
                MessageHandler(filters.TEXT, close_get_address),
            ],
            CLOSE_L1_POINT: [
                MessageHandler(filters.TEXT, close_get_load_point),
            ],
            CLOSE_L1_DATE: [
                MessageHandler(filters.TEXT, close_get_load_date),
            ],
            CLOSE_U1_POINT: [
                MessageHandler(filters.TEXT, close_get_unload_point),
            ],
            CLOSE_U1_DATE: [
                MessageHandler(filters.TEXT, close_get_unload_date),
            ],
            CLOSE_PAY: [
                CallbackQueryHandler(close_pay_choice, pattern=r"^pay_(vat|novat)$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start_handler),
        ],
        allow_reentry=True,
    )
    application.add_handler(close_conv)