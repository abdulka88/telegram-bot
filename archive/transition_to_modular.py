#!/usr/bin/env python3
"""
Скрипт для перехода к модульной архитектуре Telegram бота
"""

import os
import shutil
import sys
from datetime import datetime

def backup_current_structure():
    """Создает резервную копию текущей структуры"""
    backup_dir = f"backup_monolithic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"📦 Создание резервной копии в {backup_dir}...")
    
    # Создаем папку для бэкапа
    os.makedirs(backup_dir, exist_ok=True)
    
    # Копируем основные файлы
    files_to_backup = [
        'main.py',
        'phase1_improvements.py',
        'periodic_events.db',
        '.env',
        'requirements.txt',
        'bot.log'
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, backup_dir)
            print(f"  ✅ {file}")
    
    print(f"✅ Резервная копия создана в {backup_dir}")
    return backup_dir

def activate_modular_architecture():
    """Активирует модульную архитектуру"""
    print("🔄 Переключение на модульную архитектуру...")
    
    # Переименовываем файлы
    if os.path.exists('main.py'):
        shutil.move('main.py', 'main_old.py')
        print("  📝 main.py → main_old.py")
    
    if os.path.exists('main_new.py'):
        shutil.move('main_new.py', 'main.py')
        print("  📝 main_new.py → main.py")
    
    print("✅ Модульная архитектура активирована!")

def rollback_to_monolithic():
    """Возвращает к монолитной архитектуре"""
    print("🔄 Возврат к монолитной архитектуре...")
    
    if os.path.exists('main_old.py'):
        if os.path.exists('main.py'):
            shutil.move('main.py', 'main_new.py')
            print("  📝 main.py → main_new.py")
        
        shutil.move('main_old.py', 'main.py')
        print("  📝 main_old.py → main.py")
        
        print("✅ Возврат к монолитной архитектуре выполнен!")
    else:
        print("❌ Файл main_old.py не найден")

def show_current_status():
    """Показывает текущий статус архитектуры"""
    print("\n📊 ТЕКУЩИЙ СТАТУС АРХИТЕКТУРЫ:")
    print("=" * 50)
    
    # Проверяем какая версия активна
    if os.path.exists('main.py') and os.path.exists('config/') and os.path.exists('handlers/'):
        # Проверяем содержимое main.py
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'from config.settings import' in content:
                print("🟢 АКТИВНА: Модульная архитектура")
                print("   📁 Структура:")
                print("     ├── config/     - настройки и константы")
                print("     ├── core/       - основная логика")
                print("     ├── handlers/   - обработчики команд")
                print("     ├── managers/   - менеджеры функций")
                print("     └── models/     - модели данных")
            else:
                print("🟡 АКТИВНА: Монолитная архитектура")
                print("   📄 Все в одном файле: main.py")
    else:
        print("🟡 АКТИВНА: Монолитная архитектура")
        print("   📄 Все в одном файле: main.py")
    
    # Показываем доступные файлы
    print("\n📋 Доступные файлы:")
    files_status = {
        'main.py': '🟢 Активный главный файл',
        'main_old.py': '🔵 Резервная монолитная версия',
        'main_new.py': '🔵 Резервная модульная версия',
        'phase1_improvements.py': '🟡 Старые улучшения (можно удалить)',
        'config/': '🟢 Модульная конфигурация',
        'handlers/': '🟢 Модульные обработчики',
        'managers/': '🟢 Модульные менеджеры'
    }
    
    for file, description in files_status.items():
        if os.path.exists(file):
            print(f"   {description}: {file}")

def main():
    """Основная функция"""
    print("🤖 ПЕРЕХОД К МОДУЛЬНОЙ АРХИТЕКТУРЕ TELEGRAM БОТА")
    print("=" * 60)
    
    # Показываем текущий статус
    show_current_status()
    
    print("\nВыберите действие:")
    print("1. 🚀 Активировать модульную архитектуру (рекомендуется)")
    print("2. 🔙 Вернуться к монолитной архитектуре")
    print("3. 📦 Только создать резервную копию")
    print("4. 📊 Показать статус")
    print("5. ❌ Выход")
    
    while True:
        try:
            choice = input("\n👉 Введите номер (1-5): ").strip()
            
            if choice == "1":
                backup_dir = backup_current_structure()
                activate_modular_architecture()
                print(f"\n🎉 Переход завершен!")
                print(f"📦 Резервная копия: {backup_dir}")
                print("🚀 Теперь запускайте бота командой: python main.py")
                break
                
            elif choice == "2":
                backup_current_structure()
                rollback_to_monolithic()
                print("\n🔄 Возврат выполнен!")
                break
                
            elif choice == "3":
                backup_dir = backup_current_structure()
                print(f"📦 Резервная копия создана: {backup_dir}")
                break
                
            elif choice == "4":
                show_current_status()
                continue
                
            elif choice == "5":
                print("👋 До свидания!")
                break
                
            else:
                print("❌ Неверный выбор. Введите число от 1 до 5.")
                
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            break

if __name__ == "__main__":
    main()