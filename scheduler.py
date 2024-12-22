from apscheduler.schedulers.background import BackgroundScheduler
from database import get_room_wishes, get_all_rooms
from telegram import Bot
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)


def send_night_messages():
    rooms = get_all_rooms()
    for room in rooms:
        wishes = get_room_wishes(room['room_id'])
        for wish in wishes:
            for recipient in room['users']:
                if recipient != wish['user_id']:
                    bot.send_message(
                        chat_id=recipient,
                        text=f'🎅 {wish["user_name"]} хочет на Новый год: {wish["wish_text"]}'
                        )


sheduler = BackgroundScheduler()
sheduler.add_job(send_night_messages, 'cron', hour=0)
sheduler.start()
