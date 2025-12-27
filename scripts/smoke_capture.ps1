# Smoke test for /api/analyze/url-human endpoint
# Tests that capture and screenshots are always returned (never null)

$baseUrl = "http://127.0.0.1:8000"
$endpoint = "$baseUrl/api/analyze/url-human"

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
    Write-Host "✅ Response received!" -ForegroundColor Green
    Write-Host ""
    
    # Check required fields
    $checks = @()
    
    # Check status
    if ($response.status -eq "ok") {
        Write-Host "✅ status = 'ok'" -ForegroundColor Green
        $checks += $true
    } else {
        Write-Host "❌ status = '$($response.status)' (expected 'ok')" -ForegroundColor Red
        $checks += $false
    }
    
    # Check analysisStatus
    if ($response.analysisStatus -eq "ok") {
        Write-Host "✅ analysisStatus = 'ok'" -ForegroundColor Green
        $checks += $true
    } else {
        Write-Host "❌ analysisStatus = '$($response.analysisStatus)' (expected 'ok')" -ForegroundColor Red
        $checks += $false
    }
    
    # Check summary.url
    if ($response.summary.url -eq "https://stripe.com/pricing") {
        Write-Host "✅ summary.url = input URL" -ForegroundColor Green
        $checks += $true
    } else {
        Write-Host "❌ summary.url = '$($response.summary.url)' (expected input URL)" -ForegroundColor Red
        $checks += $false
    }
    
    # Check screenshots (must not be null)
    if ($null -ne $response.screenshots) {
        Write-Host "✅ screenshots is not null" -ForegroundColor Green
        $checks += $true
        
        # Check structure
        if ($response.screenshots.desktop -and $response.screenshots.mobile) {
            Write-Host "  ✅ screenshots.desktop exists" -ForegroundColor Green
            Write-Host "  ✅ screenshots.mobile exists" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  screenshots structure incomplete" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ screenshots is null" -ForegroundColor Red
        $checks += $false
    }
    
    # Check capture (must not be null)
    if ($null -ne $response.capture) {
        Write-Host "✅ capture is not null" -ForegroundColor Green
        $checks += $true
        
        # Check capture status
        if ($response.capture.status) {
            Write-Host "  ✅ capture.status = '$($response.capture.status)'" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  capture.status missing" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ capture is null" -ForegroundColor Red
        $checks += $false
    }
    
    # Check for Persian/mojibake in issues
    $hasPersian = $false
    if ($response.issues) {
        foreach ($issue in $response.issues) {
            if ($issue.problem -match "[\u0600-\u06FF]") {
                Write-Host "❌ Persian detected in issue.problem: $($issue.problem)" -ForegroundColor Red
                $hasPersian = $true
            }
        }
    }
    if (-not $hasPersian) {
        Write-Host "✅ No Persian detected in issues" -ForegroundColor Green
        $checks += $true
    } else {
        $checks += $false
    }
    
    # Summary
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    $passed = ($checks | Where-Object { $_ -eq $true }).Count
    $total = $checks.Count
    Write-Host "Tests passed: $passed / $total" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })
    
    if ($passed -eq $total) {
        Write-Host "✅ All checks passed!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "⚠️  Some checks failed" -ForegroundColor Yellow
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

