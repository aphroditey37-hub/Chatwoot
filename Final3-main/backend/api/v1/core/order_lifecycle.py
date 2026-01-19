"""
Order Lifecycle State Machine - SINGLE SOURCE OF TRUTH
=====================================================

This module defines and enforces the canonical order state machine.
ALL order status changes MUST go through this module.

No endpoint should directly update orders.status without using these functions.

State Machine:
--------------
                              ┌─────────────────────────┐
                              │                         │
    ┌───────────────┐   ┌─────▼─────┐   ┌────────────┐ │ ┌──────────┐
    │   CREATED     │──▶│ PENDING   │──▶│ PROCESSING │─┼▶│COMPLETED │
    │  (transient)  │   │ APPROVAL  │   │            │ │ └──────────┘
    └───────────────┘   └─────┬─────┘   └─────┬──────┘ │
                              │               │        │ ┌──────────┐
                              │               └────────┼▶│  FAILED  │
                              │                        │ └──────────┘
                              │                        │
                              │               ┌────────┴──────────┐
                              └──────────────▶│     REJECTED      │
                                              └───────────────────┘

Order Types & Flow Contracts:
-----------------------------
A) REQUIRES TELEGRAM APPROVAL:
   - wallet_load: pending_approval → approved → processing → completed
   - withdrawal_wallet: pending_approval → approved → processing → completed/failed  
   - withdrawal_game: pending_approval → approved → processing → completed/failed
   - deposit (legacy): pending_approval → approved → processing → completed

B) DIRECT EXECUTION (NO APPROVAL):
   - game_load: processing → completed/failed
   
Terminal States: completed, failed, rejected, cancelled
"""
import logging
import uuid
import json
from enum import Enum
from typing import Optional, Dict, Any, Tuple, Set, Literal
from datetime import datetime, timezone
from dataclasses import dataclass
from decimal import Decimal

from .database import fetch_one, execute, get_pool
from .structured_logging import get_correlation_id

logger = logging.getLogger(__name__)


# ==================== CANONICAL ORDER STATUS ====================

