"""
Модель уведомления
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class NotificationLevel(Enum):
    """Уровни уведомлений"""
    INFO = "info"
    WARNING = "warning" 
    URGENT = "urgent"
    CRITICAL = "critical"
    OVERDUE = "overdue"

class NotificationStatus(Enum):
    """Статусы отправки уведомлений"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Notification:
    """Модель данных уведомления"""
    
    id: Optional[int] = None
    employee_id: int = 0
    event_id: int = 0
    notification_level: NotificationLevel = NotificationLevel.INFO
    status: NotificationStatus = NotificationStatus.PENDING
    message: str = ""
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def level_emoji(self) -> str:
        """Возвращает эмодзи для уровня уведомления"""
        level_emojis = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.URGENT: "🔶",
            NotificationLevel.CRITICAL: "🔴",
            NotificationLevel.OVERDUE: "⚫"
        }
        return level_emojis.get(self.notification_level, "📢")
    
    @property
    def status_emoji(self) -> str:
        """Возвращает эмодзи для статуса уведомления"""
        status_emojis = {
            NotificationStatus.PENDING: "⏳",
            NotificationStatus.SENT: "✅",
            NotificationStatus.FAILED: "❌",
            NotificationStatus.CANCELLED: "🚫"
        }
        return status_emojis.get(self.status, "❓")
    
    @classmethod
    def from_db_row(cls, row: dict) -> 'Notification':
        """Создает объект Notification из строки базы данных"""
        return cls(
            id=row.get('id'),
            employee_id=row.get('employee_id'),
            event_id=row.get('event_id'),
            notification_level=NotificationLevel(row.get('notification_level', 'info')),
            status=NotificationStatus(row.get('status', 'pending')),
            message=row.get('message', ''),
            sent_at=datetime.fromisoformat(row['sent_at']) if row.get('sent_at') else None,
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None
        )
    
    def to_dict(self) -> dict:
        """Преобразует в словарь для сохранения в БД"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'event_id': self.event_id,
            'notification_level': self.notification_level.value,
            'status': self.status.value,
            'message': self.message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def mark_as_sent(self):
        """Отмечает уведомление как отправленное"""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now()
    
    def mark_as_failed(self):
        """Отмечает уведомление как неудачное"""
        self.status = NotificationStatus.FAILED
    
    def __str__(self) -> str:
        return f"Notification(id={self.id}, level='{self.notification_level.value}', status='{self.status.value}')"