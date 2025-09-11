"""
Обработчики настроек системы
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from core.security import is_admin
from core.utils import create_callback_data, parse_callback_data
from core.database import db_manager
from config.constants import ConversationStates

logger = logging.getLogger(__name__)

async def set_notification_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Настройка дней уведомлений"""
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
    
    # Получаем текущие настройки
    current_settings = db_manager.execute_with_retry('''
        SELECT notification_days FROM chat_settings WHERE chat_id = ?
    ''', (chat_id,), fetch="one")
    
    current_days = current_settings['notification_days'] if current_settings else 90
    
    keyboard = [
        [InlineKeyboardButton("30 дней", callback_data=create_callback_data("save_notif_days", days=30))],
        [InlineKeyboardButton("60 дней", callback_data=create_callback_data("save_notif_days", days=60))],
        [InlineKeyboardButton("90 дней", callback_data=create_callback_data("save_notif_days", days=90))],
        [InlineKeyboardButton("120 дней", callback_data=create_callback_data("save_notif_days", days=120))],
        [InlineKeyboardButton("🔙 Настройки", callback_data=create_callback_data("settings"))]
    ]
    
    text = (
        f"⏰ <b>Настройка дней уведомлений</b>\n\n"
        f"Текущее значение: <b>{current_days} дней</b>\n\n"
        f"За сколько дней до события отправлять первое уведомление?\n\n"
        f"Выберите период:"
    )
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def save_notification_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохранение настройки дней уведомлений"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    days = data.get('days')
    chat_id = update.effective_chat.id
    
    if not days:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: неверное значение дней"
        )
        return
    
    try:
        db_manager.execute_with_retry('''
            UPDATE chat_settings 
            SET notification_days = ? 
            WHERE chat_id = ?
        ''', (days, chat_id))
        
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ <b>Настройки сохранены!</b>\n\n"
                 f"⏰ Дни уведомлений: <b>{days} дней</b>\n\n"
                 f"Теперь первые уведомления будут отправляться за {days} дней до события.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error saving notification days: {e}")
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка при сохранении настроек"
        )

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Настройка часового пояса"""
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
    
    # Получаем текущие настройки
    current_settings = db_manager.execute_with_retry('''
        SELECT timezone FROM chat_settings WHERE chat_id = ?
    ''', (chat_id,), fetch="one")
    
    current_tz = current_settings['timezone'] if current_settings else 'Europe/Moscow'
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Москва (Europe/Moscow)", callback_data=create_callback_data("save_timezone", tz="Europe/Moscow"))],
        [InlineKeyboardButton("🇷🇺 Екатеринбург (Asia/Yekaterinburg)", callback_data=create_callback_data("save_timezone", tz="Asia/Yekaterinburg"))],
        [InlineKeyboardButton("🇷🇺 Новосибирск (Asia/Novosibirsk)", callback_data=create_callback_data("save_timezone", tz="Asia/Novosibirsk"))],
        [InlineKeyboardButton("🇷🇺 Владивосток (Asia/Vladivostok)", callback_data=create_callback_data("save_timezone", tz="Asia/Vladivostok"))],
        [InlineKeyboardButton("🌍 UTC", callback_data=create_callback_data("save_timezone", tz="UTC"))],
        [InlineKeyboardButton("🔙 Настройки", callback_data=create_callback_data("settings"))]
    ]
    
    text = (
        f"🕒 <b>Настройка часового пояса</b>\n\n"
        f"Текущий пояс: <b>{current_tz}</b>\n\n"
        f"Выберите часовой пояс для корректного времени уведомлений:"
    )
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def save_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохранение настройки часового пояса"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    timezone = data.get('tz')
    chat_id = update.effective_chat.id
    
    if not timezone:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: неверный часовой пояс"
        )
        return
    
    try:
        db_manager.execute_with_retry('''
            UPDATE chat_settings 
            SET timezone = ? 
            WHERE chat_id = ?
        ''', (timezone, chat_id))
        
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ <b>Настройки сохранены!</b>\n\n"
                 f"🕒 Часовой пояс: <b>{timezone}</b>\n\n"
                 f"Уведомления будут отправляться по местному времени.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error saving timezone: {e}")
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка при сохранении настроек"
        )