# راهنمای عیب‌یابی Render - خطای 500

## مشکل: خطای 500 در `/api/analyze/image-trust`

### مراحل عیب‌یابی

#### 1. بررسی Health Check Endpoint

اول endpoint health check را تست کنید:

```bash
curl https://nima-ai-marketing.onrender.com/api/analyze/image-trust/health
```

این endpoint باید وضعیت مدل را نشان دهد:
- ✅ اگر `status: "healthy"` باشد، مدل در دسترس است
- ❌ اگر `status: "error"` باشد، مشکل را در `message` می‌بینید

#### 2. بررسی لاگ‌های Render

در Render Dashboard → Logs:
- جستجو کنید: `image_trust`
- بررسی کنید که آیا مدل لود می‌شود یا نه
- خطاهای `FileNotFoundError` یا `RuntimeError` را بررسی کنید

#### 3. مشکلات احتمالی

##### مشکل 1: مدل لود نمی‌شود

**علائم:**
- خطای `FileNotFoundError` در لاگ‌ها
- خطای `Model not found` در health check

**راه‌حل:**
1. بررسی کنید که `models/visual_trust_model.keras` در repository commit شده است
2. بررسی کنید که فایل در build شامل می‌شود
3. بررسی path در لاگ‌ها

##### مشکل 2: Memory Limit

**علائم:**
- خطای `MemoryError` یا `Killed` در لاگ‌ها
- مدل لود می‌شود اما درخواست‌ها fail می‌شوند

**راه‌حل:**
1. Plan را به Starter یا بالاتر ارتقا دهید
2. سعی کنید مدل را کوچک‌تر کنید
3. از model quantization استفاده کنید

##### مشکل 3: TensorFlow Issues

**علائم:**
- خطای `ImportError` یا `ModuleNotFoundError`
- خطای `CUDA` یا `GPU` related

**راه‌حل:**
1. بررسی کنید که `tensorflow` در `requirements.txt` است
2. بررسی کنید که version TensorFlow با Python version سازگار است
3. اگر از GPU استفاده می‌کنید، مطمئن شوید که Render از GPU پشتیبانی می‌کند

##### مشکل 4: Timeout

**علائم:**
- خطای 504 (Gateway Timeout)
- درخواست‌ها timeout می‌شوند

**راه‌حل:**
1. Timeout 55 ثانیه تنظیم شده است
2. سعی کنید با تصویر کوچکتر تست کنید
3. بررسی کنید که مدل در cache است (اولین بار کندتر است)

#### 4. تست محلی

قبل از deploy، محلی تست کنید:

```bash
# Start server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Test health check
curl http://localhost:8000/api/analyze/image-trust/health

# Test endpoint
curl -X POST http://localhost:8000/api/analyze/image-trust \
  -F "file=@test_image.jpg"
```

#### 5. بررسی Environment Variables

در Render Dashboard، بررسی کنید:
- `OPENAI_API_KEY` تنظیم شده است (اگر استفاده می‌کنید)
- `PYTHON_VERSION` تنظیم شده است (3.10.14)

#### 6. بررسی Build Logs

در Render Dashboard → Build Logs:
- بررسی کنید که build موفق است
- بررسی کنید که `models/visual_trust_model.keras` در build شامل می‌شود
- بررسی خطاهای pip install

## راه‌حل‌های پیشنهادی

### اگر مدل خیلی بزرگ است:

1. **Model Quantization:**
```python
# در training script
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()
```

2. **Lazy Loading:** ✅ قبلاً پیاده‌سازی شده

3. **Model Caching:** ✅ قبلاً پیاده‌سازی شده

### اگر Memory مشکل دارد:

1. **Upgrade Plan:** به Starter یا بالاتر
2. **Reduce Batch Size:** در predict استفاده کنید
3. **Clear Cache:** بعد از هر درخواست cache را clear کنید

## لاگ‌های مفید

برای debugging، این لاگ‌ها را بررسی کنید:

```python
# در Render Logs جستجو کنید:
- "Loading visual trust model"
- "Visual trust model loaded"
- "Image trust analysis completed"
- "ERROR" یا "Exception"
```

## تماس با Support

اگر مشکل حل نشد:
1. لاگ‌های کامل را کپی کنید
2. نتیجه health check را کپی کنید
3. Build logs را بررسی کنید
4. با Render support تماس بگیرید


