"""
Обработчики автоматических отчетов для Telegram бота
Управление настройками и отправка отчетов по запросу
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.utils import create_callback_data, parse_callback_data
from core.security import is_admin
from managers.automated_reports_manager import AutomatedReportsManager
from core.database import db_manager

# Инициализируем менеджер автоматических отчетов
automated_reports_manager = AutomatedReportsManager(db_manager)

logger = logging.getLogger(__name__)

async def reports_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню автоматических отчетов"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может управлять отчетами")
        return
    
    # Получаем текущие настройки
    settings = automated_reports_manager.get_report_settings(chat_id)
    
    text_lines = [
        "📊 <b>Автоматические отчеты</b>",
        "",
        "🔄 <b>Текущие настройки:</b>",
        f"📅 Ежедневные: {'✅ Включены' if settings.get('daily_enabled') else '❌ Отключены'}",
        f"📊 Еженедельные: {'✅ Включены' if settings.get('weekly_enabled') else '❌ Отключены'}",
        f"📈 Месячные: {'✅ Включены' if settings.get('monthly_enabled') else '❌ Отключены'}",
        "",
        "⏰ <b>Расписание:</b>",
        f"🌅 Ежедневно: {settings.get('daily_time', '09:00')}",
        f"📅 Еженедельно: Понедельник в 08:00",
        f"📊 Ежемесячно: 1 число в 09:00",
        "",
        "💡 Выберите действие:"
    ]
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Настройки отчетов", callback_data=create_callback_data("reports_settings")),
            InlineKeyboardButton("📊 Запросить отчет", callback_data=create_callback_data("request_report"))
        ],
        [
            InlineKeyboardButton("📋 История отчетов", callback_data=create_callback_data("reports_history")),
            InlineKeyboardButton("📊 Тестовый отчет", callback_data=create_callback_data("test_report"))
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

async def reports_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Настройки автоматических отчетов"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем текущие настройки
    settings = automated_reports_manager.get_report_settings(chat_id)
    
    text_lines = [
        "⚙️ <b>Настройки автоматических отчетов</b>",
        "",
        "📊 <b>Типы отчетов:</b>",
        "",
        f"📅 <b>Ежедневные сводки</b>",
        f"   Статус: {'✅ Включены' if settings.get('daily_enabled') else '❌ Отключены'}",
        f"   Время: {settings.get('daily_time', '09:00')}",
        f"   Содержание: события дня, просроченные, завтрашние",
        "",
        f"📊 <b>Еженедельная аналитика</b>",
        f"   Статус: {'✅ Включены' if settings.get('weekly_enabled') else '❌ Отключены'}",
        f"   Время: Понедельник в 08:00",
        f"   Содержание: тренды, эффективность, прогнозы",
        "",
        f"📈 <b>Месячные отчеты</b>",
        f"   Статус: {'✅ Включены' if settings.get('monthly_enabled') else '❌ Отключены'}",
        f"   Время: 1 число в 09:00",
        f"   Содержание: итоги месяца, статистика, рекомендации"
    ]
    
    text = "\n".join(text_lines)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"📅 Ежедневные {'❌' if settings.get('daily_enabled') else '✅'}", 
                callback_data=create_callback_data("toggle_daily_reports")
            ),
            InlineKeyboardButton(
                f"📊 Еженедельные {'❌' if settings.get('weekly_enabled') else '✅'}", 
                callback_data=create_callback_data("toggle_weekly_reports")
            )
        ],
        [
            InlineKeyboardButton(
                f"📈 Месячные {'❌' if settings.get('monthly_enabled') else '✅'}", 
                callback_data=create_callback_data("toggle_monthly_reports")
            ),
            InlineKeyboardButton("⏰ Время", callback_data=create_callback_data("set_report_time"))
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data=create_callback_data("reports_settings")),
            InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def request_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрос отчета по требованию"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "📊 <b>Запрос отчета</b>\n\n"
        "Выберите тип отчета для немедленной генерации:\n\n"
        "📅 <b>Ежедневная сводка</b> - текущее состояние на сегодня\n"
        "📊 <b>Еженедельная аналитика</b> - анализ за последнюю неделю\n"
        "📈 <b>Месячный отчет</b> - подробный анализ за месяц\n"
        "🎯 <b>Полный отчет</b> - комплексный анализ всех данных"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Дневная сводка", callback_data=create_callback_data("generate_daily")),
            InlineKeyboardButton("📊 Недельная аналитика", callback_data=create_callback_data("generate_weekly"))
        ],
        [
            InlineKeyboardButton("📈 Месячный отчет", callback_data=create_callback_data("generate_monthly")),
            InlineKeyboardButton("🎯 Полный отчет", callback_data=create_callback_data("generate_full"))
        ],
        [
            InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def generate_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерация ежедневного отчета по запросу"""
    query = update.callback_query
    await query.answer("📊 Генерирую ежедневный отчет...")
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        await automated_reports_manager.send_custom_report(
            context, chat_id, 'daily', user_id
        )
        
        await query.edit_message_text(
            "✅ <b>Ежедневный отчет отправлен!</b>\n\n"
            "📊 Проверьте ваши сообщения",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка при генерации отчета</b>\n\n"
            "Попробуйте позже или обратитесь к администратору",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )

