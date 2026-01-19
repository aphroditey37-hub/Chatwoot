"""
API v1 Admin Routes - RESTRUCTURED
Following the authoritative admin structure:
1. Dashboard (read-only overview)
2. Approvals
3. Orders (with order detail)
4. Clients (with client detail + overrides)
5. Games (config + analytics)
6. Rules (global defaults ONLY)
7. Referrals
8. Promo Codes
9. Reports
10. System
11. Audit Logs
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import uuid
import json
import secrets
import string

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from .dependencies import authenticate_request, require_auth

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== AUTH HELPER ====================

async def require_admin_access(request: Request, authorization: str):
    """
    Require admin role for access using canonical auth module.
    
    SECURITY: All admin endpoints MUST use this dependency.
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

class GlobalRulesUpdate(BaseModel):
    """Update global rules - ONLY global defaults"""
    signup_bonus: Optional[float] = Field(None, ge=0, le=100)
    default_deposit_bonus: Optional[float] = Field(None, ge=0, le=100)
    default_referral_bonus: Optional[float] = Field(None, ge=0, le=100)
    deposit_block_balance: Optional[float] = Field(None, ge=0)
    min_cashout_multiplier: Optional[float] = Field(None, ge=0.1)
    max_cashout_multiplier: Optional[float] = Field(None, ge=0.1)
    auto_approve_deposits: Optional[bool] = None
    auto_approve_withdrawals: Optional[bool] = None


class ClientOverridesUpdate(BaseModel):
    """Client-specific overrides - lives with client"""
    bonus_percentage: Optional[float] = Field(None, ge=0, le=100)
    deposit_locked: Optional[bool] = None
    withdraw_locked: Optional[bool] = None
    is_suspicious: Optional[bool] = None
    manual_approval_only: Optional[bool] = None
    no_bonus: Optional[bool] = None


class GameConfigUpdate(BaseModel):
    """Game-specific config - lives with game"""
    min_deposit_amount: Optional[float] = Field(None, ge=0)
    max_deposit_amount: Optional[float] = Field(None, ge=0)
    min_withdrawal_amount: Optional[float] = Field(None, ge=0)
    max_withdrawal_amount: Optional[float] = Field(None, ge=0)
    bonus_rules: Optional[dict] = None
    withdrawal_rules: Optional[dict] = None
    is_active: Optional[bool] = None


class PromoCodeCreate(BaseModel):
    """Create promo code for play credits"""
    code: str = Field(..., min_length=4, max_length=50)
    credit_amount: float = Field(..., gt=0)
    max_redemptions: Optional[int] = Field(None, ge=1)
    expires_at: Optional[datetime] = None


class SystemConfigUpdate(BaseModel):
    """System operations config"""
    master_kill_switch: Optional[bool] = None
    kill_switch_reason: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    api_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None


class ApprovalAction(BaseModel):
    """Approval action"""
    action: str = Field(..., pattern="^(approve|reject)$")
    reason: Optional[str] = None
    modified_amount: Optional[float] = None


# ==================== 1. DASHBOARD (READ-ONLY OVERVIEW) ====================

@router.get("/dashboard", summary="Dashboard overview - read-only")
async def get_dashboard(request: Request, authorization: str = Header(...)):
    """Quick health check overview ONLY"""
    auth = await require_admin_access(request, authorization)
    
    # Get today's date range
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Pending approvals
    pending = await fetch_one("""
        SELECT 
            COUNT(*) FILTER (WHERE status IN ('pending_review', 'awaiting_payment_proof')) as pending_total,
            COUNT(*) FILTER (WHERE status IN ('pending_review', 'awaiting_payment_proof') AND order_type = 'deposit') as pending_deposits,
            COUNT(*) FILTER (WHERE status IN ('pending_review', 'awaiting_payment_proof') AND order_type = 'withdrawal') as pending_withdrawals
        FROM orders
    """)
    
    # Today's flow - handle both legacy 'approved' and canonical 'APPROVED_EXECUTED' statuses
    today_flow = await fetch_one("""
        SELECT 
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status IN ('approved', 'APPROVED_EXECUTED') AND approved_at >= $1), 0) as deposits_in,
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status IN ('approved', 'APPROVED_EXECUTED') AND approved_at >= $1), 0) as withdrawals_out,
            COALESCE(SUM(void_amount) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED') AND approved_at >= $1), 0) as voided_today
        FROM orders
    """, today_start)
    
    # Total profit calculation - handle both legacy and canonical statuses
    profit = await fetch_one("""
        SELECT 
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) -
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) as net_profit
        FROM orders
    """)
    
    # Active clients
    active_clients = await fetch_one("""
        SELECT COUNT(*) as count FROM users WHERE is_active = TRUE AND role = 'user'
    """)
    
    # System status
    system = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    
    return {
        "pending_approvals": {
            "total": pending['pending_total'],
            "deposits": pending['pending_deposits'],
            "withdrawals": pending['pending_withdrawals']
        },
        "today": {
            "deposits_in": round(today_flow['deposits_in'], 2),
            "withdrawals_out": round(today_flow['withdrawals_out'], 2),
            "voided": round(today_flow['voided_today'], 2)
        },
        "net_profit": round(profit['net_profit'], 2),
        "active_clients": active_clients['count'],
        "system_status": {
            "api_enabled": system.get('api_enabled', True) if system else True,
            "telegram_enabled": system.get('telegram_enabled', False) if system else False,
            "kill_switch": system.get('master_kill_switch', False) if system else False
        }
    }


# ==================== 2. APPROVALS ====================

@router.get("/approvals/pending", summary="Get pending approvals")
async def get_pending_approvals(
    request: Request,
    order_type: Optional[str] = None,
    authorization: str = Header(...)
):
    """Get all pending approvals"""
    auth = await require_admin_access(request, authorization)
    
    query = """
        SELECT o.*, 
               COALESCE(u.is_suspicious, FALSE) as is_suspicious, 
               COALESCE(co.manual_approval_required, FALSE) as manual_approval_only
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.user_id
        LEFT JOIN client_overrides co ON o.user_id = co.user_id
        WHERE o.status IN ('pending_review', 'awaiting_payment_proof')
    """
    params = []
    
    if order_type:
        params.append(order_type)
        query += f" AND o.order_type = ${len(params)}"
    
    query += " ORDER BY o.created_at ASC"
    
    orders = await fetch_all(query, *params) if params else await fetch_all(query)
    
    return {
        "pending": [{
            "order_id": o['order_id'],
            "username": o['username'],
            "order_type": o['order_type'],
            "game_name": o['game_name'],
            "amount": o['amount'],
            "bonus_amount": o['bonus_amount'],
            "total_amount": o['total_amount'],
            "status": o['status'],
            "payment_proof_url": o.get('payment_proof_url'),
            "is_suspicious": o.get('is_suspicious', False),
            "manual_approval_only": o.get('manual_approval_only', False),
            "created_at": o['created_at'].isoformat() if o.get('created_at') else None
        } for o in orders],
        "total": len(orders)
    }


