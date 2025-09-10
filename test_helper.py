#!/usr/bin/env python3
"""
Помощник для выбора и запуска тестирования бота
"""

import os
import sys
import subprocess

def print_menu():
    """Печать главного меню"""
    print("\n" + "="*60)
    print("🧪 СИСТЕМА ТЕСТИРОВАНИЯ TELEGRAM БОТА")
    print("="*60)
    print("Выберите тип тестирования:")
    print()
    print("1. 📋 Показать руководство по ручному тестированию")
    print("2. 🎯 Интерактивное пошаговое тестирование")
    print("3. 🤖 Автоматическое тестирование функций")
    print("4. 📊 Создать чеклист для тестирования")
    print("5. 🔧 Проверить статус бота")
    print("6. 📁 Показать логи бота")
    print("7. ❌ Выход")
    print("="*60)

def check_bot_status():
    """Проверка статуса бота"""
    try:
        result = subprocess.run(['./manage.sh', 'status'], 
                              capture_output=True, text=True, cwd='/Users/vadim/telegram_bot')
        print("📊 Статус бота:")
        print(result.stdout)
        if result.stderr:
            print("⚠️ Предупреждения:")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Ошибка проверки статуса: {e}")

def show_bot_logs():
    """Показ логов бота"""
    try:
        result = subprocess.run(['./manage.sh', 'logs', '-n', '30'], 
                              capture_output=True, text=True, cwd='/Users/vadim/telegram_bot')
        print("📁 Последние 30 строк логов:")
        print(result.stdout)
        if result.stderr:
            print("⚠️ Ошибки в логах:")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Ошибка получения логов: {e}")

def run_guide():
    """Запуск руководства по тестированию"""
    try:
        subprocess.run([sys.executable, 'real_bot_tester.py', '--mode', 'guide'], 
                      cwd='/Users/vadim/telegram_bot')
    except Exception as e:
        print(f"❌ Ошибка запуска руководства: {e}")

def run_interactive_testing():
    """Запуск интерактивного тестирования"""
    print("\n🎯 Запуск интерактивного пошагового тестирования...")
    print("Этот режим проведет вас через все функции бота шаг за шагом.")
    print("После каждого теста вы сможете указать, работает функция или нет.")
    
    proceed = input("\nПродолжить? (да/нет): ").strip().lower()
    if proceed in ['да', 'yes', 'y', 'д']:
        try:
            subprocess.run([sys.executable, 'interactive_manual_tester.py'], 
                          cwd='/Users/vadim/telegram_bot')
        except Exception as e:
            print(f"❌ Ошибка запуска интерактивного тестирования: {e}")
    else:
        print("❌ Тестирование отменено")

def run_automated_testing():
    """Запуск автоматического тестирования"""
    print("\n🤖 Запуск автоматического тестирования функций...")
    print("Этот режим автоматически проверит основные функции бота.")
    
    proceed = input("\nПродолжить? (да/нет): ").strip().lower()
    if proceed in ['да', 'yes', 'y', 'д']:
        try:
            subprocess.run([sys.executable, 'manual_testing_framework.py', '--mode', 'auto'], 
                          cwd='/Users/vadim/telegram_bot')
        except Exception as e:
            print(f"❌ Ошибка запуска автоматического тестирования: {e}")
    else:
        print("❌ Тестирование отменено")

def create_checklist():
    """Создание чеклиста"""
    try:
        subprocess.run([sys.executable, 'real_bot_tester.py', '--mode', 'checklist'], 
                      cwd='/Users/vadim/telegram_bot')
        print("✅ Чеклист создан в файле manual_testing_checklist.json")
    except Exception as e:
        print(f"❌ Ошибка создания чеклиста: {e}")

def main():
    """Главная функция"""
    current_dir = os.getcwd()
    target_dir = '/Users/vadim/telegram_bot'
    
    # Переходим в директорию проекта
    if current_dir != target_dir:
        try:
            os.chdir(target_dir)
            print(f"📁 Переход в директорию проекта: {target_dir}")
        except Exception as e:
            print(f"❌ Не удалось перейти в директорию {target_dir}: {e}")
            return
    
    while True:
        try:
            print_menu()
            choice = input("Выберите пункт (1-7): ").strip()
            
            if choice == '1':
                run_guide()
                
            elif choice == '2':
                run_interactive_testing()
                
            elif choice == '3':
                run_automated_testing()
                
            elif choice == '4':
                create_checklist()
                
            elif choice == '5':
                check_bot_status()
                
            elif choice == '6':
                show_bot_logs()
                
            elif choice == '7':
                print("👋 До свидания!")
                break
                
            else:
                print("❓ Неверный выбор. Пожалуйста, введите число от 1 до 7.")
            
            # Пауза перед показом меню снова
            input("\nНажмите Enter для продолжения...")
            
        except KeyboardInterrupt:
            print("\n👋 Завершение работы по Ctrl+C")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()