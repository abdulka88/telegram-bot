# ================================================================
# PHASE1_IMPROVEMENTS.PY - УЛУЧШЕНИЯ ФАЗЫ 1
# ================================================================

import io
import csv
import xlsxwriter
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional
import logging

# Получаем logger (он должен быть уже настроен в main.py)
logger = logging.getLogger(__name__)

# ================================================================
# 1. МНОГОУРОВНЕВЫЕ УВЕДОМЛЕНИЯ
# ================================================================

class NotificationLevel(Enum):
    INFO = "info"           # 90+ дней (первое уведомление за 90 дней)
    WARNING = "warning"     # 8-30 дней (уведомление за 30 дней)
    URGENT = "urgent"       # 4-7 дней (уведомление за 7 дней)
    CRITICAL = "critical"   # 0-3 дня (ежедневно)
    OVERDUE = "overdue"     # просрочено (ежедневно)

class NotificationManager:
    def __init__(self, db_manager):
        self.db = db_manager
        
    def get_notification_level(self, days_until: int) -> NotificationLevel:
        """Определяет уровень срочности уведомления"""
        if days_until < 0:
            return NotificationLevel.OVERDUE
        elif days_until <= 3:
            return NotificationLevel.CRITICAL
        elif days_until <= 7:
            return NotificationLevel.URGENT
        elif days_until <= 30:
            return NotificationLevel.WARNING
        else:
            return NotificationLevel.INFO
    
    def should_send_notification(self, level: NotificationLevel, days_until: int) -> bool:
        """Определяет, нужно ли отправлять уведомление сегодня"""
        
        # Просроченные - каждый день
        if level == NotificationLevel.OVERDUE:
            return True
        
        # Критичные (0-3 дня) - каждый день
        if level == NotificationLevel.CRITICAL:
            return True
        
        # Срочные (4-7 дней) - только в ключевые дни
        if level == NotificationLevel.URGENT:
            return days_until in [7]  # Только за 7 дней
        
        # Предупреждения (8-30 дней) - только за 30 дней
        if level == NotificationLevel.WARNING:
            return days_until in [30]  # Только за 30 дней
        
        # Информационные (31+ дней) - только за 90 дней
        if level == NotificationLevel.INFO:
            return days_until in [90]  # Первое уведомление за 90 дней
        
        return False
    
    def format_notification_message(self, notification: dict, level: NotificationLevel) -> str:
        """Форматирует сообщение в зависимости от уровня срочности"""
        # Импортируем функцию дешифрации из main
        from main import decrypt_data
        
        full_name = decrypt_data(notification['full_name'])
        event_date = datetime.fromisoformat(notification['next_notification_date']).date()
        days_until = (event_date - datetime.now().date()).days
        
        # Эмодзи и текст в зависимости от уровня
        level_config = {
            NotificationLevel.INFO: {
                "emoji": "ℹ️",
                "title": "Первое уведомление",
                "color": "🟢",
                "urgency": f"через {days_until} дн."
            },
            NotificationLevel.WARNING: {
                "emoji": "⚠️", 
                "title": "Предупреждение",
                "color": "🟡",
                "urgency": f"через {days_until} дн."
            },
            NotificationLevel.URGENT: {
                "emoji": "🚨",
                "title": "СРОЧНО",
                "color": "🟠", 
                "urgency": f"через {days_until} дн."
            },
            NotificationLevel.CRITICAL: {
                "emoji": "🔴",
                "title": "КРИТИЧНО",
                "color": "🔴",
                "urgency": "СКОРО!" if days_until > 0 else "СЕГОДНЯ!"
            },
            NotificationLevel.OVERDUE: {
                "emoji": "💀",
                "title": "ПРОСРОЧЕНО",
                "color": "⚫",
                "urgency": f"просрочено на {abs(days_until)} дн."
            }
        }
        
        config = level_config[level]
        
        message = (
            f"{config['emoji']} <b>{config['title']}: {notification['event_type']}</b>\n"
            f"👤 Сотрудник: {full_name}\n"
            f"📅 Дата события: {event_date.strftime('%d.%m.%Y')}\n"
            f"{config['color']} Срочность: {config['urgency']}"
        )
        
        # Добавляем дополнительную информацию для критичных случаев
        if level in [NotificationLevel.CRITICAL, NotificationLevel.OVERDUE]:
            message += f"\n\n📞 <b>Требуется немедленное действие!</b>"
            if notification.get('position'):
                message += f"\n💼 Должность: {notification['position']}"
        
        return message

    async def send_escalated_notifications(self, context, notification: dict, level: NotificationLevel):
        """Отправляет эскалированные уведомления для критичных случаев"""
        if level not in [NotificationLevel.CRITICAL, NotificationLevel.OVERDUE]:
            return
            
        try:
            # Получаем всех администраторов чата
            admins = self.db.execute_with_retry(
                "SELECT admin_id FROM chat_settings WHERE chat_id = ?",
                (notification['chat_id'],),
                fetch="all"
            )
            
            escalation_message = (
                f"🚨 <b>ЭСКАЛАЦИЯ</b>\n"
                f"{self.format_notification_message(notification, level)}\n\n"
                f"⚡ Уведомление направлено всем администраторам"
            )
            
            # Отправляем всем админам
            for admin in admins:
                try:
                    await context.bot.send_message(
                        chat_id=admin['admin_id'],
                        text=escalation_message,
                        parse_mode='HTML',
                        reply_markup=self.create_action_keyboard(notification)
                    )
                except Exception as e:
                    logger.warning(f"Failed to send escalation to admin {admin['admin_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in escalated notifications: {e}")

    def create_action_keyboard(self, notification: dict):
        """Создает клавиатуру с быстрыми действиями"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from main import create_callback_data
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Отметить выполненным", 
                    callback_data=create_callback_data("mark_completed", event_id=notification['id'])
                ),
                InlineKeyboardButton(
                    "📅 Перенести дату", 
                    callback_data=create_callback_data("reschedule", event_id=notification['id'])
                )
            ],
            [
                InlineKeyboardButton(
                    "👤 Связаться с сотрудником", 
                    callback_data=create_callback_data("contact_employee", emp_id=notification.get('employee_id'))
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

# ================================================================
# 2. ЭКСПОРТ В EXCEL С РАСШИРЕННОЙ ФУНКЦИОНАЛЬНОСТЬЮ  
# ================================================================

class ExcelExporter:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def export_all_events(self, chat_id: int, file_format: str = "xlsx") -> io.BytesIO:
        """Экспортирует все события в Excel с форматированием"""
        
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
        """Экспорт в CSV формат"""
        from main import decrypt_data
        
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
            decrypted_name = decrypt_data(event['full_name'])
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
        """Экспорт в Excel с форматированием"""
        from main import decrypt_data
        
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
            decrypted_name = decrypt_data(event['full_name'])
            
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
        """Добавляет лист со статистикой"""
        
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
        from collections import Counter
        
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

# ================================================================
# 3. СИСТЕМА ПОИСКА И ФИЛЬТРОВ
# ================================================================

class SearchManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def search_events(self, chat_id: int, query: str, filters: Dict = None) -> List[Dict]:
        """Универсальный поиск по событиям"""
        
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
        
        results = self.db.execute_with_retry(final_query, tuple(params), fetch="all")
        
        # Расшифровываем имена
        from main import decrypt_data
        
        decrypted_results = []
        for result in results:
            result_dict = dict(result)
            try:
                result_dict['full_name'] = decrypt_data(result_dict['full_name'])
            except ValueError:
                result_dict['full_name'] = "Ошибка дешифрации"
            decrypted_results.append(result_dict)
        
        return decrypted_results

    def get_available_event_types(self, chat_id: int) -> List[str]:
        """Получает список всех типов событий для фильтров"""
        result = self.db.execute_with_retry('''
            SELECT DISTINCT ee.event_type 
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            ORDER BY ee.event_type
        ''', (chat_id,), fetch="all")
        
        return [row['event_type'] for row in result]

# ================================================================
# 4. ШАБЛОНЫ СОБЫТИЙ
# ================================================================

class EventTemplate:
    def __init__(self, name: str, events: List[Dict]):
        self.name = name
        self.events = events  # [{'type': 'Медосмотр', 'interval_days': 365}, ...]

class TemplateManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.predefined_templates = self._load_predefined_templates()
    
    def _load_predefined_templates(self) -> Dict[str, EventTemplate]:
        """Загружает предустановленные шаблоны"""
        templates = {
            'carpenter': EventTemplate(
                name="Плотник",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Обучение работам на высоте (2 группа)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний работ на высоте (2 группа)', 'interval_days': 365},
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            ),
            'painter': EventTemplate(
                name="Маляр",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Обучение работам на высоте (2 группа)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний работ на высоте (2 группа)', 'interval_days': 365},
                    {'type': 'Инструктаж электробезопасности (1 группа)', 'interval_days': 365}
                ]
            ),
            'maintenance_worker': EventTemplate(
                name="Рабочий по комплексному обслуживанию и ремонту зданий",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Обучение работам на высоте (2 группа)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний работ на высоте (2 группа)', 'interval_days': 365},
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            ),
            'janitor': EventTemplate(
                name="Дворник",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 730},  # 2 года
                    {'type': 'Проверка знаний ОТ (П-2, П-3)', 'interval_days': 1095},  # 3 года
                    {'type': 'Инструктаж электробезопасности (1 группа)', 'interval_days': 365}
                ]
            ),
            'cleaner': EventTemplate(
                name="Уборщик производственных помещений",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3)', 'interval_days': 1095},  # 3 года
                    {'type': 'Инструктаж электробезопасности (1 группа)', 'interval_days': 365}
                ]
            ),
            'senior_master': EventTemplate(
                name="Старший мастер",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 730},  # 2 года
                    {'type': 'Проверка знаний ОТ (П-1, П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний ОТ (П-5.10, П-5.11)', 'interval_days': 365},
                    {'type': 'Обучение работам на высоте (3 группа)', 'interval_days': 1825},  # 5 лет
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            ),
            'master': EventTemplate(
                name="Мастер",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 730},  # 2 года
                    {'type': 'Проверка знаний ОТ (П-1, П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний ОТ (П-5.10, П-5.11)', 'interval_days': 365},
                    {'type': 'Обучение работам на высоте (3 группа)', 'interval_days': 1825},  # 5 лет
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            )
        }
        return templates
    
    def get_template_list(self) -> List[Dict]:
        """Возвращает список доступных шаблонов"""
        templates = []
        for key, template in self.predefined_templates.items():
            templates.append({
                'key': key,
                'name': template.name,
                'events_count': len(template.events),
                'description': ', '.join([f"{e['type']} ({e['interval_days']}д)" for e in template.events[:3]])
            })
        return templates
    
    async def apply_template(self, employee_id: int, template_key: str, base_date: datetime = None) -> bool:
        """Применяет шаблон к сотруднику"""
        if template_key not in self.predefined_templates:
            return False
        
        template = self.predefined_templates[template_key]
        base_date = base_date or datetime.now().date()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                for event in template.events:
                    # Проверяем, нет ли уже такого события
                    cursor.execute(
                        "SELECT id FROM employee_events WHERE employee_id = ? AND event_type = ?",
                        (employee_id, event['type'])
                    )
                    
                    if not cursor.fetchone():  # Добавляем только если события нет
                        next_date = base_date + timedelta(days=event['interval_days'])
                        
                        cursor.execute('''
                            INSERT INTO employee_events 
                            (employee_id, event_type, last_event_date, interval_days, next_notification_date)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            employee_id,
                            event['type'],
                            base_date.isoformat(),
                            event['interval_days'],
                            next_date.isoformat()
                        ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error applying template: {e}")
            return False

# ================================================================
# ФУНКЦИИ ИНИЦИАЛИЗАЦИИ (вызываются из main.py)
# ================================================================

def init_phase1_managers(db_manager):
    """Инициализация менеджеров Фазы 1"""
    notification_manager = NotificationManager(db_manager)
    excel_exporter = ExcelExporter(db_manager)
    search_manager = SearchManager(db_manager)
    template_manager = TemplateManager(db_manager)
    
    return notification_manager, excel_exporter, search_manager, template_manager