# Secret Santa Bot

Telegram бот для организации тайного Санты. Позволяет создавать комнаты, добавлять желания и просматривать желания других участников.

## Структура проекта

```
Secret_Santa/
├── __init__.py           # Инициализация пакета
├── main.py               # Основной файл запуска бота
├── start.py              # Инициализация бота
├── config.py             # Конфигурация проекта
├── database.py           # Модели и функции для работы с базой данных
├── rooms.py              # Функции для работы с комнатами
├── wishes.py             # Функции для работы с желаниями
├── keyboards.py          # Клавиатуры для бота
├── payment_handler.py    # Обработка платежей
├── scheduler.py          # Планировщик задач
├── utils.py              # Вспомогательные функции
├── .env                  # Переменные окружения
├── requirements.txt      # Зависимости проекта
├── README.md             # Документация проекта
├── handlers/             # Обработчики команд
│   └── __init__.py
├── templates/            # Шаблоны сообщений
│   └── __init__.py
├── scripts/              # Скрипты для управления
│   ├── __init__.py
│   ├── db_manage.py      # Управление базой данных
│   ├── check_db.py       # Проверка базы данных
│   └── test_bot_functions.py # Тестирование функций
└── tests/                # Тесты
    ├── __init__.py
    ├── test_bot.py       # Тесты бота
    └── test_data.py      # Тестовые данные
```

## Установка и настройка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/yourusername/Secret_Santa.git
cd Secret_Santa
```

2. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
pip install -r requirements.txt
```

3. Создайте файл `.env` с необходимыми переменными окружения:

```
BOT_TOKEN=your_bot_token
PAYMENT_TOKEN=your_payment_token
ENVIRONMENT=development
```

4. Инициализируйте базу данных:

```bash
python scripts/db_manage.py init-db
```

5. Запустите бота:

```bash
python main.py
```

## Тестирование

1. Запустите тесты:

```bash
pytest tests/
```

2. Проверьте базу данных:

```bash
python scripts/check_db.py
```

3. Создайте тестовые данные:

```bash
python scripts/db_manage.py create-test-data
```

4. Тестируйте функции бота:

```bash
python scripts/test_bot_functions.py
```

## Функциональность

- Создание комнат для тайного Санты
- Добавление и редактирование желаний
- Просмотр желаний других участников
- Система оплаты для расширенного функционала
- Автоматическая рассылка желаний

## Лицензия

MIT
