# تست رسمی PowerShell برای endpoint /api/analyze/url-human
# این روش ۱۰۰٪ با PowerShell سازگار است و هیچ وقت JSON خراب نمی‌فرستد

Write-Host "`n=== تست Endpoint /api/analyze/url-human ===" -ForegroundColor Cyan
Write-Host ""

# ساخت body با استفاده از ConvertTo-Json (روش استاندارد PowerShell)
$body = @{
  url    = "https://nimasaraeian.com/"
  goal   = "leads"
  locale = "fa"
} | ConvertTo-Json

Write-Host "📤 درخواست ارسالی:" -ForegroundColor Yellow
Write-Host $body
Write-Host ""

try {
    # ارسال درخواست با Invoke-RestMethod (روش استاندارد)
    $response = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/api/analyze/url-human" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -ErrorAction Stop

    Write-Host "✅ پاسخ موفقیت‌آمیز دریافت شد!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 خلاصه پاسخ:" -ForegroundColor Cyan
    Write-Host "  Status: $($response.analysisStatus)"
    Write-Host "  URL: $($response.summary.url)"
    Write-Host "  Goal: $($response.summary.goal)"
    Write-Host "  Headlines: $($response.summary.headlines_count)"
    Write-Host "  CTAs: $($response.summary.ctas_count)"
    Write-Host "  Issues: $($response.summary.issues_count)"
    Write-Host ""
    
    # نمایش گزارش انسانی (اگر موجود باشد)
    if ($response.human_report) {
        Write-Host "📝 گزارش انسانی:" -ForegroundColor Cyan
        Write-Host $response.human_report
        Write-Host ""
    }
    
} catch {
    Write-Host "❌ خطا در ارسال درخواست:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    # اگر پاسخ خطا از سرور آمده باشد
    if ($_.ErrorDetails.Message) {
        Write-Host "`n📋 جزئیات خطا از سرور:" -ForegroundColor Yellow
        try {
            $errorJson = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Host "  Error Type: $($errorJson.error_type)" -ForegroundColor Yellow
            Write-Host "  Message: $($errorJson.message)" -ForegroundColor Yellow
            if ($errorJson.details) {
                Write-Host "  Details: $($errorJson.details)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host $_.ErrorDetails.Message -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    exit 1
}

Write-Host "=== تست تکمیل شد ===" -ForegroundColor Cyan
Write-Host ""















