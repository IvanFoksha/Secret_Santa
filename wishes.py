import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    add_wish, get_user_room, get_user_wishes, update_wish, get_wish,
    Session, User, Wish, Room, count_users_in_room
)
from keyboards import get_wish_actions_keyboard
from datetime import datetime, time
import asyncio

logger = logging.getLogger(__name__)


def get_main_menu_keyboard():
    """Создает основную клавиатуру меню"""
    keyboard = [
        [InlineKeyboardButton("📝 Добавить желание", callback_data="add_wish")],
        [InlineKeyboardButton("✏️ Редактировать желания", callback_data="edit_wish")],
        [InlineKeyboardButton("📋 Мои желания", callback_data="list_wishes")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def create_wish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик создания желания"""
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} создает желание")
    
    # Проверяем, состоит ли пользователь в комнате
    user_room = get_user_room(user_id)
    if not user_room or not user_room.get('room_id'):
        await update.callback_query.message.reply_text(
            "Вы не состоите в комнате. Сначала присоединитесь к комнате или создайте новую."
        )
        return ConversationHandler.END
        
    # Запрашиваем текст желания
    await update.callback_query.message.reply_text(
        "Пожалуйста, введите текст вашего желания:"
    )
    context.user_data['waiting_for'] = 'wish'
    return ConversationHandler.END


async def handle_wish_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста желания"""
    if not context.user_data.get('waiting_for') == 'wish':
        return
        
    user_id = update.effective_user.id
    wish_text = update.message.text
    
    # Проверяем, состоит ли пользователь в комнате
    user_room = get_user_room(user_id)
    if not user_room or not user_room.get('room_id'):
        await update.message.reply_text(
            "Вы не состоите в комнате. Сначала присоединитесь к комнате или создайте новую."
        )
        return
        
    room_id = user_room['room_id']
    
    # Сохраняем желание
    success, message_text = add_wish(room_id, user_id, wish_text)
    
    if success:
        await update.message.reply_text(
            "✅ Желание успешно добавлено!",
            reply_markup=get_wish_actions_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Не удалось добавить желание: {message_text}\n"
            "Проверьте, что вы состоите в комнате и не превышен лимит желаний."
        )
    
    # Если достигнут лимит желаний, показываем меню
    if not success and "превышен лимит желаний" in message_text.lower():
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
    
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
    """Показывает список желаний пользователя в текущей комнате"""
    user_id = update.effective_user.id
    
    session = Session()
    try:
        # Находим пользователя
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.room_id:
            await update.callback_query.message.reply_text(
                "❌ Вы не состоите ни в одной комнате."
            )
            return
            
        # Находим комнату
        room = session.query(Room).filter(Room.id == user.room_id).first()
        if not room:
            await update.callback_query.message.reply_text(
                "❌ Комната не найдена. Возможно, она была удалена."
            )
            return
            
        # Получаем желания пользователя в текущей комнате
        wishes = get_user_wishes(user_id, user.room_id)
        
        if not wishes:
            await update.callback_query.message.reply_text(
                "📝 У вас пока нет желаний в этой комнате.",
                reply_markup=get_wish_actions_keyboard()
            )
            return
        
        message = f"📋 Ваши желания в комнате {room.code}:\n\n"
        for i, wish in enumerate(wishes, 1):
            message += f"{i}. {wish['text']}\n"
        
        # Добавляем информацию о комнате
        message += f"\n🏠 Комната {room.code}\n"
        message += f"🎁 Максимум желаний: {10 if room.is_paid else 3}\n"
        message += f"👥 Участников: {count_users_in_room(room.id)}/{room.max_participants}\n"
        
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


async def send_daily_wishes(context: ContextTypes.DEFAULT_TYPE):
    """Функция для ежедневной рассылки желаний"""
    logger.info("Начало ежедневной рассылки желаний")
    session = Session()
    try:
        # Получаем все комнаты
        rooms = session.query(Room).all()
        
        for room in rooms:
            # Получаем всех пользователей в комнате
            users = session.query(User).filter(User.room_id == room.id).all()
            
            for user in users:
                # Получаем желания пользователя
                wishes = session.query(Wish).filter(
                    Wish.user_id == user.id,
                    Wish.room_id == room.id
                ).all()
                
                if wishes:
                    # Формируем сообщение с желаниями
                    message = f"🎁 Желания пользователя {user.username or 'Аноним'}:\n\n"
                    for wish in wishes:
                        message += f"• {wish.text}\n"
                    
                    # Отправляем желания всем пользователям в комнате
                    for recipient in users:
                        if recipient.id != user.id:  # Не отправляем пользователю его собственные желания
                            try:
                                await context.bot.send_message(
                                    chat_id=recipient.telegram_id,
                                    text=message
                                )
                            except Exception as e:
                                logger.error(f"Ошибка при отправке желаний пользователю {recipient.telegram_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при рассылке желаний: {e}")
    finally:
        session.close()


async def schedule_wishes(context: ContextTypes.DEFAULT_TYPE):
    """Планировщик для ежедневной рассылки желаний"""
    while True:
        now = datetime.now().time()
        target_time = time(0, 0)  # 00:00
        
        # Вычисляем время до следующей рассылки
        if now >= target_time:
            # Если текущее время больше или равно целевому, ждем до следующего дня
            next_run = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            next_run = next_run.replace(day=next_run.day + 1)
        else:
            # Иначе ждем до сегодняшнего целевого времени
            next_run = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ждем до следующего запуска
        await asyncio.sleep((next_run - datetime.now()).total_seconds())
        
        # Запускаем рассылку
        await send_daily_wishes(context)
