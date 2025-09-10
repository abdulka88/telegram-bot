"""
Обработчики дашборда администратора
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.utils import create_callback_data, parse_callback_data
from core.security import is_admin
from managers.dashboard_manager import DashboardManager
from core.database import db_manager

# Инициализируем менеджер дашборда
dashboard_manager = DashboardManager(db_manager)

logger = logging.getLogger(__name__)

async def dashboard_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главная страница дашборда администратора"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может просматривать дашборд")
        return
    
    # Получаем общую статистику
    stats = dashboard_manager.get_overview_statistics(chat_id)
    performance = dashboard_manager.get_performance_metrics(chat_id)
    alerts = dashboard_manager.get_alerts_and_recommendations(chat_id)
    
    main_stats = stats.get('main', {})
    
    # Формируем главный экран дашборда
    text_lines = [
        "📊 <b>Дашборд администратора</b>",
        f"🕒 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "",
        "📈 <b>Общая статистика:</b>",
        f"👥 Сотрудников: {main_stats.get('total_employees', 0)}",
        f"📅 Всего событий: {main_stats.get('total_events', 0)}",
        f"📊 Соблюдение плана: {performance.get('compliance_rate', 0)}%",
        "",
    ]
    
    # Статистика по статусам с прогресс-барами
    text_lines.append("🚦 <b>Статус событий:</b>")
    
    total = main_stats.get('total_events', 0)
    if total > 0:
        status_data = {
            'Просрочено': main_stats.get('overdue', 0),
            'Критично': main_stats.get('critical', 0),
            'Срочно': main_stats.get('urgent', 0),
            'Ближайшие': main_stats.get('upcoming', 0),
            'Плановые': main_stats.get('planned', 0)
        }
        
        status_emojis = {
            'Просрочено': '🔴',
            'Критично': '🔴', 
            'Срочно': '🟠',
            'Ближайшие': '🟡',
            'Плановые': '🟢'
        }
        
        for status, count in status_data.items():
            if count > 0:
                percentage = (count / total) * 100
                bar_length = max(1, int(percentage / 10))  # Масштабируем до 10 символов
                bar = "█" * bar_length
                emoji = status_emojis.get(status, '📊')
                text_lines.append(f"{emoji} {status}: {count} ({percentage:.1f}%) {bar}")
    else:
        text_lines.append("📋 Нет событий в системе")
    
    # Предупреждения и рекомендации
    if alerts:
        text_lines.extend(["", "🚨 <b>Внимание:</b>"])
        for alert in alerts[:3]:  # Показываем только топ-3
            text_lines.append(f"{alert['emoji']} {alert['title']}: {alert['message']}")
    
    text = "\n".join(text_lines)
    
    # Кнопки навигации по разделам дашборда
    keyboard = [
        [
            InlineKeyboardButton("📊 Аналитика", callback_data=create_callback_data("dashboard_analytics")),
            InlineKeyboardButton("👥 Сотрудники", callback_data=create_callback_data("dashboard_employees"))
        ],
        [
            InlineKeyboardButton("📋 По должностям", callback_data=create_callback_data("dashboard_positions")),
            InlineKeyboardButton("📅 По событиям", callback_data=create_callback_data("dashboard_events"))
        ],
        [
            InlineKeyboardButton("📈 Временной анализ", callback_data=create_callback_data("dashboard_timeline")),
            InlineKeyboardButton("⚡ Производительность", callback_data=create_callback_data("dashboard_performance"))
        ],
        [
            InlineKeyboardButton("🔮 Расширенная аналитика", callback_data=create_callback_data("analytics_menu")),
        ],
        [
            InlineKeyboardButton("🚨 Предупреждения", callback_data=create_callback_data("dashboard_alerts")),
            InlineKeyboardButton("📁 Экспорт отчета", callback_data=create_callback_data("dashboard_export"))
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def dashboard_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раздел аналитики с диаграммами"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    stats = dashboard_manager.get_overview_statistics(chat_id)
    
    text_lines = [
        "📊 <b>Аналитический обзор</b>",
        "",
        "📋 <b>ТОП-5 должностей по событиям:</b>"
    ]
    
    # Создаем диаграмму по должностям
    positions = stats.get('positions', [])[:5]
    if positions:
        position_data = {pos['position']: pos['event_count'] for pos in positions}
        chart = dashboard_manager.generate_text_chart(position_data, "bar", 15)
        text_lines.extend(["```", chart, "```", ""])
    else:
        text_lines.append("📋 Нет данных о должностях")
        text_lines.append("")
    
    # ТОП типов событий
    text_lines.append("🔄 <b>ТОП-5 типов событий:</b>")
    event_types = stats.get('event_types', [])[:5]
    if event_types:
        events_data = {et['event_type'][:20]: et['count'] for et in event_types}
        chart = dashboard_manager.generate_text_chart(events_data, "bar", 15)
        text_lines.extend(["```", chart, "```"])
    else:
        text_lines.append("📋 Нет данных о типах событий")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Детальная аналитика", callback_data=create_callback_data("dashboard_detailed")),
            InlineKeyboardButton("📈 Тренды", callback_data=create_callback_data("dashboard_trends"))
        ],
        [InlineKeyboardButton("🔙 К дашборду", callback_data=create_callback_data("dashboard"))]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def dashboard_employees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Анализ по сотрудникам - кто требует внимания"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    page = parse_callback_data(query.data).get('page', 0)
    
    employees = dashboard_manager.get_employee_analysis(chat_id)
    
    # Пагинация
    per_page = 8
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_employees = employees[start_idx:end_idx]
    
    text_lines = [
        "👥 <b>Анализ сотрудников</b>",
        f"📄 Страница {page + 1} из {(len(employees) + per_page - 1) // per_page}",
        "",
        "🎯 <b>Рейтинг по уровню внимания:</b>",
        ""
    ]
    
    if not page_employees:
        text_lines.append("👨‍💼 Нет данных о сотрудниках")
    else:
        for i, emp in enumerate(page_employees, start_idx + 1):
            name = emp['full_name'][:25]  # Обрезаем длинные имена
            position = emp['position'][:15]  # Обрезаем длинные должности
            
            text_lines.append(
                f"{i}. {emp['risk_emoji']} <b>{name}</b>\n"
                f"   💼 {position}\n"
                f"   📊 События: {emp['total_events']} | {emp['risk_text']}\n"
            )
    
    text = "\n".join(text_lines)
    
    # Кнопки пагинации
    keyboard = []
    
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(
            InlineKeyboardButton("⬅️ Пред", 
                callback_data=create_callback_data("dashboard_employees", page=page-1))
        )
    if end_idx < len(employees):
        pagination_buttons.append(
            InlineKeyboardButton("След ➡️", 
                callback_data=create_callback_data("dashboard_employees", page=page+1))
        )
    
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.extend([
        [InlineKeyboardButton("📊 Детали по сотрудникам", callback_data=create_callback_data("dashboard_emp_details"))],
        [InlineKeyboardButton("🔙 К дашборду", callback_data=create_callback_data("dashboard"))]
    ])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def dashboard_performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Метрики производительности системы"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    performance = dashboard_manager.get_performance_metrics(chat_id)
    
    general = performance.get('general', {})
    overdue = performance.get('overdue', {})
    
    text_lines = [
        "⚡ <b>Производительность системы</b>",
        "",
        "📊 <b>Общие метрики:</b>",
        f"👥 Активных сотрудников: {general.get('active_employees', 0)}",
        f"📅 Всего событий: {general.get('total_events', 0)}",
        f"⭕ Средний интервал: {general.get('avg_interval', 0):.0f} дней",
        "",
        f"📈 <b>Показатель соблюдения: {performance.get('compliance_rate', 0)}%</b>",
        ""
    ]
    
    # Визуализация соблюдения
    compliance = performance.get('compliance_rate', 0)
    bar_length = int(compliance / 10)
    compliance_bar = "🟢" * bar_length + "⚪" * (10 - bar_length)
    text_lines.append(f"Соблюдение плана: {compliance_bar} {compliance:.1f}%")
    text_lines.append("")
    
    # Метрики просрочек
    if overdue.get('total_overdue', 0) > 0:
        text_lines.extend([
            "⚠️ <b>Анализ просрочек:</b>",
            f"🔴 Всего просрочено: {overdue.get('total_overdue', 0)}",
            f"📅 Средняя просрочка: {overdue.get('avg_overdue_days', 0):.1f} дней",
            f"⏰ Максимальная просрочка: {overdue.get('max_overdue_days', 0):.0f} дней",
            ""
        ])
    
    # Календарный диапазон
    if general.get('earliest_event') and general.get('latest_event'):
        text_lines.extend([
            "📅 <b>Временной диапазон:</b>",
            f"⏪ Ранняя дата: {general.get('earliest_event')}",
            f"⏩ Поздняя дата: {general.get('latest_event')}"
        ])
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Подробная статистика", callback_data=create_callback_data("dashboard_detailed_stats")),
            InlineKeyboardButton("📈 Исторический анализ", callback_data=create_callback_data("dashboard_history"))
        ],
        [InlineKeyboardButton("🔙 К дашборду", callback_data=create_callback_data("dashboard"))]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def dashboard_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Предупреждения и рекомендации"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    alerts = dashboard_manager.get_alerts_and_recommendations(chat_id)
    
    text_lines = [
        "🚨 <b>Предупреждения и рекомендации</b>",
        ""
    ]
    
    if not alerts:
        text_lines.extend([
            "✅ <b>Отлично!</b>",
            "🎉 Все события под контролем",
            "📊 Никаких критичных проблем не обнаружено",
            "💪 Система работает стабильно"
        ])
    else:
        # Группируем предупреждения по уровням
        critical_alerts = [a for a in alerts if a['level'] == 'critical']
        warning_alerts = [a for a in alerts if a['level'] == 'warning']
        info_alerts = [a for a in alerts if a['level'] == 'info']
        
        if critical_alerts:
            text_lines.extend(["🚨 <b>Критичные проблемы:</b>"])
            for alert in critical_alerts:
                text_lines.extend([
                    f"{alert['emoji']} <b>{alert['title']}</b>",
                    f"   📋 {alert['message']}",
                    f"   💡 {alert['action']}",
                    ""
                ])
        
        if warning_alerts:
            text_lines.extend(["⚠️ <b>Предупреждения:</b>"])
            for alert in warning_alerts:
                text_lines.extend([
                    f"{alert['emoji']} <b>{alert['title']}</b>",
                    f"   📋 {alert['message']}",
                    f"   💡 {alert['action']}",
                    ""
                ])
        
        if info_alerts:
            text_lines.extend(["ℹ️ <b>Информация:</b>"])
            for alert in info_alerts:
                text_lines.extend([
                    f"{alert['emoji']} <b>{alert['title']}</b>",
                    f"   📋 {alert['message']}",
                    f"   💡 {alert['action']}",
                    ""
                ])
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 Детальный анализ проблем", callback_data=create_callback_data("dashboard_problem_analysis")),
            InlineKeyboardButton("📋 План действий", callback_data=create_callback_data("dashboard_action_plan"))
        ],
        [InlineKeyboardButton("🔙 К дашборду", callback_data=create_callback_data("dashboard"))]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def dashboard_timeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Временной анализ событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    timeline = dashboard_manager.get_timeline_analysis(chat_id, 12)
    
    text_lines = [
        "📈 <b>Временной анализ</b>",
        "",
        "📅 <b>События по месяцам (последние 6 мес.):</b>",
        ""
    ]
    
    if not timeline:
        text_lines.append("📊 Недостаточно данных для анализа")
    else:
        # Сортируем месяцы и берем последние 6
        sorted_months = sorted(timeline.keys())[-6:]
        
        if sorted_months:
            month_data = {}
            for month in sorted_months:
                total = timeline[month]['total']
                overdue = timeline[month]['overdue']
                month_name = datetime.strptime(month, '%Y-%m').strftime('%m/%y')
                month_data[month_name] = total
                
                # Добавляем детали
                text_lines.append(
                    f"📅 {month_name}: {total} событий "
                    f"({overdue} просрочено)" if overdue > 0 else f"📅 {month_name}: {total} событий ✅"
                )
            
            text_lines.append("")
            
            # Генерируем график
            if month_data:
                chart = dashboard_manager.generate_text_chart(month_data, "bar", 12)
                text_lines.extend(["📊 <b>График загрузки:</b>", "```", chart, "```"])
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Годовой анализ", callback_data=create_callback_data("dashboard_yearly")),
            InlineKeyboardButton("🔮 Прогнозы", callback_data=create_callback_data("dashboard_forecast"))
        ],
        [InlineKeyboardButton("🔙 К дашборду", callback_data=create_callback_data("dashboard"))]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )