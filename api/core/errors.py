"""
Standardized error handling for FastAPI application.

All errors must follow a strict, frontend-friendly contract:
{
  "status": "error",
  "message": "<human readable string>",
  "stage": "<pipeline stage or module>",
  "hint": "<optional recovery hint>"
}
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Any

logger = logging.getLogger(__name__)


def error_payload(message: str, stage: str = "unknown", hint: str | None = None) -> dict[str, Any]:
    """
    Create standardized error payload.
    
    Args:
        message: Human-readable error message (MUST be a string)
        stage: Pipeline stage or module where error occurred
        hint: Optional recovery hint for the user
        
    Returns:
        Standardized error payload dict
    """
    payload = {
        "status": "error",
        "message": str(message),  # Ensure it's always a string
        "stage": str(stage),
    }
    if hint:
        payload["hint"] = str(hint)
    return payload


def _extract_message_from_detail(detail: Any) -> str:
    """
    Extract human-readable message from HTTPException detail.
    
    Handles:
    - String details: returns as-is
    - Dict details: extracts message field or converts to string
    - Other types: converts to string
    
    Args:
        detail: The detail from HTTPException
        
    Returns:
        Human-readable string message
    """
    if isinstance(detail, str):
        return detail
    elif isinstance(detail, dict):
        # Try to extract message field
        if "message" in detail:
            return str(detail["message"])
        elif "error" in detail and isinstance(detail["error"], dict) and "message" in detail["error"]:
            return str(detail["error"]["message"])
        else:
            # Convert dict to readable string
            # Avoid returning [object Object] by creating a meaningful message
            if "status" in detail and detail.get("status") == "error":
                # Already in error format, extract message
                return detail.get("message", "Request failed")
            # Generic dict conversion
            return "Request failed"
    else:
        # Convert other types to string
        return str(detail) if detail else "Request failed"


def _infer_stage_from_message(message: str, status_code: int, path: str) -> str:
    """
    Infer pipeline stage from error message, status code, and path.
    
    Args:
        message: Error message
        path: Request path
        
    Returns:
        Inferred stage name
    """
    message_lower = message.lower()
    path_lower = path.lower()
    
    # Check path for stage hints
    if "/api/analyze/human" in path_lower:
        if "extraction" in message_lower or "extract" in message_lower:
            return "extraction"
        elif "report" in message_lower or "generation" in message_lower or "decision" in message_lower:
            return "decision_engine"
        elif "validation" in message_lower or "input" in message_lower or "provide" in message_lower:
            return "validation"
        elif "pipeline" in message_lower:
            return "pipeline"
    
    # Check status code
    if status_code == 422:
        return "validation"
    elif status_code == 400:
        return "input_validation"
    elif status_code == 404:
        return "resource_not_found"
    elif status_code == 403:
        return "authorization"
    
    # Check message patterns
    if "validation" in message_lower or "invalid" in message_lower or "missing" in message_lower:
        return "validation"
    elif "extraction" in message_lower or "extract" in message_lower:
        return "extraction"
    elif "report" in message_lower or "generation" in message_lower:
        return "decision_engine"
    elif "timeout" in message_lower:
        return "timeout"
    elif "connection" in message_lower or "connect" in message_lower:
        return "connection"
    
    return "http_exception"


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException with standardized error format.
    
    Ensures that:
    - message is ALWAYS a string
    - detail objects are converted to readable strings
    - no Python dict is returned directly as message
    """
    detail = exc.detail
    message = _extract_message_from_detail(detail)
    
    # Try to extract stage from dict detail if available
    stage = "http_exception"
    hint = None
    
    if isinstance(detail, dict):
        stage = detail.get("stage", "http_exception")
        hint = detail.get("hint")
    else:
        # Infer stage from message and context
        stage = _infer_stage_from_message(message, exc.status_code, request.url.path)
    
    logger.warning(
        f"HTTPException: {exc.status_code} - {message} (stage: {stage}, path: {request.url.path})"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(message=message, stage=stage, hint=hint),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unhandled exceptions with standardized error format.
    
    Logs the full exception but only returns a safe, user-friendly message.
    Never leaks stack traces to the client.
    """
    error_type = type(exc).__name__
    error_message = str(exc)
    
    # Log full exception details for debugging
    logger.error(
        f"Unhandled exception: {error_type}: {error_message}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method}
    )
    
    # Determine user-friendly message and hint based on error type
    message = "Internal server error"
    hint = "Check server logs"
    
    if isinstance(exc, HTTPException):
        # This shouldn't happen, but handle it gracefully
        return await http_exception_handler(request, exc)
    
    # Provide helpful hints for common error types
    error_message_lower = error_message.lower()
    
    if "does not contain enough decision-critical" in error_message_lower or "not contain enough decision-critical" in error_message_lower or ("image" in error_message_lower and "decision" in error_message_lower and "information" in error_message_lower):
        message = "The image does not contain enough decision-critical information for analysis"
        hint = "Please upload an image that includes pricing, CTAs, guarantees, headlines, or product information. Alternatively, paste the text content directly."
    elif "403" in error_message or "forbidden" in error_message_lower or "blocks automated access" in error_message_lower:
        message = "This website blocks automated access (403 Forbidden)"
        hint = "Please manually copy the page content (headline, CTA, price, guarantee) and paste it in the input field instead of the URL"
    elif "OPENAI_API_KEY" in error_message or "api key" in error_message_lower:
        message = "OpenAI API key is not configured"
        hint = "Please contact support to configure the API key"
    elif "timeout" in error_message_lower or "timed out" in error_message_lower:
        message = "Request timed out"
        hint = "Please try again with a simpler request"
    elif "connection" in error_message_lower or "connect" in error_message_lower:
        message = "Connection error"
        hint = "Please check your internet connection and try again"
    elif "validation" in error_message_lower:
        message = "Validation error"
        hint = "Please check your input data"
    elif "not found" in error_message_lower or "404" in error_message:
        message = "Resource not found"
        hint = "Please check the URL or resource identifier"
    elif "permission" in error_message_lower or "forbidden" in error_message_lower:
        message = "Access forbidden"
        hint = "You don't have permission to access this resource"
    
    return JSONResponse(
        status_code=500,
        content=error_payload(
            message=message,
            stage="unhandled_exception",
            hint=hint,
        ),
    )

