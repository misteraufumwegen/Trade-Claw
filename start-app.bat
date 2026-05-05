@echo off
REM Trade-Claw launcher (Windows)
REM Doppelklick zum Starten — installiert venv beim ersten Start automatisch.

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [start-app] Python wurde nicht gefunden.
    echo            Bitte installiere Python 3.11+ von https://www.python.org/downloads/
    echo            und stelle sicher, dass "Add Python to PATH" angehakt ist.
    pause
    exit /b 1
)

python launcher.py
if errorlevel 1 (
    echo.
    echo [start-app] Trade-Claw wurde mit Fehler beendet ^(Code %errorlevel%^).
    pause
)
endlocal
