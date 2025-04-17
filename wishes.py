import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import add_wish, get_user_wishes, get_user_room, update_wish, Session, engine, get_wish
from sqlalchemy.orm import Session as SQLAlchemySession
from database import User, Wish, Room
from telegram.ext import ConversationHandler
from keyboards import get_wish_actions_keyboard

logger = logging.getLogger(__name__)

def get_main_menu_keyboard():
    """Создает основную клавиатуру меню"""
    keyboard = [
        [InlineKeyboardButton("📝 Добавить желание", callback_data="add_wish")],
        [InlineKeyboardButton("✏️ Редактировать желания", callback_data="edit_wish")],
        [InlineKeyboardButton("📋 Мои желания", callback_data="list_wishes")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_wish_actions_keyboard():
    """Создает клавиатуру действий с желаниями"""
    keyboard = [
        [InlineKeyboardButton("📝 Добавить желание", callback_data="add_wish")],
        [InlineKeyboardButton("✏️ Редактировать желания", callback_data="edit_wish")],
        [InlineKeyboardButton("📋 Мои желания", callback_data="list_wishes")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def create_wish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик создания желания"""
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} создает желание")
    
    # Проверяем, состоит ли пользователь в комнате
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.room_id:
            await update.callback_query.message.reply_text(
                "Вы не состоите в комнате. Сначала присоединитесь к комнате или создайте новую."
            )
            return ConversationHandler.END
            
        # Проверяем количество желаний
        current_wishes = session.query(Wish).filter(
            Wish.user_id == user.id,
            Wish.room_id == user.room_id
        ).count()
        
        if current_wishes >= user.room.max_wishes:
            await update.callback_query.message.reply_text(
                f"Вы достигли лимита желаний ({user.room.max_wishes}). "
                "Удалите существующее желание, чтобы добавить новое."
            )
            return ConversationHandler.END
            
        # Запрашиваем текст желания
        await update.callback_query.message.reply_text(
            "Пожалуйста, введите текст вашего желания:"
        )
        context.user_data['waiting_for'] = 'wish'
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка при создании желания: {e}")
        await update.callback_query.message.reply_text(
            "Произошла ошибка при создании желания. Попробуйте еще раз."
        )
        return ConversationHandler.END
    finally:
        session.close()

async def handle_wish_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста желания"""
    if not context.user_data.get('waiting_for') == 'wish':
        return
        
    user_id = update.effective_user.id
    wish_text = update.message.text
    
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.room_id:
            await update.message.reply_text(
                "Вы не состоите в комнате. Сначала присоединитесь к комнате или создайте новую."
            )
            return
            
        # Проверяем количество желаний
        current_wishes = session.query(Wish).filter(
            Wish.user_id == user.id,
            Wish.room_id == user.room_id
        ).count()
        
        if current_wishes >= user.room.max_wishes:
            await update.message.reply_text(
                f"Вы достигли лимита желаний ({user.room.max_wishes}). "
                "Удалите существующее желание, чтобы добавить новое."
            )
            return
            
        # Сохраняем желание
        wish_id = add_wish(user_id, wish_text)
        
        if wish_id:
            await update.message.reply_text(
                "✅ Желание успешно добавлено!",
                reply_markup=get_wish_actions_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось добавить желание. "
                "Проверьте, что вы состоите в комнате и не превышен лимит желаний."
            )
    except Exception as e:
        logger.error(f"Ошибка при сохранении желания: {e}")
        await update.message.reply_text(
            "Произошла ошибка при сохранении желания. Попробуйте еще раз."
        )
    finally:
        session.close()
        context.user_data['waiting_for'] = None

async def edit_wish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования желаний"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        # Проверяем, есть ли у пользователя комната
        user_room = get_user_room(user_id)
        if not user_room:
            await query.message.reply_text(
                "❌ Вы не состоите ни в одной комнате. "
                "Сначала присоединитесь к комнате или создайте новую."
            )
            return
        
        # Получаем список желаний пользователя
        wishes = get_user_wishes(user_id, user_room['room_id'])
        if not wishes:
            await query.message.reply_text(
                "❌ У вас пока нет желаний. "
                "Сначала создайте хотя бы одно желание."
            )
            return
        
        # Создаем клавиатуру с желаниями для редактирования
        keyboard = []
        for wish in wishes:
            keyboard.append([InlineKeyboardButton(
                f"✏️ {wish['text'][:30]}...",
                callback_data=f"edit_wish_{wish['id']}"
            )])
        
        # Добавляем кнопку возврата в главное меню
        keyboard.append([InlineKeyboardButton(
            "🔙 Назад",
            callback_data="main_menu"
        )])
        
        await query.message.edit_text(
            "📝 Выберите желание для редактирования:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при редактировании желания: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при редактировании желания. "
            "Пожалуйста, попробуйте позже."
        )

async def list_wishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список желаний пользователя"""
    user_id = update.effective_user.id
    room = get_user_room(user_id)
    
    if not room or room['room_id'] == 0:
        await update.callback_query.message.reply_text(
            "❌ Вы не состоите ни в одной комнате."
        )
        return
    
    # Проверяем существование комнаты
    session = Session()
    try:
        db_room = session.query(Room).filter(Room.id == room['room_id']).first()
        if not db_room:
            await update.callback_query.message.reply_text(
                "❌ Комната не найдена. Возможно, она была удалена."
            )
            return
            
        wishes = get_user_wishes(user_id, room['room_id'])
        if not wishes:
            await update.callback_query.message.reply_text(
                "📝 У вас пока нет желаний.",
                reply_markup=get_wish_actions_keyboard()
            )
            return
        
        message = "📋 Ваши желания:\n\n"
        for i, wish in enumerate(wishes, 1):
            message += f"{i}. {wish['text']}\n"
        
        # Добавляем информацию о комнате
        message += f"\n🏠 {db_room.name}\n"
        message += f"🎁 Максимум желаний: {db_room.max_wishes}\n"
        message += (
            f"👥 Участников: {room['current_users']}/"
            f"{db_room.max_participants}\n"
        )
        
        # Используем готовую клавиатуру с действиями
        await update.callback_query.message.reply_text(
            message,
            reply_markup=get_wish_actions_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка желаний: {e}")
        await update.callback_query.message.reply_text(
            "❌ Произошла ошибка при получении списка желаний. "
            "Пожалуйста, попробуйте позже."
        )
    finally:
        session.close()

async def edit_specific_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования конкретного желания"""
    query = update.callback_query
    wish_id = int(query.data.split('_')[2])
    user = query.from_user
    
    try:
        # Получаем желание
        wish = get_wish(wish_id)
        if not wish:
            await query.message.reply_text(
                "❌ Желание не найдено. "
                "Возможно, оно было удалено."
            )
            return
            
        # Получаем пользователя из базы данных
        session = Session()
        db_user = session.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            await query.message.reply_text(
                "❌ Пользователь не найден в базе данных."
            )
            return
            
        # Проверяем, принадлежит ли желание пользователю
        if wish['user_id'] != db_user.id:
            await query.message.reply_text(
                "❌ Вы не можете редактировать чужие желания."
            )
            return
            
        # Сохраняем ID желания в контексте
        context.user_data['editing_wish_id'] = wish_id
        
        # Запрашиваем новый текст желания
        await query.message.edit_text(
            f"📝 Текущий текст желания:\n{wish['text']}\n\n"
            "Введите новый текст желания:"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при редактировании желания {wish_id}: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при редактировании желания. "
            "Пожалуйста, попробуйте позже."
        )
    finally:
        if 'session' in locals():
            session.close()

async def handle_edit_wish_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нового текста желания при редактировании"""
    if 'editing_wish_id' not in context.user_data:
        await update.message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз."
        )
        return
        
    wish_id = context.user_data['editing_wish_id']
    new_text = update.message.text
    user_id = update.effective_user.id
    
    try:
        # Получаем пользователя из базы данных
        session = Session()
        db_user = session.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text(
                "❌ Пользователь не найден в базе данных."
            )
            return
            
        # Получаем желание
        wish = get_wish(wish_id)
        if not wish:
            await update.message.reply_text(
                "❌ Желание не найдено. Возможно, оно было удалено."
            )
            return
            
        # Проверяем, принадлежит ли желание пользователю
        if wish['user_id'] != db_user.id:
            await update.message.reply_text(
                "❌ Вы не можете редактировать чужие желания."
            )
            return
            
        # Обновляем желание
        success = update_wish(wish_id, new_text)
        if success:
            await update.message.reply_text(
                "✅ Желание успешно обновлено!",
                reply_markup=get_wish_actions_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить желание. "
                "Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Ошибка при обновлении желания {wish_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении желания. "
            "Пожалуйста, попробуйте позже."
        )
    finally:
        # Очищаем контекст
        context.user_data.pop('editing_wish_id', None)
        if 'session' in locals():
            session.close()
