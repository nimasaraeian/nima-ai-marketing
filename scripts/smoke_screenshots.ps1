# Smoke test script for screenshot serving
# Tests: 
# - /api/artifacts/_health
# - /api/debug_shots/_health
# - /api/analyze/url-human (with screenshots URLs)
# - /api/brain/decision-engine/report-from-url (with screenshots URLs)

$ErrorActionPreference = "Stop"

$BASE_URL = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }

Write-Host "`n=== Screenshot Smoke Test ===" -ForegroundColor Cyan
Write-Host "Base URL: $BASE_URL`n" -ForegroundColor Gray

# Step 1: Test artifacts health endpoint
Write-Host "Step 1: Testing /api/artifacts/_health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BASE_URL/api/artifacts/_health" -Method Get
    Write-Host "  ✓ Artifacts health check passed" -ForegroundColor Green
    Write-Host "    exists: $($health.exists)" -ForegroundColor Gray
    Write-Host "    is_dir: $($health.is_dir)" -ForegroundColor Gray
    Write-Host "    path: $($health.path)" -ForegroundColor Gray
    if ($health.sample_files) {
        Write-Host "    sample_files: $($health.sample_files.Count) files" -ForegroundColor Gray
    }
    
    if (-not $health.exists) {
        Write-Host "  ✗ ERROR: Directory does not exist!" -ForegroundColor Red
        exit 1
    }
    if (-not $health.is_dir) {
        Write-Host "  ✗ ERROR: Path is not a directory!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ ERROR: Artifacts health check failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Test debug_shots health endpoint
Write-Host "`nStep 2: Testing /api/debug_shots/_health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BASE_URL/api/debug_shots/_health" -Method Get
    Write-Host "  ✓ Health check passed" -ForegroundColor Green
    Write-Host "    exists: $($health.exists)" -ForegroundColor Gray
    Write-Host "    is_dir: $($health.is_dir)" -ForegroundColor Gray
    Write-Host "    path: $($health.path)" -ForegroundColor Gray
    if ($health.sample_files) {
        Write-Host "    sample_files: $($health.sample_files.Count) files" -ForegroundColor Gray
    }
    
    if (-not $health.exists) {
        Write-Host "  ✗ ERROR: Directory does not exist!" -ForegroundColor Red
        exit 1
    }
    if (-not $health.is_dir) {
        Write-Host "  ✗ ERROR: Path is not a directory!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ ERROR: Debug shots health check failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Test url-human endpoint
Write-Host "`nStep 3: Testing /api/analyze/url-human..." -ForegroundColor Yellow
$testUrl = "https://nimasaraeian.com/"
try {
    $body = @{
        url = $testUrl
        goal = "leads"
        locale = "en"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/analyze/url-human" `
        -Method Post `
        -Body $body `
        -ContentType "application/json"
    
    Write-Host "  ✓ URL-human analysis completed" -ForegroundColor Green
    Write-Host "    analysisStatus: $($response.analysisStatus)" -ForegroundColor Gray
    
    # Check for screenshots
    if ($response.capture_info -and $response.capture_info.screenshots) {
        $screenshots = $response.capture_info.screenshots
        Write-Host "  ✓ Screenshots found in response" -ForegroundColor Green
        
        if ($screenshots.above_the_fold -and $screenshots.above_the_fold.url) {
            Write-Host "    Above the fold URL: $($screenshots.above_the_fold.url)" -ForegroundColor Gray
            # Test URL
            try {
                $screenshotUrl = $screenshots.above_the_fold.url
                if ($screenshotUrl.StartsWith("/")) {
                    $screenshotUrl = "$BASE_URL$screenshotUrl"
                }
                $testResponse = Invoke-WebRequest -Uri $screenshotUrl -Method Get
                Write-Host "  ✓ Above the fold screenshot URL returns 200" -ForegroundColor Green
            } catch {
                Write-Host "  ⚠ Above the fold screenshot URL failed: $_" -ForegroundColor Yellow
            }
        }
        
        if ($screenshots.full_page -and $screenshots.full_page.url) {
            Write-Host "    Full page URL: $($screenshots.full_page.url)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Screenshots not found in response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ ERROR: URL-human analysis failed: $_" -ForegroundColor Red
    Write-Host "    Error details: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 4: Test report-from-url endpoint
Write-Host "`nStep 4: Testing /api/brain/decision-engine/report-from-url..." -ForegroundColor Yellow
$testUrl = "https://nimasaraeian.com/"
try {
    $body = @{
        url = $testUrl
        timeoutSec = 30
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/brain/decision-engine/report-from-url" `
        -Method Post `
        -Body $body `
        -ContentType "application/json"
    
    Write-Host "  ✓ Report generated successfully" -ForegroundColor Green
    Write-Host "    analysisStatus: $($response.analysisStatus)" -ForegroundColor Gray
    
    # Check for screenshots
    if ($response.screenshots) {
        Write-Host "  ✓ Screenshots object found in response" -ForegroundColor Green
        
        if ($response.screenshots.desktop) {
            $desktop = $response.screenshots.desktop
            Write-Host "    Desktop screenshot:" -ForegroundColor Gray
            Write-Host "      status: $($desktop.status)" -ForegroundColor Gray
            Write-Host "      url: $($desktop.url)" -ForegroundColor Gray
            
            if ($desktop.status -eq "ok" -and $desktop.url) {
                Write-Host "  ✓ Desktop screenshot URL available" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Desktop screenshot not available" -ForegroundColor Yellow
            }
        }
        
        if ($response.screenshots.mobile) {
            $mobile = $response.screenshots.mobile
            Write-Host "    Mobile screenshot:" -ForegroundColor Gray
            Write-Host "      status: $($mobile.status)" -ForegroundColor Gray
            Write-Host "      url: $($mobile.url)" -ForegroundColor Gray
            
            if ($mobile.status -eq "ok" -and $mobile.url) {
                Write-Host "  ✓ Mobile screenshot URL available" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Mobile screenshot not available" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  ✗ ERROR: Screenshots object missing from response!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ ERROR: Report generation failed: $_" -ForegroundColor Red
    Write-Host "    Error details: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 5: Download screenshot if available
if ($response.screenshots.desktop.status -eq "ok" -and $response.screenshots.desktop.url) {
    Write-Host "`nStep 5: Downloading desktop screenshot..." -ForegroundColor Yellow
    try {
        $screenshotUrl = $response.screenshots.desktop.url
        # Handle relative URLs
        if ($screenshotUrl.StartsWith("/")) {
            $screenshotUrl = "$BASE_URL$screenshotUrl"
        }
        
        $outputFile = ".\_smoke_desktop.png"
        Invoke-WebRequest -Uri $screenshotUrl -OutFile $outputFile
        $fileSize = (Get-Item $outputFile).Length
        Write-Host "  ✓ Screenshot downloaded: $outputFile ($fileSize bytes)" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ ERROR: Failed to download screenshot: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 6: Verify OpenAPI includes the endpoints
Write-Host "`nStep 6: Verifying OpenAPI schema..." -ForegroundColor Yellow
try {
    $openapi = Invoke-RestMethod -Uri "$BASE_URL/openapi.json" -Method Get
    $paths = $openapi.paths
    
    if ($paths."/api/artifacts/_health") {
        Write-Host "  ✓ /api/artifacts/_health found in OpenAPI" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ /api/artifacts/_health not found in OpenAPI" -ForegroundColor Yellow
    }
    
    if ($paths."/api/debug_shots/_health") {
        Write-Host "  ✓ /api/debug_shots/_health found in OpenAPI" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ /api/debug_shots/_health not found in OpenAPI" -ForegroundColor Yellow
    }
    
    if ($paths."/api/analyze/url-human") {
        Write-Host "  ✓ /api/analyze/url-human found in OpenAPI" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ /api/analyze/url-human not found in OpenAPI" -ForegroundColor Yellow
    }
    
    if ($paths."/api/brain/decision-engine/report-from-url") {
        Write-Host "  ✓ /api/brain/decision-engine/report-from-url found in OpenAPI" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ /api/brain/decision-engine/report-from-url not found in OpenAPI" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Could not verify OpenAPI: $_" -ForegroundColor Yellow
}

Write-Host "`n=== All tests passed! ===" -ForegroundColor Green

