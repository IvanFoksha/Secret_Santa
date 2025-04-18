import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class BaseConfig:
    """Базовая конфигурация"""
    DATABASE_URL = "sqlite:///Santa_bot.db"
    DB_PATH = "Santa_bot.db"
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
    MAX_FREE_USERS = 5
    MAX_PAID_USERS = 10

class TestConfig(BaseConfig):
    """Конфигурация для тестирования"""
    DATABASE_URL = "sqlite:///test_santa_bot.db"
    DB_PATH = "test_santa_bot.db"
    BOT_TOKEN = "test_token"
    PAYMENT_TOKEN = "test_payment_token"

class ProductionConfig(BaseConfig):
    """Конфигурация для продакшена"""
    DATABASE_URL = os.getenv("DATABASE_URL", BaseConfig.DATABASE_URL)
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")

# Выбор конфигурации
config = {
    'development': BaseConfig,
    'testing': TestConfig,
    'production': ProductionConfig
}

current_config = config[os.getenv('ENVIRONMENT', 'development')]()

# ID администратора
ADMIN_ID = os.getenv('ADMIN_ID')

# Настройки платежей
PRICE_FULL_ACCESS = 29900  # 299 рублей в копейках
PRICE_SINGLE_ACCESS = 9900  # 99 рублей в копейках

# Настройки комнат
FREE_MAX_USERS = current_config.MAX_FREE_USERS
PRO_MAX_USERS = current_config.MAX_PAID_USERS

# Настройки желаний
FREE_MAX_WISHES = 3  # Максимальное количество желаний в бесплатной версии
PRO_MAX_WISHES = 10  # Максимальное количество желаний в PRO версии
