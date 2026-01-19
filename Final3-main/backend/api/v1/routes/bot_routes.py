"""
API v1 Bot Routes
Safe read APIs and system bot authentication for Chatwoot integration

PRODUCTION SECURITY:
- Token issuance endpoint disabled in production (returns 410 Gone)
- Requires BOT_API_TOKEN env var in production (>= 32 chars)
- Uses constant-time comparison for token verification
- No fallback secrets in production
"""
from fastapi import APIRouter, Request, HTTPException, status, Header
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import json
import secrets
import hmac
import hashlib
import logging

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import get_api_settings
from .dependencies import check_rate_limiting

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bot", tags=["Bot"])
settings = get_api_settings()


# ==================== MODELS ====================

class BotAuthRequest(BaseModel):
    """Bot authentication request"""
    bot_id: str = Field(..., description="Bot identifier")
    secret: str = Field(..., description="Bot secret key")


class BotOrderCreate(BaseModel):
    """Bot order creation request"""
    user_id: str = Field(..., description="User ID from identity resolution")
    game_name: str
    amount: float = Field(..., gt=0)
    referral_code: Optional[str] = None
    conversation_id: Optional[str] = Field(None, description="Chatwoot conversation ID")
    external_metadata: Optional[dict] = Field(None, description="External system metadata")


class BotPaymentProof(BaseModel):
    """Bot payment proof upload"""
    order_id: str
    image_url: str = Field(..., description="URL to payment proof image")
    conversation_id: Optional[str] = None


# ==================== SECURE TOKEN VERIFICATION ====================

def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


def _get_production_bot_token() -> Optional[str]:
    """
    Get the production bot API token.
    Returns None if not configured.
    """
    return settings.bot_api_token


def _get_internal_api_secret() -> str:
    """
    Get the internal API secret.
    In production, this should be a strong secret.
    """
    return settings.internal_api_secret


async def verify_bot_token(x_bot_token: str) -> bool:
    """
    Verify bot token using secure comparison.
    
    In PRODUCTION:
    - Only accepts BOT_API_TOKEN (static bearer token)
    - No fallback to internal_api_secret
    - Uses constant-time comparison
    
    In DEVELOPMENT:
    - Accepts BOT_API_TOKEN if set
    - Falls back to internal_api_secret for convenience
    - Also checks API keys table
    """
    if not x_bot_token:
        return False
    
    # Production mode: strict token verification
    if settings.is_production:
        prod_token = _get_production_bot_token()
        if not prod_token:
            logger.error("BOT_API_TOKEN not configured in production")
            return False
        return _constant_time_compare(x_bot_token, prod_token)
    
    # Development mode: more flexible verification
    # Check 1: BOT_API_TOKEN (preferred)
    prod_token = _get_production_bot_token()
    if prod_token and _constant_time_compare(x_bot_token, prod_token):
        return True
    
    # Check 2: Internal API secret (dev convenience)
    internal_secret = _get_internal_api_secret()
    if internal_secret and _constant_time_compare(x_bot_token, internal_secret):
        return True
    
    # Check 3: API key from database (for registered bots)
    try:
        key_hash = hashlib.sha256(x_bot_token.encode()).hexdigest()
        key = await fetch_one(
            "SELECT key_id FROM api_keys WHERE key_hash = $1 AND is_active = TRUE",
            key_hash
        )
        if key:
            # Update last used timestamp
            await execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE key_id = $1",
                key['key_id']
            )
            return True
    except Exception as e:
        logger.warning(f"Error checking API key: {e}")
    
    return False


