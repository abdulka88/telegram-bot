"""
Обработчики шаблонов событий
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.security import is_admin, decrypt_data
from core.utils import create_callback_data, parse_callback_data
from core.database import db_manager
from managers.template_manager import TemplateManager

# Инициализируем template_manager
template_manager = TemplateManager(db_manager)

logger = logging.getLogger(__name__)

async def templates_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню шаблонов событий"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может использовать шаблоны")
        return
    
    # Получаем список доступных шаблонов
    templates = template_manager.get_template_list()
    
    keyboard = []
    for template in templates:
        keyboard.append([InlineKeyboardButton(
            f"📋 {template['name']} ({template['events_count']} событий)",
            callback_data=create_callback_data("select_template", key=template['key'])
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))])
    
    text = (
        "📋 <b>Шаблоны событий</b>\n\n"
        "Выберите шаблон для применения к сотруднику.\n"
        "Шаблон автоматически добавит все необходимые события согласно должности:\n\n"
    )
    
    for template in templates[:5]:  # Показываем описание первых 5 шаблонов
        text += f"• <b>{template['name']}</b>\n"
    
    if len(templates) > 5:
        text += f"• ... и еще {len(templates) - 5} шаблонов\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_employee_for_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выбор сотрудника для применения шаблона"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    template_key = data.get('key')
    
    if not template_key:
        await query.edit_message_text("❌ Ошибка: шаблон не найден")
        return
    
    # Получаем информацию о шаблоне
    template_info = template_manager.get_template_info(template_key)
    if not template_info:
        await query.edit_message_text("❌ Ошибка: шаблон не найден")
        return
    
    context.user_data['selected_template'] = template_key
    chat_id = update.effective_chat.id
    
    try:
        # Получаем список сотрудников
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, full_name, position 
                   FROM employees 
                   WHERE chat_id = ? AND is_active = 1 
                   ORDER BY full_name''',
                (chat_id,)
            )
            employees = cursor.fetchall()
        
        if not employees:
            await query.edit_message_text("❌ Нет активных сотрудников")
            return
        
        text = (
            f"📋 <b>Шаблон: {template_info['name']}</b>\n\n"
            f"📊 Событий в шаблоне: {template_info['events_count']}\n\n"
            "👥 Выберите сотрудника для применения шаблона:"
        )
        
        keyboard = []
        for emp in employees:
            try:
                decrypted_name = decrypt_data(emp['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            
            keyboard.append([InlineKeyboardButton(
                f"{decrypted_name} ({emp['position']})",
                callback_data=create_callback_data("apply_template", emp_id=emp['id'])
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 К шаблонам", callback_data=create_callback_data("templates"))])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error selecting employee for template: {e}")
        await query.edit_message_text("❌ Ошибка при получении списка сотрудников")

async def apply_template_to_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Применение шаблона к сотруднику"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('emp_id')
    template_key = context.user_data.get('selected_template')
    
    if not employee_id or not template_key:
        await query.edit_message_text("❌ Ошибка: недостаточно данных")
        return
    
    await query.edit_message_text("⏳ Применяю шаблон...")
    
    try:
        # Применяем шаблон
        success = await template_manager.apply_template(employee_id, template_key)
        
        if success:
            template_info = template_manager.get_template_info(template_key)
            await query.edit_message_text(
                f"✅ <b>Шаблон успешно применен!</b>\n\n"
                f"📋 Шаблон: {template_info['name']}\n"
                f"📊 Добавлено событий: {template_info['events_count']}\n\n"
                f"Все события автоматически добавлены в календарь сотрудника.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ Ошибка при применении шаблона")
        
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        await query.edit_message_text("❌ Произошла ошибка при применении шаблона")