import os
import logging
import random
import string
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, Index, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import current_config

logger = logging.getLogger(__name__)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(32))
    first_name = Column(String(64))
    last_name = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), index=True)
    
    # Связи
    room = relationship("Room", back_populates="users", foreign_keys=[room_id])
    created_rooms = relationship("Room", back_populates="creator", foreign_keys="Room.creator_id")
    wishes = relationship("Wish", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_telegram_room', 'telegram_id', 'room_id'),
    )


class Room(Base):
    __tablename__ = 'rooms'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    is_paid = Column(Boolean, default=False)
    max_participants = Column(Integer, default=10)
    max_wishes = Column(Integer, default=3)
    description = Column(Text, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    creator = relationship("User", back_populates="created_rooms", foreign_keys=[creator_id])
    users = relationship("User", back_populates="room", foreign_keys="User.room_id")
    wishes = relationship("Wish", back_populates="room", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_room_code_active', 'code', 'is_active'),
        Index('idx_room_creator', 'creator_id', 'is_active'),
    )


class Wish(Base):
    __tablename__ = 'wishes'
    
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_viewed = Column(Boolean, default=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    room_id = Column(Integer, ForeignKey('rooms.id'), index=True)
    
    # Связи
    user = relationship("User", back_populates="wishes")
    room = relationship("Room", back_populates="wishes")

    __table_args__ = (
        Index('idx_wish_user_room', 'user_id', 'room_id'),
        Index('idx_wish_room_viewed', 'room_id', 'is_viewed'),
    )


# Создаем подключение к базе данных
engine = create_engine(
    f'sqlite:///{current_config.DB_PATH}',
    connect_args={'check_same_thread': False}
)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def init_bd():
    """Проверяет существование файла базы данных и создает его, 
    если он не существует"""
    db_path = current_config.DB_PATH
    db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
    
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Создаем файл базы данных, если он не существует
    if not os.path.exists(db_path):
        open(db_path, 'w').close()
    
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


def create_room(
    name: str,
    creator_id: int,
    max_participants: int,
    is_paid: bool = False
) -> int:
    """Создает новую комнату и возвращает её ID"""
    session = Session()
    try:
        logger.info(
            f"Начало создания комнаты: name={name}, "
            f"creator_id={creator_id}, "
            f"max_participants={max_participants}, "
            f"is_paid={is_paid}"
        )
        
        # Проверяем существование пользователя
        user = session.query(User).filter(
            User.telegram_id == creator_id
        ).first()
        if not user:
            logger.info(
                f"Пользователь {creator_id} не найден, создаем нового"
            )
            user = User(telegram_id=creator_id)
            session.add(user)
            session.commit()
        
        # Проверяем количество комнат пользователя (созданных и присоединенных)
        created_rooms_count = session.query(Room).filter(Room.creator_id == user.id).count()
        joined_rooms_count = session.query(User).filter(
            User.telegram_id == creator_id,
            User.room_id.isnot(None)
        ).count()
        
        total_rooms = created_rooms_count + joined_rooms_count
        if total_rooms >= 3:  # Максимум 3 комнаты на пользователя
            logger.error(f"Пользователь {creator_id} достиг лимита комнат (3)")
            return 0
        
        # Устанавливаем лимиты в зависимости от типа комнаты
        if is_paid:
            max_participants = min(max_participants, current_config.MAX_PAID_USERS)
            max_wishes = current_config.MAX_PAID_WISHES
        else:
            max_participants = min(max_participants, current_config.MAX_FREE_USERS)
            max_wishes = current_config.MAX_FREE_WISHES
        
        # Генерируем уникальный код комнаты
        room_code = generate_room_code()
        logger.info(f"Сгенерирован код комнаты: {room_code}")
        
        # Создаем новую комнату
        new_room = Room(
            name=name,
            code=room_code,
            creator_id=user.id,  # Используем ID пользователя из базы
            max_participants=max_participants,
            is_paid=is_paid,
            max_wishes=max_wishes
        )
        
        session.add(new_room)
        session.commit()
        
        room_id = new_room.id
        logger.info(f"Комната успешно создана с ID: {room_id}")
        
        # Автоматически добавляем создателя в комнату
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
        
        # Проверяем, сколько комнат у пользователя
        user_rooms_count = session.query(User).filter(
            User.telegram_id == user_id,
            User.room_id.isnot(None)
        ).count()
        
        if user_rooms_count >= 3:
            logger.error(f"Пользователь {user_id} уже состоит в 3 комнатах")
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
        # 1. Находим пользователя по telegram_id
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"Пользователь с telegram_id {user_id} не найден")
            return 0
            
        # 2. Проверяем, состоит ли пользователь в комнате
        if not user.room_id:
            logger.error(f"Пользователь {user_id} не состоит в комнате")
            return 0
            
        # 3. Получаем комнату пользователя
        room = session.query(Room).filter(Room.id == user.room_id).first()
        if not room:
            logger.error(f"Комната {user.room_id} не найдена")
            return 0
            
        # 4. Проверяем количество желаний пользователя в этой комнате
        current_wishes = session.query(Wish).filter(
            Wish.user_id == user.id,
            Wish.room_id == room.id
        ).count()
        
        if current_wishes >= room.max_wishes:
            logger.error(f"Достигнут лимит желаний для пользователя {user_id} в комнате {room.id}")
            return 0
            
        # 5. Создаем новое желание
        new_wish = Wish(
            text=wish_text,
            user_id=user.id,
            room_id=room.id
        )
        
        # 6. Добавляем желание в сессию и сохраняем
        session.add(new_wish)
        session.commit()
        
        logger.info(f"Желание успешно добавлено для пользователя {user_id} в комнату {room.id}")
        return new_wish.id
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении желания: {str(e)}")
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


def get_wish(wish_id: int) -> dict:
    """Получает желание по ID"""
    session = Session()
    try:
        wish = session.query(Wish).filter(Wish.id == wish_id).first()
        if not wish:
            return None
        
        return {
            'id': wish.id,
            'user_id': wish.user_id,
            'text': wish.text,
            'room_id': wish.room_id,
            'created_at': wish.created_at
        }
    except Exception as e:
        logger.error(f"Ошибка при получении желания {wish_id}: {e}")
        return None
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


def get_user_wishes(user_id: int, room_id: int = None) -> list:
    """Получает список желаний пользователя в указанной комнате или все желания"""
    session = Session()
    try:
        # Сначала получаем пользователя по telegram_id
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"Пользователь с telegram_id {user_id} не найден")
            return []
            
        # Теперь ищем желания по user_id
        query = session.query(Wish).filter(Wish.user_id == user.id)
        
        # Если указана комната, фильтруем по ней
        if room_id is not None:
            query = query.filter(Wish.room_id == room_id)
            
        wishes = query.all()
        return [
            {
                'id': wish.id,
                'text': wish.text,
                'is_viewed': wish.is_viewed,
                'room_id': wish.room_id
            }
            for wish in wishes
        ]
    except Exception as e:
        logger.error(f"Ошибка при получении желаний пользователя: {e}")
        return []
    finally:
        session.close()


