from database import grant_access
from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes, PreCheckoutQueryHandler
from config import PRICE_SINGLE_ACCESS, PRICE_FULL_ACCESS

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) < 1 or args[0] not in ['single', 'full']:
        await update.message.reply_text('Укажите тип оплаты: /pay single или /pay full')
        return
    
    if args[0] == 'single':
        title = 'Расшифровка подарка (1 раз)'
        description = 'Позваляет увидеть одно сообщение.'
        price = PRICE_SINGLE_ACCESS
    else:
        title = 'Полный доступ к расшифровкам подарков для друзей'
        description = 'Позволяет получить доступ к функциям комнаты.'
        price = PRICE_FULL_ACCESS

    prices = [LabeledPrice(label=title, amount=price)]
    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload='custom_payload',
        provider_token='YOUR_PROVIDER_TOKEN',
        currency='RUB',
        prices=prices
    )

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload

    if payload == 'single_access':
        grant_access(user_id, single=True)
        await update.message.reply_text('Вы успешно оплатили одноразовый доступ!')
    elif payload == 'full_access':
        grant_access(user_id, single=False)
        await update.message.reply_text('Вы успешно оплатили полный доступ')
