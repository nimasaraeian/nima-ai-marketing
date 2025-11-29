# Start the FastAPI server
cd $PSScriptRoot\..
Write-Host "Starting AI Brain API server..."
Write-Host "Server will run on: http://localhost:8000"
Write-Host ""
Start-Process python -ArgumentList "-m", "uvicorn", "api.app:app", "--host", "localhost", "--port", "8000", "--reload" -NoNewWindow





