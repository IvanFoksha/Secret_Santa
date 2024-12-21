from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler
from handlers.start import start_command, help_command, button_handler
from handlers.rooms import create_room_handler, join_room_handler
from handlers.wishes import create_wish_handler, edit_wish_hendler, delete_wish_handler
from handlers.payment_handler import process_payment, successful_payment
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
    app.add_handler(create_room_handler)
    app.add_handler(join_room_handler)
    app.add_handler(create_wish_handler)
    app.add_handler(edit_wish_hendler)
    app.add_handler(delete_wish_handler)
    app.add_handler(process_payment)
    app.add_handler(PreCheckoutQueryHandler(successful_payment))

    print('Добро пожаловать к Санте!')
    app.run_polling()


signal.signal(signal.SIGINT, stop_bot)

if __name__ == '__main__':
    main()
