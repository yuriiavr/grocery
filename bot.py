import os
import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ ПОМИЛКА: Не знайдено TELEGRAM_BOT_TOKEN у змінних середовища!")

DATA_FILE = "shopping_groups.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"groups": {}, "user_groups": {}, "personal_lists": {}}
    return {"groups": {}, "user_groups": {}, "personal_lists": {}}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

def generate_group_code():
    return str(random.randint(100000, 999999))

def set_bot_commands(updater):
    commands = [
        BotCommand("start", "Головна"),
        BotCommand("list", "Переглянути список"),
        BotCommand("clear", "Очистити список"),
        BotCommand("groups", "Переглянути ваші групи"),
        BotCommand("create_group", "Створити нову групу"),
        BotCommand("join_group", "Приєднатися до групи")
    ]
    updater.bot.set_my_commands(commands)

def start(update: Update, context: CallbackContext):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🧍 Особистий список", callback_data="personal")],
        [InlineKeyboardButton("👥 Створити групу", callback_data="create_group")],
        [InlineKeyboardButton("🔗 Приєднатися до групи", callback_data="join_group")],
        [InlineKeyboardButton("📂 Мої групи", callback_data="groups")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Оберіть опцію:", reply_markup=reply_markup)

def select_personal_list(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = str(query.from_user.id)
    context.user_data["active_group"] = None
    context.user_data["personal_list"] = user_id
    data["personal_lists"].setdefault(user_id, [])
    save_data()
    query.edit_message_text("✅ Ви використовуєте *особистий список*. Надсилайте товари у чат.", parse_mode="Markdown")

def create_group(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = str(query.from_user.id)
    group_code = generate_group_code()
    data["groups"][group_code] = []
    data["user_groups"].setdefault(user_id, []).append(group_code)
    save_data()
    query.edit_message_text(f"✅ Група створена! Код для приєднання: `{group_code}`", parse_mode="Markdown")

def join_group(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    update.effective_message.reply_text("✍ Введіть код групи, щоб приєднатися:")
    context.user_data["waiting_for_group_code"] = True

def handle_text(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()

    if context.user_data.get("waiting_for_group_code"):
        if text in data["groups"]:
            data["user_groups"].setdefault(user_id, []).append(text)
            save_data()
            update.message.reply_text(f"✅ Ви приєдналися до групи {text}!")
        else:
            update.message.reply_text("❌ Код групи не знайдено. Перевірте ще раз.")
        context.user_data["waiting_for_group_code"] = False
        return

    active_group = context.user_data.get("active_group")
    personal_list = context.user_data.get("personal_list")

    if active_group:
        data["groups"][active_group].append(text.capitalize())
        save_data()
        update.message.reply_text(f"✅ Додано до групового списку: {text.capitalize()}")
    elif personal_list:
        data["personal_lists"].setdefault(user_id, []).append(text.capitalize())
        save_data()
        update.message.reply_text(f"✅ Додано у ваш особистий список: {text.capitalize()}")
    else:
        update.message.reply_text("❌ Ви не вибрали список. Введіть /start, щоб вибрати.")

def list_groups(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_groups = data["user_groups"].get(user_id, [])

    if not user_groups:
        update.message.reply_text("ℹ️ Ви ще не приєдналися до жодної групи.")
        return

    keyboard = [[InlineKeyboardButton(f"📌 {code}", callback_data=f"set_group_{code}")] for code in user_groups]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🔹 Виберіть групу для роботи:", reply_markup=reply_markup)

def set_active_group(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    group_code = query.data.split("_")[2]
    context.user_data["active_group"] = group_code
    query.edit_message_text(f"✅ Ви працюєте з групою `{group_code}`", parse_mode="Markdown")

def list_items(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    active_group = context.user_data.get("active_group")
    personal_list = context.user_data.get("personal_list")

    if active_group:
        shopping_list = data["groups"].get(active_group, [])
    elif personal_list:
        shopping_list = data["personal_lists"].get(user_id, [])
    else:
        update.message.reply_text("❌ Ви не вибрали список. Введіть /start, щоб вибрати.")
        return

    if not shopping_list:
        update.message.reply_text("📭 Список покупок порожній.")
        return

    keyboard = [[InlineKeyboardButton(f"🗑 {item}", callback_data=f"remove_{active_group or user_id}_{item}")] for item in shopping_list]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🛒 *Список покупок:*", reply_markup=reply_markup, parse_mode="Markdown")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    set_bot_commands(updater)

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("list", list_items))
    dp.add_handler(CommandHandler("clear", clear_list))
    dp.add_handler(CommandHandler("groups", list_groups))
    dp.add_handler(CommandHandler("create_group", create_group))
    dp.add_handler(CommandHandler("join_group", join_group))
    dp.add_handler(CallbackQueryHandler(select_personal_list, pattern="personal"))
    dp.add_handler(CallbackQueryHandler(set_active_group, pattern="set_group_.*"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
