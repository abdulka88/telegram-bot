"""
Обработчики расширенного поиска и фильтрации
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.utils import create_callback_data, parse_callback_data
from core.security import is_admin
from managers.search_manager import SearchManager
from core.database import db_manager
from core.security import decrypt_data

# Инициализируем менеджер поиска
search_manager = SearchManager(db_manager)

logger = logging.getLogger(__name__)

async def search_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню поиска с быстрыми фильтрами и статистикой"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not is_admin(chat_id, user_id):
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Только администратор может использовать поиск"
        )
        return
    
    # Получаем статистику
    stats = search_manager.get_events_statistics(chat_id)
    
    text = (
        "🔍 <b>Расширенный поиск событий</b>\n\n"
        "📊 <b>Статистика:</b>\n"
        f"👥 Сотрудников: {stats['total_employees']}\n"
        f"📅 Всего событий: {stats['total_events']}\n\n"
        f"🔴 Просрочено: {stats['overdue']}\n"
        f"🔴 Критично (1-3 дня): {stats['critical']}\n"
        f"🟠 Срочно (4-7 дней): {stats['urgent']}\n"
        f"🟡 Ближайшие (8-30 дней): {stats['upcoming']}\n"
        f"🟢 Плановые (30+ дней): {stats['planned']}\n\n"
        "Выберите способ поиска:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔤 Поиск по тексту", callback_data=create_callback_data("text_search_start"))],
        [
            InlineKeyboardButton(f"🔴 Просроченные ({stats['overdue']})", callback_data=create_callback_data("search_filter", status="overdue")),
            InlineKeyboardButton(f"🔴 Критичные ({stats['critical']})", callback_data=create_callback_data("search_filter", status="critical"))
        ],
        [
            InlineKeyboardButton(f"🟠 Срочные ({stats['urgent']})", callback_data=create_callback_data("search_filter", status="urgent")), 
            InlineKeyboardButton(f"🟡 Ближайшие ({stats['upcoming']})", callback_data=create_callback_data("search_filter", status="upcoming"))
        ],
        [
            InlineKeyboardButton("👥 Поиск сотрудников", callback_data=create_callback_data("search_employees")),
            InlineKeyboardButton("📋 По типу события", callback_data=create_callback_data("search_by_type"))
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data=create_callback_data("menu"))]
    ]
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def search_by_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поиск по быстрым фильтрам (статус)"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    status = data.get('status')
    page = data.get('page', 0)
    
    chat_id = update.effective_chat.id
    
    # Настройки поиска по статусу
    status_config = {
        'overdue': {'emoji': '🔴', 'title': 'Просроченные события', 'filters': {'status': 'overdue'}},
        'critical': {'emoji': '🔴', 'title': 'Критичные события (1-3 дня)', 'filters': {'status': 'critical'}},
        'urgent': {'emoji': '🟠', 'title': 'Срочные события (4-7 дней)', 'filters': {'status': 'urgent'}},
        'upcoming': {'emoji': '🟡', 'title': 'Ближайшие события (8-30 дней)', 'filters': {'status': 'upcoming'}}
    }
    
    if status not in status_config:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неизвестный статус"
        )
        return
    
    config = status_config[status]
    
    # Выполняем поиск
    results = await search_manager.search_events(
        chat_id=chat_id,
        query="",
        filters=config['filters'],
        page=page,
        per_page=5
    )
    
    await display_search_results(update, context, results, config['title'], status, page)

async def display_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: dict, title: str, search_type: str = None, page: int = 0) -> None:
    """Отображает результаты поиска с пагинацией"""
    query = update.callback_query
    
    events = results['results']
    pagination = results['pagination']
    
    if not events:
        text = f"{title}\n\n❌ События не найдены"
        keyboard = [[InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]]
    else:
        # Формируем текст с результатами
        text_lines = [f"📋 <b>{title}</b>", ""]
        
        for i, event in enumerate(events, 1):
            event_date = datetime.fromisoformat(event['next_notification_date']).strftime('%d.%m.%Y')
            text_lines.append(
                f"{i}. {event['status_emoji']} <b>{event['full_name']}</b>\n"
                f"   💼 {event['position']}\n"
                f"   📋 {event['event_type']}\n"
                f"   📅 {event_date} ({event['status_text']})\n"
            )
        
        # Добавляем информацию о пагинации
        text_lines.append(
            f"\n📄 Страница {pagination['current_page'] + 1} из {pagination['total_pages']}\n"
            f"📊 Показано {len(events)} из {pagination['total_count']} событий"
        )
        
        text = "\n".join(text_lines)
        
        # Кнопки пагинации и действий
        keyboard = []
        
        # Кнопки пагинации
        pagination_buttons = []
        if pagination['has_prev']:
            pagination_buttons.append(
                InlineKeyboardButton("⬅️ Пред", 
                    callback_data=create_callback_data("search_filter", status=search_type, page=page-1))
            )
        if pagination['has_next']:
            pagination_buttons.append(
                InlineKeyboardButton("След ➡️", 
                    callback_data=create_callback_data("search_filter", status=search_type, page=page+1))
            )
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Дополнительные действия
        keyboard.extend([
            [InlineKeyboardButton("📁 Экспорт результатов", callback_data=create_callback_data("export_search", status=search_type))],
            [InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]
        ])
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def search_employees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поиск по сотрудникам"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    page = parse_callback_data(query.data).get('page', 0)
    
    # Получаем всех сотрудников
    employees = search_manager.search_employees(chat_id)
    
    if not employees:
        text = "👥 <b>Поиск сотрудников</b>\n\n❌ Сотрудники не найдены"
        keyboard = [[InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]]
    else:
        # Пагинация сотрудников
        per_page = 8
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_employees = employees[start_idx:end_idx]
        
        text = (
            f"👥 <b>Сотрудники</b>\n\n"
            f"Выберите сотрудника для просмотра событий:\n\n"
            f"📄 Страница {page + 1} из {(len(employees) + per_page - 1) // per_page}\n"
            f"👨‍💼 Показано {len(page_employees)} из {len(employees)} сотрудников"
        )
        
        # Кнопки с сотрудниками (по 2 в ряд)
        keyboard = []
        for i in range(0, len(page_employees), 2):
            row = []
            for j in range(2):
                if i + j < len(page_employees):
                    employee = page_employees[i + j]
                    # Обрезаем имя если слишком длинное
                    name = employee['full_name']
                    if len(name) > 20:
                        name = name[:17] + "..."
                    row.append(InlineKeyboardButton(
                        f"👤 {name}",
                        callback_data=create_callback_data("employee_events", id=employee['id'])
                    ))
            keyboard.append(row)
        
        # Кнопки пагинации
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(
                InlineKeyboardButton("⬅️ Пред", 
                    callback_data=create_callback_data("search_employees", page=page-1))
            )
        total_pages = (len(employees) + per_page - 1) // per_page
        if page < total_pages - 1:
            pagination_buttons.append(
                InlineKeyboardButton("След ➡️", 
                    callback_data=create_callback_data("search_employees", page=page+1))
            )
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))])
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_employee_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает события конкретного сотрудника"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    
    if not employee_id:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: ID сотрудника не найден"
        )
        return
    
    # Получаем информацию о сотруднике и его событиях
    employee = db_manager.execute_with_retry('''
        SELECT full_name, position FROM employees WHERE id = ?
    ''', (employee_id,), fetch="one")
    
    if not employee:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Сотрудник не найден"
        )
        return
    
    try:
        decrypted_name = decrypt_data(employee['full_name'])
    except ValueError:
        decrypted_name = "Ошибка дешифрации"
    
    # Получаем события сотрудника
    events = db_manager.execute_with_retry('''
        SELECT event_type, next_notification_date, interval_days
        FROM employee_events 
        WHERE employee_id = ? 
        ORDER BY next_notification_date
    ''', (employee_id,), fetch="all")
    
    # Формируем текст ответа
    text_lines = [
        f"👤 <b>События сотрудника</b>\n",
        f"📝 ФИО: <b>{decrypted_name}</b>",
        f"💼 Должность: <b>{employee['position']}</b>",
        "",
        "📅 <b>События:</b>"
    ]
    
    if not events:
        text_lines.append("ℹ️ Нет событий")
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
            
            text_lines.append(
                f"• <b>{event['event_type']}</b>\n"
                f"  📅 {event_date.strftime('%d.%m.%Y')} ({status})\n"
                f"  🔄 Интервал: {event['interval_days']} дней"
            )
    
    text = "\n".join(text_lines)
    
    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data=create_callback_data("edit_employee", id=employee_id))],
        [InlineKeyboardButton("➕ Добавить событие", callback_data=create_callback_data("add_event", id=employee_id))],
        [InlineKeyboardButton("🔙 К сотрудникам", callback_data=create_callback_data("search_employees"))]
    ]
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def search_by_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поиск по типу события"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем все типы событий
    event_types = search_manager.get_all_event_types(chat_id)
    
    if not event_types:
        text = "📋 <b>Поиск по типу события</b>\n\n❌ Типы событий не найдены"
        keyboard = [[InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]]
    else:
        text = "📋 <b>Поиск по типу события</b>\n\nВыберите тип события:"
        
        # Создаем кнопки с типами событий (по 2 в ряд)
        keyboard = []
        for i in range(0, len(event_types), 2):
            row = []
            for j in range(2):
                if i + j < len(event_types):
                    event_type = event_types[i + j]
                    row.append(InlineKeyboardButton(
                        event_type,
                        callback_data=create_callback_data("search_event_type", type=event_type)
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))])
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def search_events_by_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поиск событий по конкретному типу"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    event_type = data.get('type')
    page = data.get('page', 0)
    
    if not event_type:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Тип события не указан"
        )
        return
    
    chat_id = update.effective_chat.id
    
    # Выполняем поиск
    results = await search_manager.search_events(
        chat_id=chat_id,
        query="",
        filters={'event_type': event_type},
        page=page,
        per_page=5
    )
    
    await display_search_results(update, context, results, f"События типа: {event_type}", f"type_{event_type}", page)

async def text_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало текстового поиска с популярными запросами"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем популярные поисковые запросы
    popular_searches = search_manager.get_popular_searches(chat_id, limit=8)
    
    text_lines = [
        "🔤 <b>Текстовый поиск</b>",
        "",
        "Введите поисковый запрос (ФИО сотрудника, должность, тип события):"
    ]
    
    # Кнопки с популярными запросами
    keyboard = []
    
    if popular_searches:
        for i, search in enumerate(popular_searches[:4]):
            keyboard.append([InlineKeyboardButton(
                f"🔍 {search[:30]}", 
                callback_data=create_callback_data("quick_text_search", q=search[:40])
            )])
    
    keyboard.extend([
        [InlineKeyboardButton("⚙️ Расширенный поиск", callback_data=create_callback_data("text_search_advanced"))],
        [InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]
    ])
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    # Сохраняем состояние для следующего сообщения
    context.user_data['waiting_for_text_search'] = True

async def handle_text_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ввод текста для поиска"""
    if not context.user_data.get('waiting_for_text_search'):
        return
    
    search_query = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    if len(search_query) < 2:
        await update.message.reply_text(
            "⚠️ Поисковый запрос должен содержать минимум 2 символа",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))
            ]])
        )
        return
    
    # Очищаем состояние
    context.user_data['waiting_for_text_search'] = False
    
    # Выполняем поиск
    await perform_text_search(update, context, search_query, 0)

