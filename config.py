import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Токен платежной системы
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN')

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Santa_bot.db')

# ID администратора
ADMIN_ID = os.getenv('ADMIN_ID')

# Настройки платежей
PRICE_FULL_ACCESS = 29900  # 299 рублей в копейках
PRICE_SINGLE_ACCESS = 9900  # 99 рублей в копейках

# Настройки комнат
MAX_FREE_USERS = 5
MAX_PAID_USERS = 10
MAX_FREE_WISHES = 3
MAX_PAID_WISHES = 10

# Константы для версий комнат (используются в rooms.py)
FREE_MAX_USERS = MAX_FREE_USERS
PRO_MAX_USERS = MAX_PAID_USERS
FREE_WISHES_PER_USER = 1
PRO_WISHES_PER_USER = 5

# Константы для лимитов желаний (используются в wishes.py)
FREE_WISH_LIMIT = 10  # Временно увеличенный лимит для тестирования
PRO_WISH_LIMIT = 20   # Временно увеличенный лимит для тестирования

# Настройки времени
WISH_DEADLINE_HOUR = 22  # Час, до которого можно добавить желание
WISH_DELIVERY_HOUR = 0   # Час, когда отправляются желания
