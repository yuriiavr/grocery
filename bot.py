import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Отримуємо токен з оточення
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ ПОМИЛКА: Не знайдено TELEGRAM_BOT_TOKEN у змінних середовища!")

# Словник для зберігання списків покупок (user_id: [список покупок])
user_shopping_lists = {}

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привіт! Надішли мені назви товарів, які потрібно купити. "
        "Щоб переглянути список із кнопками для видалення, введи /list. "
        "Щоб очистити список – /clear."
    )

def get_user_list(user_id):
    """ Отримує список покупок для конкретного користувача """
    return user_shopping_lists.setdefault(user_id, [])

def add_item(update: Update, context: CallbackContext):
    """ Додає товар до персонального списку """
    user_id = update.message.from_user.id
    item = update.message.text.strip().lower()  # Приводимо до нижнього регістру

    if item:
        user_list = get_user_list(user_id)
        user_list.append(item)
        update.message.reply_text(f"✅ Додано: {item}\n📌 У вашому списку: {len(user_list)} предметів.")
    else:
        update.message.reply_text("⚠ Введіть коректну назву товару.")

def generate_list_with_buttons(user_id):
    """ Формує список покупок з кнопками для видалення для конкретного користувача """
    user_list = get_user_list(user_id)

    if not user_list:
        return "📭 Ваш список покупок порожній.", None

    keyboard = []
    for item in user_list:
        keyboard.append([InlineKeyboardButton(f"🗑 Видалити {item}", callback_data=f"remove_{user_id}_{item}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    return "🛒 *Ваш список покупок:*", reply_markup

def list_items(update: Update, context: CallbackContext):
    """ Відображає список покупок з кнопками для видалення """
    user_id = update.message.from_user.id
    text, reply_markup = generate_list_with_buttons(user_id)
    update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

def clear_list(update: Update, context: CallbackContext):
    """ Очищає список покупок тільки для конкретного користувача """
    user_id = update.message.from_user.id
    user_shopping_lists[user_id] = []  # Очищаємо список користувача
    update.message.reply_text("🧹 Ваш список покупок очищено.")

def remove_item_callback(update: Update, context: CallbackContext):
    """ Видаляє товар після натискання на кнопку """
    query = update.callback_query
    query.answer()

    data = query.data.split("_")  # Парсимо callback_data
    user_id = int(data[1])  # ID користувача
    item_to_remove = data[2]  # Товар, який потрібно видалити

    if user_id in user_shopping_lists and item_to_remove in user_shopping_lists[user_id]:
        user_shopping_lists[user_id].remove(item_to_remove)
        query.edit_message_text(f"🗑 Видалено: {item_to_remove}")

        # Оновлюємо список після видалення
        text, reply_markup = generate_list_with_buttons(user_id)
        query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        query.edit_message_text("⚠ Товар вже видалено або не знайдено!")

def main():
    # Запускаємо бота з правильним токеном
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("list", list_items))
    dp.add_handler(CommandHandler("clear", clear_list))
    dp.add_handler(CallbackQueryHandler(remove_item_callback))  # Обробник кнопок видалення
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, add_item))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
