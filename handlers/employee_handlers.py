"""
Обработчики для управления сотрудниками
"""

import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler

from config.constants import ConversationStates, AVAILABLE_POSITIONS
from core.database import db_manager
from core.security import encrypt_data, decrypt_data, is_admin
from core.utils import create_callback_data, parse_callback_data, validate_name, validate_event_type, validate_date, validate_interval
from managers.template_manager import TemplateManager

# Инициализируем template_manager
template_manager = TemplateManager(db_manager)

logger = logging.getLogger(__name__)

async def add_employee_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса добавления сотрудника"""
    logger.info(f"🚀 add_employee_start вызвана! Update: {type(update)}")
    
    # Additional logging to debug the issue
    logger.info(f"🔍 Callback query data: {update.callback_query.data if update.callback_query else 'No callback query'}")
    
    query = update.callback_query
    logger.info(f"📞 Callback query: {query.data if query else 'None'}")
    
    # Обработка таймаутов
    if query:
        try:
            await query.answer()
            logger.info(f"✅ query.answer() выполнен успешно")
        except Exception as e:
            logger.warning(f"Failed to answer callback query in add_employee_start: {e}")

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    logger.info(f"👤 Chat ID: {chat_id}, User ID: {user_id}")

    if not is_admin(chat_id, user_id):
        logger.warning(f"❌ Пользователь {user_id} не является администратором")
        if query:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Только администратор может добавлять сотрудников"
            )
        else:
            await update.message.reply_text("❌ Только администратор может добавлять сотрудников")
        return ConversationHandler.END
    
    logger.info(f"✅ Проверка администратора пройдена")

    # Создаем клавиатуру с кнопкой отмены
    from telegram import ReplyKeyboardMarkup, KeyboardButton
    keyboard = [[KeyboardButton("❌ Отмена")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    # Отправляем сообщение с запросом ФИО с клавиатурой отмены
    # Сохраняем главное меню, отправляем новое сообщение поверх
    logger.info(f"📤 Отправляем сообщение с запросом ФИО...")
    if query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Введите ФИО сотрудника:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Введите ФИО сотрудника:", reply_markup=reply_markup)
        
    logger.info(f"✅ Сообщение отправлено, переходим в состояние ADD_NAME")
    return ConversationStates.ADD_NAME

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка контакта сотрудника"""
    contact = update.message.contact
    context.user_data['user_id'] = contact.user_id
    context.user_data['full_name'] = f"{contact.first_name} {contact.last_name}" if contact.last_name else contact.first_name

    # Показываем клавиатуру выбора должности
    await show_position_selection(update, context)
    return ConversationStates.ADD_POSITION

