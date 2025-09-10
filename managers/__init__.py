"""
Инициализация всех менеджеров для Telegram бота
"""

from core.database import db_manager
from managers.notification_manager import NotificationManager
from managers.export_manager import ExportManager
from managers.search_manager import SearchManager
from managers.template_manager import TemplateManager
from managers.dashboard_manager import DashboardManager
from managers.advanced_analytics_manager import AdvancedAnalyticsManager
from managers.automated_reports_manager import AutomatedReportsManager

def init_managers():
    """
    Инициализирует и возвращает все менеджеры
    
    Returns:
        Кортеж с инициализированными менеджерами
    """
    notification_manager = NotificationManager(db_manager)
    excel_exporter = ExportManager(db_manager)
    search_manager = SearchManager(db_manager)
    template_manager = TemplateManager(db_manager)
    dashboard_manager = DashboardManager(db_manager)
    advanced_analytics_manager = AdvancedAnalyticsManager(db_manager)
    automated_reports_manager = AutomatedReportsManager(db_manager)
    
    return (notification_manager, excel_exporter, search_manager, template_manager, 
            dashboard_manager, advanced_analytics_manager, automated_reports_manager)
