"""
Telegram Approval Security Module
Implements admin whitelist, single-use approvals, expiry, and audit logging.
"""
import os
import logging
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Set
from enum import Enum
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


# ==================== CONFIGURATION ====================

def get_admin_whitelist() -> Set[str]:
    """
    Get whitelisted admin chat IDs from environment.
    Format: TELEGRAM_ADMIN_IDS=123456,789012,345678
    """
    ids_str = os.environ.get('TELEGRAM_ADMIN_IDS', '')
    if not ids_str:
        # Fallback to single TELEGRAM_CHAT_ID if no whitelist configured
        single_id = os.environ.get('TELEGRAM_CHAT_ID', '')
        if single_id:
            return {str(single_id)}
        return set()
    
    return {str(id.strip()) for id in ids_str.split(',') if id.strip()}


def get_approval_expiry_minutes() -> int:
    """Get approval expiry time in minutes from environment."""
    return int(os.environ.get('APPROVAL_EXPIRY_MINUTES', '60'))


# ==================== APPROVAL ACTIONS ====================

class ApprovalAction(str, Enum):
    """Valid approval actions"""
    APPROVE = "approve"
    REJECT = "reject"
    FAILED = "failed"
    SENT = "sent"
    DUPLICATE = "duplicate"
    SUSPICIOUS = "suspicious"
    TAG_CHANGED = "tag_changed"
    EDIT_AMOUNT = "editamt"


# Actions that modify balance
BALANCE_MODIFYING_ACTIONS = {
    ApprovalAction.APPROVE,
    ApprovalAction.SENT,
    ApprovalAction.FAILED,  # May refund
}

# Actions allowed for Payment IN (wallet loads)
PAYMENT_IN_ACTIONS = {
    ApprovalAction.APPROVE,
    ApprovalAction.FAILED,
    ApprovalAction.DUPLICATE,
    ApprovalAction.SUSPICIOUS,
    ApprovalAction.TAG_CHANGED,
    ApprovalAction.EDIT_AMOUNT,
}

# Actions allowed for Payment OUT (withdrawals)
PAYMENT_OUT_ACTIONS = {
    ApprovalAction.SENT,
    ApprovalAction.FAILED,
    ApprovalAction.DUPLICATE,
    ApprovalAction.SUSPICIOUS,
    ApprovalAction.TAG_CHANGED,
}


# ==================== STATE MACHINE ====================

# Valid status transitions
VALID_TRANSITIONS = {
    "pending_approval": {"approved", "rejected", "failed", "cancelled"},
    "pending_review": {"approved", "rejected", "failed", "cancelled"},  # legacy
    "awaiting_payment_proof": {"approved", "rejected", "failed", "cancelled"},  # legacy
    "initiated": {"approved", "rejected", "failed", "cancelled"},  # legacy
    "approved": {"completed", "failed"},
    "completed": set(),  # Terminal state
    "failed": {"approved"},  # Can retry
    "rejected": set(),  # Terminal state
    "cancelled": set(),  # Terminal state
}


def is_valid_transition(current_status: str, new_status: str) -> bool:
    """Check if a status transition is allowed by the state machine."""
    allowed = VALID_TRANSITIONS.get(current_status, set())
    return new_status in allowed


# ==================== SINGLE-USE APPROVAL TOKENS ====================

class ApprovalTokenCache:
    """
    Tracks used approval tokens to prevent button reuse.
    Token format: {order_id}_{action}_{timestamp}
    """
    
    def __init__(self, max_size: int = 50000):
        self.max_size = max_size
        self._used_tokens: OrderedDict[str, float] = OrderedDict()
        self._lock = Lock()
    
    def generate_token(self, order_id: str, action: str) -> str:
        """Generate a unique approval token."""
        timestamp = int(time.time())
        token_str = f"{order_id}:{action}:{timestamp}"
        return hashlib.sha256(token_str.encode()).hexdigest()[:16]
    
    def mark_used(self, order_id: str, action: str) -> bool:
        """
        Mark an approval as used. Returns True if this is first use.
        Returns False if already used (replay attempt).
        """
        token = f"{order_id}:{action}"
        
        with self._lock:
            if token in self._used_tokens:
                logger.warning(f"Approval button reuse detected: order={order_id}, action={action}")
                return False
            
            # Cleanup old entries
            while len(self._used_tokens) >= self.max_size:
                self._used_tokens.popitem(last=False)
            
            self._used_tokens[token] = time.time()
            return True
    
    def is_used(self, order_id: str, action: str) -> bool:
        """Check if approval has already been used."""
        token = f"{order_id}:{action}"
        with self._lock:
            return token in self._used_tokens


# Global instance
approval_token_cache = ApprovalTokenCache()


# ==================== EXPIRY CHECK ====================

def is_approval_expired(created_at: datetime, expiry_minutes: Optional[int] = None) -> Tuple[bool, int]:
    """
    Check if an approval request has expired.
    
    Returns:
        (is_expired, minutes_remaining)
    """
    if expiry_minutes is None:
        expiry_minutes = get_approval_expiry_minutes()
    
    # Handle timezone-naive datetime
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    expiry_time = created_at + timedelta(minutes=expiry_minutes)
    
    if now > expiry_time:
        return True, 0
    
    remaining = int((expiry_time - now).total_seconds() / 60)
    return False, remaining


