# Start the FastAPI server
cd $PSScriptRoot\..
Write-Host "Starting AI Brain API server..."
Write-Host "Server will run on: http://127.0.0.1:8000"
Write-Host ""
Start-Process python -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -NoNewWindow





