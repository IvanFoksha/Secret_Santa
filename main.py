import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from start import start_command, help_command, button_handler
from rooms import handle_room_code, handle_room_version
from wishes import handle_wish_text, edit_wish_handler
from database import init_bd
from keyboards import get_main_menu_keyboard

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получение токена бота
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Не найден токен бота. Проверьте файл .env")


def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация базы данных
        init_bd()

        # Создаем приложение
        application = Application.builder().token(TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Сначала регистрируем специализированные обработчики
        application.add_handler(CallbackQueryHandler(handle_room_version, pattern="^(free|pro)_version$"))
        
        # Затем общий обработчик кнопок
        application.add_handler(CallbackQueryHandler(button_handler))

        # Создаем единый обработчик сообщений
        async def message_handler(update: Update, context):
            """Обработчик всех текстовых сообщений"""
            logger.info(f"Получено сообщение: {update.message.text}")
            logger.info(f"Состояние пользователя: {context.user_data.get('waiting_for')}")
            
            # Если пользователь ожидает ввода кода комнаты
            if context.user_data.get('waiting_for') == 'room_code':
                await handle_room_code(update, context)
                return
            
            # Если пользователь ожидает ввода желания
            if context.user_data.get('waiting_for') == 'wish':
                await handle_wish_text(update, context)
                return
            
            # Если пользователь ожидает ввода нового желания
            if context.user_data.get('waiting_for') == 'new_wish':
                await handle_wish_text(update, context)
                return
            
            # Если пользователь ожидает ввода кода комнаты для редактирования желания
            if context.user_data.get('waiting_for') == 'edit_wish_room':
                await edit_wish_handler(update, context)
                return
            
            # Если пользователь ожидает ввода номера желания для редактирования
            if context.user_data.get('waiting_for') == 'edit_wish_number':
                await edit_wish_handler(update, context)
                return
            
            # Если пользователь ожидает ввода нового текста желания
            if context.user_data.get('waiting_for') == 'edit_wish_text':
                await edit_wish_handler(update, context)
                return
            
            # Если не ожидается никакого ввода, показываем главное меню
            await update.message.reply_text(
                "Выберите действие из меню ниже 👇",
                reply_markup=get_main_menu_keyboard()
            )

        # Добавляем единый обработчик сообщений
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        ))

        # Запускаем бота
        logger.info("Запускаем бота...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise


if __name__ == '__main__':
    main()
