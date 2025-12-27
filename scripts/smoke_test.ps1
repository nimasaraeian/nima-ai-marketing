# Smoke test for /api/analyze/url-human endpoint
# Tests that capture.artifacts are always present with url or data_uri

$BASE = "http://127.0.0.1:8000"
$endpoint = "$BASE/api/analyze/url-human"

Write-Host "Testing /api/analyze/url-human endpoint..." -ForegroundColor Cyan
Write-Host "Endpoint: $endpoint" -ForegroundColor Gray
Write-Host ""

$payload = @{
    url = "https://stripe.com/pricing"
    goal = "leads"
    locale = "en"
} | ConvertTo-Json

Write-Host "Sending request..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri $endpoint -Method POST -ContentType "application/json" -Body $payload -TimeoutSec 180
    
    Write-Host ""
    Write-Host "Response received!" -ForegroundColor Green
    Write-Host ""
    
    # Check HTTP 200 (implicit - no exception means 200)
    Write-Host "HTTP Status: 200 OK" -ForegroundColor Green
    
    # Check capture exists
    if ($null -eq $response.capture) {
        Write-Host "FAIL: response.capture is null" -ForegroundColor Red
        exit 1
    }
    Write-Host "PASS: response.capture exists" -ForegroundColor Green
    
    # Check artifacts structure
    $artifacts = $response.capture.artifacts
    if ($null -eq $artifacts) {
        Write-Host "FAIL: response.capture.artifacts is null" -ForegroundColor Red
        exit 1
    }
    Write-Host "PASS: response.capture.artifacts exists" -ForegroundColor Green
    
    # Check above_the_fold
    $atf = $artifacts.above_the_fold
    if ($null -eq $atf) {
        Write-Host "FAIL: response.capture.artifacts.above_the_fold is null" -ForegroundColor Red
        exit 1
    }
    Write-Host "PASS: response.capture.artifacts.above_the_fold exists" -ForegroundColor Green
    
    # Check desktop
    $desktop = $atf.desktop
    if ($null -eq $desktop) {
        Write-Host "FAIL: response.capture.artifacts.above_the_fold.desktop is null" -ForegroundColor Red
        exit 1
    }
    Write-Host "PASS: response.capture.artifacts.above_the_fold.desktop exists" -ForegroundColor Green
    
    # Check desktop has url OR data_uri
    $desktopUrl = $desktop.url
    $desktopDataUri = $desktop.data_uri
    
    if ($null -eq $desktopUrl -and $null -eq $desktopDataUri) {
        Write-Host "FAIL: desktop has neither url nor data_uri" -ForegroundColor Red
        exit 1
    }
    
    if ($desktopUrl) {
        Write-Host "PASS: desktop.url = $desktopUrl" -ForegroundColor Green
    }
    if ($desktopDataUri) {
        Write-Host "PASS: desktop.data_uri exists (length: $($desktopDataUri.Length))" -ForegroundColor Green
    }
    
    # Check mobile
    $mobile = $atf.mobile
    if ($null -eq $mobile) {
        Write-Host "FAIL: response.capture.artifacts.above_the_fold.mobile is null" -ForegroundColor Red
        exit 1
    }
    Write-Host "PASS: response.capture.artifacts.above_the_fold.mobile exists" -ForegroundColor Green
    
    # Check mobile has url OR data_uri
    $mobileUrl = $mobile.url
    $mobileDataUri = $mobile.data_uri
    
    if ($null -eq $mobileUrl -and $null -eq $mobileDataUri) {
        Write-Host "FAIL: mobile has neither url nor data_uri" -ForegroundColor Red
        exit 1
    }
    
    if ($mobileUrl) {
        Write-Host "PASS: mobile.url = $mobileUrl" -ForegroundColor Green
    }
    if ($mobileDataUri) {
        Write-Host "PASS: mobile.data_uri exists (length: $($mobileDataUri.Length))" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "All checks passed!" -ForegroundColor Green
    exit 0
    
} catch {
    Write-Host ""
    Write-Host "FAIL: Error occurred" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

