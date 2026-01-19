"""
Rate Limiting Middleware
Protects against abuse and DoS attacks
"""
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri=os.getenv("REDIS_URL", "memory://"),
    strategy="fixed-window"
)

# Rate limit configurations
RATE_LIMITS = {
    "auth": "5/minute",  # Login/signup
    "api": "100/minute",  # General API
    "public": "200/minute",  # Public endpoints
    "admin": "300/minute",  # Admin endpoints
}

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler"""
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.detail
        }
    )
