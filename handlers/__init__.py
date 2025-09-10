"""
Обработчики команд и callback'ов для Telegram бота
"""

from .menu_handlers import show_menu, menu_handler, help_command
from .employee_handlers import (
    add_employee_start, handle_contact, add_employee_name,
    handle_position_selection, list_employees, cancel_add_employee,
    cancel_add_event_to_employee
)
from .event_handlers import my_events, all_events, view_employee_details
from .export_handlers import export_menu_start, handle_export
from .template_handlers import templates_menu, select_employee_for_template, apply_template_to_employee
from .search_handlers import search_menu_start
from .dashboard_handlers import dashboard_main, dashboard_analytics, dashboard_employees

__all__ = [
    # Меню и навигация
    'show_menu', 'menu_handler', 'help_command',
    
    # Управление сотрудниками
    'add_employee_start', 'handle_contact', 'add_employee_name',
    'handle_position_selection', 'list_employees', 'cancel_add_employee',
    'cancel_add_event_to_employee',
    
    # События
    'my_events', 'all_events', 'view_employee_details',
    
    # Экспорт
    'export_menu_start', 'handle_export',
    
    # Шаблоны
    'templates_menu', 'select_employee_for_template', 'apply_template_to_employee',
    
    # Поиск
    'search_menu_start',
    
    # Дашборд
    'dashboard_main', 'dashboard_analytics', 'dashboard_employees'
]