def get_all_rooms(telegram_id: int) -> list:
    """Получает список всех комнат пользователя"""
    session = Session()
    try:
        # Сначала находим пользователя по telegram_id
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
            
        # Затем находим все комнаты, где пользователь является создателем
        rooms = session.query(Room).filter(Room.creator_id == user.id).all()
        return [
            {
                'id': room.id,
                'name': room.name,
                'max_participants': room.max_participants,
                'is_paid': room.is_paid,
                'current_users': count_users_in_room(room.id)
            }
            for room in rooms
        ]
    finally:
        session.close()


def count_user_rooms(telegram_id: int) -> int:
    """Подсчитывает количество комнат, созданных пользователем"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return 0
        return session.query(Room).filter(Room.creator_id == user.id).count()
    finally:
        session.close()


def get_room_by_id(room_id: int) -> dict:
    """Получает информацию о комнате по ID"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return None
            
        return {
            'id': room.id,
            'name': room.name,
            'code': room.code,
            'max_participants': room.max_participants,
            'is_paid': room.is_paid,
            'current_users': count_users_in_room(room.id),
            'creator_id': room.creator_id
        }
    finally:
        session.close()


def switch_to_room(telegram_id: int, room_id: int) -> bool:
    """Переключает пользователя на указанную комнату"""
    session = Session()
    try:
        # Проверяем существование пользователя
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.error(f"Пользователь {telegram_id} не найден")
            return False
            
        # Проверяем существование комнаты
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.error(f"Комната {room_id} не найдена")
            return False
            
        # Проверяем, является ли пользователь создателем комнаты
        if room.creator_id != user.id:
            logger.error(
                f"Пользователь {telegram_id} не является создателем комнаты {room_id}"
            )
            return False
            
        # Переключаем пользователя на комнату
        user.room_id = room_id
        session.commit()
        logger.info(f"Пользователь {telegram_id} переключен на комнату {room_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при переключении на комнату: {str(e)}")
        session.rollback()
        return False
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
                'is_paid': False,
                'max_wishes': 0,
                'current_users': 0,
                'max_participants': 0
            }
        
        room = user.room
        return {
            'room_id': room.id,
            'name': room.name,
            'is_paid': room.is_paid,
            'max_wishes': room.max_wishes,
            'current_users': count_users_in_room(room.id),
            'max_participants': room.max_participants
        }
    finally:
        session.close()


