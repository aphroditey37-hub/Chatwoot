"""
Unified Approval Service
SINGLE source of truth for ALL order/wallet approvals

REFACTORED: Now uses order_lifecycle.py for state transitions.
All status changes go through the canonical state machine.

Used by:
- Telegram webhook callbacks
- Admin UI approvals
- Any other approval path

Enforces:
- State machine transitions (via order_lifecycle)
- Idempotency (can't approve twice)
- Bot permissions (if actor is Telegram bot)
- Amount adjustment limits
- Proper side effects (wallet credit, game load, withdrawal)
- Event emissions
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from enum import Enum

from .database import fetch_one, fetch_all, execute, get_pool
from .notification_router import emit_event, EventType
from .order_lifecycle import (
    OrderStatus, OrderType, OrderErrorCode,
    transition_order, approve_order as lifecycle_approve,
    reject_order as lifecycle_reject, start_processing,
    complete_order, fail_order, requires_approval, is_direct_execution
)

logger = logging.getLogger(__name__)


class ActorType(str, Enum):
    ADMIN = "admin"
    TELEGRAM_BOT = "telegram_bot"
    SYSTEM = "system"


class ApprovalResult:
    def __init__(self, success: bool, message: str, data: Dict = None):
        self.success = success
        self.message = message
        self.data = data or {}


async def approve_or_reject_order(
    order_id: str,
    action: Literal["approve", "reject"],
    actor_type: ActorType,
    actor_id: str,
    final_amount: Optional[float] = None,
    rejection_reason: Optional[str] = None,
    bot_id: Optional[str] = None
) -> ApprovalResult:
    """
    Single approval function for ALL order types.
    
    USES ORDER LIFECYCLE STATE MACHINE for all transitions.
    
    Args:
        order_id: The order to approve/reject
        action: "approve" or "reject"
        actor_type: Who is performing the action
        actor_id: ID of the actor (admin user_id or telegram bot_id)
        final_amount: Optional adjusted amount (only for approval)
        rejection_reason: Reason for rejection
        bot_id: Telegram bot ID (for permission validation)
    
    Returns:
        ApprovalResult with success status and details
    """
    logger.info(f"Processing {action} for order {order_id} by {actor_type}:{actor_id}")
    
    # Validate bot permissions if actor is Telegram bot
    if actor_type == ActorType.TELEGRAM_BOT and bot_id:
        bot = await fetch_one("SELECT * FROM telegram_bots WHERE bot_id = $1", bot_id)
        if not bot:
            return ApprovalResult(False, "Bot not found")
        if not bot.get('is_active'):
            return ApprovalResult(False, "Bot is not active")
        if not bot.get('can_approve_payments'):
            return ApprovalResult(False, "Bot does not have approval permissions")
    
    # Get the order
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        return ApprovalResult(False, "Order not found")
    
    # Check if order type is approvable
    order_type = order.get('order_type', 'deposit')
    if is_direct_execution(order_type):
        return ApprovalResult(
            False, 
            f"Order type '{order_type}' does not require approval",
            {"error_code": OrderErrorCode.NOT_APPROVABLE.value}
        )
    
    # Get user
    user = await fetch_one("SELECT * FROM users WHERE user_id = $1", order['user_id'])
    if not user:
        return ApprovalResult(False, "User not found")
    
    if action == "approve":
        return await _process_approval(order, user, actor_type, actor_id, final_amount)
    else:
        return await _process_rejection(order, user, actor_type, actor_id, rejection_reason)


async def _process_approval(
    order: Dict,
    user: Dict,
    actor_type: ActorType,
    actor_id: str,
    final_amount: Optional[float]
) -> ApprovalResult:
    """
    Process order approval with PROPER STATE TRANSITIONS.
    
    Flow: pending_approval -> approved -> processing -> completed/failed
    
    EXECUTION HONESTY: Only mark as completed after successful execution.
    MONEY SAFETY: Balance changes only committed on successful execution.
    """
    order_id = order['order_id']
    order_type = order.get('order_type', 'deposit')
    
    # Determine final amount (may have been edited)
    amount = final_amount if final_amount is not None else order['amount']
    bonus_amount = order.get('bonus_amount', 0) or 0
    
    # Track if amount was adjusted
    amount_adjusted = final_amount is not None and final_amount != order['amount']
    
    # STEP 1: Transition to approved
    approve_result = await lifecycle_approve(
        order_id=order_id,
        actor_id=actor_id,
        actor_type=actor_type.value,
        final_amount=final_amount,
        reason=f"Approved by {actor_type.value}"
    )
    
    if not approve_result.success:
        if approve_result.is_noop:
            # Already approved - proceed to execute
            logger.info(f"Order {order_id} already approved, proceeding to execute")
        else:
            return ApprovalResult(
                False,
                approve_result.message,
                {"error_code": approve_result.error_code, "already_processed": True}
            )
    
    # STEP 2: Transition to processing
    processing_result = await start_processing(order_id, actor_id, actor_type.value)
    
    if not processing_result.success and not processing_result.is_noop:
        return ApprovalResult(
            False,
            f"Failed to start processing: {processing_result.message}",
            {"error_code": processing_result.error_code}
        )
    
    # STEP 3: Execute side effects based on order type
    execution_success = False
    execution_result = None
    final_status = 'failed'
    
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                if order_type in ['wallet_topup', 'deposit', 'wallet_load']:
                    # Credit wallet
                    current_balance = float(user.get('real_balance', 0) or 0)
                    new_balance = current_balance + amount
                    
                    await conn.execute("""
                        UPDATE users SET 
                            real_balance = $1,
                            bonus_balance = bonus_balance + $2,
                            deposit_count = deposit_count + 1,
                            total_deposited = total_deposited + $3,
                            updated_at = NOW()
                        WHERE user_id = $4
                    """, new_balance, bonus_amount, amount, user['user_id'])
                    
                    # Log to ledger
                    await conn.execute("""
                        INSERT INTO wallet_ledger 
                        (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                         reference_type, reference_id, description, created_at)
                        VALUES ($1, $2, 'credit', $3, $4, $5, 'order', $6, $7, NOW())
                    """, str(uuid.uuid4()), user['user_id'], amount,
                       current_balance, new_balance, order_id,
                       f"Wallet credit via {order.get('payment_method', 'N/A')}")
                    
                    # Update order amount if adjusted
                    if amount_adjusted:
                        await conn.execute("""
                            UPDATE orders SET amount = $1, total_amount = $2, updated_at = NOW()
                            WHERE order_id = $3
                        """, amount, amount + bonus_amount, order_id)
                    
                    execution_success = True
                    execution_result = f"Wallet credited: ₱{amount:,.2f}"
                    
                elif order_type in ['withdrawal', 'withdrawal_wallet']:
                    # MONEY SAFETY: Check balance BEFORE withdrawal
                    current_balance = float(user.get('real_balance', 0) or 0)
                    
                    if current_balance < amount:
                        raise Exception(f"Insufficient balance: has ₱{current_balance:,.2f}, needs ₱{amount:,.2f}")
                    
                    new_balance = current_balance - amount
                    
                    await conn.execute("""
                        UPDATE users SET 
                            real_balance = $1,
                            total_withdrawn = total_withdrawn + $2,
                            updated_at = NOW()
                        WHERE user_id = $3
                    """, new_balance, amount, user['user_id'])
                    
                    # Log to ledger
                    await conn.execute("""
                        INSERT INTO wallet_ledger 
                        (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                         reference_type, reference_id, description, created_at)
                        VALUES ($1, $2, 'debit', $3, $4, $5, 'withdrawal', $6, $7, NOW())
                    """, str(uuid.uuid4()), user['user_id'], amount,
                       current_balance, new_balance, order_id,
                       f"Withdrawal to {order.get('payment_method', 'N/A')}")
                    
                    execution_success = True
                    execution_result = f"Withdrawal processed: ₱{amount:,.2f}"
                    
                elif order_type == 'game_load':
                    # Game load - should not reach here (direct execution)
                    execution_success = True
                    execution_result = "Game load approved"
                
                elif order_type in ['admin_manual_load']:
                    # Admin manual load
                    current_balance = float(user.get('real_balance', 0) or 0)
                    new_balance = current_balance + amount
                    
                    await conn.execute("""
                        UPDATE users SET real_balance = $1, updated_at = NOW()
                        WHERE user_id = $2
                    """, new_balance, user['user_id'])
                    
                    await conn.execute("""
                        INSERT INTO wallet_ledger 
                        (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                         reference_type, reference_id, description, created_at)
                        VALUES ($1, $2, 'credit', $3, $4, $5, 'admin_manual', $6, $7, NOW())
                    """, str(uuid.uuid4()), user['user_id'], amount,
                       current_balance, new_balance, order_id, "Admin manual balance load")
                    
                    execution_success = True
                    execution_result = f"Admin manual load: ₱{amount:,.2f}"
                
                elif order_type in ['admin_manual_withdraw']:
                    # Admin manual withdraw
                    current_balance = float(user.get('real_balance', 0) or 0)
                    
                    if current_balance < amount:
                        raise Exception("Insufficient balance for admin withdrawal")
                    
                    new_balance = current_balance - amount
                    
                    await conn.execute("""
                        UPDATE users SET real_balance = $1, updated_at = NOW()
                        WHERE user_id = $2
                    """, new_balance, user['user_id'])
                    
                    await conn.execute("""
                        INSERT INTO wallet_ledger 
                        (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                         reference_type, reference_id, description, created_at)
                        VALUES ($1, $2, 'debit', $3, $4, $5, 'admin_manual', $6, $7, NOW())
                    """, str(uuid.uuid4()), user['user_id'], amount,
                       current_balance, new_balance, order_id, "Admin manual balance withdraw")
                    
                    execution_success = True
                    execution_result = f"Admin manual withdraw: ₱{amount:,.2f}"
                
                else:
                    # Generic approval
                    execution_success = True
                    execution_result = f"Order approved: {order_type}"
                
    except Exception as e:
        logger.error(f"Order {order_id} execution failed: {e}")
        execution_success = False
        execution_result = str(e)
    
    # STEP 4: Transition to final state
    if execution_success:
        await complete_order(order_id, actor_id, actor_type.value, execution_result)
        final_status = 'completed'
    else:
        await fail_order(order_id, actor_id, actor_type.value, execution_result)
        final_status = 'failed'
    
    # Emit approval event
    event_type = EventType.ORDER_APPROVED
    if order_type in ['wallet_topup', 'wallet_load']:
        event_type = EventType.WALLET_TOPUP_APPROVED
    elif order_type in ['withdrawal', 'withdrawal_wallet']:
        event_type = EventType.WITHDRAW_APPROVED
    
    await emit_event(
        event_type=event_type,
        title=f"Order {final_status.title()}",
        message=f"Order for @{user.get('username')} {final_status} by {actor_type.value}",
        reference_id=order_id,
        reference_type="order",
        user_id=user['user_id'],
        username=user.get('username'),
        display_name=user.get('display_name'),
        amount=amount,
        extra_data={
            "order_type": order_type,
            "approved_by": actor_id,
            "actor_type": actor_type.value,
            "amount_adjusted": amount_adjusted,
            "original_amount": order['amount'] if amount_adjusted else None,
            "final_status": final_status,
            "execution_result": execution_result
        },
        requires_action=False
    )
    
    if not execution_success:
        return ApprovalResult(
            False,
            f"Order approved but execution failed: {execution_result}",
            {
                "order_id": order_id,
                "status": final_status,
                "error": execution_result
            }
        )
    
    return ApprovalResult(
        True, 
        f"Order approved and executed successfully ({final_status})",
        {
            "order_id": order_id,
            "amount": amount,
            "amount_adjusted": amount_adjusted,
            "order_type": order_type,
            "final_status": final_status,
            "execution_result": execution_result
        }
    )


async def _process_rejection(
    order: Dict,
    user: Dict,
    actor_type: ActorType,
    actor_id: str,
    rejection_reason: Optional[str]
) -> ApprovalResult:
    """
    Process order rejection using order lifecycle.
    """
    order_id = order['order_id']
    order_type = order.get('order_type', 'deposit')
    reason = rejection_reason or "Rejected by reviewer"
    
    # Use lifecycle rejection
    reject_result = await lifecycle_reject(
        order_id=order_id,
        actor_id=actor_id,
        actor_type=actor_type.value,
        reason=reason
    )
    
    if not reject_result.success:
        if reject_result.is_noop:
            return ApprovalResult(True, "Order already rejected", {"already_processed": True})
        return ApprovalResult(False, reject_result.message, {"error_code": reject_result.error_code})
    
    # Update rejection reason in order
    await execute("""
        UPDATE orders SET rejection_reason = $1 WHERE order_id = $2
    """, reason, order_id)
    
    # Emit rejection event
    event_type = EventType.ORDER_REJECTED
    if order_type in ['wallet_topup', 'wallet_load']:
        event_type = EventType.WALLET_TOPUP_REJECTED
    elif order_type in ['withdrawal', 'withdrawal_wallet']:
        event_type = EventType.WITHDRAW_REJECTED
    
    await emit_event(
        event_type=event_type,
        title="Order Rejected",
        message=f"Order for @{user.get('username')} rejected. Reason: {reason}",
        reference_id=order_id,
        reference_type="order",
        user_id=user['user_id'],
        username=user.get('username'),
        display_name=user.get('display_name'),
        amount=order['amount'],
        extra_data={
            "order_type": order_type,
            "rejected_by": actor_id,
            "actor_type": actor_type.value,
            "reason": reason,
            "final_status": "rejected"
        },
        requires_action=False
    )
    
    return ApprovalResult(
        True,
        "Order rejected",
        {
            "order_id": order_id,
            "reason": reason,
            "order_type": order_type,
            "final_status": "rejected"
        }
    )


# ==================== WALLET LOAD SPECIFIC ====================

async def approve_or_reject_wallet_load(
    request_id: str,
    action: Literal["approve", "reject"],
    actor_type: ActorType,
    actor_id: str,
    final_amount: Optional[float] = None,
    rejection_reason: Optional[str] = None,
    bot_id: Optional[str] = None
) -> ApprovalResult:
    """
    Approval function for wallet load requests (from wallet_load_requests table).
    Similar to order approval but for the separate wallet load system.
    """
    logger.info(f"Processing wallet load {action} for {request_id} by {actor_type}:{actor_id}")
    
    # Validate bot permissions if actor is Telegram bot
    if actor_type == ActorType.TELEGRAM_BOT and bot_id:
        bot = await fetch_one("SELECT * FROM telegram_bots WHERE bot_id = $1", bot_id)
        if not bot:
            return ApprovalResult(False, "Bot not found")
        if not bot.get('is_active'):
            return ApprovalResult(False, "Bot is not active")
        if not bot.get('can_approve_wallet_loads', False):
            return ApprovalResult(False, "Bot does not have wallet load approval permissions")
    
    # Get the request
    load_request = await fetch_one("""
        SELECT wlr.*, u.username, u.display_name, u.real_balance
        FROM wallet_load_requests wlr
        JOIN users u ON wlr.user_id = u.user_id
        WHERE wlr.request_id = $1
    """, request_id)
    
    if not load_request:
        return ApprovalResult(False, "Request not found")
    
    # Idempotency check - normalize status
    current_status = OrderStatus.normalize(load_request['status'])
    if current_status not in [OrderStatus.PENDING_APPROVAL.value, 'pending']:
        return ApprovalResult(False, f"Request already {load_request['status']}", {"already_processed": True})
    
    now = datetime.now(timezone.utc)
    amount = final_amount if final_amount is not None else load_request['amount']
    amount_adjusted = final_amount is not None and final_amount != load_request['amount']
    
    if action == "approve":
        current_balance = float(load_request.get('real_balance', 0) or 0)
        new_balance = current_balance + amount
        
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("""
                        UPDATE users SET real_balance = $1, updated_at = NOW()
                        WHERE user_id = $2
                    """, new_balance, load_request['user_id'])
                    
                    # CANONICAL STATUS: completed
                    await conn.execute("""
                        UPDATE wallet_load_requests 
                        SET status = $1, 
                            amount = $2,
                            reviewed_by = $3, 
                            reviewed_at = $4, 
                            updated_at = NOW()
                        WHERE request_id = $5
                    """, OrderStatus.COMPLETED.value, amount, actor_id, now, request_id)
                    
                    await conn.execute("""
                        INSERT INTO wallet_ledger 
                        (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                         reference_type, reference_id, description, created_at)
                        VALUES ($1, $2, 'credit', $3, $4, $5, 'wallet_load', $6, $7, NOW())
                    """, str(uuid.uuid4()), load_request['user_id'], amount,
                       current_balance, new_balance, request_id,
                       f"Wallet load via {load_request['payment_method']}")
                    
        except Exception as e:
            logger.error(f"Wallet load {request_id} execution failed: {e}")
            await execute("""
                UPDATE wallet_load_requests 
                SET status = $1, reviewed_by = $2, reviewed_at = $3,
                    rejection_reason = $4, updated_at = NOW()
                WHERE request_id = $5
            """, OrderStatus.FAILED.value, actor_id, now, f"Execution failed: {str(e)}", request_id)
            
            return ApprovalResult(False, f"Wallet load approved but execution failed: {str(e)}", {
                "request_id": request_id,
                "status": "failed",
                "error": str(e)
            })
        
        await emit_event(
            event_type=EventType.WALLET_LOAD_APPROVED,
            title="Wallet Load Approved & Executed",
            message=f"₱{amount:,.2f} credited to @{load_request.get('username')}",
            reference_id=request_id,
            reference_type="wallet_load",
            user_id=load_request['user_id'],
            username=load_request.get('username'),
            display_name=load_request.get('display_name'),
            amount=amount,
            extra_data={
                "new_balance": new_balance,
                "approved_by": actor_id,
                "actor_type": actor_type.value,
                "amount_adjusted": amount_adjusted,
                "final_status": "completed"
            },
            requires_action=False
        )
        
        return ApprovalResult(True, "Wallet load approved and executed (completed)", {
            "request_id": request_id,
            "amount": amount,
            "new_balance": new_balance,
            "amount_adjusted": amount_adjusted,
            "final_status": "completed"
        })
    
    else:  # reject
        reason = rejection_reason or "Rejected by reviewer"
        
        await execute("""
            UPDATE wallet_load_requests 
            SET status = $1, rejection_reason = $2,
                reviewed_by = $3, reviewed_at = $4, updated_at = NOW()
            WHERE request_id = $5
        """, OrderStatus.REJECTED.value, reason, actor_id, now, request_id)
        
        await emit_event(
            event_type=EventType.WALLET_LOAD_REJECTED,
            title="Wallet Load Rejected",
            message=f"Request from @{load_request.get('username')} rejected. Reason: {reason}",
            reference_id=request_id,
            reference_type="wallet_load",
            user_id=load_request['user_id'],
            username=load_request.get('username'),
            display_name=load_request.get('display_name'),
            amount=load_request['amount'],
            extra_data={
                "rejected_by": actor_id,
                "actor_type": actor_type.value,
                "reason": reason,
                "final_status": "rejected"
            },
            requires_action=False
        )
        
        return ApprovalResult(True, "Wallet load rejected", {
            "request_id": request_id,
            "reason": reason,
            "final_status": "rejected"
        })
