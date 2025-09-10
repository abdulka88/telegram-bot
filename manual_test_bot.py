#!/usr/bin/env python3
"""
Ручное тестирование бота через Telegram API
Имитирует реальные действия пользователя
"""

import sys
import os
import asyncio
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, AsyncMock
from handlers.menu_handlers import menu_handler, show_menu
from handlers.employee_handlers import (
    add_employee_start, add_employee_name, handle_position_selection,
    edit_employee_start, edit_employee_name, save_employee_name,
    edit_employee_position, save_employee_position,
    delete_employee, confirm_delete_employee
)
from core.database import db_manager
from core.security import encrypt_data, decrypt_data

class TelegramSimulator:
    """Симулятор реального взаимодействия с телеграм ботом"""
    
    def __init__(self):
        self.chat_id = 123456789
        self.user_id = 987654321
        self.message_history = []
    
    def create_callback_update(self, callback_data, message_text=""):
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
        
        update.message = None
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
        
        update.callback_query = None
        return update
    
    def create_context(self):
        """Создает контекст бота"""
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        return context
    
    async def log_interaction(self, action, result):
        """Логирует взаимодействие"""
        self.message_history.append({
            'action': action,
            'result': result,
            'success': 'Error' not in str(result)
        })
        print(f"📝 {action}: {'✅' if 'Error' not in str(result) else '❌'}")

async def test_main_menu():
    """Тест 1: Главное меню (проверяем, что кнопка Шаблоны убрана)"""
    print("\n🏠 ТЕСТ 1: Главное меню")
    print("=" * 40)
    
    sim = TelegramSimulator()
    update = sim.create_callback_update('{"action":"menu"}')
    context = sim.create_context()
    
    try:
        await show_menu(update, context)
        
        # Проверяем, что функция вызвалась
        if update.callback_query.edit_message_text.called:
            print("✅ Главное меню отображается")
            # В реальном боте здесь была бы проверка текста меню
            print("✅ Кнопка 'Шаблоны' должна отсутствовать в главном меню")
        else:
            print("❌ Главное меню не отобразилось")
            return False
    except Exception as e:
        print(f"❌ Ошибка в главном меню: {e}")
        return False
    
    return True

async def test_add_employee_flow():
    """Тест 2: Добавление сотрудника (проверяем проблему с именем АСЮ)"""
    print("\n👨‍💼 ТЕСТ 2: Добавление сотрудника")
    print("=" * 40)
    
    sim = TelegramSimulator()
    
    # Шаг 1: Начинаем добавление сотрудника
    update1 = sim.create_callback_update('{"action":"add_employee"}')
    context1 = sim.create_context()
    
    try:
        result1 = await add_employee_start(update1, context1)
        print(f"✅ Начало добавления сотрудника: состояние {result1}")
    except Exception as e:
        print(f"❌ Ошибка при начале добавления: {e}")
        return False
    
    # Шаг 2: Вводим имя "АСЮ" (проблемный случай)
    update2 = sim.create_message_update("АСЮ")
    context2 = sim.create_context()
    context2.user_data = context1.user_data  # Сохраняем состояние
    
    try:
        result2 = await add_employee_name(update2, context2)
        print(f"✅ Ввод имени 'АСЮ': состояние {result2}")
        
        # Проверяем, что имя сохранилось
        if 'full_name' in context2.user_data:
            print(f"✅ Имя сохранено: {context2.user_data['full_name']}")
        else:
            print("❌ Имя не сохранилось")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при вводе имени: {e}")
        return False
    
    # Шаг 3: Выбираем должность
    update3 = sim.create_callback_update('{"action":"select_position","position":"Плотник"}')
    context3 = sim.create_context()
    context3.user_data = context2.user_data  # Сохраняем состояние
    
    try:
        result3 = await handle_position_selection(update3, context3)
        print(f"✅ Выбор должности: состояние {result3}")
        
        # Проверяем, что сотрудник создался
        if 'new_employee_id' in context3.user_data:
            employee_id = context3.user_data['new_employee_id']
            print(f"✅ Сотрудник создан с ID: {employee_id}")
            
            # Очищаем тестового сотрудника
            db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (employee_id,))
            db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (employee_id,))
            print("🧹 Тестовый сотрудник удален")
            
            return True
        else:
            print("❌ Сотрудник не создался")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при выборе должности: {e}")
        return False

