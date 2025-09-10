"""
Настройки и конфигурация для Telegram бота управления периодическими событиями
"""

import os
import pytz
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class BotConfig:
    """Конфигурация бота"""
    
    # Telegram Bot настройки
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    
    # База данных
    DB_PATH = os.getenv('DB_PATH', 'periodic_events.db')
    
    # Безопасность
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Логирование
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'bot.log'
    
    # Уведомления
    DEFAULT_TIMEZONE = 'Europe/Moscow'
    DEFAULT_NOTIFICATION_DAYS = 90  # Первое уведомление за 90 дней
    NOTIFICATION_TIME_HOUR = 9      # Время отправки уведомлений (UTC)
    BACKUP_TIME_HOUR = 3           # Время резервного копирования (UTC)
    
    # Пагинация
    EMPLOYEES_PER_PAGE = 10
    SEARCH_RESULTS_LIMIT = 10
    
    # Telegram API
    POLLING_INTERVAL = 2.0
    TIMEOUT = 20
    
    @classmethod
    def get_timezone(cls):
        """Получить объект часового пояса"""
        return pytz.timezone(cls.DEFAULT_TIMEZONE)
    
    @classmethod
    def init_encryption(cls):
        """Инициализация шифрования"""
        if not cls.SECRET_KEY:
            key = Fernet.generate_key().decode()
            with open('.env', 'a') as env_file:
                env_file.write(f'\nSECRET_KEY={key}')
            load_dotenv()
            cls.SECRET_KEY = os.getenv('SECRET_KEY')
        
        if cls.SECRET_KEY:
            return Fernet(cls.SECRET_KEY.encode())
        else:
            raise ValueError("Could not initialize encryption key")

# Глобальная инициализация шифрования
encryption_manager = BotConfig.init_encryption()