"""
Обработчики для управления событиями сотрудников
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.database import db_manager
from core.security import decrypt_data, is_admin
from core.utils import create_callback_data

logger = logging.getLogger(__name__)

async def my_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает предстоящие события текущего пользователя"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Поиск сотрудника по user_id
            cursor.execute(
                '''SELECT e.id, e.full_name, e.position 
                   FROM employees e 
                   WHERE e.chat_id = ? AND e.user_id = ? AND e.is_active = 1''',
                (chat_id, user_id)
            )
            employee = cursor.fetchone()

            if not employee:
                response = "ℹ️ У вас нет записей в базе сотрудников."
                keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if update.message:
                    await update.message.reply_text(response, reply_markup=reply_markup)
                else:
                    query = update.callback_query
                    # Отправляем новое сообщение вместо редактирования
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=response,
                        reply_markup=reply_markup
                    )
                return

            # Получаем события сотрудника
            cursor.execute(
                '''SELECT event_type, next_notification_date, interval_days 
                   FROM employee_events 
                   WHERE employee_id = ? 
                   ORDER BY next_notification_date''',
                (employee['id'],)
            )
            events = cursor.fetchall()

        # Расшифровка имени
        try:
            decrypted_name = decrypt_data(employee['full_name'])
        except ValueError:
            decrypted_name = "Ошибка дешифрации"

        # Формирование ответа
        response = [
            f"📅 <b>Ваши предстоящие события</b>\n",
            f"👤 <b>Сотрудник:</b> {decrypted_name}",
            f"💼 <b>Должность:</b> {employee['position']}",
            "",
            "📅 <b>События:</b>"
        ]

        if not events:
            response.append("ℹ️ Нет предстоящих событий")
        else:
            for event in events:
                event_date = datetime.fromisoformat(event['next_notification_date']).date()
                days_left = (event_date - datetime.now().date()).days
                
                # Определяем статус события
                if days_left < 0:
                    status = f"🔴 просрочено на {abs(days_left)} дн."
                elif days_left <= 3:
                    status = f"🔴 через {days_left} дн. (критично!)"
                elif days_left <= 7:
                    status = f"🟠 через {days_left} дн. (срочно)"
                elif days_left <= 30:
                    status = f"🟡 через {days_left} дн."
                else:
                    status = f"🟢 через {days_left} дн."
                
                response.append(
                    f"• <b>{event['event_type']}</b>\n"
                    f"  📅 {event_date.strftime('%d.%m.%Y')} ({status})"
                )

        # Кнопка возврата в меню
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправка сообщения
        message = "\n".join(response)
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            query = update.callback_query
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in my_events: {e}")
        error_msg = "❌ Произошла ошибка при получении ваших событий"
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(error_msg, reply_markup=reply_markup)
        else:
            query = update.callback_query
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_msg,
                reply_markup=reply_markup
            )

async def all_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает все предстоящие события (для администраторов)"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        query = update.callback_query
        await query.answer()
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Только администратор может просматривать все события"
        )
        return

    try:
        # Получаем все события чата
        events = db_manager.execute_with_retry('''
            SELECT 
                e.full_name,
                e.position,
                ee.event_type,
                ee.next_notification_date,
                (julianday(ee.next_notification_date) - julianday('now')) as days_until
            FROM employee_events ee
            JOIN employees e ON ee.employee_id = e.id
            WHERE e.chat_id = ? AND e.is_active = 1
            ORDER BY ee.next_notification_date
            LIMIT 20
        ''', (chat_id,), fetch="all")

        if not events:
            response = "ℹ️ В системе нет событий"
        else:
            response_lines = ["📊 <b>Все предстоящие события</b>\n"]
            
            for event in events:
                try:
                    decrypted_name = decrypt_data(event['full_name'])
                except ValueError:
                    decrypted_name = "Ошибка дешифрации"
                
                event_date = datetime.fromisoformat(event['next_notification_date']).date()
                days_until = int(event['days_until']) if event['days_until'] else 0
                
                # Определяем статус
                if days_until < 0:
                    status_emoji = "🔴"
                    status_text = f"просрочено на {abs(days_until)} дн."
                elif days_until <= 3:
                    status_emoji = "🔴"
                    status_text = f"через {days_until} дн. (критично!)"
                elif days_until <= 7:
                    status_emoji = "🟠"
                    status_text = f"через {days_until} дн. (срочно)"
                elif days_until <= 30:
                    status_emoji = "🟡"
                    status_text = f"через {days_until} дн."
                else:
                    status_emoji = "🟢"
                    status_text = f"через {days_until} дн."
                
                response_lines.append(
                    f"{status_emoji} <b>{decrypted_name}</b> ({event['position']})\n"
                    f"   📋 {event['event_type']}\n"
                    f"   📅 {event_date.strftime('%d.%m.%Y')} ({status_text})\n"
                )
            
            if len(events) >= 20:
                response_lines.append("📝 <i>Показаны первые 20 событий. Используйте поиск для просмотра остальных.</i>")
            
            response = "\n".join(response_lines)

        # Кнопки управления
        keyboard = [
            [
                InlineKeyboardButton("🔍 Поиск событий", callback_data=create_callback_data("search_menu")),
                InlineKeyboardButton("📁 Экспорт", callback_data=create_callback_data("export_menu"))
            ],
            [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='HTML')
        else:
            query = update.callback_query
            await query.answer()
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in all_events: {e}")
        error_msg = "❌ Произошла ошибка при получении списка событий"
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(error_msg, reply_markup=reply_markup)
        else:
            query = update.callback_query
            await query.answer()
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_msg,
                reply_markup=reply_markup
            )

async def view_employee_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали сотрудника и его события"""
    query = update.callback_query
    await query.answer()
    employee_id = context.user_data.get('selected_employee')

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Получение информации о сотруднике
            cursor.execute(
                "SELECT full_name, position FROM employees WHERE id = ?",
                (employee_id,)
            )
            employee = cursor.fetchone()

            if not employee:
                # Отправляем новое сообщение вместо редактирования
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Сотрудник не найден"
                )
                return

            # Получение событий сотрудника
            cursor.execute(
                '''SELECT event_type, next_notification_date, interval_days
                   FROM employee_events 
                   WHERE employee_id = ? 
                   ORDER BY next_notification_date''',
                (employee_id,)
            )
            events = cursor.fetchall()

        # Расшифровка имени
        try:
            decrypted_name = decrypt_data(employee['full_name'])
        except ValueError:
            decrypted_name = "Ошибка дешифрации"

        # Формирование ответа
        response = [
            f"👤 <b>Информация о сотруднике</b>\n",
            f"📝 <b>ФИО:</b> {decrypted_name}",
            f"💼 <b>Должность:</b> {employee['position']}",
            "",
            "📅 <b>События:</b>"
        ]

        if not events:
            response.append("ℹ️ Нет событий")
        else:
            for event in events:
                event_date = datetime.fromisoformat(event['next_notification_date']).date()
                days_left = (event_date - datetime.now().date()).days
                
                if days_left < 0:
                    status = f"🔴 просрочено на {abs(days_left)} дн."
                elif days_left <= 7:
                    status = f"🟠 через {days_left} дн."
                else:
                    status = f"🟢 через {days_left} дн."
                
                response.append(
                    f"• <b>{event['event_type']}</b>\n"
                    f"  📅 {event_date.strftime('%d.%m.%Y')} ({status})\n"
                    f"  🔄 Интервал: {event['interval_days']} дней"
                )

        # Кнопки действий
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать",
                                  callback_data=create_callback_data("edit_employee", id=employee_id))],
            [InlineKeyboardButton("🔙 К списку", callback_data=create_callback_data("list_employees"))]
        ]

        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="\n".join(response),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in view_employee_details: {e}")
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Произошла ошибка при получении данных сотрудника"
        )

# Alias for backward compatibility
view_all_events = all_events