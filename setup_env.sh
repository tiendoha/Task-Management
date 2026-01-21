#!/bin/bash

echo "[INFO] Creating Python Virtual Environment (venv)..."
python3 -m venv venv

echo "[INFO] Activating venv..."
source venv/bin/activate

echo "[INFO] Upgrading pip..."
pip install --upgrade pip

echo "[INFO] Installing dependencies..."
pip install -r server/requirements.txt

echo "[INFO] Setup Complete! To start server:"
echo "    1. source venv/bin/activate"
echo "    2. cd server"
echo "    3. python app.py"
