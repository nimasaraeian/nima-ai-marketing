# Start the AI Brain API (single backend only)
Set-Location $PSScriptRoot

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

Write-Host "Starting backend on http://127.0.0.1:8000"
python run_api.py















