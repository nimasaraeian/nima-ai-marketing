# Test script for /api/brain endpoint
Write-Host "Testing /api/brain endpoint..." -ForegroundColor Cyan
Write-Host ""

$response = curl.exe -X POST "http://localhost:8000/api/brain" `
  -F "content=This is a sample landing page copy for testing the decision psychology backend." `
  -w "`nHTTP Status: %{http_code}`n" `
  --silent --show-error

Write-Host ""
Write-Host "Response:" -ForegroundColor Green
Write-Host $response

# Try to parse as JSON and display formatted
try {
    $json = $response | ConvertFrom-Json
    Write-Host ""
    Write-Host "Parsed JSON:" -ForegroundColor Yellow
    Write-Host ($json | ConvertTo-Json -Depth 10)
} catch {
    Write-Host ""
    Write-Host "Response is not valid JSON or contains errors" -ForegroundColor Red
}

