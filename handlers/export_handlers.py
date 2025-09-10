"""
Обработчики экспорта данных
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.security import is_admin
from core.utils import create_callback_data, parse_callback_data
from managers.export_manager import ExportManager
from core.database import db_manager

# Initialize export manager
excel_exporter = ExportManager(db_manager)

logger = logging.getLogger(__name__)

async def export_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню выбора формата экспорта"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        await query.edit_message_text("❌ Только администратор может экспортировать данные")
        return
    
    keyboard = [
        [InlineKeyboardButton("📈 Excel (.xlsx)", callback_data=create_callback_data("export", format="xlsx"))],
        [InlineKeyboardButton("📄 CSV (.csv)", callback_data=create_callback_data("export", format="csv"))],
        [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
    ]
    
    text = (
        "📁 <b>Экспорт данных</b>\n\n"
        "Выберите формат файла для экспорта:\n\n"
        "📈 <b>Excel</b> - с форматированием, цветовым кодированием и статистикой\n"
        "📄 <b>CSV</b> - для импорта в другие системы\n\n"
        "Файл будет содержать все события сотрудников с актуальными статусами."
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка экспорта данных"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    file_format = data.get('format', 'xlsx')
    chat_id = update.effective_chat.id
    
    await query.edit_message_text("⏳ Подготавливаю файл для экспорта...")
    
    try:
        # Экспортируем данные
        file_buffer = await excel_exporter.export_all_events(chat_id, file_format)
        
        # Формируем имя файла
        current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"events_report_{current_date}.{file_format}"
        
        # Отправляем файл
        await context.bot.send_document(
            chat_id=chat_id,
            document=file_buffer,
            filename=filename,
            caption=f"📊 Отчет по событиям от {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await query.edit_message_text("✅ Файл успешно сформирован и отправлен!")
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        await query.edit_message_text("❌ Ошибка при экспорте данных")

# Alias for backward compatibility
export_data_start = export_menu_start