async def quick_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Быстрый поиск по популярным запросам"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    search_query = data.get('q', '')
    
    if search_query:
        await perform_text_search(update, context, search_query, 0)
    else:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: поисковый запрос не найден"
        )

async def perform_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE, search_query: str, page: int = 0) -> None:
    """Выполняет текстовый поиск и отображает результаты"""
    chat_id = update.effective_chat.id
    
    # Показываем индикатор поиска
    if hasattr(update, 'callback_query') and update.callback_query:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔍 Поиск..."
        )
    else:
        search_msg = await update.message.reply_text("🔍 Поиск...")
    
    try:
        # Выполняем умный поиск
        results = await search_manager.smart_text_search(
            chat_id=chat_id,
            query=search_query,
            page=page,
            per_page=5
        )
        
        await display_text_search_results(update, context, results, search_query, page)
        
    except Exception as e:
        logger.error(f"Error in text search: {e}")
        error_text = "❌ Ошибка при выполнении поиска"
        keyboard = [[InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]]
        
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=error_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def display_text_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: dict, query: str, page: int) -> None:
    """Отображает результаты текстового поиска"""
    events = results.get('results', [])
    pagination = results.get('pagination', {})
    suggestions = results.get('search_suggestions', [])
    
    if not events:
        text_lines = [
            f"🔍 <b>Поиск: \"{query}\"</b>",
            "",
            "❌ <b>Ничего не найдено</b>",
            ""
        ]
        
        if suggestions:
            text_lines.extend([
                "💡 <b>Возможно, вы искали:</b>"
            ])
            for suggestion in suggestions:
                text_lines.append(f"• {suggestion}")
        else:
            text_lines.extend([
                "💡 <b>Советы для поиска:</b>",
                "• Попробуйте более короткие слова",
                "• Проверьте правописание", 
                "• Используйте только часть имени или должности"
            ])
        
        keyboard = [
            [InlineKeyboardButton("🔍 Новый поиск", callback_data=create_callback_data("text_search_start"))],
            [InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]
        ]
    else:
        # Формируем результаты с подсветкой совпадений
        text_lines = [
            f"🔍 <b>Результаты поиска: \"{query}\"</b>",
            f"📊 Найдено {pagination.get('total_count', 0)} событий",
            ""
        ]
        
        for i, event in enumerate(events, 1):
            event_date = datetime.fromisoformat(event['next_notification_date']).strftime('%d.%m.%Y')
            
            # Показываем совпадения
            matches_str = ""
            if event.get('match_highlights'):
                matches_str = f" (найдено в: {', '.join(event['match_highlights'])})"
            
            text_lines.append(
                f"{i}. {event['status_emoji']} <b>{event['full_name']}</b>{matches_str}\n"
                f"   💼 {event['position']}\n"
                f"   📋 {event['event_type']}\n"
                f"   📅 {event_date} ({event['status_text']})\n"
            )
        
        # Пагинация
        if pagination.get('total_pages', 0) > 1:
            text_lines.append(
                f"📄 Страница {pagination['current_page'] + 1} из {pagination['total_pages']}"
            )
        
        # Кнопки управления
        keyboard = []
        
        # Пагинация
        pagination_buttons = []
        if pagination.get('has_prev'):
            pagination_buttons.append(
                InlineKeyboardButton("⬅️ Пред", 
                    callback_data=create_callback_data("text_search_page", q=query, p=page-1))
            )
        if pagination.get('has_next'):
            pagination_buttons.append(
                InlineKeyboardButton("След ➡️", 
                    callback_data=create_callback_data("text_search_page", q=query, p=page+1))
            )
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Дополнительные действия
        keyboard.extend([
            [InlineKeyboardButton("🔍 Новый поиск", callback_data=create_callback_data("text_search_start"))],
            [InlineKeyboardButton("⚙️ Добавить фильтры", callback_data=create_callback_data("text_search_filters", q=query))],
            [InlineKeyboardButton("🔙 К поиску", callback_data=create_callback_data("search_menu"))]
        ])
    
    text = "\n".join(text_lines)
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def text_search_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка пагинации в текстовом поиске"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    search_query = data.get('q', '')
    page = data.get('p', 0)
    
    if search_query:
        await perform_text_search(update, context, search_query, page)
    else:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: параметры поиска потеряны"
        )