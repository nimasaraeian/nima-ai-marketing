# Script to start both frontend and backend locally

Write-Host "`n=== Starting NIMA AI Marketing System ===" -ForegroundColor Cyan
Write-Host ""

# Check if backend is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Backend is already running on http://localhost:8000" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Starting backend server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'n:\nima-ai-marketing'; uvicorn api.main:app --reload --host 0.0.0.0 --port 8000" -WindowStyle Minimized
    Write-Host "[OK] Backend server started in background" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

# Start frontend
Write-Host "[INFO] Starting frontend server..." -ForegroundColor Yellow
Set-Location "n:\nima-ai-marketing\web"
Start-Process python -ArgumentList "-m", "http.server", "8080" -WindowStyle Minimized
Write-Host "[OK] Frontend server started on http://localhost:8080" -ForegroundColor Green

Write-Host ""
Write-Host "=== System Ready ===" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:8080" -ForegroundColor White
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to open frontend in browser..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "http://localhost:8080"

