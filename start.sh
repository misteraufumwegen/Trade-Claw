#!/bin/bash
# Trade-Claw Startup Script (macOS / Linux)
# Usage: chmod +x start.sh && ./start.sh

echo "========================================"
echo " Trade-Claw Trading Bot - Starting..."
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Start the application
echo ""
echo "Starting Trade-Claw API on http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