class OrderStatus(str, Enum):
    """
    Canonical order status values.
    ALL code must use these constants - no string literals.
    """
    # Initial states
    PENDING_APPROVAL = "pending_approval"  # Waiting for admin/telegram approval
    
    # Intermediate states
    APPROVED = "approved"                   # Approved, awaiting processing
    PROCESSING = "processing"               # Currently being processed (side effects in progress)
    
    # Terminal states (immutable)
    COMPLETED = "completed"                 # Successfully finished
    FAILED = "failed"                       # Failed after processing attempt
    REJECTED = "rejected"                   # Rejected by admin/reviewer
    CANCELLED = "cancelled"                 # Cancelled by user
    
    @classmethod
    def terminal_states(cls) -> Set[str]:
        """States that cannot be changed"""
        return {cls.COMPLETED.value, cls.FAILED.value, cls.REJECTED.value, cls.CANCELLED.value}
    
    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if a status is terminal"""
        return status in cls.terminal_states()
    
    @classmethod
    def pending_variants(cls) -> Set[str]:
        """All variants that mean 'pending' (includes legacy)"""
        return {
            cls.PENDING_APPROVAL.value,
            "pending_review", "PENDING_REVIEW",
            "pending", "initiated",
            "awaiting_payment_proof"
        }
    
    @classmethod
    def approved_variants(cls) -> Set[str]:
        """All variants that mean 'approved' (includes legacy)"""
        return {
            cls.APPROVED.value,
            "APPROVED_EXECUTED", "confirmed"
        }
    
    @classmethod
    def normalize(cls, status: str) -> str:
        """Normalize legacy status to canonical form"""
        if status in cls.pending_variants():
            return cls.PENDING_APPROVAL.value
        if status in cls.approved_variants():
            return cls.APPROVED.value
        # Return as-is if already canonical or unknown
        return status


# ==================== CANONICAL ORDER TYPES ====================

class OrderType(str, Enum):
    """
    Canonical order types.
    Each type has specific flow requirements.
    """
    WALLET_LOAD = "wallet_load"              # Payment IN - Add to wallet (requires approval)
    GAME_LOAD = "game_load"                  # Load game from wallet (direct execution)
    WITHDRAWAL_WALLET = "withdrawal_wallet"  # Withdraw from wallet (requires approval)
    WITHDRAWAL_GAME = "withdrawal_game"      # Withdraw from game (requires approval)
    DEPOSIT = "deposit"                      # Legacy deposit (requires approval)
    ADMIN_MANUAL_LOAD = "admin_manual_load"  # Admin manual load (requires approval)
    ADMIN_MANUAL_WITHDRAW = "admin_manual_withdraw"  # Admin manual withdraw (requires approval)


# ==================== FLOW CONTRACTS ====================

# Order types that require Telegram/admin approval before processing
APPROVAL_REQUIRED_TYPES: Set[str] = {
    OrderType.WALLET_LOAD.value,
    OrderType.WITHDRAWAL_WALLET.value,
    OrderType.WITHDRAWAL_GAME.value,
    OrderType.DEPOSIT.value,
    OrderType.ADMIN_MANUAL_LOAD.value,
    OrderType.ADMIN_MANUAL_WITHDRAW.value,
}

# Order types that execute directly (no approval flow)
DIRECT_EXECUTION_TYPES: Set[str] = {
    OrderType.GAME_LOAD.value,
}


def requires_approval(order_type: str) -> bool:
    """Check if an order type requires Telegram/admin approval"""
    return order_type in APPROVAL_REQUIRED_TYPES


def is_direct_execution(order_type: str) -> bool:
    """Check if an order type executes directly without approval"""
    return order_type in DIRECT_EXECUTION_TYPES


# ==================== STATE MACHINE DEFINITION ====================

# Allowed transitions: from_status -> set of valid to_statuses
# CRITICAL: pending_approval can ONLY transition to approved/rejected/cancelled
# NOT directly to processing (approval bypass protection)
ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    # From pending_approval - MUST go through approval first
    OrderStatus.PENDING_APPROVAL.value: {
        OrderStatus.APPROVED.value,      # Approved by admin/telegram
        OrderStatus.REJECTED.value,      # Rejected by admin/telegram
        OrderStatus.CANCELLED.value,     # Cancelled by user
        # NOTE: NO processing here - prevents approval bypass
    },
    
    # From approved - can start processing
    OrderStatus.APPROVED.value: {
        OrderStatus.PROCESSING.value,    # Start processing (the ONLY way to processing for approval-required)
    },
    
    # From processing - can complete or fail
    OrderStatus.PROCESSING.value: {
        OrderStatus.COMPLETED.value,     # Successfully processed
        OrderStatus.FAILED.value,        # Processing failed
    },
    
    # Terminal states - no outgoing transitions
    OrderStatus.COMPLETED.value: set(),
    OrderStatus.FAILED.value: set(),
    OrderStatus.REJECTED.value: set(),
    OrderStatus.CANCELLED.value: set(),
}

# Legacy status transitions (normalized to canonical form)
LEGACY_TRANSITIONS: Dict[str, Set[str]] = {
    "pending_review": ALLOWED_TRANSITIONS[OrderStatus.PENDING_APPROVAL.value],
    "PENDING_REVIEW": ALLOWED_TRANSITIONS[OrderStatus.PENDING_APPROVAL.value],
    "pending": ALLOWED_TRANSITIONS[OrderStatus.PENDING_APPROVAL.value],
    "initiated": ALLOWED_TRANSITIONS[OrderStatus.PENDING_APPROVAL.value],
    "awaiting_payment_proof": ALLOWED_TRANSITIONS[OrderStatus.PENDING_APPROVAL.value],
    "APPROVED_EXECUTED": ALLOWED_TRANSITIONS[OrderStatus.APPROVED.value],
    "confirmed": ALLOWED_TRANSITIONS[OrderStatus.APPROVED.value],
    "approved": ALLOWED_TRANSITIONS[OrderStatus.APPROVED.value],  # Map approved to its transitions
}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    """Check if a status transition is valid according to the state machine"""
    # Normalize legacy statuses
    normalized_from = OrderStatus.normalize(from_status)
    
    # Check main transitions
    allowed = ALLOWED_TRANSITIONS.get(normalized_from, set())
    if to_status in allowed:
        return True
    
    # Check legacy transitions
    allowed_legacy = LEGACY_TRANSITIONS.get(from_status, set())
    return to_status in allowed_legacy


def get_allowed_transitions(from_status: str) -> Set[str]:
    """Get the set of valid target statuses from a given status"""
    normalized = OrderStatus.normalize(from_status)
    base = ALLOWED_TRANSITIONS.get(normalized, set())
    legacy = LEGACY_TRANSITIONS.get(from_status, set())
    return base | legacy


# ==================== ERROR CODES ====================

class OrderErrorCode(str, Enum):
    """Order-related error codes (E3xxx)"""
    INVALID_TRANSITION = "E3001"
    ALREADY_PROCESSED = "E3002"
    ORDER_NOT_FOUND = "E3003"
    CONCURRENT_MODIFICATION = "E3004"
    INVALID_ORDER_TYPE = "E3005"
    APPROVAL_REQUIRED = "E3006"
    NOT_APPROVABLE = "E3007"
    DUPLICATE_ORDER = "E3008"
    INSUFFICIENT_BALANCE = "E3009"
    PROCESSING_ERROR = "E3010"


# ==================== TRANSITION RESULT ====================

@dataclass
class TransitionResult:
    """Result of a state transition attempt"""
    success: bool
    order_id: str
    from_status: str
    to_status: str
    message: str
    error_code: Optional[str] = None
    is_noop: bool = False  # True if already in target state
    audit_log_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "order_id": self.order_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "message": self.message,
            "error_code": self.error_code,
            "is_noop": self.is_noop,
        }


# ==================== UNIFIED AUDIT LOGGING ====================
# CANONICAL TABLE: audit_logs (used by UI timelines and portal)
# This is the SINGLE SOURCE OF TRUTH for all order auditing.

def _safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float.
    Handles None, Decimal, str, and other types.
    """
    if value is None:
        return default
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return default


