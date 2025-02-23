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
                return {"groups": {}, "user_groups": {}, "personal_lists": {}, "group_names": {}}
    return {"groups": {}, "user_groups": {}, "personal_lists": {}, "group_names": {}}

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
        BotCommand("join_group", "Приєднатися до групи"),
        BotCommand("check_group", "Активна група")
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

def ask_group_name(update: Update, context: CallbackContext):
    context.user_data["waiting_for_group_name"] = True
    context.user_data["active_group"] = None
    text = "Введіть назву нової групи:"
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text)
    else:
        update.message.reply_text(text)

def finish_group_creation(update: Update, context: CallbackContext, group_name: str):
    user_id = str(update.effective_user.id)
    group_code = generate_group_code()
    data["groups"][group_code] = []
    data["user_groups"].setdefault(user_id, []).append(group_code)
    data["group_names"][group_code] = group_name
    save_data()
    context.user_data["active_group"] = group_code
    update.message.reply_text(
        f"✅ Групу \"{group_name}\" створено!\nКод для приєднання: `{group_code}`\nЦя група тепер встановлена як активна.",
        parse_mode="Markdown"
    )

def join_group(update: Update, context: CallbackContext):
    text = "✍ Введіть код групи, щоб приєднатися:"
    context.user_data["waiting_for_group_code"] = True
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text)
    else:
        update.message.reply_text(text)

def set_active_group(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    group_code = query.data.split("_")[2]
    context.user_data["active_group"] = group_code
    group_name = data["group_names"].get(group_code, group_code)
    query.edit_message_text(f"✅ Ви працюєте з групою: {group_name}")

def handle_text(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()
    if context.user_data.get("waiting_for_group_name"):
        group_name = text
        context.user_data["waiting_for_group_name"] = False
        finish_group_creation(update, context, group_name)
        return
    if context.user_data.get("waiting_for_group_code"):
        if text in data["groups"]:
            if text not in data["user_groups"].get(user_id, []):
                data["user_groups"].setdefault(user_id, []).append(text)
                context.user_data["active_group"] = text
                save_data()
                group_name = data["group_names"].get(text, text)
                update.message.reply_text(f"✅ Ви приєдналися до групи \"{group_name}\"!")
            else:
                update.message.reply_text("ℹ️ Ви вже в цій групі!")
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

def list_items(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    active_group = context.user_data.get("active_group")
    personal_list = context.user_data.get("personal_list")
    if active_group:
        shopping_list = data["groups"].get(active_group, [])
        group_name = data["group_names"].get(active_group, active_group)
        list_title = f"🛒 Список покупок групи \"{group_name}\":"
    elif personal_list:
        shopping_list = data["personal_lists"].get(user_id, [])
        list_title = "🛒 Ваш особистий список:"
    else:
        update.message.reply_text("❌ Ви не вибрали список. Введіть /start, щоб вибрати.")
        return
    if not shopping_list:
        update.message.reply_text("📭 Список покупок порожній.")
        return
    keyboard = [
        [InlineKeyboardButton(f"🗑 {item}", callback_data=f"remove_{active_group or user_id}_{item}")]
        for item in shopping_list
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(list_title, reply_markup=reply_markup, parse_mode="Markdown")

def clear_list(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    active_group = context.user_data.get("active_group")
    personal_list = context.user_data.get("personal_list")
    if active_group:
        data["groups"][active_group] = []
    elif personal_list:
        data["personal_lists"][user_id] = []
    else:
        update.message.reply_text("❌ Ви не вибрали список. Введіть /start, щоб вибрати.")
        return
    save_data()
    update.message.reply_text("🧹 Список очищено.")

def remove_item(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data_parts = query.data.split("_")
    list_id = data_parts[1]
    item_to_remove = "_".join(data_parts[2:])
    if list_id in data["groups"] and item_to_remove in data["groups"][list_id]:
        data["groups"][list_id].remove(item_to_remove)
    elif list_id in data["personal_lists"] and item_to_remove in data["personal_lists"][list_id]:
        data["personal_lists"][list_id].remove(item_to_remove)
    save_data()
    query.edit_message_text(f"🗑 Видалено: {item_to_remove}")
    list_items(update, context)

def list_groups(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    user_groups = data["user_groups"].get(user_id, [])
    if not user_groups:
        text = "ℹ️ Ви ще не приєдналися до жодної групи."
        reply_markup = None
    else:
        keyboard = []
        for code in user_groups:
            group_name = data["group_names"].get(code, code)
            keyboard.append([InlineKeyboardButton(f"📌 {group_name}", callback_data=f"set_group_{code}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "🔹 Виберіть групу для роботи:"
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text, reply_markup=reply_markup if user_groups else None)
    else:
        update.message.reply_text(text, reply_markup=reply_markup if user_groups else None)

def check_active_group(update: Update, context: CallbackContext):
    active_group = context.user_data.get("active_group")
    if active_group:
        group_name = data["group_names"].get(active_group, active_group)
        update.message.reply_text(f"📂 Активна група: `{group_name}`", parse_mode="Markdown")
    else:
        update.message.reply_text("❌ Ви не вибрали групу. Використовуйте /groups.")

def create_group_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    ask_group_name(update, context)

def join_group_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    join_group(update, context)

def list_groups_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    list_groups(update, context)

def main():
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
