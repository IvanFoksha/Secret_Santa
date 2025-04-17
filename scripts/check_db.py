"""Скрипт для проверки работы базы данных."""
import os
import sys

# Добавляем корневую директорию проекта в путь для импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import User, Room, Wish
from config import current_config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def check_database():
    """Проверка работы базы данных."""
    print("Проверка базы данных...")
    
    # Создаем подключение к базе данных
    engine = create_engine(current_config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Проверяем таблицы
        print("\n1. Проверка таблиц:")
        tables = engine.table_names()
        print(f"Найденные таблицы: {tables}")
        
        # Проверяем пользователей
        print("\n2. Проверка пользователей:")
        users = session.query(User).all()
        print(f"Количество пользователей: {len(users)}")
        for user in users:
            print(f"- {user.username} (ID: {user.telegram_id})")
        
        # Проверяем комнаты
        print("\n3. Проверка комнат:")
        rooms = session.query(Room).all()
        print(f"Количество комнат: {len(rooms)}")
        for room in rooms:
            print(f"- {room.name} (Код: {room.code})")
            print(f"  Создатель: {room.creator_id}")
            print(f"  Активна: {room.is_active}")
            print(f"  Оплачена: {room.is_paid}")
        
        # Проверяем желания
        print("\n4. Проверка желаний:")
        wishes = session.query(Wish).all()
        print(f"Количество желаний: {len(wishes)}")
        for wish in wishes:
            print(f"- ID: {wish.id}")
            print(f"  Пользователь: {wish.user_id}")
            print(f"  Комната: {wish.room_id}")
            print(f"  Текст: {wish.text}")
            print(f"  Просмотрено: {wish.is_viewed}")
        
        print("\nПроверка завершена успешно!")
        
    except Exception as e:
        print(f"\nОшибка при проверке базы данных: {e}")
    finally:
        session.close()


if __name__ == '__main__':
    check_database() 