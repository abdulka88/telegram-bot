"""
Модуль безопасности и шифрования для Telegram бота
"""

import logging
from config.settings import encryption_manager

logger = logging.getLogger(__name__)

def encrypt_data(data: str) -> str:
    """
    Шифрует строку с использованием Fernet
    
    Args:
        data: Строка для шифрования
        
    Returns:
        Зашифрованная строка
    """
    try:
        return encryption_manager.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError("Encryption error")

def decrypt_data(encrypted_data: str) -> str:
    """
    Дешифрует строку с использованием Fernet
    
    Args:
        encrypted_data: Зашифрованная строка
        
    Returns:
        Расшифрованная строка
    """
    try:
        return encryption_manager.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Decryption error")

def is_admin(chat_id: int, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        
    Returns:
        True если пользователь администратор
    """
    from core.database import db_manager
    
    logger.info(f"🔒 is_admin: проверяем chat_id={chat_id}, user_id={user_id}")
    
    try:
        admin_data = db_manager.execute_with_retry(
            "SELECT admin_id FROM chat_settings WHERE chat_id = ?",
            (chat_id,),
            fetch="one"
        )
        logger.info(f"📄 Данные из chat_settings: {admin_data}")
        
        result = admin_data and admin_data['admin_id'] == user_id
        logger.info(f"✅ Результат проверки админа: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False