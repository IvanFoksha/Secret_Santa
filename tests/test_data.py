"""Модуль с тестовыми данными для тестирования."""
from database import User, Room, Wish, UserRoom


def create_test_user(session, telegram_id=123456789, username="test_user"):
    """Создает тестового пользователя."""
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name="Test",
        last_name="User"
    )
    session.add(user)
    session.commit()
    return user


def create_test_room(session, owner_id, code="TEST123"):
    """Создает тестовую комнату."""
    room = Room(
        code=code,
        owner_id=owner_id,
        name="Test Room"
    )
    session.add(room)
    session.commit()
    return room


def create_test_wish(session, user_id, room_id, text="Test wish"):
    """Создает тестовое желание."""
    wish = Wish(
        user_id=user_id,
        room_id=room_id,
        text=text
    )
    session.add(wish)
    session.commit()
    return wish


def create_test_user_room(session, user_id, room_id, is_owner=False):
    """Создает тестовую связь пользователя с комнатой."""
    user_room = UserRoom(
        user_id=user_id,
        room_id=room_id,
        is_owner=is_owner
    )
    session.add(user_room)
    session.commit()
    return user_room


def setup_test_data(session):
    """Создает полный набор тестовых данных."""
    # Создаем тестового пользователя
    user = create_test_user(session)
    
    # Создаем тестовую комнату
    room = create_test_room(session, user.telegram_id)
    
    # Создаем связь пользователя с комнатой
    create_test_user_room(session, user.telegram_id, room.id, is_owner=True)
    
    # Создаем тестовое желание
    wish = create_test_wish(session, user.telegram_id, room.id)
    
    return {
        'user': user,
        'room': room,
        'wish': wish
    } 