@echo off
cd /d %~dp0\..
echo Starting AI Brain API Server...
echo.
echo Server will be available at: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.
python -m uvicorn api.app:app --host localhost --port 8000 --reload
pause





