#!/usr/bin/env python3
"""
Скрипт настройки и запуска Telegram бота для управления периодическими событиями
"""

import os
import sys
from dotenv import load_dotenv

def setup_bot():
    """Настройка бота перед первым запуском"""
    print("🤖 Настройка Telegram бота для управления периодическими событиями")
    print("=" * 60)
    
    # Загружаем существующие переменные окружения
    load_dotenv()
    
    # Проверяем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_bot_token_here':
        print("\n❗ ВНИМАНИЕ: Не настроен токен Telegram бота!")
        print("\n📝 Для получения токена:")
        print("1. Напишите @BotFather в Telegram")
        print("2. Отправьте команду /newbot")
        print("3. Следуйте инструкциям для создания бота")
        print("4. Скопируйте полученный токен")
        
        token = input("\n🔑 Введите токен бота (или 'skip' для пропуска): ")
        if token and token.lower() != 'skip':
            # Обновляем .env файл
            update_env_file('BOT_TOKEN', token)
            bot_token = token
    
    # Проверяем Admin ID
    admin_id = os.getenv('ADMIN_ID')
    if not admin_id or admin_id == 'your_telegram_user_id_here':
        print("\n👤 ADMIN_ID не настроен!")
        print("\n📝 Для получения вашего Telegram ID:")
        print("1. Напишите @userinfobot в Telegram")
        print("2. Отправьте любое сообщение")
        print("3. Скопируйте ваш ID")
        
        user_id = input("\n🆔 Введите ваш Telegram ID (или 'skip' для пропуска): ")
        if user_id and user_id.lower() != 'skip':
            update_env_file('ADMIN_ID', user_id)
            admin_id = user_id
    
    print("\n📊 Текущие настройки:")
    print(f"BOT_TOKEN: {'✅ Настроен' if bot_token and bot_token != 'your_bot_token_here' else '❌ Не настроен'}")
    print(f"ADMIN_ID: {'✅ Настроен' if admin_id and admin_id != 'your_telegram_user_id_here' else '❌ Не настроен'}")
    print(f"SECRET_KEY: {'✅ Автогенерирован' if os.getenv('SECRET_KEY') else '❌ Не настроен'}")
    
    if bot_token and bot_token != 'your_bot_token_here':
        print("\n🚀 Готов к запуску!")
        choice = input("\n▶️  Запустить бота сейчас? (y/n): ")
        if choice.lower() in ['y', 'yes', 'д', 'да']:
            return True
    else:
        print("\n⚠️  Бот не может быть запущен без токена!")
        print("Отредактируйте файл .env и добавьте корректный BOT_TOKEN")
    
    return False

def update_env_file(key, value):
    """Обновляет значение в .env файле"""
    env_path = '.env'
    
    # Читаем существующий файл
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    
    # Ищем существующую строку с ключом
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f'{key}='):
            lines[i] = f'{key}={value}\n'
            key_found = True
            break
    
    # Если ключ не найден, добавляем новую строку
    if not key_found:
        lines.append(f'{key}={value}\n')
    
    # Записываем обратно
    with open(env_path, 'w') as f:
        f.writelines(lines)

def check_dependencies():
    """Проверяет наличие всех необходимых зависимостей"""
    required_packages = [
        'telegram',
        'cryptography', 
        'dotenv',
        'pytz',
        'xlsxwriter',
        'openpyxl'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Отсутствуют пакеты: {', '.join(missing_packages)}")
        print("📦 Установите их командой: pip install -r requirements.txt")
        return False
    
    print("✅ Все зависимости установлены")
    return True

def run_bot():
    """Запускает бота"""
    try:
        print("\n🚀 Запуск бота...")
        print("Для остановки нажмите Ctrl+C")
        print("-" * 40)
        
        # Импортируем и запускаем главную функцию
        import main
        main.main()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске: {e}")
        return False
    
    return True

def main():
    """Главная функция скрипта настройки"""
    print("🔧 Проверка зависимостей...")
    if not check_dependencies():
        sys.exit(1)
    
    # Настройка бота
    should_run = setup_bot()
    
    if should_run:
        run_bot()
    else:
        print("\n📝 Для запуска бота после настройки используйте:")
        print("python main.py")

if __name__ == '__main__':
    main()