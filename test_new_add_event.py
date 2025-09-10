#!/usr/bin/env python3
"""
Практический тест новой функции добавления событий к существующим сотрудникам
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, AsyncMock
from handlers.menu_handlers import menu_handler
from handlers.employee_handlers import (
    add_event_to_employee, add_event_to_employee_type, 
    add_event_to_employee_date, add_event_to_employee_interval
)
from core.database import db_manager
from core.security import encrypt_data, decrypt_data

class TelegramSimulator:
    """Симулятор для тестирования новой функции"""
    
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
    
    def create_message_update(self, text):
        """Создает update для текстового сообщения"""
        update = Mock()
        update.message = Mock()
        update.message.text = text
        update.message.reply_text = AsyncMock()
        
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
        context.bot.send_message = AsyncMock()
        return context

async def test_new_add_event_function():
    """Тест полного цикла добавления события к существующему сотруднику"""
    print("\n🆕 ТЕСТ: Новая функция добавления событий")
    print("=" * 50)
    
    # Создаем тестового сотрудника
    encrypted_name = encrypt_data("Тестовый Работник")
    employee_id = db_manager.execute_with_retry('''
        INSERT INTO employees (chat_id, full_name, position, is_active)
        VALUES (?, ?, ?, 1)
    ''', (123456789, encrypted_name, "Маляр"))
    
    print(f"✅ Создан тестовый сотрудник ID: {employee_id}")
    
    sim = TelegramSimulator()
    
    # Шаг 1: Начинаем добавление события
    print("\n📋 Шаг 1: Начало добавления события")
    try:
        update1 = sim.create_callback_update(f'{{"action":"add_event","id":{employee_id}}}')
        context1 = sim.create_context()
        
        result1 = await add_event_to_employee(update1, context1)
        print(f"✅ Функция запустилась, возвращен код состояния: {result1}")
        
        # Проверяем, что данные сохранились в контексте
        if context1.user_data.get('current_employee_id') == employee_id:
            print("✅ ID сотрудника сохранен в контексте")
        else:
            print("❌ ID сотрудника НЕ сохранен")
            
        if update1.callback_query.edit_message_text.called:
            print("✅ Показано сообщение с запросом названия события")
        else:
            print("❌ Сообщение НЕ показано")
            
    except Exception as e:
        print(f"❌ ОШИБКА на шаге 1: {e}")
        return False
    
    # Шаг 2: Вводим название события
    print("\n📝 Шаг 2: Ввод названия события")
    try:
        update2 = sim.create_message_update("Медосмотр")
        context2 = sim.create_context()
        context2.user_data = context1.user_data.copy()  # Копируем состояние
        
        result2 = await add_event_to_employee_type(update2, context2)
        print(f"✅ Название события обработано, код состояния: {result2}")
        
        if context2.user_data.get('new_event_type') == "Медосмотр":
            print("✅ Название события сохранено")
        else:
            print("❌ Название события НЕ сохранено")
            
        if update2.message.reply_text.called:
            print("✅ Показан запрос даты события")
        else:
            print("❌ Запрос даты НЕ показан")
            
    except Exception as e:
        print(f"❌ ОШИБКА на шаге 2: {e}")
        return False
    
    # Шаг 3: Вводим дату события
    print("\n📅 Шаг 3: Ввод даты последнего события")
    try:
        update3 = sim.create_message_update("15.01.2024")
        context3 = sim.create_context()
        context3.user_data = context2.user_data.copy()  # Копируем состояние
        
        result3 = await add_event_to_employee_date(update3, context3)
        print(f"✅ Дата события обработана, код состояния: {result3}")
        
        if context3.user_data.get('new_event_last_date'):
            print("✅ Дата события сохранена")
        else:
            print("❌ Дата события НЕ сохранена")
            
        if update3.message.reply_text.called:
            print("✅ Показан запрос интервала")
        else:
            print("❌ Запрос интервала НЕ показан")
            
    except Exception as e:
        print(f"❌ ОШИБКА на шаге 3: {e}")
        return False
    
    # Шаг 4: Вводим интервал и сохраняем событие
    print("\n🔄 Шаг 4: Ввод интервала и сохранение")
    try:
        update4 = sim.create_message_update("365")
        context4 = sim.create_context()
        context4.user_data = context3.user_data.copy()  # Копируем состояние
        
        result4 = await add_event_to_employee_interval(update4, context4)
        print(f"✅ Интервал обработан, код состояния: {result4}")
        
        # Проверяем, что событие добавилось в базу
        event = db_manager.execute_with_retry('''
            SELECT * FROM employee_events WHERE employee_id = ? AND event_type = ?
        ''', (employee_id, "Медосмотр"), fetch="one")
        
        if event:
            print("✅ Событие успешно добавлено в базу данных!")
            print(f"   📋 Тип: {event['event_type']}")
            print(f"   📅 Дата: {event['last_event_date']}")
            print(f"   🔄 Интервал: {event['interval_days']} дней")
            print(f"   🔔 Следующее уведомление: {event['next_notification_date']}")
        else:
            print("❌ Событие НЕ добавилось в базу")
            return False
            
        if update4.message.reply_text.called:
            print("✅ Показано подтверждение успешного добавления")
        else:
            print("❌ Подтверждение НЕ показано")
            
    except Exception as e:
        print(f"❌ ОШИБКА на шаге 4: {e}")
        return False
    
    # Очистка
    db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (employee_id,))
    db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (employee_id,))
    print("🧹 Тестовые данные удалены")
    
    return True

async def test_route_through_menu_handler():
    """Тест маршрутизации через menu_handler"""
    print("\n🔄 ТЕСТ: Маршрутизация через menu_handler")
    print("=" * 50)
    
    # Создаем тестового сотрудника
    encrypted_name = encrypt_data("Сотрудник для маршрутизации")
    employee_id = db_manager.execute_with_retry('''
        INSERT INTO employees (chat_id, full_name, position, is_active)
        VALUES (?, ?, ?, 1)
    ''', (123456789, encrypted_name, "Плотник"))
    
    print(f"✅ Создан тестовый сотрудник ID: {employee_id}")
    
    sim = TelegramSimulator()
    
    try:
        # Тестируем маршрутизацию через menu_handler
        update = sim.create_callback_update(f'{{"action":"add_event","id":{employee_id}}}')
        context = sim.create_context()
        
        await menu_handler(update, context)
        print("✅ Callback 'add_event' успешно маршрутизируется через menu_handler")
        
        # Проверяем, что функция вызвалась
        if context.user_data.get('current_employee_id') == employee_id:
            print("✅ Функция add_event_to_employee была вызвана успешно")
        else:
            print("❌ Функция add_event_to_employee НЕ была вызвана")
            
    except Exception as e:
        print(f"❌ ОШИБКА маршрутизации: {e}")
        return False
    
    # Очистка
    db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (employee_id,))
    db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (employee_id,))
    print("🧹 Тестовые данные удалены")
    
    return True

async def main():
    """Главная функция тестирования"""
    print("🆕 ТЕСТИРОВАНИЕ НОВОЙ ФУНКЦИИ ДОБАВЛЕНИЯ СОБЫТИЙ")
    print("=" * 80)
    
    tests = [
        ("Полный цикл добавления события", test_new_add_event_function),
        ("Маршрутизация через menu_handler", test_route_through_menu_handler)
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
    
    print("\n" + "=" * 80)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ НОВОЙ ФУНКЦИИ: {passed} ✅ / {failed} ❌")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("🚀 Новая функция добавления событий работает корректно!")
        print("✨ Теперь пользователи смогут добавлять события к существующим сотрудникам!")
    else:
        print("\n⚠️ Обнаружены проблемы в новой функции")
    
    return failed == 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)