# Screenshot Troubleshooting Guide

## ✅ Current Status

**Backend is working correctly:**
- ✅ Playwright installed and working
- ✅ Screenshot service captures desktop ATF successfully
- ✅ Screenshot files are created and accessible
- ✅ API endpoint returns screenshot URLs correctly

**Test Results:**
```
Hero: /static/shots/hero.png ✅
Full: /static/shots/full.png ✅
Mobile: /static/shots/mobile.png ✅
Error: (none) ✅
```

## 🔍 If You Still See "Desktop preview not available"

### Step 1: Clear Browser Cache
The frontend might be caching old responses. Try:
- **Hard Refresh**: `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac)
- **Clear Cache**: Open DevTools → Application → Clear Storage → Clear site data
- **Incognito Mode**: Test in a private/incognito window

### Step 2: Check Server Logs
When you make a request, check the server console for:
```
[analyze_url_human] Screenshot paths - hero: shots/hero.png, full: shots/full.png
[analyze_url_human] ✅ No screenshot error, building URLs...
[analyze_url_human] ✅ Hero screenshot URL: /static/shots/hero.png
```

If you see `⚠️ Desktop screenshot error detected`, that's the actual problem.

### Step 3: Test API Directly
```powershell
$body = @{url='https://nimasaraeian.com/'} | ConvertTo-Json
$response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/analyze/url-human' -Method POST -Body $body -ContentType 'application/json'
$json = $response.Content | ConvertFrom-Json
Write-Host "Hero: $($json.screenshots.hero)"
Write-Host "Error: $($json.screenshots._error)"
```

### Step 4: Check Screenshot Files
```powershell
cd N:\nima-ai-marketing
Test-Path "api\static\shots\hero.png"
Test-Path "api\static\shots\full.png"
```

### Step 5: Verify Screenshot Accessibility
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/static/shots/hero.png" -UseBasicParsing
```

Should return `200 OK` with image data.

## 🐛 Common Issues

### Issue: Frontend Shows Error But Backend Works
**Cause**: Browser cache or frontend logic issue
**Solution**: 
1. Clear browser cache (hard refresh)
2. Check browser console for JavaScript errors
3. Check Network tab to see actual API response

### Issue: Screenshot Files Not Found
**Cause**: Files were deleted or path is wrong
**Solution**:
1. Run test: `python api/test_screenshot.py https://nimasaraeian.com/`
2. Check if files exist in `api/static/shots/`
3. Verify static files are mounted in FastAPI

### Issue: Screenshot Returns 404
**Cause**: Static files not properly mounted
**Solution**:
1. Check `api/main.py` - should have: `app.mount("/static", StaticFiles(...))`
2. Verify directory exists: `api/static/shots/`
3. Restart server

## 📊 Debug Endpoints

### Test Capture Only
```powershell
$body = @{url='YOUR_URL'} | ConvertTo-Json
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/analyze/url-human/test-capture' -Method POST -Body $body -ContentType 'application/json'
```

### Check Screenshot Files
```powershell
Get-ChildItem "N:\nima-ai-marketing\api\static\shots\" | Format-Table Name, Length, LastWriteTime
```

## 🔧 Recent Optimizations

1. **Desktop ATF Only**: No full page (faster, less memory)
2. **Increased Timeout**: 120s for page load, 90s for screenshot
3. **Block Heavy Resources**: video, media, font, analytics
4. **Realistic User-Agent**: Standard Chrome desktop UA
5. **Better Error Handling**: Detailed error messages in logs

## 📝 Next Steps

If the issue persists:

1. **Check server logs** when making a request - look for `[analyze_url_human]` messages
2. **Check browser console** - look for JavaScript errors or failed image loads
3. **Check Network tab** - verify API response contains screenshot URLs
4. **Test with different URL** - see if it's URL-specific

The backend is working correctly, so the issue is likely:
- Browser cache
- Frontend JavaScript logic
- Network/CORS issues
- Image loading in frontend


