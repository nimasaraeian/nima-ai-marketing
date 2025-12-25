# راه‌حل خطای 404 برای `/api/proxy/decision-scan`

## مشکل
Frontend (Next.js) به `/api/proxy/decision-scan` درخواست می‌دهد اما این endpoint وجود ندارد.

## راه‌حل: ایجاد Next.js API Route

در پروژه Next.js خود، یکی از این فایل‌ها را ایجاد کنید:

### برای Next.js 13+ (App Router)

**مسیر:** `app/api/proxy/decision-scan/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // URL backend (از environment variable یا default)
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 
                      process.env.BACKEND_URL || 
                      'http://localhost:8000';
    
    console.log('Proxying to backend:', `${backendUrl}/api/proxy/decision-scan`);
    
    // پروکسی به FastAPI backend
    const response = await fetch(`${backendUrl}/api/proxy/decision-scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      console.error('Backend error:', data);
      return NextResponse.json(
        { 
          error: data.detail || data.error || 'Backend error',
          status: response.status 
        },
        { status: response.status }
      );
    }
    
    return NextResponse.json(data);
    
  } catch (error: any) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { 
        error: error.message || 'Proxy error',
        details: error.toString() 
      },
      { status: 500 }
    );
  }
}
```

### برای Next.js 12 (Pages Router)

**مسیر:** `pages/api/proxy/decision-scan.ts`

```typescript
import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 
                      process.env.BACKEND_URL || 
                      'http://localhost:8000';
    
    console.log('Proxying to backend:', `${backendUrl}/api/proxy/decision-scan`);
    
    const response = await fetch(`${backendUrl}/api/proxy/decision-scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      console.error('Backend error:', data);
      return res.status(response.status).json({
        error: data.detail || data.error || 'Backend error',
      });
    }
    
    return res.status(200).json(data);
    
  } catch (error: any) {
    console.error('Proxy error:', error);
    return res.status(500).json({
      error: error.message || 'Proxy error',
      details: error.toString(),
    });
  }
}
```

## تنظیم Environment Variables

در فایل `.env.local` یا `.env` پروژه Next.js:

```env
# URL backend FastAPI
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# یا برای production:
# NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
```

## تست

بعد از ایجاد فایل، سرور Next.js را restart کنید و دوباره تست کنید.

## Alternative: تغییر Frontend برای فراخوانی مستقیم Backend

اگر نمی‌خواهید از proxy استفاده کنید، می‌توانید در frontend مستقیماً به backend درخواست بدهید:

```typescript
// در DecisionEvidenceForm.tsx یا page.tsx
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

const response = await fetch(`${backendUrl}/api/proxy/decision-scan`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(formData),
});
```

## بررسی

بعد از ایجاد API route، می‌توانید با curl تست کنید:

```bash
curl -X POST http://localhost:3000/api/proxy/decision-scan \
  -H "Content-Type: application/json" \
  -d '{"content": "test", "goal": "leads"}'
```



