@echo off
setlocal

cd /d "%~dp0"

title AKShare Cross Asset Monitor - Dashboard Only

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    echo.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

echo Starting Streamlit dashboard without refreshing data...
echo.

".venv\Scripts\python.exe" -m streamlit run dashboard\app.py

pause
