"""
API v1 Order Service
Handles order validation, creation, and bonus calculations
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List

from ..core.database import fetch_one, fetch_all, execute, execute_returning
from ..core.config import ErrorCodes, DEFAULT_BONUS_RULES
from ..models import BonusCalculation, OrderStatus
from .referral_service import get_best_perk_for_order, increment_perk_usage, validate_referral_code
from .auth_service import log_audit

logger = logging.getLogger(__name__)


async def get_game(game_name: str) -> Optional[Dict[str, Any]]:
    """Get game by name"""
    return await fetch_one(
        "SELECT * FROM games WHERE game_name = $1 AND is_active = TRUE",
        game_name.lower().strip()
    )


async def validate_order(
    user_id: str,
    username: str,
    game_name: str,
    recharge_amount: float,
    referral_code: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate an order without creating it.
    Returns (success, validation_result/error)
    """
    game_name = game_name.lower().strip()
    
    # Get game
    game = await get_game(game_name)
    if not game:
        return False, {
            "valid": False,
            "message": f"Game '{game_name}' not found",
            "error_code": ErrorCodes.GAME_NOT_FOUND
        }
    
    # Validate amount range
    min_amount = game.get('min_deposit_amount', 10.0)
    max_amount = game.get('max_deposit_amount', 10000.0)
    
    if recharge_amount < min_amount:
        return False, {
            "valid": False,
            "message": f"Amount below minimum ({min_amount})",
            "error_code": ErrorCodes.AMOUNT_BELOW_MINIMUM
        }
    
    if recharge_amount > max_amount:
        return False, {
            "valid": False,
            "message": f"Amount above maximum ({max_amount})",
            "error_code": ErrorCodes.AMOUNT_ABOVE_MAXIMUM
        }
    
    # Calculate bonus
    bonus_calc = await calculate_bonus(
        user_id=user_id,
        username=username,
        game=game,
        amount=recharge_amount,
        referral_code=referral_code
    )
    
    total_amount = recharge_amount + bonus_calc['total_bonus']
    
    return True, {
        "valid": True,
        "game_name": game['game_name'],
        "game_display_name": game['display_name'],
        "recharge_amount": recharge_amount,
        "bonus_amount": bonus_calc['total_bonus'],
        "total_amount": total_amount,
        "bonus_calculation": bonus_calc
    }


