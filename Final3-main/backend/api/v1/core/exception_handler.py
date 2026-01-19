"""
Centralized Exception Handler
Provides safe error responses without exposing stack traces.
"""
import logging
import traceback
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import httpx

logger = logging.getLogger(__name__)


# ==================== SAFE ERROR CODES ====================

ERROR_CODES = {
    # Authentication errors (1xxx)
    "E1001": "Invalid credentials",
    "E1002": "User not found",
    "E1003": "Session expired",
    "E1004": "Unauthorized access",
    "E1005": "Account locked",
    
    # Validation errors (2xxx)
    "E2001": "Invalid request format",
    "E2002": "Missing required field",
    "E2003": "Value out of range",
    "E2004": "Invalid data type",
    
    # Business rule errors (3xxx)
    "E3001": "Insufficient balance",
    "E3002": "Game not found",
    "E3003": "Amount below minimum",
    "E3004": "Amount above maximum",
    "E3010": "Deposits locked for this account",
    "E3011": "Game balance exceeds deposit limit",
    "E3015": "Minimum wagering not met",
    "E3016": "Maximum payout exceeded",
    
    # External service errors (4xxx)
    "E4001": "Games API unavailable",
    "E4002": "Games API timeout",
    "E4003": "Payment gateway error",
    "E4004": "External service error",
    
    # System errors (5xxx)
    "E5001": "Database connection error",
    "E5002": "Internal server error",
    "E5003": "Service temporarily unavailable",
    "E5004": "Configuration error",
}


class SafeAPIException(Exception):
    """
    Safe exception that can be returned to clients.
    Does not expose internal details.
    """
    
    def __init__(
        self,
        error_code: str,
        message: Optional[str] = None,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "An error occurred")
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_response(self) -> Dict[str, Any]:
        """Convert to safe response dict."""
        response = {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            response["details"] = self.details
        return response


class GamesAPIError(SafeAPIException):
    """Games API specific error."""
    
    def __init__(
        self,
        message: str = "Games API unavailable",
        original_error: Optional[Exception] = None,
        is_timeout: bool = False
    ):
        error_code = "E4002" if is_timeout else "E4001"
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=503,
            details={"retry": True, "retry_after": 30}
        )
        self.original_error = original_error


class ConfigurationError(SafeAPIException):
    """Configuration/startup error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            error_code="E5004",
            message=message,
            status_code=500,
            details={"config_key": config_key} if config_key else {}
        )


# ==================== EXCEPTION HANDLER ====================

async def centralized_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Centralized exception handler for FastAPI.
    Returns safe errors without stack traces in production.
    """
    # Get correlation ID for logging
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    # Handle our safe exceptions
    if isinstance(exc, SafeAPIException):
        logger.warning(
            f"SafeAPIException: {exc.error_code} - {exc.message}",
            extra={"correlation_id": correlation_id}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response()
        )
    
    # Handle FastAPI HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "details": exc.detail if isinstance(exc.detail, dict) else None
            }
        )
    
    # Handle Pydantic validation errors
    if isinstance(exc, ValidationError):
        logger.warning(
            f"ValidationError: {str(exc)}",
            extra={"correlation_id": correlation_id}
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "error_code": "E2001",
                "message": "Invalid request format",
                "details": {"validation_errors": exc.errors()}
            }
        )
    
    # Handle httpx errors (external API calls)
    if isinstance(exc, httpx.TimeoutException):
        logger.error(
            f"External API timeout: {str(exc)}",
            extra={"correlation_id": correlation_id}
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": True,
                "error_code": "E4002",
                "message": "External service timeout. Please try again.",
                "details": {"retry": True}
            }
        )
    
    if isinstance(exc, httpx.HTTPStatusError):
        logger.error(
            f"External API error: {exc.response.status_code}",
            extra={"correlation_id": correlation_id}
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": True,
                "error_code": "E4004",
                "message": "External service error. Please try again later.",
                "details": {"retry": True}
            }
        )
    
    # Handle all other exceptions - LOG FULL TRACE, RETURN SAFE MESSAGE
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={"correlation_id": correlation_id, "traceback": traceback.format_exc()}
    )
    
    # In production, don't expose internal error details
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "error_code": "E5002",
            "message": "An internal error occurred. Please try again later.",
            "correlation_id": correlation_id
        }
    )


def register_exception_handlers(app):
    """Register exception handlers with FastAPI app."""
    app.add_exception_handler(SafeAPIException, centralized_exception_handler)
    app.add_exception_handler(ValidationError, centralized_exception_handler)
    app.add_exception_handler(httpx.TimeoutException, centralized_exception_handler)
    app.add_exception_handler(httpx.HTTPStatusError, centralized_exception_handler)
    app.add_exception_handler(Exception, centralized_exception_handler)
