import random
import string
import logging
from database import (
    create_room, count_users_in_room, add_user_to_room, user_has_room,
    room_exists, get_room_details, get_room_id_by_code, add_user,
    get_all_rooms, generate_room_code, count_user_rooms, get_user_room,
    get_room_users, update_room_version, get_user_rooms_count, MAX_ROOMS_PER_USER,
    get_user_wishes
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from keyboards import get_main_menu_keyboard, get_room_version_keyboard
from config import FREE_MAX_USERS, PRO_MAX_USERS

# Настройка логирования
logger = logging.getLogger(__name__)


def get_room_context_menu():
    """Создает контекстное меню для комнаты"""
    keyboard = [
        [InlineKeyboardButton("📝 Добавить желание", callback_data="add_wish")],
        [InlineKeyboardButton("📋 Мои желания", callback_data="list_wishes")],
        [InlineKeyboardButton("👥 Участники комнаты", callback_data="list_room_users")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def create_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды создания комнаты"""
    logger.info("Вызван обработчик создания комнаты")
    
    if not update.effective_user:
        if update.message:
            await update.message.reply_text(
                'Ошибка: не удалось определить пользователя'
            )
        return

    user_id = update.effective_user.id
    room_name = ' '.join(context.args) if context.args else f'Комната {generate_room_code()}'

    if user_has_room(user_id):
        if update.message:
            await update.message.reply_text("Вы уже создали комнату!")
        return

    logger.info(f"Создание комнаты пользователем {user_id}")
    room_id = create_room(name=room_name, creator_id=user_id, max_participants=5)
    
    if room_id == 0:
        if update.message:
            await update.message.reply_text(
                "Произошла ошибка при создании комнаты. Попробуйте позже."
            )
        return
    
    # Получаем детали комнаты
    room = get_room_details(room_id)
    if not room:
        if update.message:
            await update.message.reply_text(
                "Произошла ошибка при получении информации о комнате. Попробуйте позже."
            )
        return
    
    keyboard = [
        [
            InlineKeyboardButton(
                "Оплатить полный доступ", 
                callback_data=f"pay_full_{room_id}"
            ),
            InlineKeyboardButton(
                "Остаться на бесплатной версии", 
                callback_data=f"stay_free_{room_id}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            f'Вы создали комнату "{room_name}", поздравляем!!\n'
            f'Друзья ждут вас, поделитесь с ними кодом: {room["code"]}\n\n'
            'Выберите тип доступа:',
            reply_markup=reply_markup
        )


async def create_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запроса создания комнаты"""
    logger.info("Вызван callback-обработчик создания комнаты")
    
    if not update.effective_user:
        return

    user_id = update.effective_user.id
    room_name = f'Комната {generate_room_code()}'

    if user_has_room(user_id):
        if update.callback_query:
            await update.callback_query.message.reply_text("Вы уже создали комнату!")
        return

    logger.info(f"Создание комнаты пользователем {user_id} через callback")
    room_id = create_room(room_name, user_id, max_participants=5)
    
    if room_id == 0:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "Произошла ошибка при создании комнаты. Попробуйте позже."
            )
        return
    
    # Получаем детали комнаты
    room = get_room_details(room_id)
    if not room:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "Произошла ошибка при получении информации о комнате. Попробуйте позже."
            )
        return
    
    keyboard = [
        [
            InlineKeyboardButton("Оплатить полный доступ", callback_data=f"pay_full_{room_id}"),
            InlineKeyboardButton("Остаться на бесплатной версии", callback_data=f"stay_free_{room_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            f'Вы создали комнату "{room_name}", поздравляем!!\n'
            f'Друзья ждут вас, поделитесь с ними кодом: {room["code"]}\n\n'
            'Выберите тип доступа:',
            reply_markup=reply_markup
        )


async def join_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды присоединения к комнате"""
    if not update.effective_user:
        if update.message:
            await update.message.reply_text('Ошибка: не удалось определить пользователя')
        return

    user_id = update.effective_user.id
    
    # Проверяем количество комнат пользователя перед присоединением
    rooms_count = await get_user_rooms_count(user_id)
    logger.info(f"Пользователь {user_id} имеет {rooms_count} комнат, лимит {MAX_ROOMS_PER_USER}")
    
    if rooms_count >= MAX_ROOMS_PER_USER:
        await update.message.reply_text(
            "❌ Вы достигли лимита в 3 комнаты. "
            "Пожалуйста, выйдите из одной из существующих комнат, "
            "чтобы присоединиться к новой.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    if update.message and update.message.text.startswith('/join_room'):
        args = update.message.text.split()
        if len(args) > 1:
            # Если код комнаты указан в команде
            room_code = args[1].upper()
            logger.info(f"Поиск комнаты с кодом: {room_code}")
            
            room_id = get_room_id_by_code(room_code)
            if not room_id:
                await update.message.reply_text(
                    '❌ Комната не найдена. Проверьте код и попробуйте снова.',
                    reply_markup=get_main_menu_keyboard()
                )
                return
            
            # Получаем информацию о комнате
            room_details = get_room_details(room_id)
            if not room_details:
                await update.message.reply_text(
                    '❌ Не удалось получить информацию о комнате',
                    reply_markup=get_main_menu_keyboard()
                )
                return

            # Проверяем, не состоит ли пользователь уже в этой комнате
            user_room = get_user_room(user_id)
            if user_room and user_room['id'] == room_id:
                await update.message.reply_text(
                    '❌ Вы уже состоите в этой комнате',
                    reply_markup=get_main_menu_keyboard()
                )
                return

            # Проверяем наличие свободных мест
            if room_details['current_users'] >= room_details['max_participants']:
                await update.message.reply_text(
                    '❌ В комнате больше нет свободных мест',
                    reply_markup=get_main_menu_keyboard()
                )
                return

            # Формируем сообщение с информацией о комнате
            message = (
                f"🔍 Найдена комната:\n\n"
                f"🏠 Название: {room_details['name']}\n"
                f"👥 Участников: {room_details['current_users']}/{room_details['max_participants']}\n"
                f"💎 Версия: {'PRO' if room_details['is_paid'] else 'Бесплатная'}\n\n"
                "Хотите присоединиться к этой комнате?"
            )

            # Создаем клавиатуру с кнопками подтверждения
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да", callback_data=f"confirm_join_{room_id}"),
                    InlineKeyboardButton("❌ Нет", callback_data="cancel_join")
                ]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Если код комнаты не указан
            await update.message.reply_text(
                '🔍 Введите код комнаты для поиска:',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
                ]])
            )
            context.user_data['waiting_for'] = 'room_code'
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            '🔍 Введите код комнаты для поиска:'
        )
        context.user_data['waiting_for'] = 'room_code'


async def join_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подключения к комнате по callback_data"""
    logger.info("Вызван обработчик подключения к комнате по callback")
    
    if not update.effective_user:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                'Ошибка: не удалось определить пользователя'
            )
        return

    user_id = update.effective_user.id
    query = update.callback_query
    
    # Получаем ID комнаты из callback_data
    room_id = int(query.data.split('_')[2])
    logger.info(
        f"Пользователь {user_id} пытается подключиться к комнате {room_id}"
    )
    
    # Проверяем существование комнаты
    room = get_room_details(room_id)
    if not room:
        await query.message.reply_text(
            '❌ Комната не найдена. Возможно, она была удалена.'
        )
        return
    
    # Проверяем, не состоит ли пользователь уже в этой комнате
    user_room = get_user_room(user_id)
    if user_room['room_id'] == room_id:
        await query.message.reply_text(
            '❌ Вы уже состоите в этой комнате.'
        )
        return
    
    # Проверяем, не превышен ли лимит комнат для пользователя
    user_rooms_count = count_user_rooms(user_id)
    if user_rooms_count >= 3:
        await query.message.reply_text(
            '❌ Вы достигли лимита комнат (максимум 3). '
            'Пожалуйста, покиньте одну из существующих комнат.'
        )
        return
    
    # Подключаем пользователя к комнате
    success = add_user_to_room(room_id, user_id)
    if success:
        await query.message.reply_text(
            f'✅ Вы успешно подключились к комнате "{room["name"]}"!\n'
            f'🔑 Код комнаты: {room["code"]}\n'
            f'👥 Участников: {count_users_in_room(room_id)}/'
            f'{room["max_participants"]}'
        )
    else:
        await query.message.reply_text(
            '❌ Не удалось подключиться к комнате. '
            'Возможно, она уже заполнена или произошла ошибка.'
        )


async def room_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды информации о комнате"""
    logger.info("Вызван обработчик информации о комнате")
    
    room_id = context.args[0] if context.args else None
    if not room_id:
        if update.message:
            await update.message.reply_text('Укажите код комнаты: /room_info *код*')
        return

    details = get_room_details(room_id)
    if details:
        status = "Платная" if details["is_paid"] else "Бесплатная"
        if update.message:
            await update.message.reply_text(
                f'Комната: {details["name"]}\n'
                f'Статус: {status}\n'
                f'Максимальное кол-во пользователей: {details["max_participants"]}\n'
                f'Текущее кол-во пользователей: {details["current_users"]}'
            )
    else:
        if update.message:
            await update.message.reply_text('Комната не найдена.')


async def handle_room_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания комнаты"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Проверяем количество комнат пользователя
        user_id = update.effective_user.id
        rooms_count = await get_user_rooms_count(user_id)
        
        logger.info(f"Пользователь {user_id} имеет {rooms_count} комнат, лимит {MAX_ROOMS_PER_USER}")
        
        if rooms_count >= MAX_ROOMS_PER_USER:
            await query.message.edit_text(
                "❌ Вы достигли лимита в 3 комнаты. "
                "Пожалуйста, удалите одну из существующих комнат, "
                "чтобы создать новую.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Создаем комнату в БД
        room_id = await create_room(user_id)
        if not room_id:
            await query.message.edit_text(
                "❌ Произошла ошибка при создании комнаты. "
                "Пожалуйста, попробуйте позже.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Сохраняем ID комнаты в контексте
        context.user_data['creating_room_id'] = room_id
        
        # Показываем меню выбора версии
        await query.message.edit_text(
            "🎄 Выбери версию комнаты:\n\n"
            "🎁 *Бесплатная версия:*\n"
            f"- До {FREE_MAX_USERS} участников\n"
            "- 1 желание на участника\n\n"
            "✨ *PRO версия:*\n"
            f"- До {PRO_MAX_USERS} участников\n"
            "- 5 желаний на участника\n"
            "- Приоритетная поддержка",
            parse_mode='Markdown',
            reply_markup=get_room_version_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in handle_room_creation: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка при создании комнаты. "
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )


async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик присоединения к комнате"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "🎄 Введите код комнаты, к которой хотите присоединиться:\n"
        "(Просто отправьте код в следующем сообщении)"
    )
    context.user_data['waiting_for'] = 'room_code'


async def handle_room_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода кода комнаты"""
    if not context.user_data.get('waiting_for') == 'room_code':
        return
        
    user_id = update.effective_user.id
    room_code = update.message.text.upper()
    
    # Получаем ID комнаты по коду
    room_id = get_room_id_by_code(room_code)
    if not room_id:
        await update.message.reply_text(
            "❌ Комната с таким кодом не найдена. "
            "Проверьте код и попробуйте снова."
        )
        return
    
    # Проверяем, существует ли комната
    if not room_exists(room_id):
        await update.message.reply_text(
            "❌ Комната не найдена. Возможно, она была удалена."
        )
        return
    
    # Проверяем, не состоит ли пользователь уже в комнате
    if user_has_room(user_id):
        await update.message.reply_text(
            "❌ Вы уже состоите в комнате. "
            "Покините текущую комнату, чтобы присоединиться к другой."
        )
        return
    
    # Проверяем количество участников
    users_count = count_users_in_room(room_id)
    room = get_room_details(room_id)
    
    if users_count >= room['max_participants']:
        await update.message.reply_text(
            "❌ Комната заполнена. Максимальное количество участников достигнуто."
        )
        return
    
    # Добавляем пользователя в комнату
    success = add_user_to_room(user_id, room_id)
    if success:
        await update.message.reply_text(
            f"✅ Вы успешно присоединились к комнате!\n\n"
            f"🏠 Название: {room['name']}\n"
            f"👥 Участников: {users_count + 1}/{room['max_participants']}\n"
            f"🎁 Максимум желаний: {room['max_wishes']}",
            reply_markup=get_room_context_menu()
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось присоединиться к комнате. Пожалуйста, попробуйте позже."
        )
    
    # Очищаем контекст
    context.user_data.pop('waiting_for', None)


async def handle_room_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора версии комнаты"""
    query = update.callback_query
    await query.answer()
    
    # Получаем callback_data
    callback_data = query.data
    
    # Определяем выбранную версию
    if callback_data == "free_version":
        version = "free"
    elif callback_data == "pro_version":
        version = "pro"
    else:
        logger.error(f"Неизвестная версия комнаты: {callback_data}")
        await query.message.edit_text(
            "Произошла ошибка при выборе версии комнаты. Пожалуйста, попробуйте снова.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Получаем ID комнаты из контекста
    room_id = context.user_data.get('creating_room_id')
    if not room_id:
        await query.message.edit_text(
            "Произошла ошибка при создании комнаты. Пожалуйста, попробуйте снова.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    try:
        # Получаем информацию о комнате, чтобы вывести её код
        room_info = get_room_details(room_id)
        if not room_info:
            await query.message.edit_text(
                "Произошла ошибка при получении информации о комнате. Пожалуйста, попробуйте снова.",
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        room_code = room_info['code']
        
        if version == "free":
            # Обновляем статус комнаты на бесплатную версию
            await update_room_version(room_id, "free")
            await query.message.edit_text(
                "🎁 Комната создана в бесплатной версии!\n\n"
                "Возможности:\n"
                "- До 5 участников\n"
                "- 1 желание на участника\n\n"
                f"🔑 Код вашей комнаты: {room_code}",
                reply_markup=get_room_context_menu()
            )
        elif version == "pro":
            # Обновляем статус комнаты на PRO версию
            await update_room_version(room_id, "pro")
            await query.message.edit_text(
                "✨ Комната создана в PRO версии!\n\n"
                "Возможности:\n"
                "- До 10 участников\n"
                "- 5 желаний на участника\n"
                "- Приоритетная поддержка\n\n"
                f"🔑 Код вашей комнаты: {room_code}",
                reply_markup=get_room_context_menu()
            )
        
        # Очищаем ID создаваемой комнаты из контекста
        context.user_data.pop('creating_room_id', None)
        
    except Exception as e:
        logger.error(f"Error in handle_room_version: {e}")
        await query.message.edit_text(
            "Произошла ошибка при создании комнаты. Пожалуйста, попробуйте снова.",
            reply_markup=get_main_menu_keyboard()
        )


async def list_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список комнат пользователя"""
    logger.info("Вызван обработчик списка комнат")
    
    if not update.effective_user:
        if update.callback_query:
            await update.callback_query.message.reply_text('Ошибка: не удалось определить пользователя')
        return

    user_id = update.effective_user.id
    
    try:
        # Получаем список комнат пользователя
        rooms = get_all_rooms(user_id)
        logger.info(f"Найдено комнат: {len(rooms)}")
        
        if not rooms:
            text = "У вас пока нет комнат. Создайте новую комнату или присоединитесь к существующей!"
            if update.callback_query:
                await update.callback_query.message.edit_text(text, reply_markup=get_main_menu_keyboard())
            else:
                await update.message.reply_text(text, reply_markup=get_main_menu_keyboard())
            return
            
        message = "📋 Ваши комнаты:\n\n"
        
        # Создаем клавиатуру с кнопками для каждой комнаты
        keyboard = []
        for i, room in enumerate(rooms, 1):
            # Проверяем наличие всех необходимых полей
            room_name = room.get('name', 'Без названия')
            room_code = room.get('code', 'Нет кода')
            room_id = room.get('id', 0)
            current_users = room.get('current_users', 0)
            max_participants = room.get('max_participants', 0)
            is_paid = room.get('is_paid', False)
            is_creator = room.get('is_creator', False)
            is_current = room.get('is_current', False)
            
            # Добавляем статус создателя и текущей комнаты, если применимо
            status = []
            if is_creator:
                status.append("Вы создатель")
            if is_current:
                status.append("Текущая комната")
            
            status_text = f" ({', '.join(status)})" if status else ""
            
            message += (
                f"{i}. {room_name}{status_text}\n"
                f"   🔑 Код: {room_code}\n"
                f"   👥 Участников: {current_users}/{max_participants}\n"
                f"   {'💎 PRO' if is_paid else '🆓 Бесплатная'}\n\n"
            )
            
            # Добавляем только кнопку для переключения на эту комнату
            keyboard.append([
                InlineKeyboardButton(
                    f"Переключиться на {room_name}", 
                    callback_data=f"switch_room_{room_id}"
                )
            ])
            
        # Добавляем кнопку возврата в главное меню
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        if update.callback_query:
            await update.callback_query.message.edit_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"Ошибка при получении списка комнат: {str(e)}")
        text = "❌ Произошла ошибка при получении списка комнат. Пожалуйста, попробуйте позже."
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_menu_keyboard())


