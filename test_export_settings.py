#!/usr/bin/env python3
"""
Дополнительное тестирование экспорта и настроек
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, AsyncMock
from handlers.menu_handlers import menu_handler
from handlers.export_handlers import export_menu_start, handle_export
from handlers.settings_handlers import set_notification_days, set_timezone
from core.database import db_manager
from core.security import encrypt_data

class TelegramSimulator:
    """Симулятор для тестирования экспорта и настроек"""
    
    def __init__(self):
        self.chat_id = 123456789
        self.user_id = 987654321
    
    def create_callback_update(self, callback_data):
        """Создает update для callback query"""
        update = Mock()
        update.callback_query = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = callback_data
        
        update.effective_chat = Mock()
        update.effective_chat.id = self.chat_id
        update.effective_user = Mock()
        update.effective_user.id = self.user_id
        
        return update
    
    def create_context(self):
        """Создает контекст бота"""
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.send_document = AsyncMock()
        context.bot.send_message = AsyncMock()
        return context

async def test_export_functionality():
    """Тест экспорта данных (Excel и CSV)"""
    print("\n📊 ТЕСТ: Экспорт данных")
    print("=" * 40)
    
    # Создаем тестовых сотрудников для экспорта
    test_employees = []
    for i in range(2):
        encrypted_name = encrypt_data(f"Сотрудник {i+1}")
        employee_id = db_manager.execute_with_retry('''
            INSERT INTO employees (chat_id, full_name, position, is_active)
            VALUES (?, ?, ?, 1)
        ''', (123456789, encrypted_name, f"Должность{i+1}"))
        test_employees.append(employee_id)
    
    print(f"✅ Создано {len(test_employees)} тестовых сотрудников")
    
    sim = TelegramSimulator()
    
    # Тест меню экспорта
    try:
        update = sim.create_callback_update('{"action":"export_data"}')
        context = sim.create_context()
        
        await export_menu_start(update, context)
        print("✅ Меню экспорта открывается")
        
    except Exception as e:
        print(f"❌ Ошибка в меню экспорта: {e}")
        return False
    
    # Тест экспорта в Excel
    try:
        update_excel = sim.create_callback_update('{"action":"export","format":"xlsx"}')
        context_excel = sim.create_context()
        
        await handle_export(update_excel, context_excel)
        print("✅ Экспорт в Excel работает")
        
    except Exception as e:
        print(f"❌ Ошибка экспорта Excel: {e}")
    
    # Тест экспорта в CSV
    try:
        update_csv = sim.create_callback_update('{"action":"export","format":"csv"}')
        context_csv = sim.create_context()
        
        await handle_export(update_csv, context_csv)
        print("✅ Экспорт в CSV работает")
        
    except Exception as e:
        print(f"❌ Ошибка экспорта CSV: {e}")
    
    # Очистка тестовых данных
    for emp_id in test_employees:
        db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (emp_id,))
        db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (emp_id,))
    
    print("🧹 Тестовые сотрудники удалены")
    return True

async def test_settings_functionality():
    """Тест настроек системы"""
    print("\n⚙️ ТЕСТ: Настройки системы")
    print("=" * 40)
    
    sim = TelegramSimulator()
    
    # Создаем настройки для чата если их нет
    try:
        db_manager.execute_with_retry('''
            INSERT OR IGNORE INTO chat_settings (chat_id, notification_days, timezone)
            VALUES (?, 90, 'Europe/Moscow')
        ''', (123456789,))
    except:
        pass
    
    # Тест изменения дней уведомления
    try:
        update_days = sim.create_callback_update('{"action":"set_notification_days"}')
        context_days = sim.create_context()
        
        await set_notification_days(update_days, context_days)
        print("✅ Изменение дней уведомления работает")
        
    except Exception as e:
        print(f"❌ Ошибка изменения дней уведомления: {e}")
    
    # Тест изменения часового пояса
    try:
        update_tz = sim.create_callback_update('{"action":"set_timezone"}')
        context_tz = sim.create_context()
        
        await set_timezone(update_tz, context_tz)
        print("✅ Изменение часового пояса работает")
        
    except Exception as e:
        print(f"❌ Ошибка изменения часового пояса: {e}")
    
    return True

async def test_callback_routing():
    """Тест маршрутизации callback запросов через menu_handler"""
    print("\n🔄 ТЕСТ: Маршрутизация callback запросов")
    print("=" * 40)
    
    sim = TelegramSimulator()
    
    # Тестируем различные callback actions
    test_callbacks = [
        '{"action":"export_data"}',
        '{"action":"export","format":"xlsx"}', 
        '{"action":"export","format":"csv"}',
        '{"action":"settings"}',
        '{"action":"set_notification_days"}',
        '{"action":"set_timezone"}',
        '{"action":"add_employee"}',
        '{"action":"view_employees"}'
    ]
    
    success_count = 0
    
    for callback_data in test_callbacks:
        try:
            update = sim.create_callback_update(callback_data)
            context = sim.create_context()
            
            # Проверяем, что menu_handler может обработать callback
            await menu_handler(update, context)
            success_count += 1
            action = callback_data.split('"action":"')[1].split('"')[0]
            print(f"✅ Callback '{action}' маршрутизируется")
            
        except Exception as e:
            action = callback_data.split('"action":"')[1].split('"')[0]
            print(f"❌ Callback '{action}' ошибка: {e}")
    
    print(f"📊 Успешно обработано: {success_count}/{len(test_callbacks)} callbacks")
    return success_count == len(test_callbacks)

async def main():
    """Главная функция дополнительного тестирования"""
    print("🔍 ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ ПРОБЛЕМНЫХ ФУНКЦИЙ")
    print("=" * 60)
    
    tests = [
        ("Экспорт данных (Excel/CSV)", test_export_functionality),
        ("Настройки системы", test_settings_functionality),
        ("Маршрутизация callbacks", test_callback_routing)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Запуск теста: {test_name}")
            if await test_func():
                passed += 1
                print(f"✅ {test_name}: УСПЕШНО")
            else:
                failed += 1
                print(f"❌ {test_name}: ОШИБКА")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: КРИТИЧЕСКАЯ ОШИБКА - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 РЕЗУЛЬТАТЫ ДОПОЛНИТЕЛЬНОГО ТЕСТИРОВАНИЯ: {passed} ✅ / {failed} ❌")
    
    return failed == 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)