#!/bin/bash

# Управление Telegram ботом для управления периодическими событиями сотрудников
# Версия: 1.0
# Дата: $(date +%Y-%m-%d)

PROJECT_DIR="/Users/vadim/telegram_bot"
PYTHON_CMD="python3"
BOT_SCRIPT="main.py"
PID_FILE="bot.pid"
LOG_FILE="bot.log"
VENV_DIR="venv"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Переход в директорию проекта
cd "$PROJECT_DIR" || {
    log_error "Не удалось перейти в директорию проекта: $PROJECT_DIR"
    exit 1
}

# Активация виртуального окружения
activate_venv() {
    if [ -d "$VENV_DIR" ]; then
        log_info "Активация виртуального окружения..."
        source "$VENV_DIR/bin/activate"
        log_success "Виртуальное окружение активировано"
    else
        log_warning "Виртуальное окружение не найдено в $VENV_DIR"
    fi
}

# Функция запуска бота
start_bot() {
    log_info "Запуск Telegram бота..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_warning "Бот уже запущен с PID: $PID"
            return 1
        else
            log_info "Удаление устаревшего PID файла"
            rm -f "$PID_FILE"
        fi
    fi
    
    activate_venv
    
    # Запуск бота в фоновом режиме
    nohup $PYTHON_CMD $BOT_SCRIPT > $LOG_FILE 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > $PID_FILE
    
    # Проверка успешного запуска
    sleep 2
    if ps -p $BOT_PID > /dev/null; then
        log_success "Бот успешно запущен с PID: $BOT_PID"
        log_info "Логи: tail -f $LOG_FILE"
        return 0
    else
        log_error "Ошибка запуска бота. Проверьте логи: $LOG_FILE"
        rm -f $PID_FILE
        return 1
    fi
}

# Функция остановки бота
stop_bot() {
    log_info "Остановка Telegram бота..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_info "Отправка сигнала TERM процессу $PID"
            kill "$PID"
            
            # Ждем завершения процесса
            for i in {1..10}; do
                if ! ps -p "$PID" > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done
            
            # Принудительное завершение если нужно
            if ps -p "$PID" > /dev/null 2>&1; then
                log_warning "Принудительное завершение процесса $PID"
                kill -9 "$PID"
                sleep 1
            fi
            
            if ! ps -p "$PID" > /dev/null 2>&1; then
                log_success "Бот остановлен"
                rm -f "$PID_FILE"
                return 0
            else
                log_error "Не удалось остановить бот"
                return 1
            fi
        else
            log_warning "Процесс с PID $PID не найден"
            rm -f "$PID_FILE"
            return 0
        fi
    else
        log_warning "PID файл не найден. Возможно, бот не запущен"
        
        # Проверяем запущенные процессы
        RUNNING_PIDS=$(pgrep -f "$PYTHON_CMD $BOT_SCRIPT")
        if [ -n "$RUNNING_PIDS" ]; then
            log_warning "Найдены запущенные процессы бота: $RUNNING_PIDS"
            echo "$RUNNING_PIDS" | xargs kill
            log_success "Процессы остановлены"
        fi
        return 0
    fi
}

# Функция перезапуска бота
restart_bot() {
    log_info "Перезапуск Telegram бота..."
    stop_bot
    sleep 2
    start_bot
}

# Функция проверки статуса
check_status() {
    log_info "Проверка статуса Telegram бота..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            # Получение информации о процессе
            MEMORY=$(ps -o rss= -p "$PID" | awk '{print $1}')
            CPU=$(ps -o pcpu= -p "$PID" | awk '{print $1}')
            UPTIME=$(ps -o etime= -p "$PID" | awk '{print $1}')
            
            log_success "Бот работает с PID: $PID"
            echo "  Время работы: $UPTIME"
            echo "  Использование CPU: ${CPU}%"
            echo "  Использование памяти: ${MEMORY}KB"
            
            # Проверка размера лог файла
            if [ -f "$LOG_FILE" ]; then
                LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
                echo "  Размер лог файла: $LOG_SIZE"
            fi
            return 0
        else
            log_warning "PID файл существует, но процесс не найден"
            rm -f "$PID_FILE"
        fi
    fi
    
    # Поиск процессов бота
    RUNNING_PIDS=$(pgrep -f "$PYTHON_CMD $BOT_SCRIPT")
    if [ -n "$RUNNING_PIDS" ]; then
        log_warning "Найдены запущенные процессы бота без PID файла:"
        echo "$RUNNING_PIDS" | while read -r pid; do
            UPTIME=$(ps -o etime= -p "$pid" | awk '{print $1}')
            echo "  PID: $pid, Время работы: $UPTIME"
        done
        return 2
    else
        log_error "Бот не запущен"
        return 1
    fi
}

