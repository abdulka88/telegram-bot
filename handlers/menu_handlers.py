"""
Обработчики главного меню и навигации
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.utils import create_callback_data, parse_callback_data
from core.security import is_admin
from core.database import db_manager

# Setup logging
logger = logging.getLogger(__name__)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает главное меню бота"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    user_is_admin = is_admin(chat_id, user_id)
    
    # Создаем клавиатуру меню
    keyboard = [
        [InlineKeyboardButton("📅 Мои события", callback_data=create_callback_data("my_events"))],
    ]
    
    if user_is_admin:
        admin_buttons = [
            [
                InlineKeyboardButton("👥 Сотрудники", callback_data=create_callback_data("list_employees")),
                InlineKeyboardButton("👨‍💼 Добавить сотрудника", callback_data=create_callback_data("add_employee"))
            ],
            [
                InlineKeyboardButton("🔍 Поиск", callback_data=create_callback_data("search_menu")),
                InlineKeyboardButton("📊 Дашборд", callback_data=create_callback_data("dashboard"))
            ],
            [
                InlineKeyboardButton("📋 Шаблоны", callback_data=create_callback_data("templates")),
                InlineKeyboardButton("📁 Экспорт", callback_data=create_callback_data("export_menu"))
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data=create_callback_data("settings")),
                InlineKeyboardButton("🤖 Отчеты", callback_data=create_callback_data("reports_menu"))
            ]
        ]
        keyboard.extend(admin_buttons)
    
    keyboard.append([InlineKeyboardButton("📚 Помощь", callback_data=create_callback_data("help"))])
    
    menu_text = (
        "🤖 <b>Telegram Бот управления периодическими событиями</b>\n\n"
        "Добро пожаловать в систему управления периодическими событиями сотрудников!\n\n"
        "📅 <b>Основные функции:</b>\n"
        "• Отслеживание периодических событий (медосмотры, инструктажи и т.д.)\n"
        "• Автоматические уведомления за 90/30/7/1-3 дня до события\n"
        "• Расширенная аналитика и прогнозирование\n"
        "• Экспорт данных в Excel/CSV\n"
        "• Управление шаблонами событий по должностям\n\n"
    )
    
    if user_is_admin:
        menu_text += (
            "👨‍💼 <b>Функции администратора:</b>\n"
            "• Управление сотрудниками и их событиями\n"
            "• Расширенный поиск и фильтрация\n"
            "• Дашборд с аналитикой в реальном времени\n"
            "• Настройка системы уведомлений\n"
            "• Автоматические отчеты\n\n"
        )
    
    menu_text += "Выберите действие из меню ниже:"
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=chat_id,
        text=menu_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Основной обработчик callback-запросов меню"""
    logger.info(f"📥 Получен callback запрос: {update.callback_query.data if update.callback_query else 'None'}")
    
    # Additional logging to debug the issue
    logger.info(f"🔍 Update type: {type(update)}")
    logger.info(f"🔍 Callback query: {update.callback_query if update.callback_query else 'No callback query'}")
    
    query = update.callback_query
    
    # Обработка таймаутов при ответе на callback
    try:
        await query.answer()
        logger.info("✅ Ответ на callback запрос отправлен")
    except Exception as e:
        logger.warning(f"Failed to answer callback query (network timeout): {e}")
        # Продолжаем выполнение несмотря на таймаут
    
    try:
        data = parse_callback_data(query.data)
        logger.info(f"📝 Распарсенные данные: {data}")
        action = data.get('action')
        
        if not action:
            logger.warning("❌ Не найдено действие в callback данных")
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Неизвестная команда"
            )
            return
        
        logger.info(f"🎯 Выполняется действие: {action}")
        
        # Импортируем обработчики по мере необходимости, чтобы избежать циклических импортов
        if action == "menu":
            await show_menu(update, context)
            
        elif action == "help":
            await help_command(update, context)
            
        elif action == "my_events":
            from handlers.event_handlers import my_events
            await my_events(update, context)
            
        elif action == "add_employee":
            from handlers.employee_handlers import add_employee_start
            await add_employee_start(update, context)
            
        elif action == "list_employees":
            from handlers.employee_handlers import list_employees
            await list_employees(update, context)
            
        elif action == "all_events":
            from handlers.event_handlers import all_events
            await all_events(update, context)
            
        elif action == "search_menu":
            from handlers.search_handlers import search_menu_start
            await search_menu_start(update, context)
            
        elif action == "export_menu":
            from handlers.export_handlers import export_menu_start
            await export_menu_start(update, context)
            
        elif action == "templates":
            from handlers.template_handlers import templates_menu
            await templates_menu(update, context)
            
        elif action == "settings":
            await settings_menu(update, context)
            
        # Обработка действий с параметрами
        elif action == "select_employee":
            employee_id = data.get('id')
            if employee_id:
                context.user_data['selected_employee'] = employee_id
                from handlers.employee_handlers import view_employee_details
                await view_employee_details(update, context)
                
        elif action == "emp_page":
            page = data.get('page', 0)
            context.user_data['employee_page'] = page
            from handlers.employee_handlers import list_employees
            await list_employees(update, context)
            
        # Новые обработчики поиска
        elif action == "search_filter":
            from handlers.search_handlers import search_by_filter
            await search_by_filter(update, context)
            
        elif action == "search_employees":
            from handlers.search_handlers import search_employees
            await search_employees(update, context)
            
        elif action == "employee_events":
            from handlers.search_handlers import show_employee_events
            await show_employee_events(update, context)
            
        elif action == "search_by_type":
            from handlers.search_handlers import search_by_event_type
            await search_by_event_type(update, context)
            
        elif action == "search_event_type":
            from handlers.search_handlers import search_events_by_type
            await search_events_by_type(update, context)
            
        # Обработчики дашборда
        elif action == "dashboard":
            from handlers.dashboard_handlers import dashboard_main
            await dashboard_main(update, context)
            
        elif action == "dashboard_analytics":
            from handlers.dashboard_handlers import dashboard_analytics
            await dashboard_analytics(update, context)
            
        elif action == "dashboard_employees":
            from handlers.dashboard_handlers import dashboard_employees
            await dashboard_employees(update, context)
            
        elif action == "dashboard_performance":
            from handlers.dashboard_handlers import dashboard_performance
            await dashboard_performance(update, context)
            
        elif action == "dashboard_alerts":
            from handlers.dashboard_handlers import dashboard_alerts
            await dashboard_alerts(update, context)
            
        elif action == "dashboard_timeline":
            from handlers.dashboard_handlers import dashboard_timeline
            await dashboard_timeline(update, context)
            
        # Обработчики текстового поиска
        elif action == "text_search_start":
            from handlers.search_handlers import text_search_start
            await text_search_start(update, context)
            
        elif action == "quick_text_search":
            from handlers.search_handlers import quick_text_search
            await quick_text_search(update, context)
            
        elif action == "text_search_page":
            from handlers.search_handlers import text_search_page
            await text_search_page(update, context)
            
        # Обработчики расширенной аналитики
        elif action == "analytics_menu":
            from handlers.analytics_handlers import analytics_main_menu
            await analytics_main_menu(update, context)
            
        elif action == "analytics_trends":
            from handlers.analytics_handlers import analytics_trends
            await analytics_trends(update, context)
            
        elif action == "analytics_timeline":
            from handlers.analytics_handlers import analytics_timeline
            await analytics_timeline(update, context)
            
        elif action == "analytics_forecast":
            from handlers.analytics_handlers import analytics_forecast
            await analytics_forecast(update, context)
            
        elif action == "analytics_efficiency":
            from handlers.analytics_handlers import analytics_efficiency
            await analytics_efficiency(update, context)
            
        elif action == "analytics_summary":
            from handlers.analytics_handlers import analytics_summary
            await analytics_summary(update, context)
            
        elif action == "analytics_export_excel":
            from handlers.analytics_handlers import analytics_export_excel
            await analytics_export_excel(update, context)
            
        # Обработчики детальных временных диаграмм
        elif action == "analytics_monthly_chart":
            from handlers.analytics_handlers import show_monthly_chart
            await show_monthly_chart(update, context)
            
        elif action == "analytics_weekly_chart":
            from handlers.analytics_handlers import show_weekly_chart
            await show_weekly_chart(update, context)
            
        elif action == "analytics_daily_chart":
            from handlers.analytics_handlers import show_daily_chart
            await show_daily_chart(update, context)
            
        # Обработчики автоматических отчетов
        elif action == "reports_menu":
            from handlers.reports_handlers import reports_main_menu
            await reports_main_menu(update, context)
            
        elif action == "reports_settings":
            from handlers.reports_handlers import reports_settings
            await reports_settings(update, context)
            
        elif action == "request_report":
            from handlers.reports_handlers import request_report
            await request_report(update, context)
            
        elif action == "generate_daily":
            from handlers.reports_handlers import generate_daily_report
            await generate_daily_report(update, context)
            
        elif action == "generate_weekly":
            from handlers.reports_handlers import generate_weekly_report
            await generate_weekly_report(update, context)
            
        elif action == "generate_monthly":
            from handlers.reports_handlers import generate_monthly_report
            await generate_monthly_report(update, context)
            
        elif action == "generate_full":
            from handlers.reports_handlers import generate_full_report
            await generate_full_report(update, context)
            
        elif action == "toggle_daily_reports":
            from handlers.reports_handlers import toggle_daily_reports
            await toggle_daily_reports(update, context)
            
        elif action == "toggle_weekly_reports":
            from handlers.reports_handlers import toggle_weekly_reports
            await toggle_weekly_reports(update, context)
            
        elif action == "toggle_monthly_reports":
            from handlers.reports_handlers import toggle_monthly_reports
            await toggle_monthly_reports(update, context)
            
        elif action == "test_report":
            from handlers.reports_handlers import test_report
            await test_report(update, context)
            
        # Обработчики расширенного прогнозирования
        elif action == "advanced_workload_forecast":
            from handlers.analytics_handlers import advanced_workload_forecast
            await advanced_workload_forecast(update, context)
            
        elif action == "forecast_short":
            from handlers.analytics_handlers import forecast_short
            await forecast_short(update, context)
            
        elif action == "forecast_medium":
            from handlers.analytics_handlers import forecast_medium
            await forecast_medium(update, context)
            
        elif action == "forecast_long":
            from handlers.analytics_handlers import forecast_long
            await forecast_long(update, context)
            
        # Обработчики настроек
        elif action == "set_notif_days":
            from handlers.settings_handlers import set_notification_days
            await set_notification_days(update, context)
            
        elif action == "set_timezone":
            from handlers.settings_handlers import set_timezone
            await set_timezone(update, context)
            
        # Обработчики экспорта
        elif action == "export":
            from handlers.export_handlers import handle_export
            await handle_export(update, context)
            
        # Обработчики шаблонов
        elif action == "select_template":
            from handlers.template_handlers import select_employee_for_template
            await select_employee_for_template(update, context)
            
        elif action == "apply_template":
            from handlers.template_handlers import apply_template_to_employee
            await apply_template_to_employee(update, context)
            
        # Обработчики редактирования сотрудников
        elif action == "edit_employee":
            from handlers.employee_handlers import edit_employee_start
            await edit_employee_start(update, context)
            
        # Обработчики сохранения настроек
        elif action == "save_notif_days":
            from handlers.settings_handlers import save_notification_days
            await save_notification_days(update, context)
            
        elif action == "save_timezone":
            from handlers.settings_handlers import save_timezone
            await save_timezone(update, context)
            
        # Обработчики редактирования сотрудников
        elif action == "edit_employee":
            from handlers.employee_handlers import edit_employee_start
            await edit_employee_start(update, context)
            
        elif action == "edit_name":
            from handlers.employee_handlers import edit_employee_name
            await edit_employee_name(update, context)
            
        elif action == "edit_position":
            from handlers.employee_handlers import edit_employee_position
            await edit_employee_position(update, context)
            
        elif action == "save_position":
            from handlers.employee_handlers import save_employee_position
            await save_employee_position(update, context)
            
        # Обработчики добавления событий к сотруднику
        elif action == "add_event_to_employee":
            from handlers.employee_handlers import add_event_to_employee
            await add_event_to_employee(update, context)
            
        # Обработчики удаления сотрудника
        elif action == "delete_employee":
            from handlers.employee_handlers import delete_employee
            await delete_employee(update, context)
            
        elif action == "confirm_delete":
            from handlers.employee_handlers import confirm_delete_employee
            await confirm_delete_employee(update, context)
            
        else:
            logger.warning(f"❌ Неизвестное действие: {action}")
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Неизвестная команда"
            )
            
    except Exception as e:
        logger.error(f"Error in menu_handler: {e}", exc_info=True)
        logger.error(f"Update details: {update}")
        logger.error(f"Context details: {context}")
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Произошла ошибка при обработке команды"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по командам"""
    help_text = (
        "📚 <b>Справка по системе управления периодическими событиями</b>\n\n"
        
        "🎯 <b>Основные функции:</b>\n"
        "• 📅 Отслеживание событий сотрудников\n"
        "• 🔔 Автоматические уведомления (90-30-7-3 дня)\n"
        "• 📊 Экспорт данных в Excel/CSV\n"
        "• 🔍 Расширенный поиск и фильтрация\n"
        "• 📋 Готовые шаблоны для должностей\n\n"
        
        "🔍 <b>Система поиска:</b>\n"
        "• 🔴 Быстрые фильтры (просроченные, критичные, срочные)\n"
        "• 👥 Поиск по сотрудникам с детальным просмотром\n"
        "• 📋 Фильтрация по типу события\n"
        "• 📊 Статистика и пагинация результатов\n"
        "• 📁 Экспорт результатов поиска\n\n"
        
        "👤 <b>Для всех пользователей:</b>\n"
        "/start - Начать работу\n"
        "/menu - Главное меню\n"
        "/help - Эта справка\n"
        "📅 Мои события - Ваши предстоящие события\n\n"
        
        "👨‍💼 <b>Для администраторов:</b>\n"
        "• 📊 Дашборд - аналитика и статистика в реальном времени\n"
        "• 🔍 Расширенный поиск с фильтрами и пагинацией\n"
        "• 👥 Управление сотрудниками с шаблонами событий\n"
        "• 📁 Экспорт данных в Excel/CSV с форматированием\n"
        "• ⚙️ Настройка уведомлений и часовых поясов\n\n"
        
        "📊 <b>Дашборд администратора:</b>\n"
        "• 📈 Общая статистика с визуализацией\n"
        "• 👥 Анализ сотрудников по уровню риска\n"
        "• 📋 Аналитика по должностям и типам событий\n"
        "• 📅 Временной анализ и тренды\n"
        "• 🚨 Предупреждения и рекомендации\n"
        "• ⚡ Метрики производительности системы\n\n"
        
        "📋 <b>Доступные должности:</b>\n"
        "• Плотник\n"
        "• Маляр\n"
        "• Рабочий по комплексному обслуживанию и ремонту зданий\n"
        "• Дворник\n"
        "• Уборщик производственных помещений\n"
        "• Мастер / Старший мастер\n\n"
        
        "🔔 <b>Система уведомлений:</b>\n"
        "• 🟢 За 90 дней - первое уведомление\n"
        "• 🟡 За 30 дней - предупреждение\n"
        "• 🟠 За 7 дней - срочно\n"
        "• 🔴 За 1-3 дня - критично (ежедневно)\n"
        "• ⚫ Просрочено - ежедневно + эскалация\n\n"
        
        "❓ <b>Нужна помощь?</b>\n"
        "Обратитесь к администратору системы."
    )

    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню настроек"""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Только администратор может изменять настройки"
        )
        return

    keyboard = [
        [InlineKeyboardButton("⏰ Дни уведомлений", callback_data=create_callback_data("set_notif_days"))],
        [InlineKeyboardButton("🕒 Часовой пояс", callback_data=create_callback_data("set_timezone"))],
        [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
    ]

    settings_text = (
        "⚙️ <b>Настройки системы</b>\n\n"
        "Здесь вы можете настроить:\n\n"
        "⏰ <b>Дни уведомлений</b> - за сколько дней до события отправлять первое уведомление\n"
        "🕒 <b>Часовой пояс</b> - для корректного времени отправки уведомлений\n\n"
        "Выберите параметр для изменения:"
    )

    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=settings_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
