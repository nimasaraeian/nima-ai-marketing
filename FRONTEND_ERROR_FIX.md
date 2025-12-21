# Fix for Frontend Error: error.split is not a function

## Problem
In `app/ai-marketing/decision-brain/page.tsx` at line 152, the code tries to call `error.split('\n')` but `error` is not a string - it's likely an object from the API response.

## Solution

Replace the error handling code with this:

```tsx
// Before (line 150-155):
<p className="text-sm font-medium text-red-400 mb-2">Error</p>
<div className="text-sm text-red-300 whitespace-pre-wrap break-words">
  {error.split('\n').map((line, index) => (
    <p key={index} className={index > 0 ? 'mt-2' : ''}>
      {line}
    </p>
  ))}
</div>

// After (fixed):
<p className="text-sm font-medium text-red-400 mb-2">Error</p>
<div className="text-sm text-red-300 whitespace-pre-wrap break-words">
  {(() => {
    // Convert error to string safely
    let errorMessage = '';
    if (typeof error === 'string') {
      errorMessage = error;
    } else if (error?.message) {
      errorMessage = error.message;
    } else if (error?.detail) {
      // Handle FastAPI error format
      if (typeof error.detail === 'string') {
        errorMessage = error.detail;
      } else if (error.detail?.message) {
        errorMessage = error.detail.message;
      } else {
        errorMessage = JSON.stringify(error.detail, null, 2);
      }
    } else if (error) {
      errorMessage = JSON.stringify(error, null, 2);
    } else {
      errorMessage = 'An unknown error occurred';
    }
    
    return errorMessage.split('\n').map((line, index) => (
      <p key={index} className={index > 0 ? 'mt-2' : ''}>
        {line}
      </p>
    ));
  })()}
</div>
```

## Alternative Simpler Solution (Recommended)

If you prefer a simpler approach, use a helper function:

```tsx
// Add this helper function at the top of your component or in a utils file
function getErrorMessage(error: any): string {
  if (typeof error === 'string') {
    return error;
  }
  if (error?.message) {
    return error.message;
  }
  if (error?.detail) {
    // Handle FastAPI error format: { detail: "..." } or { detail: { message: "..." } }
    if (typeof error.detail === 'string') {
      return error.detail;
    }
    if (error.detail?.message) {
      return error.detail.message;
    }
    // Handle our custom format: { detail: { type: "...", message: "..." } }
    if (error.detail?.type && error.detail?.message) {
      return error.detail.message;
    }
    return JSON.stringify(error.detail, null, 2);
  }
  if (error) {
    return JSON.stringify(error, null, 2);
  }
  return 'An unknown error occurred';
}

// Then use it in your JSX:
<p className="text-sm font-medium text-red-400 mb-2">Error</p>
<div className="text-sm text-red-300 whitespace-pre-wrap break-words">
  {getErrorMessage(error).split('\n').map((line, index) => (
    <p key={index} className={index > 0 ? 'mt-2' : ''}>
      {line}
    </p>
  ))}
</div>
```

## Quick Fix (One-liner)

If you want the quickest fix, just convert error to string:

```tsx
<p className="text-sm font-medium text-red-400 mb-2">Error</p>
<div className="text-sm text-red-300 whitespace-pre-wrap break-words">
  {String(error?.detail?.message || error?.detail || error?.message || error || 'Unknown error')
    .split('\n')
    .map((line, index) => (
      <p key={index} className={index > 0 ? 'mt-2' : ''}>
        {line}
      </p>
    ))}
</div>
```

## Why This Happens

The API might return errors in different formats:
- String: `"Error message"`
- Object with message: `{ message: "Error message" }`
- FastAPI error format: `{ detail: "Error message" }` or `{ detail: { type: "...", message: "..." } }`

The fix handles all these cases safely.