async def search_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск комнаты по коду"""
    logger.info("Вызван обработчик поиска комнаты")
    
    if not update.effective_user:
        if update.message:
            await update.message.reply_text('Ошибка: не удалось определить пользователя')
        return

    user_id = update.effective_user.id
    
    # Обработка команды /search_room
    if update.message and update.message.text.startswith('/search_room'):
        await update.message.reply_text(
            '🔍 Введите код комнаты для поиска:',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])
        )
        context.user_data['waiting_for'] = 'room_search'
        return
    
    # Обработка введенного кода комнаты
    if update.message and context.user_data.get('waiting_for') == 'room_search':
        room_code = update.message.text.strip().upper()
        logger.info(f"Поиск комнаты с кодом: {room_code}")
        
        room_id = get_room_id_by_code(room_code)
        if not room_id:
            await update.message.reply_text(
                '❌ Комната не найдена. Проверьте код и попробуйте снова.',
                reply_markup=get_main_menu_keyboard()
            )
            context.user_data.pop('waiting_for', None)
            return
        
        room_details = get_room_details(room_id)
        if not room_details:
            await update.message.reply_text(
                '❌ Ошибка при получении информации о комнате',
                reply_markup=get_main_menu_keyboard()
            )
            context.user_data.pop('waiting_for', None)
            return

        # Формируем сообщение с информацией о комнате
        message = (
            f"🔍 Найдена комната:\n\n"
            f"🏠 Название: {room_details['name']}\n"
            f"👥 Участников: {room_details['current_users']}/{room_details['max_participants']}\n"
            f"💎 Версия: {'PRO' if room_details['is_paid'] else 'Бесплатная'}\n"
            f"🔑 Код: {room_details['code']}\n\n"
            "Хотите присоединиться к этой комнате?"
        )

        # Создаем клавиатуру с кнопками подтверждения
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data=f"confirm_join_{room_id}"),
                InlineKeyboardButton("❌ Нет", callback_data="cancel_join")
            ]
        ]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data.pop('waiting_for', None)

async def confirm_join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения присоединения к комнате"""
    query = update.callback_query
    await query.answer()
    
    try:
        room_id = int(query.data.split('_')[2])
        user_id = query.from_user.id
        
        # Проверяем количество комнат пользователя
        rooms_count = await get_user_rooms_count(user_id)
        logger.info(f"Пользователь {user_id} имеет {rooms_count} комнат, лимит {MAX_ROOMS_PER_USER}")
        
        if rooms_count >= MAX_ROOMS_PER_USER:
            await query.message.edit_text(
                "❌ Вы достигли лимита в 3 комнаты. "
                "Пожалуйста, выйдите из одной из существующих комнат, "
                "чтобы присоединиться к новой.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Получаем актуальную информацию о комнате
        room = get_room_details(room_id)
        if not room:
            await query.message.edit_text(
                '❌ Комната больше не существует',
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        # Проверяем наличие свободных мест
        if room['current_users'] >= room['max_participants']:
            await query.message.edit_text(
                '❌ В комнате больше нет свободных мест',
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Проверяем, не состоит ли пользователь уже в этой комнате
        user_room = get_user_room(user_id)
        if user_room and user_room['id'] == room_id:
            await query.message.edit_text(
                '❌ Вы уже состоите в этой комнате',
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        # Добавляем пользователя в комнату
        if add_user_to_room(room_id, user_id):
            await query.message.edit_text(
                f"✅ Вы успешно присоединились к комнате!\n"
                f"🏠 Название: {room['name']}\n"
                f"🔑 Код комнаты: {room['code']}",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.message.edit_text(
                '❌ Не удалось присоединиться к комнате',
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка при присоединении к комнате: {str(e)}")
        await query.message.edit_text(
            '❌ Произошла ошибка при обработке запроса',
            reply_markup=get_main_menu_keyboard()
        )

async def handle_room_context_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик контекстного меню комнаты"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    logger.info(f"Получен callback_data: {action}")
    
    if action == "add_wish":
        # Перенаправляем на добавление желания
        await query.message.edit_text(
            "📝 Введите ваше желание (до 250 символов):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="room_menu")
            ]])
        )
        context.user_data['waiting_for'] = 'wish_text'
        
    elif action == "list_wishes":
        # Показываем список желаний
        user_id = query.from_user.id
        user_room = get_user_room(user_id)
        
        if not user_room:
            await query.message.edit_text(
                "❌ Вы не состоите ни в одной комнате.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Получаем ID комнаты и проверяем его тип
        room_id = user_room.get('id')
        if not room_id:
            await query.message.edit_text(
                "❌ Не удалось определить ID комнаты.",
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        # Используем get_user_wishes
        wishes = get_user_wishes(user_id, int(room_id))
        
        if not wishes:
            await query.message.edit_text(
                "📋 У вас пока нет желаний в этой комнате.",
                reply_markup=get_room_context_menu()
            )
            return
            
        message = "📋 Ваши желания:\n\n"
        for i, wish in enumerate(wishes, 1):
            wish_text = wish.get('text', 'Нет текста')
            message += f"{i}. {wish_text}\n"
            
        await query.message.edit_text(
            message,
            reply_markup=get_room_context_menu()
        )
        
    elif action == "list_room_users":
        # Показываем список участников комнаты
        user_id = query.from_user.id
        user_room = get_user_room(user_id)
        
        if not user_room:
            await query.message.edit_text(
                "❌ Вы не состоите ни в одной комнате.",
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        room_id = user_room.get('id')
        if not room_id:
            await query.message.edit_text(
                "❌ Не удалось определить ID комнаты.",
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        room = get_room_details(room_id)
        if not room:
            await query.message.edit_text(
                "❌ Комната не найдена.",
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        users = get_room_users(room_id)
        message = f"👥 Участники комнаты '{room['name']}':\n\n"
        
        for user in users:
            role = "👑 Создатель" if user.get('id') == room.get('creator_id') else "👤 Участник"
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            message += f"{role}: {first_name} {last_name or ''}\n"
            
        await query.message.edit_text(
            message,
            reply_markup=get_room_context_menu()
        )
        
    elif action == "main_menu":
        # Возвращаемся в главное меню
        await query.message.edit_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        
    elif action == "room_menu":
        # Возвращаемся в меню комнаты
        await query.message.edit_text(
            "Меню комнаты:",
            reply_markup=get_room_context_menu()
        )

async def delete_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик удаления комнаты"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Получаем ID комнаты из callback_data
        room_id = int(query.data.split('_')[2])
        user_id = query.from_user.id
        
        logger.info(f"Попытка удаления комнаты {room_id} пользователем {user_id}")
        
        # Получаем информацию о комнате
        room_info = get_room_details(room_id)
        if not room_info:
            await query.message.edit_text(
                "❌ Комната не найдена. Возможно, она уже удалена.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Запрашиваем подтверждение удаления
        await query.message.edit_text(
            f"🗑️ Вы действительно хотите удалить комнату '{room_info['name']}'?\n\n"
            "⚠️ Это действие нельзя отменить. "
            "Все желания пользователей в комнате будут удалены.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{room_id}"),
                    InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_delete")
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке к удалению комнаты: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )


async def confirm_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения удаления комнаты"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Получаем ID комнаты из callback_data
        room_id = int(query.data.split('_')[2])
        user_id = query.from_user.id
        
        logger.info(f"Подтверждено удаление комнаты {room_id} пользователем {user_id}")
        
        # Удаляем комнату
        from database import delete_room
        if delete_room(room_id, user_id):
            await query.message.edit_text(
                "✅ Комната успешно удалена.",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.message.edit_text(
                "❌ Не удалось удалить комнату. Возможно, у вас нет прав на это действие.",
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка при удалении комнаты: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка при удалении комнаты. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )


async def cancel_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены удаления комнаты"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "✅ Удаление комнаты отменено.",
        reply_markup=get_main_menu_keyboard()
    )
