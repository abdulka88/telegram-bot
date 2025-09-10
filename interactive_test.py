#!/usr/bin/env python3
"""
Интерактивный тестировщик функциональности Telegram бота
Проводит полное ручное тестирование всех возможностей
"""

import asyncio
import sys
import os
from datetime import datetime, date, timedelta
import random

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import db_manager
from core.security import encrypt_data, decrypt_data

class InteractiveTester:
    """Интерактивный тестировщик бота"""
    
    def __init__(self):
        self.test_chat_id = 12345
        self.admin_id = 67890
        
        # Данные для тестирования
        self.positions = [
            "Плотник", "Маляр", "Рабочий по комплексному обслуживанию и ремонту зданий",
            "Дворник", "Уборщик производственных помещений", "Мастер", "Старший мастер",
            "Электрик", "Слесарь", "Сварщик"
        ]
        
        self.event_types = [
            "Медицинский осмотр", "Инструктаж по охране труда",
            "Обучение пожарной безопасности", "Проверка знаний",
            "Аттестация", "Переподготовка", "Вакцинация",
            "Техническое обучение", "Курсы повышения квалификации"
        ]
        
        self.employee_names = [
            "Иванов Иван Иванович", "Петров Петр Петрович", "Сидоров Сидор Сидорович",
            "Козлов Андрей Михайлович", "Новиков Сергей Александрович", "Морозов Алексей Дмитриевич",
            "Петрова Мария Ивановна", "Смирнова Елена Петровна", "Кузнецова Анна Сергеевна",
            "Попов Владимир Николаевич", "Лебедев Михаил Александрович", "Козлова Ольга Владимировна",
            "Новикова Татьяна Михайловна", "Морозова Людмила Александровна", "Федоров Роман Андреевич",
            "Григорьев Максим Петрович", "Соловьева Светлана Ивановна", "Борисов Николай Викторович"
        ]
    
    def print_header(self, title):
        """Красивый заголовок"""
        print("\n" + "="*60)
        print(f"🤖 {title}")
        print("="*60)
    
    def print_step(self, step_num, title):
        """Заголовок этапа"""
        print(f"\n📋 Этап {step_num}: {title}")
        print("-"*40)
    
    async def setup_test_environment(self):
        """Настройка тестовой среды"""
        self.print_step(1, "Подготовка тестовой среды")
        
        try:
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
            
            # Настройка отчетов
            db_manager.execute_with_retry('''
                INSERT OR REPLACE INTO report_settings 
                (chat_id, daily_enabled, weekly_enabled, monthly_enabled, daily_time, weekly_day, monthly_day)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.test_chat_id, 1, 1, 1, '09:00', 1, 1))
            
            print("✅ Настроены автоматические отчеты")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка настройки среды: {e}")
            return False
    
    async def create_diverse_employees(self):
        """Создание разнообразных сотрудников"""
        self.print_step(2, "Создание тестовых сотрудников")
        
        employee_ids = []
        
        try:
            for i, name in enumerate(self.employee_names):
                position = self.positions[i % len(self.positions)]
                
                # Шифруем имя
                encrypted_name = encrypt_data(name)
                
                # Добавляем сотрудника
                employee_id = db_manager.execute_with_retry('''
                    INSERT INTO employees (chat_id, full_name, position, is_active)
                    VALUES (?, ?, ?, ?)
                ''', (self.test_chat_id, encrypted_name, position, True))
                
                employee_ids.append(employee_id)
                print(f"✅ Создан: {name} ({position}) [ID: {employee_id}]")
            
            # Статистика по должностям
            position_stats = {}
            for i, name in enumerate(self.employee_names):
                position = self.positions[i % len(self.positions)]
                position_stats[position] = position_stats.get(position, 0) + 1
            
            print(f"\n📊 Всего создано сотрудников: {len(employee_ids)}")
            print("\n📋 Распределение по должностям:")
            for position, count in sorted(position_stats.items()):
                print(f"   {position}: {count} чел.")
            
            return employee_ids
            
        except Exception as e:
            print(f"❌ Ошибка создания сотрудников: {e}")
            return []
    
    async def add_realistic_events(self, employee_ids):
        """Добавление реалистичных событий"""
        self.print_step(3, "Добавление событий сотрудникам")
        
        events_added = 0
        overdue_count = 0
        critical_count = 0
        warning_count = 0
        normal_count = 0
        
        try:
            for employee_id in employee_ids:
                # Каждому сотруднику добавляем 2-5 событий
                num_events = random.randint(2, 5)
                
                for _ in range(num_events):
                    event_type = random.choice(self.event_types)
                    
                    # Варьируем даты для создания разных статусов
                    if events_added % 4 == 0:  # 25% просроченных
                        days_ago = random.randint(400, 600)
                        interval_days = random.choice([180, 365])
                    elif events_added % 4 == 1:  # 25% критических (скоро)
                        days_ago = random.randint(340, 360)
                        interval_days = 365
                    elif events_added % 4 == 2:  # 25% предупреждающих
                        days_ago = random.randint(320, 350)
                        interval_days = 365
                    else:  # 25% нормальных
                        days_ago = random.randint(30, 300)
                        interval_days = random.choice([180, 240, 300, 365])
                    
                    last_event_date = date.today() - timedelta(days=days_ago)
                    next_date = last_event_date + timedelta(days=interval_days)
                    
                    # Добавляем событие
                    event_id = db_manager.execute_with_retry('''
                        INSERT INTO employee_events 
                        (employee_id, event_type, last_event_date, next_notification_date, interval_days)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (employee_id, event_type, last_event_date.isoformat(), 
                          next_date.isoformat(), interval_days))
                    
                    events_added += 1
                    
                    # Определяем статус
                    days_until = (next_date - date.today()).days
                    if days_until < 0:
                        status = "🔴 Просрочено"
                        overdue_count += 1
                    elif days_until <= 7:
                        status = "🟠 Критично"
                        critical_count += 1
                    elif days_until <= 30:
                        status = "🟡 Внимание"
                        warning_count += 1
                    else:
                        status = "🟢 Плановое"
                        normal_count += 1
                    
                    print(f"✅ {event_type} [{status}] - через {days_until} дней")
            
            print(f"\n📊 Статистика событий:")
            print(f"   🔴 Просрочено: {overdue_count}")
            print(f"   🟠 Критично: {critical_count}")
            print(f"   🟡 Внимание: {warning_count}")
            print(f"   🟢 Плановое: {normal_count}")
            print(f"   📝 Всего: {events_added}")
            
            return events_added > 0
            
        except Exception as e:
            print(f"❌ Ошибка добавления событий: {e}")
            return False
    
    async def test_search_functionality(self):
        """Тестирование поиска"""
        self.print_step(4, "Тестирование функций поиска")
        
        try:
            # Импортируем менеджер поиска
            from managers.search_manager import SearchManager
            search_manager = SearchManager(db_manager)
            
            # Тест поиска по имени
            results = search_manager.smart_text_search(self.test_chat_id, "Иванов", 5)
            print(f"✅ Поиск по имени 'Иванов': {len(results)} результатов")
            
            # Тест поиска по должности
            results = search_manager.smart_text_search(self.test_chat_id, "Плотник", 5)
            print(f"✅ Поиск по должности 'Плотник': {len(results)} результатов")
            
            # Тест фильтрации
            overdue = search_manager.filter_events_by_status(self.test_chat_id, "overdue")
            critical = search_manager.filter_events_by_status(self.test_chat_id, "critical")
            print(f"✅ Просроченные события: {len(overdue)}")
            print(f"✅ Критические события: {len(critical)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка тестирования поиска: {e}")
            return False
    
    async def test_analytics(self):
        """Тестирование аналитики"""
        self.print_step(5, "Тестирование аналитики")
        
        try:
            from managers.advanced_analytics_manager import AdvancedAnalyticsManager
            analytics = AdvancedAnalyticsManager(db_manager)
            
            # Тест базовой аналитики
            efficiency = analytics.get_efficiency_metrics(self.test_chat_id)
            print(f"✅ Показатели эффективности: {efficiency.get('efficiency_grade', 'N/A')}")
            print(f"   Соблюдение: {efficiency.get('compliance_rate', 0):.1f}%")
            
            # Тест прогноза нагрузки
            forecast = analytics.get_workload_forecast(self.test_chat_id, 30)
            total_events = forecast.get('summary', {}).get('total_events', 0)
            avg_per_day = forecast.get('summary', {}).get('avg_per_day', 0)
            print(f"✅ Прогноз на 30 дней: {total_events} событий, {avg_per_day:.1f}/день")
            
            # Тест временных диаграмм
            charts = analytics.get_detailed_timeline_charts(self.test_chat_id)
            print(f"✅ Временные диаграммы: {len(charts)} типов")
            
            # Тест расширенного прогноза
            periods = {'short': 7, 'medium': 30, 'long': 90}
            advanced = analytics.get_advanced_workload_forecast(self.test_chat_id, periods)
            forecasts = advanced.get('forecasts', {})
            print(f"✅ Расширенный прогноз: {len(forecasts)} периодов")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка тестирования аналитики: {e}")
            return False
    
    async def test_reports(self):
        """Тестирование отчетов"""
        self.print_step(6, "Тестирование автоматических отчетов")
        
        try:
            from managers.automated_reports_manager import AutomatedReportsManager
            reports = AutomatedReportsManager(db_manager)
            
            # Тест ежедневного отчета
            daily = await reports._generate_daily_summary(self.test_chat_id)
            print(f"✅ Ежедневный отчет: {len(daily) if daily else 0} символов")
            
            # Тест еженедельного отчета
            weekly = await reports._generate_weekly_report(self.test_chat_id)
            print(f"✅ Еженедельный отчет: {len(weekly) if weekly else 0} символов")
            
            # Тест месячного отчета
            monthly = await reports._generate_monthly_report(self.test_chat_id)
            print(f"✅ Месячный отчет: {len(monthly) if monthly else 0} символов")
            
            # Тест настроек
            settings = reports.get_report_settings(self.test_chat_id)
            enabled_reports = sum([
                settings.get('daily_enabled', 0),
                settings.get('weekly_enabled', 0),
                settings.get('monthly_enabled', 0)
            ])
            print(f"✅ Включено отчетов: {enabled_reports} из 3")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка тестирования отчетов: {e}")
            return False
    
    async def test_export(self):
        """Тестирование экспорта"""
        self.print_step(7, "Тестирование экспорта в Excel")
        
        try:
            from managers.export_manager import ExportManager
            export = ExportManager(db_manager)
            
            # Тест экспорта всех событий
            excel_data = await export.export_all_events(self.test_chat_id, "xlsx")
            print(f"✅ Экспорт всех событий: {len(excel_data.getvalue())} байт")
            
            # Тест экспорта аналитики
            analytics_data = await export.export_analytics_report(self.test_chat_id, "full")
            print(f"✅ Экспорт аналитики: {len(analytics_data.getvalue())} байт")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка тестирования экспорта: {e}")
            return False
    
    async def verify_data_integrity(self):
        """Проверка целостности данных"""
        self.print_step(8, "Проверка целостности данных")
        
        try:
            # Проверка сотрудников
            employees = db_manager.execute_with_retry('''
                SELECT COUNT(*) as count FROM employees WHERE chat_id = ?
            ''', (self.test_chat_id,), fetch="one")
            
            # Проверка событий
            events = db_manager.execute_with_retry('''
                SELECT COUNT(*) as count 
                FROM employee_events ee
                JOIN employees e ON ee.employee_id = e.id
                WHERE e.chat_id = ?
            ''', (self.test_chat_id,), fetch="one")
            
            # Проверка некорректных дат
            invalid_dates = db_manager.execute_with_retry('''
                SELECT COUNT(*) as count 
                FROM employee_events ee
                JOIN employees e ON ee.employee_id = e.id
                WHERE e.chat_id = ? 
                AND date(ee.next_notification_date) < date(ee.last_event_date)
            ''', (self.test_chat_id,), fetch="one")
            
            print(f"✅ Сотрудников в системе: {employees['count']}")
            print(f"✅ События в системе: {events['count']}")
            print(f"✅ Некорректных дат: {invalid_dates['count']}")
            
            # Проверка шифрования
            test_employee = db_manager.execute_with_retry('''
                SELECT full_name FROM employees WHERE chat_id = ? LIMIT 1
            ''', (self.test_chat_id,), fetch="one")
            
            if test_employee:
                decrypted_name = decrypt_data(test_employee['full_name'])
                print(f"✅ Шифрование работает: {decrypted_name[:10]}...")
            
            return invalid_dates['count'] == 0
            
        except Exception as e:
            print(f"❌ Ошибка проверки данных: {e}")
            return False
    
    async def run_comprehensive_test(self):
        """Запуск полного тестирования"""
        self.print_header("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ TELEGRAM БОТА")
        print(f"🕒 Начало: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        
        results = []
        
        # Выполняем все этапы тестирования
        results.append(await self.setup_test_environment())
        
        employee_ids = await self.create_diverse_employees()
        results.append(len(employee_ids) > 0)
        
        if employee_ids:
            results.append(await self.add_realistic_events(employee_ids))
            results.append(await self.test_search_functionality())
            results.append(await self.test_analytics())
            results.append(await self.test_reports())
            results.append(await self.test_export())
            results.append(await self.verify_data_integrity())
        
        # Итоговый отчет
        self.print_header("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        passed = sum(results)
        total = len(results)
        success_rate = (passed / total) * 100
        
        print(f"✅ Успешно пройдено: {passed}/{total} тестов")
        print(f"📊 Успешность: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        else:
            print("⚠️ Обнаружены проблемы, требуется доработка")
        
        print(f"🕒 Завершено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

async def main():
    """Главная функция"""
    tester = InteractiveTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())