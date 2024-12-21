import random, string
from database import create_room, count_users_in_room, add_user_to_room, user_has_room, room_exists, get_room_details
from telegram import Update
from telegram.ext import ContextTypes

def generate_room_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=5))

async def create_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    room_code = generate_room_code()

    if user_has_room(user_id):
        await update.message.reply_text("Вы уже создали комнату!")
        return

    create_room(room_code, user_id, max_users=5)
    await update.message.reply_text(
        'Вы создали комнату, поздравляем!!\n'
        f'Друзья ждут вас, поделитесь с ними кодом: {room_code}.'
        )

async def join_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    room_id = context.args[0] if context.args else None

    if not room_id:
        await update.message.reply_text(
            'Неверный код комнаты!'
            'Укажите корректно ваш код комнаты: /join_room "код"'
            )

    if not room_exists(room_id):
        await update.message.reply_text('Комната с таким кодом не существует((')
        return

    if count_users_in_room(room_id) >= 5:
        await update.message.reply_text(
            'Комната уже заполнена((\n'
            'Если вы хотите расширить комнату и порадовать Санту, то используй /pay.'
        )
    else:
        add_user_to_room(room_id, user_id)
        await update.message.reply_text(
            f'{user_id.user_name}, добро пожаловать в комнату {room_id}\n'
            'Друзья ждут от тебя твоего истинного желания! А Санта скоро будет\n\n'
            'Что бы поделиться желанием, используй: /add_wish'
        )

async def room_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_id = context.args[0] if context.args else None
    if not room_id:
        await update.message.reply_text('Укажите код комнаты: /room_info *код*')
        return

    details = get_room_details(room_id)
    if details:
        await update.message.reply_text(
            f'Комната: {details["room_id"]}\n'
            f'Максимальное кол-во пользователей: {details["max_users"]}\n'
            f'Создатель: {details["creator_id"]}\n'
            f'Кол-во пользователей комнаты: {details["current_users"]}'
        )
    else:
        await update.message.reply_text('Комната не найдена.')
