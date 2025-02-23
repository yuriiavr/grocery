import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Отримуємо токен з оточення
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ ПОМИЛКА: Не знайдено TELEGRAM_BOT_TOKEN у змінних середовища!")

# Глобальний список покупок
shopping_list = []

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привіт! Надішли мені назви товарів, які потрібно купити. "
        "Щоб переглянути список із кнопками для видалення, введи /list. "
        "Щоб очистити список – /clear."
    )

def add_item(update: Update, context: CallbackContext):
    """ Додає товар до списку """
    global shopping_list
    item = update.message.text.strip().lower()  # Приводимо до нижнього регістру
    if item:
        shopping_list.append(item)
        update.message.reply_text(f"✅ Додано: {item}\n📌 У списку: {len(shopping_list)} предметів.")
    else:
        update.message.reply_text("⚠ Введіть коректну назву товару.")

def generate_list_with_buttons():
    """ Формує список покупок з кнопками для видалення """
    if not shopping_list:
        return "📭 Список покупок порожній.", None

    keyboard = []
    for item in shopping_list:
        keyboard.append([InlineKeyboardButton(f"🗑 Видалити {item}", callback_data=f"remove_{item}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    return "🛒 *Список покупок:*", reply_markup

def list_items(update: Update, context: CallbackContext):
    """ Відображає список покупок з кнопками для видалення """
    text, reply_markup = generate_list_with_buttons()
    update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

def clear_list(update: Update, context: CallbackContext):
    """ Очищає весь список """
    global shopping_list
    shopping_list = []
    update.message.reply_text("🧹 Список покупок очищено.")

def remove_item_callback(update: Update, context: CallbackContext):
    """ Видаляє товар після натискання на кнопку """
    global shopping_list
    query = update.callback_query
    query.answer()

    item_to_remove = query.data.replace("remove_", "")  # Отримуємо назву товару

    if item_to_remove in shopping_list:
        shopping_list.remove(item_to_remove)
        query.edit_message_text(f"🗑 Видалено: {item_to_remove}")

        # Оновлюємо список після видалення
        text, reply_markup = generate_list_with_buttons()
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
