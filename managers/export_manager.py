"""
Менеджер экспорта данных для Telegram бота управления периодическими событиями
"""

import io
import csv
import xlsxwriter
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter
from core.security import decrypt_data
from managers.advanced_analytics_manager import AdvancedAnalyticsManager
from managers.automated_reports_manager import AutomatedReportsManager

logger = logging.getLogger(__name__)

class ExportManager:
    """Менеджер экспорта данных в Excel и CSV форматы"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.analytics_manager = AdvancedAnalyticsManager(db_manager)
        self.reports_manager = AutomatedReportsManager(db_manager)
    
    async def export_all_events(self, chat_id: int, file_format: str = "xlsx") -> io.BytesIO:
        """
        Экспортирует все события в Excel с форматированием
        
        Args:
            chat_id: ID чата
            file_format: Формат файла ('xlsx' или 'csv')
            
        Returns:
            BytesIO буфер с файлом
        """
        # Получаем данные
        events_data = self.db.execute_with_retry('''
            SELECT 
                e.full_name,
                e.position,
                ee.event_type,
                ee.last_event_date,
                ee.next_notification_date,
                ee.interval_days,
                CASE 
                    WHEN date(ee.next_notification_date) < date('now') THEN 'Просрочено'
                    WHEN date(ee.next_notification_date) <= date('now', '+7 days') THEN 'Критично'
                    WHEN date(ee.next_notification_date) <= date('now', '+14 days') THEN 'Срочно'
                    WHEN date(ee.next_notification_date) <= date('now', '+30 days') THEN 'Внимание'
                    ELSE 'Плановое'
                END as status,
                (julianday(ee.next_notification_date) - julianday('now')) as days_until
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            ORDER BY ee.next_notification_date
        ''', (chat_id,), fetch="all")
        
        if file_format == "csv":
            return self._export_to_csv(events_data)
        else:
            return self._export_to_xlsx(events_data)
    
    def _export_to_csv(self, events_data: List) -> io.BytesIO:
        """
        Экспорт в CSV формат
        
        Args:
            events_data: Данные событий
            
        Returns:
            BytesIO буфер с CSV файлом
        """
        output = io.BytesIO()
        output_str = io.StringIO()
        
        writer = csv.writer(output_str, delimiter=';')
        
        # Заголовки
        headers = [
            'ФИО', 'Должность', 'Тип события', 'Последнее событие', 
            'Следующее событие', 'Интервал (дни)', 'Статус', 'Дней до события'
        ]
        writer.writerow(headers)
        
        # Данные
        for event in events_data:
            try:
                decrypted_name = decrypt_data(event['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
                
            row = [
                decrypted_name,
                event['position'],
                event['event_type'],
                event['last_event_date'],
                event['next_notification_date'],
                event['interval_days'],
                event['status'],
                int(event['days_until']) if event['days_until'] else 0
            ]
            writer.writerow(row)
        
        # Конвертируем в BytesIO
        output.write(output_str.getvalue().encode('utf-8-sig'))
        output.seek(0)
        return output
    
    def _export_to_xlsx(self, events_data: List) -> io.BytesIO:
        """
        Экспорт в Excel с форматированием
        
        Args:
            events_data: Данные событий
            
        Returns:
            BytesIO буфер с Excel файлом
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Создаем листы
        events_sheet = workbook.add_worksheet('События')
        stats_sheet = workbook.add_worksheet('Статистика')
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd.mm.yyyy',
            'border': 1
        })
        
        # Форматы для статусов
        status_formats = {
            'Просрочено': workbook.add_format({'bg_color': '#FF0000', 'font_color': 'white', 'border': 1}),
            'Критично': workbook.add_format({'bg_color': '#FF6600', 'font_color': 'white', 'border': 1}),
            'Срочно': workbook.add_format({'bg_color': '#FFFF00', 'border': 1}),
            'Внимание': workbook.add_format({'bg_color': '#90EE90', 'border': 1}),
            'Плановое': workbook.add_format({'bg_color': '#87CEEB', 'border': 1})
        }
        
        default_format = workbook.add_format({'border': 1})
        
        # === ЛИСТ СОБЫТИЙ ===
        headers = [
            'ФИО', 'Должность', 'Тип события', 'Последнее событие',
            'Следующее событие', 'Интервал (дни)', 'Статус', 'Дней до события'
        ]
        
        # Записываем заголовки
        for col, header in enumerate(headers):
            events_sheet.write(0, col, header, header_format)
        
        # Записываем данные
        for row, event in enumerate(events_data, 1):
            try:
                decrypted_name = decrypt_data(event['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            
            events_sheet.write(row, 0, decrypted_name, default_format)
            events_sheet.write(row, 1, event['position'], default_format)
            events_sheet.write(row, 2, event['event_type'], default_format)
            events_sheet.write_datetime(row, 3, datetime.fromisoformat(event['last_event_date']), date_format)
            events_sheet.write_datetime(row, 4, datetime.fromisoformat(event['next_notification_date']), date_format)
            events_sheet.write(row, 5, event['interval_days'], default_format)
            
            # Статус с цветовым кодированием
            status = event['status']
            status_format = status_formats.get(status, default_format)
            events_sheet.write(row, 6, status, status_format)
            events_sheet.write(row, 7, int(event['days_until']) if event['days_until'] else 0, default_format)
        
        # Настройка ширины колонок
        events_sheet.set_column('A:A', 25)  # ФИО
        events_sheet.set_column('B:B', 20)  # Должность
        events_sheet.set_column('C:C', 20)  # Тип события
        events_sheet.set_column('D:E', 15)  # Даты
        events_sheet.set_column('F:F', 12)  # Интервал
        events_sheet.set_column('G:G', 12)  # Статус
        events_sheet.set_column('H:H', 15)  # Дней до события
        
        # === ЛИСТ СТАТИСТИКИ ===
        self._add_statistics_sheet(stats_sheet, events_data, workbook)
        
        workbook.close()
        output.seek(0)
        return output
    
    def _add_statistics_sheet(self, sheet, events_data: List, workbook):
        """
        Добавляет лист со статистикой
        
        Args:
            sheet: Лист Excel
            events_data: Данные событий
            workbook: Рабочая книга Excel
        """
        # Форматы
        title_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#4472C4', 
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        subtitle_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9E2F3', 'border': 1
        })
        
        data_format = workbook.add_format({'border': 1, 'align': 'center'})
        
        # Подсчет статистики
        status_counts = Counter(event['status'] for event in events_data)
        event_type_counts = Counter(event['event_type'] for event in events_data)
        
        row = 0
        
        # Заголовок
        sheet.merge_range(row, 0, row, 3, 'ОТЧЕТ ПО ПЕРИОДИЧЕСКИМ СОБЫТИЯМ', title_format)
        row += 2
        
        # Общая статистика
        sheet.write(row, 0, 'Общая статистика:', subtitle_format)
        row += 1
        sheet.write(row, 0, 'Всего событий:', data_format)
        sheet.write(row, 1, len(events_data), data_format)
        row += 1
        
        sheet.write(row, 0, 'Уникальных сотрудников:', data_format)
        unique_employees = len(set(event['full_name'] for event in events_data))
        sheet.write(row, 1, unique_employees, data_format)
        row += 2
        
        # Статистика по статусам
        sheet.write(row, 0, 'Распределение по статусам:', subtitle_format)
        row += 1
        
        for status, count in status_counts.items():
            sheet.write(row, 0, status, data_format)
            sheet.write(row, 1, count, data_format)
            percentage = (count / len(events_data)) * 100
            sheet.write(row, 2, f"{percentage:.1f}%", data_format)
            row += 1
        
        row += 1
        
        # Топ типов событий
        sheet.write(row, 0, 'Топ-5 типов событий:', subtitle_format)
        row += 1
        
        for event_type, count in event_type_counts.most_common(5):
            sheet.write(row, 0, event_type, data_format)
            sheet.write(row, 1, count, data_format)
            row += 1
        
        # Настройка ширины колонок
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 15)
    
    async def export_analytics_report(self, chat_id: int, report_type: str = "full") -> io.BytesIO:
        """
        Экспортирует аналитический отчет в Excel
        
        Args:
            chat_id: ID чата
            report_type: Тип отчета ('trends', 'forecast', 'efficiency', 'full')
            
        Returns:
            BytesIO буфер с Excel файлом
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        try:
            if report_type == "full" or report_type == "trends":
                await self._add_trends_sheet(workbook, chat_id)
            
            if report_type == "full" or report_type == "forecast":
                await self._add_forecast_sheet(workbook, chat_id)
            
            if report_type == "full" or report_type == "efficiency":
                await self._add_efficiency_sheet(workbook, chat_id)
            
            if report_type == "full":
                await self._add_timeline_charts_sheet(workbook, chat_id)
                await self._add_advanced_forecast_sheet(workbook, chat_id)
            
            workbook.close()
            output.seek(0)
            return output
            
        except Exception as e:
            logger.error(f"Error exporting analytics report: {e}")
            workbook.close()
            raise
    
    async def _add_trends_sheet(self, workbook, chat_id: int):
        """
        Добавляет лист с анализом трендов
        """
        sheet = workbook.add_worksheet('Анализ трендов')
        
        # Форматы
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#2E75B6',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#4472C4',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        data_format = workbook.add_format({'border': 1, 'align': 'left'})
        
        # Получаем данные трендов
        trends = self.analytics_manager.get_trends_analysis(chat_id, 6)
        
        row = 0
        
        # Заголовок
        sheet.merge_range(row, 0, row, 4, 'АНАЛИЗ ТРЕНДОВ СОБЫТИЙ', title_format)
        row += 2
        
        # Дата создания
        sheet.write(row, 0, 'Дата создания:', header_format)
        sheet.write(row, 1, datetime.now().strftime('%d.%m.%Y %H:%M'), data_format)
        row += 2
        
        if trends.get('trend') != 'no_data':
            # Общие события
            total_trend = trends.get('total_events_trend', {})
            if total_trend:
                sheet.write(row, 0, 'ОБЩИЕ СОБЫТИЯ:', header_format)
                row += 1
                sheet.write(row, 0, 'Описание тренда:', data_format)
                sheet.write(row, 1, total_trend.get('description', 'Нет данных'), data_format)
                row += 2
            
            # Просроченные события
            overdue_trend = trends.get('overdue_trend', {})
            if overdue_trend:
                sheet.write(row, 0, 'ПРОСРОЧЕННЫЕ СОБЫТИЯ:', header_format)
                row += 1
                sheet.write(row, 0, 'Описание тренда:', data_format)
                sheet.write(row, 1, overdue_trend.get('description', 'Нет данных'), data_format)
                row += 2
        else:
            sheet.write(row, 0, 'Недостаточно данных для анализа трендов', data_format)
        
        # Настройка ширины колонок
        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 40)
    
    async def _add_forecast_sheet(self, workbook, chat_id: int):
        """
        Добавляет лист с прогнозами нагрузки
        """
        sheet = workbook.add_worksheet('Прогноз нагрузки')
        
        # Форматы
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#70AD47',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#A9D08E',
            'border': 1, 'align': 'center'
        })
        
        data_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd.mm.yyyy'})
        
        # Получаем прогноз на 30 дней
        forecast = self.analytics_manager.get_workload_forecast(chat_id, 30)
        
        row = 0
        
        # Заголовок
        sheet.merge_range(row, 0, row, 5, 'ПРОГНОЗ РАБОЧЕЙ НАГРУЗКИ', title_format)
        row += 2
        
        # Сводка
        summary = forecast.get('summary', {})
        if summary:
            sheet.write(row, 0, 'ОБЩАЯ СТАТИСТИКА:', header_format)
            row += 1
            
            summary_data = [
                ('Период прогноза (дни)', summary.get('forecast_period', 30)),
                ('Всего событий', summary.get('total_events', 0)),
                ('Среднее в день', f"{summary.get('avg_per_day', 0):.1f}")
            ]
            
            for label, value in summary_data:
                sheet.write(row, 0, label + ':', data_format)
                sheet.write(row, 1, value, data_format)
                row += 1
        
        # Настройка ширины колонок
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 20)
    
    async def _add_efficiency_sheet(self, workbook, chat_id: int):
        """
        Добавляет лист с анализом эффективности
        """
        sheet = workbook.add_worksheet('Эффективность')
        
        # Форматы
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#E67E22',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#F39C12',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        data_format = workbook.add_format({'border': 1})
        
        # Получаем метрики эффективности
        efficiency = self.analytics_manager.get_efficiency_metrics(chat_id)
        
        row = 0
        
        # Заголовок
        sheet.merge_range(row, 0, row, 3, 'АНАЛИЗ ЭФФЕКТИВНОСТИ', title_format)
        row += 2
        
        # Общая оценка
        sheet.write(row, 0, 'ОБЩАЯ ОЦЕНКА:', header_format)
        row += 1
        
        grade = efficiency.get('efficiency_grade', 'N/A')
        emoji = efficiency.get('efficiency_emoji', '')
        sheet.write(row, 0, 'Оценка эффективности:', data_format)
        sheet.write(row, 1, f"{grade} {emoji}", data_format)
        row += 2
        
        # Ключевые показатели
        sheet.write(row, 0, 'КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ:', header_format)
        row += 1
        
        metrics_data = [
            ('Соблюдение сроков (%)', f"{efficiency.get('compliance_rate', 0)}%"),
            ('Всего событий', efficiency.get('total_events', 0)),
            ('Выполнено вовремя', efficiency.get('on_time_events', 0)),
            ('Просрочено', efficiency.get('overdue_events', 0))
        ]
        
        for label, value in metrics_data:
            sheet.write(row, 0, label + ':', data_format)
            sheet.write(row, 1, str(value), data_format)
            row += 1
        
        # Настройка ширины колонок
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 50)
    
    async def _add_timeline_charts_sheet(self, workbook, chat_id: int):
        """
        Добавляет лист с временными диаграммами
        """
        sheet = workbook.add_worksheet('Временные диаграммы')
        
        # Форматы
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#8E44AD',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#A569BD',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        data_format = workbook.add_format({'border': 1, 'font_family': 'Courier New'})
        
        # Получаем детальные временные диаграммы
        charts = self.analytics_manager.get_detailed_timeline_charts(chat_id)
        
        row = 0
        
        # Заголовок
        sheet.merge_range(row, 0, row, 3, 'ВРЕМЕННЫЕ ДИАГРАММЫ СОБЫТИЙ', title_format)
        row += 2
        
        # Месячная диаграмма
        monthly_data = charts.get('monthly', {})
        if monthly_data:
            sheet.write(row, 0, 'МЕСЯЧНАЯ ДИАГРАММА:', header_format)
            row += 1
            
            chart_text = monthly_data.get('chart', 'Нет данных')
            # Разбиваем диаграмму на строки
            chart_lines = chart_text.split('\n')
            for line in chart_lines:
                sheet.write(row, 0, line, data_format)
                row += 1
        
        # Настройка ширины колонок
        sheet.set_column('A:A', 80)  # Широкая колонка для диаграмм
    
    async def _add_advanced_forecast_sheet(self, workbook, chat_id: int):
        """
        Добавляет лист с расширенным прогнозированием
        """
        sheet = workbook.add_worksheet('Расширенный прогноз')
        
        # Форматы
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#16A085',
            'font_color': 'white', 'border': 1, 'align': 'center'
        })
        
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#48C9B0',
            'border': 1, 'align': 'center'
        })
        
        data_format = workbook.add_format({'border': 1})
        
        # Получаем расширенный прогноз
        periods = {'short': 7, 'medium': 30, 'long': 90}
        advanced_forecast = self.analytics_manager.get_advanced_workload_forecast(chat_id, periods)
        
        row = 0
        
        # Заголовок
        sheet.merge_range(row, 0, row, 4, 'РАСШИРЕННЫЙ ПРОГНОЗ НАГРУЗКИ', title_format)
        row += 2
        
        # Прогнозы по периодам
        forecasts = advanced_forecast.get('forecasts', {})
        period_names = {
            'short': 'Краткосрочный (7 дней)',
            'medium': 'Среднесрочный (30 дней)',
            'long': 'Долгосрочный (90 дней)'
        }
        
        for period_key, forecast_data in forecasts.items():
            period_name = period_names.get(period_key, period_key)
            forecast = forecast_data['forecast']
            risk = forecast_data['risk_assessment']
            summary = forecast['summary']
            
            sheet.write(row, 0, period_name.upper(), header_format)
            row += 1
            
            # Основные метрики
            metrics = [
                ('Средняя нагрузка (событий/день)', f"{summary.get('avg_per_day', 0):.1f}"),
                ('Всего событий', summary.get('total_events', 0)),
                ('Уровень риска', f"{risk['risk_emoji']} {risk['risk_level']} (балл: {risk['risk_score']})")
            ]
            
            for label, value in metrics:
                sheet.write(row, 0, label + ':', data_format)
                sheet.write(row, 1, str(value), data_format)
                row += 1
            
            row += 1
        
        # Настройка ширины колонок
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 50)
    
    async def export_automated_report(self, chat_id: int, report_type: str) -> Optional[io.BytesIO]:
        """
        Экспортирует автоматический отчет в Excel
        
        Args:
            chat_id: ID чата
            report_type: Тип отчета ('daily', 'weekly', 'monthly')
            
        Returns:
            BytesIO буфер с Excel файлом или None
        """
        try:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            
            # Генерируем отчет
            if report_type == 'daily':
                report_content = await self.reports_manager._generate_daily_summary(chat_id)
                sheet_name = 'Ежедневный отчет'
            elif report_type == 'weekly':
                report_content = await self.reports_manager._generate_weekly_report(chat_id)
                sheet_name = 'Еженедельный отчет'
            elif report_type == 'monthly':
                report_content = await self.reports_manager._generate_monthly_report(chat_id)
                sheet_name = 'Месячный отчет'
            else:
                return None
            
            if not report_content:
                return None
            
            # Создаем лист отчета
            sheet = workbook.add_worksheet(sheet_name)
            
            # Форматы
            text_format = workbook.add_format({'border': 1, 'text_wrap': True})
            
            # Разбиваем отчет на строки и записываем в Excel
            lines = report_content.split('\n')
            for row, line in enumerate(lines):
                # Очищаем от HTML тегов
                clean_line = line.replace('<b>', '').replace('</b>', '')
                sheet.write(row, 0, clean_line, text_format)
            
            # Настройка ширины колонки
            sheet.set_column('A:A', 80)
            
            workbook.close()
            output.seek(0)
            return output
            
        except Exception as e:
            logger.error(f"Error exporting automated report: {e}")
            return None
    
    async def export_overdue_events(self, chat_id: int, file_format: str = "xlsx") -> io.BytesIO:
        """
        Экспортирует только просроченные события
        
        Args:
            chat_id: ID чата
            file_format: Формат файла ('xlsx' или 'csv')
            
        Returns:
            BytesIO буфер с файлом
        """
        # Получаем только просроченные события
        overdue_events = self.db.execute_with_retry('''
            SELECT 
                e.full_name,
                e.position,
                ee.event_type,
                ee.last_event_date,
                ee.next_notification_date,
                ee.interval_days,
                'Просрочено' as status,
                (julianday('now') - julianday(ee.next_notification_date)) as days_overdue
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            AND date(ee.next_notification_date) < date('now')
            ORDER BY ee.next_notification_date
        ''', (chat_id,), fetch="all")
        
        if file_format == "csv":
            return self._export_overdue_to_csv(overdue_events)
        else:
            return self._export_overdue_to_xlsx(overdue_events)
    
    def _export_overdue_to_csv(self, overdue_events: List) -> io.BytesIO:
        """
        Экспорт просроченных событий в CSV
        
        Args:
            overdue_events: Данные просроченных событий
            
        Returns:
            BytesIO буфер с CSV файлом
        """
        output = io.BytesIO()
        output_str = io.StringIO()
        
        writer = csv.writer(output_str, delimiter=';')
        
        # Заголовки
        headers = [
            'ФИО', 'Должность', 'Тип события', 'Последнее событие',
            'Дата просрочки', 'Интервал (дни)', 'Дней просрочено'
        ]
        writer.writerow(headers)
        
        # Данные
        for event in overdue_events:
            try:
                decrypted_name = decrypt_data(event['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
                
            row = [
                decrypted_name,
                event['position'],
                event['event_type'],
                event['last_event_date'],
                event['next_notification_date'],
                event['interval_days'],
                int(event['days_overdue']) if event['days_overdue'] else 0
            ]
            writer.writerow(row)
        
        # Конвертируем в BytesIO
        output.write(output_str.getvalue().encode('utf-8-sig'))
        output.seek(0)
        return output
    
    def _export_overdue_to_xlsx(self, overdue_events: List) -> io.BytesIO:
        """
        Экспорт просроченных событий в Excel с выделением
        
        Args:
            overdue_events: Данные просроченных событий
            
        Returns:
            BytesIO буфер с Excel файлом
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        sheet = workbook.add_worksheet('Просроченные события')
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FF0000',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd.mm.yyyy',
            'border': 1,
            'bg_color': '#FFE6E6'  # Светло-красный фон
        })
        
        overdue_format = workbook.add_format({
            'border': 1,
            'bg_color': '#FFE6E6',  # Светло-красный фон
            'font_color': '#8B0000'  # Темно-красный текст
        })
        
        critical_format = workbook.add_format({
            'border': 1,
            'bg_color': '#FF0000',  # Красный фон
            'font_color': 'white',
            'bold': True
        })
        
        # Заголовки
        headers = [
            'ФИО', 'Должность', 'Тип события', 'Последнее событие',
            'Дата просрочки', 'Интервал (дни)', 'Дней просрочено'
        ]
        
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Данные
        for row, event in enumerate(overdue_events, 1):
            try:
                decrypted_name = decrypt_data(event['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            
            days_overdue = int(event['days_overdue']) if event['days_overdue'] else 0
            
            # Выбираем формат в зависимости от критичности просрочки
            cell_format = critical_format if days_overdue > 30 else overdue_format
            
            sheet.write(row, 0, decrypted_name, cell_format)
            sheet.write(row, 1, event['position'], cell_format)
            sheet.write(row, 2, event['event_type'], cell_format)
            sheet.write_datetime(row, 3, datetime.fromisoformat(event['last_event_date']), date_format)
            sheet.write_datetime(row, 4, datetime.fromisoformat(event['next_notification_date']), date_format)
            sheet.write(row, 5, event['interval_days'], cell_format)
            sheet.write(row, 6, days_overdue, cell_format)
        
        # Настройка ширины колонок
        sheet.set_column('A:A', 25)  # ФИО
        sheet.set_column('B:B', 20)  # Должность
        sheet.set_column('C:C', 25)  # Тип события
        sheet.set_column('D:E', 15)  # Даты
        sheet.set_column('F:F', 12)  # Интервал
        sheet.set_column('G:G', 15)  # Дней просрочено
        
        # Добавляем примечание
        note_format = workbook.add_format({
            'italic': True,
            'font_color': '#666666',
            'bg_color': '#F0F0F0',
            'border': 1
        })
        
        note_row = len(overdue_events) + 2
        sheet.merge_range(note_row, 0, note_row, 6, 
                         f'Отчет сгенерирован {datetime.now().strftime("%d.%m.%Y %H:%M")}. '
                         f'Всего просроченных событий: {len(overdue_events)}',
                         note_format)
        
        workbook.close()
        output.seek(0)
        return output