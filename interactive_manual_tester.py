#!/usr/bin/env python3
"""
Интерактивная система для пошагового ручного тестирования бота
Проводит тестирование с пользователем и фиксирует результаты
"""

import json
import time
from datetime import datetime
from typing import Dict, List
import os

class InteractiveManualTester:
    """
    Интерактивная система для ручного тестирования
    """
    
    def __init__(self):
        self.test_results = []
        self.current_step = 0
        self.problems_found = []
        
        # Определение всех тестовых сценариев
        self.test_scenarios = self.define_test_scenarios()
    
    def define_test_scenarios(self) -> List[Dict]:
        """Определение всех тестовых сценариев"""
        return [
            {
                "category": "🚀 Основные команды",
                "tests": [
                    {
                        "name": "Команда /start",
                        "action": "Отправьте боту команду: /start",
                        "expected": "Должно появиться главное меню с кнопками",
                        "critical": True
                    },
                    {
                        "name": "Главное меню",
                        "action": "Проверьте кнопки в главном меню",
                        "expected": "Кнопки: Добавить сотрудника, Просмотр сотрудников, Экспорт данных, Настройки (БЕЗ кнопки Шаблоны)",
                        "critical": True
                    }
                ]
            },
            {
                "category": "👥 Управление сотрудниками",
                "tests": [
                    {
                        "name": "Добавление сотрудника - Шаг 1",
                        "action": "Нажмите кнопку '👤 Добавить сотрудника'",
                        "expected": "Запрос ввода имени сотрудника",
                        "critical": True
                    },
                    {
                        "name": "Добавление сотрудника - Шаг 2",
                        "action": "Введите: 'Иван Иванович Тестов'",
                        "expected": "Появляется выбор должности (dropdown список)",
                        "critical": True
                    },
                    {
                        "name": "Добавление сотрудника - Шаг 3",
                        "action": "Выберите любую должность из списка",
                        "expected": "Сообщение об успешном добавлении + автоматическое применение шаблонов",
                        "critical": True
                    },
                    {
                        "name": "Просмотр списка сотрудников",
                        "action": "Нажмите '📊 Просмотр сотрудников'",
                        "expected": "Список с добавленным сотрудником",
                        "critical": True
                    },
                    {
                        "name": "Открытие карточки сотрудника",
                        "action": "Нажмите на созданного сотрудника",
                        "expected": "Карточка с данными и кнопками: Редактировать, Добавить событие",
                        "critical": True
                    },
                    {
                        "name": "Меню редактирования",
                        "action": "Нажмите '✏️ Редактировать'",
                        "expected": "Меню с опциями редактирования + кнопка 'Удалить сотрудника'",
                        "critical": True
                    }
                ]
            },
            {
                "category": "📅 Управление событиями", 
                "tests": [
                    {
                        "name": "Добавление события - Начало",
                        "action": "В карточке сотрудника нажмите '📅 Добавить событие'",
                        "expected": "Запрос названия события (НЕ сообщение о том, что функция будет доступна позже)",
                        "critical": True
                    },
                    {
                        "name": "Добавление события - Название",
                        "action": "Введите: 'Медосмотр'",
                        "expected": "Запрос даты последнего события",
                        "critical": True
                    },
                    {
                        "name": "Добавление события - Дата",
                        "action": "Введите: '15.01.2024'",
                        "expected": "Запрос интервала повторения в днях",
                        "critical": True
                    },
                    {
                        "name": "Добавление события - Интервал",
                        "action": "Введите: '365'",
                        "expected": "Сообщение об успешном добавлении события",
                        "critical": True
                    },
                    {
                        "name": "Проверка добавленного события",
                        "action": "Откройте карточку сотрудника еще раз",
                        "expected": "Событие 'Медосмотр' отображается в карточке",
                        "critical": True
                    }
                ]
            },
            {
                "category": "📊 Экспорт данных",
                "tests": [
                    {
                        "name": "Меню экспорта",
                        "action": "Нажмите '📊 Экспорт данных'",
                        "expected": "Меню выбора формата файла",
                        "critical": True
                    },
                    {
                        "name": "Экспорт Excel",
                        "action": "Нажмите '📈 Excel'",
                        "expected": "Файл .xlsx отправляется в чат",
                        "critical": True
                    },
                    {
                        "name": "Экспорт CSV",
                        "action": "Снова откройте экспорт и нажмите '📄 CSV'",
                        "expected": "Файл .csv отправляется в чат",
                        "critical": True
                    }
                ]
            },
            {
                "category": "⚙️ Настройки системы",
                "tests": [
                    {
                        "name": "Меню настроек",
                        "action": "Нажмите '⚙️ Настройки'",
                        "expected": "Меню настроек с опциями",
                        "critical": True
                    },
                    {
                        "name": "Настройка дней уведомлений",
                        "action": "Нажмите '⏰ Дни уведомлений'",
                        "expected": "Варианты выбора количества дней",
                        "critical": True
                    },
                    {
                        "name": "Изменение дней уведомлений",
                        "action": "Выберите любой вариант дней",
                        "expected": "Подтверждение сохранения настройки",
                        "critical": True
                    },
                    {
                        "name": "Настройка часового пояса",
                        "action": "Нажмите '🕒 Часовой пояс'",
                        "expected": "Список доступных часовых поясов",
                        "critical": True
                    },
                    {
                        "name": "Изменение часового пояса",
                        "action": "Выберите любой часовой пояс",
                        "expected": "Подтверждение сохранения настройки",
                        "critical": True
                    }
                ]
            },
            {
                "category": "🗑️ Удаление сотрудника",
                "tests": [
                    {
                        "name": "Инициация удаления",
                        "action": "В меню редактирования нажмите '🗑️ Удалить сотрудника'",
                        "expected": "Запрос подтверждения с деталями сотрудника",
                        "critical": True
                    },
                    {
                        "name": "Подтверждение удаления",
                        "action": "Подтвердите удаление",
                        "expected": "Сотрудник удален, исчез из списка вместе с событиями",
                        "critical": True
                    }
                ]
            }
        ]
    
    def print_header(self):
        """Печать заголовка"""
        print("\n" + "=" * 80)
        print("🧪 ИНТЕРАКТИВНОЕ РУЧНОЕ ТЕСТИРОВАНИЕ TELEGRAM БОТА")
        print("=" * 80)
        print("Этот скрипт проведет вас через все функции бота шаг за шагом.")
        print("После каждого теста вы будете указывать результат: работает или нет.")
        print("В конце будет сформирован подробный отчет с найденными проблемами.")
        print("=" * 80)
    
    def ask_user_confirmation(self, question: str) -> bool:
        """Запрос подтверждения у пользователя"""
        while True:
            response = input(f"{question} (да/нет): ").strip().lower()
            if response in ['да', 'yes', 'y', 'д']:
                return True
            elif response in ['нет', 'no', 'n', 'н']:
                return False
            else:
                print("Пожалуйста, введите 'да' или 'нет'")
    
    def get_user_input(self, prompt: str) -> str:
        """Получение текстового ввода от пользователя"""
        return input(f"{prompt}: ").strip()
    
    def run_test_scenario(self, category: str, tests: List[Dict]) -> List[Dict]:
        """Выполнение одного тестового сценария"""
        print(f"\n{'='*20} {category} {'='*20}")
        
        category_results = []
        
        for i, test in enumerate(tests, 1):
            print(f"\n🧪 ТЕСТ {i}: {test['name']}")
            print("─" * 60)
            print(f"📋 ДЕЙСТВИЕ: {test['action']}")
            print(f"✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: {test['expected']}")
            print("─" * 60)
            
            # Ожидание готовности пользователя
            ready = self.ask_user_confirmation("Готовы выполнить этот тест?")
            if not ready:
                print("⏸️ Тест пропущен по запросу пользователя")
                category_results.append({
                    "name": test['name'],
                    "status": "SKIPPED",
                    "notes": "Пропущен пользователем",
                    "critical": test.get('critical', False)
                })
                continue
            
            # Пауза для выполнения действия
            print("\n⏳ Выполните действие и наблюдайте результат...")
            input("Нажмите Enter, когда будете готовы сообщить результат...")
            
            # Проверка результата
            success = self.ask_user_confirmation("Работает ли функция как ожидалось?")
            
            test_result = {
                "name": test['name'],
                "action": test['action'],
                "expected": test['expected'],
                "status": "SUCCESS" if success else "FAILED",
                "critical": test.get('critical', False),
                "timestamp": datetime.now().isoformat()
            }
            
            if not success:
                # Получение деталей проблемы
                actual_result = self.get_user_input("Что произошло на самом деле?")
                error_message = self.get_user_input("Есть ли сообщение об ошибке? (если нет - оставьте пустым)")
                
                test_result["actual_result"] = actual_result
                test_result["error_message"] = error_message
                test_result["notes"] = f"Проблема: {actual_result}"
                
                # Добавление в список проблем
                self.problems_found.append({
                    "category": category,
                    "test": test['name'],
                    "problem": actual_result,
                    "error": error_message,
                    "critical": test.get('critical', False)
                })
                
                print(f"❌ Проблема зафиксирована: {actual_result}")
            else:
                test_result["notes"] = "Работает корректно"
                print(f"✅ Тест пройден успешно")
            
            category_results.append(test_result)
            self.test_results.append(test_result)
        
        return category_results
    
    def generate_final_report(self):
        """Генерация итогового отчета"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ РУЧНОГО ТЕСТИРОВАНИЯ")
        print("=" * 80)
        
        # Подсчет статистики
        total_tests = len(self.test_results)
        successful_tests = len([t for t in self.test_results if t['status'] == 'SUCCESS'])
        failed_tests = len([t for t in self.test_results if t['status'] == 'FAILED'])
        skipped_tests = len([t for t in self.test_results if t['status'] == 'SKIPPED'])
        critical_failures = len([t for t in self.test_results if t['status'] == 'FAILED' and t['critical']])
        
        print(f"📈 ОБЩАЯ СТАТИСТИКА:")
        print(f"   Всего тестов: {total_tests}")
        print(f"   ✅ Успешно: {successful_tests}")
        print(f"   ❌ Не работает: {failed_tests}")
        print(f"   ⏸️ Пропущено: {skipped_tests}")
        print(f"   🚨 Критических проблем: {critical_failures}")
        
        # Процент успешности
        if total_tests > 0:
            success_rate = (successful_tests / (total_tests - skipped_tests)) * 100 if (total_tests - skipped_tests) > 0 else 0
            print(f"   🎯 Процент успешности: {success_rate:.1f}%")
        
        # Детализация по категориям
        print(f"\n📋 РЕЗУЛЬТАТЫ ПО КАТЕГОРИЯМ:")
        for scenario in self.test_scenarios:
            category = scenario['category']
            category_tests = [t for t in self.test_results if any(test['name'] == t['name'] for test in scenario['tests'])]
            
            if category_tests:
                cat_success = len([t for t in category_tests if t['status'] == 'SUCCESS'])
                cat_total = len(category_tests)
                cat_failed = len([t for t in category_tests if t['status'] == 'FAILED'])
                
                status_icon = "✅" if cat_failed == 0 else "❌"
                print(f"   {status_icon} {category}: {cat_success}/{cat_total}")
        
        # Список найденных проблем
        if self.problems_found:
            print(f"\n🚨 НАЙДЕННЫЕ ПРОБЛЕМЫ:")
            for i, problem in enumerate(self.problems_found, 1):
                critical_mark = "🔥 [КРИТИЧНАЯ] " if problem['critical'] else ""
                print(f"\n   {i}. {critical_mark}{problem['category']} - {problem['test']}")
                print(f"      Проблема: {problem['problem']}")
                if problem['error']:
                    print(f"      Ошибка: {problem['error']}")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        if critical_failures > 0:
            print("   🚨 Обнаружены критические проблемы - требуется немедленное исправление")
        if failed_tests > 0:
            print("   🔧 Требуется исправление найденных проблем")
        if failed_tests == 0:
            print("   🎉 Все тесты пройдены успешно! Бот работает корректно")
        
        # Сохранение отчета
        self.save_report()
    
    def save_report(self):
        """Сохранение отчета в файл"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"manual_test_report_{timestamp}.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "successful_tests": len([t for t in self.test_results if t['status'] == 'SUCCESS']),
            "failed_tests": len([t for t in self.test_results if t['status'] == 'FAILED']),
            "skipped_tests": len([t for t in self.test_results if t['status'] == 'SKIPPED']),
            "critical_failures": len([t for t in self.test_results if t['status'] == 'FAILED' and t['critical']]),
            "test_results": self.test_results,
            "problems_found": self.problems_found
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 Подробный отчет сохранен в файл: {report_file}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения отчета: {e}")
    
    def run_complete_testing(self):
        """Запуск полного тестирования"""
        self.print_header()
        
        # Предварительная проверка
        bot_running = self.ask_user_confirmation("Убедитесь, что бот запущен. Бот запущен?")
        if not bot_running:
            print("🚨 Сначала запустите бота командой: ./manage.sh start")
            return
        
        bot_accessible = self.ask_user_confirmation("Открыт ли Telegram и найден ли ваш бот?")
        if not bot_accessible:
            print("🚨 Откройте Telegram и найдите вашего бота перед началом тестирования")
            return
        
        print("\n🚀 Начинаем тестирование...")
        start_time = datetime.now()
        
        # Выполнение всех сценариев
        for scenario in self.test_scenarios:
            self.run_test_scenario(scenario['category'], scenario['tests'])
            
            # Небольшая пауза между категориями
            if scenario != self.test_scenarios[-1]:  # Не последний сценарий
                continue_testing = self.ask_user_confirmation("\nПродолжить тестирование следующей категории?")
                if not continue_testing:
                    print("⏸️ Тестирование остановлено по запросу пользователя")
                    break
        
        # Генерация отчета
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n⏱️ Время тестирования: {duration}")
        self.generate_final_report()

def main():
    """Главная функция"""
    print("🔧 Система интерактивного ручного тестирования Telegram бота")
    
    tester = InteractiveManualTester()
    
    try:
        tester.run_complete_testing()
    except KeyboardInterrupt:
        print("\n\n⏸️ Тестирование прервано пользователем (Ctrl+C)")
        if tester.test_results:
            print("Генерация частичного отчета...")
            tester.generate_final_report()
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()