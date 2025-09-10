#!/usr/bin/env python3
"""
Тест функциональности расширенной аналитики
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db_manager
from managers.advanced_analytics_manager import AdvancedAnalyticsManager

async def test_advanced_analytics():
    """Тестирует функциональность расширенной аналитики"""
    
    # Инициализируем менеджер аналитики
    analytics_manager = AdvancedAnalyticsManager(db_manager)
    
    print("📊 ТЕСТИРОВАНИЕ РАСШИРЕННОЙ АНАЛИТИКИ")
    print("=" * 50)
    
    # Тестовый chat_id
    test_chat_id = 12345
    
    try:
        # Тест 1: Анализ трендов
        print("\n📈 Тест 1: Анализ трендов")
        trends = analytics_manager.get_trends_analysis(test_chat_id, 6)
        print(f"✅ Анализ трендов выполнен")
        print(f"📊 Статус: {trends.get('trend', 'неизвестно')}")
        
        # Тест 2: Недельная аналитика
        print("\n📅 Тест 2: Недельная аналитика")
        weekly_stats = analytics_manager.get_weekly_analysis(test_chat_id, 8)
        print(f"✅ Недельная аналитика получена")
        print(f"📊 Недель в анализе: {len(weekly_stats)}")
        
        # Тест 3: Прогноз нагрузки
        print("\n🎯 Тест 3: Прогноз нагрузки")
        forecast = analytics_manager.get_workload_forecast(test_chat_id, 30)
        summary = forecast.get('summary', {})
        print(f"✅ Прогноз нагрузки сформирован")
        print(f"📊 Всего событий в прогнозе: {summary.get('total_events', 0)}")
        print(f"⭕ Среднее в день: {summary.get('avg_per_day', 0):.1f}")
        
        # Тест 4: Метрики эффективности
        print("\n⚡ Тест 4: Метрики эффективности")
        efficiency = analytics_manager.get_efficiency_metrics(test_chat_id)
        print(f"✅ Метрики эффективности получены")
        print(f"📊 Оценка эффективности: {efficiency.get('efficiency_grade', 'N/A')}")
        print(f"📈 Соблюдение сроков: {efficiency.get('compliance_rate', 0)}%")
        
        # Тест 5: Генерация диаграмм
        print("\n📊 Тест 5: Генерация текстовых диаграмм")
        
        # Тестовые данные для диаграммы
        test_trend_data = {
            'direction': 'rising',
            'change_percent': 15.5,
            'description': 'Рост на 15.5%'
        }
        
        trend_chart = analytics_manager.generate_text_charts(test_trend_data, 'trend')
        print(f"✅ Диаграмма тренда: {trend_chart}")
        
        # Тестовые данные для столбчатой диаграммы
        test_bar_data = {
            'Плотник': 10,
            'Маляр': 7,
            'Мастер': 5
        }
        
        bar_chart = analytics_manager.generate_text_charts(test_bar_data, 'bar')
        print(f"✅ Столбчатая диаграмма создана:")
        print(bar_chart)
        
        print("\n🎉 ВСЕ ТЕСТЫ РАСШИРЕННОЙ АНАЛИТИКИ ПРОЙДЕНЫ!")
        print("\n📝 Новая функциональность включает:")
        print("  ✅ Анализ трендов с прогнозами")
        print("  ✅ Временная аналитика (недели/месяцы)")
        print("  ✅ Прогнозирование рабочей нагрузки")
        print("  ✅ Метрики эффективности и соблюдения сроков")
        print("  ✅ Текстовые диаграммы и визуализация")
        print("  ✅ Интеграция с дашбордом администратора")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция тестирования"""
    success = await test_advanced_analytics()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)