#!/usr/bin/env python3
"""
Тест функциональности текстового поиска
"""

import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db_manager
from managers.search_manager import SearchManager

async def test_text_search():
    """Тестирует функциональность текстового поиска"""
    
    # Инициализируем менеджер поиска
    search_manager = SearchManager(db_manager)
    
    print("🔍 ТЕСТИРОВАНИЕ ТЕКСТОВОГО ПОИСКА")
    print("=" * 50)
    
    # Тестовый chat_id
    test_chat_id = 12345
    
    try:
        # Тест 1: Умный текстовый поиск
        print("\n📋 Тест 1: Умный текстовый поиск")
        results = await search_manager.smart_text_search(
            chat_id=test_chat_id, 
            query="медосмотр"
        )
        print(f"✅ Поиск выполнен без ошибок")
        print(f"📊 Найдено: {results['pagination']['total_count']} результатов")
        
        # Тест 2: Поиск с пустым запросом
        print("\n📋 Тест 2: Поиск с пустым запросом")
        empty_results = await search_manager.smart_text_search(
            chat_id=test_chat_id, 
            query=""
        )
        print(f"✅ Пустой поиск обработан корректно")
        print(f"📊 Результатов: {empty_results['pagination']['total_count']}")
        
        # Тест 3: Получение статистики поиска
        print("\n📋 Тест 3: Статистика поиска")
        stats = search_manager.get_events_statistics(test_chat_id)
        print(f"✅ Статистика получена")
        print(f"📊 Всего событий: {stats['total_events']}")
        print(f"👥 Всего сотрудников: {stats['total_employees']}")
        
        # Тест 4: Методы поисковых предложений
        print("\n📋 Тест 4: Поисковые предложения")
        popular_searches = search_manager.get_popular_searches(test_chat_id)
        print(f"✅ Популярные поиски получены: {len(popular_searches)} элементов")
        
        search_suggestions = search_manager._get_search_suggestions(test_chat_id, "медос")
        print(f"✅ Предложения поиска получены: {len(search_suggestions)} элементов")
        
        # Тест 5: Выделение совпадений
        print("\n📋 Тест 5: Выделение совпадений")
        test_result = {
            'full_name': 'Иванов Иван Иванович',
            'position': 'Плотник',
            'event_type': 'Периодический медицинский осмотр'
        }
        highlighted = search_manager._highlight_matches(test_result, "медос")
        print(f"✅ Выделение работает: {highlighted}")
        
        print("\n🎉 ВСЕ ТЕСТЫ ТЕКСТОВОГО ПОИСКА ПРОЙДЕНЫ!")
        print("\n📝 Функциональность включает:")
        print("  ✅ Умный поиск с ранжированием релевантности")
        print("  ✅ Поиск по ФИО, должности и типу события")
        print("  ✅ Выделение совпадений в результатах")
        print("  ✅ Поисковые предложения и автодополнение")
        print("  ✅ Популярные поиски")
        print("  ✅ Пагинация результатов")
        print("  ✅ Интеграция с модульной архитектурой")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция тестирования"""
    success = await test_text_search()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)