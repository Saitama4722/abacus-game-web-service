#!/usr/bin/env bash
# Abacus Game — скрипт запуска (Mac / Linux)

set -e
cd "$(dirname "$0")"

echo ""
echo "============================================"
echo "  Abacus Game — запуск"
echo "============================================"
echo ""

# Проверка наличия Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ОШИБКА] Python не найден."
    echo ""
    echo "Установите Python:"
    echo "  macOS:   brew install python3   или скачайте с https://www.python.org/"
    echo "  Linux:  sudo apt install python3   (или аналог для вашего дистрибутива)"
    echo ""
    read -n 1 -s -r -p "Нажмите любую клавишу для выхода..."
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "[1/4] Python найден."
$PYTHON_CMD --version
echo ""

# Создание виртуального окружения, если его нет
if [ ! -f "venv/bin/activate" ]; then
    echo "[2/4] Создание виртуального окружения..."
    if ! $PYTHON_CMD -m venv venv; then
        echo "[ОШИБКА] Не удалось создать виртуальное окружение."
        read -n 1 -s -r -p "Нажмите любую клавишу для выхода..."
        exit 1
    fi
    echo "      Готово."
else
    echo "[2/4] Виртуальное окружение уже существует."
fi
echo ""

echo "[3/4] Активация окружения и установка зависимостей..."
source venv/bin/activate
if ! pip install -r requirements.txt -q; then
    echo "[ОШИБКА] Не удалось установить зависимости. Проверьте файл requirements.txt."
    read -n 1 -s -r -p "Нажмите любую клавишу для выхода..."
    exit 1
fi
echo "      Зависимости установлены."
echo ""

echo "[4/4] Запуск приложения..."
echo ""
echo "--------------------------------------------"
echo "  Откройте в браузере адрес, указанный ниже."
echo "  Для остановки сервера нажмите Ctrl+C."
echo "--------------------------------------------"
echo ""

python run.py

echo ""
echo "Сервер остановлен."
read -n 1 -s -r -p "Нажмите любую клавишу для выхода..."