async def write_order_audit(
    conn,
    order_id: str,
    user_id: str,
    username: str,
    action: str,
    from_status: Optional[str],
    to_status: str,
    actor_id: str,
    actor_type: str,
    amount: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None
) -> str:
    """
    Write to the CANONICAL audit_logs table.
    
    This is the SINGLE SOURCE OF TRUTH for order auditing.
    All transitions and creations MUST use this function.
    
    Returns:
        audit_log_id
    """
    audit_log_id = str(uuid.uuid4())
    correlation_id = get_correlation_id()
    now = datetime.now(timezone.utc)
    
    # Build detailed audit record
    audit_details = {
        "order_id": order_id,
        "from_status": from_status,
        "to_status": to_status,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "correlation_id": correlation_id,
    }
    if amount is not None:
        audit_details["amount"] = _safe_float(amount)
    if details:
        audit_details.update(details)
    
    # Write to canonical audit_logs table
    await conn.execute("""
        INSERT INTO audit_logs (
            log_id, user_id, username, action, 
            resource_type, resource_id, details, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """, audit_log_id, user_id, username, action,
         "order", order_id, json.dumps(audit_details), now)
    
    logger.debug(f"Audit log written: {action} for order {order_id}")
    
    return audit_log_id


# ==================== CORE TRANSITION FUNCTION ====================

