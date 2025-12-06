# Frontend API Client Update Summary

## ✅ Completed Changes

### 1. API Client Configuration (`lib/apiClient.ts`)

Created/updated the API client with:
- `BACKEND_BASE_URL` constant that reads from `NEXT_PUBLIC_BACKEND_URL` env var
- `IMAGE_TRUST_API_URL` constant for the image trust endpoint
- `HEALTH_URL` constant for the global health endpoint
- `runVisualTrustAnalysis(file: File)` helper function that:
  - Creates FormData with field name "image" (matches backend)
  - Sends POST request to `IMAGE_TRUST_API_URL`
  - Handles errors properly
- `checkBackendHealth()` helper function for health checks

### 2. Environment Variable

**Note:** `.env.local` is gitignored, so you need to create it manually:

Create `.env.local` in the project root with:
```
NEXT_PUBLIC_BACKEND_URL="https://nima-ai-marketing.onrender.com"
```

For local development, you can override this:
```
NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"
```

## 📝 Frontend Component Updates Required

The frontend components that call the image-trust endpoint need to be updated. Based on the search results, these files are in a different workspace:
- `components/VariantA.tsx`
- `components/VariantB.tsx`

### Update Pattern

Replace any existing image-trust calls with:

```typescript
import { runVisualTrustAnalysis, IMAGE_TRUST_API_URL, BACKEND_BASE_URL } from "@/lib/apiClient";

async function runVisualTrustAnalysis(file: File) {
  try {
    const data = await runVisualTrustAnalysis(file);
    console.log("[VisualTrust] Response", data);
    return data;
  } catch (err) {
    console.error('Visual trust analysis error', err);
    throw err;
  }
}
```

### Remove These Patterns

1. **Hardcoded URLs:**
   ```typescript
   // ❌ Remove this
   const url = "https://nima-ai-marketing.onrender.com/api/analyze/image-trust";
   
   // ✅ Use this instead
   import { IMAGE_TRUST_API_URL } from "@/lib/apiClient";
   ```

2. **Image-trust specific health endpoint:**
   ```typescript
   // ❌ Remove this
   fetch("/api/analyze/image-trust/health")
   
   // ✅ Use global health endpoint instead
   import { checkBackendHealth } from "@/lib/apiClient";
   await checkBackendHealth();
   ```

3. **Incorrect field names:**
   ```typescript
   // ❌ Wrong field name
   formData.append("file", file);
   
   // ✅ Correct field name (must be "image")
   formData.append("image", file);
   ```

## 🔍 Key Points

1. **Field Name:** The backend expects the field name to be `"image"` (see `api/routes/image_trust.py` line 191: `file: UploadFile = File(...)`)

2. **No Image-Trust Health Endpoint:** The backend does have `/api/analyze/image-trust/health`, but for consistency, use the global `/health` endpoint for pre-flight checks.

3. **Multipart/Form-Data:** The request must use `multipart/form-data` (automatically set when using FormData with fetch).

4. **Error Handling:** The helper function throws errors that should be caught and handled in the component.

## 🧪 Testing

After updating the frontend components:

1. **Local Development:**
   - Set `NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"` in `.env.local`
   - Start backend: `python -m uvicorn api.main:app --reload`
   - Test image upload

2. **Production:**
   - Ensure `NEXT_PUBLIC_BACKEND_URL="https://nima-ai-marketing.onrender.com"` is set in Vercel environment variables
   - Deploy and test

## 📋 Checklist

- [x] Created `lib/apiClient.ts` with constants and helper functions
- [ ] Create `.env.local` with `NEXT_PUBLIC_BACKEND_URL`
- [ ] Update `components/VariantA.tsx` to use `runVisualTrustAnalysis` from `apiClient.ts`
- [ ] Update `components/VariantB.tsx` to use `runVisualTrustAnalysis` from `apiClient.ts`
- [ ] Remove any hardcoded URLs
- [ ] Remove calls to `/api/analyze/image-trust/health` (use global health endpoint instead)
- [ ] Test locally
- [ ] Deploy to production

