"""
Вспомогательные функции для Telegram бота
"""

import json
import re
import logging
import os
import sys
import platform
import fcntl
import time
from datetime import datetime
from typing import Dict, Any
from config.constants import VALIDATION_RULES

logger = logging.getLogger(__name__)

def create_callback_data(action: str, **kwargs) -> str:
    """
    Создает callback_data для инлайн кнопок
    
    Args:
        action: Действие
        **kwargs: Дополнительные параметры
        
    Returns:
        JSON строка для callback_data
    """
    data = {"action": action}
    data.update(kwargs)
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

def parse_callback_data(callback_data: str) -> Dict[str, Any]:
    """
    Парсит callback_data
    
    Args:
        callback_data: JSON строка
        
    Returns:
        Словарь с данными
    """
    try:
        return json.loads(callback_data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error parsing callback data: {e}")
        return {}

def validate_name(name: str) -> bool:
    """
    Валидация имени сотрудника
    
    Args:
        name: Имя для проверки
        
    Returns:
        True если имя валидно
    """
    if not name or not isinstance(name, str):
        return False
    
    name = name.strip()
    return (VALIDATION_RULES['name_min_length'] <= len(name) <= 
            VALIDATION_RULES['name_max_length'])

def validate_position(position: str) -> bool:
    """
    Валидация должности
    
    Args:
        position: Должность для проверки
        
    Returns:
        True если должность валидна
    """
    if not position or not isinstance(position, str):
        return False
    
    return len(position.strip()) <= VALIDATION_RULES['position_max_length']

def validate_event_type(event_type: str) -> bool:
    """
    Валидация типа события
    
    Args:
        event_type: Тип события для проверки
        
    Returns:
        True если тип события валиден
    """
    if not event_type or not isinstance(event_type, str):
        return False
    
    event_type = event_type.strip()
    return (VALIDATION_RULES['event_type_min_length'] <= len(event_type) <= 
            VALIDATION_RULES['event_type_max_length'])

def validate_date(date_str: str) -> bool:
    """
    Валидация даты в формате ДД.ММ.ГГГГ
    
    Args:
        date_str: Строка даты
        
    Returns:
        True если дата валидна
    """
    if not date_str or not isinstance(date_str, str):
        return False
    
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

def validate_interval(interval_str: str) -> bool:
    """
    Валидация интервала в днях
    
    Args:
        interval_str: Строка с интервалом
        
    Returns:
        True если интервал валиден
    """
    try:
        interval = int(interval_str)
        return (VALIDATION_RULES['interval_min_days'] <= interval <= 
                VALIDATION_RULES['interval_max_days'])
    except (ValueError, TypeError):
        return False

def format_date(date_obj: datetime) -> str:
    """
    Форматирует дату для отображения
    
    Args:
        date_obj: Объект даты
        
    Returns:
        Отформатированная строка даты
    """
    return date_obj.strftime('%d.%m.%Y')

def get_days_until(target_date: datetime) -> int:
    """
    Вычисляет количество дней до целевой даты
    
    Args:
        target_date: Целевая дата
        
    Returns:
        Количество дней (может быть отрицательным для прошедших дат)
    """
    if isinstance(target_date, str):
        target_date = datetime.fromisoformat(target_date)
    
    today = datetime.now().date()
    if hasattr(target_date, 'date'):
        target_date = target_date.date()
    
    return (target_date - today).days

def singleton_lock():
    """
    Кросс-платформенная блокировка файла для предотвращения дублирующих запусков
    
    Returns:
        Объект файла блокировки
    """
    lock_file = 'bot.lock'
    try:
        # Очистка устаревших блокировок
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        os.remove(lock_file)
                    else:
                        pid = int(content)

                        # Проверка активности процесса
                        if platform.system() == 'Windows':
                            try:
                                import ctypes
                                # Константы для Windows API
                                PROCESS_QUERY_INFORMATION = 0x0400
                                process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
                                if process:
                                    ctypes.windll.kernel32.CloseHandle(process)
                                else:
                                    # Процесс не найден
                                    os.remove(lock_file)
                            except (OSError, ImportError):
                                os.remove(lock_file)
                        else:
                            # Linux/Unix проверка
                            try:
                                os.kill(pid, 0)  # Проверка существования процесса
                            except (OSError, ProcessLookupError):
                                os.remove(lock_file)
            except (ValueError, OSError, IOError):
                os.remove(lock_file)

        # Создание новой блокировки
        lock_fd = open(lock_file, 'w')
        if platform.system() == 'Windows':
            import msvcrt
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError) as e:
        print(f"Another instance is running or lock error: {e}")
        sys.exit(1)

async def delete_message_safely(context, chat_id, message_id):
    """
    Безопасно удаляет сообщение, игнорируя ошибки
    
    Args:
        context: Контекст бота
        chat_id: ID чата
        message_id: ID сообщения
    """
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        # Игнорируем ошибки удаления сообщений
        pass
