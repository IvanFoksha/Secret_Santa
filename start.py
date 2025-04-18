from telegram import Update
from telegram.ext import ContextTypes
from keyboards import get_main_menu_keyboard
from rooms import join_room, handle_room_creation
from wishes import create_wish, edit_wish_handler, list_wishes, handle_wish_text, handle_edit_wish_text, edit_specific_wish
from database import add_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    # Добавляем пользователя в базу данных
    add_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_message = (
        f"🎄 Привет, {user.first_name}! 🎅\n\n"
        "Я твой волшебный помощник в организации "
        "новогоднего обмена подарками! ✨\n\n"
        "Со мной ты сможешь:\n"
        "🎁 Создать волшебную комнату для обмена подарками\n"
        "👥 Присоединиться к друзьям в их комнате\n"
        "📝 Загадать свои новогодние желания\n\n"
        "Выбери действие в меню ниже и начнем создавать новогоднее чудо! 🎄✨"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🎄 *Как пользоваться ботом:*\n\n"
        "1. *Создание волшебной комнаты:*\n"
        "   - Нажми '🎁 Создать комнату'\n"
        "   - Выбери версию (бесплатная/PRO)\n"
        "   - Получи волшебный код комнаты\n\n"
        "2. *Присоединение к друзьям:*\n"
        "   - Нажми '🔍 Найти комнату'\n"
        "   - Введи волшебный код\n\n"
        "3. *Загадывание желаний:*\n"
        "   - Добавляй свои желания\n"
        "   - Редактируй их\n"
        "   - Смотри список желаний\n\n"
        "4. *Волшебные версии:*\n"
        "   - Бесплатная: до 10 участников, 1 желание\n"
        "   - PRO: до 50 участников, 5 желаний\n\n"
        "Нужна помощь? Обратись к волшебнику @admin ✨"
    )
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    # Пропускаем специализированные callback'и
    if query.data in ['free_version', 'pro_version']:
        return
    
    if query.data == 'create_room':
        await handle_room_creation(update, context)
    elif query.data == 'back_to_main':
        await query.message.edit_text(
            "Выберите действие из меню ниже 👇",
            reply_markup=get_main_menu_keyboard()
        )
    elif query.data == 'join_room':
        await join_room(update, context)
    elif query.data == 'create_wish' or query.data == 'add_wish':
        await create_wish(update, context)
    elif query.data == 'edit_wish':
        await edit_wish_handler(update, context)
    elif query.data.startswith('edit_wish_'):
        await edit_specific_wish(update, context)
    elif query.data == 'list_wishes':
        await list_wishes(update, context)
    elif query.data == 'help':
        # Отправляем сообщение с помощью
        help_text = (
            "🎄 *Как пользоваться ботом:*\n\n"
            "1. *Создание волшебной комнаты:*\n"
            "   - Нажми '🎁 Создать комнату'\n"
            "   - Выбери версию (бесплатная/PRO)\n"
            "   - Получи волшебный код комнаты\n\n"
            "2. *Присоединение к друзьям:*\n"
            "   - Нажми '🔍 Найти комнату'\n"
            "   - Введи волшебный код\n\n"
            "3. *Загадывание желаний:*\n"
            "   - Добавляй свои желания\n"
            "   - Редактируй их\n"
            "   - Просматривай желания друзей\n\n"
            "4. *Управление комнатами:*\n"
            "   - Создавай до 3 комнат\n"
            "   - Приглашай друзей\n"
            "   - Следи за активностью\n\n"
            "5. *Версии бота:*\n"
            "   - *Бесплатная:* до 5 участников, 3 желания\n"
            "   - *PRO:* до 10 участников, 10 желаний\n\n"
            "❓ *Нужна помощь?* Напиши /help"
        )
        await query.message.edit_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
    elif query.data == 'main_menu':
        await query.message.edit_text(
            "Выберите действие из меню ниже 👇",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.message.reply_text(
            "Выбери действие из меню ниже 👇",
            reply_markup=get_main_menu_keyboard()
        )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if context.user_data.get('waiting_for_wish'):
        await handle_wish_text(update, context)
    elif context.user_data.get('editing_wish_id'):
        await handle_edit_wish_text(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите действие из главного меню",
            reply_markup=get_main_menu_keyboard()
        )