async def transition_order(
    order_id: str,
    to_status: str,
    actor_id: str,
    actor_type: Literal["admin", "telegram_bot", "system", "user"] = "system",
    reason: Optional[str] = None,
    metadata_patch: Optional[Dict[str, Any]] = None,
    expected_from_status: Optional[str] = None,
    conn=None
) -> TransitionResult:
    """
    THE ONLY WAY TO CHANGE ORDER STATUS.
    
    This function:
    1. Acquires a row lock (SELECT FOR UPDATE)
    2. Validates current status matches expected (if provided)
    3. Validates the transition is allowed by state machine
    4. Updates the order status atomically
    5. Creates an audit log entry
    6. Returns detailed result
    
    Args:
        order_id: The order to transition
        to_status: Target status
        actor_id: Who is making this change
        actor_type: Type of actor (admin/telegram_bot/system/user)
        reason: Optional reason for the transition
        metadata_patch: Optional metadata to merge into order
        expected_from_status: If provided, fail if current status doesn't match
        conn: Optional database connection (for transaction reuse)
    
    Returns:
        TransitionResult with success status and details
        
    Idempotency:
        - If already in to_status, returns success with is_noop=True
        - If in different terminal state, returns failure with 409 conflict
    """
    correlation_id = get_correlation_id()
    
    # Use provided connection or get new one
    pool = await get_pool()
    should_close = conn is None
    
    if conn is None:
        conn = await pool.acquire()
    
    try:
        # Start transaction
        async with conn.transaction():
            # Lock the order row - INCLUDE amount for audit logging!
            order = await conn.fetchrow("""
                SELECT order_id, status, order_type, user_id, username, metadata, amount
                FROM orders 
                WHERE order_id = $1 
                FOR UPDATE
            """, order_id)
            
            if not order:
                return TransitionResult(
                    success=False,
                    order_id=order_id,
                    from_status="",
                    to_status=to_status,
                    message="Order not found",
                    error_code=OrderErrorCode.ORDER_NOT_FOUND.value
                )
            
            current_status = order['status']
            
            # IDEMPOTENCY: Already in target status = no-op success
            if current_status == to_status:
                logger.info(f"Order {order_id} already in status {to_status} (no-op)")
                return TransitionResult(
                    success=True,
                    order_id=order_id,
                    from_status=current_status,
                    to_status=to_status,
                    message=f"Order already in '{to_status}' status",
                    is_noop=True
                )
            
            # Check expected status if provided
            if expected_from_status is not None:
                normalized_current = OrderStatus.normalize(current_status)
                normalized_expected = OrderStatus.normalize(expected_from_status)
                
                if normalized_current != normalized_expected:
                    return TransitionResult(
                        success=False,
                        order_id=order_id,
                        from_status=current_status,
                        to_status=to_status,
                        message=f"Order status mismatch: expected '{expected_from_status}', found '{current_status}'",
                        error_code=OrderErrorCode.CONCURRENT_MODIFICATION.value
                    )
            
            # TERMINAL STATE CHECK: Cannot transition out of terminal states
            if OrderStatus.is_terminal(current_status):
                return TransitionResult(
                    success=False,
                    order_id=order_id,
                    from_status=current_status,
                    to_status=to_status,
                    message=f"Cannot transition from terminal state '{current_status}'",
                    error_code=OrderErrorCode.ALREADY_PROCESSED.value
                )
            
            # VALIDATE TRANSITION
            if not is_valid_transition(current_status, to_status):
                allowed = get_allowed_transitions(current_status)
                return TransitionResult(
                    success=False,
                    order_id=order_id,
                    from_status=current_status,
                    to_status=to_status,
                    message=f"Invalid transition: '{current_status}' -> '{to_status}'. Allowed: {allowed}",
                    error_code=OrderErrorCode.INVALID_TRANSITION.value
                )
            
            # Prepare metadata update
            existing_metadata = order['metadata']
            if isinstance(existing_metadata, str):
                existing_metadata = json.loads(existing_metadata)
            existing_metadata = existing_metadata or {}
            
            if metadata_patch:
                existing_metadata.update(metadata_patch)
            
            # Add transition metadata
            existing_metadata['last_transition'] = {
                'from': current_status,
                'to': to_status,
                'actor_id': actor_id,
                'actor_type': actor_type,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'correlation_id': correlation_id
            }
            
            # Update order status
            now = datetime.now(timezone.utc)
            await conn.execute("""
                UPDATE orders 
                SET status = $1, 
                    metadata = $2,
                    updated_at = $3
                WHERE order_id = $4
            """, to_status, json.dumps(existing_metadata), now, order_id)
            
            # Get amount safely for audit logging
            order_amount = _safe_float(order.get('amount'))
            
            # Write to CANONICAL audit_logs table (SINGLE SOURCE OF TRUTH)
            audit_log_id = await write_order_audit(
                conn=conn,
                order_id=order_id,
                user_id=order['user_id'],
                username=order['username'],
                action=f"order.transition.{to_status}",
                from_status=current_status,
                to_status=to_status,
                actor_id=actor_id,
                actor_type=actor_type,
                amount=order_amount,
                details={"reason": reason}
            )
            
            logger.info(
                f"Order {order_id} transitioned: {current_status} -> {to_status} "
                f"by {actor_type}:{actor_id} (reason: {reason})"
            )
            
            return TransitionResult(
                success=True,
                order_id=order_id,
                from_status=current_status,
                to_status=to_status,
                message=f"Successfully transitioned to '{to_status}'",
                audit_log_id=audit_log_id
            )
            
    finally:
        if should_close:
            await pool.release(conn)


