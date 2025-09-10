"""
Telegram-бот для управления периодическими событиями сотрудников
"""

# ================================================================
# БЛОК 1: Импорт библиотек и настройка окружения
# ================================================================
import os
import sys
import re
import json
import sqlite3
import logging
import platform
import traceback
import shutil
import fcntl
import time
from datetime import datetime, timedelta, time as dt_time
from logging.handlers import RotatingFileHandler

import pytz
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
    ContextTypes, CallbackContext
)
import io
import csv
import xlsxwriter
from enum import Enum
from typing import List, Dict, Optional

from phase1_improvements import init_phase1_managers, NotificationLevel

# ================================================================
# БЛОК 2: Безопасность и настройка окружения
# ================================================================
def singleton_lock():
    """Кросс-платформенная блокировка файла для предотвращения дублирующих запусков"""
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


# Инициализация шифрования
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    key = Fernet.generate_key().decode()
    with open('.env', 'a') as env_file:
        env_file.write(f'\nSECRET_KEY={key}')
    load_dotenv()
    SECRET_KEY = os.getenv('SECRET_KEY')

if SECRET_KEY:
    fernet = Fernet(SECRET_KEY.encode())
else:
    print("Error: Could not initialize encryption key")
    sys.exit(1)


# Шифрование конфиденциальных данных
def encrypt_data(data: str) -> str:
    """Шифрует строку с использованием Fernet"""
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Дешифрует строку с использованием Fernet"""
    try:
        return fernet.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        print(f"Decryption failed: {e}")
        raise ValueError("Decryption error")


# ================================================================
# БЛОК 3: Работа с базой данных
# ================================================================
class DatabaseManager:
    def __init__(self, db_path='periodic_events.db'):
        self.db_path = db_path
        self.connection_pool = []
        self.max_connections = 10
        self.init_db()

    def init_db(self):
        """Инициализация базы данных с необходимыми таблицами"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Таблица настроек чата
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER UNIQUE NOT NULL,
                        admin_id INTEGER NOT NULL,
                        timezone TEXT DEFAULT 'Europe/Moscow',
                        notification_days INTEGER DEFAULT 90,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Таблица сотрудников
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS employees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER NOT NULL,
                        user_id INTEGER,
                        full_name TEXT NOT NULL,
                        position TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chat_settings(chat_id),
                        UNIQUE(chat_id, full_name)
                    )
                ''')

                # Таблица событий сотрудников
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS employee_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        event_type TEXT NOT NULL,
                        last_event_date DATE NOT NULL,
                        interval_days INTEGER NOT NULL,
                        next_notification_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees(id)
                    )
                ''')

                # История уведомлений
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    notification_type TEXT NOT NULL,
                    sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'sent',
                    FOREIGN KEY (event_id) REFERENCES employee_events(id)
                )
            ''')

                # Пользовательские шаблоны
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    template_name TEXT NOT NULL,
                    template_data TEXT NOT NULL, -- JSON
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chat_settings(chat_id)
                )
            ''')

                # Создание индексов для оптимизации
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_chat_id ON employees(chat_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_employee_id ON employee_events(employee_id)')
                cursor.execute(
                    'CREATE INDEX IF NOT EXISTS idx_events_notification_date ON employee_events(next_notification_date)')

                cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_history_event_id ON notification_history(event_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_templates_chat_id ON custom_templates(chat_id)')
            
                conn.commit()
                print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise

    def get_connection(self):
        """Возвращает соединение с автоматическим retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                # Включаем WAL режим для лучшей производительности
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                return conn
            except sqlite3.OperationalError as e:
                if attempt == max_retries - 1:
                    print(f"Database connection failed after {max_retries} attempts: {e}")
                    raise
                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff

    def execute_with_retry(self, query: str, params: tuple = (), fetch: str = None):
        """Выполнение запроса с автоматическим retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)

                    if fetch == "one":
                        return cursor.fetchone()
                    elif fetch == "all":
                        return cursor.fetchall()
                    elif fetch == "many":
                        return cursor.fetchmany()

                    conn.commit()
                    return cursor.lastrowid if query.strip().upper().startswith("INSERT") else None

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                print(f"Database error: {e}")
                raise
            except Exception as e:
                print(f"Unexpected database error: {e}")
                raise

    def create_backup(self):
        """Создание резервной копии базы данных"""
        try:
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, backup_path)
            print(f"Backup created: {backup_path}")

            # Очистка старых бэкапов (оставляем только 7 последних)
            backup_pattern = f"{self.db_path}.backup_"
            backups = [f for f in os.listdir('.') if f.startswith(backup_pattern)]
            backups.sort(reverse=True)

            for old_backup in backups[7:]:
                os.remove(old_backup)
                print(f"Removed old backup: {old_backup}")

        except Exception as e:
            print(f"Backup creation failed: {e}")


# ================================================================
# БЛОК 4: Валидация и служебные функции
# ================================================================
def validate_date(date_str: str) -> bool:
    """Проверка корректности даты в формате ДД.ММ.ГГГГ"""
    return bool(re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str))


def validate_interval(interval_str: str) -> bool:
    """Проверка корректности интервала (1-3650 дней)"""
    return interval_str.isdigit() and 1 <= int(interval_str) <= 3650


def validate_name(name: str) -> bool:
    """Проверка ФИО (2-100 символов, буквы, пробелы и дефисы)"""
    return (2 <= len(name) <= 100 and
            bool(re.match(r'^[\w\s\-]+$', name, re.UNICODE)))


def validate_position(position: str) -> bool:
    """Проверка должности (2-50 символов)"""
    return 2 <= len(position) <= 50


def validate_event_type(event_type: str) -> bool:
    """Проверка типа события (2-50 символов)"""
    return 2 <= len(event_type) <= 50


def validate_input(value: str, input_type: str, min_len: int = 2, max_len: int = 100) -> tuple[bool, str]:
    """Универсальная функция валидации с подробными сообщениями об ошибках"""
    if not value or not value.strip():
        return False, f"❌ {input_type} не может быть пустым"

    value = value.strip()
    if len(value) < min_len:
        return False, f"❌ {input_type} должен содержать минимум {min_len} символов"

    if len(value) > max_len:
        return False, f"❌ {input_type} не может содержать более {max_len} символов"

    # Специфичные проверки
    if input_type == "ФИО":
        if not re.match(r'^[\w\s\-\'\.]+$', value, re.UNICODE):
            return False, "❌ ФИО может содержать только буквы, пробелы, дефисы и точки"

    elif input_type == "Дата":
        if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', value):
            return False, "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ"
        try:
            date_obj = datetime.strptime(value, "%d.%m.%Y")
            if date_obj.date() > datetime.now().date():
                return False, "❌ Дата не может быть в будущем"
        except ValueError:
            return False, "❌ Неверная дата"

    elif input_type == "Интервал":
        if not value.isdigit():
            return False, "❌ Интервал должен быть числом"
        interval = int(value)
        if not (1 <= interval <= 3650):
            return False, "❌ Интервал должен быть от 1 до 3650 дней"

    return True, ""


def create_callback_data(action: str, **kwargs) -> str:
    """Создание безопасного callback_data в формате JSON с ограничением длины"""
    data = {"action": action, **kwargs}
    callback_str = json.dumps(data, separators=(',', ':'))

    # Telegram ограничивает callback_data до 64 байт
    if len(callback_str.encode('utf-8')) > 64:
        # Сокращаем или хешируем данные
        import hashlib
        hash_obj = hashlib.md5(callback_str.encode()).hexdigest()[:8]
        return json.dumps({"action": action, "hash": hash_obj})

    return callback_str


