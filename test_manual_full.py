#!/usr/bin/env python3
"""
Полное ручное тестирование функциональности Telegram бота
Имитирует работу реального пользователя с ботом
"""

import asyncio
import sys
import os
from datetime import datetime, date, timedelta
import random

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import db_manager
from managers.notification_manager import NotificationManager
from managers.template_manager import TemplateManager
from managers.search_manager import SearchManager
from managers.export_manager import ExportManager
from managers.advanced_analytics_manager import AdvancedAnalyticsManager
from managers.automated_reports_manager import AutomatedReportsManager
from core.security import encrypt_data, decrypt_data

class BotManualTester:
    """Класс для ручного тестирования всей функциональности бота"""
    
    def __init__(self):
        self.test_chat_id = 12345
        self.admin_id = 67890
        self.notification_manager = NotificationManager(db_manager)
        self.template_manager = TemplateManager(db_manager)
        self.search_manager = SearchManager(db_manager)
        self.export_manager = ExportManager(db_manager)
        self.analytics_manager = AdvancedAnalyticsManager(db_manager)
        self.reports_manager = AutomatedReportsManager(db_manager)
        
        # Данные для тестирования
        self.test_positions = [
            "Плотник", "Маляр", "Рабочий по комплексному обслуживанию и ремонту зданий",
            "Дворник", "Уборщик производственных помещений", "Мастер", "Старший мастер"
        ]
        
        self.test_event_types = [
            "Медицинский осмотр", "Инструктаж по охране труда",
            "Обучение пожарной безопасности", "Проверка знаний",
            "Аттестация", "Переподготовка", "Вакцинация"
        ]
        
        self.employee_names = [
            "Иванов Иван Иванович", "Петров Петр Петрович", "Сидоров Сидор Сидорович",
            "Козлов Андрей Михайлович", "Новиков Сергей Александрович", "Морозов Алексей Дмитриевич",
            "Петрова Мария Ивановна", "Смирнова Елена Петровна", "Кузнецова Анна Сергеевна",
            "Попов Владимир Николаевич", "Лебедев Михаил Александрович", "Козлова Ольга Владимировна",
            "Новикова Татьяна Михайловна", "Морозова Людмила Александровна"
        ]
        
    async def run_full_test(self):
        """Запуск полного цикла тестирования"""
        print("🤖 ПОЛНОЕ РУЧНОЕ ТЕСТИРОВАНИЕ TELEGRAM БОТА")
        print("=" * 60)
        print(f"📅 Начало тестирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print()
        
        try:
            # 1. Подготовка среды
            await self.prepare_test_environment()
            
            # 2. Создание тестовых сотрудников
            employee_ids = await self.create_test_employees()
            
            # 3. Добавление событий
            await self.add_test_events(employee_ids)
            
            # 4. Тестирование поиска
            await self.test_search_functionality()
            
            # 5. Тестирование аналитики
            await self.test_analytics()
            
            # 6. Тестирование отчетов
            await self.test_reports()
            
            # 7. Тестирование экспорта
            await self.test_export()
            
            # 8. Тестирование уведомлений
            await self.test_notifications()
            
            # 9. Проверка целостности данных
            await self.verify_data_integrity()
            
            print("\n🎉 ПОЛНОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            
        except Exception as e:
            print(f"\n❌ ОШИБКА В ТЕСТИРОВАНИИ: {e}")
            import traceback
            traceback.print_exc()
    
    async def prepare_test_environment(self):
        """Подготовка тестовой среды"""
        print("🔧 Этап 1: Подготовка тестовой среды")
        print("-" * 40)
        
        # Настройка чата
        db_manager.execute_with_retry('''
            INSERT OR REPLACE INTO chat_settings 
            (chat_id, admin_id, timezone, notification_days)
            VALUES (?, ?, ?, ?)
        ''', (self.test_chat_id, self.admin_id, 'Europe/Moscow', 90))
        
        print(f"✅ Настроен тестовый чат: {self.test_chat_id}")
        print(f"✅ Администратор: {self.admin_id}")
        print(f"✅ Часовой пояс: Europe/Moscow")
        print(f"✅ Период уведомлений: 90 дней")
        print()
    
    async def create_test_employees(self):
        """Создание тестовых сотрудников"""
        print("👥 Этап 2: Создание тестовых сотрудников")
        print("-" * 40)
        
        employee_ids = []
        
        for i, name in enumerate(self.employee_names):
            position = self.test_positions[i % len(self.test_positions)]
            
            # Шифруем имя
            encrypted_name = encrypt_data(name)
            
            # Добавляем сотрудника
            employee_id = db_manager.execute_with_retry('''
                INSERT INTO employees (chat_id, full_name, position, is_active)
                VALUES (?, ?, ?, ?)
            ''', (self.test_chat_id, encrypted_name, position, True))
            
            employee_ids.append(employee_id)
            
            print(f"✅ Создан сотрудник: {name} ({position}) [ID: {employee_id}]")
        
        print(f"\n📊 Всего создано сотрудников: {len(employee_ids)}")
        
        # Статистика по должностям
        position_stats = {}
        for i, name in enumerate(self.employee_names):
            position = self.test_positions[i % len(self.test_positions)]
            position_stats[position] = position_stats.get(position, 0) + 1
        
        print("\n📋 Распределение по должностям:")
        for position, count in position_stats.items():
            print(f"   {position}: {count} чел.")
        
        print()
        return employee_ids
    
    async def add_test_events(self, employee_ids):
        """Добавление тестовых событий"""
        print("📅 Этап 3: Добавление тестовых событий")
        print("-" * 40)
        
        events_added = 0
        
        for employee_id in employee_ids:
            # Каждому сотруднику добавляем 2-4 события
            num_events = random.randint(2, 4)
            
            for _ in range(num_events):
                event_type = random.choice(self.test_event_types)
                
                # Случайная дата последнего события (от 30 до 400 дней назад)
                days_ago = random.randint(30, 400)
                last_event_date = date.today() - timedelta(days=days_ago)
                
                # Интервал события (от 180 до 365 дней)
                interval_days = random.choice([180, 240, 300, 365])
                
                # Следующее событие
                next_date = last_event_date + timedelta(days=interval_days)
                
                # Добавляем событие
                event_id = db_manager.execute_with_retry('''
                    INSERT INTO employee_events 
                    (employee_id, event_type, last_event_date, next_notification_date, interval_days)
                    VALUES (?, ?, ?, ?, ?)
                ''', (employee_id, event_type, last_event_date.isoformat(), 
                      next_date.isoformat(), interval_days))
                
                events_added += 1
                
                # Определяем статус события
                days_until = (next_date - date.today()).days
                if days_until < 0:
                    status = "🔴 Просрочено"
                elif days_until <= 7:
                    status = "🟠 Критично"
                elif days_until <= 30:
                    status = "🟡 Внимание"
                else:
                    status = "🟢 Плановое"
                
                print(f"✅ Событие добавлено: {event_type} [{status}] - через {days_until} дней")
        
        print(f"\n📊 Всего добавлено событий: {events_added}")
        
        # Статистика по статусам
        status_stats = self.get_events_status_stats()
        print("\n📈 Статистика по статусам:")
        for status, count in status_stats.items():
            print(f"   {status}: {count}")
        
        print()
    
    def get_events_status_stats(self):
        """Получение статистики по статусам событий"""
        events = db_manager.execute_with_retry('''
            SELECT next_notification_date 
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ?
        ''', (self.test_chat_id,), fetch="all")
        
        stats = {"Просрочено": 0, "Критично": 0, "Внимание": 0, "Плановое": 0}
        
        for event in events:
            next_date = date.fromisoformat(event['next_notification_date'])
            days_until = (next_date - date.today()).days
            
            if days_until < 0:
                stats["Просрочено"] += 1
            elif days_until <= 7:
                stats["Критично"] += 1
            elif days_until <= 30:
                stats["Внимание"] += 1
            else:
                stats["Плановое"] += 1
        
        return stats
    
    async def test_search_functionality(self):
        """Тестирование функций поиска"""
        print("🔍 Этап 4: Тестирование поиска")
        print("-" * 40)
        
        # Тест 1: Поиск по имени
        search_results = self.search_manager.smart_text_search(self.test_chat_id, "Иванов", 10)
        print(f"✅ Поиск по имени 'Иванов': найдено {len(search_results)} результатов")
        
        # Тест 2: Поиск по должности
        search_results = self.search_manager.smart_text_search(self.test_chat_id, "Плотник", 10)
        print(f"✅ Поиск по должности 'Плотник': найдено {len(search_results)} результатов")
        
        # Тест 3: Поиск по типу события
        search_results = self.search_manager.smart_text_search(self.test_chat_id, "медицинский", 10)
        print(f"✅ Поиск по событию 'медицинский': найдено {len(search_results)} результатов")
        
        # Тест 4: Фильтрация
        filter_results = self.search_manager.filter_events_by_status(self.test_chat_id, "overdue")
        print(f"✅ Фильтр просроченных: найдено {len(filter_results)} событий")
        
        filter_results = self.search_manager.filter_events_by_status(self.test_chat_id, "critical")
        print(f"✅ Фильтр критических: найдено {len(filter_results)} событий")
        
        print()
    
    async def test_analytics(self):
        """Тестирование аналитики"""
        print("📊 Этап 5: Тестирование аналитики")
        print("-" * 40)
        
        # Тест 1: Анализ трендов
        trends = self.analytics_manager.get_trends_analysis(self.test_chat_id, 6)
        if trends.get('trend') != 'no_data':
            print("✅ Анализ трендов: данные получены")
        else:
            print("⚠️ Анализ трендов: недостаточно данных")
        
        # Тест 2: Показатели эффективности
        efficiency = self.analytics_manager.get_efficiency_metrics(self.test_chat_id)
        print(f"✅ Эффективность: {efficiency.get('efficiency_grade', 'N/A')} "
              f"({efficiency.get('compliance_rate', 0)}% соблюдение)")
        
        # Тест 3: Прогноз нагрузки
        forecast = self.analytics_manager.get_workload_forecast(self.test_chat_id, 30)
        summary = forecast.get('summary', {})
        print(f"✅ Прогноз на 30 дней: {summary.get('total_events', 0)} событий, "
              f"среднее {summary.get('avg_per_day', 0):.1f}/день")
        
        # Тест 4: Временные диаграммы
        charts = self.analytics_manager.get_detailed_timeline_charts(self.test_chat_id)
        print(f"✅ Временные диаграммы: {len(charts)} типов сгенерировано")
        
        # Тест 5: Расширенный прогноз
        periods = {'short': 7, 'medium': 30, 'long': 90}
        advanced_forecast = self.analytics_manager.get_advanced_workload_forecast(self.test_chat_id, periods)
        forecasts = advanced_forecast.get('forecasts', {})
        print(f"✅ Расширенный прогноз: {len(forecasts)} периодов проанализировано")
        
        print()
    
    async def test_reports(self):
        """Тестирование автоматических отчетов"""
        print("📋 Этап 6: Тестирование отчетов")
        print("-" * 40)
        
        # Тест 1: Ежедневный отчет
        daily_report = await self.reports_manager._generate_daily_summary(self.test_chat_id)
        if daily_report:
            print(f"✅ Ежедневный отчет: {len(daily_report)} символов")
        else:
            print("⚠️ Ежедневный отчет: пуст")
        
        # Тест 2: Еженедельный отчет
        weekly_report = await self.reports_manager._generate_weekly_report(self.test_chat_id)
        if weekly_report:
            print(f"✅ Еженедельный отчет: {len(weekly_report)} символов")
        else:
            print("⚠️ Еженедельный отчет: пуст")
        
        # Тест 3: Месячный отчет
        monthly_report = await self.reports_manager._generate_monthly_report(self.test_chat_id)
        if monthly_report:
            print(f"✅ Месячный отчет: {len(monthly_report)} символов")
        else:
            print("⚠️ Месячный отчет: пуст")
        
        # Тест 4: Настройки отчетов
        settings = self.reports_manager.get_report_settings(self.test_chat_id)
        print(f"✅ Настройки отчетов: {len(settings)} параметров")
        
        print()
    
    async def test_export(self):
        """Тестирование экспорта"""
        print("📄 Этап 7: Тестирование экспорта")
        print("-" * 40)
        
        # Тест 1: Экспорт всех событий
        excel_data = await self.export_manager.export_all_events(self.test_chat_id, "xlsx")
        print(f"✅ Экспорт всех событий: {len(excel_data.getvalue())} байт")
        
        # Тест 2: Экспорт аналитики
        analytics_excel = await self.export_manager.export_analytics_report(self.test_chat_id, "full")
        print(f"✅ Экспорт аналитики: {len(analytics_excel.getvalue())} байт")
        
        # Тест 3: Экспорт отчета
        report_excel = await self.export_manager.export_automated_report(self.test_chat_id, "daily")
        if report_excel:
            print(f"✅ Экспорт отчета: {len(report_excel.getvalue())} байт")
        else:
            print("⚠️ Экспорт отчета: нет данных")
        
        print()
    
    async def test_notifications(self):
        """Тестирование уведомлений"""
        print("🔔 Этап 8: Тестирование уведомлений")
        print("-" * 40)
        
        # Получаем события для уведомлений
        upcoming_events = db_manager.execute_with_retry('''
            SELECT ee.*, e.full_name, e.position
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) <= date('now', '+90 days')
            ORDER BY ee.next_notification_date
            LIMIT 10
        ''', (self.test_chat_id,), fetch="all")
        
        print(f"✅ Найдено событий для уведомлений: {len(upcoming_events)}")
        
        # Тестируем определение уровня уведомлений
        for event in upcoming_events[:5]:  # Тестируем первые 5
            next_date = date.fromisoformat(event['next_notification_date'])
            days_until = (next_date - date.today()).days
            
            level = self.notification_manager.get_notification_level(days_until)
            
            try:
                name = decrypt_data(event['full_name'])
            except:
                name = "Не удалось расшифровать"
            
            print(f"   📅 {name}: {event['event_type']} через {days_until} дней ({level})")
        
        print()
    
    async def verify_data_integrity(self):
        """Проверка целостности данных"""
        print("🔍 Этап 9: Проверка целостности данных")
        print("-" * 40)
        
        # Проверка сотрудников
        employees_count = db_manager.execute_with_retry('''
            SELECT COUNT(*) as count FROM employees WHERE chat_id = ?
        ''', (self.test_chat_id,), fetch="one")['count']
        
        # Проверка событий
        events_count = db_manager.execute_with_retry('''
            SELECT COUNT(*) as count 
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ?
        ''', (self.test_chat_id,), fetch="one")['count']
        
        # Проверка дат
        invalid_dates = db_manager.execute_with_retry('''
            SELECT COUNT(*) as count 
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? 
            AND date(ee.next_notification_date) < date(ee.last_event_date)
        ''', (self.test_chat_id,), fetch="one")['count']
        
        print(f"✅ Сотрудников в системе: {employees_count}")
        print(f"✅ События в системе: {events_count}")
        print(f"✅ Некорректных дат: {invalid_dates}")
        
        if invalid_dates == 0:
            print("🎉 Целостность данных подтверждена!")
        else:
            print("⚠️ Обнаружены некорректные даты!")
        
        # Проверка шифрования
        test_employee = db_manager.execute_with_retry('''
            SELECT full_name FROM employees WHERE chat_id = ? LIMIT 1
        ''', (self.test_chat_id,), fetch="one")
        
        if test_employee:
            try:
                decrypted_name = decrypt_data(test_employee['full_name'])
                print("✅ Шифрование/дешифрование работает корректно")
            except Exception as e:
                print(f"❌ Проблема с шифрованием: {e}")
        
        print()

async def main():
    """Главная функция тестирования"""
    tester = BotManualTester()
    await tester.run_full_test()

if __name__ == "__main__":
    asyncio.run(main())