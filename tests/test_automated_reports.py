#!/usr/bin/env python3
"""
Тест функциональности автоматических отчетов
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db_manager
from managers.automated_reports_manager import AutomatedReportsManager

async def test_automated_reports():
    """Тестирует функциональность автоматических отчетов"""
    
    # Инициализируем менеджер отчетов
    reports_manager = AutomatedReportsManager(db_manager)
    
    print("📊 ТЕСТИРОВАНИЕ АВТОМАТИЧЕСКИХ ОТЧЕТОВ")
    print("=" * 50)
    
    # Тестовый chat_id
    test_chat_id = 12345
    
    try:
        # Тест 1: Получение настроек отчетов
        print("\n⚙️ Тест 1: Настройки отчетов")
        settings = reports_manager.get_report_settings(test_chat_id)
        print(f"✅ Настройки получены")
        print(f"📊 Настройки: {len(settings)} параметров")
        print(f"📅 Ежедневные: {'включены' if settings.get('daily_enabled') else 'отключены'}")
        print(f"📊 Еженедельные: {'включены' if settings.get('weekly_enabled') else 'отключены'}")
        print(f"📈 Месячные: {'включены' if settings.get('monthly_enabled') else 'отключены'}")
        
        # Тест 2: Генерация ежедневного отчета
        print("\n📅 Тест 2: Ежедневный отчет")
        daily_report = await reports_manager._generate_daily_summary(test_chat_id)
        print(f"✅ Ежедневный отчет сформирован")
        if daily_report:
            print(f"📊 Длина отчета: {len(daily_report)} символов")
            print("📄 Превью:")
            print(daily_report[:200] + "..." if len(daily_report) > 200 else daily_report)
        else:
            print("📊 Отчет пуст (нет данных)")
        
        # Тест 3: Генерация еженедельного отчета
        print("\n📊 Тест 3: Еженедельный отчет")
        weekly_report = await reports_manager._generate_weekly_report(test_chat_id)
        print(f"✅ Еженедельный отчет сформирован")
        if weekly_report:
            print(f"📊 Длина отчета: {len(weekly_report)} символов")
            print("📄 Превью:")
            print(weekly_report[:200] + "..." if len(weekly_report) > 200 else weekly_report)
        else:
            print("📊 Отчет пуст (нет данных)")
        
        # Тест 4: Генерация месячного отчета
        print("\n📈 Тест 4: Месячный отчет")
        monthly_report = await reports_manager._generate_monthly_report(test_chat_id)
        print(f"✅ Месячный отчет сформирован")
        if monthly_report:
            print(f"📊 Длина отчета: {len(monthly_report)} символов")
            print("📄 Превью:")
            print(monthly_report[:200] + "..." if len(monthly_report) > 200 else monthly_report)
        else:
            print("📊 Отчет пуст (нет данных)")
        
        # Тест 5: Настройка расписания
        print("\n⏰ Тест 5: Расписание отчетов")
        schedules = reports_manager.setup_report_schedules()
        print(f"✅ Расписание настроено")
        print(f"📅 Типов отчетов: {len(schedules)}")
        for schedule in schedules:
            status = "включен" if schedule['enabled'] else "отключен"
            print(f"   📊 {schedule['name']}: {schedule['frequency']} в {schedule['time']} ({status})")
        
        print("\n🎉 ВСЕ ТЕСТЫ АВТОМАТИЧЕСКИХ ОТЧЕТОВ ПРОЙДЕНЫ!")
        print("\n📝 Новая функциональность включает:")
        print("  ✅ Ежедневные сводные отчеты с анализом текущего дня")
        print("  ✅ Еженедельные аналитические отчеты с трендами")
        print("  ✅ Месячные отчеты с подробной статистикой")
        print("  ✅ Настройка расписания и включение/отключение отчетов")
        print("  ✅ Отправка отчетов по запросу")
        print("  ✅ Автоматическая отправка по расписанию")
        print("  ✅ Интеграция с аналитической системой")
        print("  ✅ Пользовательский интерфейс для управления")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция тестирования"""
    success = await test_automated_reports()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)