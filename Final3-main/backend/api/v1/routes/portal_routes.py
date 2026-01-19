"""
API v1 Client Portal Routes - Enhanced
Wallet breakdown, Bonus progress, Cashout preview, Promo redemption, Account rewards
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import json

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from ..services import log_audit, validate_withdrawal_order

router = APIRouter(prefix="/portal", tags=["Client Portal"])


# ==================== AUTH HELPER ====================

async def get_portal_user(request: Request, portal_token: Optional[str], client_token: Optional[str]):
    """
    Authenticate portal user from either token.
    
    SECURITY: No hardcoded users, full token validation.
    """
    from ..core.auth import get_current_user, AuthenticatedUser
    
    # Build authorization header for canonical auth
    authorization = None
    if client_token:
        authorization = f"Bearer {client_token}"
    
    try:
        # Use canonical auth
        auth_user = await get_current_user(request, authorization, portal_token)
        
        # Get full user record
        user = await fetch_one("SELECT * FROM users WHERE user_id = $1", auth_user.user_id)
        if not user:
            raise HTTPException(status_code=401, detail={"message": "User not found", "error_code": "E1004"})
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail={"message": "Authentication required", "error_code": "E1001"})


# ==================== MODELS ====================

class PromoRedeemRequest(BaseModel):
    """Promo code redemption request"""
    code: str = Field(..., min_length=3, max_length=20)


# ==================== 1) WALLET BREAKDOWN ====================

@router.get("/wallet/breakdown")
async def get_wallet_breakdown(
    request: Request,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get detailed wallet breakdown with locked/withdrawable amounts
    Tab A: Overview
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Get user balances
    cash = float(user.get('real_balance', 0) or 0)
    bonus = float(user.get('bonus_balance', 0) or 0)
    play_credits = float(user.get('play_credits', 0) or 0)
    
    # Check if withdraw is locked
    withdraw_locked = user.get('withdraw_locked', False)
    
    # Get pending withdrawals (these amounts are locked)
    pending = await fetch_one("""
        SELECT COALESCE(SUM(amount), 0) as pending_amount
        FROM orders 
        WHERE user_id = $1 AND order_type = 'withdrawal' AND status IN ('pending_review', 'awaiting_payment_proof')
    """, user['user_id'])
    
    pending_withdrawal = float(pending['pending_amount'] or 0)
    
    # Calculate locked and withdrawable
    # Bonus is never directly withdrawable (it converts via cashout rules)
    locked_amount = bonus + play_credits + pending_withdrawal
    if withdraw_locked:
        locked_amount = cash + bonus + play_credits
    
    withdrawable_amount = max(0, cash - pending_withdrawal) if not withdraw_locked else 0
    
    return {
        "overview": {
            "cash_balance": round(cash, 2),
            "bonus_balance": round(bonus, 2),
            "play_credits": round(play_credits, 2),
            "total_balance": round(cash + bonus + play_credits, 2),
            "locked_amount": round(locked_amount, 2),
            "withdrawable_amount": round(withdrawable_amount, 2),
            "pending_withdrawal": round(pending_withdrawal, 2),
            "withdraw_locked": withdraw_locked,
            "withdraw_lock_reason": "Account restricted" if withdraw_locked else None
        },
        "totals": {
            "total_deposited": round(float(user.get('total_deposited', 0) or 0), 2),
            "total_withdrawn": round(float(user.get('total_withdrawn', 0) or 0), 2)
        }
    }


# ==================== 2) BONUS & PROMO PROGRESS ====================

@router.get("/wallet/bonus-progress")
async def get_bonus_progress(
    request: Request,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get bonus progress tracker with multiplier requirements
    Tab B: Bonus & Promo
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Get system settings for multipliers
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    min_multiplier = float(settings.get('min_cashout_multiplier', 1) if settings else 1)
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    
    # Get last deposit to calculate required play-through
    last_deposit = await fetch_one("""
        SELECT amount, bonus_amount FROM orders 
        WHERE user_id = $1 AND order_type = 'deposit' AND status = 'APPROVED_EXECUTED'
        ORDER BY approved_at DESC LIMIT 1
    """, user['user_id'])
    
    deposit_amount = float(last_deposit['amount'] or 0) if last_deposit else 0
    
    # Required play-through = deposit * min_multiplier
    required_playthrough = deposit_amount * min_multiplier
    
    # Get total played/wagered (from game loads)
    total_wagered = await fetch_one("""
        SELECT COALESCE(SUM(amount + COALESCE(bonus_amount, 0)), 0) as total
        FROM orders 
        WHERE user_id = $1 AND status = 'APPROVED_EXECUTED'
    """, user['user_id'])
    
    current_playthrough = float(total_wagered['total'] or 0)
    
    # Calculate progress percentage
    progress_pct = min(100, (current_playthrough / required_playthrough * 100) if required_playthrough > 0 else 100)
    remaining = max(0, required_playthrough - current_playthrough)
    
    # Get bonus breakdown by source
    signup_bonus = await fetch_one("""
        SELECT COALESCE(SUM(bonus_amount), 0) as total
        FROM orders WHERE user_id = $1 AND status = 'APPROVED_EXECUTED'
        AND metadata::text LIKE '%signup%'
    """, user['user_id'])
    
    deposit_bonus = await fetch_one("""
        SELECT COALESCE(SUM(bonus_amount), 0) as total
        FROM orders WHERE user_id = $1 AND order_type = 'deposit' AND status = 'APPROVED_EXECUTED'
    """, user['user_id'])
    
    # Get promo credits from redemptions
    promo_credits = await fetch_one("""
        SELECT COALESCE(SUM(credit_amount), 0) as total
        FROM promo_redemptions WHERE user_id = $1
    """, user['user_id'])
    
    return {
        "progress_tracker": {
            "required_multiplier": min_multiplier,
            "max_multiplier": max_multiplier,
            "last_deposit_amount": round(deposit_amount, 2),
            "required_playthrough": round(required_playthrough, 2),
            "current_playthrough": round(current_playthrough, 2),
            "progress_percentage": round(progress_pct, 1),
            "remaining_amount": round(remaining, 2),
            "is_eligible_for_withdrawal": progress_pct >= 100
        },
        "bonus_sources": {
            "signup_bonus": round(float(signup_bonus['total'] or 0), 2),
            "deposit_bonus": round(float(deposit_bonus['total'] or 0), 2),
            "promo_credits": round(float(promo_credits['total'] or 0), 2),
            "total_bonus_received": round(
                float(signup_bonus['total'] or 0) + 
                float(deposit_bonus['total'] or 0) + 
                float(promo_credits['total'] or 0), 2
            )
        },
        "current_bonus_balance": round(float(user.get('bonus_balance', 0) or 0), 2)
    }


# ==================== 3) CASHOUT PREVIEW ====================

@router.get("/wallet/cashout-preview")
async def get_cashout_preview(
    request: Request,
    game_name: Optional[str] = None,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Preview what would happen if user withdraws now
    Tab C: Cashout Preview (READ-ONLY)
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Get a default game if not specified
    if not game_name:
        game = await fetch_one("SELECT game_name FROM games WHERE is_active = TRUE LIMIT 1")
        game_name = game['game_name'] if game else 'default'
    
    # Use the withdrawal validation to get accurate calculation
    success, result = await validate_withdrawal_order(
        user_id=user['user_id'],
        game_name=game_name
    )
    
    if not success:
        # Return preview with block reason
        return {
            "can_withdraw": False,
            "block_reason": result.get('message', 'Withdrawal not available'),
            "error_code": result.get('error_code'),
            "current_balance": {
                "cash": round(float(user.get('real_balance', 0) or 0), 2),
                "bonus": round(float(user.get('bonus_balance', 0) or 0), 2),
                "total": round(float(user.get('real_balance', 0) or 0) + float(user.get('bonus_balance', 0) or 0), 2)
            },
            "preview": None
        }
    
    cashout = result.get('cashout_calculation', {})
    
    return {
        "can_withdraw": True,
        "block_reason": None,
        "current_balance": result.get('current_balance', {}),
        "preview": {
            "eligible_payout": round(cashout.get('payout_amount', 0), 2),
            "void_amount": round(cashout.get('void_amount', 0), 2),
            "void_reason": cashout.get('void_reason'),
            "cash_to_payout": round(cashout.get('cash_consumed', 0), 2),
            "bonus_to_void": round(cashout.get('bonus_voided', 0) + cashout.get('bonus_consumed', 0), 2),
            "multiplier_used": {
                "min": result.get('min_multiplier'),
                "max": result.get('max_multiplier'),
                "applied": result.get('max_multiplier')
            },
            "last_deposit_amount": result.get('last_deposit_amount'),
            "max_cashout_limit": round(result.get('last_deposit_amount', 0) * result.get('max_multiplier', 3), 2)
        },
        "explanation": f"Based on your last deposit of ${result.get('last_deposit_amount', 0):.2f}, " +
                      f"max cashout is ${result.get('last_deposit_amount', 0) * result.get('max_multiplier', 3):.2f} " +
                      f"({result.get('max_multiplier', 3)}x multiplier). " +
                      (f"${cashout.get('void_amount', 0):.2f} will be voided as it exceeds the limit." 
                       if cashout.get('void_amount', 0) > 0 else "")
    }


# ==================== 4) PROMO CODE REDEMPTION ====================

@router.post("/promo/redeem")
async def redeem_promo_code(
    request: Request,
    data: PromoRedeemRequest,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Redeem a promo code - credits are added as PLAY CREDITS only
    
    Validation order:
    1. Invalid code (not found)
    2. Disabled promo (is_active = false)
    3. Expired promo (expires_at < now)
    4. Already redeemed by user
    5. Usage limit reached (current_redemptions >= max_redemptions)
    6. Success - apply reward
    """
    try:
        client_token = authorization.replace("Bearer ", "") if authorization else None
        user = await get_portal_user(request, x_portal_token, client_token)
        
        code = data.code.upper().strip()
        
        # 1. Find the promo code - Invalid code check
        promo = await fetch_one("""
            SELECT * FROM promo_codes 
            WHERE code = $1
        """, code)
        
        if not promo:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Invalid promo code."
                }
            )
        
        # 2. Check if code is disabled (is_active = false)
        if not promo.get('is_active', True):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "This promo code is disabled."
                }
            )
        
        # 3. Check if expired
        if promo.get('expires_at') and promo['expires_at'] < datetime.now(timezone.utc):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "This promo code has expired."
                }
            )
        
        # 4. Check if user already redeemed this code
        existing = await fetch_one("""
            SELECT * FROM promo_redemptions 
            WHERE code_id = $1 AND user_id = $2
        """, promo['code_id'], user['user_id'])
        
        if existing:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "You have already redeemed this promo code."
                }
            )
        
        # 5. Check usage limit (current_redemptions >= max_redemptions)
        max_redemptions = promo.get('max_redemptions')
        current_redemptions = promo.get('current_redemptions', 0) or 0
        
        if max_redemptions and current_redemptions >= max_redemptions:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "This promo code has reached its usage limit."
                }
            )
        
        # 6. SUCCESS - Apply reward
        bonus_amount = float(promo.get('credit_amount', 0))
        
        if bonus_amount <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "This promo code has no value."
                }
            )
        
        # Record redemption
        redemption_id = str(uuid.uuid4())
        await execute("""
            INSERT INTO promo_redemptions (redemption_id, code_id, user_id, credit_amount, redeemed_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, redemption_id, promo['code_id'], user['user_id'], bonus_amount)
        
        # Increment current_redemptions on promo_codes table
        await execute("""
            UPDATE promo_codes 
            SET current_redemptions = COALESCE(current_redemptions, 0) + 1
            WHERE code_id = $1
        """, promo['code_id'])
        
        # Add play credits to user balance
        await execute("""
            UPDATE users 
            SET play_credits = COALESCE(play_credits, 0) + $1,
                updated_at = NOW()
            WHERE user_id = $2
        """, bonus_amount, user['user_id'])
        
        # Log audit
        await log_audit(
            user['user_id'], user['username'], "promo.redeemed", "promo", promo['code_id'],
            {"code": code, "bonus_amount": bonus_amount}
        )
        
        # Emit promo code redeemed notification (non-blocking)
        try:
            from ..core.notification_router import emit_event, EventType
            await emit_event(
                event_type=EventType.PROMO_CODE_REDEEMED,
                title="🎟️ Promo Code Redeemed",
                message=f"Client {user['display_name']} redeemed promo code!\n\nCode: {code}\nBonus: ${bonus_amount:,.2f}",
                reference_id=redemption_id,
                reference_type="promo_redemption",
                user_id=user['user_id'],
                username=user['username'],
                display_name=user.get('display_name'),
                amount=bonus_amount,
                extra_data={"code": code},
                requires_action=False
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to send promo notification: {e}")
        
        # SUCCESS RESPONSE (200)
        return {
            "success": True,
            "message": f"Successful! Redeemed ${bonus_amount:.2f}.",
            "data": {
                "bonus_amount": bonus_amount
            }
        }
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Promo redemption error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An error occurred while processing your request. Please try again."
            }
        )


@router.get("/promo/history")
async def get_promo_history(
    request: Request,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Get user's promo code redemption history"""
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    redemptions = await fetch_all("""
        SELECT pr.*, pc.code, pc.description
        FROM promo_redemptions pr
        JOIN promo_codes pc ON pr.code_id = pc.code_id
        WHERE pr.user_id = $1
        ORDER BY pr.redeemed_at DESC
    """, user['user_id'])
    
    return {
        "redemptions": [{
            "code": r['code'],
            "description": r.get('description'),
            "credit_amount": round(float(r['credit_amount']), 2),
            "redeemed_at": r['redeemed_at'].isoformat() if r.get('redeemed_at') else None
        } for r in redemptions]
    }


# ==================== 5) ACCOUNT REWARDS ====================

@router.get("/rewards")
async def get_client_rewards(
    request: Request,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get rewards earned by the client
    Shows only rewards that are visible to clients
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Get granted rewards
    rewards = await fetch_all("""
        SELECT rg.*, rd.name, rd.description, rd.reward_type, rd.trigger_type
        FROM reward_grants rg
        JOIN reward_definitions rd ON rg.reward_id = rd.reward_id
        WHERE rg.user_id = $1 AND rd.visible_to_client = TRUE
        ORDER BY rg.granted_at DESC
    """, user['user_id'])
    
    return {
        "rewards": [{
            "name": r['name'],
            "description": r.get('description'),
            "reward_type": r['reward_type'],
            "trigger_type": r['trigger_type'],
            "amount": round(float(r['amount']), 2),
            "granted_at": r['granted_at'].isoformat() if r.get('granted_at') else None
        } for r in rewards],
        "total_rewards_earned": round(sum(float(r['amount']) for r in rewards), 2)
    }


# ==================== 6) ENHANCED TRANSACTIONS ====================

@router.get("/transactions/enhanced")
async def get_enhanced_transactions(
    request: Request,
    type_filter: Optional[str] = None,
    limit: int = 50,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get enhanced transaction list with approval status, rejection reason, bonus adjustments, void records
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Build query
    query = """
        SELECT order_id, order_type, game_name, game_display_name,
               amount, bonus_amount, total_amount,
               payout_amount, void_amount, void_reason,
               status, rejection_reason, 
               created_at, approved_at
        FROM orders
        WHERE user_id = $1
    """
    params = [user['user_id']]
    
    if type_filter and type_filter != 'all':
        query += " AND order_type = $2"
        params.append(type_filter)
    
    query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
    params.append(limit)
    
    orders = await fetch_all(query, *params)
    
    transactions = []
    for o in orders:
        tx = {
            "transaction_id": o['order_id'],
            "type": "IN" if o['order_type'] == 'deposit' else "OUT",
            "order_type": o['order_type'],
            "game": o.get('game_display_name') or o.get('game_name'),
            "amount": round(float(o.get('amount', 0)), 2),
            "created_at": o['created_at'].isoformat() if o.get('created_at') else None,
            
            # Approval status
            "status": o['status'],
            "status_label": {
                'initiated': 'Pending',
                'awaiting_payment_proof': 'Awaiting Proof',
                'pending_review': 'Under Review',
                'approved': 'Approved',
                'rejected': 'Rejected',
                'cancelled': 'Cancelled'
            }.get(o['status'], o['status']),
            "approved_at": o['approved_at'].isoformat() if o.get('approved_at') else None,
            
            # Rejection details
            "rejection_reason": o.get('rejection_reason'),
            
            # Bonus adjustments
            "bonus_amount": round(float(o.get('bonus_amount', 0)), 2) if o.get('bonus_amount') else None,
            "total_amount": round(float(o.get('total_amount', 0)), 2),
            
            # Void records (for withdrawals)
            "void_record": {
                "void_amount": round(float(o.get('void_amount', 0)), 2),
                "void_reason": o.get('void_reason')
            } if o.get('void_amount') and float(o.get('void_amount', 0)) > 0 else None,
            
            # Payout (for withdrawals)
            "payout_amount": round(float(o.get('payout_amount', 0)), 2) if o.get('payout_amount') else None
        }
        transactions.append(tx)
    
    return {
        "transactions": transactions,
        "total": len(transactions)
    }


# ==================== 6B) TRANSACTION DETAIL WITH AUDIT TRAIL ====================

@router.get("/transactions/{order_id}")
async def get_transaction_detail(
    request: Request,
    order_id: str,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get detailed transaction info with full audit trail
    Shows: order details, status history, admin actions, payment proof history
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Get order details - ensure user owns this order
    order = await fetch_one("""
        SELECT o.*, u.display_name as user_display_name
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.order_id = $1 AND o.user_id = $2
    """, order_id, user['user_id'])
    
    if not order:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Get audit trail for this order
    audit_logs = await fetch_all("""
        SELECT log_id, action, username, details, old_value, new_value, ip_address, created_at
        FROM audit_logs
        WHERE resource_id = $1 OR (details::text LIKE $2)
        ORDER BY created_at ASC
    """, order_id, f'%{order_id}%')
    
    # Build timeline from order data and audit logs
    timeline = []
    
    # Order created event
    timeline.append({
        "event": "order_created",
        "title": "Order Created",
        "description": f"{order['order_type'].replace('_', ' ').title()} request submitted",
        "timestamp": order['created_at'].isoformat() if order.get('created_at') else None,
        "actor": "Client",
        "icon": "plus"
    })
    
    # Payment proof uploaded
    if order.get('payment_proof_uploaded_at'):
        timeline.append({
            "event": "proof_uploaded",
            "title": "Payment Proof Uploaded",
            "description": "Payment screenshot submitted for review",
            "timestamp": order['payment_proof_uploaded_at'].isoformat(),
            "actor": "Client",
            "icon": "upload"
        })
    
    # Amount adjusted
    if order.get('amount_adjusted') and order.get('adjusted_at'):
        adjusted_by = order.get('adjusted_by', 'Admin')
        original_amount = order.get('metadata', {}).get('original_amount', order['amount'])
        timeline.append({
            "event": "amount_adjusted",
            "title": "Amount Adjusted",
            "description": f"Amount changed from ${original_amount:.2f} to ${order['amount']:.2f}",
            "timestamp": order['adjusted_at'].isoformat(),
            "actor": adjusted_by,
            "icon": "edit"
        })
    
    # Add audit log events
    for log in audit_logs:
        action = log['action']
        details = log.get('details') or {}
        
        # Skip duplicate created events
        if 'created' in action.lower() and any(t['event'] == 'order_created' for t in timeline):
            continue
        
        event_title = action.replace('.', ' ').replace('_', ' ').title()
        event_desc = details.get('reason') or details.get('message') or action
        
        timeline.append({
            "event": action,
            "title": event_title,
            "description": str(event_desc)[:200],
            "timestamp": log['created_at'].isoformat() if log.get('created_at') else None,
            "actor": log.get('username') or 'System',
            "icon": "activity"
        })
    
    # Approved/Rejected event
    if order.get('approved_at'):
        status = order['status']
        if status in ['approved', 'completed']:
            timeline.append({
                "event": "order_approved",
                "title": "Order Approved",
                "description": "Approved by admin",
                "timestamp": order['approved_at'].isoformat(),
                "actor": order.get('approved_by') or 'Admin',
                "icon": "check"
            })
        elif status == 'rejected':
            timeline.append({
                "event": "order_rejected",
                "title": "Order Rejected",
                "description": order.get('rejection_reason') or "Request was declined",
                "timestamp": order['approved_at'].isoformat(),
                "actor": order.get('approved_by') or 'Admin',
                "icon": "x"
            })
    
    # Executed event
    if order.get('executed_at'):
        timeline.append({
            "event": "order_executed",
            "title": "Order Executed",
            "description": order.get('execution_result') or "Funds transferred successfully",
            "timestamp": order['executed_at'].isoformat(),
            "actor": "System",
            "icon": "zap"
        })
    
    # Sort timeline by timestamp
    timeline.sort(key=lambda x: x['timestamp'] or '1970-01-01')
    
    # Build response
    return {
        "order": {
            "order_id": order['order_id'],
            "order_type": order['order_type'],
            "status": order['status'],
            "status_label": {
                'initiated': 'Pending',
                'awaiting_payment_proof': 'Awaiting Proof',
                'pending_review': 'Under Review',
                'approved': 'Approved',
                'completed': 'Completed',
                'rejected': 'Rejected',
                'cancelled': 'Cancelled'
            }.get(order['status'], order['status']),
            "game": order.get('game_display_name') or order.get('game_name'),
            "amount": round(float(order['amount']), 2),
            "bonus_amount": round(float(order.get('bonus_amount', 0)), 2),
            "total_amount": round(float(order.get('total_amount', 0)), 2),
            "payout_amount": round(float(order.get('payout_amount', 0)), 2) if order.get('payout_amount') else None,
            "void_amount": round(float(order.get('void_amount', 0)), 2) if order.get('void_amount') else None,
            "void_reason": order.get('void_reason'),
            "rejection_reason": order.get('rejection_reason'),
            "created_at": order['created_at'].isoformat() if order.get('created_at') else None,
            "approved_at": order['approved_at'].isoformat() if order.get('approved_at') else None,
            "executed_at": order['executed_at'].isoformat() if order.get('executed_at') else None,
            "has_payment_proof": bool(order.get('payment_proof_url')),
            "amount_was_adjusted": order.get('amount_adjusted', False)
        },
        "timeline": timeline,
        "summary": {
            "total_events": len(timeline),
            "current_status": order['status'],
            "is_final": order['status'] in ['approved', 'completed', 'rejected', 'cancelled'],
            "processing_time_hours": None  # Could calculate time between created and approved
        }
    }


# ==================== 7) GAMES WITH RULES ====================

@router.get("/games/rules")
async def get_games_with_rules(
    request: Request,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get games with deposit rules - FIXED VERSION
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Get all active games
    games = await fetch_all("""
        SELECT game_id, game_name, display_name, description, category,
               min_deposit_amount, max_deposit_amount, is_active
        FROM games WHERE is_active = TRUE
        ORDER BY display_name ASC
    """)
    
    result = []
    for game in games:
        result.append({
            "game_id": game['game_id'],
            "game_name": game['game_name'],
            "display_name": game['display_name'],
            "description": game.get('description'),
            "category": game.get('category'),
            "min_amount": float(game.get('min_deposit_amount', 10)),
            "max_amount": float(game.get('max_deposit_amount', 1000)),
            "rules": {
                "min_deposit": float(game.get('min_deposit_amount', 10)),
                "max_deposit": float(game.get('max_deposit_amount', 1000)),
                "min_cashout_multiplier": 1.0,
                "max_cashout_multiplier": 3.0,
                "deposit_bonus_enabled": True,
                "deposit_bonus_percent": 10.0
            }
        })
    
    return {"success": True, "games": result}


# Keep remaining endpoints below



# ==================== 8) REFERRAL DETAILS ====================

@router.get("/referrals/details")
async def get_referral_details(
    request: Request,
    x_portal_token: Optional[str] = Header(None, alias="X-Portal-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get referral program details including commission %, pending vs confirmed earnings, rules
    """
    client_token = authorization.replace("Bearer ", "") if authorization else None
    user = await get_portal_user(request, x_portal_token, client_token)
    
    # Get referral settings from system
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    base_commission = float(settings.get('referral_commission_percent', 5) if settings else 5)
    
    # Tier system (can be stored in DB or hardcoded for now)
    tiers = [
        {"tier": 0, "name": "Starter", "min_refs": 0, "commission": 5},
        {"tier": 1, "name": "Bronze", "min_refs": 10, "commission": 10},
        {"tier": 2, "name": "Silver", "min_refs": 25, "commission": 15},
        {"tier": 3, "name": "Gold", "min_refs": 50, "commission": 20},
        {"tier": 4, "name": "Platinum", "min_refs": 100, "commission": 25},
        {"tier": 5, "name": "Diamond", "min_refs": 200, "commission": 30},
    ]
    
    # Count active referrals (those who have deposited)
    active_count = await fetch_one("""
        SELECT COUNT(DISTINCT u.user_id) as count
        FROM users u
        JOIN orders o ON u.user_id = o.user_id
        WHERE u.referred_by_user_id = $1 AND o.order_type = 'deposit' AND o.status = 'APPROVED_EXECUTED'
    """, user['user_id'])
    
    active_refs = active_count['count'] or 0
    
    # Determine current tier
    current_tier = tiers[0]
    for tier in tiers:
        if active_refs >= tier['min_refs']:
            current_tier = tier
    
    # Get pending earnings (from pending referral deposits)
    pending_earnings = await fetch_one("""
        SELECT COALESCE(SUM(o.amount * $2 / 100), 0) as pending
        FROM users u
        JOIN orders o ON u.user_id = o.user_id
        WHERE u.referred_by_user_id = $1 
        AND o.order_type = 'deposit' 
        AND o.status IN ('pending_review', 'awaiting_payment_proof')
    """, user['user_id'], current_tier['commission'])
    
    # Get confirmed earnings (from approved referral deposits)
    confirmed_earnings = await fetch_one("""
        SELECT COALESCE(SUM(o.amount * $2 / 100), 0) as confirmed
        FROM users u
        JOIN orders o ON u.user_id = o.user_id
        WHERE u.referred_by_user_id = $1 
        AND o.order_type = 'deposit' 
        AND o.status = 'APPROVED_EXECUTED'
    """, user['user_id'], current_tier['commission'])
    
    # Find next tier
    next_tier = None
    for tier in tiers:
        if tier['tier'] == current_tier['tier'] + 1:
            next_tier = tier
            break
    
    return {
        "referral_code": user['referral_code'],
        "commission": {
            "current_percentage": current_tier['commission'],
            "max_percentage": 30,
            "is_lifetime": True,
            "explanation": f"You earn {current_tier['commission']}% commission on ALL deposits made by your referrals - FOREVER!"
        },
        "tier": {
            "current": current_tier,
            "next": next_tier,
            "progress_to_next": active_refs - current_tier['min_refs'],
            "refs_needed_for_next": next_tier['min_refs'] - active_refs if next_tier else 0,
            "all_tiers": tiers
        },
        "earnings": {
            "pending": round(float(pending_earnings['pending'] or 0), 2),
            "confirmed": round(float(confirmed_earnings['confirmed'] or 0), 2),
            "total": round(float(pending_earnings['pending'] or 0) + float(confirmed_earnings['confirmed'] or 0), 2)
        },
        "stats": {
            "active_referrals": active_refs,
            "total_referrals": await fetch_one(
                "SELECT COUNT(*) as count FROM users WHERE referred_by_user_id = $1",
                user['user_id']
            ).then(lambda r: r['count'] if r else 0) if False else (
                await fetch_one("SELECT COUNT(*) as count FROM users WHERE referred_by_user_id = $1", user['user_id'])
            )['count']
        },
        "rules": [
            "Share your referral code with friends",
            "They enter it when signing up via Messenger",
            "Once they make their first deposit, they become 'active'",
            f"You earn {current_tier['commission']}% of ALL their future deposits",
            "Earnings are automatic and lifetime",
            "Get more active referrals to unlock higher commission tiers"
        ]
    }



# ============== Credentials Endpoints ==============

@router.get("/credentials")
async def get_client_credentials(
    request: Request, 
    portal_token: str = Header(None, alias="X-Portal-Token"),
    authorization: str = Header(None)
):
    """Get client's game credentials"""
    # Extract client token from Authorization header
    client_token = None
    if authorization and authorization.startswith("Bearer "):
        client_token = authorization.replace("Bearer ", "")
    
    user = await get_portal_user(request, portal_token, client_token)
    user_id = user['user_id']
    
    try:
        credentials = await fetch_all("""
            SELECT gc.id, gc.game_id, g.name as game_name, g.platform,
                   gc.username, gc.password, gc.created_at
            FROM game_credentials gc
            JOIN games g ON gc.game_id = g.id
            WHERE gc.user_id = $1
            ORDER BY gc.created_at DESC
        """, user_id)
        
        return {
            "credentials": [
                {
                    "id": str(cred['id']),
                    "game_id": str(cred['game_id']),
                    "game_name": cred['game_name'],
                    "platform": cred['platform'],
                    "username": cred['username'],
                    "password": cred['password'],  # Note: Consider masking in production
                    "created_at": cred['created_at'].isoformat() if cred['created_at'] else None
                }
                for cred in credentials
            ]
        }
    except Exception:
        # Return empty list if table doesn't exist or other error
        return {"credentials": []}


# ============== Security Endpoints ==============

@router.post("/security/set-password")
async def set_client_password(
    request: Request,
    portal_token: str = Header(None, alias="X-Portal-Token"),
    authorization: str = Header(None)
):
    """Set up password login for client"""
    # Extract client token from Authorization header
    client_token = None
    if authorization and authorization.startswith("Bearer "):
        client_token = authorization.replace("Bearer ", "")
    
    user = await get_portal_user(request, portal_token, client_token)
    user_id = user['user_id']
    
    try:
        body = await request.json()
        username = body.get('username', '').strip()
        password = body.get('password', '')
        
        if not username or len(username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Username must be at least 3 characters", "error_code": "E2001"}
            )
        
        if not password or len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Password must be at least 6 characters", "error_code": "E2002"}
            )
        
        # Check if username already exists
        existing = await fetch_one("""
            SELECT user_id FROM users WHERE username = $1 AND user_id != $2
        """, username, user_id)
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Username already taken", "error_code": "E2003"}
            )
        
        # Hash password
        from ..core.security import hash_password
        password_hash = hash_password(password)
        
        # Update user
        await execute("""
            UPDATE users 
            SET username = $1, password_hash = $2, has_password = true
            WHERE user_id = $3
        """, username, password_hash, user_id)
        
        return {
            "success": True,
            "message": "Password login set up successfully"
        }
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to set password: {str(err)}", "error_code": "E5001"}
        )
