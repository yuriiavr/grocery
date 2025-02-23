import os
import random
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не знайдено TELEGRAM_BOT_TOKEN у змінних середовища!")

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require')

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        group_code VARCHAR(255) PRIMARY KEY,
        group_name TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_groups (
        user_id VARCHAR(255),
        group_code VARCHAR(255),
        UNIQUE (user_id, group_code)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_items (
        group_code VARCHAR(255),
        item TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS personal_lists (
        user_id VARCHAR(255),
        item TEXT
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

def generate_group_code():
    return str(random.randint(100000, 999999))

def set_bot_commands(updater):
    cmds = [
        BotCommand("start", "Головна"),
        BotCommand("list", "Переглянути список"),
        BotCommand("clear", "Очистити список"),
        BotCommand("groups", "Переглянути ваші групи"),
        BotCommand("create_group", "Створити нову групу"),
        BotCommand("join_group", "Приєднатися до групи"),
        BotCommand("check_group", "Активна група")
    ]
    updater.bot.set_my_commands(cmds)

def start(update: Update, context: CallbackContext):
    context.user_data.clear()
    kbd = [
        [InlineKeyboardButton("🧍 Особистий список", callback_data="personal")],
        [InlineKeyboardButton("👥 Створити групу", callback_data="create_group")],
        [InlineKeyboardButton("🔗 Приєднатися до групи", callback_data="join_group")],
        [InlineKeyboardButton("📂 Мої групи", callback_data="groups")]
    ]
    update.message.reply_text("Оберіть опцію:", reply_markup=InlineKeyboardMarkup(kbd))

def select_personal_list(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    uid = str(q.from_user.id)
    context.user_data["active_group"] = None
    context.user_data["personal_list"] = uid
    q.edit_message_text("Ви використовуєте особистий список. Надсилайте товари.")

def ask_group_name(update: Update, context: CallbackContext):
    context.user_data["waiting_for_group_name"] = True
    context.user_data["active_group"] = None
    txt = "Введіть назву нової групи:"
    if update.callback_query:
        q = update.callback_query
        q.answer()
        q.edit_message_text(txt)
    else:
        update.message.reply_text(txt)

def finish_group_creation(update: Update, context: CallbackContext, group_name: str):
    uid = str(update.effective_user.id)
    code = generate_group_code()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO groups (group_code, group_name) VALUES (%s, %s)", (code, group_name))
    cur.execute("INSERT INTO user_groups (user_id, group_code) VALUES (%s, %s)", (uid, code))
    conn.commit()
    cur.close()
    conn.close()
    context.user_data["active_group"] = code
    update.message.reply_text(f"Групу «{group_name}» створено!\nКод: {code}\nВстановлено як активну.")

def join_group(update: Update, context: CallbackContext):
    context.user_data["waiting_for_group_code"] = True
    txt = "Введіть код групи:"
    if update.callback_query:
        q = update.callback_query
        q.answer()
        q.edit_message_text(txt)
    else:
        update.message.reply_text(txt)

def set_active_group(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    code = q.data.split("_")[2]
    context.user_data["active_group"] = code
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT group_name FROM groups WHERE group_code=%s", (code,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    name = row[0] if row else code
    q.edit_message_text(f"Ви працюєте з групою: {name}")

def handle_text(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    txt = update.message.text.strip()
    if context.user_data.get("waiting_for_group_name"):
        context.user_data["waiting_for_group_name"] = False
        finish_group_creation(update, context, txt)
        return
    if context.user_data.get("waiting_for_group_code"):
        context.user_data["waiting_for_group_code"] = False
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM groups WHERE group_code=%s", (txt,))
        exists = cur.fetchone()
        if exists:
            cur.execute("SELECT 1 FROM user_groups WHERE user_id=%s AND group_code=%s", (uid, txt))
            already = cur.fetchone()
            if not already:
                cur.execute("INSERT INTO user_groups (user_id, group_code) VALUES (%s, %s)", (uid, txt))
                context.user_data["active_group"] = txt
                cur.execute("SELECT group_name FROM groups WHERE group_code=%s", (txt,))
                r = cur.fetchone()
                name = r[0] if r else txt
                update.message.reply_text(f"Ви приєдналися до групи «{name}»!")
            else:
                update.message.reply_text("Ви вже в цій групі!")
        else:
            update.message.reply_text("Код групи не знайдено.")
        conn.commit()
        cur.close()
        conn.close()
        return
    code = context.user_data.get("active_group")
    plist = context.user_data.get("personal_list")
    if code:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO group_items (group_code, item) VALUES (%s, %s)", (code, txt.capitalize()))
        conn.commit()
        cur.close()
        conn.close()
        update.message.reply_text("Додано до групового списку.")
    elif plist:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO personal_lists (user_id, item) VALUES (%s, %s)", (uid, txt.capitalize()))
        conn.commit()
        cur.close()
        conn.close()
        update.message.reply_text("Додано у ваш особистий список.")
    else:
        update.message.reply_text("Ви не вибрали список. Введіть /start.")

def list_items(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    code = context.user_data.get("active_group")
    plist = context.user_data.get("personal_list")
    conn = get_conn()
    cur = conn.cursor()
    if code:
        cur.execute("SELECT group_name FROM groups WHERE group_code=%s", (code,))
        row = cur.fetchone()
        name = row[0] if row else code
        cur.execute("SELECT item FROM group_items WHERE group_code=%s", (code,))
        items = [r[0] for r in cur.fetchall()]
        t = f"Список покупок групи «{name}»:"
        if not items:
            update.message.reply_text("Список порожній.")
            cur.close()
            conn.close()
            return
        kb = [[InlineKeyboardButton(f"🗑 {i}", callback_data=f"remove_{code}_{i}")] for i in items]
        update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb))
    elif plist:
        cur.execute("SELECT item FROM personal_lists WHERE user_id=%s", (uid,))
        items = [r[0] for r in cur.fetchall()]
        if not items:
            update.message.reply_text("Список порожній.")
            cur.close()
            conn.close()
            return
        kb = [[InlineKeyboardButton(f"🗑 {i}", callback_data=f"remove_{uid}_{i}")] for i in items]
        update.message.reply_text("Ваш особистий список:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        update.message.reply_text("Ви не вибрали список. Введіть /start.")
    cur.close()
    conn.close()

def clear_list(update: Update, context: CallbackContext):
    uid = str(update.message.from_user.id)
    code = context.user_data.get("active_group")
    plist = context.user_data.get("personal_list")
    conn = get_conn()
    cur = conn.cursor()
    if code:
        cur.execute("DELETE FROM group_items WHERE group_code=%s", (code,))
        update.message.reply_text("Список очищено.")
    elif plist:
        cur.execute("DELETE FROM personal_lists WHERE user_id=%s", (uid,))
        update.message.reply_text("Список очищено.")
    else:
        update.message.reply_text("Ви не вибрали список.")
        cur.close()
        conn.close()
        return
    conn.commit()
    cur.close()
    conn.close()

def remove_item(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    parts = q.data.split("_")
    list_id = parts[1]
    item = "_".join(parts[2:])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM group_items WHERE group_code=%s AND item=%s", (list_id, item))
    cur.execute("DELETE FROM personal_lists WHERE user_id=%s AND item=%s", (list_id, item))
    conn.commit()
    cur.close()
    conn.close()
    q.edit_message_text(f"Видалено: {item}")
    list_items(update, context)

def list_groups(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT group_code FROM user_groups WHERE user_id=%s", (uid,))
    codes = [r[0] for r in cur.fetchall()]
    if not codes:
        text = "Ви ще не приєдналися до жодної групи."
        if update.callback_query:
            update.callback_query.edit_message_text(text)
        else:
            update.message.reply_text(text)
        cur.close()
        conn.close()
        return
    kb = []
    for c in codes:
        cur.execute("SELECT group_name FROM groups WHERE group_code=%s", (c,))
        row = cur.fetchone()
        name = row[0] if row else c
        kb.append([InlineKeyboardButton(f"📌 {name}", callback_data=f"set_group_{c}")])
    text = "Виберіть групу:"
    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    cur.close()
    conn.close()

def check_active_group(update: Update, context: CallbackContext):
    code = context.user_data.get("active_group")
    if not code:
        update.message.reply_text("Ви не вибрали групу.")
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT group_name FROM groups WHERE group_code=%s", (code,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    name = row[0] if row else code
    update.message.reply_text(f"Активна група: {name}")

def create_group_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    ask_group_name(update, context)

def join_group_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    join_group(update, context)

def list_groups_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    list_groups(update, context)

def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    set_bot_commands(updater)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("list", list_items))
    dp.add_handler(CommandHandler("clear", clear_list))
    dp.add_handler(CommandHandler("groups", list_groups))
    dp.add_handler(CommandHandler("create_group", ask_group_name))
    dp.add_handler(CommandHandler("join_group", join_group))
    dp.add_handler(CommandHandler("check_group", check_active_group))
    dp.add_handler(CallbackQueryHandler(select_personal_list, pattern="personal"))
    dp.add_handler(CallbackQueryHandler(list_groups_callback, pattern="groups"))
    dp.add_handler(CallbackQueryHandler(create_group_callback, pattern="create_group"))
    dp.add_handler(CallbackQueryHandler(join_group_callback, pattern="join_group"))
    dp.add_handler(CallbackQueryHandler(set_active_group, pattern="set_group_.*"))
    dp.add_handler(CallbackQueryHandler(remove_item, pattern="remove_.*"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
