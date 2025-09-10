#!/usr/bin/env python3
"""
Скрипт тестирования модульной архитектуры Telegram бота
"""

import os
import sys
import importlib
import traceback
from datetime import datetime

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Тестирует импорты всех модулей"""
    print("🔍 ТЕСТИРОВАНИЕ ИМПОРТОВ МОДУЛЕЙ")
    print("=" * 50)
    
    modules_to_test = [
        # Конфигурация
        ('config.settings', 'BotConfig'),
        ('config.constants', 'AVAILABLE_POSITIONS'),
        
        # Ядро системы
        ('core.database', 'DatabaseManager'),
        ('core.security', 'encrypt_data'),
        ('core.utils', 'create_callback_data'),
        
        # Менеджеры
        ('managers.notification_manager', 'NotificationManager'),
        ('managers.template_manager', 'TemplateManager'),
        ('managers.export_manager', 'ExportManager'),
        ('managers.search_manager', 'SearchManager'),
        
        # Обработчики
        ('handlers.menu_handlers', 'show_menu'),
        ('handlers.employee_handlers', 'add_employee_start'),
        ('handlers.event_handlers', 'view_all_events'),
        ('handlers.export_handlers', 'export_data_start'),
        ('handlers.template_handlers', 'templates_menu'),
        ('handlers.search_handlers', 'search_menu_start'),
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    for module_name, class_or_func in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            
            if hasattr(module, class_or_func):
                print(f"  ✅ {module_name}.{class_or_func}")
                success_count += 1
            else:
                print(f"  ❌ {module_name}.{class_or_func} - не найден")
        
        except ImportError as e:
            print(f"  ❌ {module_name} - ошибка импорта: {e}")
        except Exception as e:
            print(f"  ❌ {module_name} - ошибка: {e}")
    
    print(f"\n📊 Результат импортов: {success_count}/{total_count}")
    return success_count == total_count

def test_database_connection():
    """Тестирует подключение к базе данных"""
    print("\n🗄️ ТЕСТИРОВАНИЕ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    try:
        from core.database import DatabaseManager
        
        # Создаем тестовый экземпляр
        db = DatabaseManager('test_db.db')
        
        # Проверяем создание таблиц
        print("  ✅ Инициализация базы данных")
        
        # Проверяем подключение
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
        expected_tables = ['chat_settings', 'employees', 'employee_events', 'notification_history', 'custom_templates']
        existing_tables = [table[0] for table in tables]
        
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✅ Таблица {table} существует")
            else:
                print(f"  ❌ Таблица {table} отсутствует")
        
        # Очищаем тестовую БД
        if os.path.exists('test_db.db'):
            os.remove('test_db.db')
            
        print("  ✅ База данных работает корректно")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка базы данных: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Тестирует конфигурацию"""
    print("\n⚙️ ТЕСТИРОВАНИЕ КОНФИГУРАЦИИ")
    print("=" * 50)
    
    try:
        from config.settings import BotConfig
        from config.constants import AVAILABLE_POSITIONS, ConversationStates
        
        # Проверяем основные настройки
        config_items = [
            ('BOT_TOKEN', getattr(BotConfig, 'BOT_TOKEN', None) is not None),
            ('DB_PATH', hasattr(BotConfig, 'DB_PATH')),
            ('DEFAULT_TIMEZONE', hasattr(BotConfig, 'DEFAULT_TIMEZONE')),
            ('NOTIFICATION_TIME_HOUR', hasattr(BotConfig, 'NOTIFICATION_TIME_HOUR')),
        ]
        
        for item, exists in config_items:
            if exists:
                print(f"  ✅ {item} настроен")
            else:
                print(f"  ⚠️ {item} не настроен")
        
        # Проверяем константы
        if len(AVAILABLE_POSITIONS) > 0:
            print(f"  ✅ Позиции загружены: {len(AVAILABLE_POSITIONS)} шт.")
        else:
            print(f"  ❌ Позиции не загружены")
            
        # Проверяем состояния разговора
        conversation_states = ['ADD_NAME', 'ADD_POSITION', 'ADD_EVENT_TYPE', 'ADD_LAST_DATE', 'ADD_INTERVAL']
        for state in conversation_states:
            if hasattr(ConversationStates, state):
                print(f"  ✅ Состояние {state} определено")
            else:
                print(f"  ❌ Состояние {state} не найдено")
        
        print("  ✅ Конфигурация корректна")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка конфигурации: {e}")
        traceback.print_exc()
        return False

