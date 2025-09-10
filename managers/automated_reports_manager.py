"""
Менеджер автоматических отчетов для Telegram бота
Создает и отправляет периодические аналитические отчеты
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Bot
from telegram.ext import ContextTypes

from core.security import decrypt_data, is_admin
from core.utils import create_callback_data
from managers.advanced_analytics_manager import AdvancedAnalyticsManager

logger = logging.getLogger(__name__)

class AutomatedReportsManager:
    """Менеджер автоматической генерации и отправки отчетов"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.analytics_manager = AdvancedAnalyticsManager(db_manager)
        
    def setup_report_schedules(self):
        """Настройка расписания автоматических отчетов"""
        schedules = [
            {
                'name': 'daily_summary',
                'frequency': 'daily',
                'time': '09:00',
                'recipients': 'admins',
                'enabled': True
            },
            {
                'name': 'weekly_analytics',
                'frequency': 'weekly',
                'time': '08:00',
                'day': 'monday',
                'recipients': 'admins',
                'enabled': True
            },
            {
                'name': 'monthly_report',
                'frequency': 'monthly',
                'time': '09:00',
                'day': 1,  # первое число месяца
                'recipients': 'admins',
                'enabled': True
            }
        ]
        return schedules
    
    async def send_daily_summary_report(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Отправляет ежедневный сводный отчет
        
        Args:
            context: Контекст бота
        """
        logger.info("Generating daily summary reports")
        
        try:
            # Получаем все активные чаты
            chats = self.db.execute_with_retry('''
                SELECT DISTINCT chat_id, admin_id, timezone 
                FROM chat_settings 
                WHERE admin_id IS NOT NULL
            ''', fetch="all")
            
            for chat in chats:
                chat_id = chat['chat_id']
                admin_id = chat['admin_id']
                
                # Генерируем отчет для этого чата
                report = await self._generate_daily_summary(chat_id)
                
                if report:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=report,
                            parse_mode='HTML'
                        )
                        logger.info(f"Daily report sent to admin {admin_id} for chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Failed to send daily report to {admin_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in daily summary reports: {e}")
    
    async def send_weekly_analytics_report(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Отправляет еженедельный аналитический отчет
        
        Args:
            context: Контекст бота
        """
        logger.info("Generating weekly analytics reports")
        
        try:
            chats = self.db.execute_with_retry('''
                SELECT DISTINCT chat_id, admin_id, timezone 
                FROM chat_settings 
                WHERE admin_id IS NOT NULL
            ''', fetch="all")
            
            for chat in chats:
                chat_id = chat['chat_id']
                admin_id = chat['admin_id']
                
                # Генерируем еженедельный отчет
                report = await self._generate_weekly_report(chat_id)
                
                if report:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=report,
                            parse_mode='HTML'
                        )
                        logger.info(f"Weekly report sent to admin {admin_id} for chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Failed to send weekly report to {admin_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in weekly analytics reports: {e}")
    
    async def send_monthly_report(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Отправляет месячный отчет
        
        Args:
            context: Контекст бота
        """
        logger.info("Generating monthly reports")
        
        try:
            chats = self.db.execute_with_retry('''
                SELECT DISTINCT chat_id, admin_id, timezone 
                FROM chat_settings 
                WHERE admin_id IS NOT NULL
            ''', fetch="all")
            
            for chat in chats:
                chat_id = chat['chat_id']
                admin_id = chat['admin_id']
                
                # Генерируем месячный отчет
                report = await self._generate_monthly_report(chat_id)
                
                if report:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=report,
                            parse_mode='HTML'
                        )
                        logger.info(f"Monthly report sent to admin {admin_id} for chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Failed to send monthly report to {admin_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in monthly reports: {e}")
    
    async def _generate_daily_summary(self, chat_id: int) -> Optional[str]:
        """
        Генерирует ежедневный сводный отчет
        
        Args:
            chat_id: ID чата
            
        Returns:
            Отформатированный отчет или None
        """
        try:
            # Получаем данные на сегодня и ближайшие дни
            today = datetime.now().date()
            
            # Статистика на сегодня
            today_events = self.db.execute_with_retry('''
                SELECT COUNT(*) as count
                FROM employee_events ee
                JOIN employees e ON ee.employee_id = e.id
                WHERE e.chat_id = ? AND e.is_active = 1
                AND date(ee.next_notification_date) = date('now')
            ''', (chat_id,), fetch="one")
            
            # Просроченные события
            overdue_events = self.db.execute_with_retry('''
                SELECT COUNT(*) as count
                FROM employee_events ee
                JOIN employees e ON ee.employee_id = e.id
                WHERE e.chat_id = ? AND e.is_active = 1
                AND date(ee.next_notification_date) < date('now')
            ''', (chat_id,), fetch="one")
            
            # События на завтра
            tomorrow_events = self.db.execute_with_retry('''
                SELECT COUNT(*) as count
                FROM employee_events ee
                JOIN employees e ON ee.employee_id = e.id
                WHERE e.chat_id = ? AND e.is_active = 1
                AND date(ee.next_notification_date) = date('now', '+1 day')
            ''', (chat_id,), fetch="one")
            
            # События на эту неделю
            week_events = self.db.execute_with_retry('''
                SELECT COUNT(*) as count
                FROM employee_events ee
                JOIN employees e ON ee.employee_id = e.id
                WHERE e.chat_id = ? AND e.is_active = 1
                AND date(ee.next_notification_date) BETWEEN date('now') 
                AND date('now', '+7 days')
            ''', (chat_id,), fetch="one")
            
            # Если нет данных, не отправляем отчет
            if not any([today_events['count'], overdue_events['count'], tomorrow_events['count']]):
                return None
            
            report_lines = [
                "📊 <b>Ежедневный сводный отчет</b>",
                f"📅 {today.strftime('%d.%m.%Y (%A)')}",
                "",
                "📈 <b>Статистика на сегодня:</b>"
            ]
            
            # Сегодняшние события
            if today_events['count'] > 0:
                report_lines.append(f"📅 События сегодня: {today_events['count']}")
            else:
                report_lines.append("📅 Событий сегодня: нет")
            
            # Просроченные
            if overdue_events['count'] > 0:
                status = "🔴 КРИТИЧНО" if overdue_events['count'] > 5 else "🟡 Внимание"
                report_lines.append(f"⚠️ Просроченные: {overdue_events['count']} {status}")
            else:
                report_lines.append("✅ Просроченных: нет")
            
            # События завтра
            if tomorrow_events['count'] > 0:
                report_lines.append(f"🔜 События завтра: {tomorrow_events['count']}")
            
            # События на неделю
            report_lines.extend([
                "",
                f"📊 <b>Прогноз на неделю:</b> {week_events['count']} событий"
            ])
            
            # Рекомендации
            recommendations = []
            if overdue_events['count'] > 0:
                recommendations.append("🔴 Проверьте просроченные события")
            if tomorrow_events['count'] > 3:
                recommendations.append("🟡 Подготовьтесь к завтрашним событиям")
            if week_events['count'] > 20:
                recommendations.append("📈 Высокая загрузка на неделе")
            
            if recommendations:
                report_lines.extend(["", "💡 <b>Рекомендации:</b>"])
                for rec in recommendations:
                    report_lines.append(f"   {rec}")
            
            report_lines.extend([
                "",
                f"🕒 Отчет создан: {datetime.now().strftime('%H:%M')}",
                "📊 Подробная аналитика доступна в боте"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating daily summary for chat {chat_id}: {e}")
            return None
    
    async def _generate_weekly_report(self, chat_id: int) -> Optional[str]:
        """
        Генерирует еженедельный аналитический отчет
        
        Args:
            chat_id: ID чата
            
        Returns:
            Отформатированный отчет или None
        """
        try:
            # Получаем аналитику за неделю
            weekly_stats = self.analytics_manager.get_weekly_analysis(chat_id, 1)
            trends = self.analytics_manager.get_trends_analysis(chat_id, 3)
            efficiency = self.analytics_manager.get_efficiency_metrics(chat_id)
            
            if not weekly_stats and efficiency.get('total_events', 0) == 0:
                return None
            
            report_lines = [
                "📊 <b>Еженедельный аналитический отчет</b>",
                f"📅 Период: {(datetime.now() - timedelta(days=7)).strftime('%d.%m')} - {datetime.now().strftime('%d.%m.%Y')}",
                "",
                "📈 <b>Ключевые показатели:</b>"
            ]
            
            # Эффективность
            if efficiency.get('total_events', 0) > 0:
                report_lines.extend([
                    f"⚡ Общая эффективность: {efficiency.get('efficiency_grade', 'N/A')} {efficiency.get('efficiency_emoji', '')}",
                    f"✅ Соблюдение сроков: {efficiency.get('compliance_rate', 0)}%",
                    f"📊 Всего событий: {efficiency.get('total_events', 0)}",
                    f"🔴 Просрочено: {efficiency.get('overdue_events', 0)}"
                ])
            
            # Тренды
            if trends.get('trend') != 'no_data':
                total_trend = trends.get('total_events_trend', {})
                if total_trend:
                    report_lines.extend([
                        "",
                        "📈 <b>Тренды:</b>",
                        f"📊 Общая динамика: {total_trend.get('description', 'Стабильно')}",
                        f"📉 Изменение: {self.analytics_manager.generate_text_charts(total_trend, 'trend')}"
                    ])
            
            # Недельная статистика
            if weekly_stats:
                current_week = list(weekly_stats.values())[-1] if weekly_stats else None
                if current_week:
                    report_lines.extend([
                        "",
                        "📅 <b>Текущая неделя:</b>",
                        f"📊 Общих событий: {current_week.get('total', 0)}",
                        f"🔴 Просроченных: {current_week.get('overdue', 0)}"
                    ])
            
            # Прогноз
            forecast = self.analytics_manager.get_workload_forecast(chat_id, 7)
            forecast_summary = forecast.get('summary', {})
            if forecast_summary.get('total_events', 0) > 0:
                report_lines.extend([
                    "",
                    "🎯 <b>Прогноз на следующую неделю:</b>",
                    f"📊 Ожидается событий: {forecast_summary.get('total_events', 0)}",
                    f"⭕ Среднее в день: {forecast_summary.get('avg_per_day', 0):.1f}"
                ])
                
                if forecast_summary.get('peak_day'):
                    peak_date = datetime.strptime(forecast_summary['peak_day'], '%Y-%m-%d')
                    report_lines.append(f"🔥 Пиковый день: {peak_date.strftime('%d.%m (%A)')} ({forecast_summary.get('peak_count', 0)} событий)")
            
            # Рекомендации
            recommendations = efficiency.get('recommendations', [])
            if recommendations:
                report_lines.extend(["", "💡 <b>Рекомендации на неделю:</b>"])
                for rec in recommendations[:3]:  # Топ-3 рекомендации
                    report_lines.append(f"   {rec}")
            
            report_lines.extend([
                "",
                f"🕒 Отчет создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                "📊 Детальная аналитика доступна в расширенной аналитике бота"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating weekly report for chat {chat_id}: {e}")
            return None
    
    async def _generate_monthly_report(self, chat_id: int) -> Optional[str]:
        """
        Генерирует месячный отчет
        
        Args:
            chat_id: ID чата
            
        Returns:
            Отформатированный отчет или None
        """
        try:
            # Получаем данные за месяц
            trends = self.analytics_manager.get_trends_analysis(chat_id, 1)
            efficiency = self.analytics_manager.get_efficiency_metrics(chat_id)
            
            # Статистика за прошлый месяц
            last_month = datetime.now().replace(day=1) - timedelta(days=1)
            month_stats = self.db.execute_with_retry('''
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN date(ee.next_notification_date) < date('now') THEN 1 END) as overdue_events,
                    COUNT(CASE WHEN ee.event_type LIKE '%медосмотр%' OR ee.event_type LIKE '%медицинский%' THEN 1 END) as medical_events,
                    COUNT(CASE WHEN ee.event_type LIKE '%инструктаж%' OR ee.event_type LIKE '%обучение%' THEN 1 END) as training_events
                FROM employee_events ee
                JOIN employees e ON ee.employee_id = e.id
                WHERE e.chat_id = ? AND e.is_active = 1
                AND strftime('%Y-%m', ee.next_notification_date) = ?
            ''', (chat_id, last_month.strftime('%Y-%m')), fetch="one")
            
            if not month_stats or month_stats['total_events'] == 0:
                return None
            
            report_lines = [
                "📊 <b>Месячный отчет</b>",
                f"📅 Период: {last_month.strftime('%B %Y')}",
                "",
                "📈 <b>Итоги месяца:</b>",
                f"📊 Всего событий: {month_stats['total_events']}",
                f"🏥 Медицинские: {month_stats['medical_events']}",
                f"📚 Обучение/Инструктажи: {month_stats['training_events']}",
                f"🔴 Просрочено: {month_stats['overdue_events']}"
            ]
            
            # Показатели эффективности
            if efficiency.get('total_events', 0) > 0:
                report_lines.extend([
                    "",
                    "⚡ <b>Эффективность системы:</b>",
                    f"🏆 Общая оценка: {efficiency.get('efficiency_grade', 'N/A')} {efficiency.get('efficiency_emoji', '')}",
                    f"✅ Соблюдение сроков: {efficiency.get('compliance_rate', 0)}%"
                ])
                
                if efficiency.get('avg_overdue_days', 0) > 0:
                    report_lines.append(f"⏰ Средняя просрочка: {efficiency.get('avg_overdue_days', 0):.1f} дней")
            
            # Тренды
            if trends.get('trend') != 'no_data':
                summary = trends.get('period_summary', {})
                if summary:
                    report_lines.extend([
                        "",
                        "📈 <b>Динамика и тренды:</b>",
                        f"⭕ Среднее событий/месяц: {summary.get('avg_events_per_month', 0):.1f}",
                        f"📈 Максимум: {summary.get('max_events_month', 0)}",
                        f"📉 Минимум: {summary.get('min_events_month', 0)}"
                    ])
            
            # Прогноз на следующий месяц
            forecast = self.analytics_manager.get_workload_forecast(chat_id, 30)
            forecast_summary = forecast.get('summary', {})
            if forecast_summary.get('total_events', 0) > 0:
                report_lines.extend([
                    "",
                    "🎯 <b>Прогноз на следующий месяц:</b>",
                    f"📊 Ожидается событий: {forecast_summary.get('total_events', 0)}",
                    f"⭕ Среднее в день: {forecast_summary.get('avg_per_day', 0):.1f}"
                ])
            
            # Рекомендации
            recommendations = []
            if month_stats['overdue_events'] > month_stats['total_events'] * 0.1:
                recommendations.append("🔴 Улучшить контроль сроков выполнения")
            if month_stats['medical_events'] > month_stats['total_events'] * 0.7:
                recommendations.append("🏥 Сфокусироваться на медицинских событиях")
            if efficiency.get('compliance_rate', 0) < 85:
                recommendations.append("📈 Повысить эффективность уведомлений")
                
            if recommendations:
                report_lines.extend(["", "💡 <b>Рекомендации:</b>"])
                for rec in recommendations:
                    report_lines.append(f"   {rec}")
            
            report_lines.extend([
                "",
                f"🕒 Отчет создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                "📊 Подробная аналитика и экспорт доступны в боте"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating monthly report for chat {chat_id}: {e}")
            return None
    
    async def send_custom_report(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, report_type: str, admin_id: int):
        """
        Отправляет пользовательский отчет по запросу
        
        Args:
            context: Контекст бота
            chat_id: ID чата
            report_type: Тип отчета ('daily', 'weekly', 'monthly')
            admin_id: ID администратора
        """
        try:
            report = None
            
            if report_type == 'daily':
                report = await self._generate_daily_summary(chat_id)
            elif report_type == 'weekly':
                report = await self._generate_weekly_report(chat_id)
            elif report_type == 'monthly':
                report = await self._generate_monthly_report(chat_id)
            
            if report:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📊 <b>Запрошенный отчет ({report_type})</b>\n\n{report}",
                    parse_mode='HTML'
                )
                logger.info(f"Custom {report_type} report sent to {admin_id}")
            else:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📊 Недостаточно данных для создания {report_type} отчета",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Error sending custom report: {e}")
    
    def get_report_settings(self, chat_id: int) -> Dict:
        """
        Получает настройки отчетов для чата
        
        Args:
            chat_id: ID чата
            
        Returns:
            Словарь с настройками отчетов
        """
        try:
            settings = self.db.execute_with_retry('''
                SELECT * FROM report_settings WHERE chat_id = ?
            ''', (chat_id,), fetch="one")
            
            if not settings:
                # Создаем настройки по умолчанию
                default_settings = {
                    'chat_id': chat_id,
                    'daily_enabled': True,
                    'weekly_enabled': True,
                    'monthly_enabled': True,
                    'daily_time': '09:00',
                    'weekly_day': 1,  # Понедельник
                    'monthly_day': 1  # Первое число
                }
                
                self.db.execute_with_retry('''
                    INSERT OR REPLACE INTO report_settings 
                    (chat_id, daily_enabled, weekly_enabled, monthly_enabled, 
                     daily_time, weekly_day, monthly_day)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chat_id, default_settings['daily_enabled'],
                    default_settings['weekly_enabled'], default_settings['monthly_enabled'],
                    default_settings['daily_time'], default_settings['weekly_day'],
                    default_settings['monthly_day']
                ))
                
                return default_settings
            
            return dict(settings)
            
        except Exception as e:
            logger.error(f"Error getting report settings for chat {chat_id}: {e}")
            return {}