# ✅ Railway URL تنظیم شد

## URL جدید Railway
```
BACKEND_BASE_URL=https://nima-ai-marketing-production-82df.up.railway.app
```

## تغییرات اعمال شده

### 1. CORS Configuration
✅ URL جدید به `api/main.py` اضافه شد:
- `https://nima-ai-marketing-production-82df.up.railway.app`

### 2. CORS برای Railway
✅ Regex برای Railway subdomains فعال است:
- `https://.*\.up\.railway\.app` - تمام Railway subdomains مجاز هستند

## تنظیمات Frontend

### گزینه 1: استفاده از Meta Tag (پیشنهادی)
در فایل HTML (مثلاً `web/index.html`):
```html
<head>
    <meta name="api-base-url" content="https://nima-ai-marketing-production-82df.up.railway.app">
</head>
```

### گزینه 2: استفاده از JavaScript
در فایل `web/app.js` یا قبل از load شدن app:
```javascript
window.API_BASE_URL = 'https://nima-ai-marketing-production-82df.up.railway.app';
```

### گزینه 3: Environment Variable
اگر از build tool استفاده می‌کنید:
```javascript
const API_BASE_URL = process.env.BACKEND_BASE_URL || 'http://127.0.0.1:8000';
```

## تست اتصال

### 1. تست Health Endpoint
```powershell
Invoke-WebRequest "https://nima-ai-marketing-production-82df.up.railway.app/health" -UseBasicParsing
```

**پاسخ مورد انتظار**:
```json
{"status": "ok"}
```

### 2. تست Root Endpoint
```powershell
Invoke-WebRequest "https://nima-ai-marketing-production-82df.up.railway.app/" -UseBasicParsing
```

**پاسخ مورد انتظار**:
```json
{
  "status": "ok",
  "service": "nima-ai-marketing-api",
  "system_prompt_loaded": true,
  "system_prompt_length": 24682,
  "quality_engine_enabled": true
}
```

### 3. تست از Frontend
در Console مرورگر:
```javascript
fetch('https://nima-ai-marketing-production-82df.up.railway.app/health')
  .then(r => r.json())
  .then(console.log);
```

## تنظیمات Environment Variables

### در Railway Dashboard
اگر نیاز به تنظیم `BACKEND_BASE_URL` در Railway دارید:
1. به Railway Dashboard بروید
2. پروژه را انتخاب کنید
3. به بخش **Variables** بروید
4. اضافه کنید:
   ```
   BACKEND_BASE_URL=https://nima-ai-marketing-production-82df.up.railway.app
   ```

**نکته**: این متغیر اختیاری است و فقط برای reference استفاده می‌شود.

## CORS Origins فعلی

در `api/main.py` این origins مجاز هستند:
- ✅ `https://nimasaraeian.com`
- ✅ `https://www.nimasaraeian.com`
- ✅ `https://nima-ai-marketing.onrender.com`
- ✅ `https://nima-ai-marketing-production.up.railway.app` (old)
- ✅ `https://nima-ai-marketing-production-82df.up.railway.app` (current)
- ✅ تمام Railway subdomains (via regex: `https://.*\.up\.railway\.app`)

## مراحل بعدی

1. ✅ CORS تنظیم شد
2. ⏳ Frontend را به‌روزرسانی کنید (اگر نیاز است)
3. ⏳ تست کنید که frontend به backend متصل می‌شود
4. ⏳ اگر CORS error دارید، لاگ‌های browser console را بررسی کنید

## Troubleshooting

### مشکل: CORS Error
**علت**: Origin در لیست مجاز نیست

**راه‌حل**:
1. Origin را به `api/main.py` اضافه کنید
2. یا از Railway regex استفاده کنید (که فعال است)

### مشکل: 502 Bad Gateway
**علت**: Backend در حال اجرا نیست

**راه‌حل**:
1. لاگ‌های Railway را بررسی کنید
2. Health endpoint را تست کنید
3. مطمئن شوید که `start.py` درست اجرا می‌شود

### مشکل: Connection Refused
**علت**: URL اشتباه است یا backend down است

**راه‌حل**:
1. URL را بررسی کنید
2. Health endpoint را تست کنید
3. مطمئن شوید که Railway deployment موفق بوده

---

**آماده استفاده!** 🚀

URL جدید Railway: `https://nima-ai-marketing-production-82df.up.railway.app`










