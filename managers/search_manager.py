"""
Менеджер поиска и фильтрации для Telegram бота управления периодическими событиями
"""

import logging
from typing import List, Dict, Optional
from core.security import decrypt_data

logger = logging.getLogger(__name__)

class SearchManager:
    """Менеджер поиска и фильтрации событий"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def search_events(self, chat_id: int, query: str, filters: Dict = None, page: int = 0, per_page: int = 10) -> Dict:
        """
        Универсальный поиск по событиям с пагинацией
        
        Args:
            chat_id: ID чата
            query: Поисковый запрос
            filters: Дополнительные фильтры
            page: Номер страницы (начиная с 0)
            per_page: Количество результатов на страницу
            
        Returns:
            Словарь с результатами и метаинформацией
        """
        base_query = '''
            SELECT 
                e.id as employee_id,
                e.full_name,
                e.position,
                ee.id as event_id,
                ee.event_type,
                ee.next_notification_date,
                ee.interval_days,
                (julianday(ee.next_notification_date) - julianday('now')) as days_until
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
        '''
        
        params = [chat_id]
        conditions = []
        
        # Текстовый поиск
        if query and query.strip():
            search_condition = '''
                (LOWER(e.full_name) LIKE LOWER(?) OR 
                 LOWER(e.position) LIKE LOWER(?) OR 
                 LOWER(ee.event_type) LIKE LOWER(?))
            '''
            conditions.append(search_condition)
            search_term = f"%{query.strip()}%"
            params.extend([search_term, search_term, search_term])
        
        # Фильтры
        if filters:
            if filters.get('status'):
                status = filters['status']
                if status == 'overdue':
                    conditions.append("date(ee.next_notification_date) < date('now')")
                elif status == 'urgent':
                    conditions.append("date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+7 days')")
                elif status == 'upcoming':
                    conditions.append("date(ee.next_notification_date) BETWEEN date('now', '+8 days') AND date('now', '+30 days')")
            
            if filters.get('event_type'):
                conditions.append("ee.event_type = ?")
                params.append(filters['event_type'])
            
            if filters.get('date_from'):
                conditions.append("date(ee.next_notification_date) >= date(?)")
                params.append(filters['date_from'])
            
            if filters.get('date_to'):
                conditions.append("date(ee.next_notification_date) <= date(?)")
                params.append(filters['date_to'])
        
        # Собираем финальный запрос
        if conditions:
            final_query = base_query + " AND " + " AND ".join(conditions)
        else:
            final_query = base_query
            
        final_query += " ORDER BY ee.next_notification_date"
        
        # Получаем общее количество результатов
        count_query = final_query.replace(
            "SELECT e.id as employee_id, e.full_name, e.position, ee.id as event_id, ee.event_type, ee.next_notification_date, ee.interval_days, (julianday(ee.next_notification_date) - julianday('now')) as days_until",
            "SELECT COUNT(*)"
        )
        total_results = self.db.execute_with_retry(count_query, tuple(params), fetch="one")
        total_count = total_results[0] if total_results else 0
        
        # Добавляем пагинацию
        final_query += f" LIMIT {per_page} OFFSET {page * per_page}"
        
        results = self.db.execute_with_retry(final_query, tuple(params), fetch="all")
        
        # Расшифровываем имена и добавляем статусы
        decrypted_results = []
        for result in results:
            result_dict = dict(result)
            try:
                result_dict['full_name'] = decrypt_data(result_dict['full_name'])
            except ValueError:
                result_dict['full_name'] = "Ошибка дешифрации"
            
            # Добавляем статус события
            days_until = result_dict.get('days_until', 0)
            if days_until < 0:
                result_dict['status'] = 'overdue'
                result_dict['status_emoji'] = '🔴'
                result_dict['status_text'] = f'просрочено на {abs(int(days_until))} дн.'
            elif days_until <= 3:
                result_dict['status'] = 'critical'
                result_dict['status_emoji'] = '🔴'
                result_dict['status_text'] = f'через {int(days_until)} дн. (критично!)'
            elif days_until <= 7:
                result_dict['status'] = 'urgent'
                result_dict['status_emoji'] = '🟠'
                result_dict['status_text'] = f'через {int(days_until)} дн. (срочно)'
            elif days_until <= 30:
                result_dict['status'] = 'upcoming'
                result_dict['status_emoji'] = '🟡'
                result_dict['status_text'] = f'через {int(days_until)} дн.'
            else:
                result_dict['status'] = 'planned'
                result_dict['status_emoji'] = '🟢'
                result_dict['status_text'] = f'через {int(days_until)} дн.'
                
            decrypted_results.append(result_dict)
        
        # Возвращаем результаты с метаинформацией
        return {
            'results': decrypted_results,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page,
                'has_next': (page + 1) * per_page < total_count,
                'has_prev': page > 0
            }
        }

    def get_available_event_types(self, chat_id: int) -> List[str]:
        """
        Получает список всех типов событий для фильтров
        
        Args:
            chat_id: ID чата
            
        Returns:
            Список типов событий
        """
        result = self.db.execute_with_retry('''
            SELECT DISTINCT ee.event_type 
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            ORDER BY ee.event_type
        ''', (chat_id,), fetch="all")
        
        return [row['event_type'] for row in result]
    
    def get_events_statistics(self, chat_id: int) -> Dict:
        """
        Получает статистику по событиям
        
        Args:
            chat_id: ID чата
            
        Returns:
            Словарь со статистикой
        """
        stats_query = '''
            SELECT 
                COUNT(*) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue,
                COUNT(CASE WHEN date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+3 days') THEN 1 END) as critical,
                COUNT(CASE WHEN date(ee.next_notification_date) BETWEEN date('now', '+4 days') AND date('now', '+7 days') THEN 1 END) as urgent,
                COUNT(CASE WHEN date(ee.next_notification_date) BETWEEN date('now', '+8 days') AND date('now', '+30 days') THEN 1 END) as upcoming,
                COUNT(CASE WHEN date(ee.next_notification_date) > date('now', '+30 days') THEN 1 END) as planned,
                COUNT(DISTINCT e.id) as total_employees
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
        '''
        
        result = self.db.execute_with_retry(stats_query, (chat_id,), fetch="one")
        
        if result:
            return {
                'total_events': result['total_events'],
                'total_employees': result['total_employees'],
                'overdue': result['overdue'],
                'critical': result['critical'], 
                'urgent': result['urgent'],
                'upcoming': result['upcoming'],
                'planned': result['planned']
            }
        else:
            return {
                'total_events': 0,
                'total_employees': 0,
                'overdue': 0,
                'critical': 0,
                'urgent': 0,
                'upcoming': 0,
                'planned': 0
            }
    
    def search_employees(self, chat_id: int, query: str = None) -> List[Dict]:
        """
        Поиск сотрудников
        
        Args:
            chat_id: ID чата
            query: Поисковый запрос (опционально)
            
        Returns:
            Список найденных сотрудников
        """
        base_query = '''
            SELECT id, full_name, position, user_id, created_at
            FROM employees 
            WHERE chat_id = ? AND is_active = 1
        '''
        
        params = [chat_id]
        
        if query and query.strip():
            base_query += " AND (LOWER(full_name) LIKE LOWER(?) OR LOWER(position) LIKE LOWER(?))"
            search_term = f"%{query.strip()}%"
            params.extend([search_term, search_term])
        
        base_query += " ORDER BY full_name"
        
        results = self.db.execute_with_retry(base_query, tuple(params), fetch="all")
        
        # Расшифровываем имена
        decrypted_results = []
        for result in results:
            result_dict = dict(result)
            try:
                result_dict['full_name'] = decrypt_data(result_dict['full_name'])
            except ValueError:
                result_dict['full_name'] = "Ошибка дешифрации"
            decrypted_results.append(result_dict)
        
        return decrypted_results
    
    async def smart_text_search(self, chat_id: int, query: str, additional_filters: Dict = None, page: int = 0, per_page: int = 10) -> Dict:
        """
        Умный текстовый поиск с улучшенными возможностями
        Исправленная версия для работы с зашифрованными данными
        
        Args:
            chat_id: ID чата
            query: Поисковый запрос
            additional_filters: Дополнительные фильтры
            page: Номер страницы
            per_page: Количество результатов на страницу
            
        Returns:
            Результаты поиска с дополнительной информацией
        """
        if not query or not query.strip():
            return {'results': [], 'pagination': {'total_count': 0, 'current_page': 0, 'total_pages': 0}}
        
        query = query.strip().lower()
        
        # Получаем все события (без текстового фильтра в SQL)
        base_query = '''
            SELECT 
                e.id as employee_id,
                e.full_name,
                e.position,
                ee.id as event_id,
                ee.event_type,
                ee.next_notification_date,
                ee.interval_days,
                (julianday(ee.next_notification_date) - julianday('now')) as days_until
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
        '''
        
        params = [chat_id]
        conditions = []
        
        # Дополнительные фильтры (не текстовые)
        if additional_filters:
            if additional_filters.get('status'):
                status = additional_filters['status']
                if status == 'overdue':
                    conditions.append("date(ee.next_notification_date) < date('now')")
                elif status == 'critical':
                    conditions.append("date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+3 days')")
                elif status == 'urgent':
                    conditions.append("date(ee.next_notification_date) BETWEEN date('now', '+4 days') AND date('now', '+7 days')")
                elif status == 'upcoming':
                    conditions.append("date(ee.next_notification_date) BETWEEN date('now', '+8 days') AND date('now', '+30 days')")
            
            if additional_filters.get('position'):
                conditions.append("e.position = ?")
                params.append(additional_filters['position'])
        
        # Собираем запрос
        if conditions:
            final_query = base_query + " AND " + " AND ".join(conditions)
        else:
            final_query = base_query
            
        final_query += " ORDER BY ee.next_notification_date ASC"
        
        # Получаем все результаты
        all_results = self.db.execute_with_retry(final_query, tuple(params), fetch="all")
        
        # Расшифровываем и фильтруем по тексту
        matching_results = []
        for result in all_results:
            result_dict = dict(result)
            
            try:
                # Расшифровываем имя для поиска
                decrypted_name = decrypt_data(result_dict['full_name'])
                result_dict['full_name'] = decrypted_name
                
                # Проверяем соответствие поисковому запросу
                if (query in decrypted_name.lower() or 
                    query in result_dict['position'].lower() or 
                    query in result_dict['event_type'].lower()):
                    
                    # Вычисляем релевантность
                    relevance_score = 1
                    if query in decrypted_name.lower():
                        relevance_score = 10
                    elif query in result_dict['position'].lower():
                        relevance_score = 8
                    elif query in result_dict['event_type'].lower():
                        relevance_score = 6
                    
                    result_dict['relevance_score'] = relevance_score
                    
                    # Добавляем статус
                    days_until = result_dict.get('days_until', 0)
                    if days_until < 0:
                        result_dict['status'] = 'overdue'
                        result_dict['status_emoji'] = '🔴'
                        result_dict['status_text'] = f'просрочено на {abs(int(days_until))} дн.'
                    elif days_until <= 3:
                        result_dict['status'] = 'critical'
                        result_dict['status_emoji'] = '🔴'
                        result_dict['status_text'] = f'через {int(days_until)} дн. (критично!)'
                    elif days_until <= 7:
                        result_dict['status'] = 'urgent'
                        result_dict['status_emoji'] = '🟠'
                        result_dict['status_text'] = f'через {int(days_until)} дн. (срочно)'
                    elif days_until <= 30:
                        result_dict['status'] = 'upcoming'
                        result_dict['status_emoji'] = '🟡'
                        result_dict['status_text'] = f'через {int(days_until)} дн.'
                    else:
                        result_dict['status'] = 'planned'
                        result_dict['status_emoji'] = '🟢'
                        result_dict['status_text'] = f'через {int(days_until)} дн.'
                    
                    # Подсветка совпадений
                    result_dict['match_highlights'] = self._highlight_matches(result_dict, query)
                    
                    matching_results.append(result_dict)
                    
            except ValueError:
                # Если не удалось расшифровать, пропускаем
                continue
        
        # Сортируем по релевантности
        matching_results.sort(key=lambda x: (-x['relevance_score'], x['days_until']))
        
        # Применяем пагинацию
        total_count = len(matching_results)
        start_idx = page * per_page
        end_idx = start_idx + per_page
        paginated_results = matching_results[start_idx:end_idx]
        
        return {
            'results': paginated_results,
            'query': query,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 0,
                'has_next': (page + 1) * per_page < total_count,
                'has_prev': page > 0
            },
            'search_suggestions': self._get_search_suggestions(chat_id, query)
        }
    
    def _highlight_matches(self, result: Dict, query: str) -> List[str]:
        """
        Определяет в каких полях найдены совпадения
        """
        matches = []
        query_lower = query.lower()
        
        if query_lower in result['full_name'].lower():
            matches.append('👤 ФИО')
        if query_lower in result['position'].lower():
            matches.append('💼 Должность')
        if query_lower in result['event_type'].lower():
            matches.append('📋 Событие')
        
        return matches
    
    def _get_search_suggestions(self, chat_id: int, query: str) -> List[str]:
        """
        Генерирует подсказки для поиска
        """
        suggestions = []
        
        # Получаем похожие ФИО
        similar_names = self.db.execute_with_retry('''
            SELECT DISTINCT e.full_name
            FROM employees e
            WHERE e.chat_id = ? AND e.is_active = 1
            AND LOWER(e.full_name) LIKE ?
            LIMIT 3
        ''', (chat_id, f"%{query.lower()}%"), fetch="all")
        
        for name_row in similar_names:
            try:
                decrypted = decrypt_data(name_row['full_name'])
                suggestions.append(f"👤 {decrypted}")
            except ValueError:
                pass
        
        # Получаем похожие должности
        similar_positions = self.db.execute_with_retry('''
            SELECT DISTINCT e.position
            FROM employees e
            WHERE e.chat_id = ? AND e.is_active = 1
            AND LOWER(e.position) LIKE ?
            LIMIT 2
        ''', (chat_id, f"%{query.lower()}%"), fetch="all")
        
        for pos_row in similar_positions:
            suggestions.append(f"💼 {pos_row['position']}")
        
        return suggestions[:5]
    
    def get_popular_searches(self, chat_id: int) -> List[str]:
        """
        Возвращает популярные поисковые запросы
        """
        # Получаем наиболее частые должности
        popular_positions = self.db.execute_with_retry('''
            SELECT e.position, COUNT(*) as cnt
            FROM employees e
            WHERE e.chat_id = ? AND e.is_active = 1
            GROUP BY e.position
            ORDER BY cnt DESC
            LIMIT 3
        ''', (chat_id,), fetch="all")
        
        # Получаем наиболее частые типы событий
        popular_events = self.db.execute_with_retry('''
            SELECT ee.event_type, COUNT(*) as cnt
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            GROUP BY ee.event_type
            ORDER BY cnt DESC
            LIMIT 3
        ''', (chat_id,), fetch="all")
        
        popular = []
        
        for pos in popular_positions:
            popular.append(pos['position'])
            
        for event in popular_events:
            popular.append(event['event_type'][:20])  # Обрезаем длинные названия
        
        return popular
    
    def get_employee_events(self, employee_id: int) -> List[Dict]:
        """
        Получает все события сотрудника
        
        Args:
            employee_id: ID сотрудника
            
        Returns:
            Список событий сотрудника
        """
        results = self.db.execute_with_retry('''
            SELECT id, event_type, last_event_date, next_notification_date, interval_days,
                   (julianday(next_notification_date) - julianday('now')) as days_until
            FROM employee_events 
            WHERE employee_id = ?
            ORDER BY next_notification_date
        ''', (employee_id,), fetch="all")
        
        return [dict(result) for result in results]
    
    def get_events_by_status(self, chat_id: int, status: str) -> List[Dict]:
        """
        Получает события по статусу
        
        Args:
            chat_id: ID чата
            status: Статус ('overdue', 'urgent', 'upcoming', 'planned')
            
        Returns:
            Список событий с указанным статусом
        """
        base_query = '''
            SELECT 
                e.id as employee_id,
                e.full_name,
                e.position,
                ee.id as event_id,
                ee.event_type,
                ee.next_notification_date,
                ee.interval_days,
                (julianday(ee.next_notification_date) - julianday('now')) as days_until
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
        '''
        
        params = [chat_id]
        
        # Добавляем условие статуса
        if status == 'overdue':
            base_query += " AND date(ee.next_notification_date) < date('now')"
        elif status == 'urgent':
            base_query += " AND date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+7 days')"
        elif status == 'upcoming':
            base_query += " AND date(ee.next_notification_date) BETWEEN date('now', '+8 days') AND date('now', '+30 days')"
        elif status == 'planned':
            base_query += " AND date(ee.next_notification_date) > date('now', '+30 days')"
        
        base_query += " ORDER BY ee.next_notification_date"
        
        results = self.db.execute_with_retry(base_query, tuple(params), fetch="all")
        
        # Расшифровываем имена
        decrypted_results = []
        for result in results:
            result_dict = dict(result)
            try:
                result_dict['full_name'] = decrypt_data(result_dict['full_name'])
            except ValueError:
                result_dict['full_name'] = "Ошибка дешифрации"
            decrypted_results.append(result_dict)
        
        return decrypted_results