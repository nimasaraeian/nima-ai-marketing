# Fix for `lib/api.ts` Error: errorDetail.slice is not a function

## Problem
In `lib/api.ts` at line 87, the code tries to call `errorDetail.slice(0, 500)` but `errorDetail` is not always a string - it might be an object from the API response.

## Error Location
```typescript
// lib/api.ts:87
throw new Error(`API ${res.status}: ${errorDetail.slice(0, 500)}`);
```

## Solution

Replace the error handling code in `lib/api.ts` with this safe version:

```typescript
// Before (line ~85-87):
const errorDetail = await res.text();
if (!res.ok) {
  throw new Error(`API ${res.status}: ${errorDetail.slice(0, 500)}`);
}

// After (fixed):
const errorText = await res.text();
let errorDetail: string;

try {
  // Try to parse as JSON first
  const errorJson = JSON.parse(errorText);
  
  // Handle different error formats
  if (typeof errorJson === 'string') {
    errorDetail = errorJson;
  } else if (errorJson?.detail) {
    // FastAPI error format: { detail: "..." } or { detail: { message: "..." } }
    if (typeof errorJson.detail === 'string') {
      errorDetail = errorJson.detail;
    } else if (errorJson.detail?.message) {
      errorDetail = errorJson.detail.message;
    } else if (errorJson.detail?.type && errorJson.detail?.message) {
      errorDetail = errorJson.detail.message;
    } else {
      errorDetail = JSON.stringify(errorJson.detail, null, 2);
    }
  } else if (errorJson?.message) {
    errorDetail = errorJson.message;
  } else if (errorJson?.error) {
    errorDetail = typeof errorJson.error === 'string' 
      ? errorJson.error 
      : JSON.stringify(errorJson.error, null, 2);
  } else {
    errorDetail = JSON.stringify(errorJson, null, 2);
  }
} catch {
  // If parsing fails, use the raw text
  errorDetail = errorText;
}

if (!res.ok) {
  // Ensure errorDetail is a string before calling slice
  const errorMessage = typeof errorDetail === 'string' 
    ? errorDetail.slice(0, 500) 
    : String(errorDetail).slice(0, 500);
  throw new Error(`API ${res.status}: ${errorMessage}`);
}
```

## Simpler Alternative (Recommended)

If you prefer a simpler approach, use a helper function:

```typescript
// Add this helper function at the top of lib/api.ts
function getErrorMessage(errorText: string): string {
  try {
    const errorJson = JSON.parse(errorText);
    
    // Handle FastAPI error format
    if (errorJson?.detail) {
      if (typeof errorJson.detail === 'string') {
        return errorJson.detail;
      }
      if (errorJson.detail?.message) {
        return errorJson.detail.message;
      }
      return JSON.stringify(errorJson.detail, null, 2);
    }
    
    // Handle other formats
    if (errorJson?.message) {
      return errorJson.message;
    }
    if (errorJson?.error) {
      return typeof errorJson.error === 'string' 
        ? errorJson.error 
        : JSON.stringify(errorJson.error, null, 2);
    }
    
    return JSON.stringify(errorJson, null, 2);
  } catch {
    // If parsing fails, return raw text
    return errorText;
  }
}

// Then in your postJSON function (around line 85-87):
const errorText = await res.text();
if (!res.ok) {
  const errorMessage = getErrorMessage(errorText);
  throw new Error(`API ${res.status}: ${errorMessage.slice(0, 500)}`);
}
```

## Quick Fix (One-liner)

If you want the quickest fix, just ensure it's a string:

```typescript
// Line ~85-87:
const errorDetail = await res.text();
if (!res.ok) {
  const errorMsg = typeof errorDetail === 'string' 
    ? errorDetail 
    : JSON.stringify(errorDetail);
  throw new Error(`API ${res.status}: ${errorMsg.slice(0, 500)}`);
}
```

## Why This Happens

FastAPI (and many APIs) can return errors in different formats:
- **String**: `"Error message"`
- **Object with detail**: `{ detail: "Error message" }`
- **Nested object**: `{ detail: { type: "...", message: "..." } }`
- **Object with message**: `{ message: "Error message" }`

The fix handles all these cases safely by:
1. Trying to parse as JSON
2. Extracting the message from various possible structures
3. Falling back to string conversion if all else fails

## Full Example Function

Here's a complete example of how the `postJSON` function should look:

```typescript
async function postJSON<T>(url: string, body: any): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  const text = await res.text();
  
  if (!res.ok) {
    let errorMessage: string;
    
    try {
      const errorJson = JSON.parse(text);
      
      // Handle FastAPI error format
      if (errorJson?.detail) {
        if (typeof errorJson.detail === 'string') {
          errorMessage = errorJson.detail;
        } else if (errorJson.detail?.message) {
          errorMessage = errorJson.detail.message;
        } else {
          errorMessage = JSON.stringify(errorJson.detail, null, 2);
        }
      } else if (errorJson?.message) {
        errorMessage = errorJson.message;
      } else {
        errorMessage = JSON.stringify(errorJson, null, 2);
      }
    } catch {
      // If parsing fails, use raw text
      errorMessage = text;
    }
    
    throw new Error(`API ${res.status}: ${errorMessage.slice(0, 500)}`);
  }

  return text ? (JSON.parse(text) as T) : ({} as T);
}
```








