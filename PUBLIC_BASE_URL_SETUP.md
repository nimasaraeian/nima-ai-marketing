# PUBLIC_BASE_URL Configuration Guide

## Overview

The backend now supports `PUBLIC_BASE_URL` environment variable to generate production-safe artifact URLs.

## Local Development

When `PUBLIC_BASE_URL` is not set, the system automatically falls back to using `request.base_url` (e.g., `http://127.0.0.1:8000`).

## Production Setup

### Railway Deployment

1. Go to your Railway project settings
2. Add a new environment variable:
   - **Name:** `PUBLIC_BASE_URL`
   - **Value:** `https://your-railway-domain.up.railway.app`
   
   Example:
   ```
   PUBLIC_BASE_URL=https://nima-ai-marketing-production.up.railway.app
   ```

3. Redeploy your service

### Verification

After deployment, test the endpoint:

```powershell
$body = @{ url = "https://example.com"; goal = "leads"; locale = "en" } | ConvertTo-Json
$r = Invoke-RestMethod "https://your-railway-domain.up.railway.app/api/analyze/url-human/test-capture" `
  -Method POST -ContentType "application/json" -Body $body

# Check screenshot URLs - they should start with https://your-railway-domain...
$r.capture.screenshots.desktop.above_the_fold
```

Expected output:
```
https://your-railway-domain.up.railway.app/api/artifacts/atf_desktop_<timestamp>.png
```

## How It Works

1. **Priority 1:** If `PUBLIC_BASE_URL` is set, use it
2. **Priority 2:** Otherwise, use `request.base_url` (from FastAPI Request object)
3. **Priority 3:** Fallback to `x-forwarded-proto` and `host` headers

## Affected Endpoints

- `/api/analyze/url-human/test-capture`
- `/api/analyze/url-human`
- Any endpoint that returns screenshot URLs

## Code Implementation

The implementation is in:
- `api/core/config.py` - `get_public_base_url()` function
- `api/routes/analyze_url_human.py` - URL building logic






