# راهنمای هماهنگی Frontend-Backend

## مشکل
وقتی Frontend و Backend در دو Cursor جداگانه توسعه می‌یابند، هماهنگی بین ساختار داده‌ها مشکل می‌شود.

## راه‌حل: API Contract

### 1. استفاده از Shared Types

#### در Backend (Python):
```python
# api/models/psychology_models.py
from pydantic import BaseModel, Field
from typing import List, Optional

class PsychologyAnalysisResult(BaseModel):
    """Output schema - این schema باید با Frontend هماهنگ باشد"""
    analysis: AnalysisDict
    overall: OverallDict
    # ...
```

#### در Frontend (JavaScript):
```javascript
// web/types.js
/**
 * @typedef {Object} PsychologyAnalysisResult
 * @property {PsychologyAnalysis} analysis
 * @property {OverallSummary} overall
 */
```

### 2. استفاده از Script برای Generate Types

```bash
# در Backend Cursor:
python scripts/generate-types.py

# این script:
# 1. Pydantic models را می‌خواند
# 2. TypeScript/JavaScript types تولید می‌کند
# 3. در web/types-generated.js ذخیره می‌کند
```

### 3. استفاده از JSON Schema

فایل `shared/api-types.json` ساختار کامل API را تعریف می‌کند.

هر دو طرف باید از این فایل استفاده کنند:
- Backend: برای validation
- Frontend: برای type checking

### 4. Workflow پیشنهادی

#### هنگام تغییر API:

1. **در Backend Cursor:**
   ```bash
   # 1. تغییر Pydantic model
   # 2. Generate types
   python scripts/generate-types.py
   # 3. Commit changes
   git add api/models/ web/types-generated.js
   git commit -m "Update API: Add new field to PsychologyAnalysisResult"
   ```

2. **در Frontend Cursor:**
   ```bash
   # 1. Pull latest changes
   git pull
   # 2. بررسی types-generated.js
   # 3. استفاده از types جدید در کد
   ```

### 5. Validation در هر دو طرف

#### Backend:
```python
# استفاده از Pydantic برای validation
result = PsychologyAnalysisResult(**data)
# اگر ساختار اشتباه باشد، خطا می‌دهد
```

#### Frontend:
```javascript
// استفاده از types برای type checking
/**
 * @param {PsychologyAnalysisResult} result
 */
function showResults(result) {
    // IDE می‌تواند autocomplete و type checking انجام دهد
    const score = result.analysis.cognitive_friction.score;
}
```

### 6. Testing

```bash
# Test که API contract درست است
python scripts/test-api-contract.py
```

### 7. Documentation

هر تغییر در API باید:
1. در `shared/api-types.json` ثبت شود
2. در `web/types-generated.js` generate شود
3. در commit message توضیح داده شود

## نکات مهم

1. **هرگز مستقیماً types-generated.js را edit نکنید**
   - این فایل auto-generated است
   - تغییرات را در Pydantic models انجام دهید

2. **همیشه قبل از commit، types را generate کنید**
   ```bash
   python scripts/generate-types.py
   git add web/types-generated.js
   ```

3. **از shared/api-types.json به عنوان source of truth استفاده کنید**
   - این فایل ساختار کامل API را تعریف می‌کند
   - هر دو طرف باید از این فایل استفاده کنند

4. **در commit messages توضیح دهید**
   ```
   Update API: Add visual_trust field to PsychologyAnalysisResult
   
   - Added visual_trust field to overall summary
   - Updated types-generated.js
   - Updated shared/api-types.json
   ```

## Troubleshooting

### مشکل: Types در Frontend outdated هستند
```bash
# Solution: Generate types دوباره
python scripts/generate-types.py
```

### مشکل: API response با types همخوانی ندارد
```bash
# Solution: بررسی Pydantic model
# مطمئن شوید که model درست است
python -c "from api.psychology_engine import PsychologyAnalysisResult; print(PsychologyAnalysisResult.model_json_schema())"
```

### مشکل: Frontend نمی‌تواند types را بخواند
```bash
# Solution: بررسی که types.js در index.html include شده
# <script src="types.js"></script>
```

