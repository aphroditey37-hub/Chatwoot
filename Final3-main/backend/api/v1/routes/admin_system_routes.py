"""
API v1 Admin System Routes
System configuration endpoints for Webhooks, API Keys, Payment Methods, etc.
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import secrets
import hashlib

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from .dependencies import require_auth

router = APIRouter(prefix="/admin/system", tags=["Admin System"])


# ==================== AUTH HELPER ====================

async def require_admin_access(request: Request, authorization: str):
    """
    Require admin role for access using canonical auth module.
    
    SECURITY: All admin system endpoints MUST use this dependency.
    """
    from ..core.auth import get_current_user
    
    # Get authenticated user via canonical auth
    user = await get_current_user(request, authorization, None)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail={"message": "Admin access required", "error_code": "E1007"}
        )
    
    return user


# ==================== MODELS ====================

class WebhookCreate(BaseModel):
    """Create webhook"""
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1)
    events: List[str] = Field(default_factory=list)
    enabled: bool = True


class WebhookUpdate(BaseModel):
    """Update webhook"""
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    enabled: Optional[bool] = None


class APIKeyCreate(BaseModel):
    """Create API key"""
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=list)


class PaymentMethodCreate(BaseModel):
    """Create payment method"""
    title: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)
    instructions: str = ""
    enabled: bool = True
    priority: int = 0
    rotation_enabled: bool = False


class PaymentMethodUpdate(BaseModel):
    """Update payment method"""
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    instructions: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    rotation_enabled: Optional[bool] = None


# ==================== WEBHOOKS CRUD ====================

@router.get("/webhooks")
async def list_admin_webhooks(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all admin-configured webhooks"""
    await require_admin_access(request, authorization)
    
    webhooks = await fetch_all("""
        SELECT webhook_id, name, url, events, enabled, created_at, 
               last_delivery_at, failure_count
        FROM admin_webhooks
        ORDER BY created_at DESC
    """)
    
    return {"webhooks": [dict(w) for w in webhooks]}


