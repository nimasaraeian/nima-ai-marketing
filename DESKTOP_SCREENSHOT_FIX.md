# Desktop Screenshot Fix - Troubleshooting Guide

## 🔧 Changes Made

### 1. Increased Timeout for Full Page Screenshots
- **Before**: 30 seconds timeout for full page screenshots
- **After**: 60 seconds timeout for full page screenshots
- **Fallback**: If full page fails, automatically tries viewport-only screenshot (30s timeout)

### 2. Improved Page Load Strategy
- **Before**: Tried `domcontentloaded`, then `load`
- **After**: Tries `domcontentloaded` → `load` → `commit` (minimal wait)
- This makes the capture more resilient to slow-loading pages

### 3. Better Error Handling
- Added explicit timeouts for ATF screenshots (30s)
- Better error messages that include specific failure reasons
- Fallback mechanism: if full page fails, tries viewport-only

### 4. Enhanced Error Reporting
- Error messages now include specific failure details
- Warnings distinguish between full page failure and viewport fallback
- Server logs include detailed error information

## 🔍 Troubleshooting Steps

### Step 1: Check Backend Server Logs
Look for these log messages in your server output:
```
[Desktop Capture] Loading URL: <url>
[Desktop Capture] [OK] Page loaded (domcontentloaded)
[Desktop Capture] Attempting ATF screenshot...
[Desktop Capture] Attempting full page screenshot...
```

If you see errors like:
- `atf_failed: TimeoutError` - ATF screenshot timed out
- `full_failed: TimeoutError` - Full page screenshot timed out
- `timeout_domcontentloaded` - Page took too long to load

### Step 2: Verify Playwright Installation
```powershell
cd N:\nima-ai-marketing
python api/check_playwright.py
```

Expected output:
```
[OK] Playwright package installed
[OK] Chromium browser is installed and working
```

### Step 3: Test Screenshot Service
```powershell
cd N:\nima-ai-marketing
python api/test_screenshot.py <problematic-url>
```

This will show:
- Whether desktop screenshots succeed
- Whether mobile screenshots succeed
- Specific error messages
- File sizes of captured screenshots

### Step 4: Check URL Accessibility
Some websites block automated requests. Test with:
```powershell
# Test with a simple URL first
python api/test_screenshot.py https://example.com

# Then test with the problematic URL
python api/test_screenshot.py <your-url>
```

### Step 5: Check Server Resources
Desktop screenshots (especially full page) can be memory-intensive. Check:
- Available RAM on the server
- Whether the process is being killed by OOM (Out of Memory) killer
- Server logs for memory-related errors

## 🐛 Common Issues and Solutions

### Issue: Desktop Screenshot Times Out
**Symptoms**: Mobile works, desktop fails with timeout
**Possible Causes**:
1. Page is very long (full page screenshot takes too long)
2. Page has slow-loading resources
3. Website blocks desktop user agents

**Solutions**:
1. The code now automatically falls back to viewport-only if full page fails
2. Check if the URL is accessible manually
3. Try a different URL to see if it's URL-specific

### Issue: Memory Errors
**Symptoms**: Screenshot fails with memory-related errors
**Possible Causes**:
1. Page is extremely long
2. Server has limited RAM

**Solutions**:
1. The viewport fallback uses less memory
2. Consider increasing server RAM
3. For very long pages, viewport-only may be sufficient

### Issue: Website Blocks Desktop User Agent
**Symptoms**: Desktop fails but mobile succeeds
**Possible Causes**:
1. Website detects automation
2. Website blocks desktop browsers but allows mobile

**Solutions**:
1. The code uses a realistic desktop user agent
2. Consider using the mobile screenshot if desktop consistently fails
3. Some websites are designed mobile-first and may block desktop automation

## 📊 What Changed in the Code

### File: `api/services/page_capture.py`

1. **Full Page Screenshot** (lines 108-130):
   - Increased timeout from 30s to 60s
   - Added viewport-only fallback
   - Better error handling

2. **ATF Screenshot** (lines 94-107):
   - Added explicit 30s timeout
   - Better error logging

3. **Page Load** (lines 76-95):
   - Added `commit` fallback strategy
   - Better timeout handling

4. **Error Reporting** (lines 355-375):
   - More detailed error messages
   - Distinguishes between full page failure and viewport fallback

## ✅ Testing

After these changes, test with:
```powershell
# Test with example.com (should work)
python api/test_screenshot.py https://example.com

# Test with a problematic URL
python api/test_screenshot.py <your-url>
```

Expected improvements:
- Desktop screenshots should succeed more often
- If full page fails, viewport-only will be used automatically
- Better error messages help diagnose issues

## 📝 Next Steps

If desktop screenshots still fail after these changes:

1. **Check server logs** for specific error messages
2. **Test with different URLs** to see if it's URL-specific
3. **Check server resources** (RAM, CPU)
4. **Consider using mobile screenshots** if desktop consistently fails for certain websites

The mobile screenshot uses a smaller viewport and different user agent, which may work better for some websites.