async def add_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода ФИО сотрудника"""
    logger.info(f"🔥🔥🔥 add_employee_name ВЫЗВАНА! Текст: '{update.message.text}'")
    logger.info(f"🔍 Получено сообщение в ConversationHandler ADD_NAME")
    
    # Additional logging to debug the issue
    logger.info(f"🔍 Update type: {type(update)}")
    logger.info(f"🔍 Update message type: {type(update.message)}")
    logger.info(f"🔍 Update message text: {update.message.text if update.message else 'No message'}")
    logger.info(f"🔍 Context user data: {context.user_data}")
    logger.info(f"🔍 Chat ID: {update.effective_chat.id if update.effective_chat else 'No chat'}")
    logger.info(f"🔍 User ID: {update.effective_user.id if update.effective_user else 'No user'}")
    
    # Check if we're in the right state
    logger.info(f"🔍 Current conversation state: {context.user_data.get('conversation_state', 'Not set')}")
    
    if not update.message or not update.message.text:
        logger.error("❌ No message text received in add_employee_name")
        return ConversationStates.ADD_NAME
    
    # Проверяем, не нажата ли кнопка отмены
    if update.message.text == "❌ Отмена":
        # Удаляем сообщение с ФИО и сообщение с кнопкой отмены
        from core.utils import delete_message_safely
        await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
        
        # Отправляем сообщение об отмене и убираем клавиатуру
        from telegram import ReplyKeyboardRemove
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Добавление сотрудника отменено",
            reply_markup=ReplyKeyboardRemove()
        )
        # Показываем главное меню снова
        from handlers.menu_handlers import show_menu
        await show_menu(update, context)
        return ConversationHandler.END
    
    # Не удаляем главное меню, отправляем новое сообщение
    # Удаляем только сообщение с вводом ФИО
    from core.utils import delete_message_safely
    await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
    
    full_name = update.message.text
    logger.info(f"📝 Полученное имя: '{full_name}'")
    
    if not validate_name(full_name):
        logger.warning(f"❌ Валидация имени не прошла: '{full_name}'")
        # Отправляем сообщение с ошибкой без клавиатуры
        from telegram import ReplyKeyboardRemove
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный формат имени. Должно быть 2-100 символов.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationStates.ADD_NAME

    logger.info(f"✅ Валидация прошла успешно")
    context.user_data['full_name'] = full_name
    logger.info(f"💾 Имя сохранено в user_data: '{full_name}'")
    
    # Показываем клавиатуру выбора должности и убираем клавиатуру отмены
    from telegram import ReplyKeyboardRemove
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите должность из списка ниже:", 
        reply_markup=ReplyKeyboardRemove()
    )  # Убираем клавиатуру с непустым текстом
    logger.info(f"🎯 Вызываем show_position_selection...")
    await show_position_selection(update, context)
    logger.info(f"✅ show_position_selection выполнена, возвращаем ADD_POSITION")
    
    return ConversationStates.ADD_POSITION

async def show_position_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает клавиатуру с выбором должностями"""
    logger.info(f"🎯 show_position_selection вызвана")
    
    # Additional logging to debug the issue
    logger.info(f"🔍 Update type: {type(update)}")
    logger.info(f"🔍 Update message type: {type(update.message) if update.message else 'No message'}")
    logger.info(f"🔍 Full name in context: {context.user_data.get('full_name', 'Not found')}")
    logger.info(f"🔍 Update effective chat: {update.effective_chat if update.effective_chat else 'No chat'}")
    logger.info(f"🔍 Update effective user: {update.effective_user if update.effective_user else 'No user'}")
    logger.info(f"🔍 Update callback query: {update.callback_query if update.callback_query else 'No callback query'}")
    
    # Не удаляем главное меню, отправляем новое сообщение с выбором должности
    
    # Создаем клавиатуру с должностями (по 2 в ряду)
    keyboard = []
    logger.info(f"📝 Создаем клавиатуру с {len(AVAILABLE_POSITIONS)} должностями")
    
    for i in range(0, len(AVAILABLE_POSITIONS), 2):
        row = []
        for j in range(2):
            if i + j < len(AVAILABLE_POSITIONS):
                # Use index instead of full position name to stay within 64-character limit
                callback_data = create_callback_data("select_position", position_index=i + j)
                logger.info(f"   Creating button: {AVAILABLE_POSITIONS[i + j]} with callback_data: {callback_data}")
                row.append(InlineKeyboardButton(
                    AVAILABLE_POSITIONS[i + j],
                    callback_data=callback_data
                ))
        keyboard.append(row)
    
    # Добавляем кнопку отмены
    cancel_callback_data = create_callback_data("cancel_add_employee")
    logger.info(f"   Creating cancel button with callback_data: {cancel_callback_data}")
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=cancel_callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.info(f"✅ Клавиатура создана: {len(keyboard)} рядов")
    
    # Получаем имя сотрудника из контекста или используем значение по умолчанию
    full_name = context.user_data.get('full_name', 'Неизвестный сотрудник')
    
    # Отправляем сообщение с инлайн клавиатурой поверх главного меню
    try:
        logger.info(f"📤 Отправляем сообщение с клавиатурой...")
        chat_id = update.effective_chat.id
        
        # Отправляем новое сообщение с инлайн клавиатурой поверх главного меню
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"👤 Сотрудник: <b>{full_name}</b>\n\n"
                 "💼 Выберите должность:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        logger.info(f"✅ Основное сообщение отправлено, message_id: {message.message_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения с клавиатурой: {e}")
        logger.error(f"❌ Update details: {update}")
        logger.error(f"❌ Context user data: {context.user_data}")

async def handle_position_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора должности из списка"""
    logger.info("📥 handle_position_selection called!")
    logger.info(f"   Update type: {type(update)}")
    logger.info(f"   Full update object: {update}")
    
    if not update.callback_query:
        logger.error("❌ No callback query in update")
        return ConversationHandler.END
        
    query = update.callback_query
    logger.info(f"   Callback query data: {query.data if query.data else 'No data'}")
    
    # Обработка таймаутов
    try:
        await query.answer()
        logger.info("✅ Callback query answered")
    except Exception as e:
        logger.warning(f"Failed to answer callback query in handle_position_selection: {e}")
    
    # Не удаляем главное меню, отправляем новое сообщение
    # Удаляем только сообщение с выбором должности
    if query.message:
        from core.utils import delete_message_safely
        await delete_message_safely(context, query.message.chat_id, query.message.message_id)
    
    if not query.data:
        logger.error("❌ No data in callback query")
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: нет данных в callback-запросе"
        )
        return ConversationHandler.END
    
    data = parse_callback_data(query.data)
    logger.info(f"   Parsed data: {data}")
    
    # Get position by index instead of directly
    position_index = data.get('position_index')
    if position_index is not None and 0 <= position_index < len(AVAILABLE_POSITIONS):
        position = AVAILABLE_POSITIONS[position_index]
    else:
        position = None
    
    logger.info(f"   Position: {position}")
    
    if not position:
        logger.warning("❌ No position in callback data")
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка при выборе должности"
        )
        return ConversationHandler.END
    
    user_data = context.user_data
    full_name = user_data.get('full_name')
    logger.info(f"   Full name from context: {full_name}")
    
    # Проверяем, что у нас есть имя сотрудника
    if not full_name:
        logger.warning("❌ No full name in user data")
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: не указано имя сотрудника"
        )
        return ConversationHandler.END
    
    user_id = user_data.get('user_id')
    chat_id = update.effective_chat.id
    logger.info(f"   User ID: {user_id}, Chat ID: {chat_id}")

    # Шифрование конфиденциальных данных
    encrypted_name = encrypt_data(full_name)
    logger.info("✅ Name encrypted")

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO employees (chat_id, user_id, full_name, position)
                   VALUES (?, ?, ?, ?)''',
                (chat_id, user_id, encrypted_name, position)
            )
            # Сохраняем ID нового сотрудника
            user_data['new_employee_id'] = cursor.lastrowid
            conn.commit()
            logger.info(f"✅ Employee inserted with ID: {cursor.lastrowid}")

        # Автоматически применяем шаблон для выбранной должности
        employee_id = user_data['new_employee_id']
        template_applied = await template_manager.apply_template_by_position(employee_id, position)
        logger.info(f"   Template applied: {template_applied}")

        # Если шаблон применен, запрашиваем даты для прошедших событий
        if template_applied:
            # Получаем список событий для этой должности
            template_key = template_manager.get_template_by_position(position)
            if template_key:
                template_info = template_manager.get_template_info(template_key)
                if template_info and template_info['events']:
                    # Сохраняем список событий в user_data
                    user_data['pending_events'] = template_info['events'].copy()
                    user_data['completed_events'] = []
                    user_data['position'] = position  # Сохраняем должность для последующего использования
                    
                    # Переходим к запросу дат для прошедших событий
                    await request_past_event_dates(update, context)
                    return ConversationStates.ADD_PAST_EVENT_DATES
        
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Сотрудник <b>{full_name}</b> с должностью <b>{position}</b> успешно добавлен!",
            parse_mode='HTML'
        )
        # Показываем главное меню снова
        from handlers.menu_handlers import show_menu
        await show_menu(update, context)
        return ConversationHandler.END
        
    except sqlite3.IntegrityError as e:
        logger.error(f"SQLite integrity error: {e}")
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Сотрудник с таким именем уже существует"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error saving employee: {e}", exc_info=True)
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Произошла ошибка при сохранении сотрудника"
        )
        return ConversationHandler.END

async def request_past_event_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает даты прошедших событий у пользователя"""
    user_data = context.user_data
    pending_events = user_data.get('pending_events', [])
    
    if not pending_events:
        # Все события обработаны
        full_name = user_data.get('full_name', 'Неизвестный сотрудник')
        position = user_data.get('position', 'Неизвестная должность')
        
        # Не удаляем главное меню, отправляем новое сообщение
        # Удаляем только сообщение с запросом даты
        if update.callback_query and update.callback_query.message:
            from core.utils import delete_message_safely
            await delete_message_safely(context, update.effective_chat.id, update.callback_query.message.message_id)
        elif update.message:
            from core.utils import delete_message_safely
            await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Сотрудник <b>{full_name}</b> с должностью <b>{position}</b> успешно добавлен!\n\n"
                 f"🎯 Все события обработаны и добавлены в календарь.",
            parse_mode='HTML'
        )
        # Показываем главное меню снова
        from handlers.menu_handlers import show_menu
        await show_menu(update, context)
        return
    
    # Берем первое событие из списка
    current_event = pending_events[0]
    event_type = current_event['type']
    interval_days = current_event['interval_days']
    
    # Сохраняем текущее событие
    user_data['current_event'] = current_event
    
    # Не удаляем главное меню, отправляем новое сообщение
    # Удаляем только сообщение с запросом даты
    if update.callback_query and update.callback_query.message:
        from core.utils import delete_message_safely
        await delete_message_safely(context, update.effective_chat.id, update.callback_query.message.message_id)
    elif update.message:
        from core.utils import delete_message_safely
        await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
    
    # Отправляем сообщение с запросом даты поверх главного меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"📅 Введите дату последнего события <b>«{event_type}»</b> в формате ДД.ММ.ГГГГ\n\n"
             f"ℹ️ Интервал повторения: {interval_days} дней",
        parse_mode='HTML'
    )