def count_user_wishes(user_id: int, room_id: int = None) -> int:
    """Подсчитать количество желаний пользователя в указанной комнате или общее количество желаний"""
    session = Session()
    try:
        query = session.query(Wish).filter(Wish.user_id == user_id)
        
        # Если указана комната, фильтруем по ней
        if room_id is not None:
            query = query.filter(Wish.room_id == room_id)
            
        return query.count()
    finally:
        session.close()


def get_room_id_by_code(code: str) -> int:
    """Получает ID комнаты по её коду"""
    session = Session()
    try:
        # Преобразуем код в верхний регистр для поиска
        code = code.upper()
        logger.info(f"Поиск комнаты с кодом {code}")
        
        # Проверяем все существующие коды комнат для отладки
        all_codes = session.query(Room.code).all()
        code_list = [c[0] for c in all_codes]
        logger.info(f"Существующие коды комнат: {code_list}")
        
        # Ищем комнату по коду (без учета регистра)
        room = session.query(Room).filter(
            Room.code == code
        ).first()
        
        if not room:
            logger.error(f"Комната с кодом {code} не найдена")
            return 0
            
        logger.info(f"Найдена комната с ID {room.id}")
        return room.id
    except Exception as e:
        logger.error(
            f"Ошибка при получении ID комнаты по коду: {e}"
        )
        return 0
    finally:
        session.close()


def get_room_by_code(code: str) -> dict:
    """Поиск комнаты по коду с дополнительной информацией"""
    session = Session()
    try:
        # Преобразуем код в верхний регистр для поиска
        code = code.upper()
        logger.info(f"Поиск комнаты с кодом {code}")
        
        # Проверяем все существующие коды комнат для отладки
        all_codes = session.query(Room.code).all()
        code_list = [c[0] for c in all_codes]
        logger.info(f"Существующие коды комнат: {code_list}")
        
        # Ищем комнату по коду (без учета регистра)
        room = session.query(Room).filter(
            Room.code == code
        ).first()
        
        if not room:
            logger.info(f"Комната с кодом {code} не найдена")
            return None
            
        # Получаем дополнительную информацию о комнате
        users_count = session.query(User).filter(
            User.room_id == room.id
        ).count()
        
        return {
            'id': room.id,
            'name': room.name,
            'code': room.code,
            'creator_id': room.creator_id,
            'is_paid': room.is_paid,
            'max_participants': room.max_participants,
            'current_participants': users_count,
            'max_wishes': room.max_wishes,
            'is_active': room.is_active
        }
    except Exception as e:
        logger.error(f"Ошибка при поиске комнаты: {e}")
        return None
    finally:
        session.close()


