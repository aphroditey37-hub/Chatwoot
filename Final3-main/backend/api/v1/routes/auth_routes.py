"""
API v1 Authentication Routes
Signup, magic link login, token management
"""
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from typing import Optional
from pydantic import BaseModel, Field

from ..models import (
    SignupRequest, SignupResponse,
    MagicLinkRequest, MagicLinkResponse, MagicLinkConsumeResponse,
    TokenValidationResponse, APIError
)
from ..services import (
    create_user, authenticate_user, create_magic_link, 
    consume_magic_link, validate_token, log_audit
)
from ..core.config import ErrorCodes, get_api_settings
from ..core.security import create_jwt_token
from .dependencies import get_client_ip, check_rate_limiting, authenticate_request, AuthResult

router = APIRouter(prefix="/auth", tags=["Authentication"])

settings = get_api_settings()


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response model"""
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in_seconds: Optional[int] = None
    user: Optional[dict] = None


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": APIError, "description": "Invalid credentials"},
        429: {"model": APIError, "description": "Rate limited"}
    },
    summary="Login with username and password",
    description="""
    Login with username and password to get an access token.
    The token can be used for authenticated API calls.
    """
)
async def login(request: Request, login_data: LoginRequest):
    """Login with username and password"""
    await check_rate_limiting(request)
    
    success, result = await authenticate_user(login_data.username, login_data.password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )
    
    # Create JWT token - use 'sub' key for user_id as expected by validate_token
    token_data = {
        "sub": result['user_id'],
        "user_id": result['user_id'],
        "username": result['username'],
        "display_name": result['display_name'],
        "referral_code": result['referral_code'],
        "role": result.get('role', 'user'),
        "type": "access"
    }
    access_token = create_jwt_token(token_data)
    
    return LoginResponse(
        success=True,
        message="Login successful",
        access_token=access_token,
        token_type="Bearer",
        expires_in_seconds=settings.access_token_expire_minutes * 60,
        user={
            "user_id": result['user_id'],
            "username": result['username'],
            "display_name": result['display_name'],
            "referral_code": result['referral_code'],
            "role": result.get('role', 'user')
        }
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    responses={
        400: {"model": APIError, "description": "Validation error or user exists"},
        429: {"model": APIError, "description": "Rate limited"}
    },
    summary="Create new user account",
    description="""
    Create a new user account. This is the only endpoint that does not require authentication.
    
    - Username must be alphanumeric (underscores allowed), 3-50 characters
    - Password must be at least 8 characters
    - Optionally provide a referral code to link to a referrer
    """
)
async def signup(request: Request, signup_data: SignupRequest):
    """Create a new user account"""
    await check_rate_limiting(request)
    
    ip_address = await get_client_ip(request)
    
    success, result = await create_user(
        username=signup_data.username,
        password=signup_data.password,
        display_name=signup_data.display_name or signup_data.username.title(),
        referred_by_code=signup_data.referred_by_code
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )
    
    return SignupResponse(
        success=True,
        message="Account created successfully",
        user_id=result['user_id'],
        username=result['username'],
        display_name=result['display_name'],
        referral_code=result['referral_code'],
        referred_by_code=result.get('referred_by_code')
    )


@router.post(
    "/magic-link/request",
    response_model=MagicLinkResponse,
    responses={
        401: {"model": APIError, "description": "Invalid credentials"},
        429: {"model": APIError, "description": "Rate limited"}
    },
    summary="Request a magic link",
    description="""
    Request a magic link for passwordless login.
    
    Requires username and password for verification. The magic link will be valid for 15 minutes.
    In production, this would send the link via email/SMS.
    """
)
async def request_magic_link(request: Request, auth_data: MagicLinkRequest):
    """Request a magic link for login"""
    await check_rate_limiting(request)
    
    # Authenticate with password
    success, result = await authenticate_user(auth_data.username, auth_data.password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )
    
    # Generate magic link
    link_data = await create_magic_link(result['user_id'], result['username'])
    
    return MagicLinkResponse(
        success=True,
        message="Magic link created. In production, this would be sent via email/SMS.",
        magic_link=link_data['magic_link'],
        expires_in_seconds=link_data['expires_in_seconds']
    )


@router.get(
    "/magic-link/consume",
    response_model=MagicLinkConsumeResponse,
    responses={
        400: {"model": APIError, "description": "Invalid or expired token"},
        429: {"model": APIError, "description": "Rate limited"}
    },
    summary="Consume magic link and get access token",
    description="""
    Consume a magic link token and receive an access token.
    
    The magic link token is single-use and expires after 15 minutes.
    Returns a JWT access token valid for 7 days.
    """
)
async def consume_magic_link_endpoint(request: Request, token: str):
    """Consume magic link and get access token"""
    await check_rate_limiting(request)
    
    success, result = await consume_magic_link(token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )
    
    return MagicLinkConsumeResponse(
        success=True,
        message="Login successful",
        access_token=result['access_token'],
        token_type="Bearer",
        expires_in_seconds=result['expires_in_seconds'],
        user=result['user']
    )


@router.get(
    "/validate-token",
    response_model=TokenValidationResponse,
    summary="Validate access token"
)
async def validate_token_get(auth: AuthResult = Depends(authenticate_request)):
    """Validate current access token"""
    return TokenValidationResponse(
        valid=True,
        user_id=auth.user_id,
        username=auth.username,
        role=auth.role
    )


@router.put("/profile")
async def update_profile(
    request: Request,
    display_name: str = None,
    email: str = None,
    auth: AuthResult = Depends(authenticate_request)
):
    """Update user profile"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        updates = []
        params = [auth.user_id]
        param_count = 2
        
        if display_name:
            updates.append(f"display_name = ${param_count}")
            params.append(display_name)
            param_count += 1
        
        if email:
            updates.append(f"email = ${param_count}")
            params.append(email)
            param_count += 1
        
        if not updates:
            raise HTTPException(400, "No updates provided")
        
        updates.append("updated_at = NOW()")
        
        await conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE user_id = $1",
            *params
        )
    
    return {"success": True, "message": "Profile updated successfully"}


