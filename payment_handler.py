from database import grant_access, get_room_details
from telegram import Update
from telegram.ext import ContextTypes


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка платежей за доступ к комнате (тестовый режим)"""
    if not update.effective_user:
        if update.message:
            await update.message.reply_text(
                'Ошибка: не удалось определить пользователя'
            )
        return

    user_id = update.effective_user.id
    
    # Получаем room_id из callback_data или аргументов команды
    if update.callback_query:
        data = update.callback_query.data
        if data.startswith('pay_full_'):
            room_id = data.split('_')[2]
        elif data.startswith('stay_free_'):
            room_id = data.split('_')[2]
            # Для бесплатной версии просто обновляем статус
            grant_access(user_id, 'free')
            if update.callback_query.message:
                await update.callback_query.message.reply_text(
                    'Вы выбрали бесплатную версию.\n'
                    'Теперь вы можете добавить до 3 желаний.'
                )
            return
    else:
        room_id = context.args[0] if context.args else None

    if not room_id:
        if update.message:
            await update.message.reply_text(
                'Пожалуйста, укажите код комнаты:\n'
                '/pay "код комнаты"'
            )
        return

    room_details = get_room_details(room_id)
    if not room_details:
        if update.message:
            await update.message.reply_text('Комната не найдена')
        return

    if room_details['creator_id'] != user_id:
        if update.message:
            await update.message.reply_text(
                'Только создатель комнаты может оплатить полный доступ'
            )
        return

    # В тестовом режиме сразу предоставляем доступ
    grant_access(user_id, 'paid')
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            '✅ Тестовый режим: Оплата успешно выполнена!\n\n'
            'Теперь ваша комната имеет полный доступ:\n'
            '• До 10 пользователей\n'
            '• До 10 желаний для каждого\n'
            '• Неограниченный просмотр желаний'
        )
    else:
        await update.message.reply_text(
            '✅ Тестовый режим: Оплата успешно выполнена!\n\n'
            'Теперь ваша комната имеет полный доступ:\n'
            '• До 10 пользователей\n'
            '• До 10 желаний для каждого\n'
            '• Неограниченный просмотр желаний'
        )


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешного платежа (тестовый режим)"""
    if not update.effective_user:
        return

    user_id = update.effective_user.id
    
    # Обновляем статус комнаты
    grant_access(user_id, 'paid')
    
    if update.message:
        await update.message.reply_text(
            '✅ Тестовый режим: Оплата успешно выполнена!\n\n'
            'Теперь ваша комната имеет полный доступ:\n'
            '• До 10 пользователей\n'
            '• До 10 желаний для каждого\n'
            '• Неограниченный просмотр желаний'
        )
