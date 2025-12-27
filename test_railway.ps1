# Test Railway Deployment
# Usage: .\test_railway.ps1

$railwayUrl = "https://nima-ai-marketing-production-82df.up.railway.app"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Railway Deployment Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URL: $railwayUrl" -ForegroundColor Gray
Write-Host ""

# Test 1: Health Endpoint
Write-Host "[1/3] Testing /health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$railwayUrl/health" -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor White
    Write-Host "   Response: $($response.Content)" -ForegroundColor White
    $healthOk = $true
} catch {
    Write-Host "❌ FAILED!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    $healthOk = $false
}
Write-Host ""

# Test 2: Root Endpoint
Write-Host "[2/3] Testing / (root) endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$railwayUrl/" -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor White
    try {
        $json = $response.Content | ConvertFrom-Json
        Write-Host "   Service: $($json.service)" -ForegroundColor White
        Write-Host "   Status: $($json.status)" -ForegroundColor White
        if ($json.system_prompt_loaded) {
            Write-Host "   System Prompt: Loaded ($($json.system_prompt_length) chars)" -ForegroundColor White
        }
    } catch {
        Write-Host "   Response: $($response.Content.Substring(0, [Math]::Min(100, $response.Content.Length)))..." -ForegroundColor White
    }
    $rootOk = $true
} catch {
    Write-Host "❌ FAILED!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    $rootOk = $false
}
Write-Host ""

# Test 3: DNS Resolution
Write-Host "[3/3] Testing DNS resolution..." -ForegroundColor Yellow
try {
    $dns = Resolve-DnsName -Name "nima-ai-marketing-production-82df.up.railway.app" -ErrorAction Stop
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host "   IP Address: $($dns[0].IPAddress)" -ForegroundColor White
    $dnsOk = $true
} catch {
    Write-Host "❌ FAILED!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    $dnsOk = $false
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($healthOk -and $rootOk) {
    Write-Host "✅ All tests PASSED! Server is working." -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now use the API at:" -ForegroundColor White
    Write-Host "  $railwayUrl" -ForegroundColor Cyan
} elseif ($dnsOk -and -not $healthOk) {
    Write-Host "⚠️  DNS works but server is not responding." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Possible reasons:" -ForegroundColor White
    Write-Host "  - Server is still starting up" -ForegroundColor Gray
    Write-Host "  - Server crashed during startup" -ForegroundColor Gray
    Write-Host "  - PORT configuration issue" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Check Railway Dashboard → Logs for details." -ForegroundColor White
} elseif (-not $dnsOk) {
    Write-Host "❌ DNS resolution failed." -ForegroundColor Red
    Write-Host "   Check if the URL is correct." -ForegroundColor White
} else {
    Write-Host "❌ Some tests failed. Check Railway Dashboard → Logs." -ForegroundColor Red
}

Write-Host ""









