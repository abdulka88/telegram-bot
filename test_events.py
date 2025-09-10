#!/usr/bin/env python3
"""
Тестирование добавления и управления событиями сотрудников
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, AsyncMock
from handlers.menu_handlers import menu_handler
from handlers.event_handlers import add_event_start, add_event_name, add_event_date, save_event
from core.database import db_manager
from core.security import encrypt_data

class TelegramSimulator:
    """Симулятор для тестирования событий"""
    
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

async def test_add_event_to_employee():
    """Тест добавления события к существующему сотруднику"""
    print("\n📅 ТЕСТ: Добавление события к сотруднику")
    print("=" * 40)
    
    # Создаем тестового сотрудника
    encrypted_name = encrypt_data("Сотрудник для События")
    employee_id = db_manager.execute_with_retry('''
        INSERT INTO employees (chat_id, full_name, position, is_active)
        VALUES (?, ?, ?, 1)
    ''', (123456789, encrypted_name, "Плотник"))
    
    print(f"✅ Создан тестовый сотрудник ID: {employee_id}")
    
    sim = TelegramSimulator()
    
    # Шаг 1: Начинаем добавление события
    try:
        update1 = sim.create_callback_update(f'{{"action":"add_event","id":{employee_id}}}')
        context1 = sim.create_context()
        
        result1 = await add_event_start(update1, context1)
        print(f"✅ Начало добавления события: состояние {result1}")
        
        # Проверяем, что employee_id сохранился
        if 'current_employee_id' in context1.user_data:
            print("✅ ID сотрудника сохранен для добавления события")
        else:
            print("❌ ID сотрудника не сохранен")
            
    except Exception as e:
        print(f"❌ Ошибка при начале добавления события: {e}")
        return False
    
    # Шаг 2: Вводим название события
    try:
        update2 = sim.create_message_update("Тестовое событие")
        context2 = sim.create_context()
        context2.user_data = context1.user_data  # Сохраняем состояние
        
        result2 = await add_event_name(update2, context2)
        print(f"✅ Ввод названия события: состояние {result2}")
        
    except Exception as e:
        print(f"❌ Ошибка при вводе названия: {e}")
        return False
    
    # Шаг 3: Вводим дату события
    try:
        update3 = sim.create_message_update("01.01.2024")
        context3 = sim.create_context()
        context3.user_data = context2.user_data  # Сохраняем состояние
        
        result3 = await add_event_date(update3, context3)
        print(f"✅ Ввод даты события: состояние {result3}")
        
    except Exception as e:
        print(f"❌ Ошибка при вводе даты: {e}")
        return False
    
    # Шаг 4: Сохраняем событие
    try:
        update4 = sim.create_callback_update('{"action":"save_event","interval":"365"}')
        context4 = sim.create_context()
        context4.user_data = context3.user_data  # Сохраняем состояние
        
        result4 = await save_event(update4, context4)
        print(f"✅ Сохранение события: состояние {result4}")
        
        # Проверяем, что событие добавилось в базу
        event = db_manager.execute_with_retry('''
            SELECT * FROM employee_events WHERE employee_id = ?
        ''', (employee_id,), fetch="one")
        
        if event:
            print("✅ Событие успешно добавлено в базу данных")
        else:
            print("❌ Событие не добавилось в базу")
            
    except Exception as e:
        print(f"❌ Ошибка при сохранении события: {e}")
        return False
    
    # Очистка
    db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (employee_id,))
    db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (employee_id,))
    print("🧹 Тестовые данные удалены")
    
    return True

async def test_view_employee_with_events():
    """Тест просмотра сотрудника с событиями"""
    print("\n👀 ТЕСТ: Просмотр сотрудника с событиями")
    print("=" * 40)
    
    # Создаем тестового сотрудника с событием
    encrypted_name = encrypt_data("Сотрудник с События")
    employee_id = db_manager.execute_with_retry('''
        INSERT INTO employees (chat_id, full_name, position, is_active)
        VALUES (?, ?, ?, 1)
    ''', (123456789, encrypted_name, "Маляр"))
    
    # Добавляем событие
    db_manager.execute_with_retry('''
        INSERT INTO employee_events (employee_id, event_type, last_event_date, interval_days, next_notification_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (employee_id, "Тестовое событие", "2024-01-01", 365, "2024-12-31"))
    
    print(f"✅ Создан сотрудник ID: {employee_id} с событием")
    
    sim = TelegramSimulator()
    
    # Тест кнопки "Добавить событие" в карточке сотрудника
    try:
        update = sim.create_callback_update(f'{{"action":"add_event","id":{employee_id}}}')
        context = sim.create_context()
        
        await menu_handler(update, context)
        print("✅ Кнопка 'Добавить событие' работает через menu_handler")
        
    except Exception as e:
        print(f"❌ Ошибка кнопки добавления события: {e}")
    
    # Очистка
    db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (employee_id,))
    db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (employee_id,))
    print("🧹 Тестовые данные удалены")
    
    return True

async def main():
    """Главная функция тестирования событий"""
    print("📅 ТЕСТИРОВАНИЕ УПРАВЛЕНИЯ СОБЫТИЯМИ")
    print("=" * 60)
    
    tests = [
        ("Добавление события к сотруднику", test_add_event_to_employee),
        ("Просмотр сотрудника с событиями", test_view_employee_with_events)
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
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ СОБЫТИЙ: {passed} ✅ / {failed} ❌")
    
    return failed == 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)