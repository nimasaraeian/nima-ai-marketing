@echo off
cd /d %~dp0\..
echo Starting AI Brain API Server...
echo.
echo Server will be available at: http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo.
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
pause





