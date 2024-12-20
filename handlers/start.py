from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton('Создать комнату', callback_data='create_room')],
        [InlineKeyboardButton('Присоединиться к комнате', callback_data='join_room')],
        [InlineKeyboardButton('Написать письмо Санте', callback_data='write_wish')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f'ХО-ХО-ХО!! Приветсвую тебя, {user.first_name}!\n'
        'Добро пожаловать в бота - Письмо Санте. \n\n'
        'Выбери действие ниже:',
        reply_markup=reply_markup
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open('templates/help.txt', 'r', encoding='utf-8') as file:
        help_text = file.read()

    await update.message.reply_text(help_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'create_room':
        await query.edit_message_text(f'Вы выбрали создание новой комнаты. Код для друзей: ')
    elif query.data == 'join_room':
        await query.edit_message_text('Введите код для при соединения к комнате.')
    elif query.data == 'write_wish':
        await query.edit_message_text('Санта ждет твоего письма!')
