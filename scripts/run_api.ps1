# اسکریپت برای راه‌اندازی سرور FastAPI
# این اسکریپت محیط مجازی را فعال می‌کند و سرور را اجرا می‌کند

Write-Host "`n=== راه‌اندازی سرور FastAPI ===" -ForegroundColor Cyan
Write-Host ""

# فعال کردن محیط مجازی
$venvPath = "N:\nima-ai-marketing\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "✅ فعال کردن محیط مجازی..." -ForegroundColor Green
    & $venvPath
} else {
    Write-Host "⚠️  محیط مجازی پیدا نشد: $venvPath" -ForegroundColor Yellow
    Write-Host "   ادامه با Python سیستم..." -ForegroundColor Yellow
}

# تنظیم متغیرهای محیطی (اختیاری - می‌تواند از .env لود شود)
# $env:OPENAI_MODEL = "gpt-4o-mini"
# $env:OPENAI_API_KEY = "PUT_YOUR_NEW_KEY_HERE"

Write-Host ""
Write-Host "🚀 راه‌اندازی سرور روی http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   برای توقف: Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# اجرای سرور
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload















