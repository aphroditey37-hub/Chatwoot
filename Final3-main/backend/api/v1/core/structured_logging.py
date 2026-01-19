"""
Structured Logging Module
Provides consistent, correlation-aware logging for critical operations.
"""
import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextvars import ContextVar
from functools import wraps

# Context variable for request correlation
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

logger = logging.getLogger(__name__)


class StructuredLogger:
    """
    Structured logger for critical operations.
    Outputs JSON-formatted logs with correlation IDs.
    """
    
    def __init__(self, component: str):
        self.component = component
        self.logger = logging.getLogger(f"structured.{component}")
    
    def _build_log(
        self,
        event: str,
        level: str,
        order_id: Optional[str] = None,
        user_id: Optional[str] = None,
        amount: Optional[float] = None,
        status: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build structured log entry."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "component": self.component,
            "event": event,
            "correlation_id": correlation_id.get() or generate_correlation_id(),
        }
        
        if order_id:
            log_entry["order_id"] = order_id
        if user_id:
            log_entry["user_id"] = user_id
        if amount is not None:
            log_entry["amount"] = amount
        if status:
            log_entry["status"] = status
        if extra:
            log_entry.update(extra)
        
        return log_entry
    
    def info(self, event: str, **kwargs):
        """Log info level structured event."""
        log_entry = self._build_log(event, "INFO", **kwargs)
        self.logger.info(json.dumps(log_entry))
    
    def warning(self, event: str, **kwargs):
        """Log warning level structured event."""
        log_entry = self._build_log(event, "WARNING", **kwargs)
        self.logger.warning(json.dumps(log_entry))
    
    def error(self, event: str, error: Optional[Exception] = None, **kwargs):
        """Log error level structured event."""
        extra = kwargs.pop('extra', {}) or {}
        if error:
            extra['error_type'] = type(error).__name__
            extra['error_message'] = str(error)
        kwargs['extra'] = extra
        log_entry = self._build_log(event, "ERROR", **kwargs)
        self.logger.error(json.dumps(log_entry))


# Pre-configured loggers for different components
order_logger = StructuredLogger("orders")
wallet_logger = StructuredLogger("wallet")
webhook_logger = StructuredLogger("webhooks")
games_api_logger = StructuredLogger("games_api")


# ==================== ORDER TRANSITION LOGGING ====================

def log_order_transition(
    order_id: str,
    user_id: str,
    from_status: str,
    to_status: str,
    order_type: str,
    amount: float,
    triggered_by: str = "system",
    extra: Optional[Dict] = None
):
    """Log order status transition."""
    order_logger.info(
        "order.transition",
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        status=to_status,
        extra={
            "from_status": from_status,
            "to_status": to_status,
            "order_type": order_type,
            "triggered_by": triggered_by,
            **(extra or {})
        }
    )


def log_order_created(
    order_id: str,
    user_id: str,
    order_type: str,
    amount: float,
    extra: Optional[Dict] = None
):
    """Log order creation."""
    order_logger.info(
        "order.created",
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        status="pending_approval",
        extra={
            "order_type": order_type,
            **(extra or {})
        }
    )


# ==================== WALLET LEDGER LOGGING ====================

def log_wallet_mutation(
    ledger_id: str,
    user_id: str,
    transaction_type: str,
    amount: float,
    balance_before: float,
    balance_after: float,
    reference_type: str,
    reference_id: str,
    description: str
):
    """Log wallet balance mutation."""
    wallet_logger.info(
        "wallet.mutation",
        user_id=user_id,
        amount=amount,
        extra={
            "ledger_id": ledger_id,
            "transaction_type": transaction_type,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "description": description
        }
    )


# ==================== WEBHOOK LOGGING ====================

def log_webhook_received(
    webhook_type: str,
    order_id: Optional[str] = None,
    admin_id: Optional[str] = None,
    action: Optional[str] = None,
    extra: Optional[Dict] = None
):
    """Log webhook receipt."""
    webhook_logger.info(
        "webhook.received",
        order_id=order_id,
        extra={
            "webhook_type": webhook_type,
            "admin_id": admin_id,
            "action": action,
            **(extra or {})
        }
    )


def log_webhook_approval(
    order_id: str,
    user_id: str,
    admin_id: str,
    action: str,
    amount: float,
    from_status: str,
    to_status: str
):
    """Log webhook approval action."""
    webhook_logger.info(
        "webhook.approval",
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        status=to_status,
        extra={
            "admin_id": admin_id,
            "action": action,
            "from_status": from_status,
            "to_status": to_status
        }
    )


# ==================== GAMES API LOGGING ====================

def log_games_api_request(
    operation: str,
    game_id: str,
    user_id: str,
    amount: Optional[float] = None,
    correlation_id: Optional[str] = None,
    extra: Optional[Dict] = None
):
    """Log Games API request."""
    games_api_logger.info(
        f"games_api.request.{operation}",
        user_id=user_id,
        amount=amount,
        extra={
            "operation": operation,
            "game_id": game_id,
            "correlation_id": correlation_id,
            **(extra or {})
        }
    )


def log_games_api_response(
    operation: str,
    game_id: str,
    user_id: str,
    success: bool,
    response_time_ms: float,
    correlation_id: Optional[str] = None,
    error: Optional[str] = None,
    extra: Optional[Dict] = None
):
    """Log Games API response."""
    log_func = games_api_logger.info if success else games_api_logger.error
    log_func(
        f"games_api.response.{operation}",
        user_id=user_id,
        extra={
            "operation": operation,
            "game_id": game_id,
            "success": success,
            "response_time_ms": response_time_ms,
            "correlation_id": correlation_id,
            "error": error,
            **(extra or {})
        }
    )


# ==================== CORRELATION CONTEXT ====================

def generate_correlation_id() -> str:
    """
    Generate a collision-safe correlation ID.
    Returns a 22-character base64url-encoded UUID (collision-safe).
    Format: Full UUID without hyphens, then base64url encoded and trimmed.
    """
    import base64
    # Generate full UUID bytes (16 bytes = 128 bits)
    full_uuid = uuid.uuid4()
    # Convert to base64url (22 chars after removing padding)
    encoded = base64.urlsafe_b64encode(full_uuid.bytes).decode('ascii').rstrip('=')
    return encoded  # 22 characters, collision-safe


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set correlation ID for current context."""
    if cid is None:
        cid = generate_correlation_id()
    elif len(cid) < 16:
        # If provided ID is too short, generate a new safe one
        cid = generate_correlation_id()
    correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get current correlation ID."""
    cid = correlation_id.get()
    if not cid or len(cid) < 16:
        return generate_correlation_id()
    return cid
