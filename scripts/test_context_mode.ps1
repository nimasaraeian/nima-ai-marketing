# Test script for context-aware mode (enterprise brand detection)
# Tests /api/analyze/url-human with Stripe pricing to verify enterprise context-aware mode

$ErrorActionPreference = "Stop"

$BASE_URL = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }

Write-Host "`n=== Testing Context-Aware Mode (Enterprise Brands) ===" -ForegroundColor Cyan
Write-Host "Base URL: $BASE_URL`n" -ForegroundColor Gray

# Test with Stripe pricing (known enterprise brand)
$testUrl = "https://stripe.com/pricing"

try {
    $body = @{
        url = $testUrl
        goal = "leads"
        locale = "en"
    } | ConvertTo-Json
    
    Write-Host "📡 Sending request to: $BASE_URL/api/analyze/url-human" -ForegroundColor Yellow
    Write-Host "📋 URL: $testUrl (Enterprise brand - Stripe)`n" -ForegroundColor Gray
    
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/analyze/url-human" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 180
    
    Write-Host "✅ Request completed successfully`n" -ForegroundColor Green
    
    # Check brand context
    Write-Host "🏢 Brand Context Check:" -ForegroundColor Cyan
    if ($response.PSObject.Properties.Name -contains "brand_context") {
        $brandCtx = $response.brand_context
        Write-Host "  ✅ brand_context exists" -ForegroundColor Green
        Write-Host "    Brand Maturity: $($brandCtx.brand_maturity)" -ForegroundColor Gray
        Write-Host "    Confidence: $($brandCtx.confidence)" -ForegroundColor Gray
        Write-Host "    Analysis Mode: $($brandCtx.analysis_mode)" -ForegroundColor Gray
        
        if ($brandCtx.brand_maturity -eq "enterprise") {
            Write-Host "    ✅ Correctly detected as enterprise brand" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Expected 'enterprise', got '$($brandCtx.brand_maturity)'" -ForegroundColor Yellow
        }
        
        if ($brandCtx.analysis_mode -eq "enterprise_context_aware") {
            Write-Host "    ✅ Enterprise context-aware mode enabled" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Expected 'enterprise_context_aware', got '$($brandCtx.analysis_mode)'" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ❌ brand_context missing" -ForegroundColor Red
    }
    Write-Host ""
    
    # Check page intent
    Write-Host "🎯 Page Intent Check:" -ForegroundColor Cyan
    if ($response.PSObject.Properties.Name -contains "page_intent") {
        $intent = $response.page_intent
        Write-Host "  ✅ page_intent exists" -ForegroundColor Green
        Write-Host "    Intent: $($intent.intent)" -ForegroundColor Gray
        Write-Host "    Confidence: $($intent.confidence)" -ForegroundColor Gray
        
        if ($intent.intent -eq "pricing") {
            Write-Host "    ✅ Correctly detected as pricing page" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Expected 'pricing', got '$($intent.intent)'" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ❌ page_intent missing" -ForegroundColor Red
    }
    Write-Host ""
    
    # Check context note (should exist for enterprise_context_aware)
    Write-Host "📝 Context Note Check:" -ForegroundColor Cyan
    if ($response.PSObject.Properties.Name -contains "context_note") {
        $contextNote = $response.context_note
        Write-Host "  ✅ context_note exists" -ForegroundColor Green
        Write-Host "    Headline: $($contextNote.headline)" -ForegroundColor Gray
        Write-Host "    Text: $($contextNote.text.Substring(0, [Math]::Min(80, $contextNote.text.Length)))..." -ForegroundColor Gray
    } else {
        Write-Host "  ⚠️  context_note missing (expected for enterprise_context_aware mode)" -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Check CTA recommendations (should be friction-diagnostic, not generic)
    Write-Host "🔘 CTA Recommendations Check:" -ForegroundColor Cyan
    if ($response.PSObject.Properties.Name -contains "cta_recommendations") {
        $cta = $response.cta_recommendations
        $primaryLabel = $cta.primary.label.ToLower()
        Write-Host "  ✅ cta_recommendations exists" -ForegroundColor Green
        Write-Host "    Primary CTA: $($cta.primary.label)" -ForegroundColor Gray
        
        $genericCTAs = @("get started", "start your journey", "learn more")
        $isGeneric = $false
        foreach ($generic in $genericCTAs) {
            if ($primaryLabel -eq $generic) {
                $isGeneric = $true
                break
            }
        }
        
        if ($isGeneric) {
            Write-Host "    ⚠️  Primary CTA is generic: $($cta.primary.label)" -ForegroundColor Yellow
            Write-Host "      Expected friction-diagnostic CTA for enterprise pricing page" -ForegroundColor Yellow
        } else {
            Write-Host "    ✅ Primary CTA is friction-diagnostic: $($cta.primary.label)" -ForegroundColor Green
        }
        
        # Check for pricing-specific secondaries
        if ($cta.secondary.Count -gt 0) {
            Write-Host "    Secondary CTAs: $($cta.secondary.Count)" -ForegroundColor Gray
            foreach ($secondary in $cta.secondary) {
                Write-Host "      - $($secondary.label)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  ❌ cta_recommendations missing" -ForegroundColor Red
    }
    Write-Host ""
    
    # Check that naive trust claims are not present
    Write-Host "🔍 Naive Verdict Check:" -ForegroundColor Cyan
    $humanReport = $response.human_report
    if ($humanReport) {
        $reportLower = $humanReport.ToLower()
        $naivePhrases = @("trust signals are missing", "no trust signals", "missing trust signals")
        $foundNaive = $false
        foreach ($phrase in $naivePhrases) {
            if ($reportLower -like "*$phrase*") {
                Write-Host "  ⚠️  Found naive phrase: '$phrase'" -ForegroundColor Yellow
                $foundNaive = $true
            }
        }
        if (-not $foundNaive) {
            Write-Host "  ✅ No naive trust claims found (correctly reframed)" -ForegroundColor Green
        }
        
        # Check for context-aware language
        if ($reportLower -like "*informed*" -or $reportLower -like "*first-time*" -or $reportLower -like "*price-sensitive*") {
            Write-Host "  ✅ Contains context-aware language" -ForegroundColor Green
        }
    }
    Write-Host ""
    
    Write-Host "🎉 Context-aware mode test completed!" -ForegroundColor Green
    Write-Host "Enterprise brands should avoid naive verdicts and use friction-diagnostic CTAs.`n" -ForegroundColor Green
    
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

