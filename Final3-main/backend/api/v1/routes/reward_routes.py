"""
API v1 Admin Rewards Routes
Reward definitions management and automatic granting
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import json

from ..core.database import fetch_one, fetch_all, execute
from ..services import log_audit

router = APIRouter(prefix="/admin/rewards", tags=["Admin Rewards"])


# ==================== AUTH HELPER ====================

async def require_admin(request: Request, authorization: str):
    """Require admin role for access"""
    from .dependencies import require_auth
    auth = await require_auth(request, authorization=authorization)
    admin = await fetch_one("SELECT role FROM users WHERE user_id = $1", auth.user_id)
    if not admin or admin.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return auth


# ==================== MODELS ====================

class RewardCreate(BaseModel):
    """Create reward definition"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    trigger_type: str = Field(..., description="account_setup, first_login, first_deposit, custom")
    reward_type: str = Field(default="play_credits", description="play_credits or bonus")
    value: float = Field(..., gt=0)
    value_type: str = Field(default="fixed", description="fixed or percentage")
    enabled: bool = True
    is_one_time: bool = True
    visible_to_client: bool = True


class RewardUpdate(BaseModel):
    """Update reward definition"""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    reward_type: Optional[str] = None
    value: Optional[float] = None
    value_type: Optional[str] = None
    enabled: Optional[bool] = None
    is_one_time: Optional[bool] = None
    visible_to_client: Optional[bool] = None


class ManualRewardGrant(BaseModel):
    """Manual reward grant request"""
    user_id: str
    reward_id: str
    custom_amount: Optional[float] = None
    reason: Optional[str] = None


# ==================== CRUD ====================

