import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from start import start_command, help_command, button_handler
from rooms import (
    create_room_handler, join_room_handler, handle_room_code,
    handle_room_version, list_rooms, search_room, confirm_join_handler,
    handle_room_context_menu
)
from wishes import handle_wish_text, edit_wish_handler, handle_edit_wish_text
from database import init_bd, switch_room, get_room_by_id
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


async def switch_room_handler(update: Update, context):
    """Обработчик переключения между комнатами"""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID комнаты из callback_data
    room_id = int(query.data.split('_')[2])
    user_id = query.from_user.id
    
    # Получаем информацию о комнате
    room = get_room_by_id(room_id)
    if not room:
        await query.message.reply_text(
            "❌ Не удалось получить информацию о комнате.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Переключаем пользователя на указанную комнату
    success = switch_room(user_id, room_id)
    
    if success:
        await query.message.reply_text(
            "✅ Вы успешно переключились на комнату!\n"
            f"🔑 Код комнаты: {room['code']}\n"
            f"🆔 ID комнаты: {room['id']}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.message.reply_text(
            "❌ Не удалось переключиться на указанную комнату.\n"
            "Возможно, вы не являетесь создателем этой комнаты.\n"
            "Пожалуйста, проверьте права доступа.",
            reply_markup=get_main_menu_keyboard()
        )


async def message_handler(update: Update, context):
    """Обработчик всех текстовых сообщений"""
    logger.info(f"Получено сообщение: {update.message.text}")
    logger.info(
        f"Состояние пользователя: {context.user_data.get('waiting_for')}"
    )
    logger.info(
        f"Редактирование желания: {context.user_data.get('editing_wish_id')}"
    )
    
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
    
    # Если пользователь ожидает ввода кода комнаты для редактирования
    if context.user_data.get('waiting_for') == 'edit_wish_room':
        await edit_wish_handler(update, context)
        return
    
    # Если пользователь ожидает ввода номера желания для редактирования
    if context.user_data.get('waiting_for') == 'edit_wish_number':
        await edit_wish_handler(update, context)
        return
    
    # Если пользователь ожидает ввода нового текста желания
    if context.user_data.get('editing_wish_id'):
        await handle_edit_wish_text(update, context)
        return
    
    # Если не ожидается никакого ввода, показываем главное меню
    await update.message.reply_text(
        "Выберите действие из меню ниже 👇",
        reply_markup=get_main_menu_keyboard()
    )


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
        application.add_handler(
            CommandHandler("create_room", create_room_handler)
        )
        application.add_handler(
            CommandHandler("join_room", join_room_handler)
        )
        application.add_handler(
            CommandHandler("search_room", search_room)
        )
        
        # Регистрируем обработчики callback-запросов
        application.add_handler(
            CallbackQueryHandler(
                handle_room_version, 
                pattern="^(free|pro)_version$"
            )
        )
        application.add_handler(
            CallbackQueryHandler(list_rooms, pattern="^list_rooms$")
        )
        application.add_handler(
            CallbackQueryHandler(
                switch_room_handler, 
                pattern="^switch_room_\\d+$"
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                confirm_join_handler, 
                pattern="^confirm_join_"
            )
        )
        application.add_handler(
            CallbackQueryHandler(search_room, pattern="^cancel_join$")
        )
        application.add_handler(
            CallbackQueryHandler(
                handle_room_version, 
                pattern="^(pay|stay)_"
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                handle_room_context_menu,
                pattern="^(add_wish|list_wishes|list_room_users|main_menu|room_menu)$"
            )
        )
        
        # Добавляем общий обработчик кнопок
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Добавляем обработчик текстовых сообщений
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
        )

        # Запускаем бота
        logger.info("Запускаем бота...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise


if __name__ == '__main__':
    main()
