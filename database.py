import os
import logging
import random
import string
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(32))
    first_name = Column(String(64))
    last_name = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    room_id = Column(Integer, ForeignKey('rooms.id'))
    
    # Связи
    room = relationship("Room", back_populates="users", foreign_keys=[room_id])
    created_rooms = relationship("Room", back_populates="creator", foreign_keys="Room.creator_id")
    wishes = relationship("Wish", back_populates="user", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = 'rooms'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_paid = Column(Boolean, default=False)
    max_participants = Column(Integer, default=10)
    max_wishes = Column(Integer, default=3)  # Ограничение на количество желаний
    
    # Связи
    creator = relationship("User", back_populates="created_rooms", foreign_keys=[creator_id])
    users = relationship("User", back_populates="room", foreign_keys="User.room_id")
    wishes = relationship("Wish", back_populates="room", cascade="all, delete-orphan")


class Wish(Base):
    __tablename__ = 'wishes'
    
    id = Column(Integer, primary_key=True)
    text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_viewed = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    room_id = Column(Integer, ForeignKey('rooms.id'))
    user = relationship("User", back_populates="wishes")
    room = relationship("Room", back_populates="wishes")


# Создаем подключение к базе данных
engine = create_engine(
    f'sqlite:///{DB_PATH}',
    connect_args={'check_same_thread': False}
)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def init_bd():
    """Проверяет существование файла базы данных и создает его, 
    если он не существует"""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Создаем файл базы данных, если он не существует
    if not os.path.exists(DB_PATH):
        open(DB_PATH, 'w').close()
    
    # Создаем все таблицы
    Base.metadata.create_all(engine)
    logger.info("База данных успешно инициализирована")
    return True


def add_user(telegram_id: int, username: str, first_name: str = None, last_name: str = None) -> bool:
    """Добавляет нового пользователя в базу данных"""
    session = Session()
    try:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def generate_room_code() -> str:
    """Генерирует уникальный код комнаты"""
    session = Session()
    try:
        while True:
            # Генерируем случайный код из 6 символов
            code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            # Проверяем, не существует ли уже комната с таким кодом
            existing_room = session.query(Room).filter(
                Room.code == code
            ).first()
            if not existing_room:
                return code
    finally:
        session.close()


def create_room(name: str, creator_id: int, max_participants: int, is_paid: bool = False) -> int:
    """Создает новую комнату и возвращает её ID"""
    session = Session()
    try:
        logger.info(f"Начало создания комнаты: name={name}, creator_id={creator_id}, max_participants={max_participants}, is_paid={is_paid}")
        
        # Генерируем уникальный код комнаты
        room_code = generate_room_code()
        logger.info(f"Сгенерирован код комнаты: {room_code}")
        
        # Создаем новую комнату
        new_room = Room(
            name=name,
            code=room_code,
            creator_id=creator_id,
            max_participants=max_participants,
            is_paid=is_paid,
            max_wishes=5 if is_paid else 1  # PRO версия - 5 желаний, бесплатная - 1
        )
        
        session.add(new_room)
        session.commit()
        
        room_id = new_room.id
        logger.info(f"Комната успешно создана с ID: {room_id}")
        
        # Автоматически добавляем создателя в комнату
        user = session.query(User).filter(User.telegram_id == creator_id).first()
        if user:
            user.room_id = room_id
            session.commit()
            logger.info(f"Создатель {creator_id} автоматически добавлен в комнату {room_id}")
        
        return room_id
    except Exception as e:
        logger.error(f"Ошибка при создании комнаты: {str(e)}")
        session.rollback()
        return 0
    finally:
        session.close()


def add_user_to_room(room_id: int, user_id: int) -> bool:
    """Добавляет пользователя в комнату"""
    session = Session()
    try:
        # Проверяем существование пользователя
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return False
        
        # Проверяем существование комнаты
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.error(f"Комната {room_id} не найдена")
            return False
        
        # Проверяем количество пользователей в комнате
        users_count = session.query(User).filter(User.room_id == room_id).count()
        if users_count >= room.max_participants:
            logger.error(f"Достигнут лимит пользователей в комнате {room_id}")
            return False
        
        # Добавляем пользователя в комнату
        user.room_id = room_id
        session.commit()
        logger.info(f"Пользователь {user_id} успешно добавлен в комнату {room_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя в комнату: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close()


def count_users_in_room(room_id: int) -> int:
    """Подсчитывает количество пользователей в комнате"""
    session = Session()
    try:
        return session.query(User).filter(User.room_id == room_id).count()
    finally:
        session.close()


def add_wish(user_id: int, wish_text: str) -> int:
    """Добавляет желание пользователя и возвращает ID созданного желания"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.room:
            logger.error(f"Пользователь {user_id} не найден или не состоит в комнате")
            return 0
            
        # Проверяем количество желаний
        current_wishes = session.query(Wish).filter(Wish.user_id == user.id).count()
        if current_wishes >= user.room.max_wishes:
            logger.error(f"Достигнут лимит желаний для пользователя {user_id}")
            return 0
            
        wish = Wish(
            user_id=user.id,
            room_id=user.room.id,
            text=wish_text
        )
        session.add(wish)
        session.commit()
        logger.info(f"Желание успешно добавлено для пользователя {user_id}")
        return wish.id
    except Exception as e:
        logger.error(f"Ошибка при добавлении желания: {e}")
        session.rollback()
        return 0
    finally:
        session.close()


def update_wish(wish_id: int, new_text: str) -> bool:
    """Обновляет текст желания"""
    session = Session()
    try:
        wish = session.query(Wish).filter(Wish.id == wish_id).first()
        if not wish:
            return False
        
        wish.text = new_text
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def delete_wish(wish_id: int, user_id: int) -> bool:
    """Удаляет желание"""
    session = Session()
    try:
        wish = session.query(Wish).filter(
            Wish.id == wish_id,
            Wish.user_id == user_id
        ).first()
        if not wish:
            return False
        
        session.delete(wish)
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def get_user_wishes(user_id: int) -> list:
    """Получает список желаний пользователя"""
    session = Session()
    try:
        wishes = session.query(Wish).filter(Wish.user_id == user_id).all()
        return [
            {
                'id': wish.id,
                'text': wish.text,
                'is_viewed': wish.is_viewed
            }
            for wish in wishes
        ]
    finally:
        session.close()


def get_all_rooms(user_id: int) -> list:
    """Получает список всех комнат пользователя"""
    session = Session()
    try:
        rooms = session.query(Room).filter(Room.creator_id == user_id).all()
        return [
            {
                'id': room.id,
                'name': room.name,
                'max_users': room.max_users,
                'is_paid': room.is_paid,
                'current_users': count_users_in_room(room.id)
            }
            for room in rooms
        ]
    finally:
        session.close()


def get_room_wishes(room_id: int) -> list:
    """Получает список желаний в комнате"""
    session = Session()
    try:
        wishes = session.query(Wish).filter(Wish.room_id == room_id).all()
        return [
            {
                'text': wish.text,
                'user_id': wish.user_id,
                'user_name': wish.user.username
            }
            for wish in wishes
        ]
    finally:
        session.close()


def grant_access(user_id: int, access_type: str) -> bool:
    """Предоставляет доступ к PRO версии"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.creator_id == user_id).first()
        if not room:
            return False
        
        room.is_paid = True
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def user_has_room(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя комната"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.creator_id == user_id).first()
        return room is not None
    finally:
        session.close()


def get_room_details(room_identifier) -> dict:
    """Получает детали комнаты по её ID или коду"""
    session = Session()
    try:
        # Пытаемся найти комнату по коду, если идентификатор - строка
        if isinstance(room_identifier, str):
            room = session.query(Room).filter(Room.code == room_identifier).first()
        # Иначе ищем по ID
        else:
            room = session.query(Room).filter(Room.id == room_identifier).first()
        
        if not room:
            return None
        
        current_users = count_users_in_room(room.id)
        wishes_per_user = 5 if room.is_paid else 1
        
        return {
            'id': room.id,
            'code': room.code,
            'name': room.name,
            'max_participants': room.max_participants,
            'current_users': current_users,
            'wishes_per_user': wishes_per_user,
            'is_paid': room.is_paid
        }
    except Exception as e:
        logger.error(f"Ошибка при получении деталей комнаты: {e}")
        return None
    finally:
        session.close()


def room_exists(room_id: int) -> bool:
    """Проверяет существование комнаты"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        return room is not None
    finally:
        session.close()


def mark_wish_as_viewed(wish_id: int) -> bool:
    """Отмечает желание как просмотренное"""
    session = Session()
    try:
        wish = session.query(Wish).filter(Wish.id == wish_id).first()
        if not wish:
            return False
        
        wish.is_viewed = True
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def get_all_active_rooms() -> list:
    """Получает список всех активных комнат"""
    session = Session()
    try:
        rooms = session.query(Room).all()
        return [
            {
                'room_id': room.id,
                'name': room.name,
                'max_users': room.max_participants,
                'creator_id': room.creator_id,
                'is_paid': room.is_paid,
                'current_users': count_users_in_room(room.id)
            }
            for room in rooms
        ]
    finally:
        session.close()


def get_user_room(user_id: int) -> dict:
    """Получить информацию о комнате пользователя"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.room:
            return {
                'room_id': 0,
                'name': '',
                'is_paid': False
            }
        
        room = user.room
        return {
            'room_id': room.id,
            'name': room.name,
            'is_paid': room.is_paid
        }
    finally:
        session.close()


def count_user_wishes(user_id: int) -> int:
    """Подсчитать количество желаний пользователя"""
    session = Session()
    try:
        return session.query(Wish).filter(Wish.user_id == user_id).count()
    finally:
        session.close()


def get_room_id_by_code(room_code: str) -> int:
    """Получает ID комнаты по её коду"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.code == room_code).first()
        return room.id if room else 0
    finally:
        session.close()
