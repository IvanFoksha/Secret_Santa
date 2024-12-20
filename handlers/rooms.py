import random, string
from database import create_room, count_users_in_room, add_user_to_room
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

def generate_room_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=5))

async def create_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    room_code = generate_room_code()
    create_room(room_code, user_id, max_users=5)
    await update.message.reply_text(
        'Вы создали комнату, поздравляем!!\n'
        f'Друзья ждут вас, поделитесь с ними кодом: {room_code}.'
        )

async def join_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    room_code = context.args[0]
    if count_users_in_room(room_code) >= 5:
        await update.message.reply_text(
            'Комната уже заполнена((\n'
            'Если вы хотите расширить комнату и порадовать Санту, то используй /pay.'
        )
    else:
        add_user_to_room(room_code, user_id)
        await update.message.reply_text(
            f'{user.user_name}, добро пожаловать в комнату {room_code}\n'
            'Друзья ждут от тебя твоего истинного желания! А Санта скоро будет\n\n'
            'Что бы поделиться желанием, используй: --' #дописать код, когда будет готов модуль с "подарками"
        )
#Дописать гет рум - для полноты дейсвтия в рассылке ночной