def parse_callback_data(data: str) -> dict:
    """Парсинг callback_data с обработкой ошибок"""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"action": "invalid"}


def is_admin(chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT admin_id FROM chat_settings WHERE chat_id = ?",
                (chat_id,)
            )
            result = cursor.fetchone()
            return result and user_id == result["admin_id"]
    except Exception:
        return False


def get_chat_timezone(chat_id: int) -> pytz.timezone:
    """Возвращает часовой пояс чата"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timezone FROM chat_settings WHERE chat_id = ?",
                (chat_id,)
            )
            result = cursor.fetchone()
            return pytz.timezone(result["timezone"] if result else 'UTC')
    except Exception:
        return pytz.timezone('UTC')


# ================================================================
# БЛОК 5: Логирование и обработка ошибок
# ================================================================
def setup_logging():
    """Настройка продвинутой системы логирования"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # JSON-форматер для структурированных логов
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(message)s %(module)s %(funcName)s'
    )

    # Консольный вывод
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # Файловый вывод с ротацией
    file_handler = RotatingFileHandler(
        'bot.log', maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    # Перехват необработанных исключений
    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.error("Uncaught exception",
                     exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    return logger


logger = setup_logging()


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок бота"""
    error = context.error
    logger.error(f"Global error: {error}", exc_info=True)

    # Формирование сообщения об ошибке
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = ''.join(tb_list)[:3000]

    error_message = (
        f"🚨 <b>CRITICAL ERROR</b>\n"
        f"<pre>{error}</pre>\n\n"
        f"<code>{tb_string}</code>"
    )

    # Отправка администратору
    admin_id = os.getenv('ADMIN_ID')
    if admin_id:
        try:
            await context.bot.send_message(
                chat_id=int(admin_id),
                text=error_message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error notification failed: {e}")

    # Ответ пользователю
    if update and isinstance(update, Update):
        try:
            if update.message:
                await update.message.reply_text(
                    "⚠️ Произошла непредвиденная ошибка. Администратор уведомлен."
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "⚠️ Произошла непредвиденная ошибка. Администратор уведомлен."
                )
        except Exception:
            pass


# ================================================================
# БЛОК 6: Основные функции бота
# ================================================================
# Константы состояний разговора
(
    ADD_NAME, ADD_POSITION, ADD_EVENT_TYPE,
    ADD_LAST_DATE, ADD_INTERVAL, SET_NOTIFICATION_DAYS
) = range(6)

# Инициализация менеджера БД
db_manager = DatabaseManager()
notification_manager, excel_exporter, search_manager, template_manager = init_phase1_managers(db_manager)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start и инициализация чата"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT admin_id FROM chat_settings WHERE chat_id = ?",
                (chat_id,)
            )
            settings = cursor.fetchone()

            if not settings:
                cursor.execute(
                    "INSERT INTO chat_settings (chat_id, admin_id) VALUES (?, ?)",
                    (chat_id, user_id)
                )
                conn.commit()
                await update.message.reply_text(
                    "Привет! Я бот для учета периодических событий. "
                    "Вы назначены администратором этого чата."
                )
            else:
                await update.message.reply_text(
                    "Привет! Я бот для учета периодических событий."
                )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "Произошла ошибка при инициализации. Попробуйте позже."
        )

    await show_menu(update, context)



async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обновленное главное меню с новыми функциями"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("📅 Мои события", callback_data=create_callback_data("my_events"))]
    ]

    if is_admin(chat_id, user_id):
        admin_buttons = [
            [
                InlineKeyboardButton("👨‍💼 Добавить сотрудника", callback_data=create_callback_data("add_employee")),
                InlineKeyboardButton("📋 Список сотрудников", callback_data=create_callback_data("list_employees"))
            ],
            [
                InlineKeyboardButton("📊 Все события", callback_data=create_callback_data("all_events")),
                InlineKeyboardButton("🔍 Поиск", callback_data=create_callback_data("search_menu"))
            ],
            [
                InlineKeyboardButton("📁 Экспорт", callback_data=create_callback_data("export_menu")),
                InlineKeyboardButton("📋 Шаблоны", callback_data=create_callback_data("templates"))
            ],
            [InlineKeyboardButton("⚙️ Настройки", callback_data=create_callback_data("settings"))]
        ]
        keyboard.extend(admin_buttons)

    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data=create_callback_data("help"))])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message:
            await update.message.reply_text(
                "📱 <b>Главное меню</b>\n✨ <i>Обновленная версия с расширенными возможностями</i>\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "📱 <b>Главное меню</b>\n✨ <i>Обновленная версия с расширенными возможностями</i>\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error showing enhanced menu: {e}")


async def enhanced_show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обновленное главное меню с новыми функциями"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("📅 Мои события", callback_data=create_callback_data("my_events"))]
    ]

    if is_admin(chat_id, user_id):
        admin_buttons = [
            [
                InlineKeyboardButton("👨‍💼 Добавить сотрудника", callback_data=create_callback_data("add_employee")),
                InlineKeyboardButton("📋 Список сотрудников", callback_data=create_callback_data("list_employees"))
            ],
            [
                InlineKeyboardButton("📊 Все события", callback_data=create_callback_data("all_events")),
                InlineKeyboardButton("🔍 Поиск", callback_data=create_callback_data("search_menu"))
            ],
            [
                InlineKeyboardButton("📁 Экспорт", callback_data=create_callback_data("export_menu")),
                InlineKeyboardButton("📋 Шаблоны", callback_data=create_callback_data("templates"))
            ],
            [InlineKeyboardButton("⚙️ Настройки", callback_data=create_callback_data("settings"))]
        ]
        keyboard.extend(admin_buttons)

    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data=create_callback_data("help"))])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message:
            await update.message.reply_text(
                "📱 <b>Главное меню</b>\n✨ <i>Версия 2.0 с расширенными возможностями</i>\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "📱 <b>Главное меню</b>\n✨ <i>Версия 2.0 с расширенными возможностями</i>\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error showing enhanced menu: {e}")


# ================================================================
# БЛОК 7: Управление сотрудниками и событиями
# ================================================================
async def add_employee_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса добавления сотрудника с отправкой запроса"""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может добавлять сотрудников")
        return ConversationHandler.END

    # Создаем клавиатуру с вариантами действий
    keyboard = [
        [KeyboardButton("📱 Отправить контакт", request_contact=True)],
        [KeyboardButton("❌ Отмена")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Отправляем сообщение с запросом
    await context.bot.send_message(
        chat_id=chat_id,
        text="Введите ФИО сотрудника или отправьте контакт:",
        reply_markup=reply_markup
    )
    return ADD_NAME


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка контакта сотрудника"""
    contact = update.message.contact
    context.user_data['user_id'] = contact.user_id
    context.user_data[
        'full_name'] = f"{contact.first_name} {contact.last_name}" if contact.last_name else contact.first_name

    # Показываем клавиатуру выбора должности
    await show_position_selection(update, context)
    return ADD_POSITION


async def add_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода ФИО сотрудника"""
    full_name = update.message.text
    if not validate_name(full_name):
        await update.message.reply_text("❌ Неверный формат имени. Должно быть 2-100 символов.")
        return ADD_NAME

    context.user_data['full_name'] = full_name
    # Показываем клавиатуру выбора должности
    await show_position_selection(update, context)
    return ADD_POSITION


async def save_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет сотрудника и переходит к добавлению события"""
    # Эта функция теперь вызывается через callback от кнопки выбора должности
    return ConversationHandler.END  # Эта функция больше не используется


async def show_position_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает клавиатуру с выбором должностей"""
    # Получаем список доступных должностей из шаблонов
    positions = [
        "Плотник",
        "Маляр", 
        "Рабочий по комплексному обслуживанию и ремонту зданий",
        "Дворник",
        "Уборщик производственных помещений",
        "Старший мастер",
        "Мастер"
    ]
    
    # Создаем клавиатуру с должностями (по 2 в ряд)
    keyboard = []
    for i in range(0, len(positions), 2):
        row = []
        for j in range(2):
            if i + j < len(positions):
                row.append(InlineKeyboardButton(
                    positions[i + j],
                    callback_data=create_callback_data("select_position", position=positions[i + j])
                ))
        keyboard.append(row)
    
    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=create_callback_data("cancel_add_employee"))])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👤 Сотрудник: <b>{context.user_data['full_name']}</b>\n\n"
        "💼 Выберите должность:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def handle_position_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора должности из списка"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    position = data.get('position')
    
    if not position:
        await query.edit_message_text("❌ Ошибка при выборе должности")
        return ConversationHandler.END
    
    user_data = context.user_data
    full_name = user_data['full_name']
    user_id = user_data.get('user_id')
    chat_id = update.effective_chat.id

    # Шифрование конфиденциальных данных
    encrypted_name = encrypt_data(full_name)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO employees (chat_id, user_id, full_name, position)
                   VALUES (?, ?, ?, ?)''',
                (chat_id, user_id, encrypted_name, position)
            )
            # Сохраняем ID нового сотрудника для добавления события
            user_data['new_employee_id'] = cursor.lastrowid
            conn.commit()

        # Переходим к добавлению события
        await query.edit_message_text(
            f"✅ Сотрудник <b>{full_name}</b> с должностью <b>{position}</b> успешно добавлен!\n\n"
            "📅 Введите тип периодического события (например, 'Медосмотр' / 'Проверка знаний П-1' и т.д.):",
            parse_mode='HTML'
        )
        return ADD_EVENT_TYPE
    except sqlite3.IntegrityError:
        await query.edit_message_text("❌ Сотрудник с таким именем уже существует")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error saving employee: {e}")
        await query.edit_message_text("❌ Произошла ошибка при сохранении сотрудника")
        return ConversationHandler.END


async def add_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода типа события"""
    event_type = update.message.text
    if not validate_event_type(event_type):
        await update.message.reply_text("❌ Неверный формат типа события. Должно быть 2-50 символов.")
        return ADD_EVENT_TYPE

    context.user_data['event_type'] = event_type
    await update.message.reply_text(
        "Введите дату последнего события в формате ДД.ММ.ГГГГ (например, 15.05.2023):"
    )
    return ADD_LAST_DATE


async def add_last_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода даты последнего события"""
    date_str = update.message.text
    if not validate_date(date_str):
        await update.message.reply_text("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return ADD_LAST_DATE

    try:
        # Преобразуем дату в объект datetime
        last_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        context.user_data['last_date'] = last_date.isoformat()

        await update.message.reply_text(
            "Введите интервал в днях между событиями (например, 365):"
        )
        return ADD_INTERVAL
    except ValueError:
        await update.message.reply_text("❌ Неверная дата. Проверьте правильность ввода.")
        return ADD_LAST_DATE


async def add_interval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода интервала и сохранение события"""
    interval_str = update.message.text
    if not validate_interval(interval_str):
        await update.message.reply_text("❌ Неверный интервал. Введите число от 1 до 3650.")
        return ADD_INTERVAL

    interval = int(interval_str)
    user_data = context.user_data

    # Рассчитываем следующую дату уведомления
    last_date = datetime.fromisoformat(user_data['last_date']).date()
    next_date = last_date + timedelta(days=interval)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO employee_events 
                   (employee_id, event_type, last_event_date, interval_days, next_notification_date)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_data['new_employee_id'], user_data['event_type'],
                 user_data['last_date'], interval, next_date.isoformat())
            )
            conn.commit()

        # Завершаем процесс
        await update.message.reply_text(
            f"✅ Событие '{user_data['event_type']}' успешно добавлено!\n"
            f"Следующее уведомление: {next_date.strftime('%d.%m.%Y')}",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_menu(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error saving event: {e}")
        await update.message.reply_text("❌ Произошла ошибка при сохранении события")
        return ConversationHandler.END


async def cancel_add_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка отмены добавления сотрудника"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("❌ Добавление сотрудника отменено")
        await show_menu(update, context)
    else:
        await update.message.reply_text(
            "❌ Добавление сотрудника отменено",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_menu(update, context)
    return ConversationHandler.END


# ================================================================
# БЛОК 8: Управление событиями и уведомлениями
# ================================================================
async def send_notifications(context: CallbackContext):
    """Ежедневная отправка уведомлений с улучшенной обработкой ошибок"""
    try:
        # Получаем уведомления с улучшенным запросом
        notifications = db_manager.execute_with_retry('''
            SELECT 
                ee.id, e.chat_id, e.user_id, 
                e.full_name, ee.event_type, 
                ee.next_notification_date,
                ee.interval_days, cs.admin_id, cs.timezone,
                cs.notification_days
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            JOIN chat_settings cs ON e.chat_id = cs.chat_id
            WHERE e.is_active = 1 
            AND date(ee.next_notification_date) BETWEEN date('now') 
            AND date('now', '+' || cs.notification_days || ' days')
            ORDER BY ee.next_notification_date
        ''', fetch="all")

        if not notifications:
            logger.info("No notifications to send")
            return

        success_count = 0
        error_count = 0

        for notification in notifications:
            try:
                # Определение часового пояса
                tz = pytz.timezone(notification['timezone'])
                today = datetime.now(tz).date()
                event_date = datetime.fromisoformat(notification['next_notification_date']).date()
                days_until = (event_date - today).days

                # Проверяем, нужно ли отправлять уведомление
                if days_until > notification['notification_days']:
                    continue

                # Расшифровка имени
                try:
                    full_name = decrypt_data(notification['full_name'])
                except ValueError:
                    logger.error(f"Failed to decrypt name for notification {notification['id']}")
                    continue

                # Формирование сообщения
                if days_until == 0:
                    urgency = "🔴 СЕГОДНЯ"
                elif days_until <= 3:
                    urgency = f"🟡 через {days_until} дней"
                else:
                    urgency = f"🟢 через {days_until} дней"

                message = (
                    f"🔔 <b>Напоминание: {notification['event_type']}</b>\n"
                    f"👤 Сотрудник: {full_name}\n"
                    f"📅 Дата события: {event_date.strftime('%d.%m.%Y')}\n"
                    f"⏰ Срочность: {urgency}"
                )

                # Отправка сотруднику
                if notification['user_id']:
                    try:
                        await context.bot.send_message(
                            chat_id=notification['user_id'],
                            text=message,
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send notification to user {notification['user_id']}: {e}")

                # Отправка администратору
                try:
                    await context.bot.send_message(
                        chat_id=notification['admin_id'],
                        text=f"[ADMIN] {message}",
                        parse_mode='HTML'
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification to admin {notification['admin_id']}: {e}")
                    error_count += 1

            except Exception as e:
                logger.error(f"Error processing notification {notification['id']}: {e}")
                error_count += 1

        logger.info(f"Notifications sent: {success_count} success, {error_count} errors")

    except Exception as e:
        logger.error(f"Critical error in send_notifications: {e}")


async def enhanced_send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Улучшенная система отправки уведомлений"""
    try:
        notifications = db_manager.execute_with_retry('''
            SELECT 
                ee.id, e.chat_id, e.user_id, e.full_name, e.position,
                ee.event_type, ee.next_notification_date, ee.interval_days,
                cs.admin_id, cs.timezone, cs.notification_days,
                e.id as employee_id
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            JOIN chat_settings cs ON e.chat_id = cs.chat_id
            WHERE e.is_active = 1 
            AND date(ee.next_notification_date) BETWEEN date('now', '-7 days')
            AND date('now', '+' || cs.notification_days || ' days')
            ORDER BY ee.next_notification_date
        ''', fetch="all")

        if not notifications:
            logger.info("No notifications to send")
            return

        notifications_sent = 0
        escalations_sent = 0

        for notification in notifications:
            try:
                # Определяем дни до события
                event_date = datetime.fromisoformat(notification['next_notification_date']).date()
                days_until = (event_date - datetime.now().date()).days

                # Определяем уровень уведомления
                level = notification_manager.get_notification_level(days_until)
                
                # Проверяем, нужно ли отправлять уведомление сегодня
                if not notification_manager.should_send_notification(level, days_until):
                    continue

                # Формируем сообщение
                message = notification_manager.format_notification_message(notification, level)
                keyboard = notification_manager.create_action_keyboard(notification)

                # Отправляем сотруднику
                if notification['user_id']:
                    try:
                        await context.bot.send_message(
                            chat_id=notification['user_id'],
                            text=message,
                            parse_mode='HTML',
                            reply_markup=keyboard
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send to user {notification['user_id']}: {e}")

                # Отправляем администратору
                try:
                    admin_message = f"[👨‍💼 ADMIN] {message}"
                    await context.bot.send_message(
                        chat_id=notification['admin_id'],
                        text=admin_message,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                    notifications_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send to admin {notification['admin_id']}: {e}")

                # Эскалация для критичных случаев
                if level in [NotificationLevel.CRITICAL, NotificationLevel.OVERDUE]:
                    await notification_manager.send_escalated_notifications(context, notification, level)
                    escalations_sent += 1

            except Exception as e:
                logger.error(f"Error processing notification {notification['id']}: {e}")

        logger.info(f"Enhanced notifications: {notifications_sent} sent, {escalations_sent} escalated")

    except Exception as e:
        logger.error(f"Critical error in enhanced_send_notifications: {e}")


# ================================================================
# БЛОК 9: Настройки и административные функции
# ================================================================
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отображение меню настроек"""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может изменять настройки")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("🕒 Изменить часовой пояс", callback_data=create_callback_data("set_timezone"))],
        [InlineKeyboardButton("⏰ Дни уведомлений", callback_data=create_callback_data("set_notif_days"))],
        [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
    ]

    await query.edit_message_text(
        "⚙️ <b>Настройки чата:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    return ConversationHandler.END


async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Устанавливает часовой пояс для чата"""
    query = update.callback_query
    await query.answer()

    # Получение доступных часовых поясов
    timezones = ["Europe/Moscow", "Asia/Yekaterinburg", "Europe/London", "America/New_York"]
    keyboard = []
    for tz in timezones:
        keyboard.append([InlineKeyboardButton(tz, callback_data=create_callback_data("set_tz", tz=tz))])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=create_callback_data("settings"))])

    await query.edit_message_text(
        "🌍 Выберите часовой пояс:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END


async def set_notification_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Устанавливает количество дней для предупреждения"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите количество дней для предварительного уведомления (1-30):")
    return SET_NOTIFICATION_DAYS


async def save_notification_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет количество дней для предупреждения"""
    try:
        days = int(update.message.text)
        if not 1 <= days <= 30:
            raise ValueError

        chat_id = update.effective_chat.id
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chat_settings SET notification_days = ? WHERE chat_id = ?",
                (days, chat_id)
            )
            conn.commit()

        await update.message.reply_text(f"✅ Установлено {days} дней для предварительного уведомления.")
        await show_menu(update, context)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Неверное значение. Введите число от 1 до 30:")
        return SET_NOTIFICATION_DAYS


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог и возвращает в меню"""
    await update.message.reply_text("❌ Операция отменена")
    context.user_data.clear()
    await show_menu(update, context)
    return ConversationHandler.END


# ================================================================
# БЛОК 10: Дополнительные функции
# ================================================================
async def list_employees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список сотрудников с пагинацией"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        if update.message:
            await update.message.reply_text("❌ Только администратор может просматривать список сотрудников.")
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text("❌ Только администратор может просматривать список сотрудников.")
        return

    # Определение текущей страницы
    page = context.user_data.get('employee_page', 0)
    limit = 5  # Количество сотрудников на странице

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Получение общего количества сотрудников
            cursor.execute(
                "SELECT COUNT(*) FROM employees WHERE chat_id = ? AND is_active = 1",
                (chat_id,)
            )
            total_count = cursor.fetchone()[0]

            # Получение сотрудников для текущей страницы
            cursor.execute(
                '''SELECT id, full_name, position 
                   FROM employees 
                   WHERE chat_id = ? AND is_active = 1
                   ORDER BY full_name
                   LIMIT ? OFFSET ?''',
                (chat_id, limit, page * limit)
            )
            employees = cursor.fetchall()

        if not employees:
            response = "ℹ️ В базе нет сотрудников."
            if update.message:
                await update.message.reply_text(response)
            else:
                query = update.callback_query
                await query.answer()
                await query.edit_message_text(response)
            return

        # Формирование сообщения
        response = [f"📋 <b>Список сотрудников (страница {page + 1}/{((total_count - 1) // limit) + 1}):</b>"]
        for emp in employees:
            try:
                decrypted_name = decrypt_data(emp['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            response.append(f"• {decrypted_name} ({emp['position']})")

        # Создание кнопок для каждого сотрудника
        keyboard = []
        for emp in employees:
            try:
                decrypted_name = decrypt_data(emp['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            keyboard.append([
                InlineKeyboardButton(
                    f"{decrypted_name}",
                    callback_data=create_callback_data(
                        "select_employee",
                        id=emp['id']
                    )
                )
            ])

        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=create_callback_data("emp_page", page=page - 1)
            ))
        if (page + 1) * limit < total_count:
            nav_buttons.append(InlineKeyboardButton(
                "Вперед ➡️",
                callback_data=create_callback_data("emp_page", page=page + 1)
            ))

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton(
            "🔙 Главное меню",
            callback_data=create_callback_data("menu")
        )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправка сообщения
        if update.message:
            await update.message.reply_text(
                "\n".join(response),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                "\n".join(response),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        # Сохранение номера страницы
        context.user_data['employee_page'] = page

    except Exception as e:
        logger.error(f"Error in list_employees: {e}")
        error_msg = "❌ Произошла ошибка при получении списка сотрудников"
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(error_msg)


async def my_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает предстоящие события текущего пользователя"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    today = datetime.now().date().isoformat()

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Поиск сотрудника по user_id
            cursor.execute(
                '''SELECT e.id, e.full_name, e.position 
                   FROM employees e 
                   WHERE e.chat_id = ? AND e.user_id = ? AND e.is_active = 1''',
                (chat_id, user_id)
            )
            employee = cursor.fetchone()

            if not employee:
                response = "ℹ️ У вас нет записей в базе сотрудников."
                if update.message:
                    await update.message.reply_text(response)
                else:
                    query = update.callback_query
                    await query.answer()
                    await query.edit_message_text(response)
                return

            # Получение событий сотрудника
            employee_id = employee['id']
            cursor.execute(
                '''SELECT event_type, next_notification_date 
                   FROM employee_events 
                   WHERE employee_id = ? AND next_notification_date >= ?
                   ORDER BY next_notification_date''',
                (employee_id, today)
            )
            events = cursor.fetchall()

            # Формирование ответа
            try:
                decrypted_name = decrypt_data(employee['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"

            response = [
                f"👤 <b>Сотрудник:</b> {decrypted_name}",
                f"💼 <b>Должность:</b> {employee['position']}",
                "",
                "📅 <b>Ваши предстоящие события:</b>"
            ]

            if not events:
                response.append("ℹ️ Нет предстоящих событий")
            else:
                for event in events:
                    event_date = datetime.fromisoformat(event['next_notification_date']).date()
                    days_left = (event_date - datetime.now().date()).days
                    response.append(
                        f"• {event['event_type']} - {event_date.strftime('%d.%m.%Y')} "
                        f"(через {days_left} дней)"
                    )

        # Отправка сообщения
        message = "\n".join(response)
        if update.message:
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in my_events: {e}")
        error_msg = "❌ Произошла ошибка при получении ваших событий"
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(error_msg)


async def all_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает все предстоящие события (только для администратора)"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    today = datetime.now().date().isoformat()

    if not is_admin(chat_id, user_id):
        response = "❌ Только администратор может просматривать все события."
        if update.message:
            await update.message.reply_text(response)
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(response)
        return

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Получение событий
            cursor.execute(
                '''SELECT e.full_name, ee.event_type, ee.next_notification_date
                   FROM employee_events ee
                   JOIN employees e ON ee.employee_id = e.id
                   WHERE e.chat_id = ? AND e.is_active = 1 AND ee.next_notification_date >= ?
                   ORDER BY ee.next_notification_date''',
                (chat_id, today)
            )
            events = cursor.fetchall()

            # Формирование ответа
            response = ["📅 <b>Все предстоящие события:</b>"]
            if not events:
                response.append("ℹ️ Нет предстоящих событий")
            else:
                for event in events:
                    try:
                        decrypted_name = decrypt_data(event['full_name'])
                    except ValueError:
                        decrypted_name = "Ошибка дешифрации"
                    event_date = datetime.fromisoformat(event['next_notification_date']).date()
                    days_left = (event_date - datetime.now().date()).days
                    response.append(
                        f"• {decrypted_name} - {event['event_type']} - "
                        f"{event_date.strftime('%d.%m.%Y')} (через {days_left} дней)"
                    )

        # Отправка сообщения
        message = "\n".join(response)
        if update.message:
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(message, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in all_events: {e}")
        error_msg = "❌ Произошла ошибка при получении списка событий"
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(error_msg)


async def view_employee_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали сотрудника и его события"""
    query = update.callback_query
    await query.answer()
    employee_id = context.user_data.get('selected_employee')

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Получение информации о сотруднике
            cursor.execute(
                "SELECT full_name, position FROM employees WHERE id = ?",
                (employee_id,)
            )
            employee = cursor.fetchone()

            if not employee:
                await query.edit_message_text("❌ Сотрудник не найден")
                return

            # Получение событий сотрудника
            cursor.execute(
                "SELECT event_type, next_notification_date FROM employee_events WHERE employee_id = ?",
                (employee_id,)
            )
            events = cursor.fetchall()

            # Формирование ответа
            try:
                decrypted_name = decrypt_data(employee['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"

            response = [
                f"👤 <b>Сотрудник:</b> {decrypted_name}",
                f"💼 <b>Должность:</b> {employee['position']}",
                "",
                "📅 <b>События:</b>"
            ]

            if not events:
                response.append("ℹ️ Нет событий")
            else:
                for event in events:
                    event_date = datetime.fromisoformat(event['next_notification_date']).date()
                    days_left = (event_date - datetime.now().date()).days
                    response.append(
                        f"• {event['event_type']} - {event_date.strftime('%d.%m.%Y')} "
                        f"(через {days_left} дней)"
                    )

        # Кнопки действий
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать",
                                  callback_data=create_callback_data("edit_employee", id=employee_id))],
            [InlineKeyboardButton("➕ Добавить событие",
                                  callback_data=create_callback_data("add_event", id=employee_id))],
            [InlineKeyboardButton("🔙 Назад", callback_data=create_callback_data("list_employees"))]
        ]

        await query.edit_message_text(
            "\n".join(response),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in view_employee_details: {e}")
        await query.edit_message_text("❌ Произошла ошибка при получении данных сотрудника")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по командам"""
    help_text = (
        "📚 <b>Справка по командам:</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/menu - Показать главное меню\n"
        "/help - Показать эту справку\n"
        "/my_events - Показать ваши события\n\n"
        "👨‍💼 <b>Команды администратора:</b>\n"
        "/add_employee - Добавить сотрудника\n"
        "/list_employees - Список сотрудников\n"
        "/all_events - Все предстоящие события\n"
        "/settings - Настройки чата"
    )

    if update.message:
        await update.message.reply_text(help_text, parse_mode='HTML')
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(help_text, parse_mode='HTML')


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Расширенный обработчик меню с новыми функциями"""
    query = update.callback_query
    await query.answer()
    
    try:
        data = parse_callback_data(query.data)
        action = data.get('action')

        # Существующие действия (ваши старые)
        if action == "my_events":
            await my_events(update, context)
        elif action == "list_employees":
            await list_employees(update, context)
        elif action == "all_events":
            await all_events(update, context)
        elif action == "settings":
            await settings_menu(update, context)
        elif action == "help":
            await help_command(update, context)
        elif action == "menu":
            await show_menu(update, context)
        
        # НОВЫЕ действия Фазы 1 (добавляем)
        elif action == "search_menu":
            await advanced_search_start(update, context)
        elif action == "export_menu":
            await export_data_start(update, context)
        elif action == "templates":
            await templates_menu(update, context)
        elif action == "search_text":
            await quick_search(update, context)
        elif action == "filter_status":
            await filter_by_status(update, context)
        elif action == "filter_apply":
            await apply_status_filter(update, context)
        elif action == "export":
            await handle_export(update, context)
        elif action == "select_template":
            await select_employee_for_template(update, context)
        elif action == "apply_template":
            await apply_template_to_employee(update, context)
        
        # Действия с событиями (новые)
        elif action == "mark_completed":
            await mark_event_completed(update, context)
        elif action == "reschedule":
            await reschedule_event(update, context)
        elif action == "contact_employee":
            await show_employee_contact(update, context)
        
        # Остальные существующие действия (ваши старые - оставляем)
        elif action == "emp_page":
            context.user_data['employee_page'] = data.get('page', 0)
            await list_employees(update, context)
        elif action == "select_employee":
            employee_id = data.get('id')
            context.user_data['selected_employee'] = employee_id
            await view_employee_details(update, context)
        elif action == "set_notif_days":
            await set_notification_days(update, context)
        elif action == "set_timezone":
            await set_timezone(update, context)
        elif action == "set_tz":
            tz = data.get('tz')
            if tz:
                chat_id = update.effective_chat.id
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE chat_settings SET timezone = ? WHERE chat_id = ?",
                        (tz, chat_id)
                    )
                    conn.commit()
                await query.edit_message_text(f"✅ Часовой пояс установлен: {tz}")
        else:
            await query.edit_message_text("❌ Неизвестная команда")
            
    except Exception as e:
        logger.error(f"Error in enhanced_menu_handler: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке команды")


async def enhanced_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Расширенный обработчик меню с новыми функциями"""
    query = update.callback_query
    await query.answer()
    
    try:
        data = parse_callback_data(query.data)
        action = data.get('action')

        # Существующие действия
        if action == "my_events":
            await my_events(update, context)
        elif action == "list_employees":
            await list_employees(update, context)
        elif action == "all_events":
            await all_events(update, context)
        elif action == "settings":
            await settings_menu(update, context)
        elif action == "help":
            await help_command(update, context)
        elif action == "menu":
            await show_menu(update, context)
        
        # Новые действия Фазы 1
        elif action == "search_menu":
            await advanced_search_start(update, context)
        elif action == "export_menu":
            await export_data_start(update, context)
        elif action == "templates":
            await templates_menu(update, context)
        elif action == "search_text":
            await quick_search(update, context)
        elif action == "filter_status":
            await filter_by_status(update, context)
        elif action == "filter_apply":
            await apply_status_filter(update, context)
        elif action == "export":
            await handle_export(update, context)
        elif action == "select_template":
            await select_employee_for_template(update, context)
        elif action == "apply_template":
            await apply_template_to_employee(update, context)
        
        # Действия с событиями
        elif action == "mark_completed":
            await mark_event_completed(update, context)
        elif action == "reschedule":
            await query.edit_message_text("🚧 Функция переноса дат будет добавлена в следующем обновлении")
        elif action == "contact_employee":
            await show_employee_contact(update, context)
        
        # Остальные существующие действия
        elif action == "emp_page":
            context.user_data['employee_page'] = data.get('page', 0)
            await list_employees(update, context)
        elif action == "select_employee":
            employee_id = data.get('id')
            context.user_data['selected_employee'] = employee_id
            await view_employee_details(update, context)
        elif action == "set_notif_days":
            await set_notification_days(update, context)
        elif action == "set_timezone":
            await set_timezone(update, context)
        elif action == "set_tz":
            tz = data.get('tz')
            if tz:
                chat_id = update.effective_chat.id
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE chat_settings SET timezone = ? WHERE chat_id = ?",
                        (tz, chat_id)
                    )
                    conn.commit()
                await query.edit_message_text(f"✅ Часовой пояс установлен: {tz}")
        else:
            await query.edit_message_text("❌ Неизвестная команда")
            
    except Exception as e:
        logger.error(f"Error in enhanced_menu_handler: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке команды")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений для поиска и других функций"""
    # Обработка поиска
    if context.user_data.get('waiting_for_search'):
        await handle_search_query(update, context)
        return
    
    # Обработка ввода дней уведомлений
    if context.user_data.get('waiting_for_notification_days'):
        await save_notification_days(update, context)
        return

# ================================================================
# БЛОК 11: Обработчики диалогов для настроек
# ================================================================
async def notification_days_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик диалога для настройки дней уведомлений"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                set_notification_days,
                pattern=r'"action":"set_notif_days"'
            )
        ],
        states={
            SET_NOTIFICATION_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_notification_days)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_conversation)
        ]
    )
async def advanced_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запуск расширенного поиска"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск по тексту", callback_data=create_callback_data("search_text"))],
        [InlineKeyboardButton("📊 Фильтр по статусу", callback_data=create_callback_data("filter_status"))],
        [InlineKeyboardButton("📅 Фильтр по дате", callback_data=create_callback_data("filter_date"))],
        [InlineKeyboardButton("📝 Фильтр по типу события", callback_data=create_callback_data("filter_type"))],
        [InlineKeyboardButton("🔙 Назад", callback_data=create_callback_data("menu"))]
    ]
    
    await query.edit_message_text(
        "🔍 <b>Расширенный поиск</b>\nВыберите тип поиска:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def export_data_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запуск экспорта данных"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может экспортировать данные")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Excel (XLSX)", callback_data=create_callback_data("export", format="xlsx"))],
        [InlineKeyboardButton("📄 CSV", callback_data=create_callback_data("export", format="csv"))],
        [InlineKeyboardButton("🔙 Назад", callback_data=create_callback_data("menu"))]
    ]
    
    await query.edit_message_text(
        "📁 <b>Экспорт данных</b>\nВыберите формат файла:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка экспорта данных"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    file_format = data.get('format', 'xlsx')
    chat_id = update.effective_chat.id
    
    await query.edit_message_text("⏳ Подготавливаю файл для экспорта...")
    
    try:
        # Экспортируем данные
        file_buffer = await excel_exporter.export_all_events(chat_id, file_format)
        
        # Формируем имя файла
        current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"events_report_{current_date}.{file_format}"
        
        # Отправляем файл
        await context.bot.send_document(
            chat_id=chat_id,
            document=file_buffer,
            filename=filename,
            caption=f"📊 Отчет по событиям от {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await query.edit_message_text("✅ Файл успешно сформирован и отправлен!")
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        await query.edit_message_text("❌ Ошибка при экспорте данных")

async def templates_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню шаблонов событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может использовать шаблоны")
        return
    
    templates = template_manager.get_template_list()
    
    text = "📋 <b>Шаблоны событий</b>\n\nВыберите шаблон для применения:\n\n"
    
    keyboard = []
    for template in templates:
        text += f"• <b>{template['name']}</b>\n  {template['description']}\n\n"
        keyboard.append([InlineKeyboardButton(
            template['name'],
            callback_data=create_callback_data("select_template", key=template['key'])
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=create_callback_data("menu"))])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_employee_for_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выбор сотрудника для применения шаблона"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    template_key = data.get('key')
    
    if not template_key:
        await query.edit_message_text("❌ Ошибка: шаблон не найден")
        return
    
    context.user_data['selected_template'] = template_key
    chat_id = update.effective_chat.id
    
    # Получаем список сотрудников
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, full_name, position 
                FROM employees 
                WHERE chat_id = ? AND is_active = 1
                ORDER BY full_name
                LIMIT 10
            ''', (chat_id,))
            employees = cursor.fetchall()
        
        if not employees:
            await query.edit_message_text("❌ Нет активных сотрудников")
            return
        
        text = f"👤 Выберите сотрудника для применения шаблона <b>\"{template_manager.predefined_templates[template_key].name}\"</b>:\n\n"
        
        keyboard = []
        for emp in employees:
            try:
                decrypted_name = decrypt_data(emp['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            
            keyboard.append([InlineKeyboardButton(
                f"{decrypted_name} ({emp['position']})",
                callback_data=create_callback_data("apply_template", emp_id=emp['id'])
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=create_callback_data("templates"))])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error selecting employee for template: {e}")
        await query.edit_message_text("❌ Ошибка при получении списка сотрудников")

async def apply_template_to_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Применение шаблона к сотруднику"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('emp_id')
    template_key = context.user_data.get('selected_template')
    
    if not employee_id or not template_key:
        await query.edit_message_text("❌ Ошибка: недостаточно данных")
        return
    
    await query.edit_message_text("⏳ Применяю шаблон...")
    
    try:
        success = await template_manager.apply_template(employee_id, template_key)
        
        if success:
            template_name = template_manager.predefined_templates[template_key].name
            events_count = len(template_manager.predefined_templates[template_key].events)
            
            await query.edit_message_text(
                f"✅ Шаблон <b>\"{template_name}\"</b> успешно применен!\n"
                f"Добавлено событий: {events_count}",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ Ошибка при применении шаблона")
            
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        await query.edit_message_text("❌ Произошла ошибка при применении шаблона")

async def quick_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Быстрый поиск по тексту"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 Введите текст для поиска по сотрудникам, должностям или типам событий:"
    )
    
    context.user_data['waiting_for_search'] = True

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка поискового запроса"""
    if not context.user_data.get('waiting_for_search'):
        return
    
    context.user_data['waiting_for_search'] = False
    search_query = update.message.text
    chat_id = update.effective_chat.id
    
    await update.message.reply_text("🔍 Ищу...")
    
    try:
        results = await search_manager.search_events(chat_id, search_query)
        
        if not results:
            await update.message.reply_text("ℹ️ По вашему запросу ничего не найдено")
            return
        
        # Формируем результаты поиска
        text = f"🔍 <b>Результаты поиска по запросу:</b> \"{search_query}\"\n\n"
        
        for i, result in enumerate(results[:10], 1):  # Показываем первые 10 результатов
            days_until = int(result['days_until']) if result['days_until'] else 0
            
            if days_until < 0:
                status_emoji = "🔴"
                status_text = f"просрочено на {abs(days_until)} дней"
            elif days_until <= 7:
                status_emoji = "🟠"
                status_text = f"через {days_until} дней"
            else:
                status_emoji = "🟢"
                status_text = f"через {days_until} дней"
            
            text += (
                f"{i}. <b>{result['full_name']}</b> ({result['position']})\n"
                f"   {result['event_type']} - {status_emoji} {status_text}\n\n"
            )
        
        if len(results) > 10:
            text += f"... и еще {len(results) - 10} результатов"
        
        # Добавляем кнопки для дополнительных действий
        keyboard = [
            [InlineKeyboardButton("📊 Экспорт результатов", callback_data=create_callback_data("export_search"))],
            [InlineKeyboardButton("🔍 Новый поиск", callback_data=create_callback_data("search_text"))],
            [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        # Сохраняем результаты для возможного экспорта
        context.user_data['last_search_results'] = results
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("❌ Ошибка при поиске")

async def filter_by_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Фильтрация по статусу событий"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔴 Просроченные", callback_data=create_callback_data("filter_apply", status="overdue"))],
        [InlineKeyboardButton("🟠 Срочные (до 7 дней)", callback_data=create_callback_data("filter_apply", status="urgent"))],
        [InlineKeyboardButton("🟢 Предстоящие", callback_data=create_callback_data("filter_apply", status="upcoming"))],
        [InlineKeyboardButton("🔙 Назад", callback_data=create_callback_data("search_menu"))]
    ]
    
    await query.edit_message_text(
        "📊 <b>Фильтр по статусу</b>\nВыберите статус событий:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def apply_status_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Применение фильтра по статусу"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    status = data.get('status')
    chat_id = update.effective_chat.id
    
    status_names = {
        'overdue': 'Просроченные',
        'urgent': 'Срочные (до 7 дней)',
        'upcoming': 'Предстоящие'
    }
    
    await query.edit_message_text("🔍 Применяю фильтр...")
    
    try:
        results = await search_manager.search_events(chat_id, "", {'status': status})
        
        if not results:
            await query.edit_message_text(
                f"ℹ️ События со статусом \"{status_names.get(status, status)}\" не найдены"
            )
            return
        
        # Формируем результаты
        text = f"📊 <b>{status_names.get(status, status)} события</b>\n\n"
        
        for i, result in enumerate(results[:15], 1):
            days_until = int(result['days_until']) if result['days_until'] else 0
            event_date = datetime.fromisoformat(result['next_notification_date']).strftime('%d.%m.%Y')
            
            text += (
                f"{i}. <b>{result['full_name']}</b>\n"
                f"   {result['event_type']} - {event_date}\n\n"
            )
        
        if len(results) > 15:
            text += f"... и еще {len(results) - 15} событий"
        
        keyboard = [
            [InlineKeyboardButton("📊 Экспорт", callback_data=create_callback_data("export_filtered"))],
            [InlineKeyboardButton("🔍 Другой фильтр", callback_data=create_callback_data("search_menu"))],
            [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        context.user_data['last_search_results'] = results
        
    except Exception as e:
        logger.error(f"Filter error: {e}")
        await query.edit_message_text("❌ Ошибка при применении фильтра")

async def mark_event_completed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отметка события как выполненного"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    event_id = data.get('event_id')
    
    if not event_id:
        await query.edit_message_text("❌ Ошибка: событие не найдено")
        return
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем данные события
            cursor.execute(
                "SELECT interval_days, event_type FROM employee_events WHERE id = ?",
                (event_id,)
            )
            event = cursor.fetchone()
            
            if not event:
                await query.edit_message_text("❌ Событие не найдено")
                return
            
            # Обновляем событие
            today = datetime.now().date()
            next_date = today + timedelta(days=event['interval_days'])
            
            cursor.execute('''
                UPDATE employee_events 
                SET last_event_date = ?, next_notification_date = ?
                WHERE id = ?
            ''', (today.isoformat(), next_date.isoformat(), event_id))
            
            conn.commit()
        
        await query.edit_message_text(
            f"✅ Событие \"{event['event_type']}\" отмечено как выполненное!\n"
            f"📅 Следующее уведомление: {next_date.strftime('%d.%m.%Y')}"
        )
        
    except Exception as e:
        logger.error(f"Error marking event completed: {e}")
        await query.edit_message_text("❌ Ошибка при обновлении события")

async def show_employee_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает контактную информацию сотрудника"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('emp_id')
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, full_name, position FROM employees WHERE id = ?",
                (employee_id,)
            )
            employee = cursor.fetchone()
        
        if not employee:
            await query.edit_message_text("❌ Сотрудник не найден")
            return
        
        decrypted_name = decrypt_data(employee['full_name'])
        
        text = f"👤 <b>Контакт сотрудника</b>\n\n"
        text += f"<b>ФИО:</b> {decrypted_name}\n"
        text += f"<b>Должность:</b> {employee['position']}\n"
        
        if employee['user_id']:
            text += f"<b>Telegram ID:</b> {employee['user_id']}\n"
            text += f"\n💬 Вы можете написать сотруднику напрямую"
        else:
            text += f"\n📞 Контактная информация недоступна"
        
        await query.edit_message_text(text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error showing employee contact: {e}")
        await query.edit_message_text("❌ Ошибка при получении контактной информации")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений"""
    # Обработка поиска
    if context.user_data.get('waiting_for_search'):
        await handle_search_query(update, context)
        return
    
    # Обработка ввода дней уведомлений
    if context.user_data.get('waiting_for_notification_days'):
        await save_notification_days(update, context)
        return


# Недостающие функции-обработчики
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по боту"""
    help_text = """
🤖 <b>Справка по боту управления периодическими событиями</b>

<b>Основные команды:</b>
/start - Запуск бота
/menu - Главное меню
/help - Справка

<b>Для администраторов:</b>
• Добавление сотрудников
• Управление событиями
• Настройка уведомлений
• Экспорт данных
• Поиск по базе

<b>Функции бота:</b>
✅ Отслеживание периодических событий
📅 Автоматические уведомления
📊 Экспорт в Excel/CSV
🔍 Поиск и фильтры
📋 Готовые шаблоны событий
⚙️ Гибкие настройки

<i>Для получения доступа к административным функциям обратитесь к администратору чата.</i>
    """
    
    if update.message:
        await update.message.reply_text(help_text, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(help_text, parse_mode='HTML')


async def advanced_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запуск расширенного поиска"""
    await update.message.reply_text("🔍 Введите запрос для поиска:")
    context.user_data['waiting_for_search'] = True


async def export_data_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запуск экспорта данных"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await update.message.reply_text("❌ Только администратор может экспортировать данные")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Excel", callback_data=create_callback_data("export", format="xlsx"))],
        [InlineKeyboardButton("📄 CSV", callback_data=create_callback_data("export", format="csv"))]
    ]
    
    await update.message.reply_text(
        "📁 Выберите формат экспорта:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def templates_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню шаблонов событий"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await update.message.reply_text("❌ Только администратор может использовать шаблоны")
        return
    
    templates = template_manager.get_template_list()
    keyboard = []
    
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                f"📋 {template['name']} ({template['events_count']} событий)",
                callback_data=create_callback_data("select_template", key=template['key'])
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))])
    
    await update.message.reply_text(
        "📋 <b>Шаблоны событий:</b>\n\nВыберите шаблон для применения к сотруднику:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка поискового запроса"""
    if not context.user_data.get('waiting_for_search'):
        return
        
    context.user_data['waiting_for_search'] = False
    search_query = update.message.text
    chat_id = update.effective_chat.id
    
    await update.message.reply_text("🔍 Ищу...")
    
    try:
        results = await search_manager.search_events(chat_id, search_query)
        
        if not results:
            await update.message.reply_text("ℹ️ По вашему запросу ничего не найдено")
            return
        
        # Формируем ответ
        text = f"🔍 <b>Результаты поиска по запросу '{search_query}':</b>\n\n"
        
        for i, result in enumerate(results[:10], 1):  # Показываем только первые 10
            event_date = datetime.fromisoformat(result['next_notification_date']).date()
            days_until = int(result['days_until']) if result['days_until'] else 0
            
            if days_until < 0:
                status_emoji = "🔴"
                status_text = f"просрочено на {abs(days_until)} дн."
            elif days_until <= 7:
                status_emoji = "🟠"
                status_text = f"через {days_until} дн."
            else:
                status_emoji = "🟢"
                status_text = f"через {days_until} дн."
            
            text += f"{i}. {status_emoji} <b>{result['full_name']}</b>\n"
            text += f"   📋 {result['event_type']}\n"
            text += f"   📅 {event_date.strftime('%d.%m.%Y')} ({status_text})\n\n"
        
        if len(results) > 10:
            text += f"<i>... и еще {len(results) - 10} результатов</i>\n"
        
        await update.message.reply_text(
            text, 
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
            ])
        )
        
        # Сохраняем результаты для дальнейшего использования
        context.user_data['last_search_results'] = results
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("❌ Ошибка при поиске")


