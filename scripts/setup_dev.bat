@echo off
REM ========================================================
REM ClipForge AI - Local Development Setup Script (Windows)
REM Strictly Free / Zero Budget Setup
REM ========================================================

echo [1/4] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.10+.
    exit /b 1
)

if not exist .venv (
    echo Creating virtual environment (.venv)...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo [2/4] Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/4] Installing Frontend dependencies...
cd frontend
call npm install
cd ..

if not exist .env (
    echo [4/4] Creating .env from .env.example...
    copy .env.example .env
) else (
    echo [4/4] .env already exists.
)

echo ========================================================
echo Setup complete!
echo To run backend:  call .venv\Scripts\activate && uvicorn backend.main:app --reload --port 8000
echo To run worker:   call .venv\Scripts\activate && python -m worker.runner --mode poll
echo To run frontend: cd frontend && npm run dev
echo ========================================================
