from database import Session, User, Room, Wish
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    session = Session()
    try:
        # Проверяем пользователей
        users = session.query(User).all()
        logger.info("\nПользователи:")
        for user in users:
            logger.info(f"ID: {user.id}, Telegram ID: {user.telegram_id}, Room ID: {user.room_id}")
        
        # Проверяем комнаты
        rooms = session.query(Room).all()
        logger.info("\nКомнаты:")
        for room in rooms:
            logger.info(f"ID: {room.id}, Name: {room.name}, Code: {room.code}")
        
        # Проверяем желания
        wishes = session.query(Wish).all()
        logger.info("\nЖелания:")
        for wish in wishes:
            logger.info(f"ID: {wish.id}, User ID: {wish.user_id}, Room ID: {wish.room_id}, Text: {wish.text}")
            
    finally:
        session.close()

if __name__ == "__main__":
    check_database() 