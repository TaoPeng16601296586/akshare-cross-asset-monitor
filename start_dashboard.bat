@echo off
setlocal

cd /d "%~dp0"

title AKShare Cross Asset Monitor

echo ==========================================
echo AKShare Cross Asset Monitor
echo ==========================================
echo.
echo Project path:
echo %CD%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    echo.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

echo Updating latest data...
echo.

".venv\Scripts\python.exe" -u src\run_all.py

echo.
echo Data update finished.
echo Starting Streamlit...
echo.

".venv\Scripts\python.exe" -m streamlit run dashboard\app.py

pause