async def handle_past_event_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода даты прошедшего события"""
    user_data = context.user_data
    current_event = user_data.get('current_event')
    
    if not current_event:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: нет данных о текущем событии"
        )
        return ConversationHandler.END
    
    # Не удаляем главное меню, отправляем новое сообщение
    # Удаляем только сообщение с вводом даты
    from core.utils import delete_message_safely
    await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
    
    date_str = update.message.text
    if not validate_date(date_str):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ"
        )
        return ConversationStates.ADD_PAST_EVENT_DATE_INPUT
    
    try:
        # Преобразуем дату в объект datetime
        last_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        
        # Обновляем дату события в базе данных
        employee_id = user_data['new_employee_id']
        event_type = current_event['type']
        interval_days = current_event['interval_days']
        
        # Рассчитываем следующую дату уведомления
        from datetime import timedelta
        next_date = last_date + timedelta(days=interval_days)
        
        # Обновляем событие в базе данных
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE employee_events 
                SET last_event_date = ?, next_notification_date = ?
                WHERE employee_id = ? AND event_type = ?
            ''', (last_date.isoformat(), next_date.isoformat(), employee_id, event_type))
            conn.commit()
        
        # Добавляем событие в список завершенных
        completed_events = user_data.get('completed_events', [])
        completed_events.append(current_event)
        user_data['completed_events'] = completed_events
        
        # Удаляем событие из списка ожидающих
        pending_events = user_data.get('pending_events', [])
        if pending_events:
            pending_events.pop(0)
            user_data['pending_events'] = pending_events
        
        # Если есть еще события, запрашиваем дату для следующего
        if pending_events:
            await request_past_event_dates(update, context)
            return ConversationStates.ADD_PAST_EVENT_DATES
        else:
            # Все события обработаны
            full_name = user_data.get('full_name', 'Неизвестный сотрудник')
            position = user_data.get('position', 'Неизвестная должность')
            
            # Не удаляем главное меню, отправляем новое сообщение
            # Удаляем только сообщение с вводом даты
            from core.utils import delete_message_safely
            await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Сотрудник <b>{full_name}</b> с должностью <b>{position}</b> успешно добавлен!\n\n"
                     f"🎯 Все события обработаны и добавлены в календарь.",
                parse_mode='HTML'
            )
            # Показываем главное меню снова
            from handlers.menu_handlers import show_menu
            await show_menu(update, context)
            return ConversationHandler.END
            
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверная дата. Проверьте правильность ввода."
        )
        return ConversationStates.ADD_PAST_EVENT_DATE_INPUT
    except Exception as e:
        logger.error(f"Error updating event date: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Произошла ошибка при обновлении даты события"
        )
        return ConversationHandler.END

async def add_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода типа события"""
    event_type = update.message.text
    if not validate_event_type(event_type):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный формат типа события. Должно быть 2-50 символов."
        )
        return ConversationStates.ADD_EVENT_TYPE

    context.user_data['event_type'] = event_type
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите дату последнего события в формате ДД.ММ.ГГГГ (например, 15.05.2023):"
    )
    return ConversationStates.ADD_LAST_DATE