def verify_bot_authorization_header(authorization: str) -> bool:
    """
    Verify bot Authorization header.
    Expects: "Bot <token>"
    
    Uses constant-time comparison to prevent timing attacks.
    """
    if not authorization:
        return False
    
    # Parse "Bot <token>" format
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bot":
        return False
    
    token = parts[1].strip()
    if not token:
        return False
    
    # Production mode: only BOT_API_TOKEN
    if settings.is_production:
        prod_token = _get_production_bot_token()
        if not prod_token:
            logger.error("BOT_API_TOKEN not configured in production")
            return False
        return _constant_time_compare(token, prod_token)
    
    # Development mode: flexible verification
    prod_token = _get_production_bot_token()
    if prod_token and _constant_time_compare(token, prod_token):
        return True
    
    internal_secret = _get_internal_api_secret()
    if internal_secret and _constant_time_compare(token, internal_secret):
        return True
    
    return False


async def require_bot_auth(authorization: str):
    """Require valid bot authentication via Authorization header."""
    if not verify_bot_authorization_header(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid bot credentials", "error_code": "E1001"}
        )


# ==================== BOT ENDPOINTS ====================

@router.get("/payment-methods")
async def get_bot_payment_methods(
    request: Request,
    x_bot_token: str = Header(..., alias="X-Bot-Token")
):
    """
    Get enabled payment methods for Chatwoot bot
    Returns only active payment methods with tags and instructions
    """
    # Verify bot token
    if not await verify_bot_token(x_bot_token):
        raise HTTPException(status_code=401, detail="Invalid bot token")
    
    # Fetch enabled payment methods ordered by priority
    methods = await fetch_all("""
        SELECT method_id, title, tags, instructions, priority
        FROM payment_methods
        WHERE enabled = TRUE
        ORDER BY priority DESC, created_at ASC
    """)
    
    return {
        "payment_methods": [
            {
                "id": m['method_id'],
                "title": m['title'],
                "tags": m['tags'] or [],
                "instructions": m['instructions'] or "",
                "priority": m['priority']
            }
            for m in methods
        ]
    }


# ==================== BOT TOKEN ENDPOINT ====================

@router.post(
    "/auth/token",
    summary="Get bot authentication token",
    description="Exchange bot credentials for a system token. DISABLED in production."
)
async def get_bot_token(data: BotAuthRequest):
    """
    Issue a restricted system token for bots.
    
    PRODUCTION BEHAVIOR:
    - Returns 410 Gone - token issuance is disabled
    - Use BOT_API_TOKEN environment variable instead
    
    DEVELOPMENT BEHAVIOR:
    - Issues token if credentials match internal_api_secret
    """
    # PRODUCTION: Token issuance disabled
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "message": "Bot token issuance is disabled in production. Use BOT_API_TOKEN environment variable.",
                "error_code": "E1010"
            }
        )
    
    # DEVELOPMENT: Allow token issuance for testing
    internal_secret = _get_internal_api_secret()
    
    if not _constant_time_compare(data.secret, internal_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bot credentials"
        )
    
    # Generate a random token for development (not a hash of secret!)
    # This is only for dev convenience - production uses BOT_API_TOKEN
    dev_token = secrets.token_urlsafe(32)
    
    logger.warning(
        "Bot token issued in development mode. "
        "This endpoint is disabled in production - use BOT_API_TOKEN env var."
    )
    
    return {
        "success": True,
        "token": dev_token,
        "token_type": "Bot",
        "warning": "Development mode only. Use BOT_API_TOKEN in production.",
        "permissions": [
            "identity.resolve",
            "orders.validate",
            "orders.create",
            "orders.read",
            "payments.upload_proof",
            "games.read",
            "balance.read"
        ]
    }


# ==================== SAFE READ APIs ====================

@router.get(
    "/games",
    summary="List all games",
    description="Get list of active games with rules (read-only)"
)
async def list_games(request: Request):
    """List all active games - public read API"""
    await check_rate_limiting(request)
    
    games = await fetch_all(
        "SELECT * FROM games WHERE is_active = TRUE ORDER BY display_name"
    )
    
    return {
        "success": True,
        "games": [{
            "game_id": g['game_id'],
            "game_name": g['game_name'],
            "display_name": g['display_name'],
            "description": g.get('description'),
            "min_deposit": g.get('min_deposit_amount', 10.0),
            "max_deposit": g.get('max_deposit_amount', 10000.0),
            "min_withdrawal": g.get('min_withdrawal_amount', 20.0),
            "max_withdrawal": g.get('max_withdrawal_amount', 10000.0),
            "bonus_rules": json.loads(g['bonus_rules']) if isinstance(g.get('bonus_rules'), str) else g.get('bonus_rules', {})
        } for g in games]
    }


