from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает основное меню бота"""
    keyboard = [
        [
            InlineKeyboardButton("🎁 Создать комнату", callback_data="create_room"),
            InlineKeyboardButton("🔍 Найти комнату", callback_data="join_room")
        ],
        [
            InlineKeyboardButton("📋 Мои комнаты", callback_data="list_rooms"),
            InlineKeyboardButton("📝 Создать желание", callback_data="create_wish")
        ],
        [
            InlineKeyboardButton("✏️ Редактировать желание", callback_data="edit_wish"),
            InlineKeyboardButton("📋 Список желаний", callback_data="list_wishes")
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_room_version_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора версии комнаты"""
    keyboard = [
        [
            InlineKeyboardButton("🎁 Бесплатная версия", callback_data="free_version"),
            InlineKeyboardButton("✨ PRO версия", callback_data="pro_version")
        ],
        [
            InlineKeyboardButton("« Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wish_actions_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру действий с желаниями"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить желание", callback_data="add_wish"),
            InlineKeyboardButton("✏️ Изменить желание", callback_data="change_wish")
        ],
        [
            InlineKeyboardButton("🗑 Удалить желание", callback_data="delete_wish"),
            InlineKeyboardButton("📋 Список желаний", callback_data="list_wishes")
        ],
        [
            InlineKeyboardButton("« Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
