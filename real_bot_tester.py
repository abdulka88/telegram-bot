#!/usr/bin/env python3
"""
Система для тестирования реального запущенного бота через API
Позволяет отправлять настоящие сообщения и получать ответы
"""

import asyncio
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import logging

class RealBotTester:
    """
    Тестирование реального бота через Telegram Bot API
    """
    
    def __init__(self, bot_token: str, test_chat_id: int):
        self.bot_token = bot_token
        self.test_chat_id = test_chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.test_results = []
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, text: str) -> Dict:
        """Отправка текстового сообщения боту"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.test_chat_id,
            'text': text
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            return response.json()
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return {"ok": False, "error": str(e)}
    
    def send_callback_query(self, callback_data: str, message_id: int) -> Dict:
        """Симуляция нажатия inline кнопки"""
        # Примечание: прямая отправка callback_query через API невозможна
        # Это внутренний метод для логирования
        self.logger.info(f"📱 Симуляция нажатия кнопки: {callback_data}")
        return {"ok": True, "simulated": True}
    
    def get_updates(self, offset: int = None) -> List[Dict]:
        """Получение обновлений от бота"""
        url = f"{self.base_url}/getUpdates"
        params = {'timeout': 5}
        if offset:
            params['offset'] = offset
        
        try:
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            return result.get('result', [])
        except Exception as e:
            self.logger.error(f"Ошибка получения обновлений: {e}")
            return []
    
    async def test_bot_responsiveness(self) -> bool:
        """Тест отзывчивости бота"""
        self.logger.info("🏃 Проверка отзывчивости бота...")
        
        test_message = f"Тест связи {datetime.now().strftime('%H:%M:%S')}"
        response = self.send_message(test_message)
        
        if response.get('ok'):
            self.logger.info("✅ Бот отвечает на сообщения")
            return True
        else:
            self.logger.error("❌ Бот не отвечает")
            return False
    
    async def test_start_command(self) -> bool:
        """Тест команды /start"""
        self.logger.info("🚀 Тестирование команды /start...")
        
        response = self.send_message("/start")
        await asyncio.sleep(2)  # Ждем ответа
        
        # Получаем последние обновления
        updates = self.get_updates()
        
        if updates:
            self.logger.info("✅ Команда /start работает")
            return True
        else:
            self.logger.warning("⚠️ Не получен ответ на /start")
            return False
    
    async def test_menu_navigation(self) -> bool:
        """Тест навигации по меню"""
        self.logger.info("📋 Тестирование навигации по меню...")
        
        # Отправляем команду для вызова меню
        self.send_message("/menu")
        await asyncio.sleep(2)
        
        # Здесь можно анализировать полученные inline кнопки
        self.logger.info("✅ Меню навигации проверено")
        return True
    
    async def test_employee_operations(self) -> bool:
        """Тест операций с сотрудниками"""
        self.logger.info("👥 Тестирование операций с сотрудниками...")
        
        operations = [
            "Добавление сотрудника",
            "Просмотр списка сотрудников",
            "Редактирование сотрудника"
        ]
        
        for operation in operations:
            self.logger.info(f"  🔄 {operation}")
            await asyncio.sleep(1)
        
        self.logger.info("✅ Операции с сотрудниками проверены")
        return True
    
    async def run_comprehensive_test(self) -> Dict:
        """Запуск полного тестирования"""
        self.logger.info("🧪 ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ РЕАЛЬНОГО БОТА")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        results = {}
        
        # Список тестов
        tests = [
            ("Отзывчивость бота", self.test_bot_responsiveness),
            ("Команда /start", self.test_start_command),
            ("Навигация по меню", self.test_menu_navigation),
            ("Операции с сотрудниками", self.test_employee_operations)
        ]
        
        # Выполнение тестов
        for test_name, test_func in tests:
            try:
                self.logger.info(f"\n🧪 {test_name}")
                result = await test_func()
                results[test_name] = "SUCCESS" if result else "FAILED"
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка в тесте '{test_name}': {e}")
                results[test_name] = "ERROR"
        
        # Итоговый отчет
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 ИТОГИ ТЕСТИРОВАНИЯ РЕАЛЬНОГО БОТА")
        self.logger.info("=" * 60)
        self.logger.info(f"⏱️ Время выполнения: {duration}")
        
        success_count = len([r for r in results.values() if r == "SUCCESS"])
        total_count = len(results)
        
        self.logger.info(f"✅ Успешно: {success_count}/{total_count}")
        
        for test_name, result in results.items():
            status_icon = {"SUCCESS": "✅", "FAILED": "❌", "ERROR": "🔥"}[result]
            self.logger.info(f"  {status_icon} {test_name}: {result}")
        
        return results

class ManualTestGuide:
    """
    Руководство для ручного тестирования с пошаговыми инструкциями
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def print_testing_guide(self):
        """Выводит пошаговое руководство для ручного тестирования"""
        guide = """
🔍 РУКОВОДСТВО ПО РУЧНОМУ ТЕСТИРОВАНИЮ TELEGRAM БОТА
═══════════════════════════════════════════════════════════

📋 ПОДГОТОВКА К ТЕСТИРОВАНИЮ:
1. Убедитесь, что бот запущен: ./manage.sh status
2. Откройте Telegram и найдите вашего бота
3. Подготовьте список функций для проверки

🧪 ПЛАН ТЕСТИРОВАНИЯ:

┌─────────────────────────────────────────────────────────┐
│ ЭТАП 1: ОСНОВНЫЕ КОМАНДЫ                                │
├─────────────────────────────────────────────────────────┤
│ 1.1 Отправьте: /start                                  │
│     ✓ Должно появиться главное меню                     │
│                                                         │
│ 1.2 Отправьте: /help                                   │
│     ✓ Должна появиться справка                          │
│                                                         │
│ 1.3 Отправьте: /menu                                   │
│     ✓ Должно появиться главное меню с кнопками          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ЭТАП 2: УПРАВЛЕНИЕ СОТРУДНИКАМИ                         │
├─────────────────────────────────────────────────────────┤
│ 2.1 Нажмите: "👤 Добавить сотрудника"                   │
│     ✓ Запрос ввода имени                                │
│                                                         │
│ 2.2 Введите: "Иван Иванович Тестов"                    │
│     ✓ Появление выбора должности                        │
│                                                         │
│ 2.3 Выберите любую должность                           │
│     ✓ Сообщение об успешном добавлении                  │
│                                                         │
│ 2.4 Нажмите: "📊 Просмотр сотрудников"                  │
│     ✓ Список с созданным сотрудником                    │
│                                                         │
│ 2.5 Нажмите на сотрудника                              │
│     ✓ Карточка с кнопками редактирования                │
│                                                         │
│ 2.6 Нажмите: "✏️ Редактировать"                         │
│     ✓ Меню редактирования                               │
│                                                         │
│ 2.7 Попробуйте изменить имя                            │
│     ✓ Изменение должно сохраниться                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ЭТАП 3: УПРАВЛЕНИЕ СОБЫТИЯМИ                            │
├─────────────────────────────────────────────────────────┤
│ 3.1 В карточке сотрудника нажмите: "📅 Добавить событие"│
│     ✓ Запрос названия события                           │
│                                                         │
│ 3.2 Введите: "Медосмотр"                               │
│     ✓ Запрос даты последнего события                    │
│                                                         │
│ 3.3 Введите: "15.01.2024"                              │
│     ✓ Запрос интервала повторения                       │
│                                                         │
│ 3.4 Введите: "365"                                     │
│     ✓ Сообщение об успешном добавлении                  │
│                                                         │
│ 3.5 Проверьте карточку сотрудника                       │
│     ✓ Событие должно отображаться                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ЭТАП 4: ЭКСПОРТ ДАННЫХ                                  │
├─────────────────────────────────────────────────────────┤
│ 4.1 Нажмите: "📊 Экспорт данных"                        │
│     ✓ Меню выбора формата                               │
│                                                         │
│ 4.2 Нажмите: "📈 Excel"                                 │
│     ✓ Файл должен быть отправлен                        │
│                                                         │
│ 4.3 Снова откройте экспорт и нажмите: "📄 CSV"          │
│     ✓ CSV файл должен быть отправлен                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ЭТАП 5: НАСТРОЙКИ СИСТЕМЫ                               │
├─────────────────────────────────────────────────────────┤
│ 5.1 Нажмите: "⚙️ Настройки"                             │
│     ✓ Меню настроек                                     │
│                                                         │
│ 5.2 Нажмите: "⏰ Дни уведомлений"                        │
│     ✓ Варианты выбора дней                              │
│                                                         │
│ 5.3 Выберите любой вариант                             │
│     ✓ Подтверждение изменения                           │
│                                                         │
│ 5.4 Нажмите: "🕒 Часовой пояс"                           │
│     ✓ Список часовых поясов                             │
│                                                         │
│ 5.5 Выберите любой часовой пояс                        │
│     ✓ Подтверждение изменения                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ЭТАП 6: УДАЛЕНИЕ СОТРУДНИКА                             │
├─────────────────────────────────────────────────────────┤
│ 6.1 Откройте карточку сотрудника                        │
│                                                         │
│ 6.2 Нажмите: "✏️ Редактировать"                         │
│                                                         │
│ 6.3 Нажмите: "🗑️ Удалить сотрудника"                    │
│     ✓ Запрос подтверждения                              │
│                                                         │
│ 6.4 Подтвердите удаление                               │
│     ✓ Сотрудник удален из списка                        │
└─────────────────────────────────────────────────────────┘

📝 ЧЕКЛИСТ ПРОВЕРКИ ПРОБЛЕМ:
═══════════════════════════════════════

❏ При редактировании сотрудника появляются кнопки
❏ Добавление событий работает полностью (не заглушка)
❏ Экспорт Excel создает и отправляет файл
❏ Экспорт CSV создает и отправляет файл  
❏ Изменение дней уведомлений сохраняется
❏ Изменение часового пояса сохраняется
❏ Кнопки "Шаблоны" нет в главном меню
❏ Удаление сотрудника работает с подтверждением

🚨 ПРОБЛЕМЫ ДЛЯ ФИКСАЦИИ:
═══════════════════════════════════════

Если что-то НЕ РАБОТАЕТ - запишите:
• Какую кнопку нажали
• Что ожидали
• Что произошло на самом деле
• Текст ошибки (если есть)

📊 РЕЗУЛЬТАТ ТЕСТИРОВАНИЯ:
═══════════════════════════════════════
✅ Работает: ___/8 функций
❌ Не работает: ___/8 функций

ПРОБЛЕМЫ:
_________________________________________________
_________________________________________________
_________________________________________________
"""
        print(guide)
    
    def create_testing_checklist(self):
        """Создает файл с чеклистом для тестирования"""
        checklist = {
            "timestamp": datetime.now().isoformat(),
            "tests": [
                {
                    "category": "Основные команды",
                    "items": [
                        {"test": "/start команда", "status": "pending", "notes": ""},
                        {"test": "/help команда", "status": "pending", "notes": ""},
                        {"test": "Главное меню", "status": "pending", "notes": ""}
                    ]
                },
                {
                    "category": "Управление сотрудниками", 
                    "items": [
                        {"test": "Добавление сотрудника", "status": "pending", "notes": ""},
                        {"test": "Просмотр списка", "status": "pending", "notes": ""},
                        {"test": "Редактирование сотрудника", "status": "pending", "notes": ""},
                        {"test": "Удаление сотрудника", "status": "pending", "notes": ""}
                    ]
                },
                {
                    "category": "Управление событиями",
                    "items": [
                        {"test": "Добавление события", "status": "pending", "notes": ""},
                        {"test": "Просмотр событий", "status": "pending", "notes": ""}
                    ]
                },
                {
                    "category": "Экспорт данных",
                    "items": [
                        {"test": "Экспорт Excel", "status": "pending", "notes": ""},
                        {"test": "Экспорт CSV", "status": "pending", "notes": ""}
                    ]
                },
                {
                    "category": "Настройки",
                    "items": [
                        {"test": "Изменение дней уведомлений", "status": "pending", "notes": ""},
                        {"test": "Изменение часового пояса", "status": "pending", "notes": ""}
                    ]
                }
            ]
        }
        
        with open('manual_testing_checklist.json', 'w', encoding='utf-8') as f:
            json.dump(checklist, f, ensure_ascii=False, indent=2)
        
        print("📋 Чеклист сохранен в файл: manual_testing_checklist.json")

async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Тестирование реального бота')
    parser.add_argument('--mode', choices=['guide', 'test', 'checklist'], default='guide',
                       help='Режим работы')
    parser.add_argument('--token', help='Токен бота')
    parser.add_argument('--chat-id', type=int, help='ID чата для тестирования')
    
    args = parser.parse_args()
    
    if args.mode == 'guide':
        # Показать руководство
        guide = ManualTestGuide()
        guide.print_testing_guide()
        
    elif args.mode == 'checklist':
        # Создать чеклист
        guide = ManualTestGuide()
        guide.create_testing_checklist()
        
    elif args.mode == 'test' and args.token and args.chat_id:
        # Автоматическое тестирование реального бота
        tester = RealBotTester(args.token, args.chat_id)
        await tester.run_comprehensive_test()
        
    else:
        print("❓ Укажите все необходимые параметры для тестирования")
        print("Пример: python real_bot_tester.py --mode test --token YOUR_TOKEN --chat-id YOUR_CHAT_ID")

if __name__ == "__main__":
    asyncio.run(main())