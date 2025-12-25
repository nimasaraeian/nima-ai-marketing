@echo off
cd /d %~dp0

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo Starting backend on http://127.0.0.1:8000
python run_api.py






