async def add_last_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода даты последнего события"""
    date_str = update.message.text
    if not validate_date(date_str):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ"
        )
        return ConversationStates.ADD_LAST_DATE

    try:
        # Преобразуем дату в объект datetime
        last_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        context.user_data['last_date'] = last_date.isoformat()

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Введите интервал в днях между событиями (например, 365):"
        )
        return ConversationStates.ADD_INTERVAL
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверная дата. Проверьте правильность ввода."
        )
        return ConversationStates.ADD_LAST_DATE

async def add_interval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода интервала и сохранение события"""
    interval_str = update.message.text
    if not validate_interval(interval_str):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный интервал. Введите число от 1 до 3650."
        )
        return ConversationStates.ADD_INTERVAL

    interval = int(interval_str)
    user_data = context.user_data

    # Рассчитываем следующую дату уведомления
    from datetime import timedelta
    last_date = datetime.fromisoformat(user_data['last_date']).date()
    next_date = last_date + timedelta(days=interval)

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO employee_events 
                   (employee_id, event_type, last_event_date, interval_days, next_notification_date)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_data['new_employee_id'], user_data['event_type'],
                 user_data['last_date'], interval, next_date.isoformat())
            )
            conn.commit()

        # Завершаем процесс
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Событие '{user_data['event_type']}' успешно добавлено!\n"
            f"Следующее уведомление: {next_date.strftime('%d.%m.%Y')}",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error saving event: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Произошла ошибка при сохранении события"
        )
        return ConversationHandler.END