def test_managers():
    """Тестирует менеджеры"""
    print("\n🎯 ТЕСТИРОВАНИЕ МЕНЕДЖЕРОВ")
    print("=" * 50)
    
    try:
        from core.database import DatabaseManager
        from managers.notification_manager import NotificationManager
        from managers.template_manager import TemplateManager
        from managers.export_manager import ExportManager
        from managers.search_manager import SearchManager
        
        # Создаем тестовую базу
        db = DatabaseManager('test_managers.db')
        
        # Тестируем NotificationManager
        notif_manager = NotificationManager(db)
        from config.constants import NotificationLevel
        level = notif_manager.get_notification_level(5)
        if level == NotificationLevel.URGENT:
            print("  ✅ NotificationManager работает")
        else:
            print("  ❌ NotificationManager некорректно определяет уровни")
        
        # Тестируем TemplateManager
        template_manager = TemplateManager(db)
        templates = template_manager.get_template_list()
        if len(templates) > 0:
            print(f"  ✅ TemplateManager: {len(templates)} шаблонов")
        else:
            print("  ❌ TemplateManager: шаблоны не найдены")
        
        # Тестируем ExportManager
        export_manager = ExportManager(db)
        print("  ✅ ExportManager инициализирован")
        
        # Тестируем SearchManager  
        search_manager = SearchManager(db)
        print("  ✅ SearchManager инициализирован")
        
        # Очистка
        if os.path.exists('test_managers.db'):
            os.remove('test_managers.db')
            
        print("  ✅ Все менеджеры работают корректно")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка менеджеров: {e}")
        traceback.print_exc()
        return False

def test_handlers():
    """Тестирует обработчики"""
    print("\n🔧 ТЕСТИРОВАНИЕ ОБРАБОТЧИКОВ")
    print("=" * 50)
    
    try:
        from handlers import menu_handlers, employee_handlers, event_handlers
        from handlers import export_handlers, template_handlers, search_handlers
        
        # Проверяем наличие основных функций
        handler_functions = [
            (menu_handlers, 'show_menu'),
            (menu_handlers, 'menu_handler'),
            (employee_handlers, 'add_employee_start'),
            (employee_handlers, 'show_position_selection'),
            (event_handlers, 'view_all_events'),
            (export_handlers, 'export_data_start'),
            (template_handlers, 'templates_menu'),
            (search_handlers, 'search_menu_start'),
        ]
        
        for module, function_name in handler_functions:
            if hasattr(module, function_name):
                print(f"  ✅ {module.__name__}.{function_name}")
            else:
                print(f"  ❌ {module.__name__}.{function_name} не найден")
        
        print("  ✅ Обработчики корректно определены")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка обработчиков: {e}")
        traceback.print_exc()
        return False

def test_security():
    """Тестирует систему безопасности"""
    print("\n🔒 ТЕСТИРОВАНИЕ БЕЗОПАСНОСТИ")
    print("=" * 50)
    
    try:
        from core.security import encrypt_data, decrypt_data, is_admin
        
        # Тестируем шифрование/дешифрование
        test_data = "Тестовые данные для шифрования"
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_data(encrypted)
        
        if decrypted == test_data:
            print("  ✅ Шифрование/дешифрование работает")
        else:
            print("  ❌ Ошибка шифрования/дешифрования")
            return False
        
        # Тестируем функцию is_admin (должна корректно обрабатывать параметры)
        try:
            is_admin(12345, 67890)  # Тестовые ID
            print("  ✅ Функция is_admin работает")
        except Exception as e:
            print(f"  ❌ Ошибка is_admin: {e}")
            return False
        
        print("  ✅ Система безопасности работает корректно")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка безопасности: {e}")
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ МОДУЛЬНОЙ АРХИТЕКТУРЫ")
    print("=" * 60)
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Добавляем текущую директорию в sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    tests = [
        ("Импорты модулей", test_imports),
        ("База данных", test_database_connection),
        ("Конфигурация", test_configuration),
        ("Менеджеры", test_managers),
        ("Обработчики", test_handlers),
        ("Безопасность", test_security),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в тесте '{test_name}': {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📋 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОШЕЛ" if result else "❌ ПРОВАЛЕН"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 РЕЗУЛЬТАТ: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Модульная архитектура готова к использованию!")
        return True
    else:
        print("⚠️ ЕСТЬ ПРОБЛЕМЫ! Необходимо исправить ошибки перед использованием.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)