# ==================== ORDER CREATION ====================

async def create_order(
    user_id: str,
    username: str,
    order_type: str,
    amount: float,
    idempotency_key: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    game_name: Optional[str] = None,
    game_display_name: Optional[str] = None,
    bonus_amount: float = 0.0,
    referral_code: Optional[str] = None,
    payment_method: Optional[str] = None,
    conn=None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Canonical order creation with correct initial status.
    
    This function:
    1. Checks idempotency (returns existing order if key matches)
    2. Sets correct initial status based on order_type:
       - Approval-required types: pending_approval
       - Direct execution types: processing
    3. Creates audit log entry
    4. Returns the created order
    
    Args:
        user_id: User creating the order
        username: Username
        order_type: Type of order (from OrderType enum)
        amount: Order amount
        idempotency_key: Optional key to prevent duplicates
        metadata: Optional additional metadata
        game_name: Game identifier (for game-related orders)
        game_display_name: Display name of game
        bonus_amount: Any bonus amount
        referral_code: Optional referral code
        payment_method: Payment method used
        conn: Optional database connection
        
    Returns:
        Tuple of (success, order_data or error_data)
    """
    correlation_id = get_correlation_id()
    pool = await get_pool()
    should_close = conn is None
    
    if conn is None:
        conn = await pool.acquire()
    
    try:
        # IDEMPOTENCY CHECK
        if idempotency_key:
            existing = await conn.fetchrow("""
                SELECT * FROM orders WHERE idempotency_key = $1
            """, idempotency_key)
            
            if existing:
                logger.info(f"Duplicate order detected (idempotency_key={idempotency_key})")
                return True, {
                    "order_id": existing['order_id'],
                    "status": existing['status'],
                    "duplicate": True,
                    "message": "Order already exists (idempotent)"
                }
        
        # DETERMINE INITIAL STATUS
        if requires_approval(order_type):
            initial_status = OrderStatus.PENDING_APPROVAL.value
        else:
            initial_status = OrderStatus.PROCESSING.value
        
        # CREATE ORDER
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        total_amount = amount + bonus_amount
        
        # Build metadata
        order_metadata = metadata or {}
        order_metadata['correlation_id'] = correlation_id
        order_metadata['created_via'] = 'order_lifecycle'
        if payment_method:
            order_metadata['payment_method'] = payment_method
        
        async with conn.transaction():
            await conn.execute("""
                INSERT INTO orders (
                    order_id, user_id, username, order_type,
                    game_name, game_display_name,
                    amount, bonus_amount, total_amount,
                    referral_code, status, idempotency_key, metadata,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $14)
            """, order_id, user_id, username, order_type,
                 game_name, game_display_name,
                 amount, bonus_amount, total_amount,
                 referral_code.upper() if referral_code else None,
                 initial_status, idempotency_key, json.dumps(order_metadata), now)
            
            # Write to CANONICAL audit_logs table (SINGLE SOURCE OF TRUTH)
            await write_order_audit(
                conn=conn,
                order_id=order_id,
                user_id=user_id,
                username=username,
                action="order.created",
                from_status=None,
                to_status=initial_status,
                actor_id=user_id,
                actor_type="user",
                amount=amount,
                details={
                    "order_type": order_type,
                    "game_name": game_name,
                    "bonus_amount": bonus_amount,
                    "total_amount": total_amount,
                    "idempotency_key": idempotency_key
                }
            )
        
        logger.info(
            f"Order {order_id} created: type={order_type}, status={initial_status}, "
            f"amount={amount}, user={username}"
        )
        
        return True, {
            "order_id": order_id,
            "user_id": user_id,
            "username": username,
            "order_type": order_type,
            "game_name": game_name,
            "game_display_name": game_display_name,
            "amount": amount,
            "bonus_amount": bonus_amount,
            "total_amount": total_amount,
            "referral_code": referral_code,
            "status": initial_status,
            "idempotency_key": idempotency_key,
            "created_at": now.isoformat(),
            "duplicate": False
        }
        
    except Exception as e:
        # Handle duplicate key constraint violation
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            if idempotency_key:
                existing = await conn.fetchrow(
                    "SELECT * FROM orders WHERE idempotency_key = $1",
                    idempotency_key
                )
                if existing:
                    return True, {
                        "order_id": existing['order_id'],
                        "status": existing['status'],
                        "duplicate": True,
                        "message": "Order already exists (race condition)"
                    }
        
        logger.error(f"Failed to create order: {e}")
        return False, {
            "message": f"Failed to create order: {str(e)}",
            "error_code": OrderErrorCode.PROCESSING_ERROR.value
        }
    finally:
        if should_close:
            await pool.release(conn)


# ==================== APPROVAL HELPERS ====================

async def approve_order(
    order_id: str,
    actor_id: str,
    actor_type: Literal["admin", "telegram_bot"] = "admin",
    final_amount: Optional[float] = None,
    reason: Optional[str] = None
) -> TransitionResult:
    """
    Approve an order (transition pending_approval -> approved).
    
    Args:
        order_id: The order to approve
        actor_id: Who is approving
        actor_type: admin or telegram_bot
        final_amount: Optional adjusted amount
        reason: Optional approval reason
    """
    # Verify order exists and is approvable
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    
    if not order:
        return TransitionResult(
            success=False,
            order_id=order_id,
            from_status="",
            to_status=OrderStatus.APPROVED.value,
            message="Order not found",
            error_code=OrderErrorCode.ORDER_NOT_FOUND.value
        )
    
    # Check if order type requires approval
    if is_direct_execution(order['order_type']):
        return TransitionResult(
            success=False,
            order_id=order_id,
            from_status=order['status'],
            to_status=OrderStatus.APPROVED.value,
            message=f"Order type '{order['order_type']}' does not require approval",
            error_code=OrderErrorCode.NOT_APPROVABLE.value
        )
    
    # Build metadata patch
    metadata_patch = {
        "approved_by": actor_id,
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    order_amount = _safe_float(order.get('amount'))
    if final_amount is not None and final_amount != order_amount:
        metadata_patch["amount_adjusted"] = True
        metadata_patch["original_amount"] = order_amount
        metadata_patch["adjusted_amount"] = final_amount
        metadata_patch["adjusted_by"] = actor_id
    
    return await transition_order(
        order_id=order_id,
        to_status=OrderStatus.APPROVED.value,
        actor_id=actor_id,
        actor_type=actor_type,
        reason=reason or "Approved",
        metadata_patch=metadata_patch
    )


async def reject_order(
    order_id: str,
    actor_id: str,
    actor_type: Literal["admin", "telegram_bot"] = "admin",
    reason: Optional[str] = None
) -> TransitionResult:
    """
    Reject an order (transition pending_approval -> rejected).
    """
    metadata_patch = {
        "rejected_by": actor_id,
        "rejected_at": datetime.now(timezone.utc).isoformat(),
        "rejection_reason": reason
    }
    
    return await transition_order(
        order_id=order_id,
        to_status=OrderStatus.REJECTED.value,
        actor_id=actor_id,
        actor_type=actor_type,
        reason=reason or "Rejected by reviewer",
        metadata_patch=metadata_patch
    )


async def start_processing(
    order_id: str,
    actor_id: str = "system",
    actor_type: Literal["admin", "telegram_bot", "system"] = "system"
) -> TransitionResult:
    """
    Start processing an order (transition approved -> processing).
    """
    return await transition_order(
        order_id=order_id,
        to_status=OrderStatus.PROCESSING.value,
        actor_id=actor_id,
        actor_type=actor_type,
        reason="Processing started"
    )


async def complete_order(
    order_id: str,
    actor_id: str = "system",
    actor_type: Literal["admin", "telegram_bot", "system"] = "system",
    execution_result: Optional[str] = None
) -> TransitionResult:
    """
    Mark order as completed (transition processing -> completed).
    """
    metadata_patch = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "execution_result": execution_result
    }
    
    return await transition_order(
        order_id=order_id,
        to_status=OrderStatus.COMPLETED.value,
        actor_id=actor_id,
        actor_type=actor_type,
        reason=execution_result or "Completed successfully",
        metadata_patch=metadata_patch
    )


async def fail_order(
    order_id: str,
    actor_id: str = "system",
    actor_type: Literal["admin", "telegram_bot", "system"] = "system",
    error_message: Optional[str] = None
) -> TransitionResult:
    """
    Mark order as failed (transition processing -> failed).
    """
    metadata_patch = {
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error_message": error_message
    }
    
    return await transition_order(
        order_id=order_id,
        to_status=OrderStatus.FAILED.value,
        actor_id=actor_id,
        actor_type=actor_type,
        reason=error_message or "Processing failed",
        metadata_patch=metadata_patch
    )


# ==================== DATABASE MIGRATION ====================

async def ensure_audit_table_exists():
    """
    DEPRECATED: Using canonical audit_logs table instead of order_audit_log.
    
    The audit_logs table already exists and is used by UI timelines.
    This function is kept for backward compatibility but is now a no-op.
    """
    logger.info("Using canonical audit_logs table for order auditing (order_audit_log deprecated)")
    # No action needed - audit_logs table is created in database.py


# ==================== EXPORTS ====================

__all__ = [
    # Enums
    "OrderStatus",
    "OrderType",
    "OrderErrorCode",
    
    # Flow contracts
    "APPROVAL_REQUIRED_TYPES",
    "DIRECT_EXECUTION_TYPES",
    "requires_approval",
    "is_direct_execution",
    
    # State machine
    "ALLOWED_TRANSITIONS",
    "is_valid_transition",
    "get_allowed_transitions",
    
    # Core functions
    "transition_order",
    "create_order",
    "TransitionResult",
    
    # Approval helpers
    "approve_order",
    "reject_order",
    "start_processing",
    "complete_order",
    "fail_order",
    
    # Audit
    "write_order_audit",
    
    # Setup (deprecated - using audit_logs)
    "ensure_audit_table_exists",
]
