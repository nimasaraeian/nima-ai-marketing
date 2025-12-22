# Test Railway Deployment Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing Railway Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$railwayUrl = "https://nima-ai-marketing-production-82df.up.railway.app"

# Test 1: Health Endpoint
Write-Host "[1/3] Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "$railwayUrl/health" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    Write-Host "✅ Health Check: SUCCESS" -ForegroundColor Green
    Write-Host "   Status: $($healthResponse.StatusCode)" -ForegroundColor White
    Write-Host "   Response: $($healthResponse.Content)" -ForegroundColor White
} catch {
    Write-Host "❌ Health Check: FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 2: Root Endpoint
Write-Host "[2/3] Testing Root Endpoint..." -ForegroundColor Yellow
try {
    $rootResponse = Invoke-WebRequest -Uri "$railwayUrl/" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    Write-Host "✅ Root Endpoint: SUCCESS" -ForegroundColor Green
    Write-Host "   Status: $($rootResponse.StatusCode)" -ForegroundColor White
    $content = $rootResponse.Content | ConvertFrom-Json
    Write-Host "   Service: $($content.service)" -ForegroundColor White
    Write-Host "   System Prompt Loaded: $($content.system_prompt_loaded)" -ForegroundColor White
} catch {
    Write-Host "❌ Root Endpoint: FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Network Connectivity
Write-Host "[3/3] Testing Network Connectivity..." -ForegroundColor Yellow
try {
    $dnsResult = Resolve-DnsName -Name "nima-ai-marketing-production-82df.up.railway.app" -ErrorAction Stop
    Write-Host "✅ DNS Resolution: SUCCESS" -ForegroundColor Green
    Write-Host "   IP Address: $($dnsResult[0].IPAddress)" -ForegroundColor White
} catch {
    Write-Host "❌ DNS Resolution: FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

