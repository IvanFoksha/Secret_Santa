"""Скрипт для тестирования основных функций бота."""
import os
import sys

# Добавляем корневую директорию проекта в путь для импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import Session, User, Room, Wish
from rooms import create_room
from wishes import add_wish, edit_wish, get_user_wishes
from payment_handler import grant_access


def test_bot_functions():
    """Тестирование основных функций бота."""
    print("Тестирование функций бота...")
    
    session = Session()
    try:
        # 1. Создание тестового пользователя
        print("\n1. Создание тестового пользователя:")
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        session.add(user)
        session.commit()
        print(f"Создан пользователь: {user.username} (ID: {user.telegram_id})")
        
        # 2. Создание комнаты
        print("\n2. Создание комнаты:")
        room_code = create_room(user.telegram_id, "Test Room")
        room = session.query(Room).filter_by(code=room_code).first()
        print(f"Создана комната: {room.name} (Код: {room.code})")
        
        # 3. Добавление желания
        print("\n3. Добавление желания:")
        wish_text = "Хочу новый телефон"
        wish_id = add_wish(user.telegram_id, room.id, wish_text)
        wish = session.query(Wish).get(wish_id)
        print(f"Добавлено желание: {wish.text}")
        
        # 4. Редактирование желания
        print("\n4. Редактирование желания:")
        new_text = "Хочу новый iPhone"
        edit_wish(wish_id, new_text)
        wish = session.query(Wish).get(wish_id)
        print(f"Отредактировано желание: {wish.text}")
        
        # 5. Проверка списка желаний
        print("\n5. Проверка списка желаний:")
        wishes = get_user_wishes(user.telegram_id, room.id)
        print(f"Количество желаний: {len(wishes)}")
        for w in wishes:
            print(f"- {w.text}")
        
        # 6. Тестирование оплаты
        print("\n6. Тестирование оплаты:")
        grant_access(room.id, 'paid')
        room = session.query(Room).get(room.id)
        print(f"Статус оплаты комнаты: {room.is_paid}")
        
        print("\nТестирование завершено успешно!")
        
    except Exception as e:
        print(f"\nОшибка при тестировании: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    test_bot_functions() 