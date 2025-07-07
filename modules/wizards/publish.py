from modules.helpers import _clean_optional, BACK_PATTERN, _norm_inn, format_company_requisites
from modules.company_service import _get_company, _save_company
from sheets import add_request_row

# Telegram imports
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler

# Standard libraries

import re
import requests

# --------------------------------------------------------------------------
# Helper to build requisites string with bank details

def _make_requisites(inn: str, kpp: str, rs: str, bank: str, bic: str, addr: str = "") -> str:
    """Return unified requisites string including bank fields."""
    parts: list[str] = [f"ИНН {inn}", f"КПП {kpp}"]
    if rs:
        parts.append(f"р/с {rs}")
    if bank:
        parts.append(f"в банке {bank}")
    if bic:
        parts.append(f"БИК {bic}")
    if addr:
        parts.append(f"Юридический адрес: {addr}")
    return ", ".join(parts)

# --------------------------------------------------------------------------
# Helper to get int from a string like "200 000 руб"
def _clean_money(val) -> int:
    if isinstance(val, (int, float)):
        return int(val)
    digits = "".join(ch for ch in str(val) if ch.isdigit())
    return int(digits) if digits else 0

# --------------------------------------------------------------------------
# Helper: extract city name from full address
_city_bad_words = {"ул", "улица", "д", "дом", "house", "street"}

def _city_from(addr: str) -> str:
    """
    Try to extract city component from free‑form address.
    • Takes substring before first comma / em‑dash / hyphen
    • Drops common words like «ул.», «д.»
    • Returns first non‑empty word ≥ 2 chars
    """
    if not addr:
        return ""
    # split on first comma / long dash / hyphen
    import re as _re
    cut = _re.split(r"[,—\-]", addr, maxsplit=1)[0].strip()
    # remove bad prefixes
    for bad in _city_bad_words:
        if cut.lower().startswith(bad):
            cut = cut[len(bad):].strip()
    # first word that looks like a name
    parts = cut.split()
    for p in parts:
        if len(p) >= 2 and p.lower() not in _city_bad_words:
            return p.strip()
    return ""

# Backend URL configuration
try:
    from modules.settings import SERVER_URL
except ModuleNotFoundError:
    # default to actual backend
    SERVER_URL = "http://147.45.232.245:8000"


# --------------------------------------------------------------------------
# Lazy helper to show main menu without circular import
async def _safe_send_main_menu(bot, chat_id: int, role: str | None = None):
    """
    Call `send_main_menu` from the root telegram_bot module without creating an
    import cycle during module load.  Falls back to a simple message if the
    function is unavailable (e.g. renamed).
    """
    try:
        # resolve only at runtime
        from telegram_bot import send_main_menu as _real_send_main_menu  # type: ignore
        await _real_send_main_menu(bot, chat_id, role)
    except Exception:
        await bot.send_message(
            chat_id=chat_id,
            text="✅ Заявка опубликована. Главное меню доступно командой /menu."
        )
# --------------------------------------------------------------------------

