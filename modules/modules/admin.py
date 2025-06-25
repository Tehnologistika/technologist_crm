ADMIN_PANEL_LABEL = "👑 Админ‑панель"
BONUS_CALC_LABEL  = "🧮 Калькулятор бонусов"
EXEC_BONUS_RATE   = 0.03   # 3 % для Драйвера
CUST_BONUS_RATE   = 0.05   # 5 % для Навигатора
# ---------- Admin UI labels ----------
ADMIN_CURRENT_LABEL = "📦 Актуальные"
ADMIN_ARCHIVE_LABEL = "📚 Архив"
TOKEN_MENU_LABEL   = "🗝️ Создать токен"
TOKEN_CUST_LABEL   = "🧭 Токен Навигатора"
TOKEN_EXEC_LABEL   = "🚚 Токен Драйвера"
BOT_USERNAME       = "TechnologisticaCRM_Bot" 

STATUS_LABELS = {
    "active":      "🟡 Активна",
    "confirmed":   "✅ Подтверждена",
    "in_progress": "🔄 В работе",
    "done":        "🟢 Исполнена",
    "paid":        "💰 Оплачена",
}

CURRENT_STATUSES = ("active", "confirmed", "in_progress", "done")
ARCHIVE_STATUSES = ("paid",)
ALL_STATUSES = CURRENT_STATUSES + ARCHIVE_STATUSES

 # ---------- ADMIN callback handlers ----------
async def admin_choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.split("_")[-1]   # current | archive
    statuses = ALL_STATUSES
    buttons = [
        [InlineKeyboardButton(STATUS_LABELS[s], callback_data=f"admin_status_{s}_0")]
        for s in statuses
    ]
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back_main")])
    await query.edit_message_text(
        "Выберите статус:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def admin_list_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    page = int(parts[-1])
    status = "_".join(parts[2:-1])   # join the middle pieces (handles "in_progress")
    try:
        rows = requests.get(
            f"{SERVER_URL}/admin/orders",
            params={"status": status, "page": page},
            timeout=5
        ).json()
    except Exception:
        rows = []
    if not rows:
        await query.edit_message_text("Пусто.", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("◀️ Назад", callback_data=f"admin_cat_{'current' if status in CURRENT_STATUSES else 'archive'}")]]
        ))
        return
    buttons = [
        [InlineKeyboardButton(f"[{r['id']}] {r['message']}", callback_data=f"admin_order_{r['id']}_{status}")]
        for r in rows
    ]
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"admin_status_{status}_{page-1}"))
    if len(rows) == 15:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"admin_status_{status}_{page+1}"))
    if nav_row:
        buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data=f"admin_cat_{'current' if status in CURRENT_STATUSES else 'archive'}")])
    await query.edit_message_text(
        f"Заявки со статусом {STATUS_LABELS[status]} (стр. {page+1}):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def admin_order_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    oid = int(parts[2])
    status = "_".join(parts[3:])
    try:
        o = requests.get(f"{SERVER_URL}/admin/order/{oid}", timeout=5).json()
    except Exception as e:
        await query.edit_message_text(f"Ошибка: {e}")
        return
    text = (f"*#{o['id']}*  {o['message']}\n"
            f"Статус: {STATUS_LABELS[o['status']]}\n\n"
            f"💵 Оригинал: {fmt_money(o['original_amt'])} ₽\n"
            f"🚚 Исполнителю: {fmt_money(o['final_amt'])} ₽\n"
            f"🏆 Бонус заказчика: {fmt_money(o['reward_cust'])} ₽\n"
            f"🏆 Бонус исполнителя: {fmt_money(o['reward_exec'])} ₽\n"
            f"💼 Платформа: {fmt_money(o['fee_platform'])} ₽\n\n"
            f"👤 Водитель: {o.get('driver_fio','—')}")
    buttons = [
        [InlineKeyboardButton("Изменить статус", callback_data=f"admin_change_{oid}_{status}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"admin_status_{status}_0")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def admin_change_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    oid = int(parts[2])
    cur_status = "_".join(parts[3:])
    other_statuses = [s for s in STATUS_LABELS if s != cur_status]
    buttons = [
        [InlineKeyboardButton(STATUS_LABELS[s], callback_data=f"admin_set_{oid}_{s}_{cur_status}")]
        for s in other_statuses
    ]
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data=f"admin_order_{oid}_{cur_status}")])
    await query.edit_message_text("Выберите новый статус:",
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def admin_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    oid = int(parts[2])
    # last part is previous status, everything between is new_status
    prev_status = parts[-1]
    new_status = "_".join(parts[3:-1])
    try:
        requests.patch(
            f"{SERVER_URL}/admin/order/{oid}/status/{new_status}",
            timeout=5
        )
    except Exception as e:
        await query.edit_message_text(f"Ошибка: {e}")
        return

    # --- fetch the updated order and refresh card ---
    try:
        o = requests.get(f"{SERVER_URL}/admin/order/{oid}", timeout=5).json()
    except Exception as e:
        await query.edit_message_text(f"Ошибка: {e}")
        return

    text = (
        f"*#{o['id']}*  {o['message']}\n"
        f"Статус: {STATUS_LABELS[o['status']]}\n\n"
        f"💵 Оригинал: {fmt_money(o['original_amt'])} ₽\n"
        f"🚚 Исполнителю: {fmt_money(o['final_amt'])} ₽\n"
        f"🏆 Бонус заказчика: {fmt_money(o['reward_cust'])} ₽\n"
        f"🏆 Бонус исполнителя: {fmt_money(o['reward_exec'])} ₽\n"
        f"💼 Платформа: {fmt_money(o['fee_platform'])} ₽\n\n"
        f"👤 Водитель: {o.get('driver_fio','—')}"
    )

    # rebuild buttons with new status value
    other_statuses = [s for s in STATUS_LABELS if s != o['status']]
    buttons = [
        [InlineKeyboardButton(STATUS_LABELS[s],
                              callback_data=f"admin_set_{oid}_{s}_{o['status']}")]
        for s in other_statuses
    ]
    buttons.append([InlineKeyboardButton("◀️ Назад",
                                         callback_data=f"admin_status_{o['status']}_0")])

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Admin back to main menu handler ---
async def admin_back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в корень админ‑панели (выбор категории)."""
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(ADMIN_CURRENT_LABEL, callback_data="admin_cat_current")],
         [InlineKeyboardButton(ADMIN_ARCHIVE_LABEL,  callback_data="admin_cat_archive")]]
    )
    await query.edit_message_text(
        "Выберите категорию заявок:",
        reply_markup=kb
    )

__all__ = (
    "ADMIN_PANEL_LABEL", "ADMIN_CURRENT_LABEL", "ADMIN_ARCHIVE_LABEL",
    "TOKEN_MENU_LABEL", "TOKEN_CUST_LABEL", "TOKEN_EXEC_LABEL",
    "STATUS_LABELS",
    "admin_choose_category", "admin_list_status", "admin_order_card",
    "admin_change_status_menu", "admin_set_status", "admin_back_main"
)