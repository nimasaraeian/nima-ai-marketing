# راهنمای Deployment برای nimasaraeian.com/ai-marketing

این راهنما نحوه پیاده‌سازی UI/UX را در آدرس https://nimasaraeian.com/ai-marketing توضیح می‌دهد.

## 📋 پیش‌نیازها

1. **Backend API** (FastAPI) - در حال اجرا
2. **Domain** - nimasaraeian.com
3. **Hosting** - برای frontend (Netlify, Vercel, یا سرور خودتان)
4. **SSL Certificate** - برای HTTPS

---

## 🚀 گزینه‌های Deployment

### گزینه 1: Netlify (پیشنهادی - ساده‌ترین)

#### مراحل:

1. **آماده‌سازی فایل‌ها:**
   ```bash
   cd web
   # فایل‌های HTML, CSS, JS آماده هستند
   ```

2. **ایجاد `netlify.toml`:**
   ```toml
   [build]
     publish = "."
   
   [[redirects]]
     from = "/*"
     to = "/index.html"
     status = 200
   ```

3. **Deploy:**
   - به https://app.netlify.com بروید
   - "Add new site" → "Deploy manually"
   - پوشه `web` را drag & drop کنید
   - یا از Git repository استفاده کنید

4. **تنظیمات:**
   - Site name: `nimasaraeian-ai-marketing`
   - Custom domain: `nimasaraeian.com`
   - Add subdomain: `ai-marketing`
   - SSL: خودکار فعال می‌شود

5. **تغییر API URL در `app.js`:**
   ```javascript
   // تغییر از:
   const API_BASE_URL = 'http://127.0.0.1:8000';
   
   // به:
   const API_BASE_URL = 'https://api.nimasaraeian.com';
   // یا
   const API_BASE_URL = 'https://your-backend-domain.com';
   ```

---

### گزینه 2: Vercel

1. **نصب Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   cd web
   vercel
   ```

3. **تنظیم Custom Domain:**
   - در dashboard Vercel
   - Settings → Domains
   - Add: `ai-marketing.nimasaraeian.com`

---

### گزینه 3: سرور خودتان (VPS/Shared Hosting)

#### برای Apache:

1. **آپلود فایل‌ها:**
   ```bash
   # آپلود محتویات پوشه web به:
   /public_html/ai-marketing/
   # یا
   /var/www/html/ai-marketing/
   ```

2. **ایجاد `.htaccess`:**
   ```apache
   RewriteEngine On
   RewriteBase /ai-marketing/
   RewriteRule ^index\.html$ - [L]
   RewriteCond %{REQUEST_FILENAME} !-f
   RewriteCond %{REQUEST_FILENAME} !-d
   RewriteRule . /ai-marketing/index.html [L]
   ```

3. **تنظیم CORS در Backend:**
   ```python
   # در api/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://nimasaraeian.com",
           "https://www.nimasaraeian.com"
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

---

## 🔧 تنظیمات Backend API

### 1. تغییر API URL در Frontend

در فایل `web/app.js`:

```javascript
// برای Production
const API_BASE_URL = 'https://api.nimasaraeian.com';

// یا اگر backend در همان domain است:
const API_BASE_URL = 'https://nimasaraeian.com/api';
```

### 2. Deploy Backend API

#### گزینه A: Railway / Render

```bash
# Railway
railway login
railway init
railway up

# Render
# از dashboard استفاده کنید
```

#### گزینه B: VPS با Nginx

```nginx
# /etc/nginx/sites-available/api.nimasaraeian.com
server {
    listen 80;
    server_name api.nimasaraeian.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Environment Variables

در production، مطمئن شوید:

```bash
# در .env یا environment variables
OPENAI_API_KEY=sk-proj-...
```

---

## 🔒 امنیت

### 1. CORS Configuration

```python
# در api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nimasaraeian.com",
        "https://www.nimasaraeian.com"
    ],  # فقط domain خودتان
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

### 2. Rate Limiting

```python
# اضافه کردن rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/brain")
@limiter.limit("10/minute")
def brain_endpoint(request: BrainRequest):
    # ...
```

### 3. API Key Protection

برای production، می‌توانید API key را در frontend قرار ندهید و از server-side proxy استفاده کنید.

---

## 📱 تست در Production

### 1. تست Local با Production API

```javascript
// در app.js موقتاً:
const API_BASE_URL = 'https://api.nimasaraeian.com';
```

### 2. تست کامل

1. باز کردن https://nimasaraeian.com/ai-marketing
2. انتخاب یک ماژول
3. پر کردن فرم
4. بررسی پاسخ API
5. بررسی Quality Score

---

## 🎨 سفارشی‌سازی

### تغییر رنگ‌ها

در `web/styles.css`:

```css
:root {
    --primary-color: #6366f1;  /* تغییر رنگ اصلی */
    --secondary-color: #8b5cf6;
    /* ... */
}
```

### تغییر Logo/Branding

در `web/index.html`:

```html
<div class="nav-brand">
    <a href="/">
        <img src="/logo.png" alt="Nima Saraeian" />
    </a>
</div>
```

---

## 📊 Analytics

### اضافه کردن Google Analytics

در `web/index.html` قبل از `</head>`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

---

## 🔄 به‌روزرسانی

### برای به‌روزرسانی Frontend:

1. تغییرات را در `web/` اعمال کنید
2. Commit و Push به Git
3. Netlify/Vercel خودکار deploy می‌کند

### برای به‌روزرسانی Backend:

1. تغییرات را در `api/` اعمال کنید
2. Restart server:
   ```bash
   # اگر با systemd:
   sudo systemctl restart nima-api
   
   # یا اگر با PM2:
   pm2 restart nima-api
   ```

---

## 🐛 Troubleshooting

### مشکل CORS

```python
# بررسی کنید که CORS در backend درست تنظیم شده:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nimasaraeian.com"],  # بدون trailing slash
    # ...
)
```

### مشکل API Connection

1. بررسی کنید API در حال اجرا است
2. بررسی کنید URL در `app.js` درست است
3. بررسی کنید CORS تنظیمات درست است
4. Console مرورگر را برای خطاها چک کنید

### مشکل SSL

- مطمئن شوید SSL certificate معتبر است
- از Let's Encrypt استفاده کنید (رایگان)

---

## ✅ Checklist قبل از Launch

- [ ] Backend API deployed و در حال اجرا
- [ ] API URL در `app.js` به production تغییر کرده
- [ ] CORS در backend تنظیم شده
- [ ] SSL certificate فعال است
- [ ] Domain به درستی تنظیم شده
- [ ] Environment variables تنظیم شده
- [ ] تست کامل انجام شده
- [ ] Analytics اضافه شده (اختیاری)
- [ ] Error handling بررسی شده

---

## 📞 پشتیبانی

اگر مشکلی پیش آمد:

1. Console مرورگر را بررسی کنید (F12)
2. Network tab را برای درخواست‌های API چک کنید
3. Backend logs را بررسی کنید
4. CORS errors را بررسی کنید

---

**موفق باشید! 🚀**



