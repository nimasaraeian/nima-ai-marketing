# Fix: desktopSrc.substring is not a function

## 🔍 Problem

Frontend code expects `screenshots.desktop` to be a string (URL), but the new API schema returns an object:

**Old Schema (deprecated):**
```json
{
  "screenshots": {
    "desktop": "/static/shots/hero.png",  // ❌ String
    "mobile": "/static/shots/mobile.png"  // ❌ String
  }
}
```

**New Schema (current):**
```json
{
  "screenshots": {
    "desktop": {
      "status": "ok",
      "mode": "above_fold",
      "viewport": [1365, 768],
      "path": "api/debug_shots/desktop_20241220_143022.png",
      "url": "/api/debug_shots/desktop_20241220_143022.png",  // ✅ String inside object
      "error": null
    },
    "mobile": {
      "status": "ok",
      "mode": "above_fold",
      "viewport": [390, 844],
      "path": "api/debug_shots/mobile_20241220_143022.png",
      "url": "/api/debug_shots/mobile_20241220_143022.png",  // ✅ String inside object
      "error": null
    }
  }
}
```

## 🔧 Solution

Update the frontend code in `app/ai-marketing/decision-brain/page.tsx`:

### Before (Line 305-309):
```typescript
const desktopSrc = data?.screenshots?.desktop_fold || data?.screenshots?.desktop_full || data?.screenshots?.desktop || "";
const mobileSrc = data?.screenshots?.mobile_fold || data?.screenshots?.mobile_full || data?.screenshot?.mobile || data?.screenshots?.mobile || "";

console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
console.log("📥 Mobile source:", mobileSrc ? `${mobileSrc.substring(0, 50)}...` : "NOT FOUND");
```

### After (Fixed):
```typescript
// Extract URL from new schema (object with .url property)
// Support both old schema (string) and new schema (object)
const getScreenshotUrl = (screenshot: any): string => {
  if (!screenshot) return "";
  // New schema: object with .url property
  if (typeof screenshot === "object" && screenshot.url) {
    return screenshot.url;
  }
  // Old schema: direct string (backward compatibility)
  if (typeof screenshot === "string") {
    return screenshot;
  }
  return "";
};

const desktopSrc = getScreenshotUrl(
  data?.screenshots?.desktop || 
  data?.screenshots?.desktop_fold || 
  data?.screenshots?.desktop_full || 
  ""
);

const mobileSrc = getScreenshotUrl(
  data?.screenshots?.mobile || 
  data?.screenshots?.mobile_fold || 
  data?.screenshots?.mobile_full || 
  data?.screenshot?.mobile || 
  ""
);

console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
console.log("📥 Mobile source:", mobileSrc ? `${mobileSrc.substring(0, 50)}...` : "NOT FOUND");
```

## 📝 Alternative: Simpler Version

If you want a simpler fix without backward compatibility:

```typescript
// New schema only
const desktopSrc = data?.screenshots?.desktop?.url || "";
const mobileSrc = data?.screenshots?.mobile?.url || "";

console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
console.log("📥 Mobile source:", mobileSrc ? `${mobileSrc.substring(0, 50)}...` : "NOT FOUND");
```

## ✅ Additional Checks

You may also want to check screenshot status:

```typescript
const desktopStatus = data?.screenshots?.desktop?.status || "unknown";
const mobileStatus = data?.screenshots?.mobile?.status || "unknown";

if (desktopStatus === "error") {
  console.warn("Desktop screenshot failed:", data?.screenshots?.desktop?.error);
}
if (mobileStatus === "error") {
  console.warn("Mobile screenshot failed:", data?.screenshots?.mobile?.error);
}
```

## 🔄 Full Example

Complete fix for the `handleSubmit` function:

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  
  // ... existing code ...
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze/url-human`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: urlInput, goal, locale }),
    });
    
    const data = await response.json();
    
    // Extract screenshot URLs (support both old and new schema)
    const getScreenshotUrl = (screenshot: any): string => {
      if (!screenshot) return "";
      if (typeof screenshot === "object" && screenshot.url) {
        return screenshot.url;
      }
      if (typeof screenshot === "string") {
        return screenshot;
      }
      return "";
    };
    
    const desktopSrc = getScreenshotUrl(data?.screenshots?.desktop);
    const mobileSrc = getScreenshotUrl(data?.screenshots?.mobile);
    
    console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
    console.log("📥 Mobile source:", mobileSrc ? `${mobileSrc.substring(0, 50)}...` : "NOT FOUND");
    
    // Check analysis status
    const analysisStatus = data?.analysisStatus || "unknown";
    if (analysisStatus === "partial") {
      console.warn("⚠️ Partial analysis - some screenshots failed");
      console.log("Missing data:", data?.missing_data);
    }
    
    // ... rest of your code ...
  } catch (error) {
    // ... error handling ...
  }
};
```

## 🎯 Key Points

1. **New schema**: `screenshots.desktop` is an object, not a string
2. **URL location**: Use `screenshots.desktop.url` to get the URL string
3. **Status check**: Use `screenshots.desktop.status` to check if screenshot succeeded
4. **Error handling**: Check `screenshots.desktop.error` if status is "error"
5. **Backward compatibility**: The helper function supports both old and new schemas

## 📍 File Location

Update this file in your Next.js project:
```
app/ai-marketing/decision-brain/page.tsx
```

Line ~308: Change how `desktopSrc` and `mobileSrc` are extracted from the API response.


