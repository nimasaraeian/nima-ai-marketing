# Script to kill all processes on port 8000
$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "=== Checking processes on port 8000 ===" -ForegroundColor Cyan

$targets = netstat -ano | Select-String ":8000\s+.*LISTENING" | ForEach-Object { ($_ -split "\s+")[-1] } | Sort-Object -Unique

if ($targets.Count -eq 0) {
    Write-Host "OK: No processes listening on port 8000" -ForegroundColor Green
    exit 0
}

Write-Host "Found LISTENING PIDs on 8000: $($targets -join ', ')" -ForegroundColor Yellow

foreach ($pid in $targets) {
    Write-Host "  Killing PID: $pid" -ForegroundColor Yellow
    taskkill /PID $pid /F | Out-Null
}

Start-Sleep -Seconds 1

$remaining = netstat -ano | findstr ":8000"
if ($remaining) {
    Write-Host "WARNING: Some processes still on port 8000:" -ForegroundColor Red
    Write-Host $remaining
} else {
    Write-Host "OK: Port 8000 is now free" -ForegroundColor Green
}

Write-Host ""

