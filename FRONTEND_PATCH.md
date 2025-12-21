# Frontend Patch: Fix Screenshot URL Extraction

## 🔧 Quick Fix for `page.tsx`

Replace lines ~305-309 in `app/ai-marketing/decision-brain/page.tsx`:

### Before:
```typescript
const desktopSrc = data?.screenshots?.desktop_fold || data?.screenshots?.desktop_full || data?.screenshots?.desktop || "";
const mobileSrc = data?.screenshots?.mobile_fold || data?.screenshots?.mobile_full || data?.screenshot?.mobile || data?.screenshots?.mobile || "";

console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
console.log("📥 Mobile source:", mobileSrc ? `${mobileSrc.substring(0, 50)}...` : "NOT FOUND");
```

### After (Option 1 - Using Helper):
```typescript
// Import helper function (copy from lib/screenshot-utils.ts or use inline)
const getScreenshotUrl = (screenshot: any): string => {
  if (!screenshot) return "";
  if (typeof screenshot === "object" && screenshot?.url) {
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
```

### After (Option 2 - Direct):
```typescript
// Direct extraction from new schema
const desktopSrc = data?.screenshots?.desktop?.url || "";
const mobileSrc = data?.screenshots?.mobile?.url || "";

console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
console.log("📥 Mobile source:", mobileSrc ? `${mobileSrc.substring(0, 50)}...` : "NOT FOUND");
```

## 📦 Using the Helper File

1. Copy `lib/screenshot-utils.ts` to your Next.js project
2. Import in your component:

```typescript
import { getDesktopScreenshotUrl, getMobileScreenshotUrl } from '@/lib/screenshot-utils';

// In your component:
const desktopSrc = getDesktopScreenshotUrl(data);
const mobileSrc = getMobileScreenshotUrl(data);
```

## ✅ Complete Example

```typescript
// In handleSubmit function
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
    
    // Extract screenshot URLs (NEW SCHEMA)
    const desktopSrc = data?.screenshots?.desktop?.url || "";
    const mobileSrc = data?.screenshots?.mobile?.url || "";
    
    // Check status
    const desktopStatus = data?.screenshots?.desktop?.status;
    const mobileStatus = data?.screenshots?.mobile?.status;
    
    console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
    console.log("📥 Mobile source:", mobileSrc ? `${mobileSrc.substring(0, 50)}...` : "NOT FOUND");
    console.log("📊 Analysis status:", data?.analysisStatus);
    
    if (desktopStatus === "error") {
      console.warn("⚠️ Desktop screenshot failed:", data?.screenshots?.desktop?.error);
    }
    if (mobileStatus === "error") {
      console.warn("⚠️ Mobile screenshot failed:", data?.screenshots?.mobile?.error);
    }
    
    // Use desktopSrc and mobileSrc in your UI
    // ...
  } catch (error) {
    // ... error handling ...
  }
};
```

## 🎯 Key Changes

1. **Old**: `data.screenshots.desktop` was a string
2. **New**: `data.screenshots.desktop` is an object with `.url` property
3. **Fix**: Use `data.screenshots.desktop.url` instead of `data.screenshots.desktop`

## 📍 File to Update

```
app/ai-marketing/decision-brain/page.tsx
Line ~308: Change screenshot extraction logic
```


