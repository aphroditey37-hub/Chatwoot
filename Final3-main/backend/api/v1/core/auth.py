"""
API v1 Canonical Authentication & Authorization Module
SINGLE SOURCE OF TRUTH for all auth across the platform

This module provides:
1. get_current_user() - Unified user authentication
2. require_admin() - Admin-only access
3. require_client_or_admin() - Shared endpoints with ownership control
4. AuthError handling - Consistent error responses

ALL routes MUST import from this module. No ad-hoc token parsing allowed.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from fastapi import Depends, Header, HTTPException, status, Request

from ..core.security import decode_jwt_token
from ..core.config import get_api_settings, ErrorCodes
from ..core.database import fetch_one

logger = logging.getLogger(__name__)
settings = get_api_settings()


# ==================== ERROR CODES ====================
# Auth error codes follow E1xxx convention

class AuthErrorCode(str, Enum):
    """Authentication/Authorization error codes"""
    MISSING_TOKEN = "E1001"
    INVALID_TOKEN = "E1002"
    TOKEN_EXPIRED = "E1003"
    USER_NOT_FOUND = "E1004"
    USER_DISABLED = "E1005"
    INSUFFICIENT_PERMISSIONS = "E1006"
    ADMIN_REQUIRED = "E1007"
    OWNERSHIP_REQUIRED = "E1008"
    INVALID_CREDENTIALS = "E1009"
    ACCOUNT_LOCKED = "E1010"
    RATE_LIMITED = "E1011"


# ==================== AUTH RESULT ====================

@dataclass
class AuthenticatedUser:
    """
    Authenticated user context.
    Contains all necessary user info for authorization checks.
    """
    user_id: str
    username: str
    display_name: str
    referral_code: str
    role: str
    is_active: bool = True
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role in ('admin', 'superadmin')
    
    @property
    def is_client(self) -> bool:
        """Check if user is regular client"""
        return self.role == 'user'


# ==================== AUTH EXCEPTIONS ====================

def raise_auth_error(
    code: AuthErrorCode,
    message: str,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
    headers: Optional[Dict[str, str]] = None
):
    """
    Raise consistent auth error with proper format.
    Integrates with centralized exception handler.
    """
    if headers is None and status_code == status.HTTP_401_UNAUTHORIZED:
        headers = {"WWW-Authenticate": "Bearer"}
    
    raise HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "error_code": code.value
        },
        headers=headers
    )


# ==================== TOKEN EXTRACTION ====================

async def extract_token(
    authorization: Optional[str] = None,
    x_portal_token: Optional[str] = None,
) -> Optional[str]:
    """
    Extract token from various sources in priority order:
    1. Authorization header (Bearer token)
    2. X-Portal-Token header (legacy portal sessions)
    
    Returns None if no token found (let downstream handle).
    """
    # Priority 1: Authorization Bearer header
    if authorization:
        if authorization.startswith("Bearer "):
            return authorization[7:].strip()
        # Allow raw token in Authorization header
        return authorization.strip()
    
    # Priority 2: X-Portal-Token header
    if x_portal_token:
        return x_portal_token.strip()
    
    return None


# ==================== USER RESOLUTION ====================

async def resolve_user_from_jwt(token: str) -> Optional[AuthenticatedUser]:
    """
    Resolve user from JWT token.
    Validates signature, expiration, and user existence.
    """
    # Decode and validate JWT
    payload = decode_jwt_token(token)
    
    if not payload:
        return None
    
    # Extract user ID
    user_id = payload.get('sub') or payload.get('user_id')
    if not user_id:
        return None
    
    # Verify user exists and is active
    user = await fetch_one(
        """SELECT user_id, username, display_name, referral_code, role, is_active 
           FROM users WHERE user_id = $1""",
        user_id
    )
    
    if not user:
        return None
    
    return AuthenticatedUser(
        user_id=user['user_id'],
        username=user['username'],
        display_name=user.get('display_name', user['username']),
        referral_code=user.get('referral_code', ''),
        role=user.get('role', 'user'),
        is_active=user.get('is_active', True)
    )


async def resolve_user_from_portal_token(token: str) -> Optional[AuthenticatedUser]:
    """
    Resolve user from portal session token (legacy support).
    """
    session = await fetch_one(
        """SELECT user_id FROM portal_sessions 
           WHERE session_token = $1 AND expires_at > NOW()""",
        token
    )
    
    if not session:
        return None
    
    user = await fetch_one(
        """SELECT user_id, username, display_name, referral_code, role, is_active 
           FROM users WHERE user_id = $1""",
        session['user_id']
    )
    
    if not user:
        return None
    
    return AuthenticatedUser(
        user_id=user['user_id'],
        username=user['username'],
        display_name=user.get('display_name', user['username']),
        referral_code=user.get('referral_code', ''),
        role=user.get('role', 'user'),
        is_active=user.get('is_active', True)
    )


# ==================== CORE AUTH DEPENDENCIES ====================

async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
) -> AuthenticatedUser:
    """
    CANONICAL authentication dependency.
    Returns authenticated user or raises 401.
    
    This is the SINGLE SOURCE OF TRUTH for authentication.
    All routes MUST use this dependency.
    
    Token resolution order:
    1. Authorization: Bearer <jwt>
    2. X-Portal-Token (legacy)
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    # Extract token from headers
    token = await extract_token(authorization, x_portal_token)
    
    if not token:
        raise_auth_error(
            AuthErrorCode.MISSING_TOKEN,
            "Authentication required. Provide Bearer token.",
            status.HTTP_401_UNAUTHORIZED
        )
    
    # Try JWT first (primary method)
    user = await resolve_user_from_jwt(token)
    
    # Fallback to portal session token
    if not user:
        user = await resolve_user_from_portal_token(token)
    
    if not user:
        raise_auth_error(
            AuthErrorCode.INVALID_TOKEN,
            "Invalid or expired token",
            status.HTTP_401_UNAUTHORIZED
        )
    
    # Check if user is active
    if not user.is_active:
        raise_auth_error(
            AuthErrorCode.USER_DISABLED,
            "Account is disabled",
            status.HTTP_403_FORBIDDEN
        )
    
    # Store user in request state for downstream use
    request.state.current_user = user
    
    logger.debug(f"Authenticated user: {user.username} (role={user.role})")
    
    return user


