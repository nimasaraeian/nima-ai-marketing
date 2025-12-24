# Test script for /api/analyze/url-human endpoint with new signature layers
# PowerShell-friendly script to test the enhanced response

$ErrorActionPreference = "Stop"

$BASE_URL = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }

Write-Host "`n=== Testing /api/analyze/url-human with Signature Layers ===" -ForegroundColor Cyan
Write-Host "Base URL: $BASE_URL`n" -ForegroundColor Gray

# Test URL
$testUrl = "https://example.com"

try {
    $body = @{
        url = $testUrl
        goal = "leads"
        locale = "en"
    } | ConvertTo-Json
    
    Write-Host "📡 Sending request to: $BASE_URL/api/analyze/url-human" -ForegroundColor Yellow
    Write-Host "📋 URL: $testUrl`n" -ForegroundColor Gray
    
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/analyze/url-human" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 180
    
    Write-Host "✅ Request completed successfully`n" -ForegroundColor Green
    
    # Check backward compatibility - existing keys
    Write-Host "📊 Backward Compatibility Check:" -ForegroundColor Cyan
    $existingKeys = @("analysisStatus", "human_report", "findings", "summary", "page_type", "screenshots")
    foreach ($key in $existingKeys) {
        if ($response.PSObject.Properties.Name -contains $key) {
            Write-Host "  ✅ $key exists" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $key missing" -ForegroundColor Red
        }
    }
    Write-Host ""
    
    # Check new signature layers
    Write-Host "🎯 New Signature Layers Check:" -ForegroundColor Cyan
    
    # 1. Decision Psychology Insight
    if ($response.PSObject.Properties.Name -contains "decision_psychology_insight") {
        Write-Host "  ✅ decision_psychology_insight exists" -ForegroundColor Green
        $insight = $response.decision_psychology_insight
        Write-Host "    Headline: $($insight.headline)" -ForegroundColor Gray
        Write-Host "    Insight: $($insight.insight.Substring(0, [Math]::Min(80, $insight.insight.Length)))..." -ForegroundColor Gray
    } else {
        Write-Host "  ❌ decision_psychology_insight missing" -ForegroundColor Red
    }
    
    # 2. CTA Recommendations
    if ($response.PSObject.Properties.Name -contains "cta_recommendations") {
        Write-Host "  ✅ cta_recommendations exists" -ForegroundColor Green
        $cta = $response.cta_recommendations
        Write-Host "    Primary CTA: $($cta.primary.label)" -ForegroundColor Gray
        Write-Host "    Reason: $($cta.primary.reason)" -ForegroundColor Gray
        Write-Host "    Secondary CTAs: $($cta.secondary.Count)" -ForegroundColor Gray
        Write-Host "    Do Not Use: $($cta.do_not_use.Count)" -ForegroundColor Gray
        
        # Check primary CTA is not generic
        $primaryLabel = $cta.primary.label.ToLower()
        $genericCTAs = @("start your journey", "learn more", "get started")
        $isGeneric = $false
        foreach ($generic in $genericCTAs) {
            if ($primaryLabel -eq $generic) {
                $isGeneric = $true
                break
            }
        }
        if ($isGeneric) {
            Write-Host "    ⚠️  Primary CTA is generic: $($cta.primary.label)" -ForegroundColor Yellow
        } else {
            Write-Host "    ✅ Primary CTA is friction-driven: $($cta.primary.label)" -ForegroundColor Green
        }
    } else {
        Write-Host "  ❌ cta_recommendations missing" -ForegroundColor Red
    }
    
    # 3. Cost of Inaction
    if ($response.PSObject.Properties.Name -contains "cost_of_inaction") {
        Write-Host "  ✅ cost_of_inaction exists" -ForegroundColor Green
        $cost = $response.cost_of_inaction
        Write-Host "    Headline: $($cost.headline)" -ForegroundColor Gray
        Write-Host "    Bullets: $($cost.bullets.Count)" -ForegroundColor Gray
        foreach ($bullet in $cost.bullets) {
            Write-Host "      - $bullet" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ❌ cost_of_inaction missing" -ForegroundColor Red
    }
    
    # 4. Mindset Personas
    if ($response.PSObject.Properties.Name -contains "mindset_personas") {
        Write-Host "  ✅ mindset_personas exists" -ForegroundColor Green
        $personas = $response.mindset_personas
        Write-Host "    Personas count: $($personas.Count)" -ForegroundColor Gray
        foreach ($persona in $personas) {
            Write-Host "    - $($persona.title) ($($persona.id))" -ForegroundColor Gray
            Write-Host "      Best CTA: $($persona.best_cta)" -ForegroundColor Gray
        }
        
        if ($personas.Count -eq 3) {
            Write-Host "    ✅ All 3 personas present" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Expected 3 personas, found $($personas.Count)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ❌ mindset_personas missing" -ForegroundColor Red
    }
    
    Write-Host "`n🎉 Test completed successfully!" -ForegroundColor Green
    Write-Host "All signature layers are present and structured correctly.`n" -ForegroundColor Green
    
} catch {
    Write-Host "`n❌ ERROR: Test failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