def switch_room(telegram_id: int, room_id: int) -> bool:
    """Переключает пользователя на указанную комнату"""
    session = Session()
    try:
        # Проверяем существование пользователя
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.error(f"Пользователь {telegram_id} не найден")
            return False
            
        # Проверяем существование комнаты
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.error(f"Комната {room_id} не найдена")
            return False
            
        # Проверяем, является ли пользователь создателем комнаты
        if room.creator_id != user.id:
            logger.error(
                f"Пользователь {telegram_id} не является создателем комнаты {room_id}"
            )
            return False
            
        # Переключаем пользователя на комнату
        user.room_id = room_id
        session.commit()
        logger.info(f"Пользователь {telegram_id} переключен на комнату {room_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при переключении на комнату: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close()


def update_room_activity(room_id: int) -> bool:
    """Обновляет время последней активности комнаты"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.error(f"Комната {room_id} не найдена")
            return False
            
        room.last_activity = datetime.utcnow()
        session.commit()
        logger.info(f"Обновлено время активности комнаты {room_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении активности комнаты: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_room_statistics(room_id: int) -> dict:
    """Получает статистику комнаты"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return None
            
        # Подсчитываем количество пользователей
        users_count = session.query(User).filter(User.room_id == room_id).count()
        
        # Подсчитываем количество желаний
        wishes_count = session.query(Wish).filter(Wish.room_id == room_id).count()
        
        # Подсчитываем просмотренные желания
        viewed_wishes = session.query(Wish).filter(
            Wish.room_id == room_id,
            Wish.is_viewed == True
        ).count()
        
        return {
            'id': room.id,
            'name': room.name,
            'code': room.code,
            'is_paid': room.is_paid,
            'max_participants': room.max_participants,
            'current_participants': users_count,
            'max_wishes': room.max_wishes,
            'total_wishes': wishes_count,
            'viewed_wishes': viewed_wishes,
            'last_activity': room.last_activity,
            'created_at': room.created_at
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики комнаты: {e}")
        return None
    finally:
        session.close()


def check_room_limits(room_id: int) -> tuple[bool, str]:
    """Проверяет лимиты комнаты и возвращает статус и сообщение"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return False, "Комната не найдена"
            
        # Проверяем количество пользователей
        users_count = session.query(User).filter(User.room_id == room_id).count()
        if users_count >= room.max_participants:
            return False, "Достигнут лимит участников"
            
        # Проверяем количество желаний
        wishes_count = session.query(Wish).filter(Wish.room_id == room_id).count()
        if wishes_count >= (room.max_wishes * users_count):
            return False, "Достигнут лимит желаний"
            
        return True, "Лимиты в порядке"
    except Exception as e:
        logger.error(f"Ошибка при проверке лимитов комнаты: {e}")
        return False, "Ошибка при проверке лимитов"
    finally:
        session.close()


def can_join_room(room_id: int, user_id: int) -> tuple[bool, str]:
    """Проверяет возможность подключения пользователя к комнате"""
    session = Session()
    try:
        # Проверяем существование комнаты
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return False, "Комната не найдена"
            
        if not room.is_active:
            return False, "Комната неактивна"
            
        # Проверяем количество участников
        users_count = session.query(User).filter(
            User.room_id == room_id
        ).count()
        if users_count >= room.max_participants:
            return False, "Комната заполнена"
            
        # Проверяем, не состоит ли пользователь уже в комнате
        user = session.query(User).filter(
            User.telegram_id == user_id
        ).first()
        if user and user.room_id == room_id:
            return False, "Вы уже состоите в этой комнате"
            
        # Проверяем общее количество комнат пользователя
        # (созданных и присоединенных)
        created_rooms = session.query(Room).filter(
            Room.creator_id == user.id
        ).count()
        
        joined_rooms = session.query(User).filter(
            User.telegram_id == user_id,
            User.room_id.isnot(None)
        ).count()
        
        total_rooms = created_rooms + joined_rooms
        if total_rooms >= 3:
            return False, "Вы уже состоите в максимальном количестве комнат (3)"
            
        return True, "Можно подключиться"
    except Exception as e:
        logger.error(f"Ошибка при проверке возможности подключения: {e}")
        return False, "Ошибка при проверке"
    finally:
        session.close()


def join_room(room_id: int, user_id: int) -> tuple[bool, str]:
    """Подключает пользователя к комнате"""
    session = Session()
    try:
        # Проверяем возможность подключения
        can_join, message = can_join_room(room_id, user_id)
        if not can_join:
            return False, message
            
        # Получаем пользователя
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return False, "Пользователь не найден"
            
        # Подключаем к комнате
        user.room_id = room_id
        session.commit()
        
        # Обновляем время активности комнаты
        room = session.query(Room).filter(Room.id == room_id).first()
        room.last_activity = datetime.utcnow()
        session.commit()
        
        logger.info(f"Пользователь {user_id} успешно подключен к комнате {room_id}")
        return True, "Успешное подключение к комнате"
    except Exception as e:
        logger.error(f"Ошибка при подключении к комнате: {e}")
        session.rollback()
        return False, "Ошибка при подключении"
    finally:
        session.close()


def get_room_users(room_id: int) -> list[dict]:
    """Получает список пользователей в комнате"""
    try:
        with Session() as session:
            users = session.query(User).join(
                Room, User.room_id == Room.id
            ).filter(Room.id == room_id).all()
            
            return [
                {
                    'id': user.telegram_id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username
                }
                for user in users
            ]
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей комнаты: {str(e)}")
        return []
