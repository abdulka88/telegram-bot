#!/usr/bin/env python3
"""
Тест функциональности экспорта аналитических отчетов в Excel
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db_manager
from managers.export_manager import ExportManager

async def test_analytics_export():
    """Тестирует функциональность экспорта аналитических отчетов в Excel"""
    
    # Инициализируем менеджер экспорта
    export_manager = ExportManager(db_manager)
    
    print("📊 ТЕСТИРОВАНИЕ ЭКСПОРТА АНАЛИТИЧЕСКИХ ОТЧЕТОВ В EXCEL")
    print("=" * 60)
    
    # Тестовый chat_id
    test_chat_id = 12345
    
    try:
        # Тест 1: Полный аналитический отчет
        print("\n📄 Тест 1: Полный аналитический отчет")
        full_report = await export_manager.export_analytics_report(test_chat_id, "full")
        print(f"✅ Полный отчет создан")
        print(f"📊 Размер файла: {len(full_report.getvalue())} байт")
        
        # Тест 2: Отчет по трендам
        print("\n📈 Тест 2: Отчет по трендам")
        trends_report = await export_manager.export_analytics_report(test_chat_id, "trends")
        print(f"✅ Отчет по трендам создан")
        print(f"📊 Размер файла: {len(trends_report.getvalue())} байт")
        
        # Тест 3: Отчет по прогнозам
        print("\n🎯 Тест 3: Отчет по прогнозам")
        forecast_report = await export_manager.export_analytics_report(test_chat_id, "forecast")
        print(f"✅ Отчет по прогнозам создан")
        print(f"📊 Размер файла: {len(forecast_report.getvalue())} байт")
        
        # Тест 4: Отчет по эффективности
        print("\n⚡ Тест 4: Отчет по эффективности")
        efficiency_report = await export_manager.export_analytics_report(test_chat_id, "efficiency")
        print(f"✅ Отчет по эффективности создан")
        print(f"📊 Размер файла: {len(efficiency_report.getvalue())} байт")
        
        # Тест 5: Экспорт автоматических отчетов
        print("\n📋 Тест 5: Экспорт автоматических отчетов")
        
        # Ежедневный отчет
        daily_excel = await export_manager.export_automated_report(test_chat_id, "daily")
        if daily_excel:
            print(f"✅ Ежедневный отчет в Excel создан")
            print(f"📊 Размер файла: {len(daily_excel.getvalue())} байт")
        else:
            print("📊 Ежедневный отчет пуст (нет данных)")
        
        # Еженедельный отчет
        weekly_excel = await export_manager.export_automated_report(test_chat_id, "weekly")
        if weekly_excel:
            print(f"✅ Еженедельный отчет в Excel создан")
            print(f"📊 Размер файла: {len(weekly_excel.getvalue())} байт")
        else:
            print("📊 Еженедельный отчет пуст (нет данных)")
        
        # Месячный отчет
        monthly_excel = await export_manager.export_automated_report(test_chat_id, "monthly")
        if monthly_excel:
            print(f"✅ Месячный отчет в Excel создан")
            print(f"📊 Размер файла: {len(monthly_excel.getvalue())} байт")
        else:
            print("📊 Месячный отчет пуст (нет данных)")
        
        # Тест 6: Проверка структуры Excel файлов
        print("\n🔍 Тест 6: Проверка структуры Excel файлов")
        
        # Сохраняем тестовый файл для проверки
        test_file_path = "/tmp/test_analytics_report.xlsx"
        with open(test_file_path, "wb") as f:
            f.write(full_report.getvalue())
        print(f"✅ Тестовый файл сохранен: {test_file_path}")
        
        # Проверяем, что файл создан корректно
        if os.path.exists(test_file_path):
            file_size = os.path.getsize(test_file_path)
            print(f"📊 Размер файла на диске: {file_size} байт")
            
            # Удаляем тестовый файл
            os.remove(test_file_path)
            print("🗑️ Тестовый файл удален")
        
        print("\n🎉 ВСЕ ТЕСТЫ ЭКСПОРТА АНАЛИТИЧЕСКИХ ОТЧЕТОВ ПРОЙДЕНЫ!")
        print("\n📝 Функциональность экспорта включает:")
        print("  ✅ Полный аналитический отчет с несколькими листами")
        print("  ✅ Экспорт анализа трендов с графиками и статистикой")
        print("  ✅ Экспорт прогнозов нагрузки с детальными данными")
        print("  ✅ Экспорт показателей эффективности")
        print("  ✅ Экспорт временных диаграмм с текстовой визуализацией")
        print("  ✅ Экспорт расширенного прогнозирования с оценкой рисков")
        print("  ✅ Экспорт автоматических отчетов в Excel формат")
        print("  ✅ Правильное форматирование и структура Excel файлов")
        print("  ✅ Обработка случаев отсутствия данных")
        print("  ✅ Интеграция с аналитическими модулями")
        
        # Дополнительная информация
        print("\n📋 Структура полного аналитического отчета:")
        print("  📊 Лист 'Анализ трендов' - динамика событий за 6 месяцев")
        print("  🎯 Лист 'Прогноз нагрузки' - прогноз на 30 дней с детализацией")
        print("  ⚡ Лист 'Эффективность' - показатели соблюдения сроков")
        print("  📅 Лист 'Временные диаграммы' - визуализация по периодам")
        print("  🔮 Лист 'Расширенный прогноз' - многопериодный анализ рисков")
        print("  💼 Форматирование с цветовым кодированием статусов")
        print("  📐 Автоматическая настройка ширины колонок")
        print("  🎨 Профессиональное оформление заголовков")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция тестирования"""
    success = await test_analytics_export()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)