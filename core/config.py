"""
Модуль конфигурации ядра системы
"""

import os
from typing import Optional

class CoreConfig:
    """Основная конфигурация системы"""
    
    # Пути к файлам
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(PROJECT_ROOT, 'periodic_events.db')
    LOG_PATH = os.path.join(PROJECT_ROOT, 'bot.log')
    
    # Настройки базы данных
    DB_TIMEOUT = 30
    DB_RETRY_COUNT = 3
    
    # Настройки безопасности
    ENCRYPTION_KEY_LENGTH = 32
    
    # Настройки логирования
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def get_env_var(cls, var_name: str, default: Optional[str] = None) -> Optional[str]:
        """Получение переменной окружения"""
        return os.getenv(var_name, default)
    
    @classmethod
    def get_project_path(cls, *path_parts) -> str:
        """Получение полного пути относительно корня проекта"""
        return os.path.join(cls.PROJECT_ROOT, *path_parts)