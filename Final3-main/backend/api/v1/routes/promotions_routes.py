"""
API v1 Promotions Routes
Backend-driven promotional banners and events for client home page

Features:
- Admin-managed promotions with schedule and priority
- Active/scheduled/expired status tracking
- Banner content with images, CTAs, and links
- Context-aware (can target specific user segments)
"""
from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid

from ..core.database import fetch_one, fetch_all, execute

router = APIRouter(prefix="/promotions", tags=["Promotions"])


# ==================== MODELS ====================

class PromotionCreate(BaseModel):
    """Create a new promotion"""
    title: str = Field(..., max_length=100)
    subtitle: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    cta_text: Optional[str] = Field("Learn More", max_length=50)
    cta_link: Optional[str] = None
    badge_text: Optional[str] = Field(None, max_length=30)
    background_color: Optional[str] = Field("#8b5cf6")  # Default purple
    text_color: Optional[str] = Field("#ffffff")
    priority: int = Field(0, ge=0, le=100)
    start_date: datetime
    end_date: datetime
    target_segment: Optional[str] = None  # all, new_users, vip, etc.
    is_active: bool = True


class PromotionUpdate(BaseModel):
    """Update promotion"""
    title: Optional[str] = Field(None, max_length=100)
    subtitle: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    cta_text: Optional[str] = Field(None, max_length=50)
    cta_link: Optional[str] = None
    badge_text: Optional[str] = Field(None, max_length=30)
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_segment: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== DATABASE SETUP ====================

async def ensure_promotions_table():
    """Create promotions table if not exists"""
    try:
        await execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                promo_id VARCHAR(36) PRIMARY KEY,
                title VARCHAR(100) NOT NULL,
                subtitle VARCHAR(200),
                description TEXT,
                image_url TEXT,
                cta_text VARCHAR(50) DEFAULT 'Learn More',
                cta_link TEXT,
                badge_text VARCHAR(30),
                background_color VARCHAR(20) DEFAULT '#8b5cf6',
                text_color VARCHAR(20) DEFAULT '#ffffff',
                priority INTEGER DEFAULT 0,
                start_date TIMESTAMPTZ NOT NULL,
                end_date TIMESTAMPTZ NOT NULL,
                target_segment VARCHAR(50) DEFAULT 'all',
                is_active BOOLEAN DEFAULT TRUE,
                views INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        await execute('CREATE INDEX IF NOT EXISTS idx_promotions_dates ON promotions(start_date, end_date)')
        await execute('CREATE INDEX IF NOT EXISTS idx_promotions_active ON promotions(is_active)')
    except Exception:
        pass


# ==================== AUTH HELPERS ====================

async def require_admin_access(request: Request, authorization: str):
    """Require admin role"""
    from ..core.auth import get_current_user
    user = await get_current_user(request, authorization, None)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_current_user_optional(request: Request, authorization: str = None):
    """Get current user if authenticated, otherwise None"""
    if not authorization:
        return None
    try:
        from ..core.auth import get_current_user
        return await get_current_user(request, authorization, None)
    except:
        return None


# ==================== PUBLIC ENDPOINTS ====================

@router.get("/active", summary="Get active promotions for client home")
async def get_active_promotions(
    request: Request,
    authorization: str = Header(None)
):
    """
    Get currently active promotions for display on client home.
    Returns promotions sorted by priority, filtered by date range.
    Optionally filters by user segment if authenticated.
    """
    await ensure_promotions_table()
    
    user = await get_current_user_optional(request, authorization)
    now = datetime.now(timezone.utc)
    
    # Get active promotions within date range
    promos = await fetch_all("""
        SELECT promo_id, title, subtitle, description, image_url,
               cta_text, cta_link, badge_text, background_color, text_color,
               priority, start_date, end_date, target_segment
        FROM promotions
        WHERE is_active = TRUE
          AND start_date <= $1
          AND end_date >= $1
        ORDER BY priority DESC, created_at DESC
        LIMIT 10
    """, now)
    
    # Filter by segment if applicable
    result = []
    for p in promos:
        segment = p.get('target_segment', 'all')
        if segment == 'all' or segment is None:
            result.append(dict(p))
        elif user:
            # Add segment-specific filtering logic here
            # For now, include all for authenticated users
            result.append(dict(p))
    
    return {
        "success": True,
        "promotions": result,
        "count": len(result)
    }


@router.post("/track-view/{promo_id}", summary="Track promotion view")
async def track_view(promo_id: str):
    """Increment view count for a promotion"""
    await ensure_promotions_table()
    await execute("UPDATE promotions SET views = views + 1 WHERE promo_id = $1", promo_id)
    return {"success": True}


