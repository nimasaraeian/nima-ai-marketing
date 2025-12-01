# راهنمای هماهنگی Frontend-Backend

## 🎯 مشکل
وقتی Frontend و Backend در دو Cursor جداگانه کار می‌کنید، هماهنگی بین ساختار داده‌ها مشکل می‌شود.

## ✅ راه‌حل: سیستم هماهنگی خودکار

### ساختار فایل‌ها

```
nima-ai-marketing/
├── shared/
│   └── api-types.json          # Source of Truth - ساختار کامل API
├── web/
│   ├── types.js                # Types دستی (JSDoc)
│   └── types-generated.js      # Types خودکار (از Pydantic)
├── scripts/
│   ├── generate-types.py       # Script برای generate types
│   └── sync-api-contract.md    # راهنمای کامل
└── api/
    └── models/                 # Pydantic models (Backend)
```

---

## 🚀 استفاده سریع

### 1. در Backend Cursor (وقتی API را تغییر می‌دهید):

```bash
# 1. تغییر Pydantic model در api/psychology_engine.py
# 2. Generate types
python scripts/generate-types.py

# 3. Commit
git add api/ web/types-generated.js shared/api-types.json
git commit -m "Update API: Add new field"
```

### 2. در Frontend Cursor (وقتی types را می‌خواهید):

```bash
# 1. Pull latest changes
git pull

# 2. بررسی types-generated.js
# 3. استفاده در کد JavaScript
```

---

## 📋 Workflow کامل

### مرحله 1: تغییر API در Backend

```python
# api/psychology_engine.py
class PsychologyAnalysisResult(BaseModel):
    analysis: AnalysisDict
    overall: OverallDict
    new_field: str = Field(..., description="New field")  # ← تغییر جدید
```

### مرحله 2: Generate Types

```bash
python scripts/generate-types.py
```

این script:
- ✅ Pydantic models را می‌خواند
- ✅ TypeScript/JavaScript types تولید می‌کند
- ✅ در `web/types-generated.js` ذخیره می‌کند

### مرحله 3: استفاده در Frontend

```javascript
// web/app.js
/**
 * @param {PsychologyAnalysisResult} result
 */
function showResults(result) {
    // IDE می‌تواند autocomplete و type checking انجام دهد
    const newField = result.new_field;  // ← IDE می‌داند این فیلد وجود دارد
}
```

---

## 🔧 تنظیمات

### 1. اضافه کردن types.js به HTML

فایل `web/index.html` را باز کنید و مطمئن شوید:

```html
<script src="types.js"></script>
<script src="app.js"></script>
```

### 2. استفاده از Types در JavaScript

```javascript
// در app.js
/**
 * @param {PsychologyAnalysisResult} result
 */
function showVisualProResults(result) {
    // حالا IDE می‌داند ساختار result چیست
    const score = result.analysis.cognitive_friction.score;
    const likelihood = result.overall.decision_likelihood_percentage;
}
```

---

## 📝 قوانین مهم

### ✅ DO:
1. **همیشه قبل از commit، types را generate کنید**
   ```bash
   python scripts/generate-types.py
   git add web/types-generated.js
   ```

2. **از shared/api-types.json به عنوان source of truth استفاده کنید**
   - این فایل ساختار کامل API را تعریف می‌کند

3. **در commit messages توضیح دهید**
   ```
   Update API: Add visual_trust field
   
   - Added visual_trust to PsychologyAnalysisResult
   - Updated types-generated.js
   ```

### ❌ DON'T:
1. **هرگز types-generated.js را مستقیماً edit نکنید**
   - این فایل auto-generated است
   - تغییرات را در Pydantic models انجام دهید

2. **هرگز ساختار API را بدون generate types تغییر ندهید**
   - Frontend نمی‌داند ساختار جدید چیست

---

## 🐛 Troubleshooting

### مشکل: Types در Frontend outdated هستند

```bash
# Solution:
python scripts/generate-types.py
```

### مشکل: API response با types همخوانی ندارد

```bash
# بررسی Pydantic model:
python -c "from api.psychology_engine import PsychologyAnalysisResult; import json; print(json.dumps(PsychologyAnalysisResult.model_json_schema(), indent=2))"
```

### مشکل: Script اجرا نمی‌شود

```bash
# بررسی dependencies:
pip install pydantic

# بررسی path:
python -c "import sys; print(sys.path)"
```

---

## 📚 فایل‌های مهم

### `shared/api-types.json`
- **Source of Truth** برای ساختار API
- JSON Schema format
- هر دو طرف باید از این فایل استفاده کنند

### `web/types.js`
- Types دستی با JSDoc
- برای documentation و IDE support
- می‌توانید مستقیماً edit کنید

### `web/types-generated.js`
- Types خودکار از Pydantic models
- **هرگز مستقیماً edit نکنید**
- با `python scripts/generate-types.py` generate می‌شود

### `scripts/generate-types.py`
- Script برای generate types
- Pydantic models را می‌خواند
- TypeScript/JavaScript types تولید می‌کند

---

## 💡 Tips

1. **استفاده از IDE autocomplete:**
   - با JSDoc types، IDE می‌تواند autocomplete و type checking انجام دهد

2. **Validation در Backend:**
   ```python
   # Pydantic خودکار validation می‌کند
   result = PsychologyAnalysisResult(**data)  # اگر ساختار اشتباه باشد، خطا می‌دهد
   ```

3. **Testing:**
   ```bash
   # Test که API contract درست است
   python -c "from api.psychology_engine import PsychologyAnalysisResult; print('OK')"
   ```

---

## 🎓 مثال کامل

### 1. تغییر API در Backend:

```python
# api/psychology_engine.py
class PsychologyAnalysisResult(BaseModel):
    analysis: AnalysisDict
    overall: OverallDict
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())  # ← جدید
```

### 2. Generate Types:

```bash
python scripts/generate-types.py
# Output: ✅ Generated type: PsychologyAnalysisResult
#         ✅ Types written to: web/types-generated.js
```

### 3. استفاده در Frontend:

```javascript
// web/app.js
/**
 * @param {PsychologyAnalysisResult} result
 */
function showResults(result) {
    console.log(result.timestamp);  // ← IDE می‌داند این فیلد وجود دارد
}
```

### 4. Commit:

```bash
git add api/psychology_engine.py web/types-generated.js
git commit -m "Add timestamp to PsychologyAnalysisResult"
```

---

## ✅ Checklist

قبل از commit، مطمئن شوید:

- [ ] Pydantic model تغییر کرده
- [ ] `python scripts/generate-types.py` اجرا شده
- [ ] `web/types-generated.js` updated شده
- [ ] Frontend از types جدید استفاده می‌کند
- [ ] Commit message توضیح داده که چه تغییراتی انجام شده

---

**سوال دارید؟** فایل `scripts/sync-api-contract.md` را ببینید برای راهنمای کامل‌تر.

