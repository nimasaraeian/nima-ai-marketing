# بررسی همخوانی Endpointهای Frontend و Backend

## ✅ Endpointهای موجود و درست

| Frontend Endpoint | Backend Endpoint | وضعیت |
|------------------|------------------|-------|
| `/api/brain/decision-engine/report-from-url` | ✅ `/api/brain/decision-engine/report-from-url` | ✅ موجود |
| `/api/brain/decision-engine` | ✅ `/api/brain/decision-engine` | ✅ موجود |
| `/api/brain/cognitive-friction` | ✅ `/api/brain/cognitive-friction` | ✅ موجود |
| `/api/brain` | ✅ `/api/brain` | ✅ موجود |
| `/api/brain/rewrite` | ✅ `/api/brain/rewrite` | ✅ موجود |
| `/api/analyze/image-trust` | ✅ `/api/analyze/image-trust` | ✅ موجود |

## ⚠️ Endpointهای Missing (نیاز به بررسی)

| Frontend Endpoint | Backend Endpoint | وضعیت | توضیحات |
|------------------|------------------|-------|---------|
| `/api/brain/decision-engine-url` | ❌ | ⚠️ Missing | احتمالاً alias برای `/api/brain/decision-engine` با URL |
| `/api/brain/decision-engine-image` | ❌ | ⚠️ Missing | احتمالاً alias برای `/api/brain/decision-engine` با image |
| `/api/brain/decision-diagnosis` | ❌ | ⚠️ Missing | فقط در config برای CTA route استفاده شده |
| `/api/articles` | ❌ | ⚠️ Missing | احتمالاً endpoint جدید یا Next.js API route |
| `/api/ai/persona` | ❌ | ⚠️ Missing | احتمالاً endpoint جدید یا Next.js API route |
| `/api/ai/optimize` | ❌ | ⚠️ Missing | احتمالاً endpoint جدید یا Next.js API route |

## 🔍 توصیه‌ها

### 1. Decision Engine Aliases
اگر frontend از `/api/brain/decision-engine-url` و `/api/brain/decision-engine-image` استفاده می‌کند، باید alias اضافه شود:

```python
# در api/decision_engine.py
@router.post("/decision-engine-url")
async def decision_engine_url_endpoint(input_data: DecisionEngineInput):
    """Alias for decision-engine with URL handling"""
    return await decision_engine_endpoint(input_data)

@router.post("/decision-engine-image")
async def decision_engine_image_endpoint(input_data: DecisionEngineInput):
    """Alias for decision-engine with image handling"""
    return await decision_engine_endpoint(input_data)
```

### 2. Decision Diagnosis
اگر `/api/brain/decision-diagnosis` نیاز است، می‌تواند alias برای `/api/brain/cognitive-friction` باشد یا endpoint جدید.

### 3. Articles, Persona, Optimize
این endpointها احتمالاً:
- Next.js API routes هستند (در `app/api/` یا `pages/api/`)
- یا endpointهای جدیدی هستند که باید اضافه شوند

## ✅ نتیجه‌گیری

**مشکلات اصلی:**
1. ✅ `/api/brain/decision-engine/report-from-url` - درست شده (import fix + human_report)
2. ⚠️ `/api/brain/decision-engine-url` - نیاز به alias
3. ⚠️ `/api/brain/decision-engine-image` - نیاز به alias
4. ⚠️ `/api/brain/decision-diagnosis` - نیاز به بررسی (احتمالاً alias برای cognitive-friction)

**Endpointهای دیگر (articles, persona, optimize):**
- احتمالاً Next.js API routes هستند
- یا باید در backend اضافه شوند

## 🎯 اقدامات پیشنهادی

1. ✅ **انجام شده:** Fix import و اضافه کردن `human_report` به `report-from-url`
2. ⚠️ **نیاز به بررسی:** اضافه کردن alias endpointها برای decision-engine-url و decision-engine-image
3. ⚠️ **نیاز به بررسی:** بررسی اینکه آیا `/api/brain/decision-diagnosis` نیاز است یا نه
4. ℹ️ **اطلاعاتی:** بررسی اینکه articles, persona, optimize در Next.js API routes هستند یا باید در backend اضافه شوند

