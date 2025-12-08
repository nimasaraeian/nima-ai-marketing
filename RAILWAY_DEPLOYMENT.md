# راهنمای Deployment روی Railway

## 📋 تنظیمات Railway

### 1. Environment Variables

در Railway Dashboard → Variables، این متغیرها را اضافه کنید:

```
OPENAI_API_KEY=sk-proj-...
PYTHON_VERSION=3.10.14
```

### 2. فایل‌های مورد نیاز

Railway به صورت خودکار این فایل‌ها را تشخیص می‌دهد:
- ✅ `requirements.txt` - وابستگی‌های Python
- ✅ `Procfile` - دستور start (اختیاری، Railway خودش تشخیص می‌دهد)
- ✅ `runtime.txt` - نسخه Python (اختیاری)

### 3. Start Command

Railway به صورت خودکار از `Procfile` استفاده می‌کند:
```
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 75
```

یا می‌توانید در Railway Dashboard → Settings → Deploy → Start Command تنظیم کنید:
```
uvicorn api.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 75
```

### 4. Build Command

Railway به صورت خودکار `pip install -r requirements.txt` را اجرا می‌کند.

اگر نیاز به build command سفارشی دارید:
```
python -m pip install --upgrade pip && pip install -r requirements.txt
```

## 🚀 مراحل Deployment

### روش 1: از GitHub (پیشنهادی)

1. به https://railway.app بروید
2. New Project → Deploy from GitHub repo
3. Repository خود را انتخاب کنید
4. Railway به صورت خودکار:
   - `requirements.txt` را پیدا می‌کند
   - Python environment را setup می‌کند
   - Dependencies را نصب می‌کند
   - از `Procfile` برای start استفاده می‌کند

### روش 2: از Railway CLI

```bash
# نصب Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

## 🔧 تنظیمات اضافی

### Health Check

Railway به صورت خودکار health check را انجام می‌دهد. مطمئن شوید endpoint `/health` در `api/main.py` وجود دارد.

### Custom Domain

1. در Railway Dashboard → Settings → Domains
2. Add Custom Domain
3. Domain خود را وارد کنید

### CORS Configuration

مطمئن شوید که در `api/main.py`، domain Railway به CORS اضافه شده:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.railway.app",
        "https://nimasaraeian.com",
        "https://www.nimasaraeian.com",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🐛 Troubleshooting

### Build Failed - "Could not open requirements file: api/requirements.txt"

**مشکل:** Railway به دنبال `api/requirements.txt` می‌گردد اما پیدا نمی‌کند.

**راه‌حل:**

1. **بررسی Build Command در Railway Dashboard:**
   - به Railway Dashboard → Service → Settings → Build & Deploy بروید
   - در بخش "Build Command"، مطمئن شوید که این دستور است:
     ```
     pip install -r requirements.txt
     ```
   - اگر `api/requirements.txt` نوشته شده، آن را به `requirements.txt` تغییر دهید

2. **بررسی Root Directory:**
   - در Railway Dashboard → Service → Settings → Source
   - مطمئن شوید که "Root Directory" خالی است یا روی `/` تنظیم شده
   - اگر روی `api/` تنظیم شده، آن را خالی کنید

3. **استفاده از railway.json:**
   - فایل `railway.json` در root پروژه ایجاد شده است
   - این فایل build command را به درستی تنظیم می‌کند

4. **اگر هنوز مشکل دارید:**
   - مطمئن شوید که `requirements.txt` در root directory وجود دارد ✅
   - همچنین `api/requirements.txt` هم وجود دارد (برای سازگاری) ✅
   - Build command را به این تغییر دهید:
     ```
     python -m pip install --upgrade pip && pip install -r requirements.txt
     ```

### Build Failed (عمومی)

اگر build failed شد:
1. لاگ‌های build را در Railway Dashboard → Deployments → View Logs بررسی کنید
2. مطمئن شوید `requirements.txt` در root directory است
3. بررسی کنید که همه dependencies درست هستند

### Port Error

Railway به صورت خودکار متغیر `$PORT` را تنظیم می‌کند. مطمئن شوید که در start command از `$PORT` استفاده می‌کنید.

### Memory Issues

اگر با TensorFlow مشکل memory دارید:
- از `tensorflow-cpu` به جای `tensorflow` استفاده کنید (✅ انجام شده)
- Memory limit را در Railway Dashboard افزایش دهید

### Timeout Issues

- Timeout keep-alive را به 75 ثانیه تنظیم کنید (✅ در Procfile تنظیم شده)
- اگر پردازش‌های طولانی دارید، از async/await استفاده کنید

## 📝 نکات مهم

1. **Auto Deploy**: Railway به صورت خودکار با هر push به GitHub deploy می‌کند
2. **Environment Variables**: حتماً `OPENAI_API_KEY` را در Variables تنظیم کنید
3. **Logs**: لاگ‌ها را در Railway Dashboard → Deployments → View Logs ببینید
4. **Health Check**: Railway به صورت خودکار health check را انجام می‌دهد

