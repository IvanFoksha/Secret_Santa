from database import Session, User, Room, Wish
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    """Проверяет содержимое базы данных"""
    session = Session()
    
    # Проверяем пользователей
    logger.info("\nПользователи:")
    users = session.query(User).all()
    for user in users:
        logger.info(f"ID: {user.id}, Telegram ID: {user.telegram_id}, Room ID: {user.room_id}")
    
    # Проверяем комнаты
    logger.info("\nКомнаты:")
    rooms = session.query(Room).all()
    for room in rooms:
        logger.info(
            f"ID: {room.id}, Код: {room.code}, "
            f"Создатель: {room.creator_id}, Активна: {room.is_active}"
        )
    
    # Проверяем желания
    logger.info("\nЖелания:")
    wishes = session.query(Wish).all()
    for wish in wishes:
        logger.info(f"ID: {wish.id}, Текст: {wish.text}, User ID: {wish.user_id}")
    
    session.close()

if __name__ == "__main__":
    check_database() 