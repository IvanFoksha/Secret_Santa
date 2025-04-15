import random
import string
import logging
from database import (
    create_room, count_users_in_room, add_user_to_room, 
    user_has_room, room_exists, get_room_details, get_room_id_by_code, add_user
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from keyboards import get_main_menu_keyboard, get_room_version_keyboard
from config import FREE_MAX_USERS, PRO_MAX_USERS

# Настройка логирования
logger = logging.getLogger(__name__)


def generate_room_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=5))


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
    room_id = context.args[0] if context.args else None

    if not room_id:
        if update.message:
            await update.message.reply_text(
                'Неверный код комнаты!\n'
                'Укажите корректно ваш код комнаты: /join_room "код"'
            )
        return

    if not room_exists(room_id):
        if update.message:
            await update.message.reply_text('Комната с таким кодом не существует((')
        return

    room_details = get_room_details(room_id)
    if not room_details:
        if update.message:
            await update.message.reply_text('Ошибка при получении информации о комнате')
        return

    current_users = count_users_in_room(room_id)
    if current_users >= room_details['max_users']:
        if update.message:
            await update.message.reply_text(
                'Комната уже заполнена((\n'
                'Если вы хотите расширить комнату и порадовать Санту, '
                'то используйте /pay'
            )
        return

    logger.info(f"Пользователь {user_id} присоединяется к комнате {room_id}")
    add_user_to_room(room_id, user_id)
    if update.message:
        await update.message.reply_text(
            f'{user_name}, добро пожаловать в комнату "{room_details["name"]}"!\n'
            'Друзья ждут от тебя твоего истинного желания! '
            'А Санта скоро будет\n\n'
            'Чтобы поделиться желанием, используй: /create_wish'
        )


async def join_room_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запроса присоединения к комнате"""
    logger.info("Вызван callback-обработчик присоединения к комнате")
    
    if not update.effective_user:
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.username
    
    # Запрашиваем код комнаты
    if update.callback_query:
        await update.callback_query.message.reply_text(
            'Пожалуйста, введите код комнаты в формате:\n'
            '/join_room "код комнаты"'
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
                f'Максимальное кол-во пользователей: {details["max_users"]}\n'
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
    room_code = update.message.text.strip()
    room = get_room_details(room_code)
    
    if not room:
        await update.message.reply_text(
            "❌ Комната не найдена. Проверьте код и попробуйте снова.",
            reply_markup=get_main_menu_keyboard()
        )
        # Сбрасываем состояние пользователя
        context.user_data['waiting_for'] = None
        return
    
    if room['current_users'] >= room['max_users']:
        await update.message.reply_text(
            "❌ В комнате уже максимальное количество участников.",
            reply_markup=get_main_menu_keyboard()
        )
        # Сбрасываем состояние пользователя
        context.user_data['waiting_for'] = None
        return
    
    # Добавляем пользователя в базу данных, если его там нет
    user = update.effective_user
    add_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Добавляем пользователя в комнату
    room_id = get_room_id_by_code(room_code)
    if not room_id:
        await update.message.reply_text(
            "❌ Произошла ошибка при присоединении к комнате.",
            reply_markup=get_main_menu_keyboard()
        )
        # Сбрасываем состояние пользователя
        context.user_data['waiting_for'] = None
        return
    
    if not add_user_to_room(room_id, user.id):
        await update.message.reply_text(
            "❌ Не удалось присоединиться к комнате.",
            reply_markup=get_main_menu_keyboard()
        )
        # Сбрасываем состояние пользователя
        context.user_data['waiting_for'] = None
        return
    
    await update.message.reply_text(
        f"✅ Вы успешно присоединились к комнате!\n\n"
        f"Участников: {room['current_users'] + 1}/{room['max_users']}\n"
        f"Желаний доступно: {room['wishes_per_user']}",
        reply_markup=get_main_menu_keyboard()
    )
    
    # Сбрасываем состояние пользователя
    context.user_data['waiting_for'] = None


async def handle_room_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора версии комнаты"""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Определяем версию комнаты
        is_paid = query.data == 'pro_version'
        max_participants = 20 if is_paid else 10
        
        # Генерируем уникальное имя комнаты
        room_name = f"Комната {generate_room_code()}"
        
        # Создаем комнату
        room_id = create_room(
            name=room_name,
            creator_id=user_id,
            max_participants=max_participants,
            is_paid=is_paid
        )
        
        if room_id == 0:
            await query.answer("❌ Не удалось создать комнату")
            return
        
        # Получаем детали комнаты
        room = get_room_details(room_id)
        if not room:
            await query.answer("❌ Не удалось получить информацию о комнате")
            return
        
        # Отправляем сообщение с кодом комнаты
        await query.edit_message_text(
            f"✅ Комната создана!\n\n"
            f"🔑 Код комнаты: {room['code']}\n"
            f"👥 Максимум участников: {room['max_participants']}\n"
            f"🎁 Максимум желаний: {room['wishes_per_user']}\n\n"
            f"Отправьте этот код друзьям, чтобы они могли присоединиться к комнате."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании комнаты: {str(e)}")
        await query.answer("❌ Произошла ошибка при создании комнаты")
