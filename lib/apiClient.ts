/**
 * API Client Configuration
 * 
 * Centralized configuration for backend API endpoints.
 * All API calls should use these constants to ensure consistency.
 */

export const BACKEND_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "https://nima-ai-marketing.onrender.com";

export const IMAGE_TRUST_API_URL = `${BACKEND_BASE_URL}/api/analyze/image-trust`;

export const HEALTH_URL = `${BACKEND_BASE_URL}/health`;

/**
 * Generic POST function to backend API
 * 
 * @param endpoint - API endpoint path (e.g., '/api/brain/cognitive-friction')
 * @param payload - Request body data
 * @returns Promise with the response data
 * @throws Error if the request fails
 */
export async function postToBrain<T = any>(endpoint: string, payload: any): Promise<T> {
  const url = endpoint.startsWith('http') 
    ? endpoint 
    : `${BACKEND_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  
  console.log('[Brain API] Fetching:', url);
  console.log('[Brain API] Payload:', payload);

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorText = await res.text();
    console.error('[Brain API] Error:', res.status, errorText);
    
    // Try to extract meaningful error message from response
    let errorMessage = `API ${res.status} error`;
    try {
      const errorJson = JSON.parse(errorText);
      // Handle FastAPI error format
      if (errorJson?.detail) {
        if (typeof errorJson.detail === 'string') {
          errorMessage = errorJson.detail;
        } else if (errorJson.detail?.message) {
          errorMessage = errorJson.detail.message;
        } else {
          errorMessage = JSON.stringify(errorJson.detail);
        }
      } else if (errorJson?.message) {
        errorMessage = errorJson.message;
      } else if (errorJson?.error) {
        errorMessage = typeof errorJson.error === 'string' 
          ? errorJson.error 
          : JSON.stringify(errorJson.error);
      }
    } catch {
      // If parsing fails, use raw text or status-based message
      if (res.status === 500) {
        errorMessage = errorText || 'Internal server error. Please check backend logs.';
      } else if (res.status === 404) {
        errorMessage = `Endpoint not found: ${endpoint}`;
      } else if (res.status === 503 || res.status === 502) {
        errorMessage = `Backend service unavailable. Please ensure the backend is running on ${BACKEND_BASE_URL}`;
      } else {
        errorMessage = errorText || `HTTP ${res.status} error`;
      }
    }
    
    throw new Error(errorMessage);
  }

  const data = await res.json();
  console.log('✅ Brain API response received');
  return data as T;
}

/**
 * Visual Trust Analysis API
 * 
 * Analyzes the visual trust level of an uploaded image.
 * 
 * @param file - The image file to analyze
 * @returns Promise with the analysis result
 * @throws Error if the request fails
 */
export async function runVisualTrustAnalysis(file: File) {
  const formData = new FormData();
  formData.append("image", file); // field name must be "image" to match backend

  console.log("[VisualTrust] Sending request to", IMAGE_TRUST_API_URL);

  const res = await fetch(IMAGE_TRUST_API_URL, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    console.error("[VisualTrust] Backend error", res.status, res.statusText);
    throw new Error(`Image trust analysis failed with status ${res.status}`);
  }

  const data = await res.json();
  console.log("[VisualTrust] Response", data);
  return data;
}

/**
 * Backend Health Check
 * 
 * Checks if the backend is healthy and available.
 * 
 * @returns Promise with the health status
 * @throws Error if the health check fails
 */
export async function checkBackendHealth() {
  const res = await fetch(HEALTH_URL);
  if (!res.ok) {
    throw new Error("Backend health check failed");
  }
  return res.json();
}

