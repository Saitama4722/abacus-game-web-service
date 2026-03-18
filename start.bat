@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo.
echo ============================================
echo   Abacus Game — запуск
echo ============================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден.
    echo.
    echo Установите Python с https://www.python.org/
    echo При установке включите опцию "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/4] Python найден.
python --version
echo.

REM Создание виртуального окружения, если его нет
if not exist "venv\Scripts\activate.bat" (
    echo [2/4] Создание виртуального окружения...
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение.
        pause
        exit /b 1
    )
    echo       Готово.
) else (
    echo [2/4] Виртуальное окружение уже существует.
)
echo.

echo [3/4] Активация окружения и установка зависимостей...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости. Проверьте файл requirements.txt.
    pause
    exit /b 1
)
echo       Зависимости установлены.
echo.

echo [4/4] Запуск приложения...
echo.
echo --------------------------------------------
echo   Откройте в браузере адрес, указанный ниже.
echo   Для остановки сервера нажмите Ctrl+C.
echo --------------------------------------------
echo.

python run.py

echo.
echo Сервер остановлен.
pause