@router.post("/webhooks")
async def create_admin_webhook(
    request: Request,
    data: WebhookCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a new admin webhook"""
    auth = await require_admin_access(request, authorization)
    
    webhook_id = str(uuid.uuid4())
    
    await execute("""
        INSERT INTO admin_webhooks (webhook_id, name, url, events, enabled, created_by, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
    """, webhook_id, data.name, data.url, data.events, data.enabled, auth.user_id)
    
    return {"webhook_id": webhook_id, "message": "Webhook created successfully"}


@router.put("/webhooks/{webhook_id}")
async def update_admin_webhook(
    request: Request,
    webhook_id: str,
    data: WebhookUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update an admin webhook"""
    await require_admin_access(request, authorization)
    
    # Build update query dynamically
    updates = []
    params = []
    param_idx = 1
    
    if data.name is not None:
        updates.append(f"name = ${param_idx}")
        params.append(data.name)
        param_idx += 1
    
    if data.url is not None:
        updates.append(f"url = ${param_idx}")
        params.append(data.url)
        param_idx += 1
    
    if data.events is not None:
        updates.append(f"events = ${param_idx}")
        params.append(data.events)
        param_idx += 1
    
    if data.enabled is not None:
        updates.append(f"enabled = ${param_idx}")
        params.append(data.enabled)
        param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(webhook_id)
    query = f"UPDATE admin_webhooks SET {', '.join(updates)} WHERE webhook_id = ${param_idx}"
    
    await execute(query, *params)
    
    return {"message": "Webhook updated successfully"}


@router.delete("/webhooks/{webhook_id}")
async def delete_admin_webhook(
    request: Request,
    webhook_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete an admin webhook"""
    await require_admin_access(request, authorization)
    
    await execute("DELETE FROM admin_webhooks WHERE webhook_id = $1", webhook_id)
    
    return {"message": "Webhook deleted successfully"}


@router.get("/webhooks/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    request: Request,
    webhook_id: str,
    limit: int = 50,
    authorization: str = Header(..., alias="Authorization")
):
    """Get webhook delivery history"""
    await require_admin_access(request, authorization)
    
    deliveries = await fetch_all("""
        SELECT delivery_id, event_type, status, response_code, 
               attempt_count, delivered_at, created_at
        FROM webhook_deliveries
        WHERE webhook_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, webhook_id, limit)
    
    return {"deliveries": [dict(d) for d in deliveries]}


# ==================== API KEYS CRUD ====================

@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all API keys (keys are masked)"""
    await require_admin_access(request, authorization)
    
    keys = await fetch_all("""
        SELECT key_id, name, key_prefix, scopes, is_active, created_at, last_used_at
        FROM api_keys
        WHERE is_active = TRUE
        ORDER BY created_at DESC
    """)
    
    result = []
    for key in keys:
        result.append({
            "id": key['key_id'],
            "name": key['name'],
            "key": key['key_prefix'] + "*" * 40,  # Show only prefix
            "scopes": key['scopes'],
            "created_at": key['created_at'],
            "last_used_at": key['last_used_at']
        })
    
    return {"api_keys": result}


@router.post("/api-keys")
async def create_api_key(
    request: Request,
    data: APIKeyCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a new API key - key shown only once"""
    auth = await require_admin_access(request, authorization)
    
    # Generate secure key
    key_id = str(uuid.uuid4())
    api_key = f"sk_{secrets.token_urlsafe(40)}"
    
    # Hash the key for storage
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:12]  # Store prefix for identification
    
    await execute("""
        INSERT INTO api_keys (key_id, name, key_hash, key_prefix, scopes, created_by, created_at, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, NOW(), TRUE)
    """, key_id, data.name, key_hash, key_prefix, data.scopes, auth.user_id)
    
    return {
        "key_id": key_id,
        "api_key": api_key,  # Only shown once!
        "message": "API key created. Save it now, you won't see it again."
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    request: Request,
    key_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Revoke an API key"""
    await require_admin_access(request, authorization)
    
    await execute("UPDATE api_keys SET is_active = FALSE WHERE key_id = $1", key_id)
    
    return {"message": "API key revoked successfully"}


# ==================== PAYMENT METHODS CRUD ====================

@router.get("/payment-methods")
async def list_payment_methods(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all payment methods"""
    await require_admin_access(request, authorization)
    
    methods = await fetch_all("""
        SELECT method_id, title, tags, instructions, enabled, priority, rotation_enabled, created_at
        FROM payment_methods
        ORDER BY priority DESC, created_at DESC
    """)
    
    return {"payment_methods": [dict(m) for m in methods]}


@router.post("/payment-methods")
async def create_payment_method(
    request: Request,
    data: PaymentMethodCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a new payment method"""
    auth = await require_admin_access(request, authorization)
    
    method_id = str(uuid.uuid4())
    
    await execute("""
        INSERT INTO payment_methods (method_id, title, tags, instructions, enabled, priority, rotation_enabled, created_by, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
    """, method_id, data.title, data.tags, data.instructions, data.enabled, data.priority, data.rotation_enabled, auth.user_id)
    
    return {"method_id": method_id, "message": "Payment method created successfully"}


@router.put("/payment-methods/{method_id}")
async def update_payment_method(
    request: Request,
    method_id: str,
    data: PaymentMethodUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update a payment method"""
    await require_admin_access(request, authorization)
    
    # Build update query dynamically
    updates = []
    params = []
    param_idx = 1
    
    if data.title is not None:
        updates.append(f"title = ${param_idx}")
        params.append(data.title)
        param_idx += 1
    
    if data.tags is not None:
        updates.append(f"tags = ${param_idx}")
        params.append(data.tags)
        param_idx += 1
    
    if data.instructions is not None:
        updates.append(f"instructions = ${param_idx}")
        params.append(data.instructions)
        param_idx += 1
    
    if data.enabled is not None:
        updates.append(f"enabled = ${param_idx}")
        params.append(data.enabled)
        param_idx += 1
    
    if data.priority is not None:
        updates.append(f"priority = ${param_idx}")
        params.append(data.priority)
        param_idx += 1
    
    if data.rotation_enabled is not None:
        updates.append(f"rotation_enabled = ${param_idx}")
        params.append(data.rotation_enabled)
        param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(method_id)
    query = f"UPDATE payment_methods SET {', '.join(updates)} WHERE method_id = ${param_idx}"
    
    await execute(query, *params)
    
    return {"message": "Payment method updated successfully"}


@router.delete("/payment-methods/{method_id}")
async def delete_payment_method(
    request: Request,
    method_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete a payment method"""
    await require_admin_access(request, authorization)
    
    await execute("DELETE FROM payment_methods WHERE method_id = $1", method_id)
    
    return {"message": "Payment method deleted successfully"}


# ==================== PAYMENT QR MANAGEMENT ====================

class PaymentQRCreate(BaseModel):
    """Create payment QR"""
    payment_method: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    image_url: str = Field(..., description="Base64 image or URL")
    is_active: bool = True
    is_default: bool = False


class PaymentQRUpdate(BaseModel):
    """Update payment QR"""
    payment_method: Optional[str] = None
    label: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


@router.get("/payment-qr")
async def list_payment_qr(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """
    GET /api/v1/admin/system/payment-qr
    List all payment QR codes for admin management
    """
    await require_admin_access(request, authorization)
    
    qr_codes = await fetch_all("""
        SELECT qr_id, payment_method, label, account_name, account_number, 
               image_url, is_active, is_default, created_at, updated_at
        FROM payment_qr
        ORDER BY payment_method, is_default DESC, created_at DESC
    """)
    
    return {"qr_codes": [dict(qr) for qr in qr_codes]}


@router.post("/payment-qr")
async def create_payment_qr(
    request: Request,
    data: PaymentQRCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """
    POST /api/v1/admin/system/payment-qr
    Create a new payment QR code
    Only ONE QR can be active per payment method
    """
    auth = await require_admin_access(request, authorization)
    
    qr_id = str(uuid.uuid4())
    
    # If setting as default, unset other defaults for same payment method
    if data.is_default:
        await execute("""
            UPDATE payment_qr SET is_default = FALSE 
            WHERE payment_method = $1
        """, data.payment_method)
    
    # If this is active and we want only one active per method, deactivate others
    if data.is_active:
        existing_active = await fetch_one("""
            SELECT qr_id FROM payment_qr 
            WHERE payment_method = $1 AND is_active = TRUE
        """, data.payment_method)
        
        if existing_active:
            # Deactivate the existing one
            await execute("""
                UPDATE payment_qr SET is_active = FALSE, updated_at = NOW()
                WHERE qr_id = $1
            """, existing_active['qr_id'])
    
    await execute("""
        INSERT INTO payment_qr 
        (qr_id, payment_method, label, account_name, account_number, image_url, 
         is_active, is_default, created_by, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
    """, qr_id, data.payment_method, data.label, data.account_name, 
       data.account_number, data.image_url, data.is_active, data.is_default, auth.user_id)
    
    return {"qr_id": qr_id, "message": "Payment QR created successfully"}


@router.patch("/payment-qr/{qr_id}")
async def update_payment_qr(
    request: Request,
    qr_id: str,
    data: PaymentQRUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """
    PATCH /api/v1/admin/system/payment-qr/{qr_id}
    Update a payment QR code
    """
    await require_admin_access(request, authorization)
    
    # Check if QR exists
    existing = await fetch_one("SELECT * FROM payment_qr WHERE qr_id = $1", qr_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Payment QR not found")
    
    # If setting as default, unset other defaults
    if data.is_default:
        method = data.payment_method or existing['payment_method']
        await execute("""
            UPDATE payment_qr SET is_default = FALSE 
            WHERE payment_method = $1 AND qr_id != $2
        """, method, qr_id)
    
    # If activating, deactivate others for same method (only ONE active per method)
    if data.is_active:
        method = data.payment_method or existing['payment_method']
        await execute("""
            UPDATE payment_qr SET is_active = FALSE, updated_at = NOW()
            WHERE payment_method = $1 AND qr_id != $2
        """, method, qr_id)
    
    # Build update query dynamically
    updates = []
    params = []
    param_idx = 1
    
    for field in ['payment_method', 'label', 'account_name', 'account_number', 
                  'image_url', 'is_active', 'is_default']:
        value = getattr(data, field, None)
        if value is not None:
            updates.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append(f"updated_at = NOW()")
    params.append(qr_id)
    
    query = f"UPDATE payment_qr SET {', '.join(updates)} WHERE qr_id = ${param_idx}"
    await execute(query, *params)
    
    return {"message": "Payment QR updated successfully"}


@router.delete("/payment-qr/{qr_id}")
async def delete_payment_qr(
    request: Request,
    qr_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """
    DELETE /api/v1/admin/system/payment-qr/{qr_id}
    Delete a payment QR code
    """
    await require_admin_access(request, authorization)
    
    await execute("DELETE FROM payment_qr WHERE qr_id = $1", qr_id)
    
    return {"message": "Payment QR deleted successfully"}


# ==================== WALLET LOAD ADMIN ====================

@router.get("/wallet-loads")
async def list_wallet_load_requests(
    request: Request,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(..., alias="Authorization")
):
    """
    GET /api/v1/admin/system/wallet-loads
    List all wallet load requests for admin review
    """
    await require_admin_access(request, authorization)
    
    if status_filter:
        requests = await fetch_all("""
            SELECT wlr.*, u.username, u.display_name
            FROM wallet_load_requests wlr
            LEFT JOIN users u ON wlr.user_id = u.user_id
            WHERE wlr.status = $1
            ORDER BY wlr.created_at DESC
            LIMIT $2 OFFSET $3
        """, status_filter, limit, offset)
    else:
        requests = await fetch_all("""
            SELECT wlr.*, u.username, u.display_name
            FROM wallet_load_requests wlr
            LEFT JOIN users u ON wlr.user_id = u.user_id
            ORDER BY wlr.created_at DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
    
    return {
        "requests": [
            {
                **dict(r),
                "created_at": r['created_at'].isoformat() if r['created_at'] else None,
                "reviewed_at": r['reviewed_at'].isoformat() if r['reviewed_at'] else None
            }
            for r in requests
        ]
    }


@router.get("/wallet-loads/{request_id}")
async def get_wallet_load_detail(
    request: Request,
    request_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """
    GET /api/v1/admin/system/wallet-loads/{request_id}
    Get detailed wallet load request for review
    """
    await require_admin_access(request, authorization)
    
    load_request = await fetch_one("""
        SELECT wlr.*, u.username, u.display_name, u.real_balance as current_balance
        FROM wallet_load_requests wlr
        LEFT JOIN users u ON wlr.user_id = u.user_id
        WHERE wlr.request_id = $1
    """, request_id)
    
    if not load_request:
        raise HTTPException(status_code=404, detail="Request not found")
    



@router.get("/settings", summary="Get system settings")
async def get_system_settings(request: Request, authorization: str = Header(...)):
    """Get all system settings"""
    await require_admin_access(request, authorization)
    
    # Return default settings (can be extended with database table)
    return {
        "success": True,
        "settings": {
            "platform_name": "Gaming Platform",
            "min_deposit": 10.0,
            "max_deposit": 10000.0,
            "min_withdrawal": 50.0,
            "max_withdrawal": 50000.0,
            "default_bonus_percent": 10.0,
            "referral_commission": 5.0,
            "auto_approve_deposits": False,
            "auto_approve_withdrawals": False
        }
    }


@router.get("/rules", summary="Get system rules")
async def get_system_rules(request: Request, authorization: str = Header(...)):
    """Get system rules and limits"""
    await require_admin_access(request, authorization)
    
    return {
        "success": True,
        "rules": {
            "deposit": {
                "min_amount": 10.0,
                "max_amount": 10000.0,
                "bonus_percent": 10.0,
                "auto_approve": False
            },
            "withdrawal": {
                "min_amount": 50.0,
                "max_amount": 50000.0,
                "min_cashout_multiplier": 1.0,
                "max_cashout_multiplier": 3.0,
                "auto_approve": False
            },
            "game_load": {
                "min_amount": 5.0,
                "max_amount": 1000.0
            },
            "referral": {
                "commission_percent": 5.0,
                "min_referrals_for_bonus": 10
            }
        }
    }


# NOTE: Promo code endpoints removed - use /admin/promo-codes from admin_routes_v2.py instead
# This avoids duplicate API surface and potential schema mismatches
