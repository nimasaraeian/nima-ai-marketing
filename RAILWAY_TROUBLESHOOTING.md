# 🔧 راهنمای حل مشکلات Railway

این راهنما شامل خطاهای رایج در Railway و راه‌حل‌های آن‌ها است.

---

## 1. Application Failed to Respond (502 Bad Gateway)

### معنای خطا
Railway نمی‌تواند به application شما متصل شود. این معمولاً به این معنی است که:
- Application شروع نشده است
- Application crash کرده است
- Application به PORT صحیح listen نمی‌کند

### چرا این خطا رخ می‌دهد
- ❌ PORT environment variable درست خوانده نمی‌شود
- ❌ Application در حال crash است
- ❌ Start command اشتباه است
- ❌ Dependencies نصب نشده‌اند
- ❌ Application timeout می‌دهد

### راه‌حل

#### ✅ بررسی Start Command
مطمئن شوید که `startCommand` در `railway.toml` درست است:
```toml
[deploy]
startCommand = "python start.py"
```

#### ✅ بررسی PORT
مطمئن شوید که application به PORT صحیح listen می‌کند:
```python
# در start.py
port = os.getenv("PORT", "8000")
```

#### ✅ بررسی لاگ‌ها
در Railway Dashboard → Logs:
- آیا application شروع شده است؟
- آیا خطای import وجود دارد؟
- آیا PORT درست خوانده شده است؟

#### ✅ تست Health Endpoint
```powershell
Invoke-WebRequest "https://your-app.up.railway.app/health" -UseBasicParsing
```

---

## 2. No Start Command Could Be Found

### معنای خطا
Railway نمی‌تواند دستور start را پیدا کند.

### چرا این خطا رخ می‌دهد
- ❌ `startCommand` در `railway.toml` تنظیم نشده
- ❌ `Procfile` وجود ندارد یا اشتباه است
- ❌ `package.json` scripts وجود ندارد (برای Node.js)

### راه‌حل

#### ✅ تنظیم startCommand در railway.toml
```toml
[deploy]
startCommand = "python start.py"
```

#### ✅ یا استفاده از Procfile
```
web: python start.py
```

#### ✅ برای Node.js
```json
{
  "scripts": {
    "start": "node server.js"
  }
}
```

---

## 3. 405 Method Not Allowed

### معنای خطا
Method HTTP درخواست شده برای endpoint مجاز نیست.

### چرا این خطا رخ می‌دهد
- ❌ از GET استفاده می‌کنید اما endpoint فقط POST می‌پذیرد
- ❌ Route درست تعریف نشده است

### راه‌حل

#### ✅ بررسی Route Definition
```python
# در api/main.py
@app.get("/health")  # فقط GET
def health():
    return {"status": "ok"}

@app.post("/api/brain")  # فقط POST
async def brain_endpoint(...):
    ...
```

#### ✅ استفاده از Method صحیح
```powershell
# برای GET
Invoke-WebRequest -Method GET "https://your-app.up.railway.app/health"

# برای POST
Invoke-WebRequest -Method POST "https://your-app.up.railway.app/api/brain" -Body $body
```

---

## 4. Nixpacks Was Unable to Generate a Build Plan

### معنای خطا
Nixpacks نمی‌تواند build plan را برای application شما ایجاد کند.

### چرا این خطا رخ می‌دهد
- ❌ فایل‌های تشخیصی وجود ندارد (requirements.txt, package.json, etc.)
- ❌ Build command اشتباه است
- ❌ Dependencies مشکل دارند

### راه‌حل

