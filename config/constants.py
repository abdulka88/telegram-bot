"""
Константы для Telegram бота управления периодическими событиями
"""

from enum import Enum

# Константы состояний разговора
class ConversationStates:
    ADD_NAME = 0
    ADD_POSITION = 1 
    ADD_EVENT_TYPE = 2
    ADD_LAST_DATE = 3
    ADD_INTERVAL = 4
    SET_NOTIFICATION_DAYS = 5
    
    # Состояния текстового поиска
    TEXT_SEARCH_INPUT = 6
    TEXT_SEARCH_FILTERS = 7
    
    # Состояния редактирования сотрудника
    EDIT_NAME = 8
    
    # Состояния добавления событий к существующему сотруднику
    ADD_EVENT_TO_EMPLOYEE_TYPE = 9
    ADD_EVENT_TO_EMPLOYEE_DATE = 10
    ADD_EVENT_TO_EMPLOYEE_INTERVAL = 11

# Уровни уведомлений
class NotificationLevel(Enum):
    INFO = "info"           # 90+ дней (первое уведомление за 90 дней)
    WARNING = "warning"     # 8-30 дней (уведомление за 30 дней)
    URGENT = "urgent"       # 4-7 дней (уведомление за 7 дней)
    CRITICAL = "critical"   # 0-3 дня (ежедневно)
    OVERDUE = "overdue"     # просрочено (ежедневно)

# Доступные должности
AVAILABLE_POSITIONS = [
    "Плотник",
    "Маляр", 
    "Рабочий по комплексному обслуживанию и ремонту зданий",
    "Дворник",
    "Уборщик производственных помещений",
    "Старший мастер",
    "Мастер"
]

# Соответствие должностей шаблонам
POSITION_TEMPLATE_MAPPING = {
    "Плотник": "carpenter",
    "Маляр": "painter", 
    "Рабочий по комплексному обслуживанию и ремонту зданий": "maintenance_worker",
    "Дворник": "janitor",
    "Уборщик производственных помещений": "cleaner",
    "Старший мастер": "senior_master",
    "Мастер": "master"
}

# Форматы экспорта
EXPORT_FORMATS = ['xlsx', 'csv']

# Валидация
VALIDATION_RULES = {
    'name_min_length': 2,
    'name_max_length': 100,
    'position_max_length': 50,
    'event_type_min_length': 2,
    'event_type_max_length': 50,
    'interval_min_days': 1,
    'interval_max_days': 3650,
    'notification_days_min': 1,
    'notification_days_max': 30
}