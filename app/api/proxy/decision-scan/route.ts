// Type definitions for unified human analysis response
type HumanAnalyzeResponse = {
  status: "ok" | "error";
  mode: "url" | "image" | "text";
  goal: string;
  human_report: string;
  page_map?: any;
  summary?: {
    url?: string | null;
    goal: string;
    locale: string;
    headlines_count?: number;
    ctas_count?: number;
    issues_count?: number;
    quick_wins_count?: number;
  };
  issues?: Array<{
    title?: string;
    problem?: string;
    why_it_hurts?: string;
    location?: string;
    fix?: string;
    severity?: string;
  }>;
  quick_wins?: Array<{
    action: string;
    where?: { section?: string; selector?: string };
    reason?: string;
  }>;
  issues_count?: number;
  quick_wins_count?: number;
  screenshots?: any;
  debug?: any;
  // Legacy fields for backward compatibility
  report?: string;
  findings?: {
    top_issues?: any[];
    quick_wins?: any[];
  };
  decision_psychology_insight?: any;
  cta_recommendations?: any;
};

export async function POST(req: Request) {
  // 🔧 For local development: prioritize localhost
  const USE_LOCAL = process.env.NEXT_PUBLIC_USE_LOCAL_BACKEND === "true" || 
                    process.env.NODE_ENV === "development";
  
  const BACKEND_PROD =
    process.env.BACKEND_BASE_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL;
  
  const BACKEND_LOCAL = "http://127.0.0.1:8000";
  const BACKEND = USE_LOCAL ? BACKEND_LOCAL : (BACKEND_PROD || BACKEND_LOCAL);

  const contentType = req.headers.get("content-type") || "";
  const isMultipart = contentType.includes("multipart/form-data");

  let mode: "url" | "image" | "text" = "url";
  let goal: "leads" | "sales" | "booking" | "contact" | "subscribe" | "other" = "other";
  let locale: "fa" | "en" | "tr" = "en";
  let formData: FormData | null = null;
  let jsonBody: any = null;

  // 1) Detect content-type and parse accordingly
  if (isMultipart) {
    // Parse FormData (DO NOT parse as JSON)
    formData = await req.formData();
    
    // Extract fields
    const urlField = formData.get("url");
    const textField = formData.get("text");
    const imageFile = formData.get("image") || formData.get("file");
    const goalField = formData.get("goal");
    const localeField = formData.get("locale");

    // Detect mode
    if (imageFile && imageFile instanceof File) {
      mode = "image";
    } else if (textField && String(textField).trim()) {
      mode = "text";
    } else if (urlField && String(urlField).trim()) {
      mode = "url";
    }

    // Parse goal and locale
    if (goalField && ["leads","sales","booking","contact","subscribe","other"].includes(String(goalField))) {
      goal = goalField as any;
    }
    if (localeField && ["fa","en","tr"].includes(String(localeField))) {
      locale = localeField as any;
    }

    // Validation: must have at least one input
    if (mode === "url" && (!urlField || !String(urlField).trim())) {
      return Response.json(
        { status: "error", stage: "validation", message: "URL field is required for URL mode." },
        { status: 400 }
      );
    }
    if (mode === "text" && (!textField || !String(textField).trim())) {
      return Response.json(
        { status: "error", stage: "validation", message: "Text field is required for text mode." },
        { status: 400 }
      );
    }
    if (mode === "image" && !imageFile) {
      return Response.json(
        { status: "error", stage: "validation", message: "Image file is required for image mode." },
        { status: 400 }
      );
    }
  } else {
    // JSON request
    try {
      jsonBody = await req.json();
    } catch (e) {
      return Response.json(
        { status: "error", stage: "validation", message: "Invalid JSON body." },
        { status: 400 }
      );
    }

    // Detect mode from JSON
    if (jsonBody.image || jsonBody.file) {
      mode = "image";
    } else if (jsonBody.text && String(jsonBody.text).trim()) {
      mode = "text";
    } else if (jsonBody.url && String(jsonBody.url).trim()) {
      mode = "url";
    }

    // Parse goal and locale
    if (jsonBody.goal && ["leads","sales","booking","contact","subscribe","other"].includes(jsonBody.goal)) {
      goal = jsonBody.goal;
    }
    if (jsonBody.locale && ["fa","en","tr"].includes(jsonBody.locale)) {
      locale = jsonBody.locale;
    }

    // Validation
    if (mode === "url" && (!jsonBody.url || !String(jsonBody.url).trim())) {
      return Response.json(
        { status: "error", stage: "validation", message: "URL field is required for URL mode." },
        { status: 400 }
      );
    }
    if (mode === "text" && (!jsonBody.text || !String(jsonBody.text).trim())) {
      return Response.json(
        { status: "error", stage: "validation", message: "Text field is required for text mode." },
        { status: 400 }
      );
    }
    if (mode === "image" && !jsonBody.image && !jsonBody.file) {
      return Response.json(
        { status: "error", stage: "validation", message: "Image field is required for image mode." },
        { status: 400 }
      );
    }
  }

  // 2) Route to unified backend endpoint
  const backendEndpoint = `${BACKEND}/api/analyze/human`;
  
  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
  
  let fetchOptions: RequestInit = {
    method: "POST",
    signal: controller.signal,
  };

  // Build FormData for unified endpoint (always use multipart/form-data)
  const unifiedFormData = new FormData();
  unifiedFormData.append("goal", goal);
  unifiedFormData.append("locale", locale);
  
  if (mode === "image") {
    if (isMultipart && formData) {
      const imageFile = formData.get("image") || formData.get("file");
      if (imageFile && imageFile instanceof File) {
        unifiedFormData.append("image", imageFile);
      }
    } else if (jsonBody.image || jsonBody.file) {
      // JSON mode with image - convert to File if possible, or skip
      // Note: base64 images would need special handling, but unified endpoint expects File
      console.warn("[Proxy] JSON image mode not fully supported - use multipart/form-data");
    }
  } else if (mode === "text") {
    if (isMultipart && formData) {
      const textField = formData.get("text");
      if (textField) {
        unifiedFormData.append("text", String(textField));
      }
    } else if (jsonBody.text) {
      unifiedFormData.append("text", String(jsonBody.text));
    }
  } else {
    // URL mode
    if (isMultipart && formData) {
      const urlField = formData.get("url");
      if (urlField) {
        unifiedFormData.append("url", String(urlField));
      }
    } else if (jsonBody.url) {
      unifiedFormData.append("url", String(jsonBody.url));
    }
  }
  
  // Always use FormData for unified endpoint (DO NOT set Content-Type - browser will set boundary)
  fetchOptions.body = unifiedFormData;

  // 3) Make request with fallback
  let response: Response;
  let backendUsed = BACKEND;

  try {
    response = await fetch(backendEndpoint, fetchOptions);
    clearTimeout(timeoutId); // Clear timeout on success
  } catch (error: any) {
    clearTimeout(timeoutId); // Clear timeout on error
    // Fallback to localhost if production fails
    if (BACKEND !== BACKEND_LOCAL && (error.code === "UND_ERR_CONNECT_TIMEOUT" || error.name === "TimeoutError" || error.message?.includes("timeout") || error.name === "AbortError")) {
      console.warn(`[Proxy] Production backend timeout, falling back to localhost: ${error.message}`);
      
      const localEndpoint = backendEndpoint.replace(BACKEND, BACKEND_LOCAL);
      const localController = new AbortController();
      const localTimeoutId = setTimeout(() => localController.abort(), 60000);
      
      try {
        response = await fetch(localEndpoint, {
          ...fetchOptions,
          signal: localController.signal,
        });
        clearTimeout(localTimeoutId);
        backendUsed = BACKEND_LOCAL;
      } catch (localError: any) {
        clearTimeout(localTimeoutId);
        return Response.json(
          {
            status: "error",
            stage: "connection",
            message: `Backend connection failed. Production: ${error.message}, Localhost: ${localError.message}`,
            debug: {
              production_backend: BACKEND,
              local_backend: BACKEND_LOCAL,
              endpoint: backendEndpoint,
            },
          },
          { status: 503 }
        );
      }
    } else {
      return Response.json(
        {
          status: "error",
          stage: "connection",
          message: `Backend connection failed: ${error.message}`,
          debug: {
            backend: BACKEND,
            endpoint: backendEndpoint,
            error: error.message,
            code: error.code,
          },
        },
        { status: 503 }
      );
    }
  }

  // 4) Return backend response transparently with validation
  const responseText = await response.text();
  
  // Parse response to check for fake reports
  try {
    const responseJson: HumanAnalyzeResponse = JSON.parse(responseText);
    
    // Debug log for smoke test
    console.log("Unified response keys:", Object.keys(responseJson));
    
    // If status is error, pass through cleanly (DO NOT construct fallback payload)
    if (responseJson.status === "error") {
      // Validate error response doesn't contain fake report content
      const humanReport = responseJson.human_report || responseJson.report || "";
      if (humanReport && humanReport.trim().length > 0) {
        // Error responses should not contain report content
        const fakeMarkers = ["CTA Recommendations", "Personas", "Decision Friction"];
        const hasFakeMarkers = fakeMarkers.some(marker => humanReport.includes(marker));
        
        if (hasFakeMarkers) {
          return Response.json(
            {
              status: "error",
              stage: "proxy_report_validation",
              message: "Backend error response contains invalid report content.",
              details: {
                mode: mode,
                endpoint: backendEndpoint,
              },
            },
            { status: 500 }
          );
        }
      }
      
      // Clean error response - pass through as-is
      return new Response(responseText, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          "X-Backend-Used": backendUsed,
          "X-Mode": mode,
        },
      });
    }
    
    // For success responses, STRICT validation
    if (responseJson.status === "ok") {
      const humanReport = responseJson.human_report || responseJson.report || "";
      
      // Validation 1: human_report must exist and be non-empty
      if (!humanReport || humanReport.trim().length === 0) {
        return Response.json(
          {
            status: "error",
            stage: "proxy_report_validation",
            message: "Backend returned empty report. Please try again.",
            details: {
              mode: mode,
              endpoint: backendEndpoint,
            },
          },
          { status: 500 }
        );
      }
      
      // Validation 2: human_report must be at least 200 characters
      if (humanReport.trim().length < 200) {
        return Response.json(
          {
            status: "error",
            stage: "proxy_report_validation",
            message: `Backend returned report too short (${humanReport.trim().length} chars, minimum 200).`,
            details: {
              mode: mode,
              endpoint: backendEndpoint,
            },
          },
          { status: 500 }
        );
      }
      
      // Validation 3: Check for null report field
      if (responseJson.report === null && !responseJson.human_report) {
        return Response.json(
          {
            status: "error",
            stage: "proxy_report_validation",
            message: "Backend returned null report. Please try again.",
            details: {
              mode: mode,
              endpoint: backendEndpoint,
            },
          },
          { status: 500 }
        );
      }
      
      // Validation 4: Check for fake template markers
      const fakeMarkers = {
        headline: "Decision Friction Detected",
        primary_cta: "See Why Users Hesitate",
        secondary_cta: "Learn More"
      };
      
      // Check decision_psychology_insight
      const insight = responseJson.decision_psychology_insight;
      if (insight && typeof insight === "object" && insight.headline === fakeMarkers.headline) {
        return Response.json(
          {
            status: "error",
            stage: "fake_report_detected",
            message: "Fake template detected: decision_psychology_insight.headline == 'Decision Friction Detected'",
            details: {
              mode: mode,
              endpoint: backendEndpoint,
            },
          },
          { status: 500 }
        );
      }
      
      // Check CTA recommendations
      const ctaRecs = responseJson.cta_recommendations;
      if (ctaRecs && typeof ctaRecs === "object") {
        if (ctaRecs.primary && ctaRecs.primary.label === fakeMarkers.primary_cta) {
          return Response.json(
            {
              status: "error",
              stage: "fake_report_detected",
              message: "Fake template detected: primary CTA label == 'See Why Users Hesitate'",
              details: {
                mode: mode,
                endpoint: backendEndpoint,
              },
            },
            { status: 500 }
          );
        }
        
        if (Array.isArray(ctaRecs.secondary)) {
          for (const sec of ctaRecs.secondary) {
            if (sec && sec.label === fakeMarkers.secondary_cta) {
              return Response.json(
                {
                  status: "error",
                  stage: "fake_report_detected",
                  message: "Fake template detected: secondary CTA label == 'Learn More'",
                  details: {
                    mode: mode,
                    endpoint: backendEndpoint,
                  },
                },
                { status: 500 }
              );
            }
          }
        }
      }
    }
  } catch (e) {
    // If response is not JSON, return as-is (might be HTML error page)
    console.warn(`[Proxy] Failed to parse response as JSON: ${e}`);
  }

  return new Response(responseText, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") || "application/json",
      "X-Backend-Used": backendUsed,
      "X-Mode": mode,
    },
  });
}
