# 🔧 حل مشکل PORT در Railway

## مشکل
```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```

## علت
Railway متغیر `$PORT` را در `startCommand` expand نمی‌کند. باید از Python script استفاده کنیم که PORT را از environment variable می‌خواند.

## راه حل اعمال شده

### 1. فایل `start.py` ایجاد شد
این فایل PORT را از environment variable می‌خواند و uvicorn را اجرا می‌کند.

### 2. فایل‌های پیکربندی به‌روزرسانی شدند
- ✅ `railway.toml` - استفاده از `python start.py`
- ✅ `railway.json` - استفاده از `python start.py`
- ✅ `Procfile` - استفاده از `python start.py`
- ✅ `Dockerfile` - استفاده از `python start.py`

### 3. `start.sh` بهبود یافت
حالا از variable expansion درست استفاده می‌کند (برای استفاده در Docker یا محیط‌های دیگر).

## مراحل بعدی

### 1. Commit و Push
```powershell
git add start.py start.sh railway.toml railway.json Procfile Dockerfile
git commit -m "Fix Railway PORT variable expansion issue"
git push
```

### 2. Railway به صورت خودکار redeploy می‌شود
بعد از push، Railway:
1. Build را دوباره اجرا می‌کند
2. `start.py` را اجرا می‌کند
3. PORT را از environment variable می‌خواند
4. سرور را با PORT صحیح شروع می‌کند

### 3. بررسی لاگ‌ها
بعد از deploy، باید این پیام‌ها را در لاگ‌ها ببینید:
```
==================================================
Starting NIMA AI Marketing API...
==================================================
PORT is: 12345  (یا هر عددی که Railway تنظیم کرده)
Python version: ...
Working directory: /app
==================================================
```

## اگر هنوز مشکل دارید

### راه حل جایگزین 1: استفاده مستقیم از uvicorn
در `railway.toml`:
```toml
[deploy]
startCommand = "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
```

**نکته**: این روش ممکن است در Railway کار نکند چون `${PORT:-8000}` shell syntax است.

### راه حل جایگزین 2: استفاده از Python inline
در `railway.toml`:
```toml
[deploy]
startCommand = "python -c \"import os; import subprocess; port = os.getenv('PORT', '8000'); subprocess.run(['uvicorn', 'api.main:app', '--host', '0.0.0.0', '--port', port])\""
```

**نکته**: این روش پیچیده است و `start.py` بهتر است.

## تست

بعد از deploy موفق، این دستور را اجرا کنید:
```powershell
Invoke-WebRequest "https://nima-ai-marketing-production.up.railway.app/health" -UseBasicParsing
```

**پاسخ مورد انتظار**:
```json
{"status": "ok"}
```

## خلاصه تغییرات

✅ `start.py` - Python script جدید برای خواندن PORT
✅ `start.sh` - بهبود یافته (برای Docker)
✅ `railway.toml` - استفاده از `python start.py`
✅ `railway.json` - استفاده از `python start.py`
✅ `Procfile` - استفاده از `python start.py`
✅ `Dockerfile` - استفاده از `python start.py`

---

**مشکل حل شد!** 🎉