@router.get("")
async def list_rewards(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all reward definitions"""
    await require_admin(request, authorization)
    
    rewards = await fetch_all("""
        SELECT reward_id, name, description, trigger_type, reward_type,
               value, value_type, enabled, is_one_time, visible_to_client,
               created_at
        FROM reward_definitions
        ORDER BY created_at DESC
    """)
    
    # Get grant counts for each reward
    result = []
    for r in rewards:
        count = await fetch_one(
            "SELECT COUNT(*) as count FROM reward_grants WHERE reward_id = $1",
            r['reward_id']
        )
        result.append({
            **dict(r),
            "grant_count": count['count'] if count else 0
        })
    
    return {"rewards": result}


@router.post("")
async def create_reward(
    request: Request,
    data: RewardCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a new reward definition"""
    auth = await require_admin(request, authorization)
    
    reward_id = str(uuid.uuid4())
    
    await execute("""
        INSERT INTO reward_definitions (
            reward_id, name, description, trigger_type, reward_type,
            value, value_type, enabled, is_one_time, visible_to_client,
            created_by, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
    """, 
        reward_id, data.name, data.description, data.trigger_type, data.reward_type,
        data.value, data.value_type, data.enabled, data.is_one_time, data.visible_to_client,
        auth.user_id
    )
    
    await log_audit(
        auth.user_id, "admin", "reward.created", "reward", reward_id,
        {"name": data.name, "trigger_type": data.trigger_type}
    )
    
    return {
        "reward_id": reward_id,
        "message": "Reward created successfully"
    }


@router.get("/{reward_id}")
async def get_reward(
    request: Request,
    reward_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Get reward definition by ID"""
    await require_admin(request, authorization)
    
    reward = await fetch_one("""
        SELECT * FROM reward_definitions WHERE reward_id = $1
    """, reward_id)
    
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    
    # Get recent grants
    grants = await fetch_all("""
        SELECT rg.*, u.username
        FROM reward_grants rg
        JOIN users u ON rg.user_id = u.user_id
        WHERE rg.reward_id = $1
        ORDER BY rg.granted_at DESC
        LIMIT 20
    """, reward_id)
    
    return {
        "reward": dict(reward),
        "recent_grants": [dict(g) for g in grants]
    }


@router.put("/{reward_id}")
async def update_reward(
    request: Request,
    reward_id: str,
    data: RewardUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update a reward definition"""
    auth = await require_admin(request, authorization)
    
    # Build update query
    updates = []
    params = []
    param_idx = 1
    
    fields = {
        'name': data.name,
        'description': data.description,
        'trigger_type': data.trigger_type,
        'reward_type': data.reward_type,
        'value': data.value,
        'value_type': data.value_type,
        'enabled': data.enabled,
        'is_one_time': data.is_one_time,
        'visible_to_client': data.visible_to_client
    }
    
    for field, value in fields.items():
        if value is not None:
            updates.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(reward_id)
    query = f"UPDATE reward_definitions SET {', '.join(updates)}, updated_at = NOW() WHERE reward_id = ${param_idx}"
    
    await execute(query, *params)
    
    await log_audit(
        auth.user_id, "admin", "reward.updated", "reward", reward_id,
        {"updates": list(fields.keys())}
    )
    
    return {"message": "Reward updated successfully"}


@router.delete("/{reward_id}")
async def delete_reward(
    request: Request,
    reward_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete a reward definition"""
    auth = await require_admin(request, authorization)
    
    await execute("DELETE FROM reward_definitions WHERE reward_id = $1", reward_id)
    
    await log_audit(
        auth.user_id, "admin", "reward.deleted", "reward", reward_id, {}
    )
    
    return {"message": "Reward deleted successfully"}


# ==================== GRANT MANAGEMENT ====================

@router.post("/grant")
async def grant_reward_manually(
    request: Request,
    data: ManualRewardGrant,
    authorization: str = Header(..., alias="Authorization")
):
    """Manually grant a reward to a user"""
    auth = await require_admin(request, authorization)
    
    # Get reward definition
    reward = await fetch_one("SELECT * FROM reward_definitions WHERE reward_id = $1", data.reward_id)
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    
    # Get user
    user = await fetch_one("SELECT * FROM users WHERE user_id = $1", data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already granted (for one-time rewards)
    if reward['is_one_time']:
        existing = await fetch_one("""
            SELECT * FROM reward_grants WHERE reward_id = $1 AND user_id = $2
        """, data.reward_id, data.user_id)
        if existing:
            raise HTTPException(status_code=400, detail="User has already received this one-time reward")
    
    # Calculate amount
    amount = data.custom_amount if data.custom_amount else float(reward['value'])
    
    # Create grant record
    grant_id = str(uuid.uuid4())
    await execute("""
        INSERT INTO reward_grants (grant_id, reward_id, user_id, amount, granted_by, reason, granted_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
    """, grant_id, data.reward_id, data.user_id, amount, auth.user_id, data.reason)
    
    # Credit user based on reward type (PLAY CREDITS ONLY for promo/rewards)
    if reward['reward_type'] == 'play_credits':
        await execute("""
            UPDATE users SET play_credits = COALESCE(play_credits, 0) + $1, updated_at = NOW()
            WHERE user_id = $2
        """, amount, data.user_id)
    elif reward['reward_type'] == 'bonus':
        await execute("""
            UPDATE users SET bonus_balance = COALESCE(bonus_balance, 0) + $1, updated_at = NOW()
            WHERE user_id = $2
        """, amount, data.user_id)
    
    await log_audit(
        auth.user_id, "admin", "reward.granted", "reward_grant", grant_id,
        {"reward_id": data.reward_id, "user_id": data.user_id, "amount": amount, "reason": data.reason}
    )
    
    return {
        "grant_id": grant_id,
        "message": f"Reward granted: ${amount:.2f} {reward['reward_type']} to {user['username']}"
    }


@router.get("/grants/history")
async def get_grant_history(
    request: Request,
    limit: int = 100,
    authorization: str = Header(..., alias="Authorization")
):
    """Get recent reward grant history"""
    await require_admin(request, authorization)
    
    grants = await fetch_all("""
        SELECT rg.*, rd.name as reward_name, rd.reward_type, u.username,
               admin.username as granted_by_username
        FROM reward_grants rg
        JOIN reward_definitions rd ON rg.reward_id = rd.reward_id
        JOIN users u ON rg.user_id = u.user_id
        LEFT JOIN users admin ON rg.granted_by = admin.user_id
        ORDER BY rg.granted_at DESC
        LIMIT $1
    """, limit)
    
    return {"grants": [dict(g) for g in grants]}


# ==================== AUTO TRIGGER ENDPOINTS ====================

@router.post("/trigger/{trigger_type}")
async def trigger_reward(
    request: Request,
    trigger_type: str,
    user_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """
    Trigger automatic reward for a specific event type.
    Called by other services when trigger events occur.
    """
    # This can be called internally or by admin
    from .dependencies import require_auth
    auth = await require_auth(request, authorization=authorization)
    
    # Find applicable reward
    reward = await fetch_one("""
        SELECT * FROM reward_definitions 
        WHERE trigger_type = $1 AND enabled = TRUE
        ORDER BY created_at DESC LIMIT 1
    """, trigger_type)
    
    if not reward:
        return {"granted": False, "message": "No active reward for this trigger type"}
    
    # Check if already granted (for one-time)
    if reward['is_one_time']:
        existing = await fetch_one("""
            SELECT * FROM reward_grants WHERE reward_id = $1 AND user_id = $2
        """, reward['reward_id'], user_id)
        if existing:
            return {"granted": False, "message": "Reward already granted"}
    
    # Grant the reward
    grant_id = str(uuid.uuid4())
    amount = float(reward['value'])
    
    await execute("""
        INSERT INTO reward_grants (grant_id, reward_id, user_id, amount, granted_by, reason, granted_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
    """, grant_id, reward['reward_id'], user_id, amount, None, f"Auto: {trigger_type}")
    
    # Credit based on type
    if reward['reward_type'] == 'play_credits':
        await execute("""
            UPDATE users SET play_credits = COALESCE(play_credits, 0) + $1, updated_at = NOW()
            WHERE user_id = $2
        """, amount, user_id)
    elif reward['reward_type'] == 'bonus':
        await execute("""
            UPDATE users SET bonus_balance = COALESCE(bonus_balance, 0) + $1, updated_at = NOW()
            WHERE user_id = $2
        """, amount, user_id)
    
    await log_audit(
        user_id, "system", "reward.auto_granted", "reward_grant", grant_id,
        {"reward_id": reward['reward_id'], "trigger_type": trigger_type, "amount": amount}
    )
    
    return {
        "granted": True,
        "grant_id": grant_id,
        "reward_name": reward['name'],
        "amount": amount,
        "reward_type": reward['reward_type']
    }