async def cancel_add_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка отмены добавления сотрудника"""
    # Не удаляем главное меню, отправляем новое сообщение
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Удаляем только сообщение с кнопкой отмены
        from core.utils import delete_message_safely
        await delete_message_safely(context, update.effective_chat.id, query.message.message_id)
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Добавление сотрудника отменено"
        )
    else:
        # Удаляем сообщение с кнопкой отмены
        from core.utils import delete_message_safely
        await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Добавление сотрудника отменено",
            reply_markup=ReplyKeyboardRemove()
        )
    # Показываем главное меню снова
    from handlers.menu_handlers import show_menu
    await show_menu(update, context)
    return ConversationHandler.END

async def list_employees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список сотрудников с пагинацией"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Проверка прав администратора
    if not is_admin(chat_id, user_id):
        if update.callback_query:
            await update.callback_query.answer()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Только администратор может просматривать список сотрудников."
            )
        return

    from config.settings import BotConfig
    page = context.user_data.get('employee_page', 0)
    limit = BotConfig.EMPLOYEES_PER_PAGE
    offset = page * limit

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Подсчитываем общее количество
            cursor.execute(
                "SELECT COUNT(*) as count FROM employees WHERE chat_id = ? AND is_active = 1",
                (chat_id,)
            )
            total_count = cursor.fetchone()['count']

            # Получаем сотрудников для текущей страницы
            cursor.execute(
                '''SELECT id, full_name, position 
                   FROM employees 
                   WHERE chat_id = ? AND is_active = 1 
                   ORDER BY full_name 
                   LIMIT ? OFFSET ?''',
                (chat_id, limit, offset)
            )
            employees = cursor.fetchall()

        if not employees and page == 0:
            response = "ℹ️ Список сотрудников пуст. Добавьте первого сотрудника!"
            if update.callback_query:
                await update.callback_query.answer()
                # Отправляем новое сообщение вместо редактирования
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=response
                )
            return

        # Формирование сообщения
        response = [f"📋 <b>Список сотрудников (страница {page + 1}/{((total_count - 1) // limit) + 1}):</b>"]
        for emp in employees:
            try:
                decrypted_name = decrypt_data(emp['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            response.append(f"• {decrypted_name} ({emp['position']})")

        # Создание кнопок для каждого сотрудника
        keyboard = []
        for emp in employees:
            try:
                decrypted_name = decrypt_data(emp['full_name'])
            except ValueError:
                decrypted_name = "Ошибка дешифрации"
            keyboard.append([
                InlineKeyboardButton(
                    f"{decrypted_name}",
                    callback_data=create_callback_data("select_employee", id=emp['id'])
                )
            ])

        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=create_callback_data("emp_page", page=page - 1)
            ))
        if (page + 1) * limit < total_count:
            nav_buttons.append(InlineKeyboardButton(
                "Вперед ➡️",
                callback_data=create_callback_data("emp_page", page=page + 1)
            ))

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton(
            "🔙 Главное меню",
            callback_data=create_callback_data("menu")
        )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправка сообщения
        if update.message:
            await update.message.reply_text(
                "\n".join(response),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            query = update.callback_query
            await query.answer()
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\n".join(response),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        # Сохранение номера страницы
        context.user_data['employee_page'] = page

    except Exception as e:
        logger.error(f"Error in list_employees: {e}")
        error_msg = "❌ Произошла ошибка при получении списка сотрудников"
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            query = update.callback_query
            await query.answer()
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_msg
            )

async def view_employee_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детали сотрудника и его события"""
    from handlers.event_handlers import view_employee_details as view_details
    await view_details(update, context)

