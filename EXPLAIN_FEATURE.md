# ویژگی Explain (تبدیل به زبان انسان)

## خلاصه
قابلیت جدید اضافه شده که خروجی مغز تصمیم‌گیری را به صورت خودکار به زبان انسان و قابل فهم تبدیل می‌کند.

## نحوه استفاده

### در Backend API

**Endpoint:** `POST /analyze-url?explain=true`

**مثال:**
```bash
curl -X POST "http://127.0.0.1:8000/analyze-url?explain=true" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://nimasaraeian.com/"}'
```

**پاسخ:**
```json
{
  "analysisStatus": "ok",
  "brain": { ... },  // خروجی اصلی مغز (بدون تغییر)
  "explanation": {
    "analysisStatus": "ok",
    "summary": "6-8 خط خلاصه قابل فهم",
    "why_users_hesitate": "توضیح 2-4 جمله‌ای",
    "top_actions": [
      {
        "title": "عنوان اقدام",
        "why": "چرا این اقدام مهم است",
        "how": "چگونه پیاده‌سازی شود",
        "example_copy": "مثال متن/کپی"
      }
    ],
    "risk_reversal_copy": "متن تضمین/اطمینان",
    "disclaimer": "Based on detected signals; validate with analytics."
  },
  "hasExplanation": true
}
```

### در Frontend (Next.js)

**به‌روزرسانی درخواست:**
```typescript
// قبل:
const response = await fetch(`${API_BASE}/analyze-url`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ url: url })
});

// بعد:
const response = await fetch(`${API_BASE}/analyze-url?explain=true`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ url: url })
});
```

**استفاده از explanation:**
```typescript
const data = await response.json();

if (data.hasExplanation && data.explanation) {
  // نمایش توضیحات قابل فهم
  setSummary(data.explanation.summary);
  setWhyUsersHesitate(data.explanation.why_users_hesitate);
  setTopActions(data.explanation.top_actions);
  setRiskReversalCopy(data.explanation.risk_reversal_copy);
} else {
  // Fallback به خروجی اصلی مغز
  // ...
}
```

## نکات مهم

1. **مغز تصمیم نمی‌گیرد:** OpenAI فقط خروجی مغز را به زبان انسان تبدیل می‌کند. تصمیم‌گیری همچنان توسط مغز انجام می‌شود.

2. **اگر explanation fail شود:** درخواست همچنان موفق است و `hasExplanation: false` برمی‌گردد. خروجی اصلی مغز در `brain` موجود است.

3. **نیاز به OPENAI_API_KEY:** برای استفاده از این قابلیت، باید `OPENAI_API_KEY` در فایل `.env` تنظیم شده باشد.

4. **زمان پاسخ:** اضافه کردن `explain=true` حدود 5-10 ثانیه به زمان پاسخ اضافه می‌کند (بسته به سرعت OpenAI API).

## تنظیمات

- **Model:** از `OPENAI_EXPLAIN_MODEL` در `.env` استفاده می‌شود (پیش‌فرض: `gpt-4o-mini`)
- **Temperature:** 0.3 (برای توضیحات ثابت و قابل اعتماد)
- **Audience:** پیش‌فرض `marketer` (می‌تواند در آینده به query param اضافه شود)
- **Language:** پیش‌فرض `en` (می‌تواند در آینده به query param اضافه شود)

## مثال کامل Frontend

```typescript
async function analyzeUrl(url: string) {
  try {
    const response = await fetch(
      `${API_BASE}/analyze-url?explain=true`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    // اگر explanation موجود باشد، از آن استفاده کن
    if (data.hasExplanation && data.explanation) {
      return {
        diagnosis: data.brain,  // خروجی اصلی مغز
        explanation: data.explanation,  // توضیحات قابل فهم
        visualTrust: data.visualTrust,
        features: data.features
      };
    } else {
      // Fallback: از خروجی اصلی مغز استفاده کن
      return {
        diagnosis: data.brain,
        explanation: null,
        explanationError: data.explanationError,
        visualTrust: data.visualTrust,
        features: data.features
      };
    }
  } catch (error) {
    console.error("Analysis failed:", error);
    throw error;
  }
}
```



