@router.get(
    "/orders/{order_id}",
    summary="Get order details",
    description="Get order information by ID (read-only)"
)
async def get_order(
    request: Request,
    order_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Get order details - requires bot auth"""
    await require_bot_auth(authorization)
    await check_rate_limiting(request)
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "success": True,
        "order": {
            "order_id": order['order_id'],
            "user_id": order['user_id'],
            "username": order['username'],
            "order_type": order.get('order_type', 'deposit'),
            "game_name": order['game_name'],
            "game_display_name": order.get('game_display_name'),
            "amount": order['amount'],
            "bonus_amount": order['bonus_amount'],
            "total_amount": order['total_amount'],
            "referral_code": order.get('referral_code'),
            "status": order['status'],
            "payment_proof_url": order.get('payment_proof_url'),
            "rejection_reason": order.get('rejection_reason'),
            "metadata": json.loads(order['metadata']) if order.get('metadata') else None,
            "created_at": order['created_at'].isoformat() if order.get('created_at') else None,
            "updated_at": order['updated_at'].isoformat() if order.get('updated_at') else None
        }
    }


@router.get(
    "/balance/{user_id}",
    summary="Get user balance",
    description="Get user balance by user ID or for specific game"
)
async def get_balance(
    request: Request,
    user_id: str,
    game: Optional[str] = None,
    authorization: str = Header(..., alias="Authorization")
):
    """Get user balance - requires bot auth"""
    await require_bot_auth(authorization)
    await check_rate_limiting(request)
    
    user = await fetch_one(
        "SELECT user_id, username, display_name, real_balance, bonus_balance, deposit_count, total_deposited, total_withdrawn FROM users WHERE user_id = $1",
        user_id
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get recent orders for this user (optionally filtered by game)
    if game:
        orders = await fetch_all(
            "SELECT * FROM orders WHERE user_id = $1 AND game_name = $2 ORDER BY created_at DESC LIMIT 10",
            user_id, game.lower()
        )
    else:
        orders = await fetch_all(
            "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10",
            user_id
        )
    
    return {
        "success": True,
        "user_id": user['user_id'],
        "username": user['username'],
        "display_name": user['display_name'],
        "real_balance": user['real_balance'],
        "bonus_balance": user['bonus_balance'],
        "total_balance": user['real_balance'] + user['bonus_balance'],
        "deposit_count": user['deposit_count'],
        "total_deposited": user['total_deposited'],
        "total_withdrawn": user['total_withdrawn'],
        "recent_orders": [{
            "order_id": o['order_id'],
            "game_name": o['game_name'],
            "amount": o['amount'],
            "status": o['status'],
            "created_at": o['created_at'].isoformat() if o.get('created_at') else None
        } for o in orders]
    }


# ==================== BOT ACTIONS ====================

@router.post(
    "/orders/validate",
    summary="Validate order (bot)",
    description="Validate order parameters and calculate bonus"
)
async def validate_order_bot(
    request: Request,
    data: BotOrderCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Validate order for bot - returns bonus calculation"""
    await require_bot_auth(authorization)
    await check_rate_limiting(request)
    
    # Get user
    user = await fetch_one("SELECT * FROM users WHERE user_id = $1", data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get game
    game = await fetch_one(
        "SELECT * FROM games WHERE game_name = $1 AND is_active = TRUE",
        data.game_name.lower()
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate amount
    min_amount = game.get('min_deposit_amount', 10.0)
    max_amount = game.get('max_deposit_amount', 10000.0)
    
    if data.amount < min_amount:
        return {
            "success": False,
            "valid": False,
            "message": f"Amount below minimum (${min_amount})",
            "min_amount": min_amount,
            "max_amount": max_amount
        }
    
    if data.amount > max_amount:
        return {
            "success": False,
            "valid": False,
            "message": f"Amount above maximum (${max_amount})",
            "min_amount": min_amount,
            "max_amount": max_amount
        }
    
    # Calculate bonus
    bonus_rules = json.loads(game['bonus_rules']) if isinstance(game.get('bonus_rules'), str) else game.get('bonus_rules', {})
    
    # Determine which rule to apply
    is_first_deposit = user.get('deposit_count', 0) == 0
    rule = bonus_rules.get('first_deposit' if is_first_deposit else 'default', {})
    
    percent_bonus = data.amount * (rule.get('percent_bonus', 0) / 100)
    flat_bonus = rule.get('flat_bonus', 0)
    total_bonus = percent_bonus + flat_bonus
    
    # Apply max cap
    max_bonus = rule.get('max_bonus')
    if max_bonus and total_bonus > max_bonus:
        total_bonus = max_bonus
    
    # Check referral bonus
    referral_bonus = 0
    if data.referral_code:
        perk = await fetch_one(
            "SELECT * FROM referral_perks WHERE referral_code = $1 AND is_active = TRUE AND (game_name IS NULL OR game_name = $2)",
            data.referral_code.upper(), data.game_name.lower()
        )
        if perk:
            ref_percent = data.amount * (perk.get('percent_bonus', 0) / 100)
            ref_flat = perk.get('flat_bonus', 0)
            referral_bonus = ref_percent + ref_flat
            if perk.get('max_bonus') and referral_bonus > perk['max_bonus']:
                referral_bonus = perk['max_bonus']
    
    total_bonus += referral_bonus
    
    return {
        "success": True,
        "valid": True,
        "user": {
            "user_id": user['user_id'],
            "username": user['username'],
            "display_name": user['display_name'],
            "is_first_deposit": is_first_deposit
        },
        "game": {
            "game_name": game['game_name'],
            "display_name": game['display_name']
        },
        "amount": data.amount,
        "bonus_calculation": {
            "percent_bonus": percent_bonus,
            "flat_bonus": flat_bonus,
            "referral_bonus": referral_bonus,
            "total_bonus": total_bonus,
            "rule_applied": "first_deposit" if is_first_deposit else "default"
        },
        "total_amount": data.amount + total_bonus
    }


@router.post(
    "/orders/create",
    summary="Create order (bot)",
    description="Create an order on behalf of a user"
)
async def create_order_bot(
    request: Request,
    data: BotOrderCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """
    Create order for bot with conversation metadata and IDEMPOTENCY.
    
    USES ORDER LIFECYCLE STATE MACHINE:
    - Initial status: pending_approval (requires approval flow)
    - Idempotency enforced via canonical create_order function
    """
    await require_bot_auth(authorization)
    await check_rate_limiting(request)
    
    # Import order lifecycle
    from ..core.order_lifecycle import create_order as lifecycle_create_order, OrderType, OrderStatus
    
    # Generate deterministic idempotency key from conversation_id
    idempotency_key = None
    if data.conversation_id:
        key_string = f"{data.user_id}:{data.conversation_id}:{data.game_name}:{data.amount}"
        idempotency_key = hashlib.sha256(key_string.encode()).hexdigest()[:64]
    
    # Validate first
    validation = await validate_order_bot(request, data, authorization)
    if not validation.get('valid'):
        return validation
    
    # Get user
    user = await fetch_one("SELECT * FROM users WHERE user_id = $1", data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build metadata with conversation info
    metadata = data.external_metadata or {}
    if data.conversation_id:
        metadata['chatwoot_conversation_id'] = data.conversation_id
    metadata['created_by'] = 'bot'
    
    # CREATE ORDER VIA CANONICAL FUNCTION
    success, result = await lifecycle_create_order(
        user_id=data.user_id,
        username=user['username'],
        order_type=OrderType.DEPOSIT.value,  # Bot orders are deposit type (require approval)
        amount=data.amount,
        idempotency_key=idempotency_key,
        metadata=metadata,
        game_name=data.game_name.lower(),
        game_display_name=validation['game']['display_name'],
        bonus_amount=validation['bonus_calculation']['total_bonus'],
        referral_code=data.referral_code
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    # Check if duplicate
    if result.get('duplicate'):
        logger.info(f"Duplicate Chatwoot order detected (idempotency_key={idempotency_key})")
        # Fetch full order details
        existing = await fetch_one("SELECT * FROM orders WHERE order_id = $1", result['order_id'])
        return {
            "success": True,
            "message": "Order already exists (idempotent)",
            "order": {
                "order_id": result['order_id'],
                "user_id": existing['user_id'] if existing else data.user_id,
                "username": existing['username'] if existing else user['username'],
                "game_name": existing['game_name'] if existing else data.game_name,
                "amount": existing['amount'] if existing else data.amount,
                "bonus_amount": existing['bonus_amount'] if existing else 0,
                "total_amount": existing['total_amount'] if existing else data.amount,
                "status": result['status'],
                "conversation_id": data.conversation_id,
                "created_at": existing['created_at'].isoformat() if existing and existing.get('created_at') else None
            },
            "duplicate": True
        }
    
    # Log audit
    await log_audit(
        data.user_id, user['username'], "bot.order_created", "order", result['order_id'],
        {"amount": data.amount, "game": data.game_name, "conversation_id": data.conversation_id}
    )
    
    return {
        "success": True,
        "message": "Order created successfully",
        "order": {
            "order_id": result['order_id'],
            "user_id": data.user_id,
            "username": user['username'],
            "game_name": data.game_name,
            "amount": data.amount,
            "bonus_amount": validation['bonus_calculation']['total_bonus'],
            "total_amount": validation['total_amount'],
            "status": result['status'],  # Will be pending_approval
            "conversation_id": data.conversation_id,
            "created_at": result['created_at']
        },
        "requires_approval": True  # Explicit flow contract
    }


@router.post(
    "/orders/{order_id}/payment-proof",
    summary="Upload payment proof (bot)",
    description="Upload payment proof URL for an order"
)
async def upload_payment_proof_bot(
    request: Request,
    order_id: str,
    data: BotPaymentProof,
    authorization: str = Header(..., alias="Authorization")
):
    """
    Upload payment proof from bot.
    
    FLOW: Order remains in pending_approval, waiting for admin/telegram approval.
    Payment proof is stored but doesn't change status - approval still required.
    """
    await require_bot_auth(authorization)
    await check_rate_limiting(request)
    
    from ..core.order_lifecycle import OrderStatus
    
    # Get order
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only allow proof upload for pending orders
    current_status = OrderStatus.normalize(order['status'])
    if current_status not in [OrderStatus.PENDING_APPROVAL.value]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Cannot upload proof for order in '{order['status']}' status",
                "error_code": "E3001",
                "current_status": order['status']
            }
        )
    
    now = datetime.now(timezone.utc)
    
    # Update metadata with conversation ID if provided
    metadata = json.loads(order['metadata']) if order.get('metadata') else {}
    if data.conversation_id:
        metadata['chatwoot_conversation_id'] = data.conversation_id
    metadata['proof_uploaded_by'] = 'bot'
    metadata['proof_uploaded_at'] = now.isoformat()
    
    # Update order with proof (status remains pending_approval - awaiting review)
    await execute('''
        UPDATE orders 
        SET payment_proof_url = $1, 
            payment_proof_uploaded_at = $2,
            metadata = $3,
            updated_at = NOW()
        WHERE order_id = $4
    ''', data.image_url, now, json.dumps(metadata), order_id)
    
    # Log audit
    await log_audit(
        order['user_id'], order['username'], "bot.payment_proof_uploaded", "order", order_id,
        {"image_url": data.image_url[:100], "conversation_id": data.conversation_id}
    )
    
    # Trigger Telegram notification via NotificationRouter (multi-bot system)
    from ..core.notification_router import emit_event, EventType
    
    try:
        await emit_event(
            event_type=EventType.ORDER_CREATED,
            title="New Game Load Order",
            message=f"User: @{order['username']}\nGame: {order.get('game_display_name', order.get('game_name', 'N/A'))}\nAmount: ₱{order['amount']:,.2f}",
            reference_id=order_id,
            reference_type="order",
            user_id=order['user_id'],
            username=order['username'],
            display_name=order.get('display_name'),
            amount=order['amount'],
            extra_data={
                "order_type": order.get('order_type', 'deposit'),
                "game_name": order.get('game_name'),
                "image_url": data.image_url  # Forward to Telegram
            },
            requires_action=True,
            entity_type="order"
        )
        telegram_notified = True
    except Exception as e:
        logger.warning(f"Failed to send Telegram notification: {e}")
        telegram_notified = False
    
    return {
        "success": True,
        "message": "Payment proof uploaded successfully. Awaiting approval.",
        "order_id": order_id,
        "status": OrderStatus.PENDING_APPROVAL.value,
        "telegram_notified": telegram_notified,
        "requires_approval": True
    }


@router.get(
    "/user/{user_id}/orders",
    summary="Get user orders (bot)",
    description="Get all orders for a user"
)
async def get_user_orders_bot(
    request: Request,
    user_id: str,
    status_filter: Optional[str] = None,
    limit: int = 20,
    authorization: str = Header(..., alias="Authorization")
):
    """Get user orders - requires bot auth"""
    await require_bot_auth(authorization)
    await check_rate_limiting(request)
    
    query = "SELECT * FROM orders WHERE user_id = $1"
    params = [user_id]
    
    if status_filter:
        params.append(status_filter)
        query += f" AND status = ${len(params)}"
    
    params.append(limit)
    query += f" ORDER BY created_at DESC LIMIT ${len(params)}"
    
    orders = await fetch_all(query, *params)
    
    return {
        "success": True,
        "user_id": user_id,
        "orders": [{
            "order_id": o['order_id'],
            "order_type": o.get('order_type', 'deposit'),
            "game_name": o['game_name'],
            "amount": o['amount'],
            "bonus_amount": o['bonus_amount'],
            "total_amount": o['total_amount'],
            "status": o['status'],
            "created_at": o['created_at'].isoformat() if o.get('created_at') else None
        } for o in orders]
    }


# ==================== WEBHOOK NOTIFICATION ====================

@router.post(
    "/webhooks/order-status",
    summary="Register order status webhook",
    description="Register a webhook to receive order status updates"
)
async def register_order_webhook(
    request: Request,
    webhook_url: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Register webhook for order status changes"""
    await require_bot_auth(authorization)
    
    # Use webhook signing secret from config (not internal API secret)
    webhook_secret = settings.webhook_signing_secret
    
    # Store webhook URL in system settings
    webhook_id = str(uuid.uuid4())
    
    await execute('''
        INSERT INTO webhooks (webhook_id, user_id, webhook_url, signing_secret, subscribed_events)
        VALUES ($1, 'system-bot', $2, $3, $4)
    ''', webhook_id, webhook_url, webhook_secret, ['order.status_changed', 'order.approved', 'order.rejected'])
    
    return {
        "success": True,
        "webhook_id": webhook_id,
        "webhook_url": webhook_url,
        "events": ["order.status_changed", "order.approved", "order.rejected"]
    }


async def log_audit(user_id, username, action, resource_type, resource_id, details=None):
    """Log an audit event"""
    log_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    ''', log_id, user_id, username, action, resource_type, resource_id,
       json.dumps(details) if details else None)
