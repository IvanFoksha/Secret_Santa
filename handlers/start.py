from rooms import join_room_handler, create_room_handler
from wishes import create_wish_handler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        if update.message:
            await update.message.reply_text('Ошибка: не удалось определить пользователя')
        return

    user_name = update.effective_user.username

    keyboard = [
        [InlineKeyboardButton('Создать комнату', callback_data='create_room')],
        [InlineKeyboardButton('Присоединиться к комнате', callback_data='join_room')],
        [InlineKeyboardButton('Написать письмо Санте', callback_data='write_wish')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            f'ХО-ХО-ХО!! Приветсвую тебя, {user_name}!\n'
            'Добро пожаловать в бота - Письмо Санте. \n\n'
            'Выбери действие ниже:',
            reply_markup=reply_markup
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open('templates/help.txt', 'r', encoding='utf-8') as file:
        help_text = file.read()

    if update.message:
        await update.message.reply_text(help_text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == 'create_room':
            await query.edit_message_text('Вы выбрали создание новой комнаты.')
            await create_room_handler(update, context)
        elif query.data == 'join_room':
            await query.edit_message_text('Вы выбрали присоединение к существующей комнате')
            await join_room_handler(update, context)
        elif query.data == 'write_wish':
            await query.edit_message_text(
                'Вы выбрали написать письмо санте\n'
                'Санта ждет твоего письма!\n'
                )
            await create_wish_handler(update, context)
