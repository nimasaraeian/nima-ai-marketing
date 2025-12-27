# Artifacts Pipeline Deployment Guide

## Summary

This implementation creates a robust artifact pipeline that:
- ✅ Never breaks the UI (always returns non-null artifacts structure)
- ✅ Saves screenshots to disk with unique filenames
- ✅ Returns both URL and data_uri for each screenshot
- ✅ Handles errors gracefully (returns error structure, doesn't crash)
- ✅ Uses environment variables for configuration
- ✅ Works on both local and Railway deployments

## Files Modified/Created

### New Files
- `api/services/artifacts.py` - Artifact management helpers
- `scripts/smoke_test.ps1` - PowerShell smoke test
- `scripts/smoke_test.sh` - Bash smoke test

### Modified Files
- `api/core/config.py` - Added `get_artifacts_dir()` with env var support
- `api/paths.py` - Uses centralized config
- `api/main.py` - Startup ensures artifacts dir, improved artifact endpoint
- `api/services/page_capture.py` - Saves artifacts, returns new structure
- `api/utils/output_sanitize.py` - Updated `ensure_capture_attached` for new structure
- `api/routes/analyze_url_human.py` - Passes base_url to capture

## Environment Variables

### Required for Railway
```bash
ARTIFACTS_DIR=/tmp/artifacts  # Optional: defaults to /tmp/artifacts (Linux) or temp dir (Windows)
BASE_PUBLIC_URL=https://your-railway-app.up.railway.app  # Required for absolute URLs
```

### Optional (backward compatibility)
```bash
PUBLIC_BASE_URL=https://your-railway-app.up.railway.app  # Falls back to BASE_PUBLIC_URL
```

## Local Testing Commands

### 1. Start the server
```powershell
# Windows PowerShell
cd n:\nima-ai-marketing
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Run smoke test
```powershell
# Windows PowerShell
.\scripts\smoke_test.ps1
```

```bash
# Linux/Mac
chmod +x scripts/smoke_test.sh
./scripts/smoke_test.sh
```

### 3. Manual test
```powershell
# Windows PowerShell
$BASE = "http://127.0.0.1:8000"
$body = @{ url="https://stripe.com/pricing"; goal="leads"; locale="en" } | ConvertTo-Json
$response = Invoke-RestMethod "$BASE/api/analyze/url-human" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 180
$response.capture.artifacts.above_the_fold.desktop
$response.capture.artifacts.above_the_fold.mobile
```

### 4. Test artifact endpoint
```powershell
# After running analyze, get the filename from response
$filename = "atf_desktop_1234567890.png"  # Replace with actual filename
Invoke-WebRequest "http://127.0.0.1:8000/api/artifacts/$filename" -OutFile test_screenshot.png
```

## Railway Deployment

### Environment Variables to Set
1. **BASE_PUBLIC_URL** (Required)
   - Value: `https://your-railway-app.up.railway.app`
   - Used to generate absolute artifact URLs

2. **ARTIFACTS_DIR** (Optional)
   - Value: `/tmp/artifacts` (default)
   - Can be set to a persistent volume path if needed

### Verification on Railway
```bash
# Test the endpoint
curl -X POST "https://your-railway-app.up.railway.app/api/analyze/url-human" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://stripe.com/pricing","goal":"leads","locale":"en"}' \
  | jq '.capture.artifacts.above_the_fold.desktop'
```

## Response Structure

The `/api/analyze/url-human` endpoint now returns:

```json
{
  "status": "ok",
  "capture": {
    "status": "ok",
    "artifacts": {
      "above_the_fold": {
        "desktop": {
          "filename": "atf_desktop_1234567890.png",
          "url": "https://domain.com/api/artifacts/atf_desktop_1234567890.png",
          "data_uri": "data:image/png;base64,...",
          "width": 1365,
          "height": 768
        },
        "mobile": {
          "filename": "atf_mobile_1234567890.png",
          "url": "https://domain.com/api/artifacts/atf_mobile_1234567890.png",
          "data_uri": "data:image/png;base64,...",
          "width": 390,
          "height": 844
        }
      }
    },
    "screenshots": { ... }  // Legacy format for backward compat
  }
}
```

## Error Handling

If capture fails, the response includes:
```json
{
  "capture": {
    "status": "error",
    "error": "Error message",
    "artifacts": {
      "above_the_fold": {
        "desktop": { "filename": null, "url": null, "data_uri": null, ... },
        "mobile": { "filename": null, "url": null, "data_uri": null, ... }
      }
    }
  }
}
```

**Never returns null** - always includes the artifacts structure.

## Key Features

1. **Dual Format**: Both URL (for CDN/caching) and data_uri (fallback)
2. **Unique Filenames**: Epoch-based filenames prevent collisions
3. **Cache Headers**: Immutable filenames get long cache headers
4. **Error Resilience**: Never crashes, always returns usable structure
5. **Environment Aware**: Works on Windows, Linux, Mac, Railway

