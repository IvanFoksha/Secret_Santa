from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler
from handlers.start import start_command, help_command, button_handler
from rooms import create_room_handler, join_room_handler
from wishes import create_wish_handler, edit_wish_handler, delete_wish_handler
from payment_handler import process_payment, successful_payment
from database import init_bd
from config import BOT_TOKEN
import signal
import sys


def stop_bot(signal, frame):
    print(
        '\nСанта ждет тебя обратно!/\n\n'
        'Чтобы запустить бота введите - /start'
    )
    sys.exit(0)


def main():
    init_bd()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(CallbackQueryHandler(create_room_handler, pattern='^create_room$'))
    app.add_handler(CallbackQueryHandler(join_room_handler, pattern='^join_room$'))
    app.add_handler(CallbackQueryHandler(create_wish_handler, pattern='^create_wish$'))
    app.add_handler(CallbackQueryHandler(edit_wish_handler, pattern='^edit_wish$'))
    app.add_handler(CallbackQueryHandler(delete_wish_handler, pattern='^delete_wish$'))

    app.add_handler(CallbackQueryHandler(process_payment, pattern='^process_payment$'))
    app.add_handler(PreCheckoutQueryHandler(successful_payment))

    print('Добро пожаловать к Санте!')
    app.run_polling()


signal.signal(signal.SIGINT, stop_bot)

if __name__ == '__main__':
    main()