async def edit_employee_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало редактирования сотрудника"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    
    if not employee_id:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: сотрудник не найден"
        )
        return
    
    # Получаем данные сотрудника
    employee = db_manager.execute_with_retry('''
        SELECT id, full_name, position FROM employees WHERE id = ?
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
    
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить имя", callback_data=create_callback_data("edit_name", id=employee_id))],
        [InlineKeyboardButton("💼 Изменить должность", callback_data=create_callback_data("edit_position", id=employee_id))],
        [InlineKeyboardButton("📅 Добавить событие", callback_data=create_callback_data("add_event_to_employee", id=employee_id))],
        [InlineKeyboardButton("🗑️ Удалить сотрудника", callback_data=create_callback_data("delete_employee", id=employee_id))],
        [InlineKeyboardButton("🔙 К сотруднику", callback_data=create_callback_data("select_employee", id=employee_id))]
    ]
    
    text = (
        f"✏️ <b>Редактирование сотрудника</b>\n\n"
        f"👤 Имя: <b>{decrypted_name}</b>\n"
        f"💼 Должность: <b>{employee['position']}</b>\n\n"
        f"Выберите действие:"
    )
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def edit_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало редактирования имени сотрудника"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    
    if not employee_id:
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: сотрудник не найден"
        )
        return ConversationHandler.END
    
    # Получаем текущие данные
    employee = db_manager.execute_with_retry('''
        SELECT full_name, position FROM employees WHERE id = ?
    ''', (employee_id,), fetch="one")
    
    if not employee:
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Сотрудник не найден"
        )
        return ConversationHandler.END
    
    try:
        current_name = decrypt_data(employee['full_name'])
    except ValueError:
        current_name = "Ошибка дешифрации"
    
    # Сохраняем ID сотрудника в контекст
    context.user_data['editing_employee_id'] = employee_id
    
    # Создаем клавиатуру с кнопкой отмены
    keyboard = [
        [KeyboardButton("❌ Отмена")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Отправляем сообщение с запросом поверх главного меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"✏️ <b>Редактирование имени сотрудника</b>\n\n"
            f"👤 Текущее имя: <b>{current_name}</b>\n"
            f"💼 Должность: <b>{employee['position']}</b>\n\n"
            f"Введите новое ФИО сотрудника:"
        ),
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return ConversationStates.EDIT_NAME

async def save_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение нового имени сотрудника"""
    new_name = update.message.text
    
    # Проверяем отмену
    if new_name == "❌ Отмена":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Редактирование отменено",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Проверяем валидность имени
    if not validate_name(new_name):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный формат имени. Должно быть 2-100 символов."
        )
        return ConversationStates.EDIT_NAME
    
    employee_id = context.user_data.get('editing_employee_id')
    if not employee_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: не удается определить сотрудника",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    try:
        # Получаем старое имя для логирования
        employee = db_manager.execute_with_retry('''
            SELECT full_name, position FROM employees WHERE id = ?
        ''', (employee_id,), fetch="one")
        
        if not employee:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Сотрудник не найден",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        try:
            old_name = decrypt_data(employee['full_name'])
        except ValueError:
            old_name = "Ошибка дешифрации"
        
        # Проверяем, что имя действительно изменилось
        if old_name == new_name:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"ℹ️ <b>Имя не изменено</b>\n\n"
                     f"👤 Имя: <b>{new_name}</b>\n"
                     f"💼 Должность: <b>{employee['position']}</b>\n\n"
                     f"Имя уже было установлено.",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='HTML'
            )
            return ConversationHandler.END
        
        # Шифруем новое имя
        encrypted_name = encrypt_data(new_name)
        
        # Обновляем имя в базе
        db_manager.execute_with_retry('''
            UPDATE employees SET full_name = ? WHERE id = ?
        ''', (encrypted_name, employee_id))
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ <b>Имя сотрудника изменено!</b>\n\n"
                 f"👤 Старое имя: <b>{old_name}</b>\n"
                 f"👤 Новое имя: <b>{new_name}</b>\n"
                 f"💼 Должность: <b>{employee['position']}</b>",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        # Логируем изменение
        logger.info(f"Employee {employee_id} name changed from '{old_name}' to '{new_name}'")
        
        return ConversationHandler.END
        
    except sqlite3.IntegrityError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Сотрудник с таким именем уже существует",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error updating employee name: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка при обновлении имени",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def cancel_edit_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена редактирования имени сотрудника"""
    # Удаляем сообщение с кнопкой отмены если это сообщение
    if update.message:
        from core.utils import delete_message_safely
        await delete_message_safely(context, update.effective_chat.id, update.message.message_id)
    
    # Отправляем сообщение об отмене и убираем клавиатуру
    from telegram import ReplyKeyboardRemove
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="❌ Редактирование имени сотрудника отменено",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def edit_employee_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Редактирование должности сотрудника"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    
    if not employee_id:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: сотрудник не найден"
        )
        return
    
    # Получаем текущие данные сотрудника
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
    
    # Создаем клавиатуру с должностями (по 2 в ряду)
    keyboard = []
    for i in range(0, len(AVAILABLE_POSITIONS), 2):
        row = []
        for j in range(2):
            if i + j < len(AVAILABLE_POSITIONS):
                position = AVAILABLE_POSITIONS[i + j]
                # Отмечаем текущую должность
                prefix = "✅ " if position == employee['position'] else ""
                row.append(InlineKeyboardButton(
                    f"{prefix}{position}",
                    callback_data=create_callback_data("save_position", id=employee_id, pos_index=i + j)
                ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Редактирование", callback_data=create_callback_data("edit_employee", id=employee_id))])
    
    text = (
        f"💼 <b>Изменение должности</b>\n\n"
        f"👤 Сотрудник: <b>{decrypted_name}</b>\n"
        f"Текущая должность: <b>{employee['position']}</b>\n\n"
        f"Выберите новую должность:"
    )
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def save_employee_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохранение новой должности сотрудника с автоматическим применением шаблонов"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    pos_index = data.get('pos_index')
    
    # Get position by index instead of directly
    if pos_index is not None and 0 <= pos_index < len(AVAILABLE_POSITIONS):
        new_position = AVAILABLE_POSITIONS[pos_index]
    else:
        new_position = None
    
    if not employee_id or not new_position:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: недостаточно данных"
        )
        return
    
    try:
        # Получаем текущие данные сотрудника
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
            
        old_position = employee['position']
        
        try:
            decrypted_name = decrypt_data(employee['full_name'])
        except ValueError:
            decrypted_name = "Ошибка дешифрации"
        
        # Если должность не изменилась
        if old_position == new_position:
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"ℹ️ <b>Должность не изменена</b>\n\n"
                     f"👤 Сотрудник: <b>{decrypted_name}</b>\n"
                     f"💼 Должность: <b>{new_position}</b>\n\n"
                     f"Должность уже была установлена.",
                parse_mode='HTML'
            )
            return
        
        # Обновляем должность
        db_manager.execute_with_retry('''
            UPDATE employees SET position = ? WHERE id = ?
        ''', (new_position, employee_id))
        
        # Применяем шаблон для новой должности
        template_applied = await template_manager.apply_template_by_position(employee_id, new_position)
        
        if template_applied:
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ <b>Должность изменена и шаблон применен!</b>\n\n"
                     f"👤 Сотрудник: <b>{decrypted_name}</b>\n"
                     f"💼 Старая должность: <b>{old_position}</b>\n"
                     f"💼 Новая должность: <b>{new_position}</b>\n\n"
                     f"🎯 Автоматически применен шаблон событий для должности <b>{new_position}</b>.\n"
                     f"📅 Все необходимые события добавлены в календарь.",
                parse_mode='HTML'
            )
        else:
            # Отправляем новое сообщение вместо редактирования
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ <b>Должность изменена!</b>\n\n"
                     f"👤 Сотрудник: <b>{decrypted_name}</b>\n"
                     f"💼 Старая должность: <b>{old_position}</b>\n"
                     f"💼 Новая должность: <b>{new_position}</b>\n\n"
                     f"ℹ️ Шаблон для данной должности не найден или уже применен.",
                parse_mode='HTML'
            )
        
        # Логируем изменение
        logger.info(f"Employee {employee_id} ({decrypted_name}) position changed from '{old_position}' to '{new_position}', template applied: {template_applied}")
        
    except Exception as e:
        logger.error(f"Error updating employee position: {e}")
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка при обновлении должности"
        )

async def add_event_to_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления события существующему сотруднику"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    
    if not employee_id:
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: сотрудник не найден"
        )
        return ConversationHandler.END
    
    # Сохраняем ID сотрудника в контексте
    context.user_data['current_employee_id'] = employee_id
    
    # Создаем клавиатуру с кнопкой отмены
    keyboard = [
        [KeyboardButton("❌ Отмена")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Отправляем сообщение с запросом поверх главного меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите тип периодического события (например, 'Медосмотр' / 'Проверка знаний П-1' и т.д.):",
        reply_markup=reply_markup
    )
    
    return ConversationStates.ADD_EVENT_TO_EMPLOYEE_TYPE

async def add_event_to_employee_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода названия события"""
    event_type = update.message.text.strip()
    
    if not validate_event_type(event_type):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверное название события.\n"
            "Должно быть от 2 до 50 символов.\n\n"
            "Попробуйте ещё раз:"
        )
        return ConversationStates.ADD_EVENT_TO_EMPLOYEE_TYPE
    
    context.user_data['new_event_type'] = event_type
    
    employee_name = context.user_data.get('current_employee_name', 'Неизвестно')
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Название: <b>{event_type}</b>\n\n"
             f"📅 Теперь введите дату последнего события\n"
             f"в формате ДД.ММ.ГГГГ\n\n"
             f"ℹ️ Пример: 15.03.2024",
        parse_mode='HTML'
    )
    
    return ConversationStates.ADD_EVENT_TO_EMPLOYEE_DATE

async def add_event_to_employee_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода даты последнего события"""
    date_str = update.message.text.strip()
    
    if not validate_date(date_str):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный формат даты.\n"
            "Используйте формат ДД.ММ.ГГГГ\n\n"
            "Пример: 15.03.2024"
        )
        return ConversationStates.ADD_EVENT_TO_EMPLOYEE_DATE
    
    try:
        # Преобразуем дату в объект datetime
        last_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        context.user_data['new_event_last_date'] = last_date.isoformat()
        
        event_type = context.user_data.get('new_event_type', 'Неизвестно')
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Дата последнего события: <b>{date_str}</b>\n\n"
                 f"🔄 Теперь введите интервал в днях\n"
                 f"между событиями '{event_type}'\n\n"
                 f"ℹ️ Примеры: 365 (год), 180 (полгода), 90 (3 месяца)",
            parse_mode='HTML'
        )
        
        return ConversationStates.ADD_EVENT_TO_EMPLOYEE_INTERVAL
        
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверная дата. Проверьте правильность ввода.\n"
            "Формат: ДД.ММ.ГГГГ"
        )
        return ConversationStates.ADD_EVENT_TO_EMPLOYEE_DATE

async def add_event_to_employee_interval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода интервала и сохранение события сотрудника"""
    interval_str = update.message.text.strip()
    
    if not validate_interval(interval_str):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Неверный интервал.\n"
            "Введите число от 1 до 3650."
        )
        return ConversationStates.ADD_EVENT_TO_EMPLOYEE_INTERVAL

    interval = int(interval_str)
    user_data = context.user_data

    # Рассчитываем следующую дату уведомления
    from datetime import timedelta
    last_date = datetime.fromisoformat(user_data['new_event_last_date']).date()
    next_date = last_date + timedelta(days=interval)

    try:
        employee_id = user_data['current_employee_id']
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO employee_events 
                   (employee_id, event_type, last_event_date, interval_days, next_notification_date)
                   VALUES (?, ?, ?, ?, ?)''',
                (employee_id, user_data['new_event_type'],
                 user_data['new_event_last_date'], interval, next_date.isoformat())
            )
            conn.commit()

        # Завершаем процесс
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Событие успешно добавлено сотруднику!\n\n"
            f"👤 Сотрудник: <b>{user_data['current_employee_name']}</b>\n"
            f"📝 Событие: <b>{user_data['new_event_type']}</b>\n"
            f"📅 Последнее событие: <b>{last_date.strftime('%d.%m.%Y')}</b>\n"
            f"🔄 Интервал: <b>{interval}</b> дней\n"
            f"🔔 Следующее уведомление: <b>{next_date.strftime('%d.%m.%Y')}</b>",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error saving employee event: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Произошла ошибка при сохранении события",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def cancel_add_event_to_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена добавления события к сотруднику"""
    # Очищаем временные данные
    for key in ['current_employee_id', 'current_employee_name', 'current_employee_position',
               'new_event_type', 'new_event_last_date']:
        context.user_data.pop(key, None)
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Отправляем новое сообщение поверх главного меню
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Добавление события отменено"
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Добавление события отменено"
        )
    
    return ConversationHandler.END

