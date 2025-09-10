"""
Менеджер шаблонов событий для Telegram бота управления периодическими событиями
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
from config.constants import AVAILABLE_POSITIONS, POSITION_TEMPLATE_MAPPING

logger = logging.getLogger(__name__)

class EventTemplate:
    """Класс шаблона событий"""
    
    def __init__(self, name: str, events: List[Dict]):
        self.name = name
        self.events = events  # [{'type': 'Медосмотр', 'interval_days': 365}, ...]

class TemplateManager:
    """Менеджер шаблонов событий для различных должностей"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.predefined_templates = self._load_predefined_templates()
    
    def _load_predefined_templates(self) -> Dict[str, EventTemplate]:
        """
        Загружает предустановленные шаблоны для всех должностей
        
        Returns:
            Словарь с шаблонами событий
        """
        templates = {
            'carpenter': EventTemplate(
                name="Плотник",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Обучение работам на высоте (2 группа)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний работ на высоте (2 группа)', 'interval_days': 365},
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            ),
            'painter': EventTemplate(
                name="Маляр",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Обучение работам на высоте (2 группа)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний работ на высоте (2 группа)', 'interval_days': 365},
                    {'type': 'Инструктаж электробезопасности (1 группа)', 'interval_days': 365}
                ]
            ),
            'maintenance_worker': EventTemplate(
                name="Рабочий по комплексному обслуживанию и ремонту зданий",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Обучение работам на высоте (2 группа)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний работ на высоте (2 группа)', 'interval_days': 365},
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            ),
            'janitor': EventTemplate(
                name="Дворник",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 730},  # 2 года
                    {'type': 'Проверка знаний ОТ (П-2, П-3)', 'interval_days': 1095},  # 3 года
                    {'type': 'Инструктаж электробезопасности (1 группа)', 'interval_days': 365}
                ]
            ),
            'cleaner': EventTemplate(
                name="Уборщик производственных помещений",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 365},
                    {'type': 'Проверка знаний ОТ (П-2, П-3)', 'interval_days': 1095},  # 3 года
                    {'type': 'Инструктаж электробезопасности (1 группа)', 'interval_days': 365}
                ]
            ),
            'senior_master': EventTemplate(
                name="Старший мастер",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 730},  # 2 года
                    {'type': 'Проверка знаний ОТ (П-1, П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний ОТ (П-5.10, П-5.11)', 'interval_days': 365},
                    {'type': 'Обучение работам на высоте (3 группа)', 'interval_days': 1825},  # 5 лет
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            ),
            'master': EventTemplate(
                name="Мастер",
                events=[
                    {'type': 'Медицинский осмотр', 'interval_days': 730},  # 2 года
                    {'type': 'Проверка знаний ОТ (П-1, П-2, П-3, П-4)', 'interval_days': 1095},  # 3 года
                    {'type': 'Проверка знаний ОТ (П-5.10, П-5.11)', 'interval_days': 365},
                    {'type': 'Обучение работам на высоте (3 группа)', 'interval_days': 1825},  # 5 лет
                    {'type': 'Проверка знаний электробезопасности (2 группа)', 'interval_days': 365}
                ]
            )
        }
        return templates
    
    def get_template_list(self) -> List[Dict]:
        """
        Возвращает список доступных шаблонов
        
        Returns:
            Список словарей с информацией о шаблонах
        """
        templates = []
        for key, template in self.predefined_templates.items():
            templates.append({
                'key': key,
                'name': template.name,
                'events_count': len(template.events),
                'description': ', '.join([f"{e['type']} ({e['interval_days']}д)" for e in template.events[:3]])
            })
        return templates
    
    def get_template_by_position(self, position: str) -> str:
        """
        Получает ключ шаблона по должности
        
        Args:
            position: Название должности
            
        Returns:
            Ключ шаблона или None если не найден
        """
        return POSITION_TEMPLATE_MAPPING.get(position)
    
    def get_template_info(self, template_key: str) -> Dict:
        """
        Получает подробную информацию о шаблоне
        
        Args:
            template_key: Ключ шаблона
            
        Returns:
            Информация о шаблоне
        """
        if template_key not in self.predefined_templates:
            return None
            
        template = self.predefined_templates[template_key]
        return {
            'key': template_key,
            'name': template.name,
            'events_count': len(template.events),
            'events': template.events
        }
    
    async def apply_template(self, employee_id: int, template_key: str, base_date: datetime = None) -> bool:
        """
        Применяет шаблон к сотруднику
        
        Args:
            employee_id: ID сотрудника
            template_key: Ключ шаблона
            base_date: Базовая дата для расчета событий
            
        Returns:
            True если шаблон успешно применен
        """
        if template_key not in self.predefined_templates:
            logger.error(f"Template {template_key} not found")
            return False
        
        template = self.predefined_templates[template_key]
        base_date = base_date or datetime.now().date()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                added_events = 0
                
                for event in template.events:
                    # Проверяем, нет ли уже такого события
                    cursor.execute(
                        "SELECT id FROM employee_events WHERE employee_id = ? AND event_type = ?",
                        (employee_id, event['type'])
                    )
                    
                    if not cursor.fetchone():  # Добавляем только если события нет
                        next_date = base_date + timedelta(days=event['interval_days'])
                        
                        cursor.execute('''
                            INSERT INTO employee_events 
                            (employee_id, event_type, last_event_date, interval_days, next_notification_date)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            employee_id,
                            event['type'],
                            base_date.isoformat(),
                            event['interval_days'],
                            next_date.isoformat()
                        ))
                        added_events += 1
                
                conn.commit()
                logger.info(f"Applied template {template_key} to employee {employee_id}, added {added_events} events")
                return True
                
        except Exception as e:
            logger.error(f"Error applying template {template_key} to employee {employee_id}: {e}")
            return False
    
    async def apply_template_by_position(self, employee_id: int, position: str, base_date: datetime = None) -> bool:
        """
        Применяет шаблон по должности сотрудника
        
        Args:
            employee_id: ID сотрудника
            position: Должность сотрудника
            base_date: Базовая дата для расчета событий
            
        Returns:
            True если шаблон успешно применен
        """
        template_key = self.get_template_by_position(position)
        
        if not template_key:
            logger.warning(f"No template found for position: {position}")
            return False
        
        return await self.apply_template(employee_id, template_key, base_date)
    
    def get_available_positions(self) -> List[str]:
        """
        Возвращает список доступных должностей
        
        Returns:
            Список должностей
        """
        return AVAILABLE_POSITIONS.copy()
    
    async def create_custom_template(self, chat_id: int, template_name: str, events: List[Dict], created_by: int) -> bool:
        """
        Создает пользовательский шаблон
        
        Args:
            chat_id: ID чата
            template_name: Название шаблона
            events: Список событий шаблона
            created_by: ID создавшего пользователя
            
        Returns:
            True если шаблон успешно создан
        """
        try:
            import json
            template_data = json.dumps({
                'name': template_name,
                'events': events
            })
            
            self.db.execute_with_retry('''
                INSERT INTO custom_templates (chat_id, template_name, template_data, created_by)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, template_name, template_data, created_by))
            
            logger.info(f"Created custom template '{template_name}' for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom template: {e}")
            return False
    
    def get_custom_templates(self, chat_id: int) -> List[Dict]:
        """
        Получает пользовательские шаблоны чата
        
        Args:
            chat_id: ID чата
            
        Returns:
            Список пользовательских шаблонов
        """
        try:
            import json
            results = self.db.execute_with_retry('''
                SELECT id, template_name, template_data, created_by, created_at
                FROM custom_templates
                WHERE chat_id = ?
                ORDER BY template_name
            ''', (chat_id,), fetch="all")
            
            templates = []
            for result in results:
                template_data = json.loads(result['template_data'])
                templates.append({
                    'id': result['id'],
                    'name': template_data['name'],
                    'events': template_data['events'],
                    'created_by': result['created_by'],
                    'created_at': result['created_at']
                })
            
            return templates
            
        except Exception as e:
            logger.error(f"Error getting custom templates: {e}")
            return []