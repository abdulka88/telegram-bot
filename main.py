"""
Главный файл Telegram бота для управления периодическими событиями сотрудников
Модульная архитектура с текстовым поиском
"""

import os
import sys
import logging
import platform
import traceback
import fcntl
from datetime import time as dt_time, timedelta

import pytz
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes
)
from telegram import Update

# Импорты модулей
from config.settings import BotConfig
from config.constants import ConversationStates
from core.database import db_manager
from core.utils import singleton_lock
from managers import init_managers
from handlers import (
    show_menu, menu_handler, help_command,
    add_employee_start, handle_contact, add_employee_name, handle_position_selection,
    list_employees, cancel_add_employee, cancel_add_event_to_employee,
    search_menu_start,
    dashboard_main, dashboard_analytics, dashboard_employees
)
from handlers.search_handlers import handle_text_search_input
from handlers.employee_handlers import (
    add_event_type, add_last_date, add_interval, edit_employee_name, save_employee_name,
    add_event_to_employee, add_event_to_employee_type, add_event_to_employee_date, 
    add_event_to_employee_interval
)
from handlers.export_handlers import export_menu_start, handle_export
from handlers.template_handlers import templates_menu, select_employee_for_template, apply_template_to_employee

# Удалена тестовая функция - используем основную логику

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Основной логгер
    logging.basicConfig(
        level=getattr(logging, BotConfig.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(BotConfig.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Снижаем уровень логирования для библиотек
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

async def global_error_handler(update, context):
    """Глобальный обработчик ошибок"""
    logger = logging.getLogger(__name__)
    
    try:
        error = context.error
        tb_list = traceback.format_exception(None, error, error.__traceback__)
        tb_string = ''.join(tb_list)
        
        logger.error(f"Exception while handling an update: {tb_string}")
        
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="😔 Произошла внутренняя ошибка. Попробуйте позже или обратитесь к администратору."
                )
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

async def start(update, context):
    """Команда /start - инициализация чата и показ меню"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    logger = logging.getLogger(__name__)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT admin_id FROM chat_settings WHERE chat_id = ?",
                (chat_id,)
            )
            settings = cursor.fetchone()

            if not settings:
                # Первый запуск - создаем настройки
                cursor.execute(
                    '''INSERT INTO chat_settings (chat_id, admin_id, timezone, notification_days)
                       VALUES (?, ?, ?, ?)''',
                    (chat_id, user_id, BotConfig.DEFAULT_TIMEZONE, BotConfig.DEFAULT_NOTIFICATION_DAYS)
                )
                conn.commit()
                await update.message.reply_text(
                    "🎉 Привет! Я бот для учета периодических событий. "
                    "Вы назначены администратором этого чата."
                )
            else:
                await update.message.reply_text(
                    "👋 Привет! Я бот для учета периодических событий."
                )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "Произошла ошибка при инициализации. Попробуйте позже."
        )

    await show_menu(update, context)

async def enhanced_send_notifications(context):
    """Улучшенная система отправки уведомлений"""
    logger = logging.getLogger(__name__)
    
    try:
        # Инициализируем менеджеры
        (notification_manager, excel_exporter, search_manager, template_manager, 
         dashboard_manager, advanced_analytics_manager, automated_reports_manager) = init_managers()
        
        notifications = db_manager.execute_with_retry('''
            SELECT 
                ee.id, e.chat_id, e.user_id, e.full_name, e.position,
                ee.event_type, ee.next_notification_date, ee.interval_days,
                cs.admin_id, cs.timezone, cs.notification_days,
                e.id as employee_id
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            JOIN chat_settings cs ON e.chat_id = cs.chat_id
            WHERE e.is_active = 1 
            AND date(ee.next_notification_date) BETWEEN date('now', '-7 days')
            AND date('now', '+' || cs.notification_days || ' days')
            ORDER BY ee.next_notification_date
        ''', fetch="all")

        if not notifications:
            logger.info("No notifications to send")
            return

        notifications_sent = 0
        escalations_sent = 0

        for notification in notifications:
            try:
                # Определяем дни до события
                from datetime import datetime
                event_date = datetime.fromisoformat(notification['next_notification_date']).date()
                days_until = (event_date - datetime.now().date()).days

                # Определяем уровень уведомления
                level = notification_manager.get_notification_level(days_until)
                
                # Проверяем, нужно ли отправлять уведомление сегодня
                if not notification_manager.should_send_notification(level, days_until):
                    continue

                # Формируем сообщение
                message = notification_manager.format_notification_message(notification, level)
                keyboard = notification_manager.create_action_keyboard(notification)

                # Отправляем сотруднику
                if notification['user_id']:
                    try:
                        await context.bot.send_message(
                            chat_id=notification['user_id'],
                            text=message,
                            parse_mode='HTML',
                            reply_markup=keyboard
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send to user {notification['user_id']}: {e}")

                # Отправляем администратору
                try:
                    admin_message = f"[👨‍💼 ADMIN] {message}"
                    await context.bot.send_message(
                        chat_id=notification['admin_id'],
                        text=admin_message,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                    notifications_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send to admin {notification['admin_id']}: {e}")

                # Эскалация для критичных случаев
                from config.constants import NotificationLevel
                if level in [NotificationLevel.CRITICAL, NotificationLevel.OVERDUE]:
                    await notification_manager.send_escalated_notifications(context, notification, level)
                    escalations_sent += 1

            except Exception as e:
                logger.error(f"Error processing notification {notification['id']}: {e}")

        logger.info(f"Enhanced notifications: {notifications_sent} sent, {escalations_sent} escalated")

    except Exception as e:
        logger.error(f"Critical error in enhanced_send_notifications: {e}")

def main():
    """Главная функция запуска бота"""
    # Защита от дублирующих запусков
    lock_fd = singleton_lock()
    
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Telegram bot with modular architecture")
        
        # Инициализация менеджеров
        logger.info("Initializing managers...")
        (notification_manager, excel_exporter, search_manager, template_manager, 
         dashboard_manager, advanced_analytics_manager, automated_reports_manager) = init_managers()
        
        # Создание приложения с увеличенными таймаутами
        if not BotConfig.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set in environment variables")
        
        # Настройки для более устойчивого соединения
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(
            connection_pool_size=1,
            connect_timeout=30.0,
            pool_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0
        )
        
        application = Application.builder().token(BotConfig.BOT_TOKEN).request(request).build()
        
        # Регистрация основных команд
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('menu', lambda u, c: show_menu(u, c)))
        application.add_handler(CommandHandler('help', lambda u, c: help_command(u, c)))
        
        # Обработчик разговора для добавления сотрудника
        add_employee_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    add_employee_start,
                    pattern=r'.*"action"\s*:\s*"add_employee".*'
                )
            ],
            states={
                ConversationStates.ADD_NAME: [
                    MessageHandler(filters.CONTACT, handle_contact),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, add_employee_name)
                ],
                ConversationStates.ADD_POSITION: [
                    CallbackQueryHandler(handle_position_selection, pattern=r'.*"action"\s*:\s*"select_position".*'),
                    CallbackQueryHandler(cancel_add_employee, pattern=r'.*"action"\s*:\s*"cancel_add_employee".*')
                ],
                ConversationStates.ADD_EVENT_TYPE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_type)
                ],
                ConversationStates.ADD_LAST_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, add_last_date)
                ],
                ConversationStates.ADD_INTERVAL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, add_interval)
                ],
            },
            fallbacks=[
                CommandHandler('cancel', lambda u, c: cancel_add_employee(u, c))
            ],
            per_message=False,
            per_chat=True,
            per_user=True
        )
        application.add_handler(add_employee_conv)
        
        # Обработчик разговора для редактирования имени сотрудника
        edit_name_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    edit_employee_name,
                    pattern=r'.*"action"\s*:\s*"edit_name".*'
                )
            ],
            states={
                ConversationStates.EDIT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), save_employee_name),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), lambda u, c: cancel_add_employee(u, c))
                ]
            },
            fallbacks=[
                MessageHandler(filters.Regex(r'^❌ Отмена$'), lambda u, c: cancel_add_employee(u, c)),
                CommandHandler('cancel', lambda u, c: cancel_add_employee(u, c))
            ],
            per_message=False,
            per_chat=True,
            per_user=True
        )
        application.add_handler(edit_name_conv)
        
        # Обработчик разговора для добавления событий к существующим сотрудникам
        add_event_to_employee_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    add_event_to_employee,
                    pattern=r'.*"action"\s*:\s*"add_event".*'
                )
            ],
            states={
                ConversationStates.ADD_EVENT_TO_EMPLOYEE_TYPE: [
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), add_event_to_employee_type),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_event_to_employee)
                ],
                ConversationStates.ADD_EVENT_TO_EMPLOYEE_DATE: [
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), add_event_to_employee_date),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_event_to_employee)
                ],
                ConversationStates.ADD_EVENT_TO_EMPLOYEE_INTERVAL: [
                    MessageHandler(filters.TEXT & ~filters.Regex(r'^❌ Отмена$'), add_event_to_employee_interval),
                    MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_event_to_employee)
                ],
            },
            fallbacks=[
                MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_add_event_to_employee),
                CommandHandler('cancel', lambda u, c: cancel_add_event_to_employee(u, c))
            ],
            per_message=False,
            per_chat=True,
            per_user=True
        )
        application.add_handler(add_event_to_employee_conv)
        
        # Основной обработчик callback-запросов (MOVED TO AFTER ConversationHandler registrations)
        application.add_handler(CallbackQueryHandler(menu_handler))
        
        # Обработчик ошибок
        application.add_error_handler(global_error_handler)
        
        # Планировщик задач
        job_queue = application.job_queue
        if job_queue:
            # Ежедневные уведомления в 9:00 по часовому поясу
            job_queue.run_daily(
                enhanced_send_notifications,
                time=dt_time(hour=BotConfig.NOTIFICATION_TIME_HOUR, minute=0)
            )
            
            # Периодическая проверка уведомлений каждые 12 часов
            job_queue.run_repeating(
                enhanced_send_notifications,
                interval=timedelta(hours=12),
                first=timedelta(minutes=1)
            )
            
            # Автоматические отчеты
            # Ежедневный сводный отчет в 9:00
            job_queue.run_daily(
                automated_reports_manager.send_daily_summary_report,
                time=dt_time(hour=9, minute=0)
            )
            
            # Еженедельный аналитический отчет (понедельник в 8:00)
            job_queue.run_daily(
                automated_reports_manager.send_weekly_analytics_report,
                time=dt_time(hour=8, minute=0),
                days=(0,)  # Понедельник (0 = понедельник в новой версии)
            )
            
            # Месячный отчет (1-е число каждого месяца в 9:00)
            from datetime import date
            job_queue.run_monthly(
                automated_reports_manager.send_monthly_report,
                when=dt_time(hour=9, minute=0),
                day=1
            )
            
            logger.info("Job queue configured for notifications and automated reports")
        
        logger.info("Bot handlers configured successfully")
        
        # Запуск бота
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=["message", "callback_query"])
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        traceback.print_exc()
    finally:
        try:
            lock_fd.close()
            if os.path.exists('bot.lock'):
                os.remove('bot.lock')
        except:
            pass

if __name__ == "__main__":
    main()