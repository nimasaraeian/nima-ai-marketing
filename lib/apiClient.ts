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

