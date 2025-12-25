# Test script for human_report_v2 pipeline
# Tests /api/analyze/url-human with different URLs to verify new structured report sections

$ErrorActionPreference = "Stop"

$BASE_URL = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }

Write-Host "`n=== Testing Human Report V2 Pipeline ===" -ForegroundColor Cyan
Write-Host "Base URL: $BASE_URL`n" -ForegroundColor Gray

# Test URLs
$testUrls = @(
    @{
        name = "Stripe Pricing (Enterprise)"
        url = "https://stripe.com/pricing"
    },
    @{
        name = "Digikala (Large Ecommerce)"
        url = "https://www.digikala.com/"
    },
    @{
        name = "Personal Site"
        url = "https://nimasaraeian.com/"
    }
)

foreach ($testCase in $testUrls) {
    Write-Host "`n📋 Testing: $($testCase.name)" -ForegroundColor Yellow
    Write-Host "   URL: $($testCase.url)`n" -ForegroundColor Gray
    
    try {
        $body = @{
            url = $testCase.url
            goal = "leads"
            locale = "en"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$BASE_URL/api/analyze/url-human" `
            -Method Post `
            -Body $body `
            -ContentType "application/json" `
            -TimeoutSec 180
        
        Write-Host "✅ Request completed successfully`n" -ForegroundColor Green
        
        # Check debug
        Write-Host "   🔍 Debug:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "debug") {
            $debug = $response.debug
            Write-Host "      Pipeline Version: $($debug.pipeline_version)" -ForegroundColor Gray
            Write-Host "      Steps: $($debug.steps -join ', ')" -ForegroundColor Gray
            Write-Host "      Analysis Mode: $($debug.analysis_mode)" -ForegroundColor Gray
            Write-Host "      Brand Maturity: $($debug.brand_maturity)" -ForegroundColor Gray
            Write-Host "      Page Intent: $($debug.page_intent)" -ForegroundColor Gray
            Write-Host "      Page Type: $($debug.page_type)" -ForegroundColor Gray
            
            if ($debug.pipeline_version -eq "human_report_v2") {
                Write-Host "      ✅ Correct pipeline version" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  Expected 'human_report_v2', got '$($debug.pipeline_version)'" -ForegroundColor Yellow
            }
            
            if ($debug.steps -contains "signature_layers") {
                Write-Host "      ✅ Signature layers step present" -ForegroundColor Green
            } else {
                Write-Host "      ❌ Signature layers step missing" -ForegroundColor Red
            }
            
            if ($debug.errors.Count -gt 0) {
                Write-Host "      ⚠️  Errors: $($debug.errors -join ', ')" -ForegroundColor Yellow
            }
        } else {
            Write-Host "      ❌ debug missing" -ForegroundColor Red
        }
        
        # Check brand context
        Write-Host "   🏢 Brand Context:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "brand_context") {
            $brandCtx = $response.brand_context
            Write-Host "      Maturity: $($brandCtx.brand_maturity)" -ForegroundColor Gray
            Write-Host "      Analysis Mode: $($brandCtx.analysis_mode)" -ForegroundColor Gray
        } else {
            Write-Host "      ❌ brand_context missing" -ForegroundColor Red
        }
        
        # Check page type
        Write-Host "   📄 Page Type:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "page_type") {
            $pageType = $response.page_type
            if ($pageType -is [PSCustomObject] -or $pageType -is [Hashtable]) {
                Write-Host "      Type: $($pageType.type)" -ForegroundColor Gray
                Write-Host "      Confidence: $($pageType.confidence)" -ForegroundColor Gray
            } else {
                Write-Host "      Type: $pageType (legacy string)" -ForegroundColor Gray
            }
        } else {
            Write-Host "      ❌ page_type missing" -ForegroundColor Red
        }
        
        # Check decision psychology insight
        Write-Host "   💡 Decision Psychology Insight:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "decision_psychology_insight") {
            $insight = $response.decision_psychology_insight
            Write-Host "      Headline: $($insight.headline)" -ForegroundColor Gray
            
            # Check for forbidden phrases
            $insightText = "$($insight.headline) $($insight.insight) $($insight.why_now) $($insight.micro_risk_reducer)".ToLower()
            $forbiddenPhrases = @("untrustworthy", "lacks trust signals", "feels risky", "no trust")
            $foundForbidden = $false
            foreach ($phrase in $forbiddenPhrases) {
                if ($insightText -like "*$phrase*") {
                    Write-Host "      ⚠️  Found forbidden phrase: '$phrase'" -ForegroundColor Yellow
                    $foundForbidden = $true
                }
            }
            if (-not $foundForbidden) {
                Write-Host "      ✅ No forbidden trust phrases found" -ForegroundColor Green
            }
        } else {
            Write-Host "      ❌ decision_psychology_insight missing" -ForegroundColor Red
        }
        
        # Check CTA recommendations
        Write-Host "   🔘 CTA Recommendations:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "cta_recommendations") {
            $cta = $response.cta_recommendations
            Write-Host "      Primary: $($cta.primary.label)" -ForegroundColor Gray
            Write-Host "      Reason: $($cta.primary.reason)" -ForegroundColor Gray
            
            # Check it's not generic
            $primaryLabel = $cta.primary.label.ToLower()
            $genericCTAs = @("get started", "start your journey", "learn more")
            $isGeneric = $false
            foreach ($generic in $genericCTAs) {
                if ($primaryLabel -eq $generic) {
                    $isGeneric = $true
                    break
                }
            }
            if ($isGeneric) {
                Write-Host "      ⚠️  Primary CTA is generic" -ForegroundColor Yellow
            } else {
                Write-Host "      ✅ Primary CTA is friction-driven" -ForegroundColor Green
            }
        } else {
            Write-Host "      ❌ cta_recommendations missing" -ForegroundColor Red
        }
        
        # Check cost of inaction
        Write-Host "   💰 Cost of Inaction:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "cost_of_inaction") {
            $cost = $response.cost_of_inaction
            Write-Host "      Headline: $($cost.headline)" -ForegroundColor Gray
            Write-Host "      Bullets: $($cost.bullets.Count)" -ForegroundColor Gray
        } else {
            Write-Host "      ❌ cost_of_inaction missing" -ForegroundColor Red
        }
        
        # Check mindset personas
        Write-Host "   👥 Mindset Personas:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "mindset_personas") {
            $personas = $response.mindset_personas
            Write-Host "      Count: $($personas.Count)" -ForegroundColor Gray
            if ($personas.Count -eq 3) {
                Write-Host "      ✅ All 3 personas present" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  Expected 3 personas, found $($personas.Count)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "      ❌ mindset_personas missing" -ForegroundColor Red
        }
        
        Write-Host ""
        
    } catch {
        Write-Host "   ❌ ERROR: Test failed" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "   Response: $responseBody" -ForegroundColor Red
        }
    }
}

Write-Host "`n🎉 Human Report V2 pipeline test completed!" -ForegroundColor Green
Write-Host "All new structured sections should be present with correct pipeline version.`n" -ForegroundColor Green




