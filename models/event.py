"""
Модель события сотрудника
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from enum import Enum

class EventStatus(Enum):
    """Статусы событий"""
    UPCOMING = "upcoming"
    OVERDUE = "overdue"
    CRITICAL = "critical"
    URGENT = "urgent"
    ATTENTION = "attention"

@dataclass
class EmployeeEvent:
    """Модель данных события сотрудника"""
    
    id: Optional[int] = None
    employee_id: int = 0
    event_type: str = ""
    last_event_date: Optional[date] = None
    next_notification_date: Optional[date] = None
    interval_days: int = 365
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def status(self) -> EventStatus:
        """Определяет статус события на основе даты"""
        if not self.next_notification_date:
            return EventStatus.UPCOMING
            
        today = date.today()
        days_until = (self.next_notification_date - today).days
        
        if days_until < 0:
            return EventStatus.OVERDUE
        elif days_until <= 3:
            return EventStatus.CRITICAL
        elif days_until <= 7:
            return EventStatus.URGENT
        elif days_until <= 30:
            return EventStatus.ATTENTION
        else:
            return EventStatus.UPCOMING
    
    @property
    def days_until_event(self) -> int:
        """Количество дней до события"""
        if not self.next_notification_date:
            return 0
        return (self.next_notification_date - date.today()).days
    
    @classmethod
    def from_db_row(cls, row: dict) -> 'EmployeeEvent':
        """Создает объект EmployeeEvent из строки базы данных"""
        return cls(
            id=row.get('id'),
            employee_id=row.get('employee_id'),
            event_type=row.get('event_type', ''),
            last_event_date=date.fromisoformat(row['last_event_date']) if row.get('last_event_date') else None,
            next_notification_date=date.fromisoformat(row['next_notification_date']) if row.get('next_notification_date') else None,
            interval_days=row.get('interval_days', 365),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None
        )
    
    def to_dict(self) -> dict:
        """Преобразует в словарь для сохранения в БД"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'event_type': self.event_type,
            'last_event_date': self.last_event_date.isoformat() if self.last_event_date else None,
            'next_notification_date': self.next_notification_date.isoformat() if self.next_notification_date else None,
            'interval_days': self.interval_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __str__(self) -> str:
        return f"EmployeeEvent(id={self.id}, type='{self.event_type}', status='{self.status.value}')"