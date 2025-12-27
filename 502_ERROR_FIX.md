# 502 Error Fix - Application Failed to Respond

## Problem
The application was returning a 502 error with message "Application failed to respond". This typically indicates:
- The application is not starting properly
- The application is not binding to the correct port
- The application is crashing during startup
- Missing environment variables or dependencies

## Fixes Applied

### 1. Fixed Dockerfile Port Configuration
**Issue:** The Dockerfile was using a hardcoded port `8000`, but many deployment platforms (Railway, Render, etc.) require using the `PORT` environment variable.

**Fix:** Updated Dockerfile to:
- Use `PORT` environment variable with fallback to 8000
- Added startup script for better error handling
- Added `--timeout-keep-alive 75` for better connection handling

### 2. Added Startup Script
Created `start.sh` to:
- Properly handle PORT environment variable
- Provide better error logging
- Ensure proper uvicorn configuration

## How to Deploy

### Using Docker
```bash
docker build -t nima-ai-marketing .
docker run -p 8000:8000 -e PORT=8000 -e OPENAI_API_KEY=your-key nima-ai-marketing
```

### Using Railway/Render
The platform will automatically:
- Set the `PORT` environment variable
- Use the startup script from the Dockerfile
- Expose the application on the assigned port

## Environment Variables Required

Make sure these are set in your deployment platform:

1. **OPENAI_API_KEY** (required)
   - Your OpenAI API key for AI functionality
   - Without this, the app will start but API calls will fail

2. **PORT** (optional, defaults to 8000)
   - Automatically set by most platforms
   - Only needed if deploying manually

## Verification Steps

### 1. Check Health Endpoint
```bash
curl https://your-app-url/health
```
Should return: `{"status":"ok"}`

### 2. Check Root Endpoint
```bash
curl https://your-app-url/
```
Should return application info including system prompt status

### 3. Check Logs
Look for these startup messages:
```
============================================================
NIMA AI BRAIN API - Starting...
============================================================
System Prompt Length: XXXXX characters
Quality Engine: Enabled
============================================================
INFO:     Application startup complete.
```

## Common Issues and Solutions

### Issue 1: Still Getting 502 After Fix
**Possible causes:**
- Build failed - check build logs
- Dependencies not installed - check requirements.txt
- Missing environment variables - verify OPENAI_API_KEY is set

**Solution:**
1. Check deployment platform logs for errors
2. Verify all dependencies in requirements.txt are installable
3. Ensure environment variables are set correctly

### Issue 2: Application Starts But Health Check Fails
**Possible causes:**
- Port mismatch
- Application binding to wrong interface

**Solution:**
- Verify PORT environment variable matches what the platform expects
- Check that application binds to `0.0.0.0` (not `127.0.0.1`)

### Issue 3: Startup Timeout
**Possible causes:**
- Loading brain memory files takes too long
- Network issues during startup
- Large dependencies taking time to load

**Solution:**
- The startup event already handles this gracefully
- Brain memory loading is lazy and won't block startup
- Check logs to see if there are specific import errors

## Testing Locally

Before deploying, test locally:

```bash
# Set environment variables
export PORT=8000
export OPENAI_API_KEY=your-key-here

# Run the startup script
./start.sh

# Or run directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75
```

Then test:
```bash
curl http://localhost:8000/health
```

## Next Steps

If the 502 error persists after these fixes:

1. **Check deployment logs** - Look for Python errors, import errors, or startup failures
2. **Verify dependencies** - Ensure all packages in requirements.txt can be installed
3. **Test locally** - Make sure the application starts successfully on your machine
4. **Check platform-specific issues** - Some platforms have specific requirements (memory limits, timeout settings, etc.)

## Files Modified

- `Dockerfile` - Updated to use PORT environment variable and startup script
- `start.sh` - New startup script for better error handling










