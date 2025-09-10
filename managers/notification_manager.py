"""
Менеджер уведомлений для Telegram бота управления периодическими событиями
"""

import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.constants import NotificationLevel
from core.security import decrypt_data
from core.utils import create_callback_data

logger = logging.getLogger(__name__)

class NotificationManager:
    """Менеджер многоуровневых уведомлений"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        
    def get_notification_level(self, days_until: int) -> NotificationLevel:
        """
        Определяет уровень срочности уведомления
        
        Args:
            days_until: Количество дней до события
            
        Returns:
            Уровень уведомления
        """
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
        """
        Определяет, нужно ли отправлять уведомление сегодня
        
        Args:
            level: Уровень уведомления
            days_until: Количество дней до события
            
        Returns:
            True если нужно отправить уведомление
        """
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
        """
        Форматирует сообщение в зависимости от уровня срочности
        
        Args:
            notification: Данные уведомления
            level: Уровень срочности
            
        Returns:
            Отформатированное сообщение
        """
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
            try:
                if notification['position']:
                    message += f"\n💼 Должность: {notification['position']}"
            except (KeyError, IndexError):
                pass  # Поле position может отсутствовать
        
        return message

    async def send_escalated_notifications(self, context, notification: dict, level: NotificationLevel):
        """
        Отправляет эскалированные уведомления для критичных случаев
        
        Args:
            context: Контекст бота
            notification: Данные уведомления
            level: Уровень срочности
        """
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
        """
        Создает клавиатуру с быстрыми действиями
        
        Args:
            notification: Данные уведомления
            
        Returns:
            InlineKeyboardMarkup с кнопками действий
        """
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
                    callback_data=create_callback_data("contact_employee", emp_id=notification['employee_id'] if 'employee_id' in notification else None)
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)