# ================================================================
# БЛОК 12: Главная функция запуска бота
# ================================================================
def main():
    """Точка входа в приложение с исправленными обработчиками"""
    lock_fd = singleton_lock()
    try:
        token = os.getenv('BOT_TOKEN')
        if not token:
            logger.error("Bot token not set. Set BOT_TOKEN environment variable.")
            sys.exit(1)

        application = Application.builder().token(token).build()
        application.add_error_handler(global_error_handler)

        # Регистрация обработчиков команд
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('menu', show_menu))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('cancel', cancel_conversation))

        # Обработчик разговора для добавления сотрудника
        add_employee_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    add_employee_start,
                    pattern=r'.*"action":"add_employee".*'
                )
            ],
            states={
                ADD_NAME: [
                    MessageHandler(filters.CONTACT, handle_contact),
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), add_employee_name),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_employee)

                ],
                ADD_POSITION: [
                    CallbackQueryHandler(handle_position_selection, pattern=r'.*"action":"select_position".*'),
                    CallbackQueryHandler(cancel_add_employee, pattern=r'.*"action":"cancel_add_employee".*')
                ],
                ADD_EVENT_TYPE: [
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), add_event_type),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_employee)
                ],
                ADD_LAST_DATE: [
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), add_last_date),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_employee)
                ],
                ADD_INTERVAL: [
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), add_interval),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_employee)
                ],
            },
            fallbacks=[
                MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_employee),
                CommandHandler('cancel', cancel_conversation)
            ]
        )
        application.add_handler(add_employee_conv)


        # Обработчик разговора для настройки дней уведомлений
        notification_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    set_notification_days,
                    pattern=r'.*"action":"set_notif_days".*'
                )
            ],
            states={
                SET_NOTIFICATION_DAYS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, save_notification_days)
                ]
            },
            fallbacks=[
                CommandHandler('cancel', cancel_conversation)
            ]
        )
        application.add_handler(notification_conv)

        # Обработчик текстовых сообщений для поиска
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^❌ Отмена$'), 
            handle_text_message
        ))
        
        # Команды для быстрого доступа к новым функциям
        application.add_handler(CommandHandler("search", lambda u, c: advanced_search_start(u, c)))
        application.add_handler(CommandHandler("export", lambda u, c: export_data_start(u, c)))
        application.add_handler(CommandHandler("templates", lambda u, c: templates_menu(u, c)))
        
        # Обработчик callback-запросов (должен быть последним)
        application.add_handler(CallbackQueryHandler(menu_handler))



        # Планировщик задач
        job_queue = application.job_queue
        job_queue.run_daily(
            enhanced_send_notifications,
            time=dt_time(hour=9, minute=0, tzinfo=pytz.UTC),
            name="enhanced_notifications"
        )
        
        # Дополнительные уведомления для критичных случаев (каждые 4 часа)
        job_queue.run_repeating(
            enhanced_send_notifications,
            interval=timedelta(hours=4),
            name="critical_notifications"
        )

        # Ежедневные уведомления
        job_queue.run_daily(
            send_notifications,
            time=dt_time(hour=9, minute=0, tzinfo=pytz.UTC),
            name="daily_notifications"
        )

        # Резервное копирование
        job_queue.run_daily(
            lambda ctx: db_manager.create_backup(),
            time=dt_time(hour=3, minute=0, tzinfo=pytz.UTC),
            name="daily_backup"
        )

        # Запуск с улучшенными параметрами
        logger.info("Starting bot...")
        application.run_polling(
            poll_interval=2.0,
            timeout=20,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        # Освобождение блокировки
        if 'lock_fd' in locals() and lock_fd:
            try:
                if platform.system() != 'Windows':
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
                if os.path.exists('bot.lock'):
                    os.remove('bot.lock')
            except Exception as e:
                logger.error(f"Lock release error: {e}")


if __name__ == '__main__':
    main()