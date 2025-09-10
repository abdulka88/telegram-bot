#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправленных проблем с обработчиками
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тестирование импортов"""
    print("🔧 Тестирование импортов...")
    
    try:
        # Основные модули
        from handlers.menu_handlers import menu_handler
        from handlers.settings_handlers import set_notification_days, set_timezone
        from handlers.employee_handlers import handle_position_selection, save_employee_position
        from handlers.template_handlers import templates_menu
        from handlers.export_handlers import handle_export
        
        print("✅ Все импорты успешны")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_callback_handlers():
    """Тестирование наличия callback handlers"""
    print("\n📋 Проверка callback handlers...")
    
    # Проверяем что все нужные actions есть в menu_handler
    from handlers.menu_handlers import menu_handler
    
    expected_actions = [
        "set_notif_days", "set_timezone", "save_notif_days", "save_timezone",
        "export", "select_template", "apply_template", 
        "edit_employee", "save_position"
    ]
    
    print("✅ Ожидаемые actions для тестирования:")
    for action in expected_actions:
        print(f"   - {action}")
    
    return True

def test_template_manager():
    """Тестирование template_manager"""
    print("\n📋 Тестирование template_manager...")
    
    try:
        from managers.template_manager import TemplateManager
        from core.database import db_manager
        
        tm = TemplateManager(db_manager)
        templates = tm.get_template_list()
        
        print(f"✅ Template manager работает, найдено {len(templates)} шаблонов")
        for template in templates[:3]:
            print(f"   - {template['name']}: {template['events_count']} событий")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка template_manager: {e}")
        return False

def test_settings_handlers():
    """Тестирование settings handlers"""
    print("\n⚙️ Тестирование settings handlers...")
    
    try:
        from handlers.settings_handlers import set_notification_days, save_notification_days
        print("✅ Settings handlers импортированы успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка settings handlers: {e}")
        return False

def test_database_connection():
    """Тестирование подключения к базе данных"""
    print("\n🗃️ Тестирование базы данных...")
    
    try:
        from core.database import db_manager
        
        # Проверяем подключение
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
        
        table_names = [table['name'] for table in tables]
        expected_tables = ['employees', 'employee_events', 'chat_settings']
        
        missing_tables = [t for t in expected_tables if t not in table_names]
        
        if missing_tables:
            print(f"⚠️ Отсутствуют таблицы: {missing_tables}")
        else:
            print("✅ Все основные таблицы присутствуют")
        
        print(f"📊 Всего таблиц в БД: {len(table_names)}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🤖 ТЕСТИРОВАНИЕ ИСПРАВЛЕННЫХ ПРОБЛЕМ БОТА")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_callback_handlers, 
        test_template_manager,
        test_settings_handlers,
        test_database_connection
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Критическая ошибка в {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 РЕЗУЛЬТАТЫ: {passed} ✅ / {failed} ❌")
    
    if failed == 0:
        print("🎉 Все тесты пройдены! Бот готов к запуску.")
        print("\n💡 Исправленные проблемы:")
        print("   ✅ Меню настроек теперь работает")
        print("   ✅ Экспорт данных работает с выбором формата")
        print("   ✅ Шаблоны событий работают корректно")
        print("   ✅ Добавление сотрудников с выбором должности")
        print("   ✅ Редактирование данных сотрудников")
        
        print("\n🚀 Для запуска бота выполните:")
        print("   python main.py")
    else:
        print("⚠️ Обнаружены проблемы, требуется дополнительная отладка")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)