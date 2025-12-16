# Demo stability check for analyze-url endpoint
# Tests encoding, VisualTrust, and response structure

$url = "https://nimasaraeian.com/"
$endpoint = "http://127.0.0.1:8000/analyze-url?refresh=1"
$successCount = 0
$failCount = 0
$errors = @()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Demo Check - Running 10 tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

for ($i = 1; $i -le 10; $i++) {
    Write-Host "Test $i/10..." -NoNewline
    
    try {
        $response = Invoke-RestMethod -Uri $endpoint -Method Post -ContentType "application/json" -Body (@{url=$url} | ConvertTo-Json) -TimeoutSec 60
        
        # Check encoding gate
        $encodingIssues = $false
        if ($response.extractedText -match "[Ââ]|Letâs|Â·") {
            $encodingIssues = $true
            Write-Host " FAILED (encoding issue)" -ForegroundColor Red
            $errors += "Test ${i}: Encoding issue found in extractedText"
            $failCount++
            continue
        }
        
        # Check analysisStatus
        if ($response.analysisStatus -ne "ok") {
            Write-Host " FAILED (analysisStatus=$($response.analysisStatus))" -ForegroundColor Red
            $errors += "Test ${i}: analysisStatus=$($response.analysisStatus)"
            $failCount++
            continue
        }
        
        # Check visualTrust structure
        $vt = $response.visualTrust
        if (-not $vt) {
            Write-Host " FAILED (visualTrust missing)" -ForegroundColor Red
            $errors += "Test ${i}: visualTrust missing"
            $failCount++
            continue
        }
        
        # Check visualTrust keys
        $requiredKeys = @("analysisStatus", "label", "confidence", "warnings", "elements", "narrative")
        $missingKeys = @()
        foreach ($key in $requiredKeys) {
            if (-not $vt.PSObject.Properties.Name -contains $key) {
                $missingKeys += $key
            }
        }
        if ($missingKeys.Count -gt 0) {
            Write-Host " FAILED (visualTrust missing keys: $($missingKeys -join ', '))" -ForegroundColor Red
            $errors += "Test ${i}: visualTrust missing keys: $($missingKeys -join ', ')"
            $failCount++
            continue
        }
        
        # Check label is not null
        if ([string]::IsNullOrEmpty($vt.label)) {
            Write-Host " FAILED (visualTrust.label is null)" -ForegroundColor Red
            $errors += "Test ${i}: visualTrust.label is null"
            $failCount++
            continue
        }
        
        # Check narrative is non-empty
        if (-not $vt.narrative -or $vt.narrative.Count -eq 0) {
            Write-Host " FAILED (visualTrust.narrative is empty)" -ForegroundColor Red
            $errors += "Test ${i}: visualTrust.narrative is empty"
            $failCount++
            continue
        }
        
        # Check debugBuild
        if ($response.debugBuild -ne "DEMO_READY_V1") {
            Write-Host " WARNING (debugBuild=$($response.debugBuild))" -ForegroundColor Yellow
        }
        
        # Check screenshot bytes
        if ($response.debugScreenshotBytes -lt 50000) {
            Write-Host " WARNING (screenshot bytes=$($response.debugScreenshotBytes))" -ForegroundColor Yellow
        }
        
        Write-Host " OK (status=$($response.analysisStatus), vt_label=$($vt.label), vt_conf=$($vt.confidence), screenshot=$($response.debugScreenshotBytes) bytes)" -ForegroundColor Green
        $successCount++
        
    } catch {
        Write-Host " FAILED (exception: $($_.Exception.Message))" -ForegroundColor Red
        $errors += "Test ${i}: Exception - $($_.Exception.Message)"
        $failCount++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Results: $successCount passed, $failCount failed" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Red" })
Write-Host "========================================" -ForegroundColor Cyan

if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "Errors:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
    exit 1
} else {
    Write-Host ""
    Write-Host "All tests passed!" -ForegroundColor Green
    exit 0
}

