@echo off
echo [INFO] Creating Python Virtual Environment (venv)...
python -m venv venv

echo [INFO] Activating venv...
call venv\Scripts\activate

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

echo [INFO] Installing dependencies...
pip install -r server\requirements.txt

echo [INFO] Setup Complete! To start server:
echo     1. venv\Scripts\activate
echo     2. cd server
echo     3. python app.py
pause
