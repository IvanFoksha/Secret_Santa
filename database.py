import os
import logging
import random
import string
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, Index, Text, Table, and_
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import current_config
from typing import Optional, Dict, Any, List, Union

logger = logging.getLogger(__name__)

Base = declarative_base()

# Таблица связи между пользователями и комнатами
user_room_association = Table(
    'user_room_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('room_id', Integer, ForeignKey('rooms.id'), primary_key=True),
    Column('joined_at', DateTime, default=datetime.utcnow)
)

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
    joined_rooms = relationship("Room", secondary=user_room_association, back_populates="joined_users")
    wishes = relationship("Wish", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_telegram_room', 'telegram_id', 'room_id'),
    )


class Room(Base):
    __tablename__ = 'rooms'
    
    id = Column(Integer, primary_key=True)
    code = Column(
        String(10), 
        unique=True, 
        nullable=False, 
        index=True
    )
    creator_id = Column(
        Integer, 
        ForeignKey('users.id'), 
        nullable=False, 
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    is_paid = Column(Boolean, default=False)
    max_participants = Column(Integer, default=5)
    description = Column(Text, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    creator = relationship(
        "User", 
        back_populates="created_rooms", 
        foreign_keys=[creator_id]
    )
    users = relationship(
        "User", 
        back_populates="room", 
        foreign_keys="User.room_id"
    )
    joined_users = relationship("User", secondary=user_room_association, back_populates="joined_rooms")
    wishes = relationship(
        "Wish", 
        back_populates="room", 
        cascade="all, delete-orphan"
    )

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


def add_user(
    telegram_id: int,
    username: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> bool:
    """Добавляет нового пользователя в базу данных или обновляет 
    существующего"""
    session = Session()
    try:
        # Проверяем, существует ли пользователь
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if user:
            # Обновляем информацию о пользователе
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            session.commit()
            logger.info(
                f"Пользователь {telegram_id} обновлен"
            )
        else:
            # Создаем нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            session.commit()
            logger.info(
                f"Пользователь {telegram_id} добавлен"
            )
        
        return True
    except Exception as e:
        logger.error(
            f"Ошибка при работе с пользователем: {e}"
        )
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


async def create_room(creator_id: int) -> Optional[int]:
    """Создает новую комнату и возвращает её ID"""
    session = Session()
    try:
        # Проверяем, есть ли у пользователя уже созданная комната
        if user_has_room(creator_id):
            logger.warning(f"Пользователь {creator_id} попытался создать вторую комнату")
            return None
            
        # Сначала проверяем/создаем пользователя
        user = session.query(User).filter(User.telegram_id == creator_id).first()
        if not user:
            user = User(telegram_id=creator_id)
            session.add(user)
            session.commit()
            logger.info(f"Создан новый пользователь: {creator_id}")
        
        # Генерируем уникальный код комнаты
        room_code = generate_room_code()
        logger.info(f"Сгенерирован код комнаты: {room_code}")
        
        # Создаем новую комнату
        new_room = Room(
            code=room_code,
            creator_id=user.id,
            is_active=True,
            max_participants=5,  # Бесплатная версия
        )
        session.add(new_room)
        session.commit()
        
        # Привязываем пользователя к комнате
        user.room_id = new_room.id
        session.commit()
        
        logger.info(f"Создана новая комната {new_room.id} для пользователя {creator_id}")
        return new_room.id
        
    except Exception as e:
        logger.error(f"Ошибка при создании комнаты: {str(e)}")
        session.rollback()
        return None
    finally:
        session.close()


async def update_room_version(room_id: int, version: str) -> bool:
    """Обновляет версию комнаты (free/pro)"""
    try:
        session = Session()
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return False
            
        if version == "pro":
            room.is_paid = True
            room.max_participants = PRO_MAX_USERS
        else:
            room.is_paid = False
            room.max_participants = FREE_MAX_USERS
            
        session.commit()
        session.close()
        return True
    except Exception as e:
        logger.error(f"Error updating room version: {e}")
        if session:
            session.rollback()
            session.close()
        return False


async def get_user_rooms_count(user_id: int) -> int:
    """Возвращает общее количество комнат пользователя (созданных и присоединенных)"""
    try:
        session = Session()
        # Находим пользователя в БД
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"Пользователь с ID {user_id} не найден в БД")
            session.close()
            return 0
            
        # Считаем комнаты, созданные пользователем
        created_rooms = session.query(Room).filter(Room.creator_id == user.id).count()
        logger.info(f"Пользователь {user_id} создал {created_rooms} комнат")
        
        # Проверяем, присоединился ли пользователь к какой-то комнате
        joined_rooms = 0
        if user.room_id:
            # Проверяем, не является ли эта комната созданной пользователем
            room = session.query(Room).filter(Room.id == user.room_id).first()
            if room and room.creator_id != user.id:
                joined_rooms = 1
                logger.info(f"Пользователь {user_id} присоединился к комнате {user.room_id}")
        
        total_rooms = created_rooms + joined_rooms
        logger.info(f"Всего комнат у пользователя {user_id}: {total_rooms}")
        
        session.close()
        return total_rooms
    except Exception as e:
        logger.error(f"Ошибка при подсчете комнат пользователя {user_id}: {e}")
        if session:
            session.close()
        return 0


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
    """Добавляет новое желание в базу данных"""
    session = Session()
    try:
        # Получаем пользователя
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return 0
            
        # Проверяем, что пользователь состоит в комнате
        if not user.room_id:
            logger.error(f"Пользователь {user_id} не состоит в комнате")
            return 0
            
        # Создаем новое желание
        wish = Wish(
            text=wish_text,
            user_id=user_id,
            room_id=user.room_id
        )
        session.add(wish)
        session.commit()
        
        logger.info(f"Добавлено желание для пользователя {user_id}")
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


def get_wish(wish_id: int) -> Optional[Dict[str, Any]]:
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


def get_user_wishes(user_id: int, room_id: Optional[int] = None) -> List[Dict[str, Any]]:
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
    """Получает список всех комнат пользователя с детальной информацией"""
    session = Session()
    try:
        # Находим пользователя
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.error(f"Пользователь {telegram_id} не найден")
            return []
        
        all_rooms = []
        
        # 1. Получаем комнаты, где пользователь является создателем
        created_rooms = session.query(Room).filter(Room.creator_id == user.id).all()
        logger.info(f"Найдено созданных комнат: {len(created_rooms)}")
        
        for room in created_rooms:
            # Получаем список участников комнаты
            participants = session.query(User).filter(User.room_id == room.id).all()
            participants_info = [
                {
                    'telegram_id': p.telegram_id,
                    'username': p.username,
                    'first_name': p.first_name,
                    'last_name': p.last_name
                } for p in participants
            ]
            
            all_rooms.append({
                'id': room.id,
                'code': room.code,
                'name': f"Комната {room.code}",
                'is_creator': True,
                'is_active': room.is_active,
                'is_paid': room.is_paid,
                'max_participants': room.max_participants,
                'current_users': len(participants),
                'participants': participants_info,
                'created_at': room.created_at.isoformat() if room.created_at else None,
                'is_current': user.room_id == room.id
            })
        
        # 2. Получаем комнаты, к которым пользователь присоединился
        joined_rooms = session.query(Room).join(
            user_room_association, user_room_association.c.room_id == Room.id
        ).filter(
            user_room_association.c.user_id == user.id,
            Room.creator_id != user.id
        ).all()
        
        logger.info(f"Найдено присоединенных комнат: {len(joined_rooms)}")
        
        for joined_room in joined_rooms:
            # Получаем список участников комнаты
            participants = session.query(User).filter(User.room_id == joined_room.id).all()
            participants_info = [
                {
                    'telegram_id': p.telegram_id,
                    'username': p.username,
                    'first_name': p.first_name,
                    'last_name': p.last_name
                } for p in participants
            ]
            
            all_rooms.append({
                'id': joined_room.id,
                'code': joined_room.code,
                'name': f"Комната {joined_room.code}",
                'is_creator': False,
                'is_active': joined_room.is_active,
                'is_paid': joined_room.is_paid,
                'max_participants': joined_room.max_participants,
                'current_users': len(participants),
                'participants': participants_info,
                'created_at': joined_room.created_at.isoformat() if joined_room.created_at else None,
                'is_current': user.room_id == joined_room.id
            })
        
        # 3. Если у пользователя есть текущая комната, но она не в списке, добавляем её
        if user.room_id:
            current_room = session.query(Room).filter(Room.id == user.room_id).first()
            if current_room and not any(room['id'] == current_room.id for room in all_rooms):
                participants = session.query(User).filter(User.room_id == current_room.id).all()
                participants_info = [
                    {
                        'telegram_id': p.telegram_id,
                        'username': p.username,
                        'first_name': p.first_name,
                        'last_name': p.last_name
                    } for p in participants
                ]
                
                all_rooms.append({
                    'id': current_room.id,
                    'code': current_room.code,
                    'name': f"Комната {current_room.code}",
                    'is_creator': current_room.creator_id == user.id,
                    'is_active': current_room.is_active,
                    'is_paid': current_room.is_paid,
                    'max_participants': current_room.max_participants,
                    'current_users': len(participants),
                    'participants': participants_info,
                    'created_at': current_room.created_at.isoformat() if current_room.created_at else None,
                    'is_current': True
                })
        
        logger.info(f"Всего найдено комнат пользователя: {len(all_rooms)}")
        return all_rooms
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка комнат: {str(e)}")
        return []
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


def get_room_by_id(room_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о комнате по ID"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return None
            
        return {
            'id': room.id,
            'code': room.code,
            'name': f"Комната {room.code}",
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
    """Получает все желания в комнате"""
    session = Session()
    try:
        wishes = session.query(Wish).filter(
            Wish.room_id == room_id
        ).all()
        
        return [
            {
                'id': wish.id,
                'text': wish.text,
                'user_id': wish.user_id,
                'created_at': wish.created_at,
                'is_viewed': wish.is_viewed
            }
            for wish in wishes
        ]
    except Exception as e:
        logger.error(f"Ошибка при получении желаний комнаты: {e}")
        return []
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


def get_room_details(room_identifier: Union[str, int]) -> Optional[Dict[str, Any]]:
    """Получает детали комнаты по её ID или коду"""
    session = Session()
    try:
        # Пытаемся найти комнату по коду, если идентификатор - строка
        if isinstance(room_identifier, str):
            room = session.query(Room).filter(
                Room.code == room_identifier
            ).first()
        # Иначе ищем по ID
        else:
            room = session.query(Room).filter(
                Room.id == room_identifier
            ).first()
        
        if not room:
            return None
        
        current_users = count_users_in_room(room.id)
        wishes_per_user = 5 if room.is_paid else 1
        
        return {
            'id': room.id,
            'code': room.code,
            'name': f"Комната {room.code}",
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
                'code': room.code,
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
                'code': '',
                'is_paid': False,
                'max_wishes': 0,
                'current_users': 0,
                'max_participants': 0
            }
        
        room = user.room
        return {
            'room_id': room.id,
            'code': room.code,
            'is_paid': room.is_paid,
            'max_wishes': room.max_wishes,
            'current_users': count_users_in_room(room.id),
            'max_participants': room.max_participants
        }
    finally:
        session.close()


def count_user_wishes(user_id: int, room_id: Optional[int] = None) -> int:
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


def get_room_by_code(code: str) -> Optional[Dict[str, Any]]:
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


def switch_room(user_id: int, room_id: int) -> bool:
    """Переключает текущую комнату пользователя"""
    session = Session()
    try:
        # Находим пользователя
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return False
            
        # Находим комнату
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.error(f"Комната {room_id} не найдена")
            return False
            
        # Проверяем, является ли пользователь создателем комнаты или участником
        is_creator = room.creator_id == user.id
        is_participant = session.query(user_room_association).filter(
            user_room_association.c.user_id == user.id,
            user_room_association.c.room_id == room_id
        ).first() is not None
        
        if not (is_creator or is_participant):
            logger.error(f"Пользователь {user_id} не имеет доступа к комнате {room_id}")
            return False
            
        # Обновляем текущую комнату пользователя
        user.room_id = room_id
        session.commit()
        
        logger.info(f"Пользователь {user_id} переключился на комнату {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при переключении комнаты: {str(e)}")
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


def get_room_statistics(room_id: int) -> Optional[Dict[str, Any]]:
    """Получает статистику комнаты"""
    session = Session()
    try:
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return None
            
        # Подсчитываем количество пользователей
        users_count = session.query(User).filter(
            User.room_id == room_id
        ).count()
        
        # Подсчитываем количество желаний
        wishes_count = session.query(Wish).filter(
            Wish.room_id == room_id
        ).count()
        
        # Подсчитываем просмотренные желания
        viewed_wishes = session.query(Wish).filter(
            Wish.room_id == room_id,
            Wish.is_viewed.is_(True)
        ).count()
        
        return {
            'id': room.id,
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
        if not user:
            return False, "Пользователь не найден"
            
        # Проверяем, не состоит ли пользователь уже в этой комнате
        already_joined = session.query(user_room_association).filter(
            user_room_association.c.user_id == user.id,
            user_room_association.c.room_id == room_id
        ).first()
        
        if already_joined:
            return False, "Вы уже состоите в этой комнате"
            
        # Проверяем общее количество комнат пользователя
        # (созданных и присоединенных)
        created_rooms = session.query(Room).filter(
            Room.creator_id == user.id
        ).count()
        
        # Проверяем количество присоединенных комнат через таблицу связи
        joined_rooms = session.query(user_room_association).filter(
            user_room_association.c.user_id == user.id
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
            
        # Подключаем к комнате через таблицу связи
        stmt = user_room_association.insert().values(
            user_id=user.id,
            room_id=room_id
        )
        session.execute(stmt)
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


def delete_room(room_id: int, user_id: int) -> bool:
    """Удаляет комнату, если пользователь является ее создателем"""
    session = Session()
    try:
        # Находим пользователя
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return False
            
        # Находим комнату
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.error(f"Комната {room_id} не найдена")
            return False
            
        # Проверяем, является ли пользователь создателем комнаты
        if room.creator_id != user.id:
            logger.error(f"Пользователь {user_id} не является создателем комнаты {room_id}")
            return False
            
        # Получаем всех пользователей в комнате
        users_in_room = session.query(User).filter(User.room_id == room_id).all()
        
        # Удаляем пользователей из комнаты
        for u in users_in_room:
            logger.info(f"Удаляем пользователя {u.telegram_id} из комнаты {room_id}")
            u.room_id = None
            
        # Удаляем связанные желания
        wishes = session.query(Wish).filter(Wish.room_id == room_id).all()
        for wish in wishes:
            logger.info(f"Удаляем желание {wish.id} из комнаты {room_id}")
            session.delete(wish)
            
        # Удаляем комнату
        logger.info(f"Удаляем комнату {room_id}")
        session.delete(room)
        session.commit()
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при удалении комнаты {room_id}: {e}")
        session.rollback()
        return False
    finally:
        session.close()


# Константы для лимитов
MAX_ROOMS_PER_USER = 3
FREE_MAX_USERS = 5
PRO_MAX_USERS = 10
FREE_MAX_WISHES = 1
PRO_MAX_WISHES = 5


def get_room_participants(room_id: int) -> Dict[str, Any]:
    """Получает информацию об участниках комнаты"""
    session = Session()
    try:
        # Проверяем существование комнаты
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.error(f"Комната {room_id} не найдена")
            return {
                'success': False,
                'error': 'Комната не найдена',
                'participants': []
            }
        
        # Получаем всех участников комнаты
        participants = session.query(User).filter(
            User.room_id == room_id
        ).all()
        
        # Формируем информацию об участниках
        participants_info = []
        for user in participants:
            # Получаем количество желаний пользователя
            wishes_count = session.query(Wish).filter(
                Wish.user_id == user.id,
                Wish.room_id == room_id
            ).count()
            
            participants_info.append({
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_creator': user.id == room.creator_id,
                'wishes_count': wishes_count,
                'joined_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return {
            'success': True,
            'room_id': room_id,
            'room_code': room.code,
            'total_participants': len(participants),
            'max_participants': room.max_participants,
            'is_paid': room.is_paid,
            'participants': participants_info
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении участников комнаты: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'participants': []
        }
    finally:
        session.close()


def leave_room(user_id: int, room_id: int) -> tuple[bool, str]:
    """Отключает пользователя от комнаты"""
    session = Session()
    try:
        # Получаем пользователя
        user = session.query(User).filter(
            User.telegram_id == user_id
        ).first()
        if not user:
            return False, "Пользователь не найден"
            
        # Проверяем, состоит ли пользователь в комнате
        room = session.query(Room).filter(Room.id == room_id).first()
        if not room:
            return False, "Комната не найдена"
            
        # Проверяем, является ли пользователь создателем комнаты
        if room.creator_id == user.id:
            return False, "Создатель не может покинуть комнату"
            
        # Удаляем связь пользователя с комнатой
        session.execute(
            user_room_association.delete().where(
                and_(
                    user_room_association.c.user_id == user.id,
                    user_room_association.c.room_id == room_id
                )
            )
        )
        
        # Обновляем время последней активности комнаты
        room.last_activity = datetime.utcnow()
        
        session.commit()
        logger.info(
            f"Пользователь {user_id} отключился от комнаты {room_id}"
        )
        return True, "Вы успешно покинули комнату"
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при отключении от комнаты: {e}")
        return False, "Ошибка при отключении от комнаты"
    finally:
        session.close()


def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """
    Получает пользователя по его Telegram ID
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        User: Объект пользователя или None, если пользователь не найден
    """
    try:
        session = Session()
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return user
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя по Telegram ID {telegram_id}: {str(e)}")
        return None
    finally:
        session.close()


def check_user_in_room(telegram_id: int, room_id: int) -> bool:
    """
    Проверяет, является ли пользователь участником комнаты
    
    Args:
        telegram_id: Telegram ID пользователя
        room_id: ID комнаты
        
    Returns:
        bool: True, если пользователь является участником комнаты, иначе False
    """
    try:
        session = Session()
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
            
        # Проверяем, является ли пользователь создателем комнаты
        room = session.query(Room).filter(Room.id == room_id).first()
        if room and room.creator_id == user.id:
            return True
            
        # Проверяем, является ли пользователь участником комнаты через таблицу связи
        association = session.query(user_room_association).filter(
            user_room_association.c.user_id == user.id,
            user_room_association.c.room_id == room_id
        ).first()
        
        return association is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке участия пользователя {telegram_id} в комнате {room_id}: {str(e)}")
        return False
    finally:
        session.close()
