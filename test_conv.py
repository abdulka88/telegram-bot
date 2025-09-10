"""
Минимальный тестовый файл для проверки работы ConversationHandler
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
NAME, AGE = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отправляет приветственное сообщение и переходит в состояние NAME."""
    await update.message.reply_text("Введите ваше имя:")
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает имя пользователя и запрашивает возраст."""
    logger.info(f"Получено имя: {update.message.text}")
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите ваш возраст:")
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает возраст пользователя и завершает разговор."""
    logger.info(f"Получен возраст: {update.message.text}")
    context.user_data['age'] = update.message.text
    await update.message.reply_text(
        f"Спасибо! Ваши данные:\n"
        f"Имя: {context.user_data['name']}\n"
        f"Возраст: {context.user_data['age']}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет разговор."""
    await update.message.reply_text('Разговор отменен.')
    return ConversationHandler.END

def main():
    """Запуск бота."""
    # Создаем Application
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    # Добавляем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()