async def delete_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ подтверждения удаления сотрудника"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    
    if not employee_id:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: сотрудник не найден"
        )
        return
    
    # Получаем данные сотрудника
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
    
    # Подсчитываем количество событий
    events_count = db_manager.execute_with_retry('''
        SELECT COUNT(*) as count FROM employee_events WHERE employee_id = ?
    ''', (employee_id,), fetch="one")['count']
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Да, удалить", callback_data=create_callback_data("confirm_delete", id=employee_id))],
        [InlineKeyboardButton("❌ Отмена", callback_data=create_callback_data("edit_employee", id=employee_id))]
    ]
    
    text = (
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"👤 Сотрудник: <b>{decrypted_name}</b>\n"
        f"💼 Должность: <b>{employee['position']}</b>\n"
        f"📅 События: <b>{events_count} шт.</b>\n\n"
        f"🚨 <b>ВНИМАНИЕ!</b> Это действие нельзя отменить.\n"
        f"Будут безвозвратно удалены:\n"
        f"• Данные сотрудника\n"
        f"• Все его события ({events_count} шт.)\n"
        f"• История уведомлений\n\n"
        f"Вы уверены?"
    )
    
    # Отправляем новое сообщение вместо редактирования
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def confirm_delete_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Окончательное удаление сотрудника и всех его событий"""
    query = update.callback_query
    await query.answer()
    
    data = parse_callback_data(query.data)
    employee_id = data.get('id')
    
    if not employee_id:
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ошибка: сотрудник не найден"
        )
        return
    
    # Получаем данные сотрудника для логирования
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
    
    try:
        # Подсчитываем количество событий перед удалением
        events_count = db_manager.execute_with_retry('''
            SELECT COUNT(*) as count FROM employee_events WHERE employee_id = ?
        ''', (employee_id,), fetch="one")['count']
        
        # Удаляем все события сотрудника
        events_deleted = db_manager.execute_with_retry('''
            DELETE FROM employee_events WHERE employee_id = ?
        ''', (employee_id,))
        
        # Удаляем самого сотрудника
        employee_deleted = db_manager.execute_with_retry('''
            DELETE FROM employees WHERE id = ?
        ''', (employee_id,))
        
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ <b>Сотрудник успешно удален</b>\n\n"
                 f"👤 Удален: <b>{decrypted_name}</b>\n"
                 f"💼 Должность: <b>{employee['position']}</b>\n"
                 f"📅 Удалено событий: <b>{events_count} шт.</b>\n\n"
                 f"🗑️ Все данные безвозвратно удалены из системы.",
            parse_mode='HTML'
        )
        
        # Логируем удаление
        logger.info(f"Employee {employee_id} ({decrypted_name}) and {events_count} events deleted")
        
    except Exception as e:
        logger.error(f"Error deleting employee {employee_id}: {e}")
        # Отправляем новое сообщение вместо редактирования
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Ошибка при удалении</b>\n\n"
                 f"Произошла ошибка при удалении сотрудника.\n"
                 f"Обратитесь к администратору.",
            parse_mode='HTML'
        )

# Removed duplicate conversation handler to prevent conflicts
# The conversation handler is properly defined in main.py

# Conversation handler for employee management

