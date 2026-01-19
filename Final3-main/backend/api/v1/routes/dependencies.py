"""
API v1 Authentication Dependencies
CONSOLIDATED: All auth flows through canonical auth module

This file provides backwards-compatible wrappers that delegate to
the canonical auth module at api/v1/core/auth.py

For new code, import directly from ..core.auth:
    from ..core.auth import get_current_user, require_admin, AuthenticatedUser
"""
from fastapi import Depends, Header, HTTPException, status, Request
from typing import Optional, Dict, Any, Tuple

from ..core.security import check_rate_limit, decode_jwt_token
from ..core.config import ErrorCodes
from ..services import authenticate_user, validate_token, get_user_by_username

# Import canonical auth
from ..core.auth import (
    AuthenticatedUser,
    AuthResult as CanonicalAuthResult,
    get_current_user,
    require_admin as canonical_require_admin,
    require_client_or_admin,
    enforce_ownership,
    authenticate_request_legacy,
    raise_auth_error,
    AuthErrorCode,
)


# ==================== LEGACY AUTH RESULT ====================
# Kept for backwards compatibility with existing routes

class AuthResult:
    """
    Legacy authentication result container.
    DEPRECATED: New code should use AuthenticatedUser from core.auth
    """
    def __init__(self, user_id: str, username: str, display_name: str, referral_code: str, role: str = "user"):
        self.user_id = user_id
        self.username = username
        self.display_name = display_name
        self.referral_code = referral_code
        self.role = role
    
    @classmethod
    def from_authenticated_user(cls, user: AuthenticatedUser) -> "AuthResult":
        """Create legacy AuthResult from AuthenticatedUser"""
        return cls(
            user_id=user.user_id,
            username=user.username,
            display_name=user.display_name,
            referral_code=user.referral_code,
            role=user.role
        )


# ==================== UTILITY FUNCTIONS ====================

async def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limiting(request: Request) -> bool:
    """Rate limit check dependency"""
    client_ip = await get_client_ip(request)
    is_allowed, remaining = check_rate_limit(client_ip)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Rate limit exceeded. Please try again later.",
                "error_code": ErrorCodes.RATE_LIMITED
            }
        )
    
    return True


# ==================== LEGACY AUTH FUNCTIONS ====================

async def authenticate_request(
    request: Request,
    username: Optional[str] = None,
    password: Optional[str] = None,
    authorization: Optional[str] = Header(None)
) -> AuthResult:
    """
    LEGACY: Authenticate a request using either:
    1. Bearer token (if Authorization header present)
    2. Username + Password (from request body)
    
    Token takes precedence if both are provided.
    
    DEPRECATED: For new code, use get_current_user() from core.auth
    """
    # Check rate limiting
    await check_rate_limiting(request)
    
    # Try token auth first
    if authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            is_valid, result = await validate_token(token)
            
            if is_valid:
                return AuthResult(
                    user_id=result['user_id'],
                    username=result['username'],
                    display_name=result['display_name'],
                    referral_code=result['referral_code'],
                    role=result.get('role', 'user')
                )
        
        # Invalid token format or token validation failed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Invalid or expired token",
                "error_code": ErrorCodes.INVALID_TOKEN
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Fall back to username/password auth
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Authentication required. Provide username/password or Bearer token.",
                "error_code": ErrorCodes.INVALID_CREDENTIALS
            }
        )
    
    is_valid, result = await authenticate_user(username, password)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )
    
    return AuthResult(
        user_id=result['user_id'],
        username=result['username'],
        display_name=result['display_name'],
        referral_code=result['referral_code'],
        role=result.get('role', 'user')
    )


def create_auth_dependency():
    """
    LEGACY: Factory to create auth dependency that extracts credentials from body.
    
    DEPRECATED: For new code, use get_current_user() from core.auth
    """
    async def auth_dependency(
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ) -> AuthResult:
        # For JSON body, we need to parse it
        body = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
            except Exception:
                pass
        
        username = body.get('username')
        password = body.get('password')
        
        return await authenticate_request(request, username, password, authorization)
    
    return auth_dependency


# Convenience dependency (legacy)
require_auth = create_auth_dependency()


# ==================== NEW CANONICAL EXPORTS ====================
# These are the preferred auth dependencies for new code

__all__ = [
    # Legacy (backwards compatible)
    "AuthResult",
    "get_client_ip",
    "check_rate_limiting",
    "authenticate_request",
    "create_auth_dependency",
    "require_auth",
    
    # Canonical (preferred for new code)
    "AuthenticatedUser",
    "get_current_user",
    "canonical_require_admin",
    "require_client_or_admin",
    "enforce_ownership",
    "raise_auth_error",
    "AuthErrorCode",
]
