@echo off
REM Trade-Claw Startup Script (Windows)
REM Usage: start.bat

echo ========================================
echo  Trade-Claw Trading Bot - Starting...
echo ========================================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt -q

REM Start the application
echo.
echo Starting Trade-Claw API on http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
