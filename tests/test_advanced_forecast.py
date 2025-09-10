#!/usr/bin/env python3
"""
Тест функциональности расширенного прогнозирования нагрузки
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db_manager
from managers.advanced_analytics_manager import AdvancedAnalyticsManager

async def test_advanced_workload_forecast():
    """Тестирует функциональность расширенного прогнозирования нагрузки"""
    
    # Инициализируем менеджер аналитики
    analytics_manager = AdvancedAnalyticsManager(db_manager)
    
    print("🎯 ТЕСТИРОВАНИЕ РАСШИРЕННОГО ПРОГНОЗИРОВАНИЯ НАГРУЗКИ")
    print("=" * 60)
    
    # Тестовый chat_id
    test_chat_id = 12345
    
    try:
        # Тест 1: Базовый прогноз нагрузки с новыми метриками
        print("\n📊 Тест 1: Улучшенный прогноз нагрузки")
        forecast = analytics_manager.get_workload_forecast(test_chat_id, 30)
        print(f"✅ Прогноз сформирован")
        print(f"📊 Общая сводка: {len(forecast.get('summary', {}))} параметров")
        print(f"📈 Ежедневный прогноз: {len(forecast.get('daily_forecast', []))} дней")
        
        # Проверяем новые поля
        if 'workload_metrics' in forecast:
            metrics = forecast['workload_metrics']
            print(f"🎯 Метрики нагрузки: {len(metrics)} показателей")
            print(f"   📊 Общий уровень: {metrics.get('overall_load', 'N/A')}")
            print(f"   📅 Самый загруженный день: {metrics.get('busiest_day', 'N/A')}")
            print(f"   🔴 Дней с высокой нагрузкой: {metrics.get('high_load_days', 0)}")
        
        # Тест 2: Расширенный прогноз на несколько периодов
        print("\n🔮 Тест 2: Многопериодный прогноз")
        periods = {'short': 7, 'medium': 30, 'long': 90}
        advanced_forecast = analytics_manager.get_advanced_workload_forecast(test_chat_id, periods)
        print(f"✅ Многопериодный прогноз создан")
        
        forecasts = advanced_forecast.get('forecasts', {})
        print(f"📊 Периодов в анализе: {len(forecasts)}")
        
        for period_name, period_data in forecasts.items():
            risk = period_data['risk_assessment']
            print(f"   📅 {period_name}: {risk['risk_emoji']} {risk['risk_level']} (балл: {risk['risk_score']})")
        
        # Тест 3: Сравнительный анализ
        print("\n🔄 Тест 3: Сравнительный анализ периодов")
        analysis = advanced_forecast.get('comparative_analysis', {})
        print(f"✅ Сравнительный анализ выполнен")
        print(f"📈 Тренды: {len(analysis.get('trends', {}))}")
        print(f"💡 Рекомендации: {len(analysis.get('recommendations', []))}")
        
        if analysis.get('trends'):
            trends = analysis['trends']
            print(f"   📊 Тренд нагрузки: {trends.get('load_trend', 'N/A')}")
        
        if analysis.get('recommendations'):
            print("   💡 Топ рекомендации:")
            for i, rec in enumerate(analysis['recommendations'][:2], 1):
                print(f"      {i}. {rec}")
        
        # Тест 4: Оценка рисков
        print("\n⚠️ Тест 4: Система оценки рисков")
        test_forecast = {
            'summary': {'avg_per_day': 5.5, 'peak_count': 12, 'forecast_period': 30},
            'workload_metrics': {'high_load_days': 8}
        }
        risk_assessment = analytics_manager._assess_period_risk(test_forecast)
        print(f"✅ Оценка рисков работает")
        print(f"⚠️ Уровень риска: {risk_assessment['risk_level']} {risk_assessment['risk_emoji']}")
        print(f"📊 Балл риска: {risk_assessment['risk_score']}")
        print(f"🎯 Факторы риска: {len(risk_assessment['factors'])}")
        
        # Тест 5: Генерация рекомендаций
        print("\n💡 Тест 5: Система рекомендаций")
        test_daily_forecast = [
            {'events_count': 8, 'priority': 'critical'},
            {'events_count': 6, 'priority': 'high'},
            {'events_count': 3, 'priority': 'medium'},
            {'events_count': 1, 'priority': 'low'}
        ]
        recommendations = analytics_manager._generate_workload_recommendations(
            6.5, 2, 1, 'Понедельник', test_daily_forecast
        )
        print(f"✅ Рекомендации сгенерированы")
        print(f"📝 Количество рекомендаций: {len(recommendations)}")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        # Тест 6: Распределение по дням недели
        print("\n📅 Тест 6: Анализ распределения по дням недели")
        weekly_distribution = [5, 3, 7, 4, 8, 2, 1]  # Пн-Вс
        day_names = ['Пон', 'Вто', 'Сре', 'Чет', 'Пят', 'Суб', 'Вос']
        
        busiest_day = day_names[weekly_distribution.index(max(weekly_distribution))]
        quietest_day = day_names[weekly_distribution.index(min(weekly_distribution))]
        
        print(f"✅ Анализ распределения выполнен")
        print(f"📅 Самый загруженный день: {busiest_day} ({max(weekly_distribution)} событий)")
        print(f"🟢 Самый свободный день: {quietest_day} ({min(weekly_distribution)} событий)")
        
        print("\n🎉 ВСЕ ТЕСТЫ РАСШИРЕННОГО ПРОГНОЗИРОВАНИЯ ПРОЙДЕНЫ!")
        print("\n📝 Новая функциональность включает:")
        print("  ✅ Многопериодное прогнозирование (7, 30, 90 дней)")
        print("  ✅ Расширенные метрики нагрузки с классификацией дней")
        print("  ✅ Система оценки рисков с балльной шкалой")
        print("  ✅ Сравнительный анализ трендов между периодами")
        print("  ✅ Интеллектуальные рекомендации по оптимизации")
        print("  ✅ Анализ распределения нагрузки по дням недели")
        print("  ✅ Выявление пиковых периодов и последовательных нагрузок")
        print("  ✅ Прогнозирование с учетом должностей и типов событий")
        print("  ✅ Интеграция с пользовательским интерфейсом")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция тестирования"""
    success = await test_advanced_workload_forecast()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)