@router.post("/track-click/{promo_id}", summary="Track promotion click")
async def track_click(promo_id: str):
    """Increment click count for a promotion"""
    await ensure_promotions_table()
    await execute("UPDATE promotions SET clicks = clicks + 1 WHERE promo_id = $1", promo_id)
    return {"success": True}


# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/all", summary="Get all promotions (admin)")
async def get_all_promotions(
    request: Request,
    authorization: str = Header(...)
):
    """Get all promotions including inactive and scheduled"""
    await require_admin_access(request, authorization)
    await ensure_promotions_table()
    
    promos = await fetch_all("""
        SELECT * FROM promotions
        ORDER BY priority DESC, created_at DESC
    """)
    
    now = datetime.now(timezone.utc)
    
    # Add status field based on dates
    result = []
    for p in promos:
        promo = dict(p)
        if not promo['is_active']:
            promo['status'] = 'disabled'
        elif promo['end_date'] < now:
            promo['status'] = 'expired'
        elif promo['start_date'] > now:
            promo['status'] = 'scheduled'
        else:
            promo['status'] = 'active'
        result.append(promo)
    
    return {
        "success": True,
        "promotions": result
    }


@router.post("/admin", summary="Create promotion (admin)")
async def create_promotion(
    request: Request,
    data: PromotionCreate,
    authorization: str = Header(...)
):
    """Create a new promotion"""
    admin = await require_admin_access(request, authorization)
    await ensure_promotions_table()
    
    promo_id = str(uuid.uuid4())
    
    await execute('''
        INSERT INTO promotions (
            promo_id, title, subtitle, description, image_url,
            cta_text, cta_link, badge_text, background_color, text_color,
            priority, start_date, end_date, target_segment, is_active, created_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
    ''', promo_id, data.title, data.subtitle, data.description, data.image_url,
       data.cta_text, data.cta_link, data.badge_text, data.background_color, data.text_color,
       data.priority, data.start_date, data.end_date, data.target_segment, data.is_active,
       admin.user_id)
    
    return {"success": True, "promo_id": promo_id, "message": "Promotion created"}


@router.put("/admin/{promo_id}", summary="Update promotion (admin)")
async def update_promotion(
    request: Request,
    promo_id: str,
    data: PromotionUpdate,
    authorization: str = Header(...)
):
    """Update an existing promotion"""
    await require_admin_access(request, authorization)
    
    # Build dynamic update query
    updates = []
    params = [promo_id]
    idx = 2
    
    fields = [
        ('title', data.title),
        ('subtitle', data.subtitle),
        ('description', data.description),
        ('image_url', data.image_url),
        ('cta_text', data.cta_text),
        ('cta_link', data.cta_link),
        ('badge_text', data.badge_text),
        ('background_color', data.background_color),
        ('text_color', data.text_color),
        ('priority', data.priority),
        ('start_date', data.start_date),
        ('end_date', data.end_date),
        ('target_segment', data.target_segment),
        ('is_active', data.is_active),
    ]
    
    for field_name, value in fields:
        if value is not None:
            updates.append(f"{field_name} = ${idx}")
            params.append(value)
            idx += 1
    
    if updates:
        updates.append("updated_at = NOW()")
        query = f"UPDATE promotions SET {', '.join(updates)} WHERE promo_id = $1"
        await execute(query, *params)
    
    return {"success": True, "message": "Promotion updated"}


@router.delete("/admin/{promo_id}", summary="Delete promotion (admin)")
async def delete_promotion(
    request: Request,
    promo_id: str,
    authorization: str = Header(...)
):
    """Delete a promotion"""
    await require_admin_access(request, authorization)
    
    await execute("DELETE FROM promotions WHERE promo_id = $1", promo_id)
    
    return {"success": True, "message": "Promotion deleted"}


@router.get("/admin/stats", summary="Get promotion statistics")
async def get_promotion_stats(
    request: Request,
    authorization: str = Header(...)
):
    """Get aggregate statistics for promotions"""
    await require_admin_access(request, authorization)
    await ensure_promotions_table()
    
    now = datetime.now(timezone.utc)
    
    stats = await fetch_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_active AND start_date <= $1 AND end_date >= $1) as active,
            COUNT(*) FILTER (WHERE is_active AND start_date > $1) as scheduled,
            COUNT(*) FILTER (WHERE end_date < $1) as expired,
            SUM(views) as total_views,
            SUM(clicks) as total_clicks
        FROM promotions
    """, now)
    
    return {
        "success": True,
        "stats": dict(stats) if stats else {}
    }