@router.post("/approvals/{order_id}/action", summary="Approve or reject order")
async def process_approval(
    request: Request,
    order_id: str,
    data: ApprovalAction,
    authorization: str = Header(...)
):
    """Process approval using centralized approval service"""
    from ..core.approval_service import approve_or_reject_order, ActorType
    
    auth = await require_admin_access(request, authorization)
    
    # Use the centralized approval service
    result = await approve_or_reject_order(
        order_id=order_id,
        action=data.action,
        actor_type=ActorType.ADMIN,
        actor_id=auth.user_id,
        final_amount=data.modified_amount,
        rejection_reason=data.reason
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    # Audit log
    await log_audit(auth.user_id, auth.username, f"approval.{data.action}", "order", order_id, {
        "reason": data.reason,
        "modified_amount": data.modified_amount
    })
    
    return {
        "success": True, 
        "message": f"Order {data.action}d", 
        "new_status": "approved" if data.action == "approve" else "rejected",
        **result.data
    }


# ==================== 3. ORDERS ====================

@router.get("/orders", summary="List all orders with filters")
async def list_orders(
    request: Request,
    status_filter: Optional[str] = None,
    order_type: Optional[str] = None,
    suspicious_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(...)
):
    """List all orders with filters"""
    auth = await require_admin_access(request, authorization)
    
    query = "SELECT * FROM orders WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM orders WHERE 1=1"
    params = []
    
    if status_filter:
        params.append(status_filter)
        query += f" AND status = ${len(params)}"
        count_query += f" AND status = ${len(params)}"
    if order_type:
        params.append(order_type)
        query += f" AND order_type = ${len(params)}"
        count_query += f" AND order_type = ${len(params)}"
    if suspicious_only:
        query += " AND (SELECT is_suspicious FROM users WHERE users.user_id = orders.user_id) = TRUE"
        count_query += " AND (SELECT is_suspicious FROM users WHERE users.user_id = orders.user_id) = TRUE"
    
    total = await fetch_one(count_query, *params) if params else await fetch_one(count_query)
    
    params.extend([limit, offset])
    query += f" ORDER BY created_at DESC LIMIT ${len(params)-1} OFFSET ${len(params)}"
    
    orders = await fetch_all(query, *params)
    
    return {
        "orders": [format_order_list(o) for o in orders],
        "total": total['count'],
        "limit": limit,
        "offset": offset
    }


@router.get("/orders/{order_id}", summary="Get order detail with full flow")
async def get_order_detail(
    request: Request,
    order_id: str,
    authorization: str = Header(...)
):
    """Get full order detail with balance flow"""
    auth = await require_admin_access(request, authorization)
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get user info
    user = await fetch_one("SELECT username, real_balance, bonus_balance, play_credits FROM users WHERE user_id = $1", order['user_id'])
    
    # Parse metadata
    metadata = json.loads(order['metadata']) if order.get('metadata') else {}
    
    return {
        "order_id": order['order_id'],
        "user": {
            "user_id": order['user_id'],
            "username": order['username'],
            "current_balance": {
                "real": user['real_balance'] if user else 0,
                "bonus": user['bonus_balance'] if user else 0,
                "play_credits": user['play_credits'] if user else 0
            }
        },
        "order_type": order['order_type'],
        "game": {
            "name": order['game_name'],
            "display_name": order['game_display_name']
        },
        "amounts": {
            "deposit_amount": order['amount'],
            "play_credits_added": order.get('play_credits_added', 0),
            "bonus_added": order['bonus_amount'],
            "total_credited": order['total_amount']
        },
        "consumption": {
            "cash_consumed": order.get('cash_consumed', 0),
            "play_credits_consumed": order.get('play_credits_consumed', 0),
            "bonus_consumed": order.get('bonus_consumed', 0)
        },
        "cashout": {
            "balance_at_cashout": metadata.get('balance_before', {}).get('total', 0) if order['order_type'] == 'withdrawal' else None,
            "min_cashout": metadata.get('min_cashout'),
            "max_cashout": metadata.get('max_cashout'),
            "payout_amount": order.get('payout_amount', 0),
            "void_amount": order.get('void_amount', 0),
            "void_reason": order.get('void_reason')
        },
        "profit": {
            "net": order['amount'] - order.get('payout_amount', 0) if order['order_type'] == 'deposit' else -(order.get('payout_amount', 0))
        },
        "status": order['status'],
        "payment_proof_url": order.get('payment_proof_url'),
        "referral_code": order.get('referral_code'),
        "is_suspicious": order.get('is_suspicious', False),
        "timeline": {
            "created_at": order['created_at'].isoformat() if order.get('created_at') else None,
            "proof_uploaded_at": order['payment_proof_uploaded_at'].isoformat() if order.get('payment_proof_uploaded_at') else None,
            "approved_at": order['approved_at'].isoformat() if order.get('approved_at') else None,
            "approved_by": order.get('approved_by'),
            "rejection_reason": order.get('rejection_reason')
        },
        "metadata": metadata
    }


# ==================== 4. CLIENTS ====================

@router.post("/clients", summary="Create new client")
async def create_client(
    request: Request,
    data: dict,
    authorization: str = Header(...)
):
    """
    Create a new client user (ADMIN ONLY)
    Security: Passwords are hashed before storage, never logged.
    Generated passwords returned ONCE in response only.
    
    Required: username
    Optional: display_name, password (auto-generated if empty), initial_bonus, risk_flags
    """
    auth = await require_admin_access(request, authorization)
    
    # Extract and validate inputs
    username = data.get('username', '').strip()
    user_password = data.get('password', '').strip() or None
    display_name = data.get('display_name', '').strip() or username
    initial_bonus = data.get('initial_bonus', 0)
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    # Validate username format
    if len(username) < 3 or len(username) > 50:
        raise HTTPException(status_code=400, detail="Username must be 3-50 characters")
    
    # Check if username exists
    existing = await fetch_one("SELECT user_id FROM users WHERE username = $1", username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Generate or use provided password
    # SECURITY: Store plaintext only temporarily for response, never log
    password_was_generated = user_password is None
    if password_was_generated:
        plaintext_password = secrets.token_urlsafe(16)  # 21-char secure password
    else:
        plaintext_password = user_password
        # Validate manual password strength
        if len(plaintext_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Hash password IMMEDIATELY
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    password_hash = pwd_context.hash(plaintext_password)
    
    # Generate referral code
    chars = string.ascii_uppercase + string.digits
    referral_code = ''.join(secrets.choice(chars) for _ in range(8))
    
    # Create user with hashed password only
    user_id = str(uuid.uuid4())
    await execute("""
        INSERT INTO users (
            user_id, username, password_hash, display_name, referral_code,
            role, is_active, is_verified, bonus_balance, created_at
        ) VALUES ($1, $2, $3, $4, $5, 'user', TRUE, TRUE, $6, NOW())
    """, user_id, username, password_hash, display_name, referral_code, initial_bonus)
    
    # Apply risk flags if provided
    if data.get('manual_approval_required') or data.get('bonus_disabled') or data.get('withdraw_disabled'):
        await execute("""
            INSERT INTO client_overrides (
                override_id, user_id, manual_approval_required, bonus_disabled, withdraw_disabled, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """, str(uuid.uuid4()), user_id, 
            data.get('manual_approval_required', False),
            data.get('bonus_disabled', False),
            data.get('withdraw_disabled', False),
            auth.user_id)
    
    # Log audit - NEVER log passwords
    await log_audit(auth.user_id, auth.username, "client.created", "user", user_id, {
        "username": username,
        "display_name": display_name,
        "initial_bonus": initial_bonus,
        "password_was_auto_generated": password_was_generated,
        "risk_flags": {
            "manual_approval_required": data.get('manual_approval_required', False),
            "bonus_disabled": data.get('bonus_disabled', False),
            "withdraw_disabled": data.get('withdraw_disabled', False)
        }
    })
    
    # Return response with generated password ONCE
    # SECURITY: Frontend must show warning to save immediately
    response = {
        "user_id": user_id,
        "username": username,
        "referral_code": referral_code,
        "message": "Client created successfully"
    }
    
    # Add generated_password ONLY if auto-generated
    if password_was_generated:
        response["generated_password"] = plaintext_password
    else:
        response["generated_password"] = None  # Manual password not returned
    
    # Backward compatibility (deprecated, prefer generated_password)
    if password_was_generated:
        response["password"] = plaintext_password
    
    return response


@router.get("/clients", summary="List clients")
async def list_clients(
    request: Request,
    search: Optional[str] = None,
    filter_type: Optional[str] = None,  # all, suspicious, referred, non_referred
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(...)
):
    """List clients with filters"""
    auth = await require_admin_access(request, authorization)
    
    query = "SELECT * FROM users WHERE role = 'user'"
    count_query = "SELECT COUNT(*) FROM users WHERE role = 'user'"
    params = []
    
    if search:
        params.append(f'%{search}%')
        query += f" AND (username ILIKE ${len(params)} OR display_name ILIKE ${len(params)} OR referral_code ILIKE ${len(params)})"
        count_query += f" AND (username ILIKE ${len(params)} OR display_name ILIKE ${len(params)} OR referral_code ILIKE ${len(params)})"
    
    if filter_type == 'suspicious':
        query += " AND is_suspicious = TRUE"
        count_query += " AND is_suspicious = TRUE"
    elif filter_type == 'referred':
        query += " AND referred_by_code IS NOT NULL"
        count_query += " AND referred_by_code IS NOT NULL"
    elif filter_type == 'non_referred':
        query += " AND referred_by_code IS NULL"
        count_query += " AND referred_by_code IS NULL"
    
    total = await fetch_one(count_query, *params) if params else await fetch_one(count_query)
    
    params.extend([limit, offset])
    query += f" ORDER BY created_at DESC LIMIT ${len(params)-1} OFFSET ${len(params)}"
    
    users = await fetch_all(query, *params)
    
    return {
        "clients": [format_client_list(u) for u in users],
        "total": total['count'],
        "limit": limit,
        "offset": offset
    }


@router.get("/clients/{user_id}", summary="Get client detail with history")
async def get_client_detail(
    request: Request,
    user_id: str,
    authorization: str = Header(...)
):
    """Get detailed client information including balances, stats, orders, flags"""
    auth = await require_admin_access(request, authorization)
    
    # Get user info
    user = await fetch_one("""
        SELECT user_id, username, display_name, email, referral_code, referred_by_code,
               role, is_active, is_verified,
               real_balance, bonus_balance, play_credits,
               total_deposited, total_withdrawn, created_at,
               withdraw_locked, deposit_locked, is_suspicious, visibility_level
        FROM users
        WHERE user_id = $1
    """, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get orders history
    orders = await fetch_all("""
        SELECT order_id, order_type, game_name, amount, status, 
               bonus_amount, payout_amount, void_amount, void_reason,
               created_at, approved_at
        FROM orders
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 20
    """, user_id)
    
    # Get game credentials
    game_credentials = []
    # Check if table exists before querying
    try:
        game_credentials = await fetch_all("""
            SELECT game_id, game_user_id, created_at
            FROM game_credentials
            WHERE user_id = $1
        """, user_id) or []
    except:
        pass
    
    # Get overrides/flags
    overrides = await fetch_one("""
        SELECT custom_deposit_bonus, custom_cashout_min, custom_cashout_max,
               manual_approval_required, bonus_disabled, withdraw_disabled
        FROM client_overrides
        WHERE user_id = $1
    """, user_id)
    
    # Build response matching frontend expectations
    # Calculate financial summary
    deposits_in = sum(float(o.get('amount', 0)) for o in orders if o.get('order_type') == 'deposit' and o.get('status') == 'approved')
    withdrawals_out = sum(float(o.get('payout_amount', 0) or 0) for o in orders if o.get('order_type') == 'withdrawal' and o.get('status') == 'approved')
    
    return {
        "client": {
            "user_id": user['user_id'],
            "client_id": user['user_id'],  # Frontend expects client_id
            "username": user['username'],
            "display_name": user['display_name'],
            "email": user.get('email'),
            "referral_code": user['referral_code'],
            "referred_by_code": user.get('referred_by_code'),
            "role": user.get('role', 'user'),
            "status": 'active' if user['is_active'] else 'banned',
            "is_active": user['is_active'],
            "is_verified": user.get('is_verified', True),
            "is_suspicious": user.get('is_suspicious', False),
            "withdraw_locked": user.get('withdraw_locked', False),
            "visibility_level": user.get('visibility_level', 'full'),
            "created_at": user['created_at'].isoformat() if user.get('created_at') else None
        },
        "financial_summary": {
            "total_in": deposits_in,
            "total_out": withdrawals_out,
            "net_balance": float(user.get('real_balance', 0) or 0) + float(user.get('bonus_balance', 0) or 0),
            "referral_earnings": 0  # Calculated from referral system
        },
        "credentials": [dict(g) for g in game_credentials],
        "recent_transactions": [
            {
                "transaction_id": o['order_id'],
                "type": 'IN' if o.get('order_type') == 'deposit' else 'OUT',
                "amount": float(o.get('amount', 0)),
                "created_at": o['created_at'].isoformat() if o.get('created_at') else None
            }
            for o in orders[:10]
        ],
        "recent_orders": [dict(o) for o in orders[:20]],
        # Keep additional data for different frontend views
        "balances": {
            "cash": float(user.get('real_balance', 0) or 0),
            "play_credits": float(user.get('play_credits', 0) or 0),
            "bonus": float(user.get('bonus_balance', 0) or 0),
            "total": float(user.get('real_balance', 0) or 0) + float(user.get('bonus_balance', 0) or 0)
        },
        "stats": {
            "total_deposited": float(user.get('total_deposited', 0) or 0),
            "total_withdrawn": float(user.get('total_withdrawn', 0) or 0),
            "total_in": deposits_in,
            "total_out": withdrawals_out,
            "deposit_count": len([o for o in orders if o.get('order_type') == 'deposit']),
            "withdrawal_count": len([o for o in orders if o.get('order_type') == 'withdrawal'])
        },
        "flags": {
            "manual_approval_required": overrides.get('manual_approval_required', False) if overrides else False,
            "bonus_disabled": overrides.get('bonus_disabled', False) if overrides else False,
            "withdraw_disabled": overrides.get('withdraw_disabled', False) if overrides else False,
            "is_suspicious": user.get('is_suspicious', False)
        },
        "history": {
            "orders": [dict(o) for o in orders]
        },
        "game_credentials": [dict(g) for g in game_credentials]
    }


@router.put("/clients/{user_id}", summary="Update client basic fields")
async def update_client(
    request: Request,
    user_id: str,
    data: dict,
    authorization: str = Header(...)
):
    """
    Update client basic fields (status, flags)
    Frontend uses this for status toggles, locks, etc.
    """
    auth = await require_admin_access(request, authorization)
    
    # Check client exists
    client = await fetch_one("SELECT username FROM users WHERE user_id = $1", user_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Build update query dynamically
    updates = []
    params = []
    param_idx = 1
    
    # Status update (is_active)
    if 'status' in data:
        status_value = data['status'] in ['active', True, 'true']
        updates.append(f"is_active = ${param_idx}")
        params.append(status_value)
        param_idx += 1
    
    # Lock/unlock
    if 'is_locked' in data:
        updates.append(f"is_active = ${param_idx}")
        params.append(not data['is_locked'])  # locked = not active
        param_idx += 1
    
    # Suspicious flag (skip if column doesn't exist)
    # if 'is_suspicious' in data:
    #     updates.append(f"is_suspicious = ${param_idx}")
    #     params.append(data['is_suspicious'])
    #     param_idx += 1
    
    # Visibility (optional, if column exists)
    if 'visibility_level' in data:
        # Skip if column doesn't exist
        pass
    
    # Execute updates if any
    if updates:
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ${param_idx}"
        await execute(query, *params)
    
    # Log audit
    await log_audit(auth.user_id, auth.username, "client.updated", "user", user_id, {
        "fields_updated": list(data.keys())
    })
    
    return {"success": True, "message": "Client updated successfully"}


@router.put("/clients/{user_id}/overrides", summary="Update client overrides")
async def update_client_overrides(
    request: Request,
    user_id: str,
    data: ClientOverridesUpdate,
    authorization: str = Header(...)
):
    """Update client-specific overrides and risk flags"""
    auth = await require_admin_access(request, authorization)
    
    user = await fetch_one("SELECT username FROM users WHERE user_id = $1", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updates = []
    params = []
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            params.append(value)
            updates.append(f"{field} = ${len(params)}")
    
    if updates:
        params.append(user_id)
        await execute(
            f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE user_id = ${len(params)}",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "client.overrides_updated", "user", user_id, data.model_dump())
    
    return {"success": True, "message": "Client overrides updated"}


@router.get("/clients/{user_id}/overrides", summary="Get client overrides")
async def get_client_overrides(
    request: Request,
    user_id: str,
    authorization: str = Header(...)
):
    """Get client-specific overrides and risk flags"""
    auth = await require_admin_access(request, authorization)
    
    # Check if client_overrides table exists, if not return defaults
    overrides = await fetch_one("""
        SELECT custom_deposit_bonus, custom_cashout_min, custom_cashout_max,
               manual_approval_required, bonus_disabled, withdraw_disabled
        FROM client_overrides
        WHERE user_id = $1
    """, user_id)
    
    if not overrides:
        # Return empty overrides
        return {
            "custom_deposit_bonus": None,
            "custom_cashout_min": None,
            "custom_cashout_max": None,
            "manual_approval_required": False,
            "bonus_disabled": False,
            "withdraw_disabled": False
        }
    
    return dict(overrides)


@router.get("/clients/{user_id}/activity", summary="Get client activity timeline")
async def get_client_activity(
    request: Request,
    user_id: str,
    limit: int = 50,
    authorization: str = Header(...)
):
    """Get chronological activity timeline for client"""
    auth = await require_admin_access(request, authorization)
    
    # Gather all activities
    activities = []
    
    # User signup
    user = await fetch_one("SELECT username, created_at FROM users WHERE user_id = $1", user_id)
    if user:
        activities.append({
            "type": "signup",
            "title": "Account Created",
            "description": f"User {user['username']} registered",
            "timestamp": user['created_at'],
            "amount": None
        })
    
    # Deposits
    deposits = await fetch_all("""
        SELECT order_id, amount, bonus_amount, status, created_at
        FROM orders
        WHERE user_id = $1 AND order_type = 'deposit'
        ORDER BY created_at DESC
        LIMIT 20
    """, user_id)
    
    for d in deposits:
        activities.append({
            "type": "deposit",
            "title": f"Deposit {d['status']}",
            "description": f"Deposited ${d['amount']:.2f}, received ${d['bonus_amount']:.2f} bonus",
            "timestamp": d['created_at'],
            "amount": d['amount']
        })
    
    # Withdrawals
    withdrawals = await fetch_all("""
        SELECT order_id, amount, payout_amount, void_amount, status, created_at
        FROM orders
        WHERE user_id = $1 AND order_type = 'withdrawal'
        ORDER BY created_at DESC
        LIMIT 20
    """, user_id)
    
    for w in withdrawals:
        activities.append({
            "type": "withdrawal",
            "title": f"Withdrawal {w['status']}",
            "description": f"Requested ${w['amount']:.2f}, paid ${w.get('payout_amount', 0):.2f}",
            "timestamp": w['created_at'],
            "amount": w.get('payout_amount', 0)
        })
    
    # Promo redemptions
    promos = await fetch_all("""
        SELECT pr.credit_amount, pr.redeemed_at, pc.code
        FROM promo_redemptions pr
        JOIN promo_codes pc ON pr.code_id = pc.code_id
        WHERE pr.user_id = $1
        ORDER BY pr.redeemed_at DESC
        LIMIT 10
    """, user_id)
    
    for p in promos:
        activities.append({
            "type": "bonus",
            "title": "Promo Code Redeemed",
            "description": f"Used code {p['code']} for ${p['credit_amount']:.2f} play credits",
            "timestamp": p['redeemed_at'],
            "amount": p['credit_amount']
        })
    
    # Sort by timestamp descending
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return {"activities": activities[:limit]}


@router.post("/clients/{user_id}/credentials", summary="Add game credentials for client")
async def add_client_credentials(
    request: Request,
    user_id: str,
    authorization: str = Header(...)
):
    """Add game credentials for a client"""
    auth = await require_admin_access(request, authorization)
    
    try:
        body = await request.json()
        game_id = body.get('game_id')
        username = body.get('username', '').strip()
        password = body.get('password', '').strip()
        
        if not game_id or not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "game_id, username, and password are required", "error_code": "E2001"}
            )
        
        # Verify user exists
        user = await fetch_one("SELECT user_id, username FROM users WHERE user_id = $1", user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "User not found", "error_code": "E4001"}
            )
        
        # Verify game exists
        game = await fetch_one("SELECT id, game_name FROM games WHERE id = $1 OR game_id = $1", game_id)
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Game not found", "error_code": "E4002"}
            )
        
        import uuid
        credential_id = str(uuid.uuid4())
        
        await execute("""
            INSERT INTO game_credentials (id, user_id, game_id, username, password, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (user_id, game_id) 
            DO UPDATE SET username = $4, password = $5, updated_at = NOW()
        """, credential_id, user_id, game['id'], username, password)
        
        await log_audit(
            auth['user_id'], auth.get('username', 'admin'), "credentials_added", "user", user_id,
            json.dumps({"game": game['game_name'], "username": username})
        )
        
        return {
            "success": True,
            "message": "Credentials added successfully",
            "credential_id": credential_id
        }
    except HTTPException:
        raise
    except Exception as e:
        # If table doesn't exist, create it
        if "game_credentials" in str(e):
            await execute("""
                CREATE TABLE IF NOT EXISTS game_credentials (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(user_id),
                    game_id UUID NOT NULL REFERENCES games(id),
                    username VARCHAR(255) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP,
                    UNIQUE(user_id, game_id)
                )
            """)
            return await add_client_credentials(request, user_id, authorization)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to add credentials: {str(e)}", "error_code": "E5001"}
        )


# ==================== 5. GAMES ====================

@router.get("/games", summary="List games with analytics")
async def list_games(request: Request, authorization: str = Header(...)):
    """List all games with config and analytics"""
    auth = await require_admin_access(request, authorization)
    
    games = await fetch_all("SELECT * FROM games ORDER BY display_name")
    
    result = []
    for g in games:
        # Get analytics - handle both legacy 'approved' and canonical 'APPROVED_EXECUTED' statuses
        analytics = await fetch_one("""
            SELECT 
                COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_in,
                COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_out,
                COALESCE(SUM(bonus_amount) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_bonus,
                COALESCE(SUM(play_credits_added) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_play_credits,
                COALESCE(SUM(void_amount) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_void
            FROM orders WHERE game_name = $1
        """, g['game_name'])
        
        result.append({
            "game_id": g['game_id'],
            "game_name": g['game_name'],
            "display_name": g['display_name'],
            "description": g.get('description'),
            "is_active": g['is_active'],
            "config": {
                "min_deposit": g['min_deposit_amount'],
                "max_deposit": g['max_deposit_amount'],
                "min_withdrawal": g.get('min_withdrawal_amount', 20),
                "max_withdrawal": g.get('max_withdrawal_amount', 10000),
                "bonus_rules": json.loads(g['bonus_rules']) if isinstance(g.get('bonus_rules'), str) else g.get('bonus_rules', {}),
                "withdrawal_rules": json.loads(g['withdrawal_rules']) if isinstance(g.get('withdrawal_rules'), str) else g.get('withdrawal_rules', {})
            },
            "analytics": {
                "total_in": round(analytics['total_in'], 2),
                "total_out": round(analytics['total_out'], 2),
                "total_bonus": round(analytics['total_bonus'], 2),
                "total_play_credits": round(analytics['total_play_credits'], 2),
                "total_void": round(analytics['total_void'], 2),
                "net_profit": round(analytics['total_in'] - analytics['total_out'], 2)
            }
        })
    
    return {"games": result}


@router.post("/games", summary="Create new game")
async def create_game(
    request: Request,
    authorization: str = Header(...)
):
    """Create a new game"""
    auth = await require_admin_access(request, authorization)
    
    try:
        body = await request.json()
        game_name = body.get('game_name', '').strip()
        display_name = body.get('display_name', '').strip()
        
        if not game_name or not display_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "game_name and display_name are required", "error_code": "E2001"}
            )
        
        # Check if game already exists
        existing = await fetch_one("SELECT id FROM games WHERE game_name = $1", game_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Game with this name already exists", "error_code": "E2002"}
            )
        
        import uuid
        game_id = str(uuid.uuid4())
        
        await execute("""
            INSERT INTO games (
                id, game_id, game_name, display_name, description, 
                is_active, is_featured, min_deposit_amount, max_deposit_amount,
                bonus_rules, withdrawal_rules, created_at
            ) VALUES (
                $1, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW()
            )
        """, 
            game_id, game_name, display_name, 
            body.get('description', ''),
            body.get('is_active', True),
            body.get('is_featured', False),
            body.get('min_deposit', 10),
            body.get('max_deposit', 10000),
            json.dumps(body.get('bonus_rules', {})),
            json.dumps(body.get('withdrawal_rules', {}))
        )
        
        await log_audit(
            auth['user_id'], auth.get('username', 'admin'), "game_created", "game", game_id,
            json.dumps({"game_name": game_name, "display_name": display_name})
        )
        
        return {
            "success": True,
            "message": "Game created successfully",
            "game_id": game_id,
            "game_name": game_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to create game: {str(e)}", "error_code": "E5001"}
        )


