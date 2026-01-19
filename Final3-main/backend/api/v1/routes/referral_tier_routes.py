"""
API v1 Referral Tier Routes
Manages referral tier system with:
- Tier definitions (Starter, Silver, Gold, Platinum, Ruby)
- Global bonus overrides for campaigns
- Individual client overrides

Tier Levels:
- Starter: 0-6 referrals = 10%
- Silver: 7-14 referrals = 15%
- Gold: 15-29 referrals = 20%
- Platinum: 30-49 referrals = 25%
- Ruby: 50+ referrals = 30%

Override Priority:
1. Individual client override (highest)
2. Global campaign override
3. Tier-based percentage
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid

from ..core.database import fetch_one, fetch_all, execute

router = APIRouter(prefix="/admin/referral-tiers", tags=["Admin - Referral Tiers"])


# ==================== MODELS ====================

class ReferralTier(BaseModel):
    """Referral tier definition"""
    tier_name: str
    min_referrals: int
    max_referrals: Optional[int] = None  # None = unlimited
    bonus_percentage: float = Field(..., ge=0, le=100)
    description: Optional[str] = None
    is_active: bool = True


class GlobalOverride(BaseModel):
    """Global bonus override for campaigns"""
    name: str
    bonus_percentage: float = Field(..., ge=0, le=100)
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    is_active: bool = True


class ClientOverrideCreate(BaseModel):
    """Individual client bonus override"""
    user_id: str
    bonus_percentage: float = Field(..., ge=0, le=100)
    expires_at: Optional[datetime] = None
    reason: str


class ClientOverrideUpdate(BaseModel):
    """Update client override"""
    bonus_percentage: Optional[float] = Field(None, ge=0, le=100)
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== AUTH HELPER ====================

async def require_admin_access(request: Request, authorization: str):
    """Require admin role"""
    from ..core.auth import get_current_user
    user = await get_current_user(request, authorization, None)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ==================== DATABASE SCHEMA SETUP ====================

async def ensure_tier_tables():
    """Create referral tier tables if they don't exist"""
    try:
        await execute('''
            CREATE TABLE IF NOT EXISTS referral_tiers (
                tier_id VARCHAR(36) PRIMARY KEY,
                tier_name VARCHAR(50) UNIQUE NOT NULL,
                min_referrals INTEGER NOT NULL,
                max_referrals INTEGER,
                bonus_percentage FLOAT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        await execute('''
            CREATE TABLE IF NOT EXISTS referral_global_overrides (
                override_id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                bonus_percentage FLOAT NOT NULL,
                start_date TIMESTAMPTZ NOT NULL,
                end_date TIMESTAMPTZ NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        await execute('''
            CREATE TABLE IF NOT EXISTS referral_client_overrides (
                override_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                bonus_percentage FLOAT NOT NULL,
                expires_at TIMESTAMPTZ,
                reason TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id)
            )
        ''')
        
        # Seed default tiers if none exist
        existing = await fetch_one("SELECT COUNT(*) as count FROM referral_tiers")
        if existing['count'] == 0:
            default_tiers = [
                ('STARTER', 'Starter', 0, 6, 10.0, 'Entry level - 0-6 referrals'),
                ('SILVER', 'Silver', 7, 14, 15.0, 'Silver tier - 7-14 referrals'),
                ('GOLD', 'Gold', 15, 29, 20.0, 'Gold tier - 15-29 referrals'),
                ('PLATINUM', 'Platinum', 30, 49, 25.0, 'Platinum tier - 30-49 referrals'),
                ('RUBY', 'Ruby', 50, None, 30.0, 'Ruby tier - 50+ referrals (highest)'),
            ]
            for tier_id, name, min_ref, max_ref, pct, desc in default_tiers:
                await execute('''
                    INSERT INTO referral_tiers (tier_id, tier_name, min_referrals, max_referrals, bonus_percentage, description)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''', tier_id, name, min_ref, max_ref, pct, desc)
    except Exception as e:
        # Tables may already exist - that's fine
        pass


# ==================== TIER ENDPOINTS ====================

@router.get("/tiers", summary="Get all referral tiers")
async def get_tiers(request: Request, authorization: str = Header(...)):
    """Get all tier definitions"""
    await require_admin_access(request, authorization)
    await ensure_tier_tables()
    
    tiers = await fetch_all("""
        SELECT tier_id, tier_name, min_referrals, max_referrals, 
               bonus_percentage, description, is_active,
               created_at, updated_at
        FROM referral_tiers
        ORDER BY min_referrals ASC
    """)
    
    return {
        "success": True,
        "tiers": [dict(t) for t in tiers]
    }


@router.put("/tiers/{tier_id}", summary="Update a tier")
async def update_tier(
    request: Request,
    tier_id: str,
    data: ReferralTier,
    authorization: str = Header(...)
):
    """Update tier configuration"""
    admin = await require_admin_access(request, authorization)
    await ensure_tier_tables()
    
    result = await execute('''
        UPDATE referral_tiers
        SET tier_name = $2, min_referrals = $3, max_referrals = $4,
            bonus_percentage = $5, description = $6, is_active = $7,
            updated_at = NOW()
        WHERE tier_id = $1
    ''', tier_id, data.tier_name, data.min_referrals, data.max_referrals,
       data.bonus_percentage, data.description, data.is_active)
    
    return {"success": True, "message": "Tier updated"}


# ==================== GLOBAL OVERRIDE ENDPOINTS ====================

@router.get("/global-overrides", summary="Get global overrides")
async def get_global_overrides(request: Request, authorization: str = Header(...)):
    """Get all global bonus overrides (campaigns)"""
    await require_admin_access(request, authorization)
    await ensure_tier_tables()
    
    overrides = await fetch_all("""
        SELECT override_id, name, bonus_percentage, start_date, end_date,
               description, is_active, created_by, created_at
        FROM referral_global_overrides
        ORDER BY start_date DESC
    """)
    
    # Check which one is currently active
    now = datetime.now(timezone.utc)
    active_override = None
    for o in overrides:
        if o['is_active'] and o['start_date'] <= now <= o['end_date']:
            active_override = dict(o)
            break
    
    return {
        "success": True,
        "overrides": [dict(o) for o in overrides],
        "active_override": active_override
    }


@router.post("/global-overrides", summary="Create global override")
async def create_global_override(
    request: Request,
    data: GlobalOverride,
    authorization: str = Header(...)
):
    """Create a global bonus override campaign"""
    admin = await require_admin_access(request, authorization)
    await ensure_tier_tables()
    
    override_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO referral_global_overrides 
        (override_id, name, bonus_percentage, start_date, end_date, description, is_active, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    ''', override_id, data.name, data.bonus_percentage, data.start_date,
       data.end_date, data.description, data.is_active, admin.user_id)
    
    return {"success": True, "override_id": override_id, "message": "Global override created"}


@router.put("/global-overrides/{override_id}", summary="Update global override")
async def update_global_override(
    request: Request,
    override_id: str,
    data: GlobalOverride,
    authorization: str = Header(...)
):
    """Update a global override"""
    await require_admin_access(request, authorization)
    
    await execute('''
        UPDATE referral_global_overrides
        SET name = $2, bonus_percentage = $3, start_date = $4, end_date = $5,
            description = $6, is_active = $7, updated_at = NOW()
        WHERE override_id = $1
    ''', override_id, data.name, data.bonus_percentage, data.start_date,
       data.end_date, data.description, data.is_active)
    
    return {"success": True, "message": "Global override updated"}


@router.delete("/global-overrides/{override_id}", summary="Delete global override")
async def delete_global_override(
    request: Request,
    override_id: str,
    authorization: str = Header(...)
):
    """Delete a global override"""
    await require_admin_access(request, authorization)
    
    await execute("DELETE FROM referral_global_overrides WHERE override_id = $1", override_id)
    
    return {"success": True, "message": "Global override deleted"}


# ==================== CLIENT OVERRIDE ENDPOINTS ====================

@router.get("/client-overrides", summary="Get all client overrides")
async def get_client_overrides(request: Request, authorization: str = Header(...)):
    """Get all individual client overrides"""
    await require_admin_access(request, authorization)
    await ensure_tier_tables()
    
    overrides = await fetch_all("""
        SELECT co.*, u.username, u.display_name
        FROM referral_client_overrides co
        JOIN users u ON u.user_id = co.user_id
        ORDER BY co.created_at DESC
    """)
    
    return {
        "success": True,
        "overrides": [dict(o) for o in overrides]
    }


@router.post("/client-overrides", summary="Create client override")
async def create_client_override(
    request: Request,
    data: ClientOverrideCreate,
    authorization: str = Header(...)
):
    """Create an individual client bonus override"""
    admin = await require_admin_access(request, authorization)
    await ensure_tier_tables()
    
    # Check user exists
    user = await fetch_one("SELECT user_id FROM users WHERE user_id = $1", data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if override already exists
    existing = await fetch_one(
        "SELECT override_id FROM referral_client_overrides WHERE user_id = $1",
        data.user_id
    )
    
    if existing:
        # Update existing
        await execute('''
            UPDATE referral_client_overrides
            SET bonus_percentage = $2, expires_at = $3, reason = $4, is_active = TRUE, updated_at = NOW()
            WHERE user_id = $1
        ''', data.user_id, data.bonus_percentage, data.expires_at, data.reason)
        return {"success": True, "message": "Client override updated"}
    
    override_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO referral_client_overrides 
        (override_id, user_id, bonus_percentage, expires_at, reason, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
    ''', override_id, data.user_id, data.bonus_percentage, data.expires_at, 
       data.reason, admin.user_id)
    
    return {"success": True, "override_id": override_id, "message": "Client override created"}


@router.put("/client-overrides/{user_id}", summary="Update client override")
async def update_client_override(
    request: Request,
    user_id: str,
    data: ClientOverrideUpdate,
    authorization: str = Header(...)
):
    """Update a client override"""
    await require_admin_access(request, authorization)
    
    updates = []
    params = [user_id]
    idx = 2
    
    if data.bonus_percentage is not None:
        updates.append(f"bonus_percentage = ${idx}")
        params.append(data.bonus_percentage)
        idx += 1
    
    if data.expires_at is not None:
        updates.append(f"expires_at = ${idx}")
        params.append(data.expires_at)
        idx += 1
    
    if data.reason is not None:
        updates.append(f"reason = ${idx}")
        params.append(data.reason)
        idx += 1
    
    if data.is_active is not None:
        updates.append(f"is_active = ${idx}")
        params.append(data.is_active)
        idx += 1
    
    if updates:
        updates.append("updated_at = NOW()")
        query = f"UPDATE referral_client_overrides SET {', '.join(updates)} WHERE user_id = $1"
        await execute(query, *params)
    
    return {"success": True, "message": "Client override updated"}


@router.delete("/client-overrides/{user_id}", summary="Delete client override")
async def delete_client_override(
    request: Request,
    user_id: str,
    authorization: str = Header(...)
):
    """Delete a client override"""
    await require_admin_access(request, authorization)
    
    await execute("DELETE FROM referral_client_overrides WHERE user_id = $1", user_id)
    
    return {"success": True, "message": "Client override deleted"}


# ==================== EFFECTIVE BONUS CALCULATOR ====================

@router.get("/effective-bonus/{user_id}", summary="Calculate effective bonus for a user")
async def get_effective_bonus(
    request: Request,
    user_id: str,
    authorization: str = Header(...)
):
    """
    Calculate the effective referral bonus percentage for a user.
    
    Priority:
    1. Individual client override (if active and not expired)
    2. Global campaign override (if active and within date range)
    3. Tier-based percentage (based on referral count)
    """
    await require_admin_access(request, authorization)
    await ensure_tier_tables()
    
    now = datetime.now(timezone.utc)
    
    # Get user's referral count
    referral_count = await fetch_one("""
        SELECT COUNT(*) as count FROM users WHERE referred_by_user_id = $1
    """, user_id)
    count = referral_count['count'] if referral_count else 0
    
    # 1. Check for individual override
    client_override = await fetch_one("""
        SELECT bonus_percentage, expires_at, reason
        FROM referral_client_overrides
        WHERE user_id = $1 AND is_active = TRUE
    """, user_id)
    
    if client_override:
        if client_override['expires_at'] is None or client_override['expires_at'] > now:
            return {
                "success": True,
                "user_id": user_id,
                "referral_count": count,
                "effective_percentage": client_override['bonus_percentage'],
                "source": "individual_override",
                "reason": client_override['reason'],
                "details": dict(client_override)
            }
    
    # 2. Check for active global override
    global_override = await fetch_one("""
        SELECT name, bonus_percentage, description
        FROM referral_global_overrides
        WHERE is_active = TRUE AND start_date <= $1 AND end_date >= $1
        ORDER BY bonus_percentage DESC
        LIMIT 1
    """, now)
    
    if global_override:
        return {
            "success": True,
            "user_id": user_id,
            "referral_count": count,
            "effective_percentage": global_override['bonus_percentage'],
            "source": "global_campaign",
            "campaign_name": global_override['name'],
            "details": dict(global_override)
        }
    
    # 3. Calculate tier-based percentage
    tier = await fetch_one("""
        SELECT tier_name, bonus_percentage, description
        FROM referral_tiers
        WHERE is_active = TRUE
          AND min_referrals <= $1
          AND (max_referrals IS NULL OR max_referrals >= $1)
        ORDER BY min_referrals DESC
        LIMIT 1
    """, count)
    
    if tier:
        return {
            "success": True,
            "user_id": user_id,
            "referral_count": count,
            "effective_percentage": tier['bonus_percentage'],
            "source": "tier",
            "tier_name": tier['tier_name'],
            "details": dict(tier)
        }
    
    # Default fallback
    return {
        "success": True,
        "user_id": user_id,
        "referral_count": count,
        "effective_percentage": 10.0,  # Default Starter rate
        "source": "default",
        "details": None
    }


# ==================== PUBLIC: USER'S OWN TIER INFO ====================

@router.get("/my-tier", summary="Get current user's tier info")
async def get_my_tier(request: Request, authorization: str = Header(...)):
    """Get the current user's referral tier and bonus percentage"""
    from ..core.auth import get_current_user
    
    user = await get_current_user(request, authorization, None)
    await ensure_tier_tables()
    
    now = datetime.now(timezone.utc)
    
    # Get referral count
    referral_count = await fetch_one("""
        SELECT COUNT(*) as count FROM users WHERE referred_by_user_id = $1
    """, user.user_id)
    count = referral_count['count'] if referral_count else 0
    
    # Get all tiers for progress display
    all_tiers = await fetch_all("""
        SELECT tier_name, min_referrals, max_referrals, bonus_percentage
        FROM referral_tiers
        WHERE is_active = TRUE
        ORDER BY min_referrals ASC
    """)
    
    # Calculate effective bonus
    effective_pct = 10.0
    current_tier = "Starter"
    next_tier = None
    referrals_to_next = None
    
    for tier in all_tiers:
        if count >= tier['min_referrals']:
            effective_pct = tier['bonus_percentage']
            current_tier = tier['tier_name']
        else:
            next_tier = tier['tier_name']
            referrals_to_next = tier['min_referrals'] - count
            break
    
    # Check for individual override
    client_override = await fetch_one("""
        SELECT bonus_percentage FROM referral_client_overrides
        WHERE user_id = $1 AND is_active = TRUE
          AND (expires_at IS NULL OR expires_at > $2)
    """, user.user_id, now)
    
    if client_override:
        effective_pct = client_override['bonus_percentage']
    
    # Check for global override
    global_override = await fetch_one("""
        SELECT bonus_percentage, name FROM referral_global_overrides
        WHERE is_active = TRUE AND start_date <= $1 AND end_date >= $1
        LIMIT 1
    """, now)
    
    promotion_active = False
    promotion_name = None
    if global_override and not client_override:
        effective_pct = global_override['bonus_percentage']
        promotion_active = True
        promotion_name = global_override['name']
    
    return {
        "success": True,
        "referral_count": count,
        "current_tier": current_tier,
        "effective_percentage": effective_pct,
        "next_tier": next_tier,
        "referrals_to_next": referrals_to_next,
        "promotion_active": promotion_active,
        "promotion_name": promotion_name,
        "all_tiers": [dict(t) for t in all_tiers]
    }
