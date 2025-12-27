# Deployment Steps to Fix 502 Error

## Current Status
✅ Dockerfile fixed to use PORT environment variable
✅ Startup script created (`start.sh`)
✅ Changes committed to git

## Next Steps to Deploy

### Step 1: Push Changes to Repository
```bash
git push origin main
```

### Step 2: Rebuild and Redeploy

#### If using Railway:
1. Go to your Railway dashboard
2. The service should auto-redeploy when it detects the new commit
3. If not, manually trigger a redeploy
4. Check the deployment logs for any errors

#### If using Render:
1. Go to your Render dashboard
2. The service should auto-redeploy when it detects the new commit
3. If not, click "Manual Deploy" → "Deploy latest commit"
4. Check the deployment logs

#### If using Docker directly:
```bash
# Build the new image
docker build -t nima-ai-marketing .

# Run with PORT environment variable
docker run -p 8000:8000 \
  -e PORT=8000 \
  -e OPENAI_API_KEY=your-key-here \
  nima-ai-marketing
```

### Step 3: Verify Deployment

1. **Check Health Endpoint:**
```bash
curl https://your-app-url/health
```
Should return: `{"status":"ok"}`

2. **Check Application Logs:**
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

3. **Test the Endpoint:**
Based on the error screenshot, the frontend is calling an endpoint for URL analysis. Test it:
```bash
curl -X POST https://your-app-url/api/brain/cognitive-friction \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.selphlyze.com/"}'
```

### Step 4: Common Issues to Check

#### Issue: Still Getting 502 After Redeploy
**Check:**
- [ ] Are deployment logs showing successful build?
- [ ] Is the application actually starting? (check logs for "Application startup complete")
- [ ] Is PORT environment variable set correctly?
- [ ] Are there any import errors in the logs?
- [ ] Is OPENAI_API_KEY set? (app should still start without it, but endpoints will fail)

#### Issue: Application Starts But Endpoints Return 502
**Possible causes:**
- Port mismatch - verify PORT env var matches what platform expects
- Application binding to wrong interface - should be `0.0.0.0`
- Health check failing - verify `/health` endpoint works

#### Issue: Build Fails
**Check:**
- [ ] All dependencies in `requirements.txt` are valid
- [ ] Python version matches (3.11 in Dockerfile)
- [ ] Playwright Chromium installation succeeds
- [ ] No syntax errors in `start.sh`

### Step 5: Debug Commands

If still having issues, check these:

```bash
# Test locally first
export PORT=8000
export OPENAI_API_KEY=your-key
./start.sh

# Or test with uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75
```

### Step 6: Check Deployment Platform Logs

**Railway:**
- Go to your service → "Deployments" → Click latest deployment → "View Logs"

**Render:**
- Go to your service → "Logs" tab → Check build and runtime logs

Look for:
- ✅ "Application startup complete" = Success
- ❌ Import errors = Missing dependencies
- ❌ Port binding errors = PORT configuration issue
- ❌ Timeout errors = Startup taking too long

## Expected Behavior After Fix

Once deployed correctly:
1. Application should start within 30-60 seconds
2. `/health` endpoint should return `{"status":"ok"}` immediately
3. `/api/brain/cognitive-friction` should accept requests (may take time to process)
4. No more 502 errors from the gateway

## If Problem Persists

1. Share the deployment logs (build + runtime)
2. Share the output of: `curl https://your-app-url/health`
3. Check if there are any platform-specific requirements we're missing










