"""
API v1 Order Routes - COMPLETE ORDER SYSTEM
Supports deposit and withdrawal orders with rules engine validation
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import json

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from ..services import (
    validate_deposit_order,
    validate_withdrawal_order,
    trigger_webhooks, 
    log_audit,
    list_games
)
from .dependencies import get_client_ip, authenticate_request

router = APIRouter(prefix="/orders", tags=["Orders"])


# ==================== MODELS ====================

class DepositValidateRequest(BaseModel):
    """Deposit validation request"""
    username: str
    password: str
    game_name: str
    amount: float = Field(..., gt=0, description="Deposit amount")
    referral_code: Optional[str] = None


class DepositCreateRequest(BaseModel):
    """Deposit creation request"""
    username: str
    password: str
    game_name: str
    amount: float = Field(..., gt=0)
    referral_code: Optional[str] = None
    metadata: Optional[dict] = None


class WithdrawalValidateRequest(BaseModel):
    """Withdrawal validation request"""
    username: str
    password: str
    game_name: str


class WithdrawalCreateRequest(BaseModel):
    """Withdrawal creation request"""
    username: str
    password: str
    game_name: str
    metadata: Optional[dict] = None


class OrderListRequest(BaseModel):
    """Order list request"""
    username: str
    password: str
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    status: Optional[str] = None
    order_type: Optional[str] = None


# ==================== DEPOSIT ENDPOINTS ====================

@router.post(
    "/deposit/validate",
    summary="Validate deposit order",
    description="""
    Validate a deposit order with full rules engine:
    - CLIENT > GAME > GLOBAL priority for limits
    - Balance blocking rules
    - Bonus calculation with signup, referral, and game bonuses
    """
)
async def validate_deposit(
    request: Request,
    data: DepositValidateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Validate deposit order without creating"""
    auth = await authenticate_request(request, data.username, data.password, authorization)
    
    success, result = await validate_deposit_order(
        user_id=auth.user_id,
        game_name=data.game_name,
        amount=data.amount,
        referral_code=data.referral_code
    )
    
    if not success:
        return {
            "success": False,
            "valid": False,
            **result
        }
    
    return {
        "success": True,
        "valid": True,
        **result
    }