async def calculate_bonus(
    user_id: str,
    username: str,
    game: Dict[str, Any],
    amount: float,
    referral_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate bonus for an order using the bonus engine.
    Returns BonusCalculation data.
    """
    bonus_rules = game.get('bonus_rules', {})
    if isinstance(bonus_rules, str):
        bonus_rules = json.loads(bonus_rules)
    
    # Get default game bonus rule
    default_rule = bonus_rules.get('default', DEFAULT_BONUS_RULES['default'])
    
    # Check if first recharge (special bonus)
    is_first_recharge = await check_first_recharge(user_id, game['game_name'])
    if is_first_recharge and 'first_recharge' in bonus_rules:
        active_rule = bonus_rules['first_recharge']
        rule_name = "first_recharge"
    else:
        active_rule = default_rule
        rule_name = "default"
    
    # Calculate base game bonus
    percent_bonus = amount * (active_rule.get('percent_bonus', 0) / 100)
    flat_bonus = active_rule.get('flat_bonus', 0)
    game_bonus = percent_bonus + flat_bonus
    
    # Apply game bonus cap
    max_bonus = active_rule.get('max_bonus')
    if max_bonus and game_bonus > max_bonus:
        game_bonus = max_bonus
    
    # Calculate referral bonus
    referral_bonus = 0.0
    referral_perk = None
    
    if referral_code:
        # Validate referral code first
        is_valid, ref_data = await validate_referral_code(referral_code, user_id, username)
        
        if is_valid:
            # Get best perk for this order
            referral_perk = await get_best_perk_for_order(
                referral_code,
                game['game_name'],
                amount
            )
            
            if referral_perk:
                ref_percent = amount * (referral_perk.get('percent_bonus', 0) / 100)
                ref_flat = referral_perk.get('flat_bonus', 0)
                referral_bonus = ref_percent + ref_flat
                
                # Apply referral bonus cap
                ref_max = referral_perk.get('max_bonus')
                if ref_max and referral_bonus > ref_max:
                    referral_bonus = ref_max
    
    total_bonus = game_bonus + referral_bonus
    
    return {
        "base_amount": amount,
        "percent_bonus": percent_bonus,
        "flat_bonus": flat_bonus,
        "referral_bonus": referral_bonus,
        "total_bonus": round(total_bonus, 2),
        "rule_applied": rule_name,
        "rule_details": {
            "game_rule": active_rule,
            "referral_perk": referral_perk,
            "is_first_recharge": is_first_recharge
        }
    }


async def check_first_recharge(user_id: str, game_name: str) -> bool:
    """Check if this is the user's first recharge for this game"""
    existing = await fetch_one('''
        SELECT order_id FROM orders 
        WHERE user_id = $1 AND game_name = $2 AND status IN ('confirmed', 'completed')
        LIMIT 1
    ''', user_id, game_name)
    return existing is None


async def create_order(
    user_id: str,
    username: str,
    game_name: str,
    recharge_amount: float,
    referral_code: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    metadata: Optional[Dict] = None,
    ip_address: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Create a new order.
    Returns (success, order/error)
    """
    # Check idempotency
    if idempotency_key:
        existing = await fetch_one(
            "SELECT * FROM orders WHERE idempotency_key = $1",
            idempotency_key
        )
        if existing:
            # Return existing order
            return True, format_order(existing)
    
    # Validate order first
    is_valid, validation = await validate_order(
        user_id, username, game_name, recharge_amount, referral_code
    )
    
    if not is_valid:
        return False, validation
    
    # Create order
    order_id = str(uuid.uuid4())
    
    await execute('''
        INSERT INTO orders (
            order_id, user_id, username, order_type, game_name, game_display_name,
            amount, bonus_amount, total_amount, referral_code,
            referral_bonus_applied, rule_applied, status, idempotency_key, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
    ''', 
        order_id, user_id, username, 'deposit',
        validation['game_name'], validation['game_display_name'],
        recharge_amount, validation['bonus_amount'], validation['total_amount'],
        referral_code.upper() if referral_code else None,
        referral_code is not None and validation['bonus_calculation']['referral_bonus'] > 0,
        json.dumps(validation['bonus_calculation']['rule_details']),
        OrderStatus.PENDING.value,
        idempotency_key,
        json.dumps(metadata) if metadata else None
    )
    
    # Increment referral perk usage if applicable
    if referral_code and validation['bonus_calculation'].get('rule_details', {}).get('referral_perk'):
        perk = validation['bonus_calculation']['rule_details']['referral_perk']
        if perk.get('perk_id'):
            await increment_perk_usage(perk['perk_id'])
    
    # Log audit
    await log_audit(
        user_id, username, "order.created", "order", order_id,
        {"amount": recharge_amount, "game": game_name, "referral": referral_code},
        ip_address
    )
    
    # Fetch created order
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    
    return True, format_order(order)


def format_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """Format order for response"""
    return {
        "order_id": order['order_id'],
        "username": order['username'],
        "game_name": order['game_name'],
        "game_display_name": order.get('game_display_name'),
        "recharge_amount": order.get('amount', order.get('recharge_amount', 0)),
        "bonus_amount": order['bonus_amount'],
        "total_amount": order['total_amount'],
        "referral_code": order.get('referral_code'),
        "referral_bonus_applied": order.get('referral_bonus_applied', False),
        "rule_applied": order.get('rule_applied'),
        "status": order['status'],
        "created_at": order['created_at'].isoformat() if order.get('created_at') else None,
        "metadata": json.loads(order['metadata']) if order.get('metadata') else None
    }


async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Get order by ID"""
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    return format_order(order) if order else None


async def get_user_orders(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None
) -> Tuple[List[Dict], int]:
    """Get paginated orders for a user"""
    offset = (page - 1) * page_size
    
    # Count query
    count_query = "SELECT COUNT(*) FROM orders WHERE user_id = $1"
    params = [user_id]
    
    if status:
        count_query += " AND status = $2"
        params.append(status)
    
    total = await fetch_one(count_query, *params)
    total_count = total['count'] if total else 0
    
    # Data query
    query = "SELECT * FROM orders WHERE user_id = $1"
    if status:
        query += " AND status = $2"
    query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)
    params.extend([page_size, offset])
    
    orders = await fetch_all(query, *params)
    
    return [format_order(o) for o in orders], total_count


async def update_order_status(order_id: str, new_status: OrderStatus, user_id: str = None) -> bool:
    """
    Update order status - DEPRECATED
    
    This function is DEPRECATED. Use order_lifecycle.transition_order() instead.
    This wrapper delegates to the canonical lifecycle function for backward compatibility.
    
    WARNING: This should not be used for new code.
    """
    from ..core.order_lifecycle import transition_order
    
    logger.warning(
        f"DEPRECATED: update_order_status called for {order_id}. "
        f"Use transition_order() instead."
    )
    
    # Delegate to lifecycle
    result = await transition_order(
        order_id=order_id,
        to_status=new_status.value,
        actor_id=user_id or "system",
        actor_type="system",
        reason="Legacy update_order_status call"
    )
    
    return result.success


async def list_games() -> List[Dict[str, Any]]:
    """List all active games"""
    games = await fetch_all(
        "SELECT * FROM games WHERE is_active = TRUE ORDER BY display_name"
    )
    
    result = []
    for g in games:
        bonus_rules = g.get('bonus_rules', {})
        if isinstance(bonus_rules, str):
            bonus_rules = json.loads(bonus_rules)
        
        result.append({
            "game_id": g['game_id'],
            "game_name": g['game_name'],
            "display_name": g['display_name'],
            "description": g.get('description'),
            "min_recharge_amount": g.get('min_deposit_amount', 10.0),
            "max_recharge_amount": g.get('max_deposit_amount', 10000.0),
            "bonus_rules": bonus_rules,
            "is_active": g['is_active']
        })
    
    return result
