"""
API v1 Identity Routes
FB/Chatwoot identity resolution and management
"""
from fastapi import APIRouter, Request, HTTPException, status, Header
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from .dependencies import check_rate_limiting, require_auth, AuthResult

router = APIRouter(prefix="/identity", tags=["Identity"])


# ==================== MODELS ====================

class IdentityResolveRequest(BaseModel):
    """Resolve external identity to internal user"""
    provider: str = Field(..., description="Identity provider (facebook, chatwoot)")
    external_id: str = Field(..., description="External ID from provider")
    display_name: Optional[str] = Field(None, description="Display name to use if creating user")


class IdentityLinkRequest(BaseModel):
    """Link identity to user (admin)"""
    user_id: str
    provider: str
    external_id: str
    is_primary: bool = False


class IdentitySwitchPrimaryRequest(BaseModel):
    """Switch primary identity (admin)"""
    user_id: str
    identity_id: str


class IdentityTransferRequest(BaseModel):
    """Transfer identity to another user (admin)"""
    identity_id: str
    from_user_id: str
    to_user_id: str
    reason: str


# ==================== PUBLIC ENDPOINTS ====================

@router.post(
    "/resolve",
    summary="Resolve external identity",
    description="""
    Resolve a FB/Chatwoot external ID to an internal user.
    Creates a new user if the identity doesn't exist.
    
    Used by Chatwoot bot to identify users.
    """
)
async def resolve_identity(request: Request, data: IdentityResolveRequest):
    """Resolve external identity to internal user"""
    await check_rate_limiting(request)
    
    provider = data.provider.lower()
    external_id = data.external_id.strip()
    
    # Check if identity exists
    identity = await fetch_one('''
        SELECT i.*, u.username, u.display_name, u.referral_code, u.is_active
        FROM user_identities i
        JOIN users u ON i.user_id = u.user_id
        WHERE i.provider = $1 AND i.external_id = $2
    ''', provider, external_id)
    
    if identity:
        if not identity['is_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Account is disabled", "error_code": "E1006"}
            )
        
        return {
            "success": True,
            "found": True,
            "user_id": identity['user_id'],
            "username": identity['username'],
            "display_name": identity['display_name'],
            "referral_code": identity['referral_code'],
            "is_primary": identity['is_primary']
        }
    
    # Identity not found - create new user
    from ..core.security import generate_referral_code, hash_password
    import secrets
    
    user_id = str(uuid.uuid4())
    username = f"{provider}_{external_id[:8]}_{secrets.token_hex(4)}"
    display_name = data.display_name or f"User {external_id[:8]}"
    referral_code = generate_referral_code()
    temp_password = secrets.token_hex(16)
    
    # Ensure unique referral code
    while await fetch_one("SELECT user_id FROM users WHERE referral_code = $1", referral_code):
        referral_code = generate_referral_code()
    
    # Create user
    await execute('''
        INSERT INTO users (user_id, username, password_hash, display_name, referral_code)
        VALUES ($1, $2, $3, $4, $5)
    ''', user_id, username, hash_password(temp_password), display_name, referral_code)
    
    # Create identity link
    identity_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO user_identities (identity_id, user_id, provider, external_id, is_primary)
        VALUES ($1, $2, $3, $4, TRUE)
    ''', identity_id, user_id, provider, external_id)
    
    # Log audit
    await log_audit(user_id, username, "identity.created", "identity", identity_id, {
        "provider": provider,
        "external_id": external_id
    })
    
    return {
        "success": True,
        "found": False,
        "created": True,
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "referral_code": referral_code,
        "is_primary": True
    }


@router.get(
    "/lookup/{provider}/{external_id}",
    summary="Lookup identity without creating",
    description="Check if an external identity exists without creating a new user"
)
async def lookup_identity(request: Request, provider: str, external_id: str):
    """Lookup identity without creating"""
    await check_rate_limiting(request)
    
    identity = await fetch_one('''
        SELECT i.*, u.username, u.display_name, u.referral_code, u.is_active
        FROM user_identities i
        JOIN users u ON i.user_id = u.user_id
        WHERE i.provider = $1 AND i.external_id = $2
    ''', provider.lower(), external_id.strip())
    
    if not identity:
        return {"success": True, "found": False}
    
    return {
        "success": True,
        "found": True,
        "user_id": identity['user_id'],
        "username": identity['username'],
        "display_name": identity['display_name'],
        "is_active": identity['is_active'],
        "is_primary": identity['is_primary']
    }


# ==================== ADMIN ENDPOINTS ====================

@router.post(
    "/admin/link",
    summary="Link identity to user",
    description="Admin: Link an external identity to an existing user"
)
async def admin_link_identity(
    request: Request,
    data: IdentityLinkRequest,
    authorization: str = Header(..., alias="Authorization")
):
    """Admin: Link identity to user"""
    auth = await require_auth(request, authorization=authorization)
    
    # Check admin role
    admin = await fetch_one("SELECT role FROM users WHERE user_id = $1", auth.user_id)
    if not admin or admin['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if identity already exists
    existing = await fetch_one(
        "SELECT identity_id, user_id FROM user_identities WHERE provider = $1 AND external_id = $2",
        data.provider.lower(), data.external_id
    )
    
    if existing:
        if existing['user_id'] == data.user_id:
            return {"success": True, "message": "Identity already linked to this user"}
        raise HTTPException(
            status_code=400,
            detail={"message": "Identity already linked to another user", "existing_user_id": existing['user_id']}
        )
    
    # Check user exists
    user = await fetch_one("SELECT username FROM users WHERE user_id = $1", data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If setting as primary, unset other primaries
    if data.is_primary:
        await execute(
            "UPDATE user_identities SET is_primary = FALSE WHERE user_id = $1",
            data.user_id
        )
    
    # Create identity
    identity_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO user_identities (identity_id, user_id, provider, external_id, is_primary)
        VALUES ($1, $2, $3, $4, $5)
    ''', identity_id, data.user_id, data.provider.lower(), data.external_id, data.is_primary)
    
    await log_audit(auth.user_id, auth.username, "admin.identity_linked", "identity", identity_id, {
        "target_user_id": data.user_id,
        "provider": data.provider,
        "external_id": data.external_id
    })
    
    return {
        "success": True,
        "message": "Identity linked successfully",
        "identity_id": identity_id
    }


