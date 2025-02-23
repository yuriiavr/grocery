import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Отримуємо токен з оточення
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ ПОМИЛКА: Не знайдено TELEGRAM_BOT_TOKEN у змінних середовища!")

# Глобальний список для зберігання покупок
shopping_list = []

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Привіт! Надішли мені назви товарів, які потрібно купити. "
        "Щоб переглянути список, введи /list, а щоб очистити список — /clear."
    )

def add_item(update: Update, context: CallbackContext):
    global shopping_list
    item = update.message.text.strip()
    if item:  # Переконуємося, що повідомлення не порожнє
        shopping_list.append(item)
        update.message.reply_text(f"✅ Додано: {item}\n📌 У списку: {len(shopping_list)} предметів.")
    else:
        update.message.reply_text("⚠ Введіть коректну назву товару.")

def list_items(update: Update, context: CallbackContext):
    if shopping_list:
        text = "🛒 *Список покупок:*\n" + "\n".join(f"- {item}" for item in shopping_list)
        update.message.reply_text(text, parse_mode="Markdown")
    else:
        update.message.reply_text("📭 Список покупок порожній.")

def clear_list(update: Update, context: CallbackContext):
    global shopping_list
    shopping_list = []
    update.message.reply_text("🧹 Список покупок очищено.")

def main():
    # Запускаємо бота з правильним токеном
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("list", list_items))
    dp.add_handler(CommandHandler("clear", clear_list))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, add_item))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
