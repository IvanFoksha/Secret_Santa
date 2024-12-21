from database import grant_access
from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes
from config import PRICE_SINGLE_ACCESS, PRICE_FULL_ACCESS


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_chat.id:
        return

    chat_id = update.effective_chat.id
    args = context.args if context.args else []

    if len(args) < 1 or args[0] not in ['single', 'full']:
        if update.message:
            await update.message.reply_text(
                'Укажите тип оплаты: /pay single или /pay full'
            )
        return

    if args[0] == 'single':
        title = 'Расшифровка подарка (1 раз)'
        description = 'Позволяет увидеть одно сообщение.'
        price = PRICE_SINGLE_ACCESS
        payload = 'single_access'
    else:
        title = 'Полный доступ к расшифровкам подарков для друзей'
        description = 'Позволяет получить доступ к функциям комнаты.'
        price = PRICE_FULL_ACCESS
        payload = 'full_access'

    prices = [LabeledPrice(label=title, amount=price)]
    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token='YOUR_PROVIDER_TOKEN',
            currency='RUB',
            prices=prices
        )
    except Exception as e:
        if update.message:
            await update.message.reply_text(f'Ошибка при оплате: {str(e)}')


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.successful_payment:
        return

    user_id = update.effective_user.id if update.effective_user else None
    payload = update.message.successful_payment.invoice_payload

    if user_id is None:
        if update.message:
            await update.message.reply_text('Ошибка: не возможно определить пользователя.')
        return

    if payload == 'single_access':
        grant_access(user_id, access_type='single')
        if update.message:
            await update.message.reply_text('Вы успешно оплатили одноразовый доступ!')
    elif payload == 'full_access':
        grant_access(user_id, access_type='full')
        if update.message:
            await update.message.reply_text('Вы успешно оплатили полный доступ')
    else:
        if update.message:
            await update.message.reply_text('Неизвестный тип платежа.')
