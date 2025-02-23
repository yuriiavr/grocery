import os
import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Отримуємо токен з оточення
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ ПОМИЛКА: Не знайдено TELEGRAM_BOT_TOKEN у змінних середовища!")

# Файл для збереження даних
DATA_FILE = "shopping_groups.json"

# Завантаження списків із файлу
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"groups": {}, "user_groups": {}}
    return {"groups": {}, "user_groups": {}}

# Збереження списків у файл
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Завантажуємо дані
data = load_data()

def generate_group_code():
    """ Генерує унікальний код для групи """
    return str(random.randint(100000, 999999))

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🧍 Особистий список", callback_data="personal")],
        [InlineKeyboardButton("👥 Створити групу", callback_data="create_group")],
        [InlineKeyboardButton("🔗 Приєднатися до групи", callback_data="join_group")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Оберіть опцію:", reply_markup=reply_markup)

def create_group(update: Update, context: CallbackContext):
    """ Користувач створює нову групу """
    query = update.callback_query
    query.answer()

    user_id = str(query.from_user.id)
    group_code = generate_group_code()

    data["groups"][group_code] = []
    data["user_groups"].setdefault(user_id, []).append(group_code)
    save_data()

    query.edit_message_text(f"✅ Група створена! Код для приєднання: `{group_code}`", parse_mode="Markdown")

def join_group(update: Update, context: CallbackContext):
    """ Запитує у користувача код для приєднання """
    query = update.callback_query
    query.answer()
    query.edit_message_text("✍ Введіть код групи, щоб приєднатися:")

    context.user_data["waiting_for_group_code"] = True

def handle_text(update: Update, context: CallbackContext):
    """ Обробляє введення коду групи або додавання товару """
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

    # Якщо це не код групи, вважаємо, що це товар
    active_group = context.user_data.get("active_group")
    if active_group:
        data["groups"][active_group].append(text.capitalize())
        save_data()
        update.message.reply_text(f"✅ Додано: {text.capitalize()}")
    else:
        update.message.reply_text("❌ Спочатку оберіть групу за допомогою команди /groups.")

def list_groups(update: Update, context: CallbackContext):
    """ Показує списки, до яких приєднався користувач """
    user_id = str(update.message.from_user.id)
    user_groups = data["user_groups"].get(user_id, [])

    if not user_groups:
        update.message.reply_text("ℹ️ Ви ще не приєдналися до жодної групи.")
        return

    keyboard = [[InlineKeyboardButton(f"📌 {code}", callback_data=f"set_group_{code}")] for code in user_groups]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🔹 Виберіть групу для роботи:", reply_markup=reply_markup)

def set_active_group(update: Update, context: CallbackContext):
    """ Встановлює активну групу для користувача """
    query = update.callback_query
    query.answer()

    group_code = query.data.split("_")[2]
    context.user_data["active_group"] = group_code

    query.edit_message_text(f"✅ Ви працюєте з групою `{group_code}`", parse_mode="Markdown")

def list_items(update: Update, context: CallbackContext):
    """ Відображає список товарів у вибраній групі """
    active_group = context.user_data.get("active_group")
    
    if not active_group:
        update.message.reply_text("❌ Ви не обрали групу. Використайте /groups, щоб вибрати.")
        return

    shopping_list = data["groups"].get(active_group, [])
    
    if not shopping_list:
        update.message.reply_text("📭 Список покупок порожній.")
        return

    keyboard = [[InlineKeyboardButton("🗑", callback_data=f"remove_{active_group}_{item}")] for item in shopping_list]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("🛒 *Список покупок:*", reply_markup=reply_markup, parse_mode="Markdown")

def remove_item(update: Update, context: CallbackContext):
    """ Видаляє товар із групового списку """
    query = update.callback_query
    query.answer()

    data_parts = query.data.split("_")
    group_code = data_parts[1]
    item_to_remove = data_parts[2]

    if group_code in data["groups"] and item_to_remove in data["groups"][group_code]:
        data["groups"][group_code].remove(item_to_remove)
        save_data()
        query.edit_message_text(f"🗑 Видалено: {item_to_remove}")

        text, reply_markup = list_items(update, context)
        query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("groups", list_groups))
    dp.add_handler(CommandHandler("list", list_items))
    dp.add_handler(CallbackQueryHandler(create_group, pattern="create_group"))
    dp.add_handler(CallbackQueryHandler(join_group, pattern="join_group"))
    dp.add_handler(CallbackQueryHandler(set_active_group, pattern="set_group_.*"))
    dp.add_handler(CallbackQueryHandler(remove_item, pattern="remove_.*"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