# --- Entry point: publish form intro ---
async def publish_form_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 👉 сброс предыдущих данных, чтобы не тянуть старые loads/unloads
    context.user_data["new_order"] = {}

    await update.message.reply_text(
        "📝 *Шаг 1 / 11*\n"
        "Сколько автомобилей вы планируете перевезти? (числом):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_CAR_COUNT

PUB_CAR_COUNT, PUB_CAR_MODELS, PUB_VINS, \
PUB_L_ADDR, PUB_L_DATE, PUB_L_CONTACT, PUB_L_MORE, \
PUB_U_ADDR, PUB_U_DATE, PUB_U_CONTACT, PUB_U_MORE, \
PUB_BUDGET, PUB_PAY, PUB_PAY_TERMS, PUB_INN, PUB_COMPANY_CONFIRM, \
PUB_COMPANY_NAME, PUB_COMPANY_KPP, PUB_COMPANY_ADDRESS, PUB_COMPANY_ACCOUNT, PUB_COMPANY_BANK, PUB_COMPANY_BIC, \
PUB_DIR, PUB_CONFIRM = range(24)
async def pub_car_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Шаг 2: Сохраняет количество автомобилей и спрашивает марки.
    """
    text = update.message.text.strip()
    try:
        count = int(text)
    except ValueError:
        await update.message.reply_text(
            "❗️ Пожалуйста, введите только число автомобилей (цифрами):",
            reply_markup=BACK_KB
        )
        return PUB_CAR_COUNT

    context.user_data["new_order"]["car_count"] = count
    # Запрашиваем марки автомобилей
    await update.message.reply_text(
        "📝 *Шаг 2 / 11*\n"
        "Каких марок автомобили? (название бренда/модели):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_CAR_MODELS

# --- Legacy compatibility aliases (used in some back handlers) ---
PUB_ADDRS = PUB_L_ADDR
PUB_DATE  = PUB_L_DATE

# --- Back button keyboard ---
BACK_LABEL = "⬅️ Назад"
BACK_KB = ReplyKeyboardMarkup([[BACK_LABEL]], resize_keyboard=True)

# -------- MULTI‑POINT wizard helpers --------
def _init_order_lists(ctx):
    ctx.user_data.setdefault("new_order", {}).setdefault("loads", [])
    ctx.user_data["new_order"].setdefault("unloads", [])

async def _ask_load_addr(update, ctx):
    _init_order_lists(ctx)
    await update.message.reply_text(
        f"📝 *Погрузка #{len(ctx.user_data['new_order']['loads'])+1}*\n"
        "Точный адрес погрузки (город, улица, номер дома):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_L_ADDR

async def pub_cargo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # сохраняем только марки автомобилей
    context.user_data["new_order"]["car_models"] = update.message.text.strip()
    # --- сразу переходим к шагу VIN‑кодов (шаг 2 из 11) ---
    await update.message.reply_text(
        "📝 *Шаг 2 / 11*\n"
        "VIN‑коды автомобилей (через запятую, *если VIN отсутствует — напишите «нет»*):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_VINS

async def pub_vins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 3: VIN‑коды (можно несколько, через запятую)."""
    vins_raw = update.message.text.strip()
    if vins_raw.lower() in {"нет", "-", "—"}:
        vin_list = []
    else:
        vin_list = [v.strip() for v in re.split(r"[;,\\s]+", vins_raw) if v.strip()]
    context.user_data["new_order"]["vin_list"] = vin_list

    await _ask_load_addr(update, context)
    return PUB_L_ADDR

# --- LOAD steps ---
async def pub_load_addr(update, ctx):
    _init_order_lists(ctx)
    ctx.user_data.setdefault("cur_load", {})["place"] = update.message.text.strip()
    await update.message.reply_text("Дата погрузки (ДД.ММ.ГГГГ):",
                                    reply_markup=BACK_KB)
    return PUB_L_DATE

async def pub_load_date(update, ctx):
    from datetime import datetime, date

    date_str = update.message.text.strip()
    try:
        load_dt = datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        await update.message.reply_text(
            "❗️ Формат даты должен быть ДД.ММ.ГГГГ. Попробуйте ещё раз:",
            reply_markup=BACK_KB
        )
        return PUB_L_DATE

    if load_dt < date.today():
        await update.message.reply_text(
            "❗️ Дата погрузки не может быть раньше сегодняшнего дня. "
            "Введите корректную дату (ДД.ММ.ГГГГ):",
            reply_markup=BACK_KB
        )
        return PUB_L_DATE

    ctx.user_data["cur_load"]["date"] = date_str
    await update.message.reply_text("Контакт на погрузке (Имя, телефон) "
                                    "или «нет»:",
                                    reply_markup=BACK_KB)
    return PUB_L_CONTACT

async def pub_load_contact(update, ctx):
    ctx.user_data["cur_load"]["contact"] = _clean_optional(update.message.text)
    # attach VIN list (= all by default)
    ctx.user_data["cur_load"]["vins"] = ctx.user_data["new_order"].get("vin_list", [])
    ctx.user_data["new_order"]["loads"].append(ctx.user_data.pop("cur_load"))
    await update.message.reply_text("Добавить ещё точку погрузки? (да/нет)",
                                    reply_markup=BACK_KB)
    return PUB_L_MORE

async def pub_load_more(update, ctx):
    if update.message.text.strip().lower().startswith("д"):
        return await _ask_load_addr(update, ctx)
    # else -> move to first unload
    await update.message.reply_text(
        "Теперь точки *выгрузки*.\n"
        "Адрес выгрузки #1 (город, улица, дом), например «Казань, ул. Тукая 5»:",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_U_ADDR

async def pub_unload_addr(update, ctx):
    _init_order_lists(ctx)
    ctx.user_data.setdefault("cur_unload", {})["place"] = update.message.text.strip()
    await update.message.reply_text("Дата выгрузки (ДД.ММ.ГГГГ):",
                                    reply_markup=BACK_KB)
    return PUB_U_DATE

async def pub_unload_date(update, ctx):
    from datetime import datetime, date

    unload_date_str = update.message.text.strip()
    try:
        unload_dt = datetime.strptime(unload_date_str, "%d.%m.%Y").date()
    except ValueError:
        await update.message.reply_text(
            "❗️ Формат даты должен быть ДД.ММ.ГГГГ. Попробуйте ещё раз:",
            reply_markup=BACK_KB
        )
        return PUB_U_DATE

    if unload_dt < date.today():
        await update.message.reply_text(
            "❗️ Дата выгрузки не может быть раньше сегодняшнего дня. "
            "Введите корректную дату выгрузки (ДД.ММ.ГГГГ):",
            reply_markup=BACK_KB
        )
        return PUB_U_DATE

    # Проверяем, что выгрузка не раньше погрузки
    try:
        load_date_str = ctx.user_data["new_order"]["loads"][-1]["date"]
        load_dt = datetime.strptime(load_date_str, "%d.%m.%Y").date()
        if unload_dt < load_dt:
            await update.message.reply_text(
                "❗️ Дата выгрузки не может быть раньше даты погрузки. "
                "Введите корректную дату выгрузки (ДД.ММ.ГГГГ):",
                reply_markup=BACK_KB
            )
            return PUB_U_DATE
    except Exception:
        pass

    ctx.user_data["cur_unload"]["date"] = unload_date_str
    await update.message.reply_text("Контакт на выгрузке (Имя, телефон) или «нет»:",
                                    reply_markup=BACK_KB)
    return PUB_U_CONTACT

async def pub_unload_contact(update, ctx):
    ctx.user_data["cur_unload"]["contact"] = _clean_optional(update.message.text)
    ctx.user_data["cur_unload"]["vins"] = ctx.user_data["new_order"].get("vin_list", [])
    ctx.user_data["new_order"]["unloads"].append(ctx.user_data.pop("cur_unload"))
    await update.message.reply_text("Добавить ещё точку выгрузки? (да/нет)",
                                    reply_markup=BACK_KB)
    return PUB_U_MORE

async def pub_unload_more(update, ctx):
    if update.message.text.strip().lower().startswith("д"):
        await update.message.reply_text("Адрес выгрузки:",
                                        reply_markup=BACK_KB)
        return PUB_U_ADDR
    # переход к ставке
    await update.message.reply_text(
        "📝 *Ставка*\n"
        "Укажите стоимость перевозки, например _120 000 руб_",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_BUDGET

async def pub_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_order"]["budget"] = update.message.text.strip()

    kb_vat = InlineKeyboardMarkup([
        [InlineKeyboardButton("С НДС",  callback_data="pay_vat"),
         InlineKeyboardButton("Без НДС", callback_data="pay_novat")]
    ])
    await update.message.reply_text(
        "📝 *Шаг 7 / 11*\n"
        "Выберите форму оплаты:",
        parse_mode="Markdown",
        reply_markup=kb_vat
    )
    return PUB_PAY

async def pub_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_order"]["pay_terms"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 *Шаг 8 / 11*\n"
        "Введите ИНН компании‑заказчика:",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_INN

# --- Handler for payment terms entry step in publishing wizard ---
async def pub_pay_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Saves entered payment terms and moves to INN step.
    """
    text_raw = update.message.text.strip()
    context.user_data["new_order"]["pay_terms"] = text_raw

    # determine payment_type from text
    if "налич" in text_raw.lower():
        context.user_data["new_order"]["payment_type"] = "cash"
    else:
        # if not already set by buttons, default to noncash
        context.user_data["new_order"].setdefault("payment_type", "noncash")

    # Ask for INN
    await update.message.reply_text(
        "📝 *Шаг 9 / 11*\n"
        "Введите ИНН компании‑заказчика:",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_INN

# ---------- Handler for VAT buttons ("pay_vat", "pay_novat") ----------
async def pub_pay_choice(update: Update, ctx):
    """
    Callback handler for inline buttons «С НДС» / «Без НДС».
    Saves only VAT flag *and* sets default `payment_type="noncash"`.
    Real text of payment terms пользователь введёт на следующем шаге.
    """
    q = update.callback_query
    await q.answer()

    choice = q.data  # "pay_vat" or "pay_novat"
    o = ctx.user_data.setdefault("new_order", {})

    # --- set VAT flag ---
    if choice == "pay_vat":
        o["vat"] = True
    elif choice == "pay_novat":
        o["vat"] = False
    else:
        o["vat"] = True   # fallback: treat as "с НДС"

    # Всегда считаем, что кнопка = безналичный расчет,
    # реальное уточнение (нал/безнал) будет в следующем шаге.
    o["payment_type"] = "noncash"

    # prompt next step (user enters free‑form payment terms)
    await q.edit_message_text("Форма оплаты принята.")

    vat_label = "С НДС" if o["vat"] else "Без НДС"
    prompt_text = (
        "📝 *Шаг 8 / 11*\n"
        f"Вы выбрали: *{vat_label}*.\n"
        "Введите условия оплаты (пример: *100% безнал, 3 банковских дня*):"
    )
    await ctx.bot.send_message(
        chat_id=q.from_user.id,
        text=prompt_text,
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_PAY_TERMS

async def pub_inn(update: Update, ctx):
    import re
    # 1) Оставляем из введённого только цифры
    raw_digits = re.sub(r"\D", "", update.message.text)
    # 2) Если ровно 10 или 12 цифр, считаем это «валидным ИНН»
    if len(raw_digits) in (10, 12):
        inn = raw_digits
    else:
        # иначе сохраняем то, что есть (например, 8 или 9 цифр)
        inn = raw_digits

    # сохраняем в контекст под двумя ключами, чтобы далее упростить логику
    ctx.user_data["new_order"]["inn"] = inn
    ctx.user_data["new_order"]["cust_inn"] = inn

    # DEBUG: посмотрим, что именно хранится
    print(f"[DEBUG pub_inn] raw input: '{update.message.text}' → digits: '{raw_digits}', using INN='{inn}'")

    company = await _get_company(inn)
    print(f"[DEBUG pub_inn] _get_company({inn}) → {company if company else '<нет записей>'}")
    if company:
        ctx.user_data["new_order"].update({
            "cust_company_name": company.get("name", ""),
            "cust_kpp":          company.get("kpp", ""),
            "cust_address":      company.get("address", ""),
            "cust_account":      company.get("bank_rs", ""),
            "cust_bank_name":    company.get("bank_name", ""),
            "cust_bic":          company.get("bank_bic", ""),
            "cust_requisites":   format_company_requisites(company),
            "cust_director":     company.get("director", ""),
            "cust_account":      company.get("bank_rs", ""),
            "cust_bank_name":    company.get("bank_name", ""),
            "cust_bic":          company.get("bank_bic", ""),
        })
        # Clean and force address from company (for saved companies)
        if company.get("address"):
            ctx.user_data["new_order"]["cust_address"] = company.get("address", "")
        n = ctx.user_data["new_order"]
        n["cust_requisites"] = _make_requisites(
            n.get("cust_inn", n.get("inn", "")),
            n.get("cust_kpp", ""),
            n.get("cust_account", ""),
            n.get("cust_bank_name", ""),
            n.get("cust_bic", ""),
            n.get("cust_address", "")
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="cmp_yes"),
             InlineKeyboardButton("✏️ Нет", callback_data="cmp_no")]
        ])
        await update.message.reply_text(
            f"🏢 Компания «{company['name']}» найдена.\n"
            "Использовать сохранённые реквизиты?",
            reply_markup=kb
        )
        return PUB_COMPANY_CONFIRM

    await update.message.reply_text(
        "📝 Название компании-заказчика:",
        reply_markup=BACK_KB
    )
    return PUB_COMPANY_NAME

# ---- New handlers for step-by-step company data entry ----
async def pub_company_name(update: Update, ctx):
    ctx.user_data["new_order"]["cust_company_name"] = update.message.text
    await update.message.reply_text("Введите КПП:")
    return PUB_COMPANY_KPP

async def pub_company_kpp(update: Update, ctx):
    ctx.user_data["new_order"]["cust_kpp"] = update.message.text
    await update.message.reply_text("Введите юридический адрес:")
    return PUB_COMPANY_ADDRESS

async def pub_company_address(update: Update, ctx):
    ctx.user_data["new_order"]["cust_address"] = update.message.text
    await update.message.reply_text("Введите расчётный счёт:")
    return PUB_COMPANY_ACCOUNT

async def pub_company_account(update: Update, ctx):
    import re
    clean_rs = re.sub(r"\D", "", update.message.text)
    if len(clean_rs) < 15 or len(clean_rs) > 26:
        await update.message.reply_text(
            "Расчётный счёт должен содержать 15–26 цифр. Введите корректно:",
            reply_markup=BACK_KB
        )
        return PUB_COMPANY_ACCOUNT

    ctx.user_data["new_order"]["cust_account"] = clean_rs
    await update.message.reply_text("Введите наименование банка:")
    return PUB_COMPANY_BANK

async def pub_company_bank(update: Update, ctx):
    ctx.user_data["new_order"]["cust_bank_name"] = update.message.text
    await update.message.reply_text("Введите БИК:")
    return PUB_COMPANY_BIC

async def pub_company_bic(update: Update, ctx):
    import re
    clean_bic = re.sub(r"\D", "", update.message.text)
    if len(clean_bic) not in (8, 9):
        await update.message.reply_text(
            "БИК должен содержать 8 или 9 цифр. Введите корректно:",
            reply_markup=BACK_KB
        )
        return PUB_COMPANY_BIC

    ctx.user_data["new_order"]["cust_bic"] = clean_bic
    data = ctx.user_data["new_order"]
    data["cust_requisites"] = _make_requisites(
        data.get("inn", ""),
        data.get("cust_kpp", ""),
        data.get("cust_account", ""),
        data.get("cust_bank_name", ""),
        clean_bic,
        data.get("cust_address", "")
    )
    return await pub_company_finish(update, ctx)

async def pub_company_finish(update: Update, ctx):
    data = ctx.user_data["new_order"]

    # Формируем полную карточку компании с ФИО директора (если оно уже есть)
    new_company = {
        "inn": data.get("inn", ""),
        "name": data.get("cust_company_name", ""),
        "kpp": data.get("cust_kpp", ""),
        "address": data.get("cust_address", ""),
        "bank_rs":   data.get("cust_account", ""),
        "bank_name": data.get("cust_bank_name", ""),
        "bank_bic":  data.get("cust_bic", ""),
        "director":  data.get("cust_director", ""),  # директор уже на этом шаге может быть пустым — это ок
    }

    # Всегда сохраняем полный комплект, включая директора (если уже есть)
    await _save_company(new_company)

    # Обновляем строку requisites для заказа (если директор еще не введён — она всё равно будет валидна)
    data["cust_requisites"] = _make_requisites(
        new_company["inn"],
        new_company["kpp"],
        new_company["bank_rs"],
        new_company["bank_name"],
        new_company["bank_bic"],
        new_company["address"]
    )

    await update.message.reply_text(
        "✅ Компания сохранена.\n"
        "📝 *Шаг 10 / 11*\n"
        "Введите ФИО директора компании‑заказчика:",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_DIR
# ---------- confirm company from cache ----------
async def pub_confirm_company(update: Update, ctx):
    q = update.callback_query
    await q.answer()

    # 'Да' — реквизиты остаются
    if q.data == "cmp_yes":
        n = ctx.user_data["new_order"]
        company = None
        if n.get("inn"):
            company = await _get_company(n.get("inn"))
        # Ensure cust_address is set from company if available, then build requisites
        if not n.get("cust_address") and company and company.get("address"):
            n["cust_address"] = company.get("address", "")
        # --- ensure we pick director from the saved company object ---
        if company:
            director_raw = (company.get("director") or "").strip()
            # overwrite any garbage (e.g., previous bot prompt) in the wizard data
            n["cust_director"] = director_raw
            n["cust_sign_name"] = director_raw
            # optional alias for templates that expect a different key
            n["customer_director"] = director_raw
        n["cust_requisites"] = _make_requisites(
            n.get("cust_inn", n.get("inn", "")),
            n.get("cust_kpp", ""),
            n.get("cust_account", ""),
            n.get("cust_bank_name", ""),
            n.get("cust_bic", ""),
            n.get("cust_address", "")
        )
        n["cust_sign_name"] = n.get("cust_director", "")
        # если директор уже известен — сразу показываем превью (без лишнего вызова pub_dir)
        if n.get("cust_director"):
            prev = (
                f"🚚 *Превью*\n"
                f"Компания‑заказчик: {n.get('cust_company_name','—')}\n"
                f"{n.get('cargo','—')}\n"
                f"{n.get('route','—')}\n"
                f"VIN: {', '.join(n.get('vin_list', [])) or '—'}\n"
                f"Погрузка: {n.get('addresses','—')}\n"
                f"Контакт погрузка: {n.get('contact_load','—')}\n"
                f"Контакт выгрузка: {n.get('contact_unload','—')}\n"
                f"Дата(ы): {n.get('date','—')}\n"
                f"Ставка: {n.get('budget','—')}\n"
                f"Форма оплаты: {n.get('pay_terms','—')}\n"
                f"🏢 Реквизиты:\n{n.get('cust_requisites', '—')}\n"
                f"👤 Директор: {n.get('cust_director','—')}\n\nОпубликовать?"
            )
            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ Опубликовать", callback_data="pub_yes"),
                  InlineKeyboardButton("✖️ Отмена", callback_data="pub_cancel")]]
            )
            await q.message.reply_text(prev, parse_mode="Markdown", reply_markup=kb)
            return PUB_CONFIRM
        # иначе спрашиваем реквизиты вручную
        await q.edit_message_text(
            "📝 *Шаг 10 / 11*\n"
            "Введите ФИО директора компании-заказчика:",
            parse_mode="Markdown",
            reply_markup=BACK_KB
        )
        return PUB_DIR

    # очистим ранее подставленные поля, чтобы начать ввод заново
    for k in list(ctx.user_data["new_order"].keys()):
        if k.startswith("cust_"):
            ctx.user_data["new_order"].pop(k, None)
    # отправляем новое сообщение (reply_text), т.к. edit_message_text нельзя
    await q.message.reply_text(
        "Название компании-заказчика:",
        reply_markup=BACK_KB
    )
    return PUB_COMPANY_NAME

# --- Handler for customer director step ---
async def pub_dir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ------------------- validate director FIO -------------------
    director_input = update.message.text.strip()

    # допускаем русские или латинские буквы, фамилия + инициалы "Иванов И. И." или "Иванов И."
    import re
    pattern = r"^[A-Za-zА-Яа-яЁё][-A-Za-zА-Яа-яЁё']+\s+[A-Za-zА-ЯЁ]\.(?:\s?[A-Za-zА-ЯЁ]\.)?$"
    if not re.match(pattern, director_input):
        await update.message.reply_text(
            "❗️ Введите ФИО директора в формате «Фамилия И. И.» (инициалы с точками).",
            reply_markup=BACK_KB
        )
        return PUB_DIR  # остаёмся на этом шаге

    context.user_data["new_order"]["cust_director"] = director_input
    o = context.user_data["new_order"]
    o["cust_sign_name"] = o["cust_director"]

    print("=== Сохраняю новую компанию ===")
    for k in ("inn", "cust_inn", "cust_kpp", "cust_company_name", "cust_director", "cust_bank_name", "cust_account", "cust_bic", "cust_address"):
        print(k, "=", o.get(k, ""))
    print("===============================")

    await _save_company({
        "inn": o.get("inn", ""),
        "kpp": o.get("cust_kpp", ""),
        "name": o.get("cust_company_name", ""),
        "director": o.get("cust_director", ""),
        "bank_name": o.get("cust_bank_name", ""),
        "bank_rs": o.get("cust_account", ""),
        "bank_bic": o.get("cust_bic", ""),
        "address": o.get("cust_address", "")
    })
    # дальше остальной код...
    prev = (f"🚚 *Превью*\n"
            f"Компания-заказчик: {o.get('cust_company_name','—')}\n"
            f"{o['cargo']}\n"
            f"{o.get('route', '—')}\n"
            f"VIN: {', '.join(o.get('vin_list', [])) or '—'}\n"
            f"Погрузка: {o.get('addresses','—')}\n"
            f"Контакт погрузка: {o.get('contact_load','—')}\n"
            f"Контакт выгрузка: {o.get('contact_unload','—')}\n"
            f"Дата(ы): {o.get('date','—')}\n"
            f"Ставка: {o['budget']}\n"
            f"Форма оплаты: {'с НДС' if o.get('vat') else 'без НДС'}; {o.get('pay_terms','')}\n"
            f"🏢 Реквизиты:\n{o.get('cust_requisites', '—')}\n"
            f"👤 Директор: {o.get('cust_director','—')}\n\nОпубликовать?")
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Опубликовать", callback_data="pub_yes"),
          InlineKeyboardButton("✖️ Отмена", callback_data="pub_cancel")]]
    )
    await update.message.reply_text(prev, parse_mode="Markdown", reply_markup=kb)
    return PUB_CONFIRM

async def pub_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "pub_cancel":
        await q.edit_message_text("🚫 Публикация отменена.")
        # вернуть клавиатуру меню
        try:
            prof = requests.get(f"{SERVER_URL}/agent/{q.from_user.id}", timeout=4).json()
            role = prof.get("agent_type")
        except Exception:
            role = None
        await _safe_send_main_menu(context.bot, q.from_user.id, role)
        return ConversationHandler.END

    o = context.user_data["new_order"]
    import re
    # ---------- build structured fields ----------
    vin_list = o.get("vin_list", [])
    loads   = o.get("loads", [])
    unloads = o.get("unloads", [])
    # --- ensure both loads and unloads are present ---
    if not loads or not unloads:
        await q.edit_message_text(
            "❗️ Необходимо указать минимум одну точку погрузки И одну точку выгрузки.\n"
            "Исправьте адреса и попробуйте опубликовать снова.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # --- build multi-point loads and unloads summary ---
    load_lines = [
        f"{i+1}. {item['place']} ({item['date']})"
        for i, item in enumerate(loads)
    ]
    text_loads = "Погрузка:\n" + "\n".join(load_lines) if loads else ""

    unload_lines = [
        f"{i+1}. {item['place']} ({item['date']})"
        for i, item in enumerate(unloads)
    ]
    text_unloads = "Выгрузка:\n" + "\n".join(unload_lines) if unloads else ""

    # --- build route using robust _city_from helper ---
    origin = _city_from(loads[0].get("place", "")) if loads else ""
    dest   = _city_from(unloads[0].get("place", "")) if unloads else ""

    route = f"{origin} — {dest}" if origin and dest else origin or dest

    date_str = ""
    if loads and unloads:
        date_str = f"{loads[0].get('date', '')} – {unloads[0].get('date', '')}"
    elif loads:
        date_str = loads[0].get('date', '')
    elif unloads:
        date_str = unloads[0].get('date', '')

    # --- build a structured message with clearly marked loads and unloads ---
    sections = []
    if loads:
        sections.append("📍 Пункты погрузки:")
        for i, item in enumerate(loads, start=1):
            sections.append(f"  {i}. {item['place']} ({item['date']})")
        sections.append("")

    if unloads:
        sections.append("📍 Пункты выгрузки:")
        for i, item in enumerate(unloads, start=1):
            sections.append(f"  {i}. {item['place']} ({item['date']})")
        sections.append("")

    cargo_text = o.get("cargo", "")
    if cargo_text:
        sections.append(f"🚚 Груз: {cargo_text}")

    budget_text = o.get("budget", "")
    if budget_text:
        sections.append(f"💵 Цена: {budget_text}")

    pay_terms_text = o.get("pay_terms", "")
    if pay_terms_text:
        sections.append(f"💳 Условия оплаты: {pay_terms_text}")

    msg = "\n".join(sections)

    # ---------- cars list  ---------------------------------
    # Хотим гарантированно передать brand/model, чтобы уведомление Драйвера
    # показывало «N × Brand Model», даже если ввод был в произвольной форме.

    cargo_descr = o.get("cargo", "")
    brand = model = ""
    qty = 0

    # 1) Попытка распарсить «…, Lada Granta, 3 авто …»
    m = re.search(r"(?:,|^)\s*([^,]+?)\s*,\s*(\d+)\s+авто", cargo_descr, re.I)

    # 2) Попытка «3 авто Haval H3»
    if not m:
        m = re.search(r"(\d+)\s+авто\s+(.+)", cargo_descr, re.I)

    if m:
        if m.lastindex == 2:
            # оба паттерна дают две группы qty/brand_model
            if m.re.pattern.startswith("(?:,|^"):
                brand_model_raw, qty_str = m.group(1), m.group(2)
            else:
                qty_str, brand_model_raw = m.group(1), m.group(2)
            qty = int(qty_str)
            parts = brand_model_raw.strip().split(maxsplit=1)
            brand = parts[0]
            model = parts[1] if len(parts) > 1 else ""

    # 3) Fallback: если не нашли по шаблону, попробуем наивно.
    if not brand:
        # убираем слова "авто", цифры, запятые
        tmp = re.sub(r"\b\d+\b|\bавто\b|,", " ", cargo_descr, flags=re.I)
        tmp = " ".join(tmp.split())        # нормализуем пробелы
        parts = tmp.split(maxsplit=2)
        if parts:
            brand = parts[0]
            model = " ".join(parts[1:]) if len(parts) > 1 else ""

    # 4) qty по умолчанию = len(vin_list) (если оно >0 и qty ещё не найден)
    if not qty and o.get("vin_list"):
        qty = len(o["vin_list"])

    vin_list = o.get("vin_list", [])

    cars: list[dict] = []
    if vin_list:
        # если есть VIN-ы, дублируем brand/model в каждый
        for v in vin_list:
            car: dict = {"vin": v}
            if brand:
                car["brand"] = brand
            if model:
                car["model"] = model
            cars.append(car)
    elif qty:
        # VIN-ов нет, но известно количество
        cars = [{"brand": brand, "model": model} for _ in range(qty)]
    # если ничего не смогли определить, оставляем пустой список
    # --- validate route: must have both origin and dest ---
    if not origin or not dest:
        await q.edit_message_text(
            "❗️ Маршрут не распознан. Проверьте города погрузки и выгрузки.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    # ------- Build human‑readable message BEFORE POST -------
    cars_descr = ""
    if o.get("car_count") and o.get("car_models"):
        cars_descr = f"{o['car_count']}×{o['car_models']}".strip()
    elif o.get("cargo"):
        cars_descr = o["cargo"].strip()
    # remove commas so backend doesn't split route on them
    cars_descr = cars_descr.replace(",", " ")

    budget_text = re.sub(",", " ", o.get("budget", "")).strip()
    # Build "Маршрут • Груз — Цена"
    msg_parts = [route]
    if cars_descr:
        msg_parts.append(f"• {cars_descr}")
    if budget_text:
        msg_parts.append(f"— {budget_text}")
    human_message = " ".join(msg_parts).strip()
    # numeric price for driver lists / push
    final_amt = _clean_money(budget_text)

    r = requests.post(
        f"{SERVER_URL}/add_order",
        json={
            "status": "active",            # <-- гарантируем стартовый статус
            "telegram_id": q.from_user.id,
            "message": human_message,
            "cargo": cars_descr,
            "final_amt":  final_amt,
            "cust_company_name": o.get("cust_company_name", ""),
            "cust_kpp":          o.get("cust_kpp", ""),
            "cust_address":      o.get("cust_address", ""),
            "cust_account":      o.get("cust_account", ""),
            "cust_bank_name":    o.get("cust_bank_name", ""),
            "cust_bic":          o.get("cust_bic", ""),
            "cust_requisites":   o.get("cust_requisites", ""),
            "cust_director":     o.get("cust_director", ""),
            "cust_sign_name":    o.get("cust_director", ""),
            "cust_name":         o.get("cust_company_name", ""),   # ← добавили alias
            "vat":        o.get("vat", True),
            "pay_terms":  o.get("pay_terms", ""),
            "cars":     cars,
            "loads":    loads,
            "unloads":  unloads,
        }
    )
    # --- ALWAYS save the latest company with all director/bank fields after successful add_order ---
    await _save_company({
        "inn": o.get("inn", ""),
        "kpp": o.get("cust_kpp", ""),
        "name": o.get("cust_company_name", ""),
        "director": o.get("cust_director", ""),
        "bank_name": o.get("cust_bank_name", ""),
        "bank_rs": o.get("cust_account", ""),
        "bank_bic": o.get("cust_bic", ""),
        "address": o.get("cust_address", "")
    })

    if r.status_code == 200:
        res = r.json()
        # extract numeric order id from message "Ваш номер заявки: N"
        import re as _re
        m_id = _re.search(r"\d+", res.get("message", ""))
        order_id = int(m_id.group(0)) if m_id else 0
        try:
            prof = requests.get(f"{SERVER_URL}/agent/{q.from_user.id}", timeout=4).json()
        except Exception:
            prof = {}
        try:
            add_request_row({
                "id": order_id,
                "date": date_str,
                "navigator": prof.get("name", ""),
                "customer_company": o.get("cust_company_name", ""),
                "route": route,
                "cargo": cars_descr,
                "orig_price": _clean_money(budget_text),
            })
        except Exception as e:
            print("Sheets add_request_row error:", e)
        kb_cancel = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Отменить", callback_data=f"nv_cancel_{order_id}")]]
        )
        await q.edit_message_text(
            f"✅ {res['status']}\n{res['message']}",
            reply_markup=kb_cancel
        )
        # вернуть клавиатуру меню
        try:
            prof = requests.get(f"{SERVER_URL}/agent/{q.from_user.id}", timeout=4).json()
            role = prof.get("agent_type")
        except Exception:
            role = None
        # Отправка ободряющего сообщения и мини-инструкции
        try:
            name = prof.get("name", "").split()[0] or "друг"
        except Exception:
            name = "друг"
        from telegram_bot import ENCOURAGE
        import random
        msg = (
            f"{random.choice(ENCOURAGE)}\n\n"
            "✅ Заявка принята и отправлена водителям!\n"
            "Мы запустили поиск надёжного исполнителя. "
            "📲 Как только водитель подтвердит перевозку, вы получите уведомление."
        )
        await context.bot.send_message(chat_id=q.from_user.id, text=msg)
        # очистим данные визарда, чтобы новая заявка начиналась «с нуля»
        context.user_data["new_order"] = {}
        await _safe_send_main_menu(context.bot, q.from_user.id, role)
        return ConversationHandler.END
    elif r.status_code == 400 and "Укажите маршрут" in r.text:
        # backend вернул ошибку формата маршрута
        await q.edit_message_text(
            "❗️ Маршрут не распознан. Проверьте адреса погрузки и выгрузки.\n"
            "Вернитесь к шагу адресов и укажите города в формате «ГородA — ГородB».",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    else:
        await q.edit_message_text(f"❌ Ошибка: {r.text}")
    return ConversationHandler.END

# ---------- Back handlers for publish wizard ----------
async def back_from_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # return to car count question
    await update.message.reply_text(
        "📝 *Шаг 1 / 11*\n"
        "Сколько автомобилей вы планируете перевезти? (числом):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_CAR_COUNT

async def back_from_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Шаг 6 / 11*\n"
        "Контактное лицо на погрузке/выгрузке (имя и телефон):",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_U_CONTACT

# --- Handler for going back from pay step in publishing wizard ---
async def back_from_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Шаг 7 / 11*\n"
        "Ставка?  _120 000 руб_",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_BUDGET


async def back_from_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Шаг 5 / 11*\n"
        "Когда погрузка и когда выгрузка?  (пример «12.05 – 15.05»)",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_DATE

async def back_from_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Шаг 4 / 11*\n"
        "Точные адреса погрузки и выгрузки?\n"
        "_Москва, ул. Ленина 1 — Казань, ул. Тукая 5_",
        parse_mode="Markdown",
        reply_markup=BACK_KB
    )
    return PUB_ADDRS

async def back_to_publish_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return from wizard to publish menu without circular import at module load."""
    from telegram_bot import show_publish_menu as _show_publish_menu   # local import
    await _show_publish_menu(update, context)
    return ConversationHandler.END

 # ---------- Navigator cancels own order ----------
async def nav_cancel_order(update: Update, ctx):
    """
    Callback handler for button  «❌ Отменить».
    Sets order status to `cancelled`.
    """
    q = update.callback_query
    await q.answer()
    try:
        order_id = int(q.data.split("_")[2])          # pattern nv_cancel_<id>
    except Exception:
        await q.edit_message_text("⚠️ Не удалось определить ID заявки.")
        return

    try:
        requests.patch(
            f"{SERVER_URL}/admin/order/{order_id}/status/cancelled",
            timeout=5
        )
        await q.edit_message_text(f"✅ Заявка №{order_id} отменена.")
    except Exception as e:
        await q.edit_message_text(f"❌ Ошибка отмены: {e}")

__all__ = (
    # states
    "PUB_CAR_COUNT", "PUB_CAR_MODELS", "PUB_VINS", "PUB_L_ADDR", "PUB_L_DATE", "PUB_L_CONTACT", "PUB_L_MORE",
    "PUB_U_ADDR", "PUB_U_DATE", "PUB_U_CONTACT", "PUB_U_MORE",
    "PUB_BUDGET", "PUB_PAY", "PUB_INN",
    "PUB_COMPANY_NAME", "PUB_COMPANY_KPP", "PUB_COMPANY_ADDRESS", "PUB_COMPANY_ACCOUNT", "PUB_COMPANY_BANK", "PUB_COMPANY_BIC",
    "PUB_DIR", "PUB_CONFIRM", "PUB_COMPANY_CONFIRM",
    # handlers & helpers
    "_init_order_lists", "_ask_load_addr",
    "pub_car_count", "pub_cargo", "pub_vins", "pub_load_addr", "pub_load_date",
    "pub_load_contact", "pub_load_more", "pub_unload_addr", "pub_unload_date",
    "pub_unload_contact", "pub_unload_more", "pub_budget", "pub_pay",
    "pub_inn", "pub_company_name", "pub_company_kpp", "pub_company_address",
    "pub_company_account", "pub_company_bank", "pub_company_bic", "pub_company_finish",
    "pub_dir", "pub_confirm",
    "back_from_route", "back_from_budget", "back_from_pay",
    "back_from_contacts", "back_from_date", "back_to_publish_menu", "pub_confirm_company",
    "nav_cancel_order",
    # legacy aliases
    "PUB_ADDRS", "PUB_DATE",
    
)