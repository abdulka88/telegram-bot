"""
Менеджер базы данных для Telegram бота управления периодическими событиями
"""

import sqlite3
import time
import shutil
import os
import logging
from datetime import datetime
from config.settings import BotConfig

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных с поддержкой retry и резервного копирования"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or BotConfig.DB_PATH
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
                        template_data TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chat_settings(chat_id)
                    )
                ''')

                # Настройки автоматических отчетов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS report_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER UNIQUE NOT NULL,
                        daily_enabled INTEGER DEFAULT 1,
                        weekly_enabled INTEGER DEFAULT 1,
                        monthly_enabled INTEGER DEFAULT 1,
                        daily_time TEXT DEFAULT '09:00',
                        weekly_day INTEGER DEFAULT 1,
                        monthly_day INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chat_settings(chat_id)
                    )
                ''')

                # Создание индексов для оптимизации
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_chat_id ON employees(chat_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_employee_id ON employee_events(employee_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_notification_date ON employee_events(next_notification_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_history_event_id ON notification_history(event_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_custom_templates_chat_id ON custom_templates(chat_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_report_settings_chat_id ON report_settings(chat_id)')
            
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
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
                    logger.error(f"Database connection failed after {max_retries} attempts: {e}")
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
                logger.error(f"Database error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                raise

    def create_backup(self):
        """Создание резервной копии базы данных"""
        try:
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup created: {backup_path}")

            # Очистка старых бэкапов (оставляем только 7 последних)
            backup_pattern = f"{self.db_path}.backup_"
            backups = [f for f in os.listdir('.') if f.startswith(backup_pattern)]
            backups.sort(reverse=True)

            for old_backup in backups[7:]:
                os.remove(old_backup)
                logger.info(f"Removed old backup: {old_backup}")

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")

# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()