# Функция просмотра логов
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        case "$2" in
            "-f"|"--follow")
                log_info "Просмотр логов в реальном времени (Ctrl+C для выхода):"
                tail -f "$LOG_FILE"
                ;;
            "-n"|"--lines")
                LINES=${3:-20}
                log_info "Последние $LINES строк логов:"
                tail -n "$LINES" "$LOG_FILE"
                ;;
            *)
                log_info "Последние 50 строк логов:"
                tail -n 50 "$LOG_FILE"
                ;;
        esac
    else
        log_error "Лог файл не найден: $LOG_FILE"
        return 1
    fi
}

# Функция установки зависимостей
install_deps() {
    log_info "Установка зависимостей..."
    
    activate_venv
    
    if [ -f "requirements.txt" ]; then
        pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
        log_success "Зависимости установлены"
    else
        log_error "Файл requirements.txt не найден"
        return 1
    fi
}

# Функция тестирования
test_bot() {
    log_info "Запуск тестов..."
    
    activate_venv
    
    # Проверка синтаксиса
    $PYTHON_CMD -m py_compile $BOT_SCRIPT
    if [ $? -eq 0 ]; then
        log_success "Синтаксис основного файла корректен"
    else
        log_error "Ошибка синтаксиса в $BOT_SCRIPT"
        return 1
    fi
    
    # Запуск тестов если есть
    if [ -d "tests" ]; then
        $PYTHON_CMD -m pytest tests/ -v
    else
        log_info "Тесты не найдены"
    fi
}

# Функция очистки
cleanup() {
    log_info "Очистка временных файлов..."
    
    # Удаление .pyc файлов
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # Удаление старых логов (старше 30 дней)
    find . -name "*.log.*" -mtime +30 -delete 2>/dev/null || true
    
    # Удаление временных файлов базы данных
    rm -f *.db-journal
    rm -f bot.lock
    
    log_success "Временные файлы очищены"
}

# Функция отображения статистики проекта
show_status() {
    log_info "Статус проекта:"
    echo ""
    
    # Информация о файлах
    echo "📁 Структура проекта:"
    echo "  Python файлы: $(find . -name "*.py" | wc -l)"
    echo "  Всего строк кода: $(find . -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')"
    echo "  Конфигурационные файлы: $(find . -name "*.txt" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" | wc -l)"
    
    echo ""
    echo "🗄️ База данных:"
    if [ -f "employees.db" ]; then
        DB_SIZE=$(du -h "employees.db" | cut -f1)
        echo "  Размер БД: $DB_SIZE"
        
        # Подсчет записей (если sqlite3 установлен)
        if command -v sqlite3 >/dev/null 2>&1; then
            EMPLOYEES=$(sqlite3 employees.db "SELECT COUNT(*) FROM employees WHERE is_active = 1;" 2>/dev/null || echo "N/A")
            EVENTS=$(sqlite3 employees.db "SELECT COUNT(*) FROM employee_events;" 2>/dev/null || echo "N/A")
            echo "  Активные сотрудники: $EMPLOYEES"
            echo "  Всего событий: $EVENTS"
        fi
    else
        echo "  База данных не найдена"
    fi
    
    echo ""
    check_status
}

# Функция отображения справки
show_help() {
    cat << EOF
🤖 Управление Telegram ботом для периодических событий сотрудников

ИСПОЛЬЗОВАНИЕ:
    ./manage.sh <команда> [опции]

КОМАНДЫ:
    start               Запуск бота в фоновом режиме
    stop                Остановка бота
    restart             Перезапуск бота (stop + start)
    status              Проверка статуса работы бота
    logs [опции]        Просмотр логов
    install             Установка зависимостей
    test               Запуск тестов и проверки синтаксиса
    cleanup            Очистка временных файлов
    info               Отображение информации о проекте
    help               Показать эту справку

ОПЦИИ ДЛЯ LOGS:
    -f, --follow        Просмотр логов в реальном времени
    -n, --lines N       Показать последние N строк (по умолчанию: 20)

ПРИМЕРЫ:
    ./manage.sh start                 # Запуск бота
    ./manage.sh logs -f               # Просмотр логов в реальном времени
    ./manage.sh logs -n 100           # Показать последние 100 строк логов
    ./manage.sh restart               # Перезапуск бота
    ./manage.sh cleanup               # Очистка временных файлов

ФАЙЛЫ:
    $BOT_SCRIPT          Основной файл бота
    $PID_FILE            Файл с PID процесса
    $LOG_FILE            Файл логов
    requirements.txt     Зависимости Python

УПРАВЛЕНИЕ:
    Для остановки бота: Ctrl+C (если запущен в терминале) или ./manage.sh stop
    Логи в реальном времени: ./manage.sh logs -f
    Проверка статуса: ./manage.sh status

EOF
}

# Основная логика скрипта
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs "$@"
        ;;
    install)
        install_deps
        ;;
    test)
        test_bot
        ;;
    cleanup)
        cleanup
        ;;
    info)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Неизвестная команда: $1"
        echo ""
        echo "Используйте './manage.sh help' для получения справки"
        echo ""
        echo "Доступные команды: start, stop, restart, status, logs, install, test, cleanup, info, help"
        exit 1
        ;;
esac