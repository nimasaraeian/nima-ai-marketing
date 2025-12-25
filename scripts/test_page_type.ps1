# Test script for page type detection
# Tests /api/analyze/url-human with different page types to verify context-aware recommendations

$ErrorActionPreference = "Stop"

$BASE_URL = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }

Write-Host "`n=== Testing Page Type Detection ===" -ForegroundColor Cyan
Write-Host "Base URL: $BASE_URL`n" -ForegroundColor Gray

# Test URLs
$testUrls = @(
    @{
        name = "Shopify Product Page"
        url = "https://shopify.com/products/example"
        expectedType = "ecommerce_product"
    },
    @{
        name = "SaaS Pricing Page"
        url = "https://stripe.com/pricing"
        expectedType = "saas_pricing"
    },
    @{
        name = "Local Clinic Page"
        url = "https://example-clinic.com"
        expectedType = "local_service"
    }
)

foreach ($testCase in $testUrls) {
    Write-Host "`n📋 Testing: $($testCase.name)" -ForegroundColor Yellow
    Write-Host "   URL: $($testCase.url)" -ForegroundColor Gray
    Write-Host "   Expected Type: $($testCase.expectedType)`n" -ForegroundColor Gray
    
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
        
        # Check page type
        Write-Host "   📊 Page Type:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "page_type") {
            $pageType = $response.page_type
            Write-Host "      Type: $($pageType.type)" -ForegroundColor Gray
            Write-Host "      Confidence: $($pageType.confidence)" -ForegroundColor Gray
            
            if ($pageType.type -eq $testCase.expectedType) {
                Write-Host "      ✅ Correctly detected as $($testCase.expectedType)" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  Expected '$($testCase.expectedType)', got '$($pageType.type)'" -ForegroundColor Yellow
            }
        } else {
            Write-Host "      ❌ page_type missing" -ForegroundColor Red
        }
        
        # Check brand context
        Write-Host "   🏢 Brand Context:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "brand_context") {
            $brandCtx = $response.brand_context
            Write-Host "      Maturity: $($brandCtx.brand_maturity)" -ForegroundColor Gray
            Write-Host "      Analysis Mode: $($brandCtx.analysis_mode)" -ForegroundColor Gray
        }
        
        # Check page intent
        Write-Host "   🎯 Page Intent:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "page_intent") {
            $intent = $response.page_intent
            Write-Host "      Intent: $($intent.intent)" -ForegroundColor Gray
        }
        
        # Check CTA recommendations (should be context-aware)
        Write-Host "   🔘 Primary CTA:" -ForegroundColor Cyan
        if ($response.PSObject.Properties.Name -contains "cta_recommendations") {
            $cta = $response.cta_recommendations
            $primaryLabel = $cta.primary.label
            Write-Host "      $primaryLabel" -ForegroundColor Gray
            Write-Host "      Reason: $($cta.primary.reason)" -ForegroundColor Gray
            
            # Verify CTA is appropriate for page type
            $isAppropriate = $false
            switch ($pageType.type) {
                "ecommerce_product" {
                    $isAppropriate = $primaryLabel -like "*Cart*" -or $primaryLabel -like "*Buy*"
                }
                "saas_pricing" {
                    $isAppropriate = $primaryLabel -like "*Trial*" -or $primaryLabel -like "*Sales*"
                }
                "local_service" {
                    $isAppropriate = $primaryLabel -like "*Call*" -or $primaryLabel -like "*Appointment*" -or $primaryLabel -like "*Book*"
                }
                default {
                    $isAppropriate = $true  # Unknown type, can't verify
                }
            }
            
            if ($isAppropriate) {
                Write-Host "      ✅ CTA is appropriate for page type" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  CTA may not be optimal for this page type" -ForegroundColor Yellow
            }
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

Write-Host "`n🎉 Page type detection test completed!" -ForegroundColor Green
Write-Host "Page types should be correctly detected and CTAs should be context-aware.`n" -ForegroundColor Green




