"""
Менеджер дашборда для аналитики и визуализации данных
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import Counter, defaultdict
from core.security import decrypt_data

logger = logging.getLogger(__name__)

class DashboardManager:
    """Менеджер дашборда с аналитикой и визуализацией"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_overview_statistics(self, chat_id: int) -> Dict:
        """
        Получает общую статистику для главной страницы дашборда
        
        Args:
            chat_id: ID чата
            
        Returns:
            Словарь с общей статистикой
        """
        # Основная статистика
        main_stats = self.db.execute_with_retry('''
            SELECT 
                COUNT(DISTINCT e.id) as total_employees,
                COUNT(ee.id) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue,
                COUNT(CASE WHEN date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+3 days') THEN 1 END) as critical,
                COUNT(CASE WHEN date(ee.next_notification_date) BETWEEN date('now', '+4 days') AND date('now', '+7 days') THEN 1 END) as urgent,
                COUNT(CASE WHEN date(ee.next_notification_date) BETWEEN date('now', '+8 days') AND date('now', '+30 days') THEN 1 END) as upcoming,
                COUNT(CASE WHEN date(ee.next_notification_date) > date('now', '+30 days') THEN 1 END) as planned
            FROM employees e
            LEFT JOIN employee_events ee ON e.id = ee.employee_id
            WHERE e.chat_id = ? AND e.is_active = 1
        ''', (chat_id,), fetch="one")
        
        # Статистика по должностям
        positions_stats = self.db.execute_with_retry('''
            SELECT 
                e.position,
                COUNT(DISTINCT e.id) as employee_count,
                COUNT(ee.id) as event_count,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_count
            FROM employees e
            LEFT JOIN employee_events ee ON e.id = ee.employee_id
            WHERE e.chat_id = ? AND e.is_active = 1
            GROUP BY e.position
            ORDER BY overdue_count DESC, event_count DESC
        ''', (chat_id,), fetch="all")
        
        # Статистика по типам событий
        event_types_stats = self.db.execute_with_retry('''
            SELECT 
                ee.event_type,
                COUNT(*) as count,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_count,
                AVG(ee.interval_days) as avg_interval
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            GROUP BY ee.event_type
            ORDER BY overdue_count DESC, count DESC
        ''', (chat_id,), fetch="all")
        
        return {
            'main': dict(main_stats) if main_stats else {},
            'positions': [dict(row) for row in positions_stats] if positions_stats else [],
            'event_types': [dict(row) for row in event_types_stats] if event_types_stats else []
        }
    
    def get_timeline_analysis(self, chat_id: int, months: int = 12) -> Dict:
        """
        Анализ событий по времени (помесячно)
        
        Args:
            chat_id: ID чата
            months: Количество месяцев для анализа
            
        Returns:
            Временной анализ событий
        """
        # Получаем события за указанный период
        timeline_data = self.db.execute_with_retry('''
            SELECT 
                strftime('%Y-%m', ee.next_notification_date) as month,
                COUNT(*) as events_count,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_count,
                ee.event_type
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) >= date('now', '-{} months')
            AND date(ee.next_notification_date) <= date('now', '+{} months')
            GROUP BY strftime('%Y-%m', ee.next_notification_date), ee.event_type
            ORDER BY month
        '''.format(months // 2, months // 2), (chat_id,), fetch="all")
        
        # Группируем данные по месяцам
        monthly_stats = defaultdict(lambda: {'total': 0, 'overdue': 0, 'types': Counter()})
        
        for row in timeline_data:
            month = row['month']
            monthly_stats[month]['total'] += row['events_count']
            monthly_stats[month]['overdue'] += row['overdue_count']
            monthly_stats[month]['types'][row['event_type']] += row['events_count']
        
        return dict(monthly_stats)
    
    def get_employee_analysis(self, chat_id: int) -> List[Dict]:
        """
        Анализ по сотрудникам - кто требует больше внимания
        
        Args:
            chat_id: ID чата
            
        Returns:
            Анализ сотрудников
        """
        employee_stats = self.db.execute_with_retry('''
            SELECT 
                e.id,
                e.full_name,
                e.position,
                COUNT(ee.id) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_events,
                COUNT(CASE WHEN date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+7 days') THEN 1 END) as urgent_events,
                MIN(julianday(ee.next_notification_date) - julianday('now')) as days_to_next_event
            FROM employees e
            LEFT JOIN employee_events ee ON e.id = ee.employee_id
            WHERE e.chat_id = ? AND e.is_active = 1
            GROUP BY e.id, e.full_name, e.position
            ORDER BY overdue_events DESC, urgent_events DESC, days_to_next_event ASC
        ''', (chat_id,), fetch="all")
        
        # Расшифровываем имена и добавляем категории риска
        processed_employees = []
        for row in employee_stats:
            employee = dict(row)
            try:
                employee['full_name'] = decrypt_data(employee['full_name'])
            except ValueError:
                employee['full_name'] = "Ошибка дешифрации"
            
            # Определяем уровень риска
            overdue = employee['overdue_events']
            urgent = employee['urgent_events']
            
            if overdue > 0:
                employee['risk_level'] = 'critical'
                employee['risk_emoji'] = '🔴'
                employee['risk_text'] = f"{overdue} просрочено"
            elif urgent > 0:
                employee['risk_level'] = 'urgent'
                employee['risk_emoji'] = '🟠'
                employee['risk_text'] = f"{urgent} срочных"
            elif employee['days_to_next_event'] and employee['days_to_next_event'] <= 30:
                employee['risk_level'] = 'attention'
                employee['risk_emoji'] = '🟡'
                employee['risk_text'] = f"события через {int(employee['days_to_next_event'])} дн."
            else:
                employee['risk_level'] = 'ok'
                employee['risk_emoji'] = '🟢'
                employee['risk_text'] = "под контролем"
            
            processed_employees.append(employee)
        
        return processed_employees
    
    def get_performance_metrics(self, chat_id: int) -> Dict:
        """
        Метрики производительности системы
        
        Args:
            chat_id: ID чата
            
        Returns:
            Метрики производительности
        """
        # Общие метрики
        metrics = self.db.execute_with_retry('''
            SELECT 
                COUNT(DISTINCT e.id) as active_employees,
                COUNT(ee.id) as total_events,
                AVG(ee.interval_days) as avg_interval,
                MIN(date(ee.next_notification_date)) as earliest_event,
                MAX(date(ee.next_notification_date)) as latest_event
            FROM employees e
            LEFT JOIN employee_events ee ON e.id = ee.employee_id
            WHERE e.chat_id = ? AND e.is_active = 1
        ''', (chat_id,), fetch="one")
        
        # Метрики просрочек
        overdue_metrics = self.db.execute_with_retry('''
            SELECT 
                COUNT(*) as total_overdue,
                AVG(julianday('now') - julianday(ee.next_notification_date)) as avg_overdue_days,
                MAX(julianday('now') - julianday(ee.next_notification_date)) as max_overdue_days
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) < date('now')
        ''', (chat_id,), fetch="one")
        
        # Вычисляем процент соблюдения
        total_events = metrics['total_events'] if metrics else 0
        overdue_count = overdue_metrics['total_overdue'] if overdue_metrics else 0
        
        compliance_rate = 0 if total_events == 0 else ((total_events - overdue_count) / total_events) * 100
        
        return {
            'general': dict(metrics) if metrics else {},
            'overdue': dict(overdue_metrics) if overdue_metrics else {},
            'compliance_rate': round(compliance_rate, 1),
            'total_events': total_events,
            'overdue_count': overdue_count
        }
    
    def generate_text_chart(self, data: Dict, chart_type: str = "bar", max_width: int = 20) -> str:
        """
        Генерирует текстовую диаграмму для Telegram
        
        Args:
            data: Данные для диаграммы {название: значение}
            chart_type: Тип диаграммы ("bar", "progress")
            max_width: Максимальная ширина диаграммы
            
        Returns:
            Строка с текстовой диаграммой
        """
        if not data:
            return "📊 Нет данных для отображения"
        
        max_value = max(data.values()) if data.values() else 1
        lines = []
        
        if chart_type == "bar":
            for name, value in data.items():
                bar_length = int((value / max_value) * max_width)
                bar = "█" * bar_length + "░" * (max_width - bar_length)
                lines.append(f"{name[:15]:15} │{bar}│ {value}")
        
        elif chart_type == "progress":
            for name, value in data.items():
                percentage = (value / max_value) * 100
                bar_length = int((percentage / 100) * max_width)
                bar = "🟢" * bar_length + "⚪" * (max_width - bar_length)
                lines.append(f"{name[:15]:15} {bar} {percentage:.1f}%")
        
        return "\n".join(lines)
    
    def generate_trend_indicator(self, current: int, previous: int) -> str:
        """
        Генерирует индикатор тренда
        
        Args:
            current: Текущее значение
            previous: Предыдущее значение
            
        Returns:
            Строка с индикатором тренда
        """
        if previous == 0:
            return "🆕 новое"
        
        change = ((current - previous) / previous) * 100
        
        if change > 10:
            return f"📈 +{change:.1f}%"
        elif change < -10:
            return f"📉 {change:.1f}%"
        elif change > 0:
            return f"↗️ +{change:.1f}%"
        elif change < 0:
            return f"↘️ {change:.1f}%"
        else:
            return "➡️ стабильно"
    
    def get_alerts_and_recommendations(self, chat_id: int) -> List[Dict]:
        """
        Генерирует предупреждения и рекомендации
        
        Args:
            chat_id: ID чата
            
        Returns:
            Список предупреждений и рекомендаций
        """
        alerts = []
        
        # Проверяем критические просрочки
        critical_overdue = self.db.execute_with_retry('''
            SELECT COUNT(*) as count
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND julianday('now') - julianday(ee.next_notification_date) > 30
        ''', (chat_id,), fetch="one")
        
        if critical_overdue and critical_overdue['count'] > 0:
            alerts.append({
                'level': 'critical',
                'emoji': '🚨',
                'title': 'Критические просрочки',
                'message': f"Найдено {critical_overdue['count']} событий с просрочкой более 30 дней",
                'action': 'Требуется немедленное внимание!'
            })
        
        # Проверяем сотрудников с множественными просрочками  
        multiple_overdue = self.db.execute_with_retry('''
            SELECT e.full_name, COUNT(*) as overdue_count
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) < date('now')
            GROUP BY e.id, e.full_name
            HAVING COUNT(*) >= 3
        ''', (chat_id,), fetch="all")
        
        if multiple_overdue:
            for emp in multiple_overdue[:3]:  # Показываем топ-3
                try:
                    name = decrypt_data(emp['full_name'])
                except ValueError:
                    name = "Сотрудник"
                
                alerts.append({
                    'level': 'warning',
                    'emoji': '⚠️',
                    'title': 'Множественные просрочки',
                    'message': f"{name}: {emp['overdue_count']} просроченных событий",
                    'action': 'Рекомендуется индивидуальная работа'
                })
        
        # Проверяем загруженность на ближайшую неделю
        upcoming_week = self.db.execute_with_retry('''
            SELECT COUNT(*) as count
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+7 days')
        ''', (chat_id,), fetch="one")
        
        if upcoming_week and upcoming_week['count'] > 10:
            alerts.append({
                'level': 'info',
                'emoji': '📅',
                'title': 'Высокая загруженность',
                'message': f"На следующую неделю запланировано {upcoming_week['count']} событий",
                'action': 'Рекомендуется заблаговременная подготовка'
            })
        
        return alerts