"""
Обработчики расширенной аналитики для Telegram бота
Включает тренды, прогнозы и детальную статистику
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.utils import create_callback_data, parse_callback_data
from core.security import is_admin
from managers.advanced_analytics_manager import AdvancedAnalyticsManager
from managers.export_manager import ExportManager
from core.database import db_manager

# Инициализируем менеджер расширенной аналитики
advanced_analytics_manager = AdvancedAnalyticsManager(db_manager)
export_manager = ExportManager(db_manager)

logger = logging.getLogger(__name__)

async def analytics_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню расширенной аналитики"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может просматривать аналитику")
        return
    
    text = (
        "📊 <b>Расширенная аналитика</b>\n\n"
        "🔍 Выберите тип анализа для получения детальной информации:\n\n"
        "📈 <b>Тренды</b> - анализ изменений за период\n"
        "⏰ <b>Временной анализ</b> - статистика по неделям и месяцам\n"
        "🎯 <b>Прогнозы</b> - предсказание загрузки\n"
        "⚡ <b>Эффективность</b> - показатели соблюдения сроков"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📈 Анализ трендов", callback_data=create_callback_data("analytics_trends")),
            InlineKeyboardButton("⏰ Временной анализ", callback_data=create_callback_data("analytics_timeline"))
        ],
        [
            InlineKeyboardButton("🎯 Прогнозы нагрузки", callback_data=create_callback_data("analytics_forecast")),
            InlineKeyboardButton("⚡ Эффективность", callback_data=create_callback_data("analytics_efficiency"))
        ],
        [
            InlineKeyboardButton("🔮 Расширенные прогнозы", callback_data=create_callback_data("advanced_workload_forecast")),
            InlineKeyboardButton("📊 Сводный отчет", callback_data=create_callback_data("analytics_summary"))
        ],
        [
            InlineKeyboardButton("🔄 Автоматические отчеты", callback_data=create_callback_data("reports_menu"))
        ],
        [
            InlineKeyboardButton("🔙 К дашборду", callback_data=create_callback_data("dashboard"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def analytics_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Анализ трендов событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем трендовый анализ
    trends = advanced_analytics_manager.get_trends_analysis(chat_id, 6)
    
    if trends.get('trend') == 'no_data':
        text = (
            "📈 <b>Анализ трендов</b>\n\n"
            "❌ Недостаточно данных для анализа трендов\n\n"
            "💡 Добавьте больше событий и повторите анализ через некоторое время."
        )
    else:
        total_trend = trends.get('total_events_trend', {})
        overdue_trend = trends.get('overdue_trend', {})
        summary = trends.get('period_summary', {})
        predictions = trends.get('predictions', {})
        
        text_lines = [
            "📈 <b>Анализ трендов (6 месяцев)</b>",
            "",
            "📊 <b>Общие события:</b>",
            f"   {advanced_analytics_manager.generate_text_charts(total_trend, 'trend')}",
            f"   {total_trend.get('description', 'Нет данных')}",
            "",
            "🔴 <b>Просроченные события:</b>",
            f"   {advanced_analytics_manager.generate_text_charts(overdue_trend, 'trend')}",
            f"   {overdue_trend.get('description', 'Нет данных')}",
            "",
            "📋 <b>Сводка за период:</b>",
            f"📅 Месяцев в анализе: {summary.get('total_months', 0)}",
            f"⭕ Среднее событий/месяц: {summary.get('avg_events_per_month', 0):.1f}",
            f"📈 Пик событий: {summary.get('max_events_month', 0)}",
            f"📉 Минимум событий: {summary.get('min_events_month', 0)}",
            f"🔴 Всего просрочено: {summary.get('total_overdue', 0)}",
        ]
        
        # Добавляем прогнозы если есть
        if predictions:
            text_lines.extend(["", "🔮 <b>Прогнозы:</b>"])
            if 'next_month_events' in predictions:
                pred = predictions['next_month_events']
                text_lines.append(f"📈 Следующий месяц: ~{pred['estimate']} событий ({pred['confidence']} уверенность)")
            if 'next_month_overdue' in predictions:
                pred = predictions['next_month_overdue']
                text_lines.append(f"🔴 Ожидаемые просрочки: ~{pred['estimate']} ({pred['risk_level']} риск)")
        
        text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Детальная статистика", callback_data=create_callback_data("analytics_detailed_trends")),
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_trends"))
        ],
        [
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def analytics_timeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Временной анализ событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем недельную аналитику
    weekly_stats = advanced_analytics_manager.get_weekly_analysis(chat_id, 8)
    
    text_lines = [
        "⏰ <b>Временной анализ</b>",
        "",
        "📅 <b>Статистика по неделям (последние 8 недель):</b>",
        ""
    ]
    
    if not weekly_stats:
        text_lines.extend([
            "❌ Нет данных для временного анализа",
            "",
            "💡 Добавьте события для получения статистики"
        ])
    else:
        # Показываем последние 5 недель
        recent_weeks = list(weekly_stats.items())[-5:]
        
        for week, data in recent_weeks:
            week_display = week.replace('W', ' неделя ')
            total = data['total']
            overdue = data['overdue']
            
            # Определяем статус недели
            if overdue > 5:
                week_emoji = "🔴"
                status = "критичная"
            elif overdue > 2:
                week_emoji = "🟡"
                status = "напряженная"
            elif total > 10:
                week_emoji = "🟠"
                status = "загруженная"
            else:
                week_emoji = "🟢"
                status = "спокойная"
            
            text_lines.extend([
                f"{week_emoji} <b>{week_display}</b> ({status})",
                f"   📊 Всего событий: {total}",
                f"   🔴 Просрочено: {overdue}",
                ""
            ])
        
        # Добавляем распределение по дням недели для последней недели
        if recent_weeks:
            last_week_data = recent_weeks[-1][1]
            days_data = last_week_data.get('days', {})
            
            if days_data:
                text_lines.extend([
                    "📅 <b>Распределение по дням (последняя неделя):</b>",
                    ""
                ])
                
                for day, count in days_data.items():
                    if count > 0:
                        bar = "█" * min(count, 10)
                        text_lines.append(f"{day}: {bar} {count}")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Месячная статистика", callback_data=create_callback_data("analytics_monthly_chart")),
            InlineKeyboardButton("📈 Недельная статистика", callback_data=create_callback_data("analytics_weekly_chart"))
        ],
        [
            InlineKeyboardButton("📅 Дневная статистика", callback_data=create_callback_data("analytics_daily_chart")),
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_timeline"))
        ],
        [
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def analytics_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Прогноз рабочей нагрузки"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем прогноз на 30 дней
    forecast = advanced_analytics_manager.get_workload_forecast(chat_id, 30)
    
    daily_forecast = forecast.get('daily_forecast', [])
    summary = forecast.get('summary', {})
    
    text_lines = [
        "🎯 <b>Прогноз рабочей нагрузки</b>",
        f"📅 Период: следующие {summary.get('forecast_period', 30)} дней",
        "",
        "📊 <b>Общая статистика:</b>",
        f"📈 Всего событий: {summary.get('total_events', 0)}",
        f"⭕ Среднее в день: {summary.get('avg_per_day', 0):.1f}",
        ""
    ]
    
    if summary.get('peak_day') and summary.get('peak_count', 0) > 0:
        text_lines.extend([
            f"🔥 <b>Пиковый день:</b> {summary['peak_day']}",
            f"   📊 Событий: {summary['peak_count']}",
            ""
        ])
    
    if daily_forecast:
        text_lines.append("📅 <b>Ближайшие дни с высокой нагрузкой:</b>")
        text_lines.append("")
        
        # Показываем только дни с нагрузкой
        high_load_days = [day for day in daily_forecast if day['events_count'] >= 3][:7]
        
        if high_load_days:
            for day in high_load_days:
                date_obj = datetime.strptime(day['event_date'], '%Y-%m-%d')
                date_display = date_obj.strftime('%d.%m (%a)')
                
                text_lines.append(
                    f"{day['load_emoji']} <b>{date_display}</b> - {day['events_count']} событий"
                )
                
                # Показываем типы событий для дней с высокой нагрузкой
                if day['events_count'] >= 5:
                    event_types = day.get('event_types', '')[:50]
                    if event_types:
                        text_lines.append(f"   📋 {event_types}...")
                
                text_lines.append("")
        else:
            text_lines.append("✅ Нет дней с высокой нагрузкой в ближайшем периоде")
    else:
        text_lines.append("📋 Нет запланированных событий на ближайший период")
    
    # Добавляем рекомендации
    if summary.get('total_events', 0) > 0:
        avg_per_day = summary.get('avg_per_day', 0)
        text_lines.extend([
            "",
            "💡 <b>Рекомендации:</b>"
        ])
        
        if avg_per_day > 5:
            text_lines.append("⚠️ Высокая средняя нагрузка - рассмотрите перераспределение")
        elif avg_per_day > 3:
            text_lines.append("🟡 Умеренная нагрузка - следите за пиковыми днями")
        else:
            text_lines.append("🟢 Нормальная нагрузка - система под контролем")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Детальный прогноз", callback_data=create_callback_data("analytics_detailed_forecast")),
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_forecast"))
        ],
        [
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def analytics_efficiency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Анализ эффективности работы с событиями"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем метрики эффективности
    efficiency = advanced_analytics_manager.get_efficiency_metrics(chat_id)
    
    text_lines = [
        "⚡ <b>Анализ эффективности</b>",
        "",
        f"📊 <b>Общая оценка: {efficiency.get('efficiency_grade', 'N/A')} {efficiency.get('efficiency_emoji', '')}</b>",
        "",
        "📈 <b>Ключевые показатели:</b>",
        f"✅ Соблюдение сроков: {efficiency.get('compliance_rate', 0)}%",
        f"📅 Всего событий: {efficiency.get('total_events', 0)}",
        f"🟢 Вовремя: {efficiency.get('on_time_events', 0)}",
        f"🔴 Просрочено: {efficiency.get('overdue_events', 0)}",
        ""
    ]
    
    if efficiency.get('avg_overdue_days', 0) > 0:
        text_lines.extend([
            f"⏰ Средняя просрочка: {efficiency.get('avg_overdue_days', 0):.1f} дней",
            ""
        ])
    
    # Показываем прогресс-бар соблюдения
    compliance_rate = efficiency.get('compliance_rate', 0)
    bar_length = int(compliance_rate / 10)
    compliance_bar = "🟢" * bar_length + "⚪" * (10 - bar_length)
    text_lines.extend([
        "📊 <b>Визуализация соблюдения:</b>",
        f"{compliance_bar} {compliance_rate}%",
        ""
    ])
    
    # Добавляем рекомендации
    recommendations = efficiency.get('recommendations', [])
    if recommendations:
        text_lines.append("💡 <b>Рекомендации по улучшению:</b>")
        for rec in recommendations:
            text_lines.append(f"   {rec}")
    else:
        text_lines.append("🎉 <b>Отличная работа!</b> Рекомендаций нет - система работает эффективно.")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 История эффективности", callback_data=create_callback_data("analytics_efficiency_history")),
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_efficiency"))
        ],
        [
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def analytics_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сводный аналитический отчет"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем все необходимые данные
    trends = advanced_analytics_manager.get_trends_analysis(chat_id, 3)
    efficiency = advanced_analytics_manager.get_efficiency_metrics(chat_id)
    forecast = advanced_analytics_manager.get_workload_forecast(chat_id, 14)
    
    text_lines = [
        "📊 <b>Сводный аналитический отчет</b>",
        f"🕒 Создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "",
        "⚡ <b>Текущая эффективность:</b>",
        f"   {efficiency.get('efficiency_emoji', '📊')} {efficiency.get('efficiency_grade', 'N/A')} ({efficiency.get('compliance_rate', 0)}%)",
        ""
    ]
    
    # Тренды
    if trends.get('trend') != 'no_data':
        total_trend = trends.get('total_events_trend', {})
        text_lines.extend([
            "📈 <b>Тренд событий:</b>",
            f"   {advanced_analytics_manager.generate_text_charts(total_trend, 'trend')} {total_trend.get('description', '')}",
            ""
        ])
    
    # Прогноз на 2 недели
    forecast_summary = forecast.get('summary', {})
    if forecast_summary.get('total_events', 0) > 0:
        text_lines.extend([
            "🎯 <b>Прогноз на 2 недели:</b>",
            f"   📊 Ожидается событий: {forecast_summary.get('total_events', 0)}",
            f"   ⭕ Среднее в день: {forecast_summary.get('avg_per_day', 0):.1f}",
            ""
        ])
        
        if forecast_summary.get('peak_day'):
            text_lines.append(f"   🔥 Пиковый день: {forecast_summary['peak_day']} ({forecast_summary.get('peak_count', 0)} событий)")
            text_lines.append("")
    
    # Ключевые метрики
    text_lines.extend([
        "🎯 <b>Ключевые показатели:</b>",
        f"   📅 Всего событий в системе: {efficiency.get('total_events', 0)}",
        f"   🔴 Текущих просрочек: {efficiency.get('overdue_events', 0)}",
        ""
    ])
    
    # Статус системы
    overdue_events = efficiency.get('overdue_events', 0)
    total_events = efficiency.get('total_events', 0)
    
    if total_events == 0:
        system_status = "🔍 Нет данных"
        status_description = "Добавьте события для анализа"
    elif overdue_events == 0:
        system_status = "🟢 Отлично"
        status_description = "Все события выполняются вовремя"
    elif overdue_events / total_events <= 0.1:
        system_status = "🟡 Хорошо"
        status_description = "Небольшое количество просрочек"
    elif overdue_events / total_events <= 0.25:
        system_status = "🟠 Требует внимания"
        status_description = "Есть проблемы с соблюдением сроков"
    else:
        system_status = "🔴 Критично"
        status_description = "Много просроченных событий"
    
    text_lines.extend([
        f"🏆 <b>Статус системы: {system_status}</b>",
        f"   💬 {status_description}",
        ""
    ])
    
    # Рекомендации
    recommendations = efficiency.get('recommendations', [])
    if recommendations:
        text_lines.append("💡 <b>Приоритетные действия:</b>")
        for rec in recommendations[:2]:  # Показываем только топ-2
            text_lines.append(f"   {rec}")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📄 Экспорт в Excel", callback_data=create_callback_data("analytics_export_excel")),
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_summary"))
        ],
        [
            InlineKeyboardButton("📈 Детальная аналитика", callback_data=create_callback_data("analytics_trends")),
            InlineKeyboardButton("🎯 Прогнозы", callback_data=create_callback_data("analytics_forecast"))
        ],
        [
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_monthly_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать месячную диаграмму событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем детальные временные диаграммы
    charts = advanced_analytics_manager.get_detailed_timeline_charts(chat_id)
    monthly_data = charts.get('monthly', {})
    
    text_lines = [
        "📅 <b>Месячная диаграмма событий</b>",
        "",
        monthly_data.get('chart', '📊 Нет данных для отображения'),
        ""
    ]
    
    # Добавляем сводку
    summary = monthly_data.get('summary', {})
    if summary:
        text_lines.extend([
            "📊 <b>Сводка:</b>",
            f"📈 Всего событий: {summary.get('total_events', 0)}",
            f"🔴 Всего просрочек: {summary.get('total_overdue', 0)}",
            f"⭕ Среднее/месяц: {summary.get('avg_per_month', 0):.1f}"
        ])
        
        if summary.get('peak_month'):
            text_lines.append(f"🔥 Пиковый месяц: {summary['peak_month']} ({summary.get('peak_count', 0)} событий)")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Недельная диаграмма", callback_data=create_callback_data("analytics_weekly_chart")),
            InlineKeyboardButton("📈 Дневная диаграмма", callback_data=create_callback_data("analytics_daily_chart"))
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_monthly_chart")),
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_weekly_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать недельную диаграмму событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем детальные временные диаграммы
    charts = advanced_analytics_manager.get_detailed_timeline_charts(chat_id)
    weekly_data = charts.get('weekly', {})
    
    text_lines = [
        "📅 <b>Недельная диаграмма событий</b>",
        "",
        weekly_data.get('chart', '📊 Нет данных для отображения'),
        ""
    ]
    
    # Добавляем сводку
    summary = weekly_data.get('summary', {})
    if summary:
        text_lines.extend([
            "📊 <b>Сводка:</b>",
            f"📈 Всего событий: {summary.get('total_events', 0)}",
            f"🔴 Всего просрочек: {summary.get('total_overdue', 0)}",
            f"⭕ Среднее/неделю: {summary.get('avg_per_week', 0):.1f}"
        ])
        
        if summary.get('peak_week'):
            text_lines.append(f"🔥 Пиковая неделя: {summary['peak_week']} ({summary.get('peak_count', 0)} событий)")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Месячная диаграмма", callback_data=create_callback_data("analytics_monthly_chart")),
            InlineKeyboardButton("📈 Дневная диаграмма", callback_data=create_callback_data("analytics_daily_chart"))
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_weekly_chart")),
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_daily_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать дневную диаграмму событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем детальные временные диаграммы
    charts = advanced_analytics_manager.get_detailed_timeline_charts(chat_id)
    daily_data = charts.get('daily', {})
    
    text_lines = [
        "📅 <b>Дневная диаграмма событий</b>",
        "",
        daily_data.get('chart', '📊 Нет данных для отображения'),
        ""
    ]
    
    # Добавляем сводку
    summary = daily_data.get('summary', {})
    if summary:
        text_lines.extend([
            "📊 <b>Сводка:</b>",
            f"📈 Всего событий: {summary.get('total_events', 0)}",
            f"🔴 Всего просрочек: {summary.get('total_overdue', 0)}",
            f"📅 Дней с событиями: {summary.get('days_with_events', 0)}"
        ])
        
        if summary.get('peak_day'):
            peak_day_obj = datetime.strptime(summary['peak_day'], '%Y-%m-%d')
            peak_day_display = peak_day_obj.strftime('%d.%m.%Y')
            text_lines.append(f"🔥 Пиковый день: {peak_day_display} ({summary.get('peak_count', 0)} событий)")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Месячная диаграмма", callback_data=create_callback_data("analytics_monthly_chart")),
            InlineKeyboardButton("📈 Недельная диаграмма", callback_data=create_callback_data("analytics_weekly_chart"))
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("analytics_daily_chart")),
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def advanced_workload_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Расширенный прогноз рабочей нагрузки"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем расширенный прогноз на разные периоды
    periods = {'short': 7, 'medium': 30, 'long': 90}
    advanced_forecast = advanced_analytics_manager.get_advanced_workload_forecast(chat_id, periods)
    
    forecasts = advanced_forecast.get('forecasts', {})
    analysis = advanced_forecast.get('comparative_analysis', {})
    
    text_lines = [
        "🎯 <b>Расширенный прогноз нагрузки</b>",
        "",
        "🔮 <b>Прогнозы по периодам:</b>"
    ]
    
    period_names = {
        'short': 'Краткосрочный (7 дней)',
        'medium': 'Среднесрочный (30 дней)',
        'long': 'Долгосрочный (90 дней)'
    }
    
    for period_key, forecast_data in forecasts.items():
        forecast = forecast_data['forecast']
        risk = forecast_data['risk_assessment']
        summary = forecast['summary']
        
        period_name = period_names.get(period_key, period_key)
        
        text_lines.extend([
            "",
            f"📅 <b>{period_name}</b>",
            f"   🎯 Средняя нагрузка: {summary.get('avg_per_day', 0):.1f} событий/день",
            f"   📈 Всего событий: {summary.get('total_events', 0)}",
            f"   {risk['risk_emoji']} Уровень риска: {risk['risk_level']}"
        ])
        
        if summary.get('peak_day'):
            peak_date = datetime.strptime(summary['peak_day'], '%Y-%m-%d')
            text_lines.append(f"   🔥 Пик: {peak_date.strftime('%d.%m')} ({summary.get('peak_count', 0)} событий)")
    
    # Сравнительный анализ
    if analysis:
        text_lines.extend([
            "",
            "🔄 <b>Сравнительный анализ:</b>"
        ])
        
        trends = analysis.get('trends', {})
        if trends.get('load_trend'):
            trend_emoji = {
                'рост': '📈',
                'снижение': '📉',
                'стабильность': '➡️'
            }.get(trends['load_trend'], '📊')
            text_lines.append(f"   {trend_emoji} Тренд: {trends['load_trend']}")
        
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            text_lines.extend(["", "💡 <b>Ключевые рекомендации:</b>"])
            for rec in recommendations[:3]:  # Показываем только 3
                text_lines.append(f"   {rec}")
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Краткосрочный", callback_data=create_callback_data("forecast_short")),
            InlineKeyboardButton("📆 Среднесрочный", callback_data=create_callback_data("forecast_medium"))
        ],
        [
            InlineKeyboardButton("📇 Долгосрочный", callback_data=create_callback_data("forecast_long")),
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("advanced_workload_forecast"))
        ],
        [
            InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_detailed_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str) -> None:
    """Показать детальный прогноз для определенного периода"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Определяем количество дней
    period_days = {
        'short': 7,
        'medium': 30,
        'long': 90
    }
    
    period_names = {
        'short': 'Краткосрочный (7 дней)',
        'medium': 'Среднесрочный (30 дней)',
        'long': 'Долгосрочный (90 дней)'
    }
    
    days = period_days.get(period, 30)
    period_name = period_names.get(period, period)
    
    # Получаем детальный прогноз
    forecast = advanced_analytics_manager.get_workload_forecast(chat_id, days)
    
    summary = forecast.get('summary', {})
    metrics = forecast.get('workload_metrics', {})
    daily_forecast = forecast.get('daily_forecast', [])
    
    text_lines = [
        f"🎯 <b>Детальный прогноз: {period_name}</b>",
        "",
        "📊 <b>Общие метрики:</b>",
        f"📈 Всего событий: {summary.get('total_events', 0)}",
        f"⭕ Средняя нагрузка: {summary.get('avg_per_day', 0):.1f}/день"
    ]
    
    if summary.get('peak_day'):
        peak_date = datetime.strptime(summary['peak_day'], '%Y-%m-%d')
        text_lines.extend([
            f"🔥 Пиковый день: {peak_date.strftime('%d.%m.%Y')}",
            f"📈 Максимум событий: {summary.get('peak_count', 0)}"
        ])
    
    # Метрики нагрузки
    if metrics:
        text_lines.extend([
            "",
            "📊 <b>Анализ нагрузки:</b>",
            f"🔄 Общий уровень: {metrics.get('overall_load', 'неизвестно')}",
            f"🔴 Дней с высокой нагрузкой: {metrics.get('high_load_days', 0)}",
            f"🟡 Дней со средней нагрузкой: {metrics.get('medium_load_days', 0)}",
            f"🟢 Дней с низкой нагрузкой: {metrics.get('low_load_days', 0)}"
        ])
        
        if metrics.get('busiest_day') and metrics.get('busiest_day') != 'Н/Д':
            text_lines.extend([
                "",
                f"📅 Самый загруженный день: {metrics['busiest_day']}",
                f"🟢 Самый свободный день: {metrics.get('quietest_day', 'Н/Д')}"
            ])
    
    # Рекомендации
    recommendations = metrics.get('recommendations', [])
    if recommendations:
        text_lines.extend(["", "💡 <b>Рекомендации:</b>"])
        for rec in recommendations[:4]:  # Показываем только 4
            text_lines.append(f"   {rec}")
    
    # Показываем ключевые дни
    if daily_forecast:
        high_load_days = [d for d in daily_forecast if d.get('priority') in ['critical', 'high']][:5]
        if high_load_days:
            text_lines.extend(["", "🔥 <b>Ключевые дни:</b>"])
            for day in high_load_days:
                date_obj = datetime.strptime(day['event_date'], '%Y-%m-%d')
                date_display = date_obj.strftime('%d.%m (%a)')
                text_lines.append(
                    f"   {day['load_emoji']} {date_display}: {day['events_count']} событий"
                )
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Визуализация", callback_data=create_callback_data(f"forecast_chart_{period}")),
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data(f"forecast_{period}"))
        ],
        [
            InlineKeyboardButton("🔙 К прогнозам", callback_data=create_callback_data("advanced_workload_forecast"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# Обработчики для конкретных периодов
async def forecast_short(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Краткосрочный прогноз"""
    await show_detailed_forecast(update, context, 'short')

async def forecast_medium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Среднесрочный прогноз"""
    await show_detailed_forecast(update, context, 'medium')

async def forecast_long(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Долгосрочный прогноз"""
    await show_detailed_forecast(update, context, 'long')


async def analytics_export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Экспорт аналитического отчета в Excel"""
    query = update.callback_query
    await query.answer("📊 Генерирую Excel отчет...")
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может экспортировать отчеты")
        return
    
    try:
        # Генерируем полный аналитический отчет
        excel_buffer = await export_manager.export_analytics_report(chat_id, "full")
        
        # Создаем имя файла с датой
        filename = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        # Отправляем файл пользователю
        await context.bot.send_document(
            chat_id=user_id,
            document=excel_buffer,
            filename=filename,
            caption="📊 <b>Полный аналитический отчет</b>\n\n"
                   "Включает:\n"
                   "• Анализ трендов событий\n"
                   "• Прогнозы рабочей нагрузки\n"
                   "• Показатели эффективности\n"
                   "• Временные диаграммы\n"
                   "• Расширенное прогнозирование",
            parse_mode='HTML'
        )
        
        await query.edit_message_text(
            "✅ <b>Excel отчет создан и отправлен!</b>\n\n"
            "📄 Проверьте ваши файлы",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error exporting analytics to Excel: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка при создании Excel отчета</b>\n\n"
            "Попробуйте позже или обратитесь к администратору",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К аналитике", callback_data=create_callback_data("analytics_menu"))
            ]])
        )
