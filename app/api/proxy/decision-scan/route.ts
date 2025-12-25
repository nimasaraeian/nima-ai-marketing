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

  // 2) Route to correct backend endpoint
  let backendEndpoint = "";
  
  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
  
  let fetchOptions: RequestInit = {
    method: "POST",
    signal: controller.signal,
  };

  if (mode === "image") {
    backendEndpoint = `${BACKEND}/api/analyze/image-human`;
    
    if (isMultipart && formData) {
      // Forward FormData directly (DO NOT set Content-Type - let fetch handle boundary)
      fetchOptions.body = formData;
      // DO NOT set Content-Type header - browser will set it with boundary
    } else {
      // JSON mode with image (base64 or URL)
      fetchOptions.headers = { "Content-Type": "application/json" };
      fetchOptions.body = JSON.stringify({
        image: jsonBody.image || jsonBody.file,
        goal: goal,
        locale: locale
      });
    }
  } else if (mode === "text") {
    backendEndpoint = `${BACKEND}/api/analyze/text-human`;
    
    if (isMultipart && formData) {
      // Forward FormData directly
      fetchOptions.body = formData;
    } else {
      fetchOptions.headers = { "Content-Type": "application/json" };
      fetchOptions.body = JSON.stringify({
        text: jsonBody.text,
        goal: goal,
        locale: locale
      });
    }
  } else {
    // URL mode
    backendEndpoint = `${BACKEND}/api/analyze/url-human`;
    
    if (isMultipart && formData) {
      // Convert FormData to JSON for URL endpoint (it expects JSON)
      fetchOptions.headers = { "Content-Type": "application/json" };
      fetchOptions.body = JSON.stringify({
        url: formData.get("url"),
        goal: goal,
        locale: locale
      });
    } else {
      fetchOptions.headers = { "Content-Type": "application/json" };
      fetchOptions.body = JSON.stringify({
        url: jsonBody.url,
        goal: goal,
        locale: locale
      });
    }
  }

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

  // 4) Return backend response transparently
  const responseText = await response.text();
  
  // Parse response to check for fake reports
  try {
    const responseJson = JSON.parse(responseText);
    
    // If status is error, validate it doesn't contain fake report content
    if (responseJson.status === "error") {
      const humanReport = responseJson.human_report || responseJson.report || "";
      const fakeMarkers = ["CTA Recommendations", "Personas", "Decision Friction"];
      const hasFakeMarkers = fakeMarkers.some(marker => humanReport.includes(marker));
      
      if (hasFakeMarkers) {
        // Error response should not contain report content
        return Response.json(
          {
            status: "error",
            stage: "report_validation",
            message: "Error response contains invalid report content. Please try again.",
            debug: {
              mode: mode,
              endpoint: backendEndpoint,
            },
          },
          { status: 500 }
        );
      }
      
      // Error responses without fake content are OK - return as-is
      return new Response(responseText, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          "X-Backend-Used": backendUsed,
          "X-Mode": mode,
        },
      });
    }
    
    // For success responses, check for empty/null reports
    const humanReport = responseJson.human_report || responseJson.report || "";
    
    // Check for null report field
    if (responseJson.report === null && !responseJson.human_report) {
      return Response.json(
        {
          status: "error",
          stage: "report_validation",
          message: "Backend returned null report. Please try again.",
          debug: {
            mode: mode,
            endpoint: backendEndpoint,
          },
        },
        { status: 500 }
      );
    }
    
    // Check for empty report
    if (!humanReport || humanReport.trim().length === 0) {
      return Response.json(
        {
          status: "error",
          stage: "report_validation",
          message: "Backend returned empty report. Please try again.",
          debug: {
            mode: mode,
            endpoint: backendEndpoint,
          },
        },
        { status: 500 }
      );
    }
    
    // Check for fake content without corresponding data structures
    const hasFakeContent = 
      (humanReport.includes("CTA Recommendations") && !responseJson.cta_recommendations) ||
      (humanReport.includes("Personas") && !responseJson.mindset_personas);
    
    if (hasFakeContent) {
      console.warn(`[Proxy] Detected fake content in report for mode: ${mode}`);
      // Don't block, but log warning
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