#### ✅ برای Python
مطمئن شوید که `requirements.txt` وجود دارد:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
...
```

#### ✅ تنظیم buildCommand در railway.toml
```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt && python -m playwright install chromium"
```

#### ✅ برای Node.js
مطمئن شوید که `package.json` وجود دارد:
```json
{
  "dependencies": {
    "express": "^4.18.0"
  }
}
```

---

## 5. ENOTFOUND redis.railway.internal

### معنای خطا
Application نمی‌تواند به Redis service متصل شود.

### چرا این خطا رخ می‌دهد
- ❌ Redis service در Railway ایجاد نشده
- ❌ Connection string اشتباه است
- ❌ Network issue

### راه‌حل

#### ✅ ایجاد Redis Service در Railway
1. به Railway Dashboard بروید
2. New → Database → Redis
3. Service را به project خود متصل کنید

#### ✅ استفاده از Environment Variables
Railway به صورت خودکار این متغیرها را تنظیم می‌کند:
- `REDIS_URL`
- `REDIS_HOST`
- `REDIS_PORT`

#### ✅ بررسی Connection
```python
import os
redis_url = os.getenv("REDIS_URL")
# استفاده از redis_url
```

---

## 6. PORT Variable Not Found

### معنای خطا
`$PORT` به عنوان literal string استفاده می‌شود نه به عنوان environment variable.

### چرا این خطا رخ می‌دهد
- ❌ Railway متغیر `$PORT` را expand نمی‌کند
- ❌ از shell script استفاده می‌کنید که expand نمی‌شود

### راه‌حل

#### ✅ استفاده از Python Script (پیشنهادی)
```python
# start.py
import os
port = os.getenv("PORT", "8000")
os.execvp("uvicorn", ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", port])
```

#### ✅ تنظیم در railway.toml
```toml
[deploy]
startCommand = "python start.py"
```

---

## 7. Import Errors

### معنای خطا
Python نمی‌تواند module را import کند.

### چرا این خطا رخ می‌دهد
- ❌ Dependencies نصب نشده‌اند
- ❌ Path اشتباه است
- ❌ Module وجود ندارد

### راه‌حل

#### ✅ بررسی requirements.txt
مطمئن شوید که همه dependencies در `requirements.txt` هستند:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
...
```

#### ✅ بررسی Import Paths
```python
# درست
from api.main import app

# اشتباه
from main import app  # اگر در root نیست
```

---

## 8. Build Timeout

### معنای خطا
Build process بیش از حد طول می‌کشد و timeout می‌شود.

### چرا این خطا رخ می‌دهد
- ❌ Dependencies زیادی برای نصب
- ❌ Playwright install طول می‌کشد
- ❌ Network issue

### راه‌حل

#### ✅ بهینه‌سازی Build Command
```toml
[build]
buildCommand = "pip install -r requirements.txt && python -m playwright install chromium --with-deps chromium"
```

#### ✅ استفاده از Cache
Railway به صورت خودکار cache می‌کند، اما می‌توانید:
```toml
[build]
cache = true
```

---

## 9. Health Check Failed

### معنای خطا
Health check endpoint پاسخ نمی‌دهد.

### چرا این خطا رخ می‌دهد
- ❌ Health endpoint وجود ندارد
- ❌ Application شروع نشده
- ❌ Timeout خیلی کوتاه است

### راه‌حل

#### ✅ ایجاد Health Endpoint
```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

#### ✅ تنظیم Health Check در railway.toml
```toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 60
```

---

## 10. CORS Errors

### معنای خطا
Frontend نمی‌تواند به API دسترسی پیدا کند.

### چرا این خطا رخ می‌دهد
- ❌ Origin در لیست مجاز نیست
- ❌ CORS middleware تنظیم نشده

### راه‌حل

#### ✅ اضافه کردن Origin به CORS
```python
origins = [
    "https://your-frontend-domain.com",
    "https://*.up.railway.app",  # برای Railway
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📋 Checklist عمومی

قبل از deploy، این موارد را بررسی کنید:

- [ ] `railway.toml` یا `railway.json` موجود است
- [ ] `startCommand` تنظیم شده است
- [ ] `requirements.txt` (برای Python) یا `package.json` (برای Node.js) موجود است
- [ ] Health endpoint وجود دارد
- [ ] PORT از environment variable خوانده می‌شود
- [ ] CORS برای frontend تنظیم شده
- [ ] Environment variables در Railway Dashboard تنظیم شده‌اند
- [ ] Build command درست است

---

## 🔍 Debugging Tips

### 1. بررسی لاگ‌ها
```powershell
# در Railway Dashboard → Logs
# یا از CLI
railway logs
```

### 2. تست Local
```powershell
# قبل از deploy، local تست کنید
python start.py
# یا
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 3. بررسی Environment Variables
```python
import os
print("PORT:", os.getenv("PORT"))
print("All env vars:", dict(os.environ))
```

### 4. تست Health Endpoint
```powershell
Invoke-WebRequest "https://your-app.up.railway.app/health" -UseBasicParsing
```

---

## 📚 منابع بیشتر

- [Railway Documentation](https://docs.railway.app/)
- [Railway Errors Reference](https://docs.railway.app/reference/errors)
- [Nixpacks Documentation](https://nixpacks.com/)

---

**آخرین به‌روزرسانی**: تمام مشکلات رایج Railway و راه‌حل‌های آن‌ها ✅