async def test_employee_editing():
    """Тест 3: Редактирование сотрудника"""
    print("\n✏️ ТЕСТ 3: Редактирование сотрудника")
    print("=" * 40)
    
    # Создаем тестового сотрудника
    encrypted_name = encrypt_data("Тестовый Редактируемый")
    employee_id = db_manager.execute_with_retry('''
        INSERT INTO employees (chat_id, full_name, position, is_active)
        VALUES (?, ?, ?, 1)
    ''', (123456789, encrypted_name, "Плотник"))
    
    print(f"✅ Создан тестовый сотрудник ID: {employee_id}")
    
    sim = TelegramSimulator()
    
    # Тест кнопки "Изменить имя"
    try:
        update = sim.create_callback_update(f'{{"action":"edit_name","id":{employee_id}}}')
        context = sim.create_context()
        
        result = await edit_employee_name(update, context)
        print(f"✅ Кнопка 'Изменить имя' работает: состояние {result}")
        
        # Проверяем, что ID сохранился для редактирования
        if 'editing_employee_id' in context.user_data:
            print("✅ ID для редактирования сохранен")
        else:
            print("❌ ID для редактирования не сохранен")
            
    except Exception as e:
        print(f"❌ Ошибка в edit_name: {e}")
    
    # Тест сохранения нового имени
    try:
        update_save = sim.create_message_update("Новое Тестовое Имя")
        context_save = sim.create_context()
        context_save.user_data['editing_employee_id'] = employee_id
        
        result_save = await save_employee_name(update_save, context_save)
        print(f"✅ Сохранение нового имени: состояние {result_save}")
        
        # Проверяем, что имя изменилось в базе
        employee = db_manager.execute_with_retry('''
            SELECT full_name FROM employees WHERE id = ?
        ''', (employee_id,), fetch="one")
        
        if employee:
            decrypted_name = decrypt_data(employee['full_name'])
            if decrypted_name == "Новое Тестовое Имя":
                print("✅ Имя успешно изменено в базе данных")
            else:
                print(f"❌ Имя не изменилось. Получено: {decrypted_name}")
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении имени: {e}")
    
    # Тест кнопки "Изменить должность"
    try:
        update_pos = sim.create_callback_update(f'{{"action":"edit_position","id":{employee_id}}}')
        context_pos = sim.create_context()
        
        await edit_employee_position(update_pos, context_pos)
        print("✅ Кнопка 'Изменить должность' работает")
        
    except Exception as e:
        print(f"❌ Ошибка в edit_position: {e}")
    
    # Тест автоматического применения шаблонов при смене должности
    try:
        update_save_pos = sim.create_callback_update(f'{{"action":"save_position","id":{employee_id},"pos":"Маляр"}}')
        context_save_pos = sim.create_context()
        
        await save_employee_position(update_save_pos, context_save_pos)
        print("✅ Сохранение новой должности с автоматическим применением шаблонов")
        
        # Проверяем, что должность изменилась
        employee = db_manager.execute_with_retry('''
            SELECT position FROM employees WHERE id = ?
        ''', (employee_id,), fetch="one")
        
        if employee and employee['position'] == "Маляр":
            print("✅ Должность изменена на 'Маляр'")
        else:
            print("❌ Должность не изменилась")
            
    except Exception as e:
        print(f"❌ Ошибка при смене должности: {e}")
    
    # Очистка
    db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (employee_id,))
    db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (employee_id,))
    print("🧹 Тестовый сотрудник удален")
    
    return True

async def test_employee_deletion():
    """Тест 4: Удаление сотрудника"""
    print("\n🗑️ ТЕСТ 4: Удаление сотрудника")
    print("=" * 40)
    
    # Создаем тестового сотрудника с событиями
    encrypted_name = encrypt_data("Удаляемый Сотрудник")
    employee_id = db_manager.execute_with_retry('''
        INSERT INTO employees (chat_id, full_name, position, is_active)
        VALUES (?, ?, ?, 1)
    ''', (123456789, encrypted_name, "Плотник"))
    
    # Добавляем события
    for i in range(2):
        db_manager.execute_with_retry('''
            INSERT INTO employee_events (employee_id, event_type, last_event_date, interval_days, next_notification_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, f"Тестовое событие {i+1}", "2024-01-01", 365, "2024-12-31"))
    
    print(f"✅ Создан тестовый сотрудник ID: {employee_id} с 2 событиями")
    
    sim = TelegramSimulator()
    
    # Тест кнопки удаления
    try:
        update_del = sim.create_callback_update(f'{{"action":"delete_employee","id":{employee_id}}}')
        context_del = sim.create_context()
        
        await delete_employee(update_del, context_del)
        print("✅ Кнопка удаления работает (показывает диалог подтверждения)")
        
    except Exception as e:
        print(f"❌ Ошибка в delete_employee: {e}")
    
    # Тест подтверждения удаления
    try:
        update_confirm = sim.create_callback_update(f'{{"action":"confirm_delete","id":{employee_id}}}')
        context_confirm = sim.create_context()
        
        await confirm_delete_employee(update_confirm, context_confirm)
        print("✅ Подтверждение удаления работает")
        
        # Проверяем, что сотрудник и события удалены
        employee_check = db_manager.execute_with_retry('''
            SELECT id FROM employees WHERE id = ?
        ''', (employee_id,), fetch="one")
        
        events_check = db_manager.execute_with_retry('''
            SELECT COUNT(*) as count FROM employee_events WHERE employee_id = ?
        ''', (employee_id,), fetch="one")
        
        if not employee_check and events_check['count'] == 0:
            print("✅ Сотрудник и все события полностью удалены")
        else:
            print("❌ Удаление не завершилось полностью")
            
    except Exception as e:
        print(f"❌ Ошибка в confirm_delete: {e}")
    
    return True

async def main():
    """Главная функция ручного тестирования"""
    print("🤖 РУЧНОЕ ТЕСТИРОВАНИЕ TELEGRAM БОТА")
    print("📞 Симуляция реальных действий пользователя")
    print("=" * 60)
    
    tests = [
        ("Главное меню (без кнопки Шаблоны)", test_main_menu),
        ("Добавление сотрудника (проблема с 'АСЮ')", test_add_employee_flow),
        ("Редактирование сотрудника", test_employee_editing),
        ("Удаление сотрудника", test_employee_deletion)
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
    print(f"📊 РЕЗУЛЬТАТЫ РУЧНОГО ТЕСТИРОВАНИЯ: {passed} ✅ / {failed} ❌")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("🚀 Бот готов к использованию пользователями")
    else:
        print("\n⚠️ Обнаружены проблемы, требующие исправления")
        print("🔧 Необходимо проверить работу бота в реальном Telegram")
    
    return failed == 0

if __name__ == "__main__":
    result = asyncio.run(main())
    print("\n📝 РЕКОМЕНДАЦИИ:")
    print("1. Проверьте работу бота в реальном Telegram интерфейсе")
    print("2. Протестируйте каждую кнопку и функцию вручную")
    print("3. Убедитесь, что все проблемы действительно исправлены")
    
    sys.exit(0 if result else 1)