# ==================== ADMIN VERIFICATION ====================

def verify_admin(chat_id: str) -> Tuple[bool, str]:
    """
    Verify that a chat ID is in the admin whitelist.
    
    Returns:
        (is_valid, error_message)
    """
    whitelist = get_admin_whitelist()
    
    if not whitelist:
        logger.warning("No admin whitelist configured - allowing all (INSECURE)")
        return True, ""
    
    chat_id_str = str(chat_id)
    if chat_id_str not in whitelist:
        logger.warning(f"Unauthorized approval attempt from chat_id={chat_id}")
        return False, f"Unauthorized: Chat ID {chat_id} is not in admin whitelist"
    
    return True, ""


# ==================== COMPREHENSIVE APPROVAL CHECK ====================

async def verify_approval_request(
    order_id: str,
    action: str,
    admin_chat_id: str,
    order_created_at: datetime,
    order_status: str,
    order_type: str
) -> Tuple[bool, str]:
    """
    Comprehensive approval request verification.
    
    Checks:
    1. Admin is whitelisted
    2. Approval hasn't expired
    3. Button hasn't been used (single-use)
    4. Status transition is valid
    5. Action is appropriate for order type
    
    Returns:
        (is_valid, error_message)
    """
    # 1. Verify admin whitelist
    is_admin, error = verify_admin(admin_chat_id)
    if not is_admin:
        return False, error
    
    # 2. Check expiry
    is_expired, minutes_remaining = is_approval_expired(order_created_at)
    if is_expired:
        return False, f"Approval request expired (created {get_approval_expiry_minutes()} minutes ago)"
    
    # 3. Check single-use (button reuse)
    if not approval_token_cache.mark_used(order_id, action):
        return False, f"This approval button has already been used"
    
    # 4. Validate status transition
    target_status = get_target_status(action)
    if target_status and not is_valid_transition(order_status, target_status):
        return False, f"Invalid transition: {order_status} → {target_status}"
    
    # 5. Validate action for order type
    valid, error = validate_action_for_order_type(action, order_type)
    if not valid:
        return False, error
    
    return True, ""


def get_target_status(action: str) -> Optional[str]:
    """Map action to target status."""
    mapping = {
        "approve": "approved",
        "reject": "rejected",
        "failed": "failed",
        "sent": "approved",  # For withdrawals, "sent" means approved
        "duplicate": "rejected",
        "suspicious": "rejected",
        "tag_changed": "rejected",
    }
    return mapping.get(action)


def validate_action_for_order_type(action: str, order_type: str) -> Tuple[bool, str]:
    """Validate that the action is appropriate for the order type."""
    # Normalize action
    action_lower = action.lower()
    
    # Payment IN types
    if order_type in ('wallet_load', 'deposit'):
        if action_lower.startswith('w'):  # withdrawal actions
            return False, f"Action '{action}' not valid for wallet load orders"
    
    # Payment OUT types
    elif order_type in ('withdrawal_wallet', 'withdrawal_game', 'withdrawal'):
        if action_lower == 'approve':
            return False, "Use 'sent' action for withdrawals, not 'approve'"
    
    return True, ""


# ==================== AUDIT LOGGING ====================

async def log_approval_action(
    conn,
    order_id: str,
    action: str,
    admin_chat_id: str,
    admin_username: Optional[str],
    previous_status: str,
    new_status: str,
    amount: float,
    user_id: str,
    extra_data: Optional[dict] = None
) -> str:
    """
    Log approval action to audit_logs table.
    
    Returns:
        log_id
    """
    import uuid
    import json
    
    log_id = str(uuid.uuid4())
    
    details = {
        "order_id": order_id,
        "action": action,
        "admin_chat_id": str(admin_chat_id),
        "admin_username": admin_username,
        "previous_status": previous_status,
        "new_status": new_status,
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    if extra_data:
        details.update(extra_data)
    
    try:
        await conn.execute("""
            INSERT INTO audit_logs 
            (log_id, user_id, username, action, resource_type, resource_id, details, created_at)
            VALUES ($1, $2, $3, $4, 'order', $5, $6, NOW())
        """, log_id, user_id, admin_username or f"admin_{admin_chat_id}",
             f"telegram.{action}", order_id, json.dumps(details))
        
        logger.info(f"Audit log created: {action} on order {order_id[:8]} by {admin_chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
    
    return log_id


# ==================== FLOW RULES ENFORCEMENT ====================

def requires_approval(order_type: str) -> bool:
    """
    Check if an order type requires Telegram approval.
    
    Based on state machine from order_types.py:
    - wallet_load: YES (telegram_approval: True)
    - game_load: NO (instant from wallet)
    - withdrawal_wallet: YES
    - withdrawal_game: YES
    """
    REQUIRES_APPROVAL = {
        'wallet_load': True,
        'deposit': True,  # Legacy
        'withdrawal_wallet': True,
        'withdrawal_game': True,
        'withdrawal': True,  # Legacy
        'game_load': False,  # Instant if balance available
    }
    
    return REQUIRES_APPROVAL.get(order_type, True)  # Default to requiring approval


def get_flow_config(order_type: str) -> dict:
    """Get flow configuration for an order type."""
    from .order_types import FLOWS
    return FLOWS.get(order_type, {
        "telegram_approval": True,
        "description": "Unknown order type"
    })