async def get_current_user_optional(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication - returns None if no valid token.
    Use for endpoints that work both authenticated and unauthenticated.
    """
    token = await extract_token(authorization, x_portal_token)
    
    if not token:
        return None
    
    user = await resolve_user_from_jwt(token)
    if not user:
        user = await resolve_user_from_portal_token(token)
    
    if user and user.is_active:
        request.state.current_user = user
        return user
    
    return None


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require admin role for access.
    
    Usage:
        @router.get("/admin-endpoint")
        async def admin_endpoint(admin: AuthenticatedUser = Depends(require_admin)):
            ...
    """
    if not user.is_admin:
        raise_auth_error(
            AuthErrorCode.ADMIN_REQUIRED,
            "Admin access required",
            status.HTTP_403_FORBIDDEN
        )
    
    return user


async def require_client_or_admin(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Allow both clients and admins.
    Used for shared endpoints where clients see their own data,
    and admins can see all.
    
    Caller must implement ownership filtering.
    """
    # Both roles allowed
    return user


# ==================== OWNERSHIP ENFORCEMENT ====================

async def enforce_ownership(
    user: AuthenticatedUser,
    resource_user_id: str,
    resource_name: str = "resource"
) -> bool:
    """
    Enforce that a user can only access their own resources.
    Admins can access any resource.
    
    Returns True if access allowed.
    Raises 403 if denied.
    
    Usage:
        await enforce_ownership(user, order['user_id'], "order")
    """
    if user.is_admin:
        return True
    
    if user.user_id != resource_user_id:
        raise_auth_error(
            AuthErrorCode.OWNERSHIP_REQUIRED,
            f"You do not have access to this {resource_name}",
            status.HTTP_403_FORBIDDEN
        )
    
    return True


async def enforce_ownership_or_404(
    user: AuthenticatedUser,
    resource_user_id: Optional[str],
    resource_name: str = "resource"
) -> bool:
    """
    Like enforce_ownership, but returns 404 instead of 403.
    Use when you want to hide the existence of resources.
    """
    if user.is_admin:
        return True
    
    if not resource_user_id or user.user_id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"{resource_name.capitalize()} not found", "error_code": "E4001"}
        )
    
    return True


# ==================== LEGACY COMPATIBILITY ====================

class AuthResult:
    """
    Legacy auth result for backwards compatibility.
    New code should use AuthenticatedUser directly.
    """
    def __init__(self, user: AuthenticatedUser):
        self.user_id = user.user_id
        self.username = user.username
        self.display_name = user.display_name
        self.referral_code = user.referral_code
        self.role = user.role


async def authenticate_request_legacy(
    request: Request,
    username: Optional[str] = None,
    password: Optional[str] = None,
    authorization: Optional[str] = Header(None)
) -> AuthResult:
    """
    Legacy authentication wrapper.
    Supports both token auth and username/password.
    
    DEPRECATED: Use get_current_user() for new code.
    """
    from ..services import authenticate_user
    
    # Try token auth first
    if authorization:
        try:
            user = await get_current_user(request, authorization, None)
            return AuthResult(user)
        except HTTPException:
            pass
    
    # Fall back to username/password
    if username and password:
        is_valid, result = await authenticate_user(username, password)
        
        if is_valid:
            return AuthResult(AuthenticatedUser(
                user_id=result['user_id'],
                username=result['username'],
                display_name=result['display_name'],
                referral_code=result['referral_code'],
                role=result.get('role', 'user'),
                is_active=True
            ))
        else:
            raise_auth_error(
                AuthErrorCode.INVALID_CREDENTIALS,
                result.get('message', 'Invalid credentials'),
                status.HTTP_401_UNAUTHORIZED
            )
    
    raise_auth_error(
        AuthErrorCode.MISSING_TOKEN,
        "Authentication required. Provide username/password or Bearer token.",
        status.HTTP_401_UNAUTHORIZED
    )


# ==================== EXPORTS ====================

__all__ = [
    # Core types
    "AuthenticatedUser",
    "AuthErrorCode",
    
    # Primary dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "require_client_or_admin",
    
    # Ownership enforcement
    "enforce_ownership",
    "enforce_ownership_or_404",
    
    # Legacy support
    "AuthResult",
    "authenticate_request_legacy",
    
    # Utilities
    "raise_auth_error",
]
