"""
Расширенный модуль аналитики для Telegram бота
Включает тренды, прогнозы и детальную аналитику событий
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
import statistics
from core.security import decrypt_data

logger = logging.getLogger(__name__)

class AdvancedAnalyticsManager:
    """Менеджер расширенной аналитики с трендами и прогнозами"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_trends_analysis(self, chat_id: int, period_months: int = 6) -> Dict:
        """
        Анализ трендов событий за указанный период
        
        Args:
            chat_id: ID чата
            period_months: Количество месяцев для анализа
            
        Returns:
            Словарь с трендовой аналитикой
        """
        # Получаем данные по месяцам для трендового анализа
        monthly_data = self.db.execute_with_retry('''
            SELECT 
                strftime('%Y-%m', ee.next_notification_date) as month,
                COUNT(*) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_events,
                COUNT(CASE WHEN ee.event_type LIKE '%медосмотр%' OR ee.event_type LIKE '%медицинский%' THEN 1 END) as medical_events,
                COUNT(CASE WHEN ee.event_type LIKE '%инструктаж%' OR ee.event_type LIKE '%обучение%' THEN 1 END) as training_events,
                AVG(ee.interval_days) as avg_interval
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) >= date('now', '-{} months')
            AND date(ee.next_notification_date) <= date('now', '+{} months')
            GROUP BY strftime('%Y-%m', ee.next_notification_date)
            ORDER BY month
        '''.format(period_months, period_months), (chat_id,), fetch="all")
        
        if not monthly_data:
            return {'trend': 'no_data', 'monthly_stats': [], 'predictions': {}}
        
        # Обрабатываем данные
        monthly_stats = []
        total_events_trend = []
        overdue_trend = []
        
        for row in monthly_data:
            month_data = dict(row)
            monthly_stats.append(month_data)
            total_events_trend.append(month_data['total_events'])
            overdue_trend.append(month_data['overdue_events'])
        
        # Вычисляем тренды
        trend_analysis = {
            'total_events_trend': self._calculate_trend(total_events_trend),
            'overdue_trend': self._calculate_trend(overdue_trend),
            'monthly_stats': monthly_stats,
            'period_summary': {
                'total_months': len(monthly_stats),
                'avg_events_per_month': sum(total_events_trend) / len(total_events_trend) if total_events_trend else 0,
                'max_events_month': max(total_events_trend) if total_events_trend else 0,
                'min_events_month': min(total_events_trend) if total_events_trend else 0,
                'total_overdue': sum(overdue_trend) if overdue_trend else 0
            }
        }
        
        # Добавляем прогнозы
        trend_analysis['predictions'] = self._generate_predictions(total_events_trend, overdue_trend)
        
        return trend_analysis
    
    def _calculate_trend(self, data_points: List[int]) -> Dict:
        """Вычисляет тренд для набора данных"""
        if len(data_points) < 2:
            return {'direction': 'stable', 'change_percent': 0, 'description': 'Недостаточно данных'}
        
        # Простой линейный тренд
        first_half = data_points[:len(data_points)//2]
        second_half = data_points[len(data_points)//2:]
        
        if not first_half or not second_half:
            return {'direction': 'stable', 'change_percent': 0, 'description': 'Недостаточно данных'}
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        if avg_first == 0:
            change_percent = 0
        else:
            change_percent = ((avg_second - avg_first) / avg_first) * 100
        
        # Определяем направление тренда
        if change_percent > 10:
            direction = 'rising'
            description = f'Рост на {change_percent:.1f}%'
        elif change_percent < -10:
            direction = 'falling'
            description = f'Снижение на {abs(change_percent):.1f}%'
        else:
            direction = 'stable'
            description = 'Стабильно'
        
        return {
            'direction': direction,
            'change_percent': round(change_percent, 1),
            'description': description
        }
    
    def _generate_predictions(self, events_trend: List[int], overdue_trend: List[int]) -> Dict:
        """Генерирует простые прогнозы на основе трендов"""
        predictions = {}
        
        if len(events_trend) >= 3:
            # Простое прогнозирование на основе средних значений
            recent_avg = sum(events_trend[-3:]) / 3
            overall_avg = sum(events_trend) / len(events_trend)
            
            predictions['next_month_events'] = {
                'estimate': int(recent_avg),
                'confidence': 'средняя' if abs(recent_avg - overall_avg) < overall_avg * 0.2 else 'низкая'
            }
        
        if len(overdue_trend) >= 3:
            recent_overdue_avg = sum(overdue_trend[-3:]) / 3
            predictions['next_month_overdue'] = {
                'estimate': int(recent_overdue_avg),
                'risk_level': 'высокий' if recent_overdue_avg > 5 else 'средний' if recent_overdue_avg > 2 else 'низкий'
            }
        
        return predictions
    
    def get_weekly_analysis(self, chat_id: int, weeks: int = 8) -> Dict:
        """
        Недельный анализ событий
        
        Args:
            chat_id: ID чата
            weeks: Количество недель для анализа
            
        Returns:
            Недельная аналитика
        """
        weekly_data = self.db.execute_with_retry('''
            SELECT 
                strftime('%Y-W%W', ee.next_notification_date) as week,
                strftime('%w', ee.next_notification_date) as day_of_week,
                COUNT(*) as events_count,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_count
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) >= date('now', '-{} days')
            AND date(ee.next_notification_date) <= date('now', '+{} days')
            GROUP BY strftime('%Y-W%W', ee.next_notification_date), strftime('%w', ee.next_notification_date)
            ORDER BY week, day_of_week
        '''.format(weeks * 7, weeks * 7), (chat_id,), fetch="all")
        
        # Группируем по неделям
        weekly_stats = defaultdict(lambda: {'total': 0, 'overdue': 0, 'days': defaultdict(int)})
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        
        for row in weekly_data:
            week = row['week']
            day_num = int(row['day_of_week'])
            # Корректируем воскресенье (0) в понедельник (0)
            day_index = (day_num + 6) % 7
            
            weekly_stats[week]['total'] += row['events_count']
            weekly_stats[week]['overdue'] += row['overdue_count']
            weekly_stats[week]['days'][day_names[day_index]] += row['events_count']
        
        return dict(weekly_stats)
    
    def get_workload_forecast(self, chat_id: int, forecast_days: int = 30) -> Dict:
        """
        Прогноз рабочей нагрузки на указанное количество дней
        
        Args:
            chat_id: ID чата
            forecast_days: Количество дней для прогноза
            
        Returns:
            Прогноз нагрузки
        """
        # Получаем предстоящие события
        upcoming_events = self.db.execute_with_retry('''
            SELECT 
                date(ee.next_notification_date) as event_date,
                COUNT(*) as events_count,
                GROUP_CONCAT(ee.event_type, ', ') as event_types,
                GROUP_CONCAT(e.position, ', ') as positions
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) BETWEEN date('now') AND date('now', '+{} days')
            GROUP BY date(ee.next_notification_date)
            ORDER BY event_date
        '''.format(forecast_days), (chat_id,), fetch="all")
        
        # Анализируем загрузку по дням
        daily_forecast = []
        total_events = 0
        peak_day = None
        peak_count = 0
        weekly_distribution = [0] * 7  # По дням недели
        monthly_projection = {}
        
        for row in upcoming_events:
            day_data = dict(row)
            total_events += day_data['events_count']
            
            if day_data['events_count'] > peak_count:
                peak_count = day_data['events_count']
                peak_day = day_data['event_date']
            
            # Определяем уровень загрузки
            if day_data['events_count'] >= 10:
                day_data['load_level'] = 'высокая'
                day_data['load_emoji'] = '🔴'
                day_data['priority'] = 'critical'
            elif day_data['events_count'] >= 5:
                day_data['load_level'] = 'средняя'
                day_data['load_emoji'] = '🟡'
                day_data['priority'] = 'high'
            elif day_data['events_count'] >= 3:
                day_data['load_level'] = 'умеренная'
                day_data['load_emoji'] = '🟠'
                day_data['priority'] = 'medium'
            else:
                day_data['load_level'] = 'низкая'
                day_data['load_emoji'] = '🟢'
                day_data['priority'] = 'low'
            
            # Анализ по дням недели
            from datetime import datetime
            event_date_obj = datetime.strptime(day_data['event_date'], '%Y-%m-%d')
            weekday = event_date_obj.weekday()
            weekly_distribution[weekday] += day_data['events_count']
            
            # Месячная проекция
            month_key = event_date_obj.strftime('%Y-%m')
            if month_key not in monthly_projection:
                monthly_projection[month_key] = {'events': 0, 'days': set()}
            monthly_projection[month_key]['events'] += day_data['events_count']
            monthly_projection[month_key]['days'].add(day_data['event_date'])
            
            daily_forecast.append(day_data)
        
        # Расчет дополнительных метрик
        workload_metrics = self._calculate_workload_metrics(
            daily_forecast, weekly_distribution, monthly_projection, forecast_days
        )
        
        return {
            'daily_forecast': daily_forecast,
            'summary': {
                'total_events': total_events,
                'avg_per_day': total_events / forecast_days if forecast_days > 0 else 0,
                'peak_day': peak_day,
                'peak_count': peak_count,
                'forecast_period': forecast_days
            },
            'weekly_distribution': weekly_distribution,
            'monthly_projection': monthly_projection,
            'workload_metrics': workload_metrics
        }
    
    def get_efficiency_metrics(self, chat_id: int) -> Dict:
        """
        Метрики эффективности работы с событиями
        
        Args:
            chat_id: ID чата
            
        Returns:
            Метрики эффективности
        """
        # Анализ соблюдения сроков
        compliance_data = self.db.execute_with_retry('''
            SELECT 
                COUNT(*) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) >= date('now') THEN 1 END) as on_time_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_events,
                AVG(CASE WHEN date(ee.next_notification_date) < date('now') 
                    THEN julianday('now') - julianday(ee.next_notification_date) 
                    ELSE 0 END) as avg_overdue_days
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
        ''', (chat_id,), fetch="one")
        
        if not compliance_data or compliance_data['total_events'] == 0:
            return {'compliance_rate': 0, 'efficiency_grade': 'N/A', 'recommendations': []}
        
        # Вычисляем показатели
        total = compliance_data['total_events']
        on_time = compliance_data['on_time_events']
        overdue = compliance_data['overdue_events']
        
        compliance_rate = (on_time / total) * 100 if total > 0 else 0
        avg_overdue = compliance_data['avg_overdue_days'] or 0
        
        # Определяем оценку эффективности
        if compliance_rate >= 95 and avg_overdue <= 1:
            efficiency_grade = 'Отлично'
            efficiency_emoji = '🟢'
        elif compliance_rate >= 85 and avg_overdue <= 3:
            efficiency_grade = 'Хорошо'
            efficiency_emoji = '🟡'
        elif compliance_rate >= 70:
            efficiency_grade = 'Удовлетворительно'
            efficiency_emoji = '🟠'
        else:
            efficiency_grade = 'Требует улучшения'
            efficiency_emoji = '🔴'
        
        # Генерируем рекомендации
        recommendations = []
        if compliance_rate < 90:
            recommendations.append("📈 Увеличить частоту уведомлений")
        if overdue > total * 0.1:
            recommendations.append("⚠️ Проверить настройки уведомлений")
        if avg_overdue > 5:
            recommendations.append("🔔 Добавить дополнительные напоминания")
        
        return {
            'compliance_rate': round(compliance_rate, 1),
            'efficiency_grade': efficiency_grade,
            'efficiency_emoji': efficiency_emoji,
            'total_events': total,
            'on_time_events': on_time,
            'overdue_events': overdue,
            'avg_overdue_days': round(avg_overdue, 1),
            'recommendations': recommendations
        }
    
    def generate_text_charts(self, data: Dict, chart_type: str = "trend") -> str:
        """
        Генерирует текстовые диаграммы для Telegram
        
        Args:
            data: Данные для диаграммы
            chart_type: Тип диаграммы (trend, bar, line)
            
        Returns:
            Строка с текстовой диаграммой
        """
        if not data:
            return "📊 Нет данных для отображения"
        
        if chart_type == "trend":
            return self._generate_trend_chart(data)
        elif chart_type == "bar":
            return self._generate_bar_chart(data)
        elif chart_type == "timeline":
            return self._generate_timeline_chart(data)
        
        return "📊 Неподдерживаемый тип диаграммы"
    
    def _generate_trend_chart(self, trend_data: Dict) -> str:
        """Генерирует текстовую диаграмму тренда"""
        direction = trend_data.get('direction', 'stable')
        change = trend_data.get('change_percent', 0)
        
        if direction == 'rising':
            trend_visual = "📈 ↗️↗️↗️"
        elif direction == 'falling':
            trend_visual = "📉 ↘️↘️↘️"
        else:
            trend_visual = "📊 ➡️➡️➡️"
        
        return f"{trend_visual} {change:+.1f}%"
    
    def _generate_bar_chart(self, data: Dict, max_width: int = 15) -> str:
        """Генерирует текстовую столбчатую диаграмму"""
        if not data:
            return "📊 Нет данных"
        
        max_value = max(data.values()) if data.values() else 1
        lines = []
        
        for name, value in data.items():
            bar_length = int((value / max_value) * max_width)
            bar = "█" * bar_length + "░" * (max_width - bar_length)
            lines.append(f"{name[:15]:15} │{bar}│ {value}")
        
        return "\n".join(lines)
    
    def _generate_timeline_chart(self, timeline_data: List[Dict]) -> str:
        """Генерирует временную диаграмму"""
        if not timeline_data:
            return "📊 Нет данных для временной диаграммы"
        
        lines = []
        for item in timeline_data[-7:]:  # Показываем последние 7 элементов
            date = item.get('date', 'N/A')
            count = item.get('count', 0)
            
            # Визуальное представление количества
            if count == 0:
                visual = "⚪"
            elif count <= 2:
                visual = "🟢"
            elif count <= 5:
                visual = "🟡"
            else:
                visual = "🔴"
            
            lines.append(f"{date[:10]:10} {visual} {count}")
        
        return "\n".join(lines)
    
    def get_detailed_timeline_charts(self, chat_id: int) -> Dict:
        """
        Создает детальные временные диаграммы
        Улучшенная версия для корректной работы с данными
        
        Args:
            chat_id: ID чата
            
        Returns:
            Словарь с различными временными диаграммами
        """
        # Данные для месячной диаграммы (включая будущие события)
        monthly_chart_data = self.db.execute_with_retry('''
            SELECT 
                strftime('%Y-%m', ee.next_notification_date) as month,
                COUNT(*) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_events
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) >= date('now', '-6 months')
            AND date(ee.next_notification_date) <= date('now', '+12 months')
            GROUP BY strftime('%Y-%m', ee.next_notification_date)
            ORDER BY month
        ''', (chat_id,), fetch="all")
        
        # Данные для недельной диаграммы (включая будущие события)
        weekly_chart_data = self.db.execute_with_retry('''
            SELECT 
                strftime('%Y-W%W', ee.next_notification_date) as week,
                COUNT(*) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_events
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) >= date('now', '-4 weeks')
            AND date(ee.next_notification_date) <= date('now', '+8 weeks')
            GROUP BY strftime('%Y-W%W', ee.next_notification_date)
            ORDER BY week
        ''', (chat_id,), fetch="all")
        
        # Данные для дневной диаграммы (включая будущие события)
        daily_chart_data = self.db.execute_with_retry('''
            SELECT 
                date(ee.next_notification_date) as day,
                COUNT(*) as total_events,
                COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_events
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) >= date('now', '-7 days')
            AND date(ee.next_notification_date) <= date('now', '+30 days')
            GROUP BY date(ee.next_notification_date)
            ORDER BY day
        ''', (chat_id,), fetch="all")
        
        return {
            'monthly': self._create_monthly_chart([dict(row) for row in monthly_chart_data]),
            'weekly': self._create_weekly_chart([dict(row) for row in weekly_chart_data]),
            'daily': self._create_daily_chart([dict(row) for row in daily_chart_data])
        }
    
    def _create_monthly_chart(self, monthly_data: List[Dict]) -> Dict:
        """Создает месячную диаграмму событий"""
        if not monthly_data:
            return {'chart': '📊 Нет данных за последние 12 месяцев', 'summary': {}}
        
        chart_lines = ["📅 Месячная статистика (последние 12 месяцев):"]
        chart_lines.append("")
        
        total_events = 0
        total_overdue = 0
        max_events = 0
        peak_month = ""
        
        for month_data in monthly_data[-6:]:  # Показываем последние 6 месяцев
            month = month_data['month']
            events = month_data['total_events']
            overdue = month_data['overdue_events']
            
            total_events += events
            total_overdue += overdue
            
            if events > max_events:
                max_events = events
                peak_month = month
            
            # Создаем визуальный индикатор
            if events == 0:
                bar = "⚪" * 1
            else:
                bar_length = min(10, max(1, events // 2))  # Масштабируем
                if overdue > events * 0.3:  # Более 30% просрочек
                    bar = "🔴" * bar_length
                elif overdue > 0:
                    bar = "🟡" * bar_length
                else:
                    bar = "🟢" * bar_length
            
            month_display = datetime.strptime(month, '%Y-%m').strftime('%m/%y')
            chart_lines.append(f"{month_display:5} │{bar:<10}│ {events:3} ({overdue} просроч.)")
        
        chart_lines.append("")
        chart_lines.append("Легенда: 🟢 норма, 🟡 есть просрочки, 🔴 много просрочек")
        
        summary = {
            'total_events': total_events,
            'total_overdue': total_overdue,
            'avg_per_month': total_events / len(monthly_data) if monthly_data else 0,
            'peak_month': peak_month,
            'peak_count': max_events
        }
        
        return {
            'chart': "\n".join(chart_lines),
            'summary': summary
        }
    
    def _create_weekly_chart(self, weekly_data: List[Dict]) -> Dict:
        """Создает недельную диаграмму событий"""
        if not weekly_data:
            return {'chart': '📊 Нет данных за последние 8 недель', 'summary': {}}
        
        chart_lines = ["📅 Недельная статистика (последние 8 недель):"]
        chart_lines.append("")
        
        total_events = 0
        total_overdue = 0
        max_events = 0
        peak_week = ""
        
        for week_data in weekly_data[-6:]:  # Показываем последние 6 недель
            week = week_data['week']
            events = week_data['total_events']
            overdue = week_data['overdue_events']
            
            total_events += events
            total_overdue += overdue
            
            if events > max_events:
                max_events = events
                peak_week = week
            
            # Создаем визуальный индикатор
            if events == 0:
                bar = "⚪" * 1
            else:
                bar_length = min(8, max(1, events // 3))  # Масштабируем
                if overdue > events * 0.25:  # Более 25% просрочек
                    bar = "🔴" * bar_length
                elif overdue > 0:
                    bar = "🟡" * bar_length
                else:
                    bar = "🟢" * bar_length
            
            week_display = week.replace('W', ' нед.')
            chart_lines.append(f"{week_display:12} │{bar:<8}│ {events:3} ({overdue} просроч.)")
        
        chart_lines.append("")
        chart_lines.append("Легенда: 🟢 норма, 🟡 есть просрочки, 🔴 много просрочек")
        
        summary = {
            'total_events': total_events,
            'total_overdue': total_overdue,
            'avg_per_week': total_events / len(weekly_data) if weekly_data else 0,
            'peak_week': peak_week,
            'peak_count': max_events
        }
        
        return {
            'chart': "\n".join(chart_lines),
            'summary': summary
        }
    
    def _create_daily_chart(self, daily_data: List[Dict]) -> Dict:
        """Создает дневную диаграмму событий"""
        if not daily_data:
            return {'chart': '📊 Нет данных за последние 30 дней', 'summary': {}}
        
        chart_lines = ["📅 Дневная статистика (ближайшие события):"]
        chart_lines.append("")
        
        total_events = 0
        total_overdue = 0
        max_events = 0
        peak_day = ""
        
        # Показываем только дни с событиями, но не больше 10
        days_with_events = [day for day in daily_data if day['total_events'] > 0][-10:]
        
        if not days_with_events:
            return {'chart': '📊 Нет событий в ближайшие дни', 'summary': {}}
        
        for day_data in days_with_events:
            day = day_data['day']
            events = day_data['total_events']
            overdue = day_data['overdue_events']
            
            total_events += events
            total_overdue += overdue
            
            if events > max_events:
                max_events = events
                peak_day = day
            
            # Создаем визуальный индикатор
            if events <= 1:
                bar = "🟢" * 1
            elif events <= 3:
                bar = "🟡" * min(3, events)
            else:
                bar = "🔴" * min(5, events)
            
            # Определяем статус дня
            if overdue > 0:
                status = " (просрочено!)"
            elif events >= 5:
                status = " (загружен)"
            else:
                status = ""
            
            day_obj = datetime.strptime(day, '%Y-%m-%d')
            day_display = day_obj.strftime('%d.%m (%a)')
            chart_lines.append(f"{day_display:12} │{bar:<5}│ {events} событий{status}")
        
        chart_lines.append("")
        chart_lines.append("Легенда: 🟢 1-2 события, 🟡 3-4 события, 🔴 5+ событий")
        
        summary = {
            'total_events': total_events,
            'total_overdue': total_overdue,
            'days_with_events': len(days_with_events),
            'peak_day': peak_day,
            'peak_count': max_events
        }
        
        return {
            'chart': "\n".join(chart_lines),
            'summary': summary
        }
    
    def _calculate_workload_metrics(self, daily_forecast: List[Dict], 
                                   weekly_distribution: List[int], 
                                   monthly_projection: Dict, 
                                   forecast_days: int) -> Dict:
        """
        Рассчитывает метрики рабочей нагрузки
        
        Args:
            daily_forecast: Ежедневный прогноз
            weekly_distribution: Распределение по дням недели
            monthly_projection: Месячная проекция
            forecast_days: Количество дней прогноза
            
        Returns:
            Метрики рабочей нагрузки
        """
        # Анализ распределения по дням недели
        day_names = ['Пон', 'Вто', 'Сре', 'Чет', 'Пят', 'Суб', 'Вос']
        busiest_day = day_names[weekly_distribution.index(max(weekly_distribution))] if weekly_distribution else 'Н/Д'
        quietest_day = day_names[weekly_distribution.index(min(weekly_distribution))] if weekly_distribution else 'Н/Д'
        
        # Классификация дней по уровню нагрузки
        high_load_days = len([d for d in daily_forecast if d.get('priority') == 'critical'])
        medium_load_days = len([d for d in daily_forecast if d.get('priority') in ['high', 'medium']])
        low_load_days = len([d for d in daily_forecast if d.get('priority') == 'low'])
        
        # Оценка общей нагрузки
        total_events = sum(d['events_count'] for d in daily_forecast)
        avg_load = total_events / forecast_days if forecast_days > 0 else 0
        
        if avg_load > 7:
            overall_load = 'очень высокая'
            load_status = 'critical'
        elif avg_load > 5:
            overall_load = 'высокая'
            load_status = 'high'
        elif avg_load > 3:
            overall_load = 'средняя'
            load_status = 'medium'
        else:
            overall_load = 'низкая'
            load_status = 'low'
        
        # Рекомендации
        recommendations = self._generate_workload_recommendations(
            avg_load, high_load_days, medium_load_days, busiest_day, daily_forecast
        )
        
        return {
            'overall_load': overall_load,
            'load_status': load_status,
            'avg_load': round(avg_load, 1),
            'busiest_day': busiest_day,
            'quietest_day': quietest_day,
            'high_load_days': high_load_days,
            'medium_load_days': medium_load_days,
            'low_load_days': low_load_days,
            'weekly_distribution': dict(zip(day_names, weekly_distribution)),
            'recommendations': recommendations
        }
    
    def _generate_workload_recommendations(self, avg_load: float, high_load_days: int, 
                                         medium_load_days: int, busiest_day: str,
                                         daily_forecast: List[Dict]) -> List[str]:
        """
        Генерирует рекомендации по рабочей нагрузке
        
        Returns:
            Список рекомендаций
        """
        recommendations = []
        
        if avg_load > 7:
            recommendations.append("🔴 Критическая нагрузка - рассмотрите перераспределение")
        elif avg_load > 5:
            recommendations.append("🟡 Высокая нагрузка - планируйте ресурсы")
        
        if high_load_days > 5:
            recommendations.append("⚠️ Много дней с высокой нагрузкой")
        
        if busiest_day and busiest_day != 'Н/Д':
            recommendations.append(f"📅 Особое внимание на {busiest_day}")
        
        # Проверяем последовательные дни с высокой нагрузкой
        consecutive_high = 0
        max_consecutive = 0
        for day in daily_forecast:
            if day.get('priority') in ['critical', 'high']:
                consecutive_high += 1
                max_consecutive = max(max_consecutive, consecutive_high)
            else:
                consecutive_high = 0
        
        if max_consecutive >= 3:
            recommendations.append(f"🔥 {max_consecutive} дней подряд с высокой нагрузкой")
        
        if not recommendations:
            recommendations.append("🟢 Нагрузка в норме - система под контролем")
        
        return recommendations
    
    def get_advanced_workload_forecast(self, chat_id: int, periods: Dict[str, int] = None) -> Dict:
        """
        Получает расширенный прогноз нагрузки на разные периоды
        
        Args:
            chat_id: ID чата
            periods: Словарь периодов {'short': 7, 'medium': 30, 'long': 90}
            
        Returns:
            Расширенный прогноз
        """
        if periods is None:
            periods = {'short': 7, 'medium': 30, 'long': 90}
            
        forecasts = {}
        
        for period_name, days in periods.items():
            forecast = self.get_workload_forecast(chat_id, days)
            forecasts[period_name] = {
                'days': days,
                'forecast': forecast,
                'risk_assessment': self._assess_period_risk(forecast)
            }
        
        # Сравнительный анализ
        comparative_analysis = self._compare_forecast_periods(forecasts)
        
        return {
            'forecasts': forecasts,
            'comparative_analysis': comparative_analysis,
            'generated_at': datetime.now().isoformat()
        }
    
    def _assess_period_risk(self, forecast: Dict) -> Dict:
        """
        Оценивает риски для периода прогноза
        
        Args:
            forecast: Прогноз нагрузки
            
        Returns:
            Оценка рисков
        """
        summary = forecast.get('summary', {})
        metrics = forecast.get('workload_metrics', {})
        
        avg_load = summary.get('avg_per_day', 0)
        high_load_days = metrics.get('high_load_days', 0)
        total_days = summary.get('forecast_period', 1)
        
        # Расчет уровня риска
        risk_score = 0
        
        # Коэффициент средней нагрузки
        if avg_load > 7:
            risk_score += 40
        elif avg_load > 5:
            risk_score += 25
        elif avg_load > 3:
            risk_score += 10
        
        # Коэффициент дней с высокой нагрузкой
        high_load_ratio = high_load_days / total_days if total_days > 0 else 0
        if high_load_ratio > 0.3:
            risk_score += 30
        elif high_load_ratio > 0.2:
            risk_score += 20
        elif high_load_ratio > 0.1:
            risk_score += 10
        
        # Пиковая нагрузка
        peak_count = summary.get('peak_count', 0)
        if peak_count > 15:
            risk_score += 30
        elif peak_count > 10:
            risk_score += 20
        elif peak_count > 5:
            risk_score += 10
        
        # Определение уровня риска
        if risk_score >= 80:
            risk_level = 'критический'
            risk_emoji = '🔴'
        elif risk_score >= 60:
            risk_level = 'высокий'
            risk_emoji = '🟡'
        elif risk_score >= 40:
            risk_level = 'средний'
            risk_emoji = '🟠'
        elif risk_score >= 20:
            risk_level = 'низкий'
            risk_emoji = '🟢'
        else:
            risk_level = 'минимальный'
            risk_emoji = '🟢'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_emoji': risk_emoji,
            'factors': {
                'avg_load': avg_load,
                'high_load_ratio': round(high_load_ratio * 100, 1),
                'peak_count': peak_count
            }
        }
    
    def _compare_forecast_periods(self, forecasts: Dict) -> Dict:
        """
        Сравнивает прогнозы на разные периоды
        
        Args:
            forecasts: Прогнозы на разные периоды
            
        Returns:
            Сравнительный анализ
        """
        analysis = {
            'trends': {},
            'recommendations': [],
            'summary': {}
        }
        
        # Сравнение средней нагрузки
        avg_loads = {}
        risk_levels = {}
        
        for period_name, period_data in forecasts.items():
            forecast = period_data['forecast']
            avg_loads[period_name] = forecast['summary'].get('avg_per_day', 0)
            risk_levels[period_name] = period_data['risk_assessment']['risk_level']
        
        # Определение трендов
        if len(avg_loads) >= 2:
            loads_list = list(avg_loads.values())
            if loads_list[0] < loads_list[-1]:
                analysis['trends']['load_trend'] = 'рост'
            elif loads_list[0] > loads_list[-1]:
                analysis['trends']['load_trend'] = 'снижение'
            else:
                analysis['trends']['load_trend'] = 'стабильность'
        
        # Рекомендации
        if 'критический' in risk_levels.values():
            analysis['recommendations'].append("🔴 Необходимо срочное планирование")
        elif 'высокий' in risk_levels.values():
            analysis['recommendations'].append("🟡 Рекомендуется предварительное планирование")
        
        if analysis['trends'].get('load_trend') == 'рост':
            analysis['recommendations'].append("📈 Нагрузка увеличивается - подготовьте ресурсы")
        
        analysis['summary'] = {
            'total_periods': len(forecasts),
            'highest_risk_period': max(risk_levels, key=lambda k: ['минимальный', 'низкий', 'средний', 'высокий', 'критический'].index(risk_levels[k]) if risk_levels[k] in ['минимальный', 'низкий', 'средний', 'высокий', 'критический'] else 0) if risk_levels else None,
            'avg_loads': avg_loads
        }
        
        return analysis