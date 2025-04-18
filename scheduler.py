import logging
from datetime import datetime, timedelta
from telegram.ext import Application
from database import (
    get_room_wishes, get_all_active_rooms, get_room_users,
    get_user_by_telegram_id
)

logger = logging.getLogger(__name__)


async def deliver_wishes(context):
    """Отправляет желания всем участникам комнаты"""
    logger.info("Начало выполнения deliver_wishes")
    try:
        # Получаем все активные комнаты
        rooms = get_all_active_rooms()
        logger.info(f"Найдено {len(rooms)} активных комнат")
        
        for room in rooms:
            # Получаем всех пользователей в комнате
            users = get_room_users(room['id'])
            logger.info(f"Комната {room['id']}: найдено {len(users)} пользователей")
            
            # Получаем все желания в комнате
            wishes = get_room_wishes(room['id'])
            logger.info(f"Комната {room['id']}: найдено {len(wishes)} желаний")
            
            # Для каждого пользователя отправляем желания других участников
            for user in users:
                user_telegram = get_user_by_telegram_id(user['telegram_id'])
                if not user_telegram:
                    continue
                    
                # Формируем сообщение с желаниями других участников
                other_wishes = [
                    wish for wish in wishes 
                    if wish['user_id'] != user_telegram.id
                ]
                
                if other_wishes:
                    message = "🎁 Желания участников комнаты:\n\n"
                    for wish in other_wishes:
                        wish_user = get_user_by_telegram_id(wish['user_id'])
                        if wish_user:
                            username = wish_user.username or 'Аноним'
                            message += f"От {username}:\n{wish['text']}\n\n"
                    
                    # Отправляем сообщение пользователю
                    await context.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=message
                    )
                    logger.info(
                        f"Отправлены желания пользователю {user['telegram_id']}"
                    )
    except Exception as e:
        logger.error(f"Ошибка при отправке желаний: {e}")


def setup_scheduler(application: Application):
    """Настраивает планировщик для отправки желаний"""
    logger.info("Настройка планировщика")
    job_queue = application.job_queue
    
    # Запускаем рассылку каждый день в 00:00
    job_queue.run_daily(
        deliver_wishes,
        time=datetime.time(hour=0, minute=0)
    )
    logger.info("Планировщик настроен")