@router.post(
    "/admin/switch-primary",
    summary="Switch primary identity",
    description="Admin: Change which identity is primary for a user"
)
async def admin_switch_primary(
    request: Request,
    data: IdentitySwitchPrimaryRequest,
    authorization: str = Header(..., alias="Authorization")
):
    """Admin: Switch primary identity"""
    auth = await require_auth(request, authorization=authorization)
    
    admin = await fetch_one("SELECT role FROM users WHERE user_id = $1", auth.user_id)
    if not admin or admin['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify identity belongs to user
    identity = await fetch_one(
        "SELECT * FROM user_identities WHERE identity_id = $1 AND user_id = $2",
        data.identity_id, data.user_id
    )
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found for this user")
    
    # Unset all primaries
    await execute("UPDATE user_identities SET is_primary = FALSE WHERE user_id = $1", data.user_id)
    
    # Set new primary
    await execute("UPDATE user_identities SET is_primary = TRUE WHERE identity_id = $1", data.identity_id)
    
    await log_audit(auth.user_id, auth.username, "admin.identity_primary_changed", "identity", data.identity_id, {
        "target_user_id": data.user_id
    })
    
    return {"success": True, "message": "Primary identity switched"}


@router.post(
    "/admin/transfer",
    summary="Transfer identity to another user",
    description="Admin: Move an identity from one user to another"
)
async def admin_transfer_identity(
    request: Request,
    data: IdentityTransferRequest,
    authorization: str = Header(..., alias="Authorization")
):
    """Admin: Transfer identity"""
    auth = await require_auth(request, authorization=authorization)
    
    admin = await fetch_one("SELECT role FROM users WHERE user_id = $1", auth.user_id)
    if not admin or admin['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify identity belongs to source user
    identity = await fetch_one(
        "SELECT * FROM user_identities WHERE identity_id = $1 AND user_id = $2",
        data.identity_id, data.from_user_id
    )
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found for source user")
    
    # Verify target user exists
    target_user = await fetch_one("SELECT username FROM users WHERE user_id = $1", data.to_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Transfer
    await execute('''
        UPDATE user_identities 
        SET user_id = $1, is_primary = FALSE, updated_at = NOW()
        WHERE identity_id = $2
    ''', data.to_user_id, data.identity_id)
    
    await log_audit(auth.user_id, auth.username, "admin.identity_transferred", "identity", data.identity_id, {
        "from_user_id": data.from_user_id,
        "to_user_id": data.to_user_id,
        "reason": data.reason
    })
    
    return {"success": True, "message": "Identity transferred successfully"}


@router.get(
    "/admin/user/{user_id}",
    summary="Get user identities",
    description="Admin: Get all identities for a user"
)
async def admin_get_user_identities(
    request: Request,
    user_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Admin: Get user identities"""
    auth = await require_auth(request, authorization=authorization)
    
    admin = await fetch_one("SELECT role FROM users WHERE user_id = $1", auth.user_id)
    if not admin or admin['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    identities = await fetch_all(
        "SELECT * FROM user_identities WHERE user_id = $1 ORDER BY is_primary DESC, created_at ASC",
        user_id
    )
    
    return {
        "success": True,
        "user_id": user_id,
        "identities": [
            {
                "identity_id": i['identity_id'],
                "provider": i['provider'],
                "external_id": i['external_id'],
                "is_primary": i['is_primary'],
                "status": i['status'],
                "created_at": i['created_at'].isoformat() if i.get('created_at') else None
            }
            for i in identities
        ]
    }


async def log_audit(user_id, username, action, resource_type, resource_id, details=None, ip=None):
    """Log an audit event"""
    import json
    log_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details, ip_address)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    ''', log_id, user_id, username, action, resource_type, resource_id,
       json.dumps(details) if details else None, ip)
