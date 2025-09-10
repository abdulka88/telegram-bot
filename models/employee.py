"""
Модель сотрудника
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Employee:
    """Модель данных сотрудника"""
    
    id: Optional[int] = None
    chat_id: int = 0
    full_name: str = ""
    position: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @classmethod
    def from_db_row(cls, row: dict) -> 'Employee':
        """Создает объект Employee из строки базы данных"""
        return cls(
            id=row.get('id'),
            chat_id=row.get('chat_id'),
            full_name=row.get('full_name', ''),
            position=row.get('position', ''),
            is_active=bool(row.get('is_active', True)),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None
        )
    
    def to_dict(self) -> dict:
        """Преобразует в словарь для сохранения в БД"""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'full_name': self.full_name,
            'position': self.position,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __str__(self) -> str:
        return f"Employee(id={self.id}, name='{self.full_name}', position='{self.position}')"