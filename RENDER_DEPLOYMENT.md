# راهنمای Deployment روی Render

## مشکلات رایج و راه‌حل‌ها

### 1. ERR_HTTP2_PROTOCOL_ERROR

**مشکل:** این خطا معمولاً به دلیل timeout یا فایل‌های بزرگ است.

**راه‌حل:**
- ✅ Timeout handling اضافه شده (55 ثانیه)
- ✅ محدودیت اندازه فایل (10MB)
- ✅ استفاده از async executor برای جلوگیری از blocking

### 2. CORS Errors

**مشکل:** Frontend نمی‌تواند به API دسترسی پیدا کند.

**راه‌حل:**
- ✅ Domain Render به CORS اضافه شده: `https://nima-ai-marketing.onrender.com`
- ✅ اگر domain دیگری دارید، به `api/main.py` اضافه کنید

### 3. Timeout Issues

**مشکل:** Render معمولاً timeout 60 ثانیه دارد.

**راه‌حل:**
- ✅ Timeout 55 ثانیه تنظیم شده
- ✅ استفاده از `asyncio.wait_for` برای مدیریت timeout
- ✅ در `render.yaml` تنظیم `--timeout-keep-alive 75`

## تنظیمات Render

### 1. Environment Variables

در Render Dashboard، این متغیرها را تنظیم کنید:

```
OPENAI_API_KEY=sk-proj-...
PYTHON_VERSION=3.10.14
```

### 2. Build Command

```
pip install -r requirements.txt
```

### 3. Start Command

```
uvicorn api.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 75
```

### 4. Health Check

```
/health
```

## بررسی مشکلات

### لاگ‌ها را چک کنید

در Render Dashboard → Logs:
- خطاهای `image_trust` را جستجو کنید
- بررسی کنید که مدل TensorFlow لود می‌شود
- بررسی timeout errors

### تست Endpoint

```bash
curl -X POST https://nima-ai-marketing.onrender.com/api/analyze/image-trust \
  -F "file=@test_image.jpg"
```

## نکات مهم

1. **Memory Limits:** Render Starter plan محدودیت memory دارد. اگر مدل TensorFlow خیلی بزرگ است، ممکن است مشکل داشته باشید.

2. **Cold Start:** اولین درخواست ممکن است کند باشد چون مدل باید لود شود.

3. **File Size:** حداکثر 10MB برای فایل‌های تصویری.

4. **Timeout:** اگر پردازش بیشتر از 55 ثانیه طول بکشد، timeout می‌شود.

## Troubleshooting

### اگر مدل لود نمی‌شود:

1. بررسی کنید که `models/visual_trust_model.keras` در repository است
2. بررسی کنید که فایل در build شامل می‌شود
3. بررسی لاگ‌ها برای خطاهای FileNotFoundError

### اگر CORS error می‌گیرید:

1. بررسی کنید که domain در `api/main.py` اضافه شده
2. بررسی کنید که `allow_origins` شامل domain شماست
3. بررسی کنید که `allow_credentials=True` است

### اگر timeout می‌گیرید:

1. سعی کنید با تصویر کوچکتر تست کنید
2. بررسی کنید که مدل در cache است (اولین بار کندتر است)
3. بررسی memory usage در Render Dashboard

