@echo off
echo [INFO] Setting up development environment...

if not exist "venv" (
    echo [INFO] Creating venv...
    python -m venv venv
)

echo [INFO] Activating venv...
call venv\Scripts\activate

if exist "requirements.txt" (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
)

echo [SUCCESS] Environment ready!
cmd /k