@router.put("/change-password")
async def change_password(
    request: Request,
    current_password: str,
    new_password: str,
    auth: AuthResult = Depends(authenticate_request)
):
    """Change user password"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get current password hash
        user = await conn.fetchrow(
            "SELECT password_hash FROM users WHERE user_id = $1",
            auth.user_id
        )
        
        if not user:
            raise HTTPException(404, "User not found")
        
        # Verify current password
        if not pwd_context.verify(current_password, user['password_hash']):
            raise HTTPException(401, "Current password is incorrect")
        
        # Hash new password
        new_hash = pwd_context.hash(new_password)
        
        # Update password
        await conn.execute(
            "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE user_id = $2",
            new_hash, auth.user_id
        )
    
    return {"success": True, "message": "Password changed successfully"}

async def validate_token_endpoint(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """Validate an access token"""
    await check_rate_limiting(request)
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Invalid authorization header format",
                "error_code": ErrorCodes.INVALID_TOKEN
            }
        )
    
    token = authorization[7:]
    is_valid, result = await validate_token(token)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )
    
    return TokenValidationResponse(
        valid=True,
        user_id=result['user_id'],
        username=result['username'],
        display_name=result.get('display_name'),
        referral_code=result.get('referral_code'),
        role=result.get('role', 'user'),
        expires_at=result['expires_at'],
        user={
            "user_id": result['user_id'],
            "username": result['username'],
            "display_name": result.get('display_name'),
            "referral_code": result.get('referral_code'),
            "role": result.get('role', 'user')
        }
    )


@router.post(
    "/validate-token",
    response_model=TokenValidationResponse,
    responses={
        401: {"model": APIError, "description": "Invalid token"}
    },
    summary="Validate access token (POST)",
    description="Validate a Bearer token and return user information"
)
async def validate_token_endpoint_post(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """Validate an access token (POST method)"""
    return await validate_token_endpoint(request, authorization)
