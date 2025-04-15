# Secret Santa Bot

Telegram бот для организации "Тайного Санты" с поддержкой платной и бесплатной версий.

## Возможности

- Создание и управление комнатами
- Система желаний с автоматической отправкой
- Платная и бесплатная версии
- Автоматическая отправка желаний в полночь

## Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/yourusername/secret-santa-bot.git
cd secret-santa-bot
```

2. Создайте виртуальное окружение и активируйте его:

```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` и заполните его:

```env
BOT_TOKEN=your_bot_token_here
PAYMENT_TOKEN=your_payment_token_here
ADMIN_ID=your_telegram_id_here
```

## Запуск

```bash
python main.py
```

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/create_room` - Создать новую комнату
- `/join_room` - Присоединиться к комнате
- `/room_info` - Информация о комнате
- `/create_wish` - Создать желание
- `/edit_wish` - Редактировать желание
- `/delete_wish` - Удалить желание
- `/list_wishes` - Список желаний
- `/pay` - Оплатить доступ

## Версии

### Бесплатная версия

- До 5 пользователей в комнате
- До 3 желаний для каждого
- 1 бесплатный просмотр желания

### Платная версия

- До 10 пользователей в комнате
- До 10 желаний для каждого
- Неограниченный просмотр желаний

## Лицензия

MIT
