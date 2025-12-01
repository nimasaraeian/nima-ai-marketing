# ✅ Deployment Checklist

## 📋 وضعیت فعلی

### ✅ Backend (API)
- [x] CORS برای production تنظیم شده (`https://nimasaraeian.com`)
- [x] API key در `.env` تنظیم شده
- [x] همه endpoints تست شده‌اند
- [x] JSON parsing errors مدیریت شده‌اند

### ⚠️ Frontend
- [ ] `API_BASE_URL` باید برای production تغییر کند
- [x] فایل‌های HTML/CSS/JS آماده هستند
- [x] می‌تواند به صورت local اجرا شود

---

## 🚀 گزینه 1: اجرای Local (برای تست)

### Frontend:
```powershell
cd web
python -m http.server 8080
```
سپس به `http://localhost:8080` بروید.

**⚠️ مهم:** در `web/app.js` خط 2، `API_BASE_URL` باید `http://127.0.0.1:8000` باشد.

### Backend:
```powershell
cd n:\nima-ai-marketing
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 گزینه 2: Deployment کامل

### مرحله 1: تغییر API URL در Frontend

در `web/app.js` خط 2 را تغییر دهید:

```javascript
// از این:
const API_BASE_URL = 'http://127.0.0.1:8000';

// به این (بسته به اینکه backend کجا deploy می‌شود):
const API_BASE_URL = 'https://api.nimasaraeian.com';
// یا
const API_BASE_URL = 'https://your-backend-domain.com';
```

### مرحله 2: Deploy Backend

#### گزینه A: Render.com (پیشنهادی)
1. به https://render.com بروید
2. New → Web Service
3. Connect repository یا Deploy manually
4. تنظیمات:
   - **Name:** `nima-ai-marketing-api`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables:**
     - `OPENAI_API_KEY` = (از `.env` کپی کنید)
5. Save & Deploy

#### گزینه B: Railway.app
1. به https://railway.app بروید
2. New Project → Deploy from GitHub
3. تنظیمات مشابه Render

### مرحله 3: Deploy Frontend

#### گزینه A: Netlify (ساده‌ترین)
1. به https://app.netlify.com بروید
2. Add new site → Deploy manually
3. پوشه `web` را drag & drop کنید
4. یا از Git repository استفاده کنید

**تنظیمات:**
- Site name: `nimasaraeian-ai-marketing`
- Custom domain: `nimasaraeian.com/ai-marketing` (یا subdomain)

#### گزینه B: Vercel
```powershell
cd web
npm i -g vercel
vercel
```

### مرحله 4: تست Production

1. Frontend را باز کنید: `https://nimasaraeian.com/ai-marketing`
2. یک درخواست تست بفرستید
3. Console browser را بررسی کنید (F12) برای خطاهای CORS
4. Network tab را بررسی کنید که درخواست‌ها به backend می‌روند

---

## 🔧 تنظیمات اضافی

### اگر Backend در همان Domain است:
```javascript
// در web/app.js
const API_BASE_URL = window.location.origin + '/api';
```

### اگر Backend در Domain جداگانه است:
```javascript
// در web/app.js
const API_BASE_URL = 'https://api.nimasaraeian.com';
```

و در `api/main.py` مطمئن شوید که CORS شامل domain frontend است:
```python
origins = [
    "https://nimasaraeian.com",
    "https://www.nimasaraeian.com",
    # ... سایر domains
]
```

---

## ✅ چک‌لیست نهایی

- [ ] Backend deploy شده و در دسترس است
- [ ] `API_BASE_URL` در `web/app.js` به production URL تغییر کرده
- [ ] Frontend deploy شده
- [ ] CORS در backend برای domain frontend تنظیم شده
- [ ] تست کامل انجام شده
- [ ] SSL/HTTPS فعال است
- [ ] Environment variables در production تنظیم شده‌اند

---

## 🐛 Troubleshooting

### خطای CORS:
- بررسی کنید که domain frontend در `api/main.py` در لیست `origins` باشد
- مطمئن شوید که هر دو frontend و backend از HTTPS استفاده می‌کنند

### خطای "Failed to fetch":
- بررسی کنید که `API_BASE_URL` درست است
- بررسی کنید که backend در حال اجرا است
- Console browser را بررسی کنید

### خطای JSON parsing:
- این مشکل باید با تغییرات اخیر حل شده باشد
- اگر هنوز رخ می‌دهد، لاگ‌های backend را بررسی کنید