@router.put("/games/{game_id}", summary="Update game config")
async def update_game_config(
    request: Request,
    game_id: str,
    data: GameConfigUpdate,
    authorization: str = Header(...)
):
    """Update game-specific configuration"""
    auth = await require_admin_access(request, authorization)
    
    game = await fetch_one("SELECT * FROM games WHERE game_id = $1", game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    updates = []
    params = []
    
    if data.min_deposit_amount is not None:
        params.append(data.min_deposit_amount)
        updates.append(f"min_deposit_amount = ${len(params)}")
    if data.max_deposit_amount is not None:
        params.append(data.max_deposit_amount)
        updates.append(f"max_deposit_amount = ${len(params)}")
    if data.min_withdrawal_amount is not None:
        params.append(data.min_withdrawal_amount)
        updates.append(f"min_withdrawal_amount = ${len(params)}")
    if data.max_withdrawal_amount is not None:
        params.append(data.max_withdrawal_amount)
        updates.append(f"max_withdrawal_amount = ${len(params)}")
    if data.bonus_rules is not None:
        params.append(json.dumps(data.bonus_rules))
        updates.append(f"bonus_rules = ${len(params)}")
    if data.withdrawal_rules is not None:
        params.append(json.dumps(data.withdrawal_rules))
        updates.append(f"withdrawal_rules = ${len(params)}")
    if data.is_active is not None:
        params.append(data.is_active)
        updates.append(f"is_active = ${len(params)}")
    
    if updates:
        params.append(game_id)
        await execute(
            f"UPDATE games SET {', '.join(updates)}, updated_at = NOW() WHERE game_id = ${len(params)}",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "game.config_updated", "game", game_id, data.model_dump())
    
    return {"success": True, "message": f"Game config updated for {game['display_name']}"}


# ==================== 6. RULES (GLOBAL DEFAULTS ONLY) ====================

@router.get("/rules", summary="Get global rules - defaults only")
async def get_global_rules(request: Request, authorization: str = Header(...)):
    """Get ONLY global default rules - no client or game settings"""
    auth = await require_admin_access(request, authorization)
    
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    
    return {
        "global_defaults": {
            "signup_bonus_percent": settings.get('signup_bonus', 0) if settings else 0,
            "default_deposit_bonus_percent": settings.get('default_deposit_bonus', 0) if settings else 0,
            "default_referral_bonus_percent": settings.get('default_referral_bonus', 5) if settings else 5,
            "deposit_block_balance": settings.get('deposit_block_balance', 5) if settings else 5,
            "min_cashout_multiplier": settings.get('min_cashout_multiplier', 1) if settings else 1,
            "max_cashout_multiplier": settings.get('max_cashout_multiplier', 3) if settings else 3
        },
        "approval_defaults": {
            "auto_approve_deposits": settings.get('auto_approve_deposits', False) if settings else False,
            "auto_approve_withdrawals": settings.get('auto_approve_withdrawals', False) if settings else False
        },
        "note": "Per-client overrides are in Clients. Per-game settings are in Games."
    }


@router.put("/rules", summary="Update global rules")
async def update_global_rules(
    request: Request,
    data: GlobalRulesUpdate,
    authorization: str = Header(...)
):
    """Update ONLY global default rules"""
    auth = await require_admin_access(request, authorization)
    
    updates = []
    params = []
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            params.append(value)
            updates.append(f"{field} = ${len(params)}")
    
    if updates:
        await execute(
            f"UPDATE system_settings SET {', '.join(updates)}, updated_at = NOW() WHERE id = 'global'",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "rules.global_updated", "config", "global", data.model_dump())
    
    return {"success": True, "message": "Global rules updated"}


# ==================== 7. REFERRALS ====================

@router.get("/referrals/dashboard", summary="Referral dashboard")
async def get_referral_dashboard(request: Request, authorization: str = Header(...)):
    """Referral system overview"""
    auth = await require_admin_access(request, authorization)
    
    stats = await fetch_one("""
        SELECT 
            COUNT(DISTINCT user_id) FILTER (WHERE referred_by_code IS NOT NULL) as referred_users,
            COUNT(DISTINCT referred_by_code) FILTER (WHERE referred_by_code IS NOT NULL) as active_referrers
        FROM users WHERE role = 'user'
    """)
    
    top_referrers = await fetch_all("""
        SELECT u.username, u.referral_code, COUNT(r.user_id) as referral_count
        FROM users u
        LEFT JOIN users r ON r.referred_by_code = u.referral_code
        WHERE u.role = 'user'
        GROUP BY u.user_id, u.username, u.referral_code
        HAVING COUNT(r.user_id) > 0
        ORDER BY referral_count DESC
        LIMIT 10
    """)
    
    return {
        "stats": {
            "total_referred_users": stats['referred_users'],
            "active_referrers": stats['active_referrers']
        },
        "top_referrers": [{
            "username": r['username'],
            "referral_code": r['referral_code'],
            "referral_count": r['referral_count']
        } for r in top_referrers]
    }


@router.get("/referrals/ledger", summary="Referral ledger")
async def get_referral_ledger(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(...)
):
    """List all referral relationships"""
    auth = await require_admin_access(request, authorization)
    
    referrals = await fetch_all("""
        SELECT u.username as user, u.created_at, r.username as referrer, r.referral_code
        FROM users u
        JOIN users r ON u.referred_by_code = r.referral_code
        WHERE u.referred_by_code IS NOT NULL
        ORDER BY u.created_at DESC
        LIMIT $1 OFFSET $2
    """, limit, offset)
    
    return {
        "ledger": [{
            "user": r['user'],
            "referrer": r['referrer'],
            "referral_code": r['referral_code'],
            "joined_at": r['created_at'].isoformat() if r.get('created_at') else None
        } for r in referrals]
    }


# ==================== 8. PROMO CODES ====================

@router.get("/promo-codes", summary="List promo codes")
async def list_promo_codes(request: Request, authorization: str = Header(...)):
    """List all promo codes"""
    auth = await require_admin_access(request, authorization)
    
    codes = await fetch_all("SELECT * FROM promo_codes ORDER BY created_at DESC")
    
    return {
        "promo_codes": [{
            "code_id": c['code_id'],
            "code": c['code'],
            "credit_amount": c['credit_amount'],
            "max_redemptions": c.get('max_redemptions'),
            "current_redemptions": c.get('current_redemptions', 0),
            "expires_at": c['expires_at'].isoformat() if c.get('expires_at') else None,
            "is_active": c['is_active'],
            "created_at": c['created_at'].isoformat() if c.get('created_at') else None
        } for c in codes]
    }


@router.post("/promo-codes", summary="Create promo code")
async def create_promo_code(
    request: Request,
    data: PromoCodeCreate,
    authorization: str = Header(...)
):
    """Create a new promo code for play credits"""
    auth = await require_admin_access(request, authorization)
    
    # Check if code exists
    existing = await fetch_one("SELECT code_id FROM promo_codes WHERE code = $1", data.code.upper())
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already exists")
    
    code_id = str(uuid.uuid4())
    
    await execute("""
        INSERT INTO promo_codes (code_id, code, credit_amount, max_redemptions, expires_at, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, code_id, data.code.upper(), data.credit_amount, data.max_redemptions, data.expires_at, auth.user_id)
    
    await log_audit(auth.user_id, auth.username, "promo.created", "promo_code", code_id, {
        "code": data.code.upper(),
        "credit_amount": data.credit_amount
    })
    
    return {"success": True, "code_id": code_id, "message": f"Promo code {data.code.upper()} created"}


@router.put("/promo-codes/{code_id}/disable", summary="Disable promo code")
async def disable_promo_code(
    request: Request,
    code_id: str,
    authorization: str = Header(...)
):
    """Disable a promo code"""
    auth = await require_admin_access(request, authorization)
    
    await execute("UPDATE promo_codes SET is_active = FALSE WHERE code_id = $1", code_id)
    await log_audit(auth.user_id, auth.username, "promo.disabled", "promo_code", code_id)
    
    return {"success": True, "message": "Promo code disabled"}


@router.get("/promo-codes/{code_id}/redemptions", summary="View redemption history")
async def get_promo_redemptions(
    request: Request,
    code_id: str,
    authorization: str = Header(...)
):
    """View redemption history for a promo code"""
    auth = await require_admin_access(request, authorization)
    
    redemptions = await fetch_all("""
        SELECT pr.*, u.username FROM promo_redemptions pr
        JOIN users u ON pr.user_id = u.user_id
        WHERE pr.code_id = $1
        ORDER BY pr.redeemed_at DESC
    """, code_id)
    
    return {
        "redemptions": [{
            "redemption_id": r['redemption_id'],
            "username": r['username'],
            "credit_amount": r['credit_amount'],
            "redeemed_at": r['redeemed_at'].isoformat() if r.get('redeemed_at') else None
        } for r in redemptions]
    }


# ==================== 9. REPORTS ====================

@router.get("/reports/balance-flow", summary="Balance flow report")
async def get_balance_flow_report(
    request: Request,
    days: int = 30,
    authorization: str = Header(...)
):
    """Balance flow report"""
    auth = await require_admin_access(request, authorization)
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Handle both legacy 'approved' and canonical 'APPROVED_EXECUTED' statuses
    flow = await fetch_one("""
        SELECT 
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_deposits,
            COALESCE(SUM(bonus_amount) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_bonus,
            COALESCE(SUM(play_credits_added) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_play_credits,
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_payouts,
            COALESCE(SUM(void_amount) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as total_voided
        FROM orders WHERE created_at >= $1
    """, since)
    
    return {
        "period_days": days,
        "flow": {
            "deposits": round(flow['total_deposits'], 2),
            "bonus_granted": round(flow['total_bonus'], 2),
            "play_credits_granted": round(flow['total_play_credits'], 2),
            "payouts": round(flow['total_payouts'], 2),
            "voided": round(flow['total_voided'], 2),
            "net_profit": round(flow['total_deposits'] - flow['total_payouts'], 2)
        }
    }


@router.get("/reports/profit-by-game", summary="Profit by game")
async def get_profit_by_game(request: Request, authorization: str = Header(...)):
    """Profit breakdown by game"""
    auth = await require_admin_access(request, authorization)
    
    # Handle both legacy 'approved' and canonical 'APPROVED_EXECUTED' statuses
    games = await fetch_all("""
        SELECT 
            game_name,
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) as deposits,
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status IN ('approved', 'APPROVED_EXECUTED')), 0) as payouts,
            COALESCE(SUM(bonus_amount) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as bonus,
            COALESCE(SUM(void_amount) FILTER (WHERE status IN ('approved', 'APPROVED_EXECUTED')), 0) as voided
        FROM orders
        GROUP BY game_name
        ORDER BY (SUM(amount) FILTER (WHERE order_type = 'deposit' AND status IN ('approved', 'APPROVED_EXECUTED')) - 
                  SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status IN ('approved', 'APPROVED_EXECUTED'))) DESC
    """)
    
    return {
        "by_game": [{
            "game": g['game_name'],
            "deposits": round(g['deposits'], 2),
            "payouts": round(g['payouts'], 2),
            "bonus": round(g['bonus'], 2),
            "voided": round(g['voided'], 2),
            "net_profit": round(g['deposits'] - g['payouts'], 2)
        } for g in games]
    }


@router.get("/reports/voids", summary="Void report")
async def get_void_report(
    request: Request,
    days: int = 30,
    authorization: str = Header(...)
):
    """Void report"""
    auth = await require_admin_access(request, authorization)
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    voids = await fetch_all("""
        SELECT order_id, username, game_name, void_amount, void_reason, approved_at
        FROM orders
        WHERE void_amount > 0 AND approved_at >= $1
        ORDER BY approved_at DESC
    """, since)
    
    total = await fetch_one("""
        SELECT COALESCE(SUM(void_amount), 0) as total FROM orders
        WHERE void_amount > 0 AND approved_at >= $1
    """, since)
    
    return {
        "period_days": days,
        "total_voided": round(total['total'], 2),
        "voids": [{
            "order_id": v['order_id'],
            "username": v['username'],
            "game": v['game_name'],
            "amount": round(v['void_amount'], 2),
            "reason": v['void_reason'],
            "date": v['approved_at'].isoformat() if v.get('approved_at') else None
        } for v in voids]
    }


# ==================== 10. SYSTEM ====================

@router.get("/system", summary="System configuration")
async def get_system_config(request: Request, authorization: str = Header(...)):
    """Get system operations config"""
    auth = await require_admin_access(request, authorization)
    
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    
    return {
        "kill_switch": {
            "enabled": settings.get('master_kill_switch', False) if settings else False,
            "reason": settings.get('kill_switch_reason') if settings else None
        },
        "integrations": {
            "telegram_enabled": settings.get('telegram_enabled', False) if settings else False,
            "api_enabled": settings.get('api_enabled', True) if settings else True,
            "webhook_enabled": settings.get('webhook_enabled', True) if settings else True
        },
        "features": {
            "referral_system": settings.get('referral_system_enabled', True) if settings else True,
            "bonus_system": settings.get('bonus_system_enabled', True) if settings else True
        }
    }


@router.put("/system", summary="Update system config")
async def update_system_config(
    request: Request,
    data: SystemConfigUpdate,
    authorization: str = Header(...)
):
    """Update system operations config"""
    auth = await require_admin_access(request, authorization)
    
    updates = []
    params = []
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            params.append(value)
            updates.append(f"{field} = ${len(params)}")
    
    if updates:
        await execute(
            f"UPDATE system_settings SET {', '.join(updates)}, updated_at = NOW() WHERE id = 'global'",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "system.config_updated", "config", "global", data.model_dump())
    
    return {"success": True, "message": "System config updated"}


# ==================== 11. AUDIT LOGS ====================

@router.get("/audit-logs", summary="Get audit logs")
async def get_audit_logs(
    request: Request,
    action_filter: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    authorization: str = Header(...)
):
    """Get audit logs - read only"""
    auth = await require_admin_access(request, authorization)
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if action_filter:
        params.append(f"%{action_filter}%")
        query += f" AND action ILIKE ${len(params)}"
    if resource_type:
        params.append(resource_type)
        query += f" AND resource_type = ${len(params)}"
    
    params.append(limit)
    query += f" ORDER BY created_at DESC LIMIT ${len(params)}"
    
    logs = await fetch_all(query, *params)
    
    return {
        "logs": [{
            "log_id": l['log_id'],
            "username": l.get('username'),
            "action": l['action'],
            "resource_type": l.get('resource_type'),
            "resource_id": l.get('resource_id'),
            "details": json.loads(l['details']) if l.get('details') else None,
            "ip_address": l.get('ip_address'),
            "created_at": l['created_at'].isoformat() if l.get('created_at') else None
        } for l in logs]
    }


# ==================== LEGACY COMPATIBILITY ====================

@router.get("/stats", summary="Legacy stats endpoint", include_in_schema=False)
async def legacy_stats(request: Request, authorization: str = Header(...)):
    """Legacy endpoint - redirects to dashboard"""
    return await get_dashboard(request, authorization)


@router.get("/settings", summary="Legacy settings endpoint", include_in_schema=False)
async def legacy_settings(request: Request, authorization: str = Header(...)):
    """Legacy endpoint - returns combined settings"""
    auth = await require_admin_access(request, authorization)
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    if not settings:
        return {}
    return {k: v for k, v in settings.items() if k != 'id'}


@router.put("/settings", summary="Legacy settings update", include_in_schema=False)
async def legacy_settings_update(request: Request, authorization: str = Header(...)):
    """Legacy endpoint"""
    return await update_global_rules(request, GlobalRulesUpdate(), authorization)


# ==================== HELPERS ====================

def format_order_list(o: dict) -> dict:
    return {
        "order_id": o['order_id'],
        "username": o['username'],
        "order_type": o['order_type'],
        "game_name": o.get('game_name'),
        "amount": o['amount'],
        "bonus_amount": o.get('bonus_amount', 0),
        "payout_amount": o.get('payout_amount', 0),
        "void_amount": o.get('void_amount', 0),
        "status": o['status'],
        "is_suspicious": o.get('is_suspicious', False),
        "created_at": o['created_at'].isoformat() if o.get('created_at') else None
    }


def format_client_list(u: dict) -> dict:
    return {
        "user_id": u['user_id'],
        "username": u['username'],
        "display_name": u.get('display_name'),
        "referral_code": u['referral_code'],
        "balance": {
            "real": u.get('real_balance', 0),
            "bonus": u.get('bonus_balance', 0),
            "play_credits": u.get('play_credits', 0)
        },
        "is_suspicious": u.get('is_suspicious', False),
        "is_active": u['is_active'],
        "created_at": u['created_at'].isoformat() if u.get('created_at') else None
    }


async def table_exists(table_name: str) -> bool:
    result = await fetch_one("""
        SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)
    """, table_name)
    return result['exists'] if result else False


async def log_audit(user_id, username, action, resource_type, resource_id, details=None):
    """Log an audit event"""
    log_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    ''', log_id, user_id, username, action, resource_type, resource_id,
       json.dumps(details) if details else None)
