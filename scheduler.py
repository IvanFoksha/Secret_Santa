import logging
from datetime import datetime, timedelta
from telegram.ext import Application
from database import get_room_wishes, mark_wish_as_viewed, get_all_active_rooms
from config import WISH_DELIVERY_HOUR

logger = logging.getLogger(__name__)


async def deliver_wishes(context):
    """Отправляет желания в указанное время"""
    logger.info("Начало выполнения deliver_wishes")
    try:
        current_hour = datetime.now().hour
        if current_hour == WISH_DELIVERY_HOUR:
            logger.info(f"Отправка желаний в час {WISH_DELIVERY_HOUR}")
            # Получаем все активные комнаты
            rooms = get_all_active_rooms()
            logger.info(f"Найдено {len(rooms)} активных комнат")
            
            for room in rooms:
                # Получаем желания для каждой комнаты
                wishes = get_room_wishes(room['room_id'])
                logger.info(
                    f"Комната {room['room_id']}: найдено {len(wishes)} желаний"
                )
                
                for wish in wishes:
                    # Отмечаем желание как отправленное
                    mark_wish_as_viewed(wish['id'])
                    # Отправляем желание получателю
                    await context.bot.send_message(
                        chat_id=wish['target_user_id'],
                        text=f"🎁 Ваше желание: {wish['text']}"
                    )
                    logger.info(
                        f"Отправлено желание ID {wish['id']} "
                        f"пользователю {wish['target_user_id']}"
                    )
        else:
            logger.debug(
                f"Текущее время {current_hour}, "
                f"пропуск отправки (ожидается {WISH_DELIVERY_HOUR})"
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке желаний: {e}")


def setup_scheduler(application: Application):
    """Настраивает планировщик для отправки желаний"""
    logger.info("Настройка планировщика")
    job_queue = application.job_queue
    # Запускаем проверку каждый час
    job_queue.run_repeating(deliver_wishes, interval=timedelta(hours=1))
    logger.info("Планировщик настроен")
