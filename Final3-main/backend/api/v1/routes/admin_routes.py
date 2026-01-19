"""
API v1 Admin Routes - Comprehensive Administration
Per-client bonus, signup bonus, rules, orders, Telegram config, audit logs
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import json

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from .dependencies import authenticate_request, require_auth

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== AUTH HELPER ====================

async def require_admin(request: Request, authorization: str):
    """Require admin role for access"""
    auth = await require_auth(request, authorization=authorization)
    
    admin = await fetch_one("SELECT role FROM users WHERE user_id = $1", auth.user_id)
    if not admin or admin.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return auth


# ==================== MODELS ====================

class PerkCreate(BaseModel):
    """Create a new referral perk"""
    referral_code: str = Field(..., min_length=4, max_length=20)
    game_name: Optional[str] = Field(None, description="Specific game or null for all games")
    percent_bonus: float = Field(0.0, ge=0, le=100)
    flat_bonus: float = Field(0.0, ge=0)
    max_bonus: Optional[float] = Field(None, ge=0)
    min_amount: Optional[float] = Field(None, ge=0)
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = Field(None, ge=1)
    is_active: bool = True


class PerkUpdate(BaseModel):
    """Update an existing perk"""
    percent_bonus: Optional[float] = Field(None, ge=0, le=100)
    flat_bonus: Optional[float] = Field(None, ge=0)
    max_bonus: Optional[float] = None
    min_amount: Optional[float] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None
    is_active: Optional[bool] = None


class ClientBonusUpdate(BaseModel):
    """Update client-specific bonus settings"""
    bonus_percentage: Optional[float] = Field(None, ge=0, le=100)
    signup_bonus_claimed: Optional[bool] = None
    deposit_locked: Optional[bool] = None
    withdraw_locked: Optional[bool] = None


class RuleCreate(BaseModel):
    """Create a deposit/withdrawal rule"""
    rule_type: str = Field(..., description="deposit or withdrawal")
    scope: str = Field(default="global", description="global, game, or client")
    scope_id: Optional[str] = None
    priority: int = Field(default=0)
    conditions: dict = Field(default_factory=dict)
    actions: dict = Field(default_factory=dict)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True


# TelegramConfigUpdate REMOVED - use /api/v1/admin/telegram/bots


class SystemSettingsUpdate(BaseModel):
    """Update system settings"""
    api_enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    manual_verification: Optional[bool] = None
    auto_approve_deposits: Optional[bool] = None
    auto_approve_withdrawals: Optional[bool] = None
    referral_system_enabled: Optional[bool] = None
    bonus_system_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None
    default_deposit_bonus: Optional[float] = None
    signup_bonus: Optional[float] = None
    default_referral_bonus: Optional[float] = None
    deposit_block_balance: Optional[float] = Field(None, description="Block deposits if game balance > this amount")
    min_cashout_multiplier: Optional[float] = Field(None, description="Min withdrawal = X × last deposit")
    max_cashout_multiplier: Optional[float] = Field(None, description="Max withdrawal = Y × last deposit")


class GameRulesUpdate(BaseModel):
    """Update game-specific rules"""
    min_deposit_amount: Optional[float] = Field(None, ge=0)
    max_deposit_amount: Optional[float] = Field(None, ge=0)
    min_withdrawal_amount: Optional[float] = Field(None, ge=0)
    max_withdrawal_amount: Optional[float] = Field(None, ge=0)
    deposit_rules: Optional[dict] = None
    withdrawal_rules: Optional[dict] = None
    bonus_rules: Optional[dict] = None
    is_active: Optional[bool] = None


# ==================== STATS & DASHBOARD ====================

@router.get("/stats", summary="Get admin dashboard statistics")
async def get_admin_stats(request: Request, authorization: str = Header(..., alias="Authorization")):
    """Get admin dashboard statistics"""
    auth = await require_admin(request, authorization)
    
    total_users = (await fetch_one("SELECT COUNT(*) as count FROM users"))['count']
    total_orders = (await fetch_one("SELECT COUNT(*) as count FROM orders"))['count']
    total_perks = (await fetch_one("SELECT COUNT(*) as count FROM referral_perks WHERE is_active = TRUE"))['count']
    
    total_volume = await fetch_one(
        "SELECT COALESCE(SUM(amount), 0) as total FROM orders WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED'"
    )
    total_bonus = await fetch_one(
        "SELECT COALESCE(SUM(bonus_amount), 0) as total FROM orders WHERE status = 'APPROVED_EXECUTED'"
    )
    pending_orders = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE status IN ('initiated', 'pending_review', 'awaiting_payment_proof')"
    ))['count']
    
    recent_orders = await fetch_all('''
        SELECT * FROM orders ORDER BY created_at DESC LIMIT 10
    ''')
    
    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "total_active_perks": total_perks,
        "total_volume": total_volume['total'],
        "total_bonus_distributed": total_bonus['total'],
        "recent_orders": [{
            "order_id": o['order_id'],
            "username": o['username'],
            "order_type": o['order_type'],
            "game_name": o.get('game_name'),
            "amount": o['amount'],
            "bonus_amount": o['bonus_amount'],
            "status": o['status'],
            "created_at": o['created_at'].isoformat() if o.get('created_at') else None
        } for o in recent_orders]
    }


# ==================== CLIENT MANAGEMENT ====================

@router.get("/clients", summary="List all clients/users")
async def list_clients(
    request: Request,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(..., alias="Authorization")
):
    """List all clients with their bonus settings"""
    auth = await require_admin(request, authorization)
    
    if search:
        users = await fetch_all('''
            SELECT user_id, username, display_name, email, referral_code, role,
                   bonus_percentage, signup_bonus_claimed, deposit_count,
                   total_deposited, total_withdrawn, real_balance, bonus_balance,
                   deposit_locked, withdraw_locked, is_active, created_at
            FROM users 
            WHERE username ILIKE $1 OR referral_code ILIKE $1 OR display_name ILIKE $1 OR email ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        ''', f'%{search}%', limit, offset)
    else:
        users = await fetch_all('''
            SELECT user_id, username, display_name, email, referral_code, role,
                   bonus_percentage, signup_bonus_claimed, deposit_count,
                   total_deposited, total_withdrawn, real_balance, bonus_balance,
                   deposit_locked, withdraw_locked, is_active, created_at
            FROM users 
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        ''', limit, offset)
    
    return [{
        "user_id": u['user_id'],
        "username": u['username'],
        "display_name": u['display_name'],
        "email": u.get('email'),
        "referral_code": u['referral_code'],
        "role": u.get('role', 'user'),
        "bonus_percentage": u.get('bonus_percentage', 0),
        "signup_bonus_claimed": u.get('signup_bonus_claimed', False),
        "deposit_count": u.get('deposit_count', 0),
        "total_deposited": u.get('total_deposited', 0),
        "total_withdrawn": u.get('total_withdrawn', 0),
        "real_balance": u.get('real_balance', 0),
        "bonus_balance": u.get('bonus_balance', 0),
        "deposit_locked": u.get('deposit_locked', False),
        "withdraw_locked": u.get('withdraw_locked', False),
        "is_active": u['is_active'],
        "created_at": u['created_at'].isoformat() if u.get('created_at') else None
    } for u in users]


@router.get("/clients/{user_id}", summary="Get client details")
async def get_client(
    request: Request,
    user_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Get detailed client information"""
    auth = await require_admin(request, authorization)
    
    user = await fetch_one("SELECT * FROM users WHERE user_id = $1", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get identities
    identities = await fetch_all(
        "SELECT * FROM user_identities WHERE user_id = $1", user_id
    )
    
    # Get recent orders
    orders = await fetch_all(
        "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20", user_id
    )
    
    # Don't return password hash
    user.pop('password_hash', None)
    
    return {
        **user,
        "created_at": user['created_at'].isoformat() if user.get('created_at') else None,
        "identities": [{
            "identity_id": i['identity_id'],
            "provider": i['provider'],
            "external_id": i['external_id'],
            "is_primary": i['is_primary']
        } for i in identities],
        "recent_orders": [{
            "order_id": o['order_id'],
            "order_type": o['order_type'],
            "amount": o['amount'],
            "status": o['status'],
            "created_at": o['created_at'].isoformat() if o.get('created_at') else None
        } for o in orders]
    }


@router.put("/clients/{user_id}/bonus", summary="Update client bonus settings")
async def update_client_bonus(
    request: Request,
    user_id: str,
    data: ClientBonusUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update client-specific bonus and lock settings"""
    auth = await require_admin(request, authorization)
    
    user = await fetch_one("SELECT username FROM users WHERE user_id = $1", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updates = []
    params = []
    
    if data.bonus_percentage is not None:
        params.append(data.bonus_percentage)
        updates.append(f"bonus_percentage = ${len(params)}")
    if data.signup_bonus_claimed is not None:
        params.append(data.signup_bonus_claimed)
        updates.append(f"signup_bonus_claimed = ${len(params)}")
    if data.deposit_locked is not None:
        params.append(data.deposit_locked)
        updates.append(f"deposit_locked = ${len(params)}")
    if data.withdraw_locked is not None:
        params.append(data.withdraw_locked)
        updates.append(f"withdraw_locked = ${len(params)}")
    
    if updates:
        params.append(user_id)
        await execute(
            f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE user_id = ${len(params)}",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "admin.client_bonus_updated", "user", user_id, data.model_dump())
    
    return {"success": True, "message": "Client bonus settings updated"}


# ==================== ORDER MANAGEMENT ====================

@router.get("/orders", summary="List all orders")
async def list_orders(
    request: Request,
    status_filter: Optional[str] = None,
    order_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(..., alias="Authorization")
):
    """List all orders with filters"""
    auth = await require_admin(request, authorization)
    
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    
    if status_filter:
        params.append(status_filter)
        query += f" AND status = ${len(params)}"
    if order_type:
        params.append(order_type)
        query += f" AND order_type = ${len(params)}"
    
    params.extend([limit, offset])
    query += f" ORDER BY created_at DESC LIMIT ${len(params)-1} OFFSET ${len(params)}"
    
    orders = await fetch_all(query, *params)
    
    return [{
        "order_id": o['order_id'],
        "user_id": o['user_id'],
        "username": o['username'],
        "order_type": o['order_type'],
        "game_name": o.get('game_name'),
        "amount": o['amount'],
        "bonus_amount": o['bonus_amount'],
        "total_amount": o['total_amount'],
        "referral_code": o.get('referral_code'),
        "status": o['status'],
        "payment_proof_url": o.get('payment_proof_url'),
        "rejection_reason": o.get('rejection_reason'),
        "created_at": o['created_at'].isoformat() if o.get('created_at') else None
    } for o in orders]


@router.get("/orders/{order_id}", summary="Get order details")
async def get_order_admin(
    request: Request,
    order_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Get detailed order information"""
    auth = await require_admin(request, authorization)
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        **order,
        "created_at": order['created_at'].isoformat() if order.get('created_at') else None,
        "updated_at": order['updated_at'].isoformat() if order.get('updated_at') else None,
        "approved_at": order['approved_at'].isoformat() if order.get('approved_at') else None
    }


# ==================== REFERRAL PERKS ====================

@router.get("/perks", summary="List all referral perks")
async def list_perks(
    request: Request,
    referral_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    authorization: str = Header(..., alias="Authorization")
):
    """List all referral perks"""
    auth = await require_admin(request, authorization)
    
    query = "SELECT * FROM referral_perks WHERE 1=1"
    params = []
    
    if referral_code:
        params.append(referral_code.upper())
        query += f" AND referral_code = ${len(params)}"
    if is_active is not None:
        params.append(is_active)
        query += f" AND is_active = ${len(params)}"
    
    query += " ORDER BY created_at DESC"
    perks = await fetch_all(query, *params) if params else await fetch_all(query)
    
    return [{
        "perk_id": p['perk_id'],
        "referral_code": p['referral_code'],
        "game_name": p.get('game_name'),
        "percent_bonus": p['percent_bonus'],
        "flat_bonus": p['flat_bonus'],
        "max_bonus": p.get('max_bonus'),
        "min_amount": p.get('min_amount'),
        "valid_until": p['valid_until'].isoformat() if p.get('valid_until') else None,
        "max_uses": p.get('max_uses'),
        "current_uses": p.get('current_uses', 0),
        "is_active": p['is_active'],
        "created_at": p['created_at'].isoformat() if p.get('created_at') else None
    } for p in perks]


@router.post("/perks", summary="Create a referral perk")
async def create_perk(
    request: Request,
    data: PerkCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a new referral perk"""
    auth = await require_admin(request, authorization)
    
    # Verify referral code exists
    user = await fetch_one(
        "SELECT user_id FROM users WHERE referral_code = $1",
        data.referral_code.upper()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Referral code not found")
    
    perk_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    await execute('''
        INSERT INTO referral_perks (
            perk_id, referral_code, game_name, percent_bonus, flat_bonus,
            max_bonus, min_amount, valid_from, valid_until, max_uses, is_active, created_by, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    ''', perk_id, data.referral_code.upper(), data.game_name.lower() if data.game_name else None,
        data.percent_bonus, data.flat_bonus, data.max_bonus, data.min_amount,
        now, data.valid_until, data.max_uses, data.is_active, auth.user_id, now)
    
    await log_audit(auth.user_id, auth.username, "admin.perk_created", "perk", perk_id, data.model_dump())
    
    return {"success": True, "perk_id": perk_id, "message": "Perk created"}


@router.put("/perks/{perk_id}", summary="Update a perk")
async def update_perk(
    request: Request,
    perk_id: str,
    data: PerkUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update an existing perk"""
    auth = await require_admin(request, authorization)
    
    perk = await fetch_one("SELECT * FROM referral_perks WHERE perk_id = $1", perk_id)
    if not perk:
        raise HTTPException(status_code=404, detail="Perk not found")
    
    updates = []
    params = []
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            params.append(value)
            updates.append(f"{field} = ${len(params)}")
    
    if updates:
        params.append(perk_id)
        await execute(
            f"UPDATE referral_perks SET {', '.join(updates)} WHERE perk_id = ${len(params)}",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "admin.perk_updated", "perk", perk_id, data.model_dump())
    
    return {"success": True, "message": "Perk updated"}


@router.delete("/perks/{perk_id}", summary="Delete a perk")
async def delete_perk(
    request: Request,
    perk_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete a perk (soft delete)"""
    auth = await require_admin(request, authorization)
    
    await execute("UPDATE referral_perks SET is_active = FALSE WHERE perk_id = $1", perk_id)
    await log_audit(auth.user_id, auth.username, "admin.perk_deleted", "perk", perk_id)
    
    return {"success": True, "message": "Perk deleted"}


# ==================== RULES ENGINE ====================

@router.get("/rules", summary="List all rules")
async def list_rules(
    request: Request,
    rule_type: Optional[str] = None,
    scope: Optional[str] = None,
    authorization: str = Header(..., alias="Authorization")
):
    """List all deposit/withdrawal rules"""
    auth = await require_admin(request, authorization)
    
    query = "SELECT * FROM rules WHERE 1=1"
    params = []
    
    if rule_type:
        params.append(rule_type)
        query += f" AND rule_type = ${len(params)}"
    if scope:
        params.append(scope)
        query += f" AND scope = ${len(params)}"
    
    query += " ORDER BY priority DESC, created_at DESC"
    rules = await fetch_all(query, *params) if params else await fetch_all(query)
    
    return [{
        "rule_id": r['rule_id'],
        "rule_type": r['rule_type'],
        "scope": r['scope'],
        "scope_id": r.get('scope_id'),
        "priority": r['priority'],
        "conditions": json.loads(r['conditions']) if isinstance(r['conditions'], str) else r['conditions'],
        "actions": json.loads(r['actions']) if isinstance(r['actions'], str) else r['actions'],
        "is_active": r['is_active'],
        "valid_from": r['valid_from'].isoformat() if r.get('valid_from') else None,
        "valid_until": r['valid_until'].isoformat() if r.get('valid_until') else None
    } for r in rules]


@router.post("/rules", summary="Create a rule")
async def create_rule(
    request: Request,
    data: RuleCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a deposit/withdrawal rule"""
    auth = await require_admin(request, authorization)
    
    rule_id = str(uuid.uuid4())
    
    await execute('''
        INSERT INTO rules (rule_id, rule_type, scope, scope_id, priority, conditions, actions, is_active, valid_from, valid_until, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
    ''', rule_id, data.rule_type, data.scope, data.scope_id, data.priority,
        json.dumps(data.conditions), json.dumps(data.actions), data.is_active, data.valid_from, data.valid_until)
    
    await log_audit(auth.user_id, auth.username, "admin.rule_created", "rule", rule_id, data.model_dump())
    
    return {"success": True, "rule_id": rule_id, "message": "Rule created"}


@router.delete("/rules/{rule_id}", summary="Delete a rule")
async def delete_rule(
    request: Request,
    rule_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete a rule"""
    auth = await require_admin(request, authorization)
    
    await execute("DELETE FROM rules WHERE rule_id = $1", rule_id)
    await log_audit(auth.user_id, auth.username, "admin.rule_deleted", "rule", rule_id)
    
    return {"success": True, "message": "Rule deleted"}


# ==================== LEGACY TELEGRAM CONFIG DELETED ====================
# These endpoints have been REMOVED per system requirements.
# Use /api/v1/admin/telegram/bots for multi-bot management ONLY.


# ==================== SYSTEM SETTINGS ====================

@router.get("/settings", summary="Get system settings")
async def get_system_settings(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """Get system settings including rules engine config"""
    auth = await require_admin(request, authorization)
    
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    if not settings:
        return {"configured": False}
    
    return {
        "api_enabled": settings.get('api_enabled', True),
        "telegram_enabled": settings.get('telegram_enabled', False),
        "manual_verification": settings.get('manual_verification', True),
        "auto_approve_deposits": settings.get('auto_approve_deposits', False),
        "auto_approve_withdrawals": settings.get('auto_approve_withdrawals', False),
        "referral_system_enabled": settings.get('referral_system_enabled', True),
        "bonus_system_enabled": settings.get('bonus_system_enabled', True),
        "webhook_enabled": settings.get('webhook_enabled', True),
        "default_deposit_bonus": settings.get('default_deposit_bonus', 0),
        "signup_bonus": settings.get('signup_bonus', 0),
        "default_referral_bonus": settings.get('default_referral_bonus', 5),
        "deposit_block_balance": settings.get('deposit_block_balance', 5),
        "min_cashout_multiplier": settings.get('min_cashout_multiplier', 1),
        "max_cashout_multiplier": settings.get('max_cashout_multiplier', 3)
    }


@router.put("/settings", summary="Update system settings")
async def update_system_settings(
    request: Request,
    data: SystemSettingsUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update system settings"""
    auth = await require_admin(request, authorization)
    
    updates = []
    params = []
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            params.append(value)
            updates.append(f"{field} = ${len(params)}")
    
    if updates:
        updates.append("updated_at = NOW()")
        await execute(
            f"UPDATE system_settings SET {', '.join(updates)} WHERE id = 'global'",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "admin.settings_updated", "config", "global", data.model_dump())
    
    return {"success": True, "message": "Settings updated"}


# ==================== GAMES ====================

@router.get("/games", summary="List games with rules")
async def list_games_admin(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all games with their rules"""
    auth = await require_admin(request, authorization)
    
    games = await fetch_all("SELECT * FROM games ORDER BY display_name")
    
    return [{
        "game_id": g['game_id'],
        "game_name": g['game_name'],
        "display_name": g['display_name'],
        "description": g.get('description'),
        "min_deposit_amount": g['min_deposit_amount'],
        "max_deposit_amount": g['max_deposit_amount'],
        "min_withdrawal_amount": g['min_withdrawal_amount'],
        "max_withdrawal_amount": g['max_withdrawal_amount'],
        "bonus_rules": json.loads(g['bonus_rules']) if isinstance(g.get('bonus_rules'), str) else g.get('bonus_rules', {}),
        "deposit_rules": json.loads(g['deposit_rules']) if isinstance(g.get('deposit_rules'), str) else g.get('deposit_rules', {}),
        "withdrawal_rules": json.loads(g['withdrawal_rules']) if isinstance(g.get('withdrawal_rules'), str) else g.get('withdrawal_rules', {}),
        "is_active": g['is_active']
    } for g in games]


@router.put("/games/{game_id}", summary="Update game rules")
async def update_game_rules(
    request: Request,
    game_id: str,
    data: GameRulesUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update game-specific rules and limits"""
    auth = await require_admin(request, authorization)
    
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
    if data.deposit_rules is not None:
        params.append(json.dumps(data.deposit_rules))
        updates.append(f"deposit_rules = ${len(params)}")
    if data.withdrawal_rules is not None:
        params.append(json.dumps(data.withdrawal_rules))
        updates.append(f"withdrawal_rules = ${len(params)}")
    if data.bonus_rules is not None:
        params.append(json.dumps(data.bonus_rules))
        updates.append(f"bonus_rules = ${len(params)}")
    if data.is_active is not None:
        params.append(data.is_active)
        updates.append(f"is_active = ${len(params)}")
    
    if updates:
        params.append(game_id)
        updates.append("updated_at = NOW()")
        await execute(
            f"UPDATE games SET {', '.join(updates)} WHERE game_id = ${len(params)}",
            *params
        )
    
    await log_audit(auth.user_id, auth.username, "admin.game_rules_updated", "game", game_id, data.model_dump())
    
    return {"success": True, "message": f"Game rules updated for {game['display_name']}"}


# ==================== AUDIT LOGS ====================

@router.get("/audit-logs", summary="Get audit logs")
async def get_audit_logs(
    request: Request,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    authorization: str = Header(..., alias="Authorization")
):
    """Get audit logs with filters"""
    auth = await require_admin(request, authorization)
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if user_id:
        params.append(user_id)
        query += f" AND user_id = ${len(params)}"
    if action:
        params.append(f"%{action}%")
        query += f" AND action ILIKE ${len(params)}"
    if resource_type:
        params.append(resource_type)
        query += f" AND resource_type = ${len(params)}"
    
    params.append(limit)
    query += f" ORDER BY created_at DESC LIMIT ${len(params)}"
    
    logs = await fetch_all(query, *params)
    
    return [{
        "log_id": l['log_id'],
        "user_id": l.get('user_id'),
        "username": l.get('username'),
        "action": l['action'],
        "resource_type": l.get('resource_type'),
        "resource_id": l.get('resource_id'),
        "details": json.loads(l['details']) if isinstance(l.get('details'), str) else l.get('details'),
        "ip_address": l.get('ip_address'),
        "created_at": l['created_at'].isoformat() if l.get('created_at') else None
    } for l in logs]


# ==================== HELPER ====================

async def log_audit(user_id, username, action, resource_type, resource_id, details=None):
    """Log an audit event"""
    log_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    ''', log_id, user_id, username, action, resource_type, resource_id,
       json.dumps(details) if details else None)
