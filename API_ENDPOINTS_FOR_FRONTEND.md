# مسیرهای API برای Frontend

## Base URL

### Development (Local)
```
http://localhost:8000
```

### Production
```
https://your-backend-domain.com
```
(یا از environment variable استفاده کنید: `NEXT_PUBLIC_BACKEND_URL`)

---

## Endpoint: Decision Scan

### مسیر اصلی
```
POST /api/decision-scan
```

### مسیر Proxy (برای Next.js)
```
POST /api/proxy/decision-scan
```

**نکته:** هر دو endpoint یکسان عمل می‌کنند. از هر کدام که راحت‌ترید استفاده کنید.

---

## Request Formats

### 1. Mode: URL (JSON)

**Content-Type:** `application/json`

```json
{
  "mode": "url",
  "url": "https://example.com",
  "goal": "leads",
  "locale": "en"
}
```

**Example:**
```javascript
const response = await fetch('http://localhost:8000/api/decision-scan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    mode: 'url',
    url: 'https://nimasaraeian.com',
    goal: 'leads',
    locale: 'en'
  })
});
```

---

### 2. Mode: Text (JSON)

**Content-Type:** `application/json`

```json
{
  "mode": "text",
  "text": "Your text content here..."
}
```

**Example:**
```javascript
const response = await fetch('http://localhost:8000/api/decision-scan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    mode: 'text',
    text: 'Your text content here...'
  })
});
```

---

### 3. Mode: Image (Multipart Form Data)

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `mode`: `"image"`
- `image`: File (image file)

**Example:**
```javascript
const formData = new FormData();
formData.append('mode', 'image');
formData.append('image', fileInput.files[0]); // File from input

const response = await fetch('http://localhost:8000/api/decision-scan', {
  method: 'POST',
  body: formData
  // Don't set Content-Type header - browser will set it with boundary
});
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "status": "ok",
  "decision_state": {
    "label": "Interested but Confused",
    "confidence": "low" | "medium" | "high",
    "evidence": [
      "Evidence string 1",
      "Evidence string 2"
    ]
  },
  "human_report": "# Analysis Report\n\n...",
  "summary": "Summary text...",
  "issues": [
    {
      "title": "Issue Title",
      "why": "Why this is an issue",
      "fix": "How to fix it",
      "location": null
    }
  ],
  "screenshots": {
    "desktop": "data:image/png;base64,...",
    "mobile": "data:image/png;base64,..."
  }
}
```

### Error Response (400/500)

```json
{
  "status": "error",
  "error": "Error message",
  "decision_state": null,
  "human_report": null,
  "summary": null,
  "issues": null,
  "screenshots": null
}
```

---

## TypeScript Types (برای Frontend)

```typescript
interface DecisionScanRequest {
  mode: 'url' | 'text' | 'image';
  url?: string;
  text?: string;
  goal?: string;
  locale?: string;
  image?: File;
}

interface DecisionState {
  label: string;
  confidence: 'low' | 'medium' | 'high';
  evidence: string[];
}

interface Issue {
  title: string;
  why: string;
  fix: string;
  location: string | null;
}

interface DecisionScanResponse {
  status: 'ok' | 'error';
  decision_state: DecisionState | null;
  human_report: string | null;
  summary: string | null;
  issues: Issue[] | null;
  screenshots: {
    desktop?: string;
    mobile?: string;
  } | null;
  error?: string;
}
```

---

## مثال کامل برای Frontend (React/Next.js)

### با Fetch API

```typescript
async function analyzeDecision(
  mode: 'url' | 'text' | 'image',
  data: { url?: string; text?: string; image?: File }
): Promise<DecisionScanResponse> {
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  
  if (mode === 'image' && data.image) {
    // Multipart form data
    const formData = new FormData();
    formData.append('mode', 'image');
    formData.append('image', data.image);
    
    const response = await fetch(`${BACKEND_URL}/api/decision-scan`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } else {
    // JSON
    const body: any = { mode };
    if (mode === 'url' && data.url) {
      body.url = data.url;
      body.goal = 'leads';
      body.locale = 'en';
    } else if (mode === 'text' && data.text) {
      body.text = data.text;
    }
    
    const response = await fetch(`${BACKEND_URL}/api/decision-scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }
}

// Usage
const result = await analyzeDecision('url', { url: 'https://example.com' });
console.log(result.decision_state.label);
```

### با Axios

```typescript
import axios from 'axios';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// URL mode
async function analyzeUrl(url: string) {
  const response = await axios.post<DecisionScanResponse>(
    `${BACKEND_URL}/api/decision-scan`,
    {
      mode: 'url',
      url,
      goal: 'leads',
      locale: 'en'
    },
    {
      headers: {
        'Content-Type': 'application/json'
      }
    }
  );
  return response.data;
}

// Text mode
async function analyzeText(text: string) {
  const response = await axios.post<DecisionScanResponse>(
    `${BACKEND_URL}/api/decision-scan`,
    {
      mode: 'text',
      text
    },
    {
      headers: {
        'Content-Type': 'application/json'
      }
    }
  );
  return response.data;
}

// Image mode
async function analyzeImage(imageFile: File) {
  const formData = new FormData();
  formData.append('mode', 'image');
  formData.append('image', imageFile);
  
  const response = await axios.post<DecisionScanResponse>(
    `${BACKEND_URL}/api/decision-scan`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  );
  return response.data;
}
```

---

## Health Check

برای بررسی اینکه endpoint در دسترس است:

```
GET /api/decision-scan/health
```

**Response:**
```json
{
  "status": "ok",
  "endpoint": "/api/decision-scan",
  "modes": ["url", "text", "image"]
}
```

---

## نکات مهم

1. **Locale:** همیشه `"en"` است (enforced در backend)
2. **Goal:** برای URL mode، می‌تواند `"leads"`, `"sales"`, `"other"` باشد
3. **Screenshots:** به صورت Base64 data URL برگردانده می‌شوند
4. **Error Handling:** همیشه `status` field را چک کنید
5. **CORS:** اگر از frontend مستقیماً به backend درخواست می‌دهید، مطمئن شوید CORS تنظیم شده است

---

## Environment Variables

در `.env.local` یا `.env`:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

برای production:
```env
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
```


