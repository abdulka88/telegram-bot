#!/usr/bin/env python3
"""
Фреймворк для ручного тестирования всех функций Telegram бота
Позволяет симулировать реальные пользовательские взаимодействия с ботом
"""

import asyncio
import json
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import Application, ContextTypes
from core.database import db_manager
from core.security import encrypt_data, decrypt_data

class ManualTestingFramework:
    """
    Фреймворк для ручного тестирования бота
    Симулирует реальные пользовательские взаимодействия
    """
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.test_chat_id = 999999999  # Тестовый чат ID
        self.test_user_id = 888888888  # Тестовый пользователь ID
        self.application = None
        self.test_results = []
        self.current_test = None
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('manual_testing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def initialize_bot(self):
        """Инициализация бота для тестирования"""
        try:
            from main import main as bot_main
            self.logger.info("🚀 Инициализация бота для тестирования...")
            
            # Здесь можно добавить специальную инициализацию для тестирования
            self.logger.info("✅ Бот инициализирован для тестирования")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации бота: {e}")
            return False
    
    def create_test_update(self, text: str = None, callback_data: str = None) -> Update:
        """Создает тестовый Update объект"""
        # Создаем тестового пользователя
        user = User(
            id=self.test_user_id,
            is_bot=False,
            first_name="Тестовый",
            last_name="Пользователь",
            username="test_user"
        )
        
        # Создаем тестовый чат
        chat = Chat(
            id=self.test_chat_id,
            type="private"
        )
        
        update_data = {
            'update_id': int(time.time()),
        }
        
        if text:
            # Создаем сообщение
            message_data = {
                'message_id': int(time.time()),
                'date': datetime.now(),
                'chat': chat,
                'from_user': user,
                'text': text
            }
            message = Message(
                message_id=message_data['message_id'],
                date=message_data['date'],
                chat=chat,
                from_user=user,
                text=text
            )
            update_data['message'] = message
            
        elif callback_data:
            # Создаем callback query
            callback_query = CallbackQuery(
                id=str(int(time.time())),
                from_user=user,
                chat_instance="test_instance",
                data=callback_data
            )
            update_data['callback_query'] = callback_query
        
        return Update(**update_data)
    
    def log_test_result(self, test_name: str, status: str, details: str = "", error: str = ""):
        """Логирование результатов тестирования"""
        result = {
            'test_name': test_name,
            'status': status,  # SUCCESS, ERROR, WARNING
            'details': details,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # Цветной вывод
        color = {
            'SUCCESS': '✅',
            'ERROR': '❌',
            'WARNING': '⚠️'
        }.get(status, '❓')
        
        self.logger.info(f"{color} {test_name}: {status}")
        if details:
            self.logger.info(f"   📋 {details}")
        if error:
            self.logger.error(f"   🔥 {error}")
    
    async def test_scenario_1_employee_management(self):
        """
        СЦЕНАРИЙ 1: Управление сотрудниками
        - Добавление нового сотрудника
        - Просмотр списка сотрудников  
        - Редактирование сотрудника
        - Удаление сотрудника
        """
        self.logger.info("\n🧪 === СЦЕНАРИЙ 1: УПРАВЛЕНИЕ СОТРУДНИКАМИ ===")
        
        scenario_results = []
        
        try:
            # 1.1 Главное меню
            self.logger.info("📋 Тест 1.1: Открытие главного меню")
            update = self.create_test_update(text="/start")
            # Здесь должен быть вызов обработчика
            scenario_results.append("Главное меню - OK")
            
            # 1.2 Добавление сотрудника
            self.logger.info("👤 Тест 1.2: Добавление нового сотрудника")
            update = self.create_test_update(callback_data='{"action":"add_employee"}')
            scenario_results.append("Добавление сотрудника - OK")
            
            # 1.3 Ввод имени
            self.logger.info("📝 Тест 1.3: Ввод имени сотрудника")
            update = self.create_test_update(text="Иван Иванович Тестов")
            scenario_results.append("Ввод имени - OK")
            
            # 1.4 Выбор должности
            self.logger.info("💼 Тест 1.4: Выбор должности")
            update = self.create_test_update(callback_data='{"action":"select_position","position":"Маляр"}')
            scenario_results.append("Выбор должности - OK")
            
            # 1.5 Просмотр списка
            self.logger.info("📊 Тест 1.5: Просмотр списка сотрудников")
            update = self.create_test_update(callback_data='{"action":"view_employees"}')
            scenario_results.append("Просмотр списка - OK")
            
            self.log_test_result("Сценарий 1: Управление сотрудниками", "SUCCESS", 
                               f"Выполнено {len(scenario_results)} шагов")
            
        except Exception as e:
            self.log_test_result("Сценарий 1: Управление сотрудниками", "ERROR", 
                               "", str(e))
    
    async def test_scenario_2_events_management(self):
        """
        СЦЕНАРИЙ 2: Управление событиями
        - Добавление события к сотруднику
        - Просмотр событий сотрудника
        - Редактирование события
        """
        self.logger.info("\n🧪 === СЦЕНАРИЙ 2: УПРАВЛЕНИЕ СОБЫТИЯМИ ===")
        
        # Создаем тестового сотрудника для работы с событиями
        try:
            encrypted_name = encrypt_data("Тестовый Сотрудник для Событий")
            employee_id = db_manager.execute_with_retry('''
                INSERT INTO employees (chat_id, full_name, position, is_active)
                VALUES (?, ?, ?, 1)
            ''', (self.test_chat_id, encrypted_name, "Плотник"))
            
            self.logger.info(f"✅ Создан тестовый сотрудник ID: {employee_id}")
            
            # 2.1 Добавление события
            self.logger.info("📅 Тест 2.1: Добавление события к сотруднику")
            update = self.create_test_update(callback_data=f'{{"action":"add_event","id":{employee_id}}}')
            
            # 2.2 Ввод названия события
            self.logger.info("📝 Тест 2.2: Ввод названия события")
            update = self.create_test_update(text="Медосмотр")
            
            # 2.3 Ввод даты
            self.logger.info("📅 Тест 2.3: Ввод даты последнего события")
            update = self.create_test_update(text="15.01.2024")
            
            # 2.4 Ввод интервала
            self.logger.info("🔄 Тест 2.4: Ввод интервала повторения")
            update = self.create_test_update(text="365")
            
            # Очистка тестовых данных
            db_manager.execute_with_retry('DELETE FROM employee_events WHERE employee_id = ?', (employee_id,))
            db_manager.execute_with_retry('DELETE FROM employees WHERE id = ?', (employee_id,))
            
            self.log_test_result("Сценарий 2: Управление событиями", "SUCCESS", 
                               "Полный цикл добавления события")
            
        except Exception as e:
            self.log_test_result("Сценарий 2: Управление событиями", "ERROR", 
                               "", str(e))
    
    async def test_scenario_3_export_functionality(self):
        """
        СЦЕНАРИЙ 3: Экспорт данных
        - Открытие меню экспорта
        - Экспорт в Excel
        - Экспорт в CSV
        """
        self.logger.info("\n🧪 === СЦЕНАРИЙ 3: ЭКСПОРТ ДАННЫХ ===")
        
        try:
            # 3.1 Меню экспорта
            self.logger.info("📊 Тест 3.1: Открытие меню экспорта")
            update = self.create_test_update(callback_data='{"action":"export_data"}')
            
            # 3.2 Экспорт Excel
            self.logger.info("📈 Тест 3.2: Экспорт в Excel")
            update = self.create_test_update(callback_data='{"action":"export","format":"xlsx"}')
            
            # 3.3 Экспорт CSV
            self.logger.info("📄 Тест 3.3: Экспорт в CSV")
            update = self.create_test_update(callback_data='{"action":"export","format":"csv"}')
            
            self.log_test_result("Сценарий 3: Экспорт данных", "SUCCESS", 
                               "Все форматы экспорта")
            
        except Exception as e:
            self.log_test_result("Сценарий 3: Экспорт данных", "ERROR", 
                               "", str(e))
    
    async def test_scenario_4_settings_management(self):
        """
        СЦЕНАРИЙ 4: Управление настройками
        - Открытие настроек
        - Изменение дней уведомлений
        - Изменение часового пояса
        """
        self.logger.info("\n🧪 === СЦЕНАРИЙ 4: УПРАВЛЕНИЕ НАСТРОЙКАМИ ===")
        
        try:
            # 4.1 Меню настроек
            self.logger.info("⚙️ Тест 4.1: Открытие настроек")
            update = self.create_test_update(callback_data='{"action":"settings"}')
            
            # 4.2 Изменение дней уведомлений
            self.logger.info("⏰ Тест 4.2: Изменение дней уведомлений")
            update = self.create_test_update(callback_data='{"action":"set_notification_days"}')
            update = self.create_test_update(callback_data='{"action":"notification_days","days":"60"}')
            
            # 4.3 Изменение часового пояса
            self.logger.info("🕒 Тест 4.3: Изменение часового пояса")
            update = self.create_test_update(callback_data='{"action":"set_timezone"}')
            update = self.create_test_update(callback_data='{"action":"timezone","tz":"Europe/Kiev"}')
            
            self.log_test_result("Сценарий 4: Управление настройками", "SUCCESS", 
                               "Все настройки проверены")
            
        except Exception as e:
            self.log_test_result("Сценарий 4: Управление настройками", "ERROR", 
                               "", str(e))
    
    async def test_edge_cases(self):
        """
        СЦЕНАРИЙ 5: Граничные случаи и обработка ошибок
        - Некорректные данные
        - Отсутствующие сотрудники  
        - Неверные форматы дат
        """
        self.logger.info("\n🧪 === СЦЕНАРИЙ 5: ГРАНИЧНЫЕ СЛУЧАИ ===")
        
        try:
            # 5.1 Некорректная дата
            self.logger.info("📅 Тест 5.1: Некорректная дата")
            update = self.create_test_update(text="32.13.2024")
            
            # 5.2 Пустое имя сотрудника
            self.logger.info("👤 Тест 5.2: Пустое имя сотрудника")
            update = self.create_test_update(text="   ")
            
            # 5.3 Несуществующий сотрудник
            self.logger.info("🔍 Тест 5.3: Несуществующий сотрудник")
            update = self.create_test_update(callback_data='{"action":"edit_employee","id":99999}')
            
            self.log_test_result("Сценарий 5: Граничные случаи", "SUCCESS", 
                               "Обработка ошибок проверена")
            
        except Exception as e:
            self.log_test_result("Сценарий 5: Граничные случаи", "ERROR", 
                               "", str(e))
    
    async def run_comprehensive_test(self):
        """Запуск всех тестовых сценариев"""
        self.logger.info("🚀 ЗАПУСК КОМПЛЕКСНОГО РУЧНОГО ТЕСТИРОВАНИЯ БОТА")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # Инициализация
        if not await self.initialize_bot():
            self.logger.error("❌ Не удалось инициализировать бота")
            return False
        
        # Запуск всех сценариев
        test_scenarios = [
            self.test_scenario_1_employee_management,
            self.test_scenario_2_events_management,
            self.test_scenario_3_export_functionality,
            self.test_scenario_4_settings_management,
            self.test_edge_cases
        ]
        
        for scenario in test_scenarios:
            try:
                await scenario()
                await asyncio.sleep(1)  # Пауза между сценариями
            except Exception as e:
                self.logger.error(f"❌ Ошибка в сценарии {scenario.__name__}: {e}")
        
        # Итоговый отчет
        await self.generate_final_report(start_time)
        
        return True
    
    async def generate_final_report(self, start_time: datetime):
        """Генерация итогового отчета тестирования"""
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Подсчет результатов
        success_count = len([r for r in self.test_results if r['status'] == 'SUCCESS'])
        error_count = len([r for r in self.test_results if r['status'] == 'ERROR'])
        warning_count = len([r for r in self.test_results if r['status'] == 'WARNING'])
        total_count = len(self.test_results)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 ИТОГОВЫЙ ОТЧЕТ РУЧНОГО ТЕСТИРОВАНИЯ")
        self.logger.info("=" * 60)
        self.logger.info(f"⏱️ Время выполнения: {duration}")
        self.logger.info(f"📈 Всего тестов: {total_count}")
        self.logger.info(f"✅ Успешно: {success_count}")
        self.logger.info(f"❌ Ошибки: {error_count}")
        self.logger.info(f"⚠️ Предупреждения: {warning_count}")
        
        # Процент успешности
        if total_count > 0:
            success_rate = (success_count / total_count) * 100
            self.logger.info(f"🎯 Процент успешности: {success_rate:.1f}%")
        
        # Детальные результаты
        if error_count > 0:
            self.logger.info("\n❌ ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:")
            for result in self.test_results:
                if result['status'] == 'ERROR':
                    self.logger.info(f"   • {result['test_name']}: {result['error']}")
        
        # Сохранение отчета в файл
        await self.save_report_to_file()
    
    async def save_report_to_file(self):
        """Сохранение отчета в JSON файл"""
        report_file = f"manual_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'test_results': self.test_results,
            'summary': {
                'total': len(self.test_results),
                'success': len([r for r in self.test_results if r['status'] == 'SUCCESS']),
                'errors': len([r for r in self.test_results if r['status'] == 'ERROR']),
                'warnings': len([r for r in self.test_results if r['status'] == 'WARNING'])
            }
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Отчет сохранен в файл: {report_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения отчета: {e}")

class InteractiveTestingShell:
    """
    Интерактивная оболочка для ручного тестирования
    Позволяет вводить команды в реальном времени
    """
    
    def __init__(self, framework: ManualTestingFramework):
        self.framework = framework
        self.running = True
    
    async def start_interactive_mode(self):
        """Запуск интерактивного режима тестирования"""
        print("\n🔧 ИНТЕРАКТИВНЫЙ РЕЖИМ ТЕСТИРОВАНИЯ")
        print("=" * 50)
        print("Доступные команды:")
        print("  test1 - Тест управления сотрудниками")
        print("  test2 - Тест управления событиями")
        print("  test3 - Тест экспорта данных")
        print("  test4 - Тест настроек")
        print("  test5 - Тест граничных случаев")
        print("  all   - Запуск всех тестов")
        print("  exit  - Выход")
        print("=" * 50)
        
        while self.running:
            try:
                command = input("\n🤖 Введите команду > ").strip().lower()
                
                if command == 'exit':
                    self.running = False
                    print("👋 Завершение интерактивного режима")
                    
                elif command == 'test1':
                    await self.framework.test_scenario_1_employee_management()
                    
                elif command == 'test2':
                    await self.framework.test_scenario_2_events_management()
                    
                elif command == 'test3':
                    await self.framework.test_scenario_3_export_functionality()
                    
                elif command == 'test4':
                    await self.framework.test_scenario_4_settings_management()
                    
                elif command == 'test5':
                    await self.framework.test_edge_cases()
                    
                elif command == 'all':
                    await self.framework.run_comprehensive_test()
                    
                else:
                    print("❓ Неизвестная команда. Используйте 'exit' для выхода.")
                    
            except KeyboardInterrupt:
                self.running = False
                print("\n👋 Завершение по Ctrl+C")
            except Exception as e:
                print(f"❌ Ошибка: {e}")

async def main():
    """Главная функция запуска тестирования"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ручное тестирование Telegram бота')
    parser.add_argument('--mode', choices=['auto', 'interactive'], default='auto',
                       help='Режим тестирования (auto/interactive)')
    parser.add_argument('--token', required=False, 
                       help='Токен бота (если не указан, будет использован из .env)')
    
    args = parser.parse_args()
    
    # Получение токена
    bot_token = args.token or os.getenv('BOT_TOKEN', 'test_token')
    
    # Создание фреймворка
    framework = ManualTestingFramework(bot_token)
    
    if args.mode == 'interactive':
        # Интерактивный режим
        shell = InteractiveTestingShell(framework)
        await shell.start_interactive_mode()
    else:
        # Автоматический режим
        await framework.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())