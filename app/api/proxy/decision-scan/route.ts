export async function POST(req: Request) {
  // 🔧 For local development: prioritize localhost
  // Set NEXT_PUBLIC_USE_LOCAL_BACKEND=true to force localhost
  const USE_LOCAL = process.env.NEXT_PUBLIC_USE_LOCAL_BACKEND === "true" || 
                    process.env.NODE_ENV === "development";
  
  const BACKEND_PROD =
    process.env.BACKEND_BASE_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL;
  
  const BACKEND_LOCAL = "http://127.0.0.1:8000";
  
  // In development, prefer localhost unless explicitly set
  const BACKEND = USE_LOCAL ? BACKEND_LOCAL : (BACKEND_PROD || BACKEND_LOCAL);

  const ct = req.headers.get("content-type") || "";

  let url = "";
  let goal: "leads" | "sales" | "booking" | "contact" | "subscribe" | "other" = "other";
  let locale: "fa" | "en" | "tr" = "en";
  let hasFile = false;

  if (ct.includes("multipart/form-data")) {
    const fd = await req.formData();
    url = String(fd.get("url") || "").trim();
    const g = String(fd.get("goal") || "").trim();
    const l = String(fd.get("locale") || "").trim();
    const file = fd.get("file");

    hasFile = !!file;

    if (["leads","sales","booking","contact","subscribe","other"].includes(g)) {
      goal = g as any;
    }
    if (["fa","en","tr"].includes(l)) {
      locale = l as any;
    }
  } else {
    const j: any = await req.json().catch(() => ({}));
    url = String(j.url || "").trim();
    const g = String(j.goal || "").trim();
    const l = String(j.locale || "").trim();

    if (["leads","sales","booking","contact","subscribe","other"].includes(g)) {
      goal = g as any;
    }
    if (["fa","en","tr"].includes(l)) {
      locale = l as any;
    }
  }

  // 🔴 جلوگیری از 422
  if (!url) {
    if (hasFile) {
      return Response.json(
        { status: "error", message: "حالت تصویر فعال است ولی هنوز endpoint تصویری وصل نشده. یا URL بده یا image endpoint را وصل کن." },
        { status: 400 }
      );
    }
    return Response.json(
      { status: "error", message: "فیلد url اجباری است." },
      { status: 400 }
    );
  }

  // ✅ ارسال صحیح به بک‌اند با timeout و fallback
  // /api/decision-scan requires 'mode' field
  const payload = { mode: "url", url, goal, locale };
  
  // Create AbortController for timeout (compatible with older Node.js)
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
  
  const fetchOptions = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: controller.signal,
  };

  let r: Response;
  let backendUsed = BACKEND;

  try {
    // Try production backend first - use /api/decision-scan endpoint
    r = await fetch(`${BACKEND}/api/decision-scan`, fetchOptions);
    clearTimeout(timeoutId); // Clear timeout on success
  } catch (error: any) {
    clearTimeout(timeoutId); // Clear timeout on error
    // If production fails and we're not already using localhost, try localhost
    if (BACKEND !== BACKEND_LOCAL && (error.code === "UND_ERR_CONNECT_TIMEOUT" || error.name === "TimeoutError" || error.message?.includes("timeout") || error.name === "AbortError")) {
      console.warn(`[Proxy] Production backend timeout, falling back to localhost: ${error.message}`);
      // Create new controller for localhost attempt
      const localController = new AbortController();
      const localTimeoutId = setTimeout(() => localController.abort(), 15000);
      try {
        r = await fetch(`${BACKEND_LOCAL}/api/decision-scan`, {
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
            message: `Backend connection failed. Production: ${error.message}, Localhost: ${localError.message}`,
            debug: {
              production_backend: BACKEND,
              local_backend: BACKEND_LOCAL,
              error: error.message,
            },
          },
          { status: 503 }
        );
      }
    } else {
      return Response.json(
        {
          status: "error",
          message: `Backend connection failed: ${error.message}`,
          debug: {
            backend: BACKEND,
            error: error.message,
            code: error.code,
          },
        },
        { status: 503 }
      );
    }
  }

  const text = await r.text();
  return new Response(text, {
    status: r.status,
    headers: { 
      "Content-Type": r.headers.get("content-type") || "application/json",
      "X-Backend-Used": backendUsed,
    },
  });
}


