#!/usr/bin/env bash
# ========================================================
# ClipForge AI - Local Development Setup Script (Linux/macOS)
# Strictly Free / Zero Budget Setup
# ========================================================
set -e

echo "[1/4] Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "[2/4] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/4] Installing Frontend dependencies..."
cd frontend
npm install
cd ..

if [ ! -f ".env" ]; then
    echo "[4/4] Creating .env from .env.example..."
    cp .env.example .env
else
    echo "[4/4] .env already exists."
fi

echo "========================================================"
echo "Setup complete!"
echo "To run backend:  source .venv/bin/activate && uvicorn backend.main:app --reload --port 8000"
echo "To run worker:   source .venv/bin/activate && python -m worker.runner --mode poll"
echo "To run frontend: cd frontend && npm run dev"
echo "========================================================"
