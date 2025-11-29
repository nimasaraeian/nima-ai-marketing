# راهنمای تنظیم API Key

## مشکل فعلی

API key موجود quota error می‌دهد، در حالی که داشبورد نشان می‌دهد:
- بودجه: $50
- مصرف: $2.55
- باقیمانده: $47.45

## علت احتمالی

API key ممکن است به پروژه دیگری متصل باشد یا نیاز به تنظیمات اضافی داشته باشد.

## راه‌حل

### گزینه 1: ایجاد API Key جدید از داشبورد

1. به داشبورد بروید: https://platform.openai.com/api-keys
2. روی "Create new secret key" کلیک کنید
3. نام مناسب بدهید (مثلاً "Nima AI Brain")
4. API key را کپی کنید
5. در فایل `.env` جایگزین کنید

### گزینه 2: بررسی Project Settings

1. در داشبورد، مطمئن شوید که "Default project" انتخاب شده است
2. به Settings → API Keys بروید
3. بررسی کنید که API key به همان پروژه متصل است

### گزینه 3: استفاده از Organization API Key

اگر Organization دارید:
1. به Organization settings بروید
2. API key مربوط به Organization را استفاده کنید

## پس از تنظیم API Key جدید

1. فایل `.env` را به‌روزرسانی کنید
2. تست کنید: `python api/test_api.py`
3. اگر کار کرد، تست کامل: `python api/test_marketing_framework.py`

## نکات مهم

- API key را در `.gitignore` نگه دارید
- هرگز API key را در کد commit نکنید
- برای production از environment variables استفاده کنید




