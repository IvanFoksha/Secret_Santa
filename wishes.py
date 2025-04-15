from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import add_wish, get_user_wishes, get_user_room, update_wish
import logging
from sqlalchemy.orm import Session
from database import User, Wish
from telegram.ext import ConversationHandler

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

def create_wish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик создания желания"""
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} создает желание")
    
    # Проверяем, состоит ли пользователь в комнате
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.room:
            update.message.reply_text(
                "Вы не состоите в комнате. Сначала присоединитесь к комнате или создайте новую."
            )
            return ConversationHandler.END
            
        # Проверяем количество желаний
        current_wishes = session.query(Wish).filter(Wish.user_id == user.id).count()
        if current_wishes >= user.room.max_wishes:
            update.message.reply_text(
                f"Вы достигли лимита желаний ({user.room.max_wishes}). "
                "Удалите существующее желание, чтобы добавить новое."
            )
            return ConversationHandler.END
            
        # Сохраняем текст желания
        wish_text = update.message.text
        wish_id = add_wish(user_id, wish_text)
        
        if wish_id:
            update.message.reply_text(
                "Ваше желание успешно добавлено! 🎉\n"
                f"Осталось желаний: {user.room.max_wishes - current_wishes - 1}"
            )
        else:
            update.message.reply_text(
                "Произошла ошибка при добавлении желания. Попробуйте еще раз."
            )
            
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при создании желания: {e}")
        update.message.reply_text(
            "Произошла ошибка при создании желания. Попробуйте еще раз."
        )
        return ConversationHandler.END
    finally:
        session.close()

async def handle_wish_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста желания"""
    user_id = update.effective_user.id
    wish_text = update.message.text
    
    if add_wish(user_id, wish_text):
        await update.message.reply_text(
            "✅ Желание успешно добавлено!",
            reply_markup=get_wish_actions_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось добавить желание. "
            "Проверьте, что вы состоите в комнате и не превышен лимит желаний."
        )
    
    context.user_data['state'] = None

async def edit_wish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования желания"""
    user_id = update.effective_user.id
    wishes = get_user_wishes(user_id)
    
    if not wishes:
        await update.callback_query.message.reply_text(
            "❌ У вас нет желаний для редактирования."
        )
        return
        
    keyboard = []
    for wish in wishes:
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ {wish.text[:30]}...",
                callback_data=f"edit_wish_{wish.id}"
            )
        ])
    
    await update.callback_query.message.reply_text(
        "Выберите желание для редактирования:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def list_wishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список желаний пользователя"""
    user_id = update.effective_user.id
    room = get_user_room(user_id)
    
    if not room:
        await update.callback_query.message.reply_text(
            "❌ Вы не состоите ни в одной комнате."
        )
        return
        
    wishes = get_user_wishes(user_id)
    if not wishes:
        await update.callback_query.message.reply_text(
            "📝 У вас пока нет желаний.",
            reply_markup=get_wish_actions_keyboard()
        )
        return
        
    message = "📋 Ваши желания:\n\n"
    for i, wish in enumerate(wishes, 1):
        message += f"{i}. {wish.text}\n"
        
    # Добавляем информацию о комнате
    message += f"\n🏠 Комната: {room['name']}\n"
    message += f"🎁 Максимум желаний: {room['wishes_per_user']}\n"
    message += f"👥 Участников: {room['current_users']}/{room['max_participants']}\n"
    
    # Создаем клавиатуру с кнопками для действий с желаниями
    keyboard = [
        [InlineKeyboardButton("📝 Добавить желание", callback_data="add_wish")],
        [InlineKeyboardButton("✏️ Редактировать желания", callback_data="edit_wish")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    await update.callback_query.message.reply_text(
        message,
        reply_markup=reply_markup
    )