@router.post(
    "/deposit/create",
    summary="Create deposit order",
    description="""
    Create a deposit order with bonus calculation.
    Order starts in 'initiated' status, awaiting payment proof.
    """
)
async def create_deposit(
    request: Request,
    data: DepositCreateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Create a deposit order"""
    auth = await authenticate_request(request, data.username, data.password, authorization)
    ip_address = await get_client_ip(request)
    
    # Check idempotency
    if idempotency_key:
        existing = await fetch_one("SELECT * FROM orders WHERE idempotency_key = $1", idempotency_key)
        if existing:
            return {
                "success": True,
                "message": "Order already exists (idempotent)",
                "order": format_order(existing)
            }
    
    # Validate
    success, validation = await validate_deposit_order(
        user_id=auth.user_id,
        game_name=data.game_name,
        amount=data.amount,
        referral_code=data.referral_code
    )
    
    if not success:
        return {
            "success": False,
            "message": validation.get('message', 'Validation failed'),
            "error_code": validation.get('error_code')
        }
    
    # Create order
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    bonus_info = validation.get('bonus_calculation', {})
    
    await execute('''
        INSERT INTO orders (
            order_id, user_id, username, order_type, game_name, game_display_name,
            amount, bonus_amount, total_amount, referral_code,
            status, idempotency_key, metadata, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
    ''',
        order_id, auth.user_id, auth.username, 'deposit',
        validation['game_name'], validation['game_display_name'],
        data.amount, bonus_info.get('total_bonus', 0), validation['total_amount'],
        data.referral_code.upper() if data.referral_code else None,
        'initiated', idempotency_key,
        json.dumps({
            **(data.metadata or {}),
            'bonus_calculation': bonus_info,
            'rules_applied': validation.get('rules_applied', [])
        }),
        now
    )
    
    # Log audit
    await log_audit(
        auth.user_id, auth.username, "order.deposit_created", "order", order_id,
        {"amount": data.amount, "game": data.game_name, "bonus": bonus_info.get('total_bonus', 0)},
        ip_address
    )
    
    # Trigger webhook
    await trigger_webhooks("order.created", {
        "order_id": order_id,
        "order_type": "deposit",
        "username": auth.username,
        "game": data.game_name,
        "amount": data.amount,
        "bonus_amount": bonus_info.get('total_bonus', 0),
        "total_amount": validation['total_amount']
    }, auth.user_id)
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    
    return {
        "success": True,
        "message": "Deposit order created. Upload payment proof to proceed.",
        "order": format_order(order)
    }


# ==================== WITHDRAWAL ENDPOINTS ====================

@router.post(
    "/withdrawal/validate",
    summary="Validate withdrawal order",
    description="""
    Validate a withdrawal/cashout with full rules engine:
    - CLIENT > GAME > GLOBAL priority for multipliers
    - Min/Max cashout = multiplier × last deposit
    - Returns payout_amount and void_amount calculations
    - ALL balance is redeemed (mandatory)
    - CASH consumed FIRST, then BONUS
    """
)
async def validate_withdrawal(
    request: Request,
    data: WithdrawalValidateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Validate withdrawal order with cashout calculation"""
    auth = await authenticate_request(request, data.username, data.password, authorization)
    
    success, result = await validate_withdrawal_order(
        user_id=auth.user_id,
        game_name=data.game_name
    )
    
    if not success:
        return {
            "success": False,
            "valid": False,
            **result
        }
    
    return {
        "success": True,
        "valid": True,
        **result
    }


@router.post(
    "/withdrawal/create",
    summary="Create withdrawal order",
    description="""
    Create a withdrawal order. 
    
    MANDATORY RULES:
    - ALL balance is redeemed
    - payout_amount = MIN(balance, max_cashout)
    - void_amount = MAX(0, balance - max_cashout)
    - CASH consumed first, BONUS consumed after
    
    Order starts in 'pending_review' status for admin approval.
    """
)
async def create_withdrawal(
    request: Request,
    data: WithdrawalCreateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Create a withdrawal order"""
    auth = await authenticate_request(request, data.username, data.password, authorization)
    ip_address = await get_client_ip(request)
    
    # Check idempotency
    if idempotency_key:
        existing = await fetch_one("SELECT * FROM orders WHERE idempotency_key = $1", idempotency_key)
        if existing:
            return {
                "success": True,
                "message": "Order already exists (idempotent)",
                "order": format_order(existing)
            }
    
    # Validate with full cashout calculation
    success, validation = await validate_withdrawal_order(
        user_id=auth.user_id,
        game_name=data.game_name
    )
    
    if not success:
        return {
            "success": False,
            "message": validation.get('message', 'Validation failed'),
            "error_code": validation.get('error_code'),
            "details": validation
        }
    
    # Extract cashout calculation
    cashout = validation['cashout_calculation']
    
    # Create withdrawal order
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Store all details in metadata for audit
    order_metadata = {
        **(data.metadata or {}),
        'last_deposit_order_id': validation.get('last_deposit_order_id'),
        'last_deposit_amount': validation.get('last_deposit_amount'),
        'min_multiplier': validation.get('min_multiplier'),
        'max_multiplier': validation.get('max_multiplier'),
        'balance_before': validation.get('current_balance'),
        'cashout_calculation': cashout,
        'rules_applied': validation.get('rules_applied', [])
    }
    
    await execute('''
        INSERT INTO orders (
            order_id, user_id, username, order_type, game_name, game_display_name,
            amount, bonus_amount, total_amount, 
            payout_amount, void_amount, void_reason,
            cash_consumed, bonus_consumed,
            status, idempotency_key, metadata, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
    ''',
        order_id, auth.user_id, auth.username, 'withdrawal',
        validation['game_name'], validation['game_display_name'],
        validation['current_balance']['total'],  # Total balance being withdrawn
        0,  # No bonus added for withdrawals
        validation['current_balance']['total'],  # Total is the full balance
        cashout['payout_amount'],
        cashout['void_amount'],
        cashout.get('void_reason'),
        cashout['cash_consumed'],
        cashout['bonus_consumed'],
        'pending_review',  # Withdrawals need review
        idempotency_key,
        json.dumps(order_metadata),
        now
    )
    
    # Deduct balance immediately (pending withdrawal)
    await execute('''
        UPDATE users 
        SET real_balance = real_balance - $1,
            bonus_balance = bonus_balance - $2,
            updated_at = NOW()
        WHERE user_id = $3
    ''', 
        cashout['cash_consumed'] + cashout.get('cash_voided', 0),
        cashout['bonus_consumed'] + cashout.get('bonus_voided', 0),
        auth.user_id
    )
    
    # Log audit
    await log_audit(
        auth.user_id, auth.username, "order.withdrawal_created", "order", order_id,
        {
            "payout_amount": cashout['payout_amount'],
            "void_amount": cashout['void_amount'],
            "void_reason": cashout.get('void_reason'),
            "game": data.game_name
        },
        ip_address
    )
    
    # Trigger webhook
    await trigger_webhooks("order.created", {
        "order_id": order_id,
        "order_type": "withdrawal",
        "username": auth.username,
        "game": data.game_name,
        "payout_amount": cashout['payout_amount'],
        "void_amount": cashout['void_amount']
    }, auth.user_id)
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    
    return {
        "success": True,
        "message": f"Withdrawal order created. Payout: ${cashout['payout_amount']:.2f}" + 
                  (f", Voided: ${cashout['void_amount']:.2f} ({cashout['void_reason']})" if cashout['void_amount'] > 0 else ""),
        "order": format_order(order),
        "cashout_details": cashout
    }


# ==================== LEGACY ENDPOINTS (backwards compatible) ====================

@router.post("/validate", summary="Validate order (legacy)", include_in_schema=False)
async def validate_order_legacy(
    request: Request,
    data: DepositValidateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Legacy endpoint - redirects to deposit/validate"""
    return await validate_deposit(request, data, authorization)


@router.post("/create", summary="Create order (legacy)", include_in_schema=False)
async def create_order_legacy(
    request: Request,
    data: DepositCreateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Legacy endpoint - redirects to deposit/create"""
    return await create_deposit(request, data, authorization, idempotency_key)


# ==================== ORDER RETRIEVAL ====================

@router.get(
    "/{order_id}",
    summary="Get order by ID"
)
async def get_order_by_id(
    request: Request,
    order_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """
    Get order details by ID.
    
    SECURITY (IDOR Prevention):
    - Client can only access their own orders
    - Admin can access any order
    - Returns 403 if client tries to access another user's order
    """
    from ..core.auth import get_current_user, enforce_ownership, AuthenticatedUser
    
    # Get authenticated user
    user = await get_current_user(request, authorization, None)
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # IDOR Prevention: Enforce ownership
    await enforce_ownership(user, order['user_id'], "order")
    
    return {
        "success": True,
        "order": format_order(order, include_details=True)
    }


@router.post(
    "/list",
    summary="List user orders"
)
async def list_orders(
    request: Request,
    data: OrderListRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Get paginated list of orders"""
    auth = await authenticate_request(request, data.username, data.password, authorization)
    
    offset = (data.page - 1) * data.page_size
    
    query = "SELECT * FROM orders WHERE user_id = $1"
    count_query = "SELECT COUNT(*) FROM orders WHERE user_id = $1"
    params = [auth.user_id]
    
    if data.status:
        params.append(data.status)
        query += f" AND status = ${len(params)}"
        count_query += f" AND status = ${len(params)}"
    
    if data.order_type:
        params.append(data.order_type)
        query += f" AND order_type = ${len(params)}"
        count_query += f" AND order_type = ${len(params)}"
    
    total = await fetch_one(count_query, *params)
    total_count = total['count'] if total else 0
    
    params.extend([data.page_size, offset])
    query += f" ORDER BY created_at DESC LIMIT ${len(params)-1} OFFSET ${len(params)}"
    
    orders = await fetch_all(query, *params)
    
    return {
        "success": True,
        "data": [format_order(o) for o in orders],
        "total": total_count,
        "page": data.page,
        "page_size": data.page_size,
        "has_more": (data.page * data.page_size) < total_count
    }


# ==================== GAMES ====================



@router.get(
    "",
    summary="List all orders",
    responses={200: {"description": "List of orders"}}
)
async def list_all_orders(
    request: Request,
    order_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List orders with optional filters"""
    user = await authenticate_request(request)
    
    # Build query
    conditions = []
    params = []
    param_idx = 1
    
    if user['role'] != 'admin':
        conditions.append(f"user_id = ${param_idx}")
        params.append(user['user_id'])
        param_idx += 1
    
    if order_type:
        conditions.append(f"order_type = ${param_idx}")
        params.append(order_type.upper())
        param_idx += 1
    
    if status:
        conditions.append(f"status = ${param_idx}")
        params.append(status.upper())
        param_idx += 1
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    
    orders = await fetch_all(f"""
        SELECT * FROM orders 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params)
    
    count_params = params[:-2]
    count = await fetch_one(f"SELECT COUNT(*) as total FROM orders {where_clause}", *count_params)
    
    return {
        "success": True,
        "orders": [dict(o) for o in orders],
        "total": count['total'] if count else 0,
        "limit": limit,
        "offset": offset
    }

@router.get(
    "/games/list",
    summary="List available games"
)
async def list_games_endpoint(request: Request):
    """List all active games"""
    games = await list_games()
    
    return {
        "success": True,
        "games": games
    }


# ==================== HELPERS ====================

def format_order(order: dict, include_details: bool = False) -> dict:
    """Format order for response"""
    result = {
        "order_id": order['order_id'],
        "user_id": order['user_id'],
        "username": order['username'],
        "order_type": order.get('order_type', 'deposit'),
        "game_name": order['game_name'],
        "game_display_name": order.get('game_display_name'),
        "amount": order.get('amount', 0),
        "bonus_amount": order.get('bonus_amount', 0),
        "total_amount": order.get('total_amount', 0),
        "referral_code": order.get('referral_code'),
        "status": order['status'],
        "created_at": order['created_at'].isoformat() if order.get('created_at') else None
    }
    
    # Add withdrawal-specific fields
    if order.get('order_type') == 'withdrawal':
        result.update({
            "payout_amount": order.get('payout_amount'),
            "void_amount": order.get('void_amount'),
            "void_reason": order.get('void_reason'),
            "cash_consumed": order.get('cash_consumed'),
            "bonus_consumed": order.get('bonus_consumed')
        })
    
    if include_details:
        result.update({
            "payment_proof_url": order.get('payment_proof_url'),
            "rejection_reason": order.get('rejection_reason'),
            "approved_by": order.get('approved_by'),
            "approved_at": order['approved_at'].isoformat() if order.get('approved_at') else None,
            "updated_at": order['updated_at'].isoformat() if order.get('updated_at') else None,
            "metadata": json.loads(order['metadata']) if order.get('metadata') else None
        })
    
    return result
