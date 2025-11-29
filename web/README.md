# AI Marketing Operating System - Frontend

این یک رابط کاربری مدرن برای سیستم AI Marketing Operating System است که با API backend ارتباط برقرار می‌کند.

## ویژگی‌ها

- ✅ **5 ماژول اصلی:**
  - Behavioral DeepScan
  - Market & Trend Intelligence
  - AI Content Engine
  - Conversion & Funnel Architecture
  - AI Automation System

- ✅ **UI/UX مدرن:**
  - طراحی Responsive
  - انیمیشن‌های نرم
  - Modal windows
  - Loading states

- ✅ **ادغام با API:**
  - ارتباط با `/api/brain` endpoint
  - نمایش نتایج با Quality Score
  - دانلود نتایج

## نحوه استفاده

### 1. راه‌اندازی Backend

```bash
# در terminal جداگانه
cd C:\Users\USER\Desktop\tensorflow-nima
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. باز کردن Frontend

```bash
# فایل index.html را در مرورگر باز کنید
# یا با یک local server:
cd web
python -m http.server 8080
# سپس به http://localhost:8080 بروید
```

### 3. استفاده

1. روی دکمه "Explore Modules" کلیک کنید
2. یکی از 5 ماژول را انتخاب کنید
3. فرم را پر کنید
4. روی "Analyze with AI" کلیک کنید
5. نتایج را مشاهده کنید

## تنظیمات API

در فایل `app.js` می‌توانید URL API را تغییر دهید:

```javascript
// برای local development
const API_BASE_URL = 'http://127.0.0.1:8000';

// برای production
const API_BASE_URL = 'https://api.nimasaraeian.com';
```

## ساختار فایل‌ها

```
web/
├── index.html      # صفحه اصلی
├── styles.css      # استایل‌ها
├── app.js          # منطق JavaScript
└── README.md       # این فایل
```

## ویژگی‌های UI

- **Hero Section:** معرفی سیستم
- **Why Section:** توضیح مزایا
- **Modules Section:** 5 ماژول اصلی
- **Modal Forms:** فرم‌های ورودی
- **Results Display:** نمایش نتایج AI
- **Quality Score:** نمایش کیفیت پاسخ

## مراحل بعدی

- [ ] اضافه کردن Authentication
- [ ] ذخیره نتایج در Database
- [ ] اضافه کردن History
- [ ] Export به PDF
- [ ] Integration با Selphlyze و Contlyze

## نکات

- مطمئن شوید CORS در backend فعال است
- برای production، API URL را تغییر دهید
- می‌توانید استایل‌ها را سفارشی کنید



