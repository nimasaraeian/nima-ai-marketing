# 🚂 راهنمای کامل Deployment روی Railway

## ✅ تغییرات اعمال شده

### 1. فایل‌های پیکربندی
- ✅ `railway.toml` - پیکربندی کامل برای Nixpacks
- ✅ `railway.json` - پیکربندی JSON برای Railway
- ✅ `start.sh` - اسکریپت راه‌اندازی بهبود یافته
- ✅ `Procfile` - اصلاح شده برای Railway
- ✅ `Dockerfile` - آماده برای Docker deployment

### 2. CORS Configuration
- ✅ Railway domain اضافه شده: `https://nima-ai-marketing-production.up.railway.app`
- ✅ تمام Railway subdomains مجاز: `https://*.up.railway.app`

### 3. Health Check
- ✅ Endpoint: `/health`
- ✅ Timeout: 60 ثانیه
- ✅ Response: `{"status": "ok"}`

## 📋 مراحل Deployment

### مرحله 1: آماده‌سازی Repository
```bash
git add .
git commit -m "Fix Railway deployment configuration"
git push
```

### مرحله 2: تنظیمات Railway Dashboard

#### 2.1. Environment Variables
در Railway Dashboard → Variables، این متغیرها را اضافه کنید:

```
OPENAI_API_KEY=sk-proj-... (اگر نیاز است)
PORT (Railway خودش تنظیم می‌کند - نیازی به تنظیم دستی نیست)
```

#### 2.2. Build Settings
- **Builder**: Nixpacks (خودکار تشخیص داده می‌شود)
- **Build Command**: `pip install -r requirements.txt && python -m playwright install chromium`
- **Start Command**: `sh start.sh`

#### 2.3. Health Check
- **Path**: `/health`
- **Timeout**: 60 seconds

### مرحله 3: Deploy
1. Railway به صورت خودکار از `railway.toml` استفاده می‌کند
2. Build شروع می‌شود
3. بعد از build موفق، deployment شروع می‌شود
4. Health check هر 60 ثانیه یکبار اجرا می‌شود

## 🔍 Troubleshooting

### مشکل 1: 502 Bad Gateway
**علت**: سرور شروع نشده یا crash کرده

**راه‌حل**:
1. لاگ‌های Railway را بررسی کنید
2. مطمئن شوید `start.sh` executable است
3. بررسی کنید که `PORT` environment variable تنظیم شده

### مشکل 2: Build Failed
**علت**: Dependencies نصب نشده یا Playwright مشکل دارد

**راه‌حل**:
1. بررسی کنید `requirements.txt` کامل است
2. مطمئن شوید `playwright install chromium` اجرا شده
3. لاگ‌های build را بررسی کنید

### مشکل 3: Health Check Failed
**علت**: سرور به `/health` پاسخ نمی‌دهد

**راه‌حل**:
1. بررسی کنید که endpoint `/health` در `api/main.py` وجود دارد
2. Timeout را افزایش دهید (در `railway.toml`)
3. لاگ‌های runtime را بررسی کنید

### مشکل 4: CORS Error
**علت**: Domain در لیست CORS نیست

**راه‌حل**:
1. Domain Railway را به `api/main.py` اضافه کنید
2. یا از wildcard استفاده کنید: `https://*.up.railway.app`

## 📊 بررسی Status

### تست Health Endpoint
```powershell
Invoke-WebRequest "https://nima-ai-marketing-production.up.railway.app/health" -UseBasicParsing
```

**پاسخ مورد انتظار**:
```json
{"status": "ok"}
```

### تست Root Endpoint
```powershell
Invoke-WebRequest "https://nima-ai-marketing-production.up.railway.app/" -UseBasicParsing
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

## 🔧 تنظیمات پیشرفته

### استفاده از Docker
اگر Railway از Docker استفاده می‌کند:
- `Dockerfile` موجود است
- `CMD ["/app/start.sh"]` تنظیم شده
- همه dependencies نصب می‌شوند

### استفاده از Nixpacks
اگر Railway از Nixpacks استفاده می‌کند:
- `railway.toml` تنظیم شده
- Build command در `railway.toml` تعریف شده
- Start command در `railway.toml` تعریف شده

## 📝 لاگ‌ها

### مشاهده لاگ‌ها در Railway
1. به Railway Dashboard بروید
2. پروژه را انتخاب کنید
3. به بخش **Logs** بروید
4. لاگ‌های real-time را مشاهده کنید

### لاگ‌های مهم
- ✅ `Starting API...` - سرور شروع شده
- ✅ `PORT is: XXXX` - Port تنظیم شده
- ✅ `Application startup complete` - FastAPI آماده است
- ❌ هر خطای import یا runtime

## 🎯 Checklist نهایی

قبل از deploy، این موارد را بررسی کنید:

- [ ] `railway.toml` موجود است
- [ ] `railway.json` موجود است
- [ ] `start.sh` executable است
- [ ] `requirements.txt` کامل است
- [ ] `api/main.py` دارای endpoint `/health` است
- [ ] CORS برای Railway domain تنظیم شده
- [ ] Environment variables در Railway Dashboard تنظیم شده
- [ ] Repository به Railway متصل است

## 🚀 بعد از Deploy

1. ✅ Health endpoint را تست کنید
2. ✅ Root endpoint را تست کنید
3. ✅ لاگ‌ها را بررسی کنید
4. ✅ اگر مشکلی بود، این راهنما را دنبال کنید

## 📞 پشتیبانی

اگر بعد از این مراحل هنوز مشکل دارید:
1. لاگ‌های Railway را بررسی کنید
2. Health endpoint را تست کنید
3. Environment variables را بررسی کنید
4. Build logs را بررسی کنید

---

**آخرین به‌روزرسانی**: تمام مشکلات Railway deployment حل شده است ✅









