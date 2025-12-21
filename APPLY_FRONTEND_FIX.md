# Apply Frontend Fix - Quick Guide

## 🚀 Automatic Fix (Recommended)

### Option 1: PowerShell Script (Windows)
```powershell
cd N:\nima-ai-marketing
.\scripts\patch-frontend-screenshots.ps1
```

### Option 2: Node.js Script (Cross-platform)
```bash
cd N:\nima-ai-marketing
node scripts/patch-frontend-screenshots.js
```

## 📝 Manual Fix

If automatic scripts don't work, manually update the file:

**File**: `app/ai-marketing/decision-brain/page.tsx` (in your Next.js project)

**Find** (around line 305-309):
```typescript
const desktopSrc = data?.screenshots?.desktop_fold || data?.screenshots?.desktop_full || data?.screenshots?.desktop || "";
const mobileSrc = data?.screenshots?.mobile_fold || data?.screenshots?.mobile_full || data?.screenshot?.mobile || data?.screenshots?.mobile || "";

console.log("📥 Desktop source:", desktopSrc ? `${desktopSrc.substring(0, 50)}...` : "NOT FOUND");
```

**Replace with**:
```typescript
// Extract screenshot URLs (supports new schema: object with .url property)
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

## ✅ Verification

After applying the fix, the error should be resolved. The code now:
1. ✅ Checks if screenshot is an object with `.url` property (new schema)
2. ✅ Falls back to string if it's a direct string (old schema compatibility)
3. ✅ Safely extracts the URL string for `.substring()` call

## 📦 Helper File Available

A TypeScript helper is available at `lib/screenshot-utils.ts` that you can copy to your Next.js project for cleaner code.