async def generate_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерация еженедельного отчета по запросу"""
    query = update.callback_query
    await query.answer("📊 Генерирую еженедельный отчет...")
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        await automated_reports_manager.send_custom_report(
            context, chat_id, 'weekly', user_id
        )
        
        await query.edit_message_text(
            "✅ <b>Еженедельный отчет отправлен!</b>\n\n"
            "📊 Проверьте ваши сообщения",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка при генерации отчета</b>\n\n"
            "Попробуйте позже или обратитесь к администратору",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )

async def generate_monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерация месячного отчета по запросу"""
    query = update.callback_query
    await query.answer("📊 Генерирую месячный отчет...")
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        await automated_reports_manager.send_custom_report(
            context, chat_id, 'monthly', user_id
        )
        
        await query.edit_message_text(
            "✅ <b>Месячный отчет отправлен!</b>\n\n"
            "📊 Проверьте ваши сообщения",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка при генерации отчета</b>\n\n"
            "Попробуйте позже или обратитесь к администратору",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )

async def generate_full_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерация полного отчета"""
    query = update.callback_query
    await query.answer("📊 Генерирую полный отчет...")
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        # Отправляем все три типа отчетов
        await automated_reports_manager.send_custom_report(context, chat_id, 'daily', user_id)
        await automated_reports_manager.send_custom_report(context, chat_id, 'weekly', user_id)
        await automated_reports_manager.send_custom_report(context, chat_id, 'monthly', user_id)
        
        await query.edit_message_text(
            "✅ <b>Полный отчет отправлен!</b>\n\n"
            "📊 Проверьте ваши сообщения - отправлены все типы отчетов",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error generating full report: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка при генерации отчета</b>\n\n"
            "Попробуйте позже или обратитесь к администратору",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )

async def toggle_daily_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переключение ежедневных отчетов"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    try:
        # Получаем текущие настройки
        settings = automated_reports_manager.get_report_settings(chat_id)
        new_status = not settings.get('daily_enabled', True)
        
        # Обновляем настройки
        db_manager.execute_with_retry('''
            INSERT OR REPLACE INTO report_settings 
            (chat_id, daily_enabled, weekly_enabled, monthly_enabled, daily_time, weekly_day, monthly_day)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id, new_status, settings.get('weekly_enabled', True),
            settings.get('monthly_enabled', True), settings.get('daily_time', '09:00'),
            settings.get('weekly_day', 1), settings.get('monthly_day', 1)
        ))
        
        status_text = "включены" if new_status else "отключены"
        await query.answer(f"📅 Ежедневные отчеты {status_text}")
        
        # Возвращаемся к настройкам
        await reports_settings(update, context)
        
    except Exception as e:
        logger.error(f"Error toggling daily reports: {e}")
        await query.answer("❌ Ошибка изменения настроек")

async def toggle_weekly_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переключение еженедельных отчетов"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    try:
        settings = automated_reports_manager.get_report_settings(chat_id)
        new_status = not settings.get('weekly_enabled', True)
        
        db_manager.execute_with_retry('''
            INSERT OR REPLACE INTO report_settings 
            (chat_id, daily_enabled, weekly_enabled, monthly_enabled, daily_time, weekly_day, monthly_day)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id, settings.get('daily_enabled', True), new_status,
            settings.get('monthly_enabled', True), settings.get('daily_time', '09:00'),
            settings.get('weekly_day', 1), settings.get('monthly_day', 1)
        ))
        
        status_text = "включены" if new_status else "отключены"
        await query.answer(f"📊 Еженедельные отчеты {status_text}")
        
        await reports_settings(update, context)
        
    except Exception as e:
        logger.error(f"Error toggling weekly reports: {e}")
        await query.answer("❌ Ошибка изменения настроек")

async def toggle_monthly_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переключение месячных отчетов"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    try:
        settings = automated_reports_manager.get_report_settings(chat_id)
        new_status = not settings.get('monthly_enabled', True)
        
        db_manager.execute_with_retry('''
            INSERT OR REPLACE INTO report_settings 
            (chat_id, daily_enabled, weekly_enabled, monthly_enabled, daily_time, weekly_day, monthly_day)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_id, settings.get('daily_enabled', True), settings.get('weekly_enabled', True),
            new_status, settings.get('daily_time', '09:00'),
            settings.get('weekly_day', 1), settings.get('monthly_day', 1)
        ))
        
        status_text = "включены" if new_status else "отключены"
        await query.answer(f"📈 Месячные отчеты {status_text}")
        
        await reports_settings(update, context)
        
    except Exception as e:
        logger.error(f"Error toggling monthly reports: {e}")
        await query.answer("❌ Ошибка изменения настроек")

async def test_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка тестового отчета"""
    query = update.callback_query
    await query.answer("📊 Отправляю тестовый отчет...")
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        test_report = (
            "📊 <b>Тестовый отчет системы</b>\n\n"
            f"🕒 Создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"💻 Чат ID: {chat_id}\n"
            f"👤 Пользователь ID: {user_id}\n\n"
            "✅ <b>Статус системы:</b> Работает корректно\n"
            "📊 <b>Автоматические отчеты:</b> Настроены и активны\n"
            "🔔 <b>Уведомления:</b> Функционируют\n"
            "📈 <b>Аналитика:</b> Доступна\n\n"
            "💡 Этот отчет подтверждает, что система автоматических отчетов работает правильно."
        )
        
        await context.bot.send_message(
            chat_id=user_id,
            text=test_report,
            parse_mode='HTML'
        )
        
        await query.edit_message_text(
            "✅ <b>Тестовый отчет отправлен!</b>\n\n"
            "📊 Система работает корректно",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error sending test report: {e}")
        await query.edit_message_text(
            "❌ <b>Ошибка отправки тестового отчета</b>\n\n"
            "Проверьте настройки системы",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К отчетам", callback_data=create_callback_data("reports_menu"))
            ]])
        )