from database import add_wish, edit_wish, delete_wish, get_user_wishes
from config import ADMIN_ID
from telegram import Update
from telegram.ext import ContextTypes


async def create_wish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.effective_user.id:
        if update.message:
            await update.message.reply_text('Ошибка: пользователь не определен.')
        return

    user_id = update.effective_user.id
    wish_text = ' '.join(context.args) if context.args else ''

    user_wishes = get_user_wishes(user_id)
    if len(user_wishes) >= 3:
        if update.message:
            await update.message.reply_text(
                'Вы использовали лимит беслпатных желаний (3).\n'
                'Хотите расширить? Используйте /pay.'
            )
        return

    add_wish(user_id, wish_text)
    if update.message:
        await update.message.reply_text(
            'Ваше желание добавлено! Санта уже принял ваше пожелание\n'
            'Вы можете отредактировать его: /edit_wish\n'
            'Или удалить его: /delete_wish'
        )


async def edit_wish_hendler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id:
        if update.message:
            await update.message.reply_text('Ошибка: пользователь не определен.')
        return

    if not context.args or len(context.args) < 1:
        if update.message:
            await update.message.reply_text('Ошибка: недопустимый формат команды.')
        return

    user_id = update.effective_user.id
    wish_id = context.args[0]
    new_text = ' '.join(context.args[1:])

    if edit_wish(user_id, wish_id, new_text):
        if update.message:
            await update.message.reply_text(
                'Важе желание обновлено!!'
            )
    else:
        if update.message:
            await update.message.reply_text(
                'Не удалось найти ваше желание.\n'
                'Вы моеже добавть новое желание: /create_wish\n'
                f'Либо обратиться за помощью к {ADMIN_ID}'
            )


async def delete_wish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.effective_user.id:
        if update.message:
            await update.message.reply_text('Ошибка: пользователь не определен.')
        return

    if not context.args or len(context.args) < 1:
        if update.message:
            await update.message.reply_text('Ошибка: неверный формат команды.')
        return

    user_id = update.effective_user.id
    wish_id = context.args[0]

    if delete_wish(user_id, wish_id):
        if update.message:
            await update.message.reply_text('Ваше желание успешно удалено!')
    else:
        if update.message:
            await update.message.reply_text('Не удалось найти ваше желание...')
