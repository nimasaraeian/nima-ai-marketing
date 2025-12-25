# راه‌اندازی Next.js API Route برای `/api/proxy/decision-scan`

## مشکل
Frontend (Next.js) به `http://localhost:3000/api/proxy/decision-scan` درخواست می‌دهد اما این endpoint در Next.js وجود ندارد.

## راه‌حل: ایجاد Next.js API Route

### برای Next.js 13+ (App Router)

**مسیر:** `app/api/proxy/decision-scan/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const contentType = request.headers.get('content-type') || '';
    
    // Handle multipart/form-data (for image uploads)
    if (contentType.includes('multipart/form-data')) {
      const formData = await request.formData();
      
      // Forward to backend
      const backendResponse = await fetch(`${BACKEND_URL}/api/proxy/decision-scan`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - fetch will set it with boundary
      });
      
      const data = await backendResponse.json();
      
      if (!backendResponse.ok) {
        return NextResponse.json(
          { 
            error: data.detail || data.error || 'Backend error',
            status: 'error'
          },
          { status: backendResponse.status }
        );
      }
      
      return NextResponse.json(data);
    }
    
    // Handle JSON
    const body = await request.json();
    
    const backendResponse = await fetch(`${BACKEND_URL}/api/proxy/decision-scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    const data = await backendResponse.json();
    
    if (!backendResponse.ok) {
      return NextResponse.json(
        { 
          error: data.detail || data.error || 'Backend error',
          status: 'error'
        },
        { status: backendResponse.status }
      );
    }
    
    return NextResponse.json(data);
    
  } catch (error: any) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { 
        error: error.message || 'Proxy error',
        status: 'error',
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
import FormData from 'form-data';
import fetch from 'node-fetch';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export const config = {
  api: {
    bodyParser: false, // Disable body parsing for multipart/form-data
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const contentType = req.headers['content-type'] || '';
    
    // Handle multipart/form-data
    if (contentType.includes('multipart/form-data')) {
      // Forward the raw request to backend
      const backendResponse = await fetch(`${BACKEND_URL}/api/proxy/decision-scan`, {
        method: 'POST',
        headers: {
          ...req.headers,
          host: undefined, // Remove host header
        },
        body: req, // Stream the request body
      } as any);
      
      const data = await backendResponse.json();
      
      if (!backendResponse.ok) {
        return res.status(backendResponse.status).json({
          error: data.detail || data.error || 'Backend error',
          status: 'error'
        });
      }
      
      return res.status(200).json(data);
    }
    
    // Handle JSON
    const body = req.body;
    
    const backendResponse = await fetch(`${BACKEND_URL}/api/proxy/decision-scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    const data = await backendResponse.json();
    
    if (!backendResponse.ok) {
      return res.status(backendResponse.status).json({
        error: data.detail || data.error || 'Backend error',
        status: 'error'
      });
    }
    
    return res.status(200).json(data);
    
  } catch (error: any) {
    console.error('Proxy error:', error);
    return res.status(500).json({
      error: error.message || 'Proxy error',
      status: 'error',
      details: error.toString(),
    });
  }
}
```

## تنظیم Environment Variable

در فایل `.env.local` پروژه Next.js:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

برای production:
```env
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
```

## تست

بعد از ایجاد فایل:

1. Restart سرور Next.js
2. تست کنید:
   ```bash
   # JSON mode
   curl -X POST http://localhost:3000/api/proxy/decision-scan \
     -H "Content-Type: application/json" \
     -d '{"mode":"text","text":"Test"}'
   
   # Multipart mode (image)
   curl -X POST http://localhost:3000/api/proxy/decision-scan \
     -F "mode=image" \
     -F "image=@test.jpg"
   ```

## Alternative: تغییر Frontend برای فراخوانی مستقیم Backend

اگر نمی‌خواهید از proxy استفاده کنید، می‌توانید frontend را به‌روزرسانی کنید تا مستقیماً به backend درخواست بدهد:

```typescript
// در component frontend
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

const response = await fetch(`${BACKEND_URL}/api/proxy/decision-scan`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(formData),
});
```

## وضعیت Backend

✅ Backend endpoint `/api/proxy/decision-scan` آماده است و کار می‌کند.
✅ پشتیبانی از JSON و multipart/form-data
✅ پشتیبانی از mode=url, mode=text, mode=image

فقط نیاز به ایجاد Next.js API route دارید که درخواست‌ها را به backend proxy کند.


