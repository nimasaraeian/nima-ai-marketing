# 🔧 راهنمای استفاده از Endpoint `/analyze-url`

## ❌ خطای "Method Not Allowed"

این خطا معمولاً به این دلایل رخ می‌دهد:

### 1. استفاده از روش HTTP اشتباه
- ✅ **درست:** `POST /analyze-url`
- ❌ **اشتباه:** `GET /analyze-url`

### 2. استفاده از path اشتباه
- ✅ **درست:** `/analyze-url` (بدون `/api/`)
- ❌ **اشتباه:** `/api/analyze-url`

---

## ✅ استفاده صحیح

### با cURL:
```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### با Python (requests):
```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/analyze-url",
    json={"url": "https://example.com"}
)
print(response.json())
```

### با JavaScript (fetch):
```javascript
fetch('http://127.0.0.1:8000/analyze-url', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    url: 'https://example.com'
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### با PowerShell:
```powershell
$body = @{
    url = "https://example.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/analyze-url" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

---

## 📋 پارامترها

### Request Body:
```json
{
  "url": "https://example.com",  // الزامی
  "refresh": false                // اختیاری - برای bypass cache
}
```

### Query Parameters:
- `refresh` (اختیاری): `true` یا `false` - برای bypass cache

مثال:
```
POST /analyze-url?refresh=true
```

---

## 📤 Response Format

```json
{
  "analysisStatus": "ok",
  "inputType": "url",
  "url": "https://example.com",
  "featuresSchemaVersion": "1.0",
  "visualTrust": {
    "analysisStatus": "ok",
    "label": "High",
    "confidence": 0.85,
    "probs": {...}
  },
  "features": {
    "visual": {...},
    "text": {...},
    "meta": {...}
  },
  "brain": {
    "frictionScore": 45,
    "trustScore": 75,
    "clarityScore": 80,
    "decisionProbability": 0.65,
    "keyDecisionBlockers": [...],
    "recommendedQuickWins": [...],
    "recommendedDeepChanges": [...]
  },
  "extractedText": "...",
  "debugScreenshotPath": "...",
  "debugScreenshotBytes": 12345
}
```

---

## 🔍 عیب‌یابی

### خطای 405 (Method Not Allowed)
**علت:** از GET به جای POST استفاده شده
**راه حل:** از `POST` استفاده کنید

### خطای 404 (Not Found)
**علت:** path اشتباه است
**راه حل:** از `/analyze-url` استفاده کنید (نه `/api/analyze-url`)

### خطای 422 (Validation Error)
**علت:** فیلد `url` در body موجود نیست یا خالی است
**راه حل:** مطمئن شوید که `{"url": "..."}` در body موجود است

### خطای Timeout
**علت:** درخواست بیش از 60 ثانیه طول می‌کشد
**راه حل:** 
- timeout را افزایش دهید
- یا از URL ساده‌تر استفاده کنید

---

## 🧪 تست سریع

### با Python:
```python
import requests

# تست ساده
response = requests.post(
    "http://127.0.0.1:8000/analyze-url",
    json={"url": "https://example.com"},
    timeout=60
)

if response.status_code == 200:
    print("✅ موفق!")
    print(response.json())
else:
    print(f"❌ خطا: {response.status_code}")
    print(response.text)
```

### با test script:
```powershell
python test_analyze_url.py https://example.com
```

---

## 📝 نکات مهم

1. ✅ همیشه از **POST** استفاده کنید
2. ✅ path صحیح: `/analyze-url` (بدون `/api/`)
3. ✅ Content-Type: `application/json`
4. ✅ body باید شامل `{"url": "..."}` باشد
5. ⏱️ timeout: حداقل 60 ثانیه (تحلیل ممکن است طول بکشد)
6. 💾 Cache: نتایج برای 30 دقیقه cache می‌شوند
7. 🔄 برای bypass cache: `refresh=true` در query یا body

---

## 🔗 Endpoint های مرتبط

- `GET /health` - بررسی سلامت سرور
- `POST /api/brain/cognitive-friction` - تحلیل Cognitive Friction
- `POST /api/analyze/image-trust` - تحلیل تصویر










