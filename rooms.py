import random
import string
import logging
from database import (
    create_room, count_users_in_room, add_user_to_room, 
    user_has_room, room_exists, get_room_details, get_room_id_by_code, add_user, get_all_rooms, generate_room_code, count_user_rooms, get_user_room, get_room_users
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
    logger.info("Вызван обработчик присоединения к комнате")
    
    if not update.effective_user:
        if update.message:
            await update.message.reply_text('Ошибка: не удалось определить пользователя')
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.username
    
    # Если это callback query, запрашиваем код комнаты
    if update.callback_query:
        await update.callback_query.message.reply_text(
            'Пожалуйста, введите код комнаты в формате:\n'
            '/join_room "код комнаты"'
        )
        return
    
    # Если это сообщение с кодом комнаты (не команда)
    if update.message and not update.message.text.startswith('/'):
        room_code = update.message.text.strip().upper()
        logger.info(f"Пользователь {user_id} пытается присоединиться к комнате с кодом {room_code}")
        
        room_id = get_room_id_by_code(room_code)
        logger.info(f"Получен ID комнаты: {room_id}")
        
        if room_id == 0:
            await update.message.reply_text(
                '❌ Комната не найдена. Проверьте код и попробуйте снова.'
            )
            return

        if not room_exists(room_id):
            logger.error(f"Комната {room_id} не существует в базе данных")
            await update.message.reply_text(
                '❌ Комната с таким кодом не существует((' 
            )
            return

        room_details = get_room_details(room_id)
        if not room_details:
            logger.error(f"Не удалось получить детали комнаты {room_id}")
            await update.message.reply_text(
                '❌ Ошибка при получении информации о комнате'
            )
            return

        current_users = count_users_in_room(room_id)
        logger.info(f"Текущее количество пользователей в комнате: {current_users}")
        
        if current_users >= room_details['max_participants']:
            await update.message.reply_text(
                '❌ Комната уже заполнена((\n'
                'Если вы хотите расширить комнату и порадовать Санту, '
                'то используйте /pay'
            )
            return

        # Проверяем, сколько комнат у пользователя
        user_rooms_count = count_user_rooms(user_id)
        logger.info(f"Количество комнат у пользователя: {user_rooms_count}")
        
        if user_rooms_count >= 3:
            await update.message.reply_text(
                "❌ Вы уже состоите в максимальном количестве комнат (3). "
                "Пожалуйста, покиньте одну из комнат, чтобы присоединиться к новой."
            )
            return

        logger.info(f"Пользователь {user_id} присоединяется к комнате {room_id}")
        success = add_user_to_room(room_id, user_id)
        if success:
            await update.message.reply_text(
                f'✅ Вы успешно присоединились к комнате "{room_details["name"]}"!\n'
                f'🔑 Код комнаты: {room_details["code"]}\n'
                f'👥 Участников: {count_users_in_room(room_id)}/{room_details["max_participants"]}'
            )
        else:
            await update.message.reply_text(
                '❌ Не удалось присоединиться к комнате. Возможно, произошла ошибка.'
            )
        return
    
    # Если это команда /join_room
    if not context.args:
        await update.message.reply_text(
            'Неверный код комнаты!\n'
            'Укажите корректно ваш код комнаты: /join_room "код"'
        )
        return

    room_code = context.args[0].upper()  # Преобразуем код в верхний регистр
    logger.info(f"Пользователь {user_id} пытается присоединиться к комнате с кодом {room_code}")
    
    room_id = get_room_id_by_code(room_code)
    logger.info(f"Получен ID комнаты: {room_id}")
    
    if room_id == 0:
        await update.message.reply_text(
            '❌ Комната не найдена. Проверьте код и попробуйте снова.'
        )
        return

    if not room_exists(room_id):
        logger.error(f"Комната {room_id} не существует в базе данных")
        await update.message.reply_text(
            '❌ Комната с таким кодом не существует(('
        )
        return

    room_details = get_room_details(room_id)
    if not room_details:
        logger.error(f"Не удалось получить детали комнаты {room_id}")
        await update.message.reply_text(
            '❌ Ошибка при получении информации о комнате'
        )
        return

    current_users = count_users_in_room(room_id)
    logger.info(f"Текущее количество пользователей в комнате: {current_users}")
    
    if current_users >= room_details['max_participants']:
        await update.message.reply_text(
            '❌ Комната уже заполнена((\n'
            'Если вы хотите расширить комнату и порадовать Санту, '
            'то используйте /pay'
        )
        return

    # Проверяем, сколько комнат у пользователя
    user_rooms_count = count_user_rooms(user_id)
    logger.info(f"Количество комнат у пользователя: {user_rooms_count}")
    
    if user_rooms_count >= 3:
        await update.message.reply_text(
            "❌ Вы уже состоите в максимальном количестве комнат (3). "
            "Пожалуйста, покиньте одну из комнат, чтобы присоединиться к новой."
        )
        return

    logger.info(f"Пользователь {user_id} присоединяется к комнате {room_id}")
    success = add_user_to_room(room_id, user_id)
    if success:
        await update.message.reply_text(
            f'✅ Вы успешно присоединились к комнате "{room_details["name"]}"!\n'
            f'🔑 Код комнаты: {room_details["code"]}\n'
            f'👥 Участников: {count_users_in_room(room_id)}/{room_details["max_participants"]}'
        )
    else:
        await update.message.reply_text(
            '❌ Не удалось присоединиться к комнате. Возможно, произошла ошибка.'
        )


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
    
    await query.message.reply_text(
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
    
    data = query.data.split('_')
    action = data[0]
    room_id = int(data[2])
    
    if action == "pay":
        # Логика для оплаты полного доступа
        await query.message.edit_text(
            "Вы выбрали полный доступ. Функционал оплаты будет добавлен позже.",
            reply_markup=get_room_context_menu()
        )
    elif action == "stay":
        # Логика для бесплатной версии
        await query.message.edit_text(
            "Вы выбрали бесплатную версию. Наслаждайтесь!",
            reply_markup=get_room_context_menu()
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
        rooms = get_all_rooms(user_id)
        
        if not rooms:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "У вас пока нет комнат. Создайте новую комнату или присоединитесь к существующей!"
                )
            return
            
        message = "📋 Ваши комнаты:\n\n"
        
        # Создаем клавиатуру с кнопками для каждой комнаты
        keyboard = []
        for i, room in enumerate(rooms, 1):
            message += (
                f"{i}. {room['name']}\n"
                f"   👥 Участников: {room['current_users']}/{room['max_participants']}\n"
                f"   {'💎 PRO' if room['is_paid'] else '🆓 Бесплатная'}\n\n"
            )
            
            # Добавляем кнопку для переключения на эту комнату
            keyboard.append([
                InlineKeyboardButton(
                    f"Переключиться на {room['name']}", 
                    callback_data=f"switch_room_{room['id']}"
                )
            ])
            
        # Добавляем кнопку возврата в главное меню
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        if update.callback_query:
            await update.callback_query.message.edit_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"Ошибка при получении списка комнат: {str(e)}")
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "❌ Произошла ошибка при получении списка комнат. Пожалуйста, попробуйте позже."
            )


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
        
        # Получаем актуальную информацию о комнате
        room = get_room_details(room_id)
        if not room:
            await query.message.reply_text('❌ Комната больше не существует')
            return
            
        # Проверяем наличие свободных мест
        if room['current_users'] >= room['max_participants']:
            await query.message.reply_text('❌ В комнате больше нет свободных мест')
            return
            
        # Добавляем пользователя в комнату
        if add_user_to_room(room_id, user_id):
            await query.message.reply_text(
                f"✅ Вы успешно присоединились к комнате!\n"
                f"🏠 Название: {room['name']}\n"
                f"🔑 Код комнаты: {room['code']}",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.message.reply_text(
                '❌ Не удалось присоединиться к комнате',
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка при присоединении к комнате: {str(e)}")
        await query.message.reply_text(
            '❌ Произошла ошибка при обработке запроса',
            reply_markup=get_main_menu_keyboard()
        )

async def handle_room_context_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик контекстного меню комнаты"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
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
            
        wishes = list_wishes(user_id, user_room['room_id'])
        if not wishes:
            await query.message.edit_text(
                "📋 У вас пока нет желаний в этой комнате.",
                reply_markup=get_room_context_menu()
            )
            return
            
        message = "📋 Ваши желания:\n\n"
        for i, wish in enumerate(wishes, 1):
            message += f"{i}. {wish['text']}\n"
            
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
            
        room = get_room_details(user_room['room_id'])
        if not room:
            await query.message.edit_text(
                "❌ Комната не найдена.",
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        users = get_room_users(user_room['room_id'])
        message = f"👥 Участники комнаты '{room['name']}':\n\n"
        
        for user in users:
            role = "👑 Создатель" if user['id'] == room['creator_id'] else "👤 Участник"
            message += f"{role}: {user['first_name']} {user['last_name'] or ''}\n"
            
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
