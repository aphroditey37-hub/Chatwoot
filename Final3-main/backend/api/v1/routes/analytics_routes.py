"""
API v1 Analytics Routes
Layered Analytics System:
- Layer 1: Executive Snapshot (Dashboard)
- Layer 2: Platform Trend Analytics
- Layer 3: Risk & Exposure Analytics
- Layer 4: Entity Analytics (Clients / Games)
- Layer 5: Advanced Efficiency Metrics
"""
from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import json

from ..core.database import fetch_one, fetch_all, execute
from .dependencies import require_auth

router = APIRouter(prefix="/admin/analytics", tags=["Analytics"])


# ==================== AUTH HELPER ====================

async def require_admin_access(request: Request, authorization: str):
    """
    Require admin role for access.
    
    SECURITY: Uses canonical auth module for consistent behavior.
    """
    from ..core.auth import get_current_user, AuthenticatedUser
    
    # Get authenticated user
    user = await get_current_user(request, authorization, None)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail={"message": "Admin access required", "error_code": "E1007"}
        )
    
    return user


# ==================== LAYER 1: EXECUTIVE SNAPSHOT ====================

@router.get("/risk-snapshot", summary="Risk & Exposure Snapshot for Dashboard")
async def get_risk_snapshot(request: Request, authorization: str = Header(...)):
    """
    Risk & Exposure Snapshot (3 cards max for Dashboard)
    - Total Client Balance (Cash + Bonus)
    - Probable Max Cashout (worst-case projection)
    - Cashout Pressure Indicator
    """
    auth = await require_admin_access(request, authorization)
    
    # Total client balances
    balances = await fetch_one("""
        SELECT 
            COALESCE(SUM(real_balance), 0) as total_cash,
            COALESCE(SUM(bonus_balance), 0) as total_bonus,
            COALESCE(SUM(play_credits), 0) as total_play_credits,
            COALESCE(SUM(real_balance + bonus_balance + COALESCE(play_credits, 0)), 0) as total_combined
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    # Get system settings for multipliers
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    
    # Calculate probable max cashout
    # Worst case: all users cashout at max multiplier
    total_deposited = await fetch_one("""
        SELECT COALESCE(SUM(total_deposited), 0) as total
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    # Probable max is MIN of (balance, deposited * max_multiplier)
    total_balance = float(balances['total_combined'] or 0)
    probable_max_cashout = min(
        total_balance,
        float(total_deposited['total'] or 0) * max_multiplier
    )
    
    # Calculate pending withdrawals
    pending_withdrawals = await fetch_one("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(amount), 0) as total_amount
        FROM orders 
        WHERE order_type = 'withdrawal' AND status IN ('pending_review', 'awaiting_payment_proof')
    """)
    
    # Cashout pressure indicator
    # Low: < 20% of balance in pending
    # Medium: 20-50% of balance in pending
    # High: > 50% of balance in pending
    pending_ratio = (float(pending_withdrawals['total_amount'] or 0) / total_balance * 100) if total_balance > 0 else 0
    
    if pending_ratio < 20:
        pressure = "low"
    elif pending_ratio < 50:
        pressure = "medium"
    else:
        pressure = "high"
    
    return {
        "total_client_balance": {
            "cash": round(float(balances['total_cash'] or 0), 2),
            "bonus": round(float(balances['total_bonus'] or 0), 2),
            "play_credits": round(float(balances['total_play_credits'] or 0), 2),
            "combined": round(total_balance, 2)
        },
        "probable_max_cashout": {
            "amount": round(probable_max_cashout, 2),
            "max_multiplier_used": max_multiplier
        },
        "cashout_pressure": {
            "indicator": pressure,
            "pending_count": pending_withdrawals['count'],
            "pending_amount": round(float(pending_withdrawals['total_amount'] or 0), 2),
            "pressure_ratio_percent": round(pending_ratio, 1)
        }
    }


# ==================== LAYER 2: PLATFORM TREND ANALYTICS ====================

@router.get("/platform-trends", summary="Platform Performance Trend Chart Data")
async def get_platform_trends(
    request: Request,
    days: int = 30,
    game: Optional[str] = None,
    client_segment: Optional[str] = None,  # all, referred, non_referred, high_risk
    wallet_type: Optional[str] = None,  # cash, bonus, combined
    authorization: str = Header(...)
):
    """
    Platform Performance Trend - Time series data for dashboard chart
    Returns daily aggregated data for the selected period
    """
    auth = await require_admin_access(request, authorization)
    
    # Calculate date range
    end_date = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
    start_date = end_date - timedelta(days=days)
    
    # Build dynamic query based on filters
    base_conditions = "WHERE o.created_at >= $1 AND o.created_at <= $2"
    params = [start_date, end_date]
    param_idx = 3
    
    # Game filter
    if game and game != 'all':
        base_conditions += f" AND o.game_name = ${param_idx}"
        params.append(game)
        param_idx += 1
    
    # Client segment filter - requires JOIN
    segment_join = ""
    if client_segment and client_segment != 'all':
        segment_join = " JOIN users u ON o.user_id = u.user_id"
        if client_segment == 'referred':
            base_conditions += " AND u.referred_by_code IS NOT NULL"
        elif client_segment == 'non_referred':
            base_conditions += " AND u.referred_by_code IS NULL"
        elif client_segment == 'high_risk':
            base_conditions += " AND u.is_suspicious = TRUE"
    
    # Get daily trend data
    trend_query = f"""
        SELECT 
            DATE(o.created_at) as date,
            COALESCE(SUM(o.amount) FILTER (WHERE o.order_type = 'deposit' AND o.status = 'APPROVED_EXECUTED'), 0) as deposits,
            COALESCE(SUM(o.payout_amount) FILTER (WHERE o.order_type = 'withdrawal' AND o.status = 'APPROVED_EXECUTED'), 0) as withdrawals_paid,
            COALESCE(SUM(o.bonus_amount) FILTER (WHERE o.status = 'APPROVED_EXECUTED'), 0) as bonus_issued,
            COALESCE(SUM(o.void_amount) FILTER (WHERE o.status = 'APPROVED_EXECUTED'), 0) as bonus_voided,
            COALESCE(SUM(o.play_credits_added) FILTER (WHERE o.status = 'APPROVED_EXECUTED'), 0) as play_credits_added,
            COUNT(DISTINCT o.user_id) FILTER (WHERE o.status = 'APPROVED_EXECUTED') as active_clients
        FROM orders o
        {segment_join}
        {base_conditions}
        GROUP BY DATE(o.created_at)
        ORDER BY date ASC
    """
    
    daily_data = await fetch_all(trend_query, *params)
    
    # Format for chart
    trend_data = []
    for row in daily_data:
        deposits = float(row['deposits'] or 0)
        withdrawals = float(row['withdrawals_paid'] or 0)
        net_profit = deposits - withdrawals
        
        trend_data.append({
            "date": row['date'].isoformat() if row.get('date') else None,
            "deposits": round(deposits, 2),
            "withdrawals_paid": round(withdrawals, 2),
            "net_profit": round(net_profit, 2),
            "bonus_issued": round(float(row['bonus_issued'] or 0), 2),
            "bonus_voided": round(float(row['bonus_voided'] or 0), 2),
            "play_credits_added": round(float(row['play_credits_added'] or 0), 2),
            "active_clients": row['active_clients'] or 0
        })
    
    # Calculate totals for the period
    totals = {
        "deposits": sum(d['deposits'] for d in trend_data),
        "withdrawals_paid": sum(d['withdrawals_paid'] for d in trend_data),
        "net_profit": sum(d['net_profit'] for d in trend_data),
        "bonus_issued": sum(d['bonus_issued'] for d in trend_data),
        "bonus_voided": sum(d['bonus_voided'] for d in trend_data)
    }
    
    # Get available games for filter dropdown
    games = await fetch_all("SELECT DISTINCT game_name FROM orders ORDER BY game_name")
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days
        },
        "filters": {
            "game": game or "all",
            "client_segment": client_segment or "all",
            "wallet_type": wallet_type or "combined"
        },
        "available_games": [g['game_name'] for g in games if g['game_name']],
        "trend_data": trend_data,
        "totals": {k: round(v, 2) for k, v in totals.items()}
    }


# ==================== LAYER 3: RISK & EXPOSURE ANALYTICS ====================

@router.get("/risk-exposure", summary="Full Risk & Exposure Report")
async def get_risk_exposure(
    request: Request,
    authorization: str = Header(...)
):
    """
    Full Risk & Exposure Analytics for Reports page
    """
    auth = await require_admin_access(request, authorization)
    
    # SECTION A: Platform Exposure
    exposure = await fetch_one("""
        SELECT 
            COALESCE(SUM(real_balance), 0) as total_cash,
            COALESCE(SUM(bonus_balance), 0) as total_bonus,
            COALESCE(SUM(play_credits), 0) as total_play_credits,
            COALESCE(SUM(real_balance + bonus_balance + COALESCE(play_credits, 0)), 0) as combined_balance,
            COALESCE(SUM(CASE WHEN withdraw_locked = TRUE THEN real_balance + bonus_balance ELSE 0 END), 0) as locked_balance,
            COALESCE(SUM(CASE WHEN withdraw_locked = FALSE THEN real_balance ELSE 0 END), 0) as withdrawable_cash
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    # Get system settings
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    min_multiplier = float(settings.get('min_cashout_multiplier', 1) if settings else 1)
    
    # SECTION B: Probable Max Cashout by Game
    game_exposure = await fetch_all("""
        SELECT 
            g.game_name,
            g.display_name,
            COALESCE(SUM(o.amount) FILTER (WHERE o.order_type = 'deposit' AND o.status = 'APPROVED_EXECUTED'), 0) as total_deposited,
            COALESCE(SUM(o.payout_amount) FILTER (WHERE o.order_type = 'withdrawal' AND o.status = 'APPROVED_EXECUTED'), 0) as total_withdrawn
        FROM games g
        LEFT JOIN orders o ON g.game_name = o.game_name
        GROUP BY g.game_id, g.game_name, g.display_name
        ORDER BY total_deposited DESC
    """)
    
    # SECTION B: Probable Max Cashout by Client Tier
    # High-risk, Regular, VIP (based on deposit amount)
    client_tiers = await fetch_all("""
        SELECT 
            CASE 
                WHEN total_deposited >= 1000 THEN 'vip'
                WHEN total_deposited >= 100 THEN 'regular'
                ELSE 'new'
            END as tier,
            COUNT(*) as client_count,
            COALESCE(SUM(real_balance), 0) as total_cash,
            COALESCE(SUM(bonus_balance), 0) as total_bonus,
            COALESCE(SUM(total_deposited), 0) as total_deposited
        FROM users 
        WHERE role = 'user' AND is_active = TRUE
        GROUP BY CASE 
            WHEN total_deposited >= 1000 THEN 'vip'
            WHEN total_deposited >= 100 THEN 'regular'
            ELSE 'new'
        END
    """)
    
    # SECTION C: Bonus Risk
    bonus_stats = await fetch_one("""
        SELECT 
            COALESCE(SUM(bonus_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_issued,
            COALESCE(SUM(bonus_consumed) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_converted,
            COALESCE(SUM(void_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_voided
        FROM orders
    """)
    
    # Current bonus at risk (still in user balances)
    bonus_at_risk = await fetch_one("""
        SELECT COALESCE(SUM(bonus_balance), 0) as total
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    # SECTION D: Client Risk Table (Top 10 by balance)
    client_risk = await fetch_all("""
        SELECT 
            user_id, username, display_name,
            real_balance, bonus_balance, play_credits,
            total_deposited, total_withdrawn,
            is_suspicious, withdraw_locked
        FROM users 
        WHERE role = 'user' AND is_active = TRUE
        ORDER BY (real_balance + bonus_balance) DESC
        LIMIT 10
    """)
    
    # SECTION D: Game Risk Table
    game_risk = await fetch_all("""
        SELECT 
            g.game_name,
            g.display_name,
            COUNT(DISTINCT o.user_id) as active_players,
            COALESCE(SUM(o.amount) FILTER (WHERE o.order_type = 'deposit' AND o.status = 'APPROVED_EXECUTED'), 0) as total_in,
            COALESCE(SUM(o.payout_amount) FILTER (WHERE o.order_type = 'withdrawal' AND o.status = 'APPROVED_EXECUTED'), 0) as total_out,
            COALESCE(SUM(o.bonus_amount) FILTER (WHERE o.status = 'APPROVED_EXECUTED'), 0) as bonus_given,
            COALESCE(SUM(o.void_amount) FILTER (WHERE o.status = 'APPROVED_EXECUTED'), 0) as voided
        FROM games g
        LEFT JOIN orders o ON g.game_name = o.game_name
        GROUP BY g.game_id, g.game_name, g.display_name
        ORDER BY total_in DESC
    """)
    
    return {
        "platform_exposure": {
            "total_cash_balance": round(float(exposure['total_cash'] or 0), 2),
            "total_bonus_balance": round(float(exposure['total_bonus'] or 0), 2),
            "total_play_credits": round(float(exposure['total_play_credits'] or 0), 2),
            "combined_balance": round(float(exposure['combined_balance'] or 0), 2),
            "locked_balance": round(float(exposure['locked_balance'] or 0), 2),
            "withdrawable_balance": round(float(exposure['withdrawable_cash'] or 0), 2)
        },
        "probable_max_cashout": {
            "total_probable_max": round(float(exposure['withdrawable_cash'] or 0) * max_multiplier, 2),
            "cash_only_max": round(float(exposure['total_cash'] or 0), 2),
            "bonus_inclusive_max": round(float(exposure['combined_balance'] or 0), 2),
            "multiplier_settings": {
                "min": min_multiplier,
                "max": max_multiplier
            },
            "by_game": [{
                "game": g['game_name'],
                "display_name": g['display_name'],
                "total_deposited": round(float(g['total_deposited'] or 0), 2),
                "total_withdrawn": round(float(g['total_withdrawn'] or 0), 2),
                "max_exposure": round(float(g['total_deposited'] or 0) * max_multiplier - float(g['total_withdrawn'] or 0), 2)
            } for g in game_exposure],
            "by_tier": [{
                "tier": t['tier'],
                "client_count": t['client_count'],
                "total_balance": round(float(t['total_cash'] or 0) + float(t['total_bonus'] or 0), 2),
                "max_cashout": round(float(t['total_deposited'] or 0) * max_multiplier, 2)
            } for t in client_tiers]
        },
        "bonus_risk": {
            "bonus_issued": round(float(bonus_stats['bonus_issued'] or 0), 2),
            "bonus_converted": round(float(bonus_stats['bonus_converted'] or 0), 2),
            "bonus_voided": round(float(bonus_stats['bonus_voided'] or 0), 2),
            "bonus_at_risk": round(float(bonus_at_risk['total'] or 0), 2)
        },
        "tables": {
            "client_risk": [{
                "user_id": c['user_id'],
                "username": c['username'],
                "display_name": c['display_name'],
                "cash_balance": round(float(c['real_balance'] or 0), 2),
                "bonus_balance": round(float(c['bonus_balance'] or 0), 2),
                "total_balance": round(float(c['real_balance'] or 0) + float(c['bonus_balance'] or 0), 2),
                "total_deposited": round(float(c['total_deposited'] or 0), 2),
                "total_withdrawn": round(float(c['total_withdrawn'] or 0), 2),
                "max_eligible_cashout": round(float(c['total_deposited'] or 0) * max_multiplier, 2),
                "is_suspicious": c['is_suspicious'],
                "withdraw_locked": c['withdraw_locked']
            } for c in client_risk],
            "game_risk": [{
                "game": g['game_name'],
                "display_name": g['display_name'],
                "active_players": g['active_players'] or 0,
                "total_in": round(float(g['total_in'] or 0), 2),
                "total_out": round(float(g['total_out'] or 0), 2),
                "net_profit": round(float(g['total_in'] or 0) - float(g['total_out'] or 0), 2),
                "bonus_given": round(float(g['bonus_given'] or 0), 2),
                "voided": round(float(g['voided'] or 0), 2)
            } for g in game_risk]
        }
    }


# ==================== LAYER 4: ENTITY ANALYTICS ====================

@router.get("/client/{user_id}", summary="Client Analytics Detail")
async def get_client_analytics(
    request: Request,
    user_id: str,
    authorization: str = Header(...)
):
    """
    Client-level Analytics for Client Detail page Analytics tab
    """
    auth = await require_admin_access(request, authorization)
    
    # Get user info
    user = await fetch_one("""
        SELECT user_id, username, display_name,
               real_balance, bonus_balance, play_credits,
               total_deposited, total_withdrawn,
               withdraw_locked, is_suspicious
        FROM users WHERE user_id = $1
    """, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get system settings
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    
    # Lifetime stats from orders
    lifetime = await fetch_one("""
        SELECT 
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED'), 0) as lifetime_deposits,
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED'), 0) as lifetime_withdrawals,
            COALESCE(SUM(bonus_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as lifetime_bonus,
            COALESCE(SUM(void_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as lifetime_void,
            COUNT(*) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED') as deposit_count,
            COUNT(*) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED') as withdrawal_count
        FROM orders WHERE user_id = $1
    """, user_id)
    
    # Calculate max eligible cashout
    total_deposited = float(user['total_deposited'] or 0)
    current_balance = float(user['real_balance'] or 0) + float(user['bonus_balance'] or 0)
    max_eligible = min(current_balance, total_deposited * max_multiplier)
    
    # Expected void if withdrawn now
    # Void = bonus that would be forfeited
    expected_void = float(user['bonus_balance'] or 0)
    
    return {
        "user_id": user_id,
        "username": user['username'],
        "balances": {
            "cash": round(float(user['real_balance'] or 0), 2),
            "bonus": round(float(user['bonus_balance'] or 0), 2),
            "play_credits": round(float(user['play_credits'] or 0), 2),
            "total": round(current_balance, 2)
        },
        "withdrawal_status": {
            "locked": user['withdraw_locked'],
            "withdrawable": round(float(user['real_balance'] or 0), 2) if not user['withdraw_locked'] else 0,
            "locked_amount": round(current_balance if user['withdraw_locked'] else float(user['bonus_balance'] or 0), 2)
        },
        "cashout_projection": {
            "max_eligible_cashout": round(max_eligible, 2),
            "expected_void_if_withdrawn": round(expected_void, 2),
            "max_multiplier": max_multiplier,
            "total_deposited": round(total_deposited, 2)
        },
        "lifetime_stats": {
            "deposits": round(float(lifetime['lifetime_deposits'] or 0), 2),
            "withdrawals": round(float(lifetime['lifetime_withdrawals'] or 0), 2),
            "bonus_received": round(float(lifetime['lifetime_bonus'] or 0), 2),
            "voided": round(float(lifetime['lifetime_void'] or 0), 2),
            "deposit_count": lifetime['deposit_count'] or 0,
            "withdrawal_count": lifetime['withdrawal_count'] or 0
        },
        "risk_flags": {
            "is_suspicious": user['is_suspicious'],
            "withdraw_locked": user['withdraw_locked']
        }
    }


@router.get("/game/{game_name}", summary="Game Analytics Detail")
async def get_game_analytics(
    request: Request,
    game_name: str,
    authorization: str = Header(...)
):
    """
    Game-level Analytics for Game Detail
    """
    auth = await require_admin_access(request, authorization)
    
    # Get game info
    game = await fetch_one("SELECT * FROM games WHERE game_name = $1", game_name)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get system settings
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    max_multiplier = float(settings.get('max_cashout_multiplier', 3) if settings else 3)
    
    # Analytics
    analytics = await fetch_one("""
        SELECT 
            COALESCE(SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED'), 0) as total_deposits,
            COALESCE(SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED'), 0) as total_withdrawals,
            COALESCE(SUM(bonus_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_issued,
            COALESCE(SUM(bonus_consumed) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_converted,
            COALESCE(SUM(void_amount) FILTER (WHERE status = 'APPROVED_EXECUTED'), 0) as bonus_voided,
            COUNT(DISTINCT user_id) FILTER (WHERE status = 'APPROVED_EXECUTED') as total_players,
            COUNT(DISTINCT user_id) FILTER (WHERE status = 'APPROVED_EXECUTED' AND created_at >= NOW() - INTERVAL '7 days') as active_7d
        FROM orders WHERE game_name = $1
    """, game_name)
    
    # Average balance per player
    avg_balance = await fetch_one("""
        SELECT 
            AVG(u.real_balance + u.bonus_balance) as avg_balance,
            COUNT(DISTINCT u.user_id) as player_count
        FROM users u
        JOIN orders o ON u.user_id = o.user_id
        WHERE o.game_name = $1 AND u.role = 'user'
    """, game_name)
    
    # Calculate net profit
    deposits = float(analytics['total_deposits'] or 0)
    withdrawals = float(analytics['total_withdrawals'] or 0)
    
    return {
        "game_name": game_name,
        "display_name": game['display_name'],
        "is_active": game['is_active'],
        "financial": {
            "total_deposits": round(deposits, 2),
            "total_withdrawals": round(withdrawals, 2),
            "net_profit": round(deposits - withdrawals, 2),
            "profit_margin_percent": round((deposits - withdrawals) / deposits * 100 if deposits > 0 else 0, 1)
        },
        "bonus": {
            "issued": round(float(analytics['bonus_issued'] or 0), 2),
            "converted": round(float(analytics['bonus_converted'] or 0), 2),
            "voided": round(float(analytics['bonus_voided'] or 0), 2)
        },
        "players": {
            "total": analytics['total_players'] or 0,
            "active_7d": analytics['active_7d'] or 0,
            "avg_balance": round(float(avg_balance['avg_balance'] or 0), 2)
        },
        "exposure": {
            "max_probable_cashout": round(deposits * max_multiplier - withdrawals, 2)
        }
    }


# ==================== LAYER 5: ADVANCED EFFICIENCY METRICS ====================

@router.get("/advanced-metrics", summary="Advanced Efficiency Metrics")
async def get_advanced_metrics(
    request: Request,
    days: int = 30,
    authorization: str = Header(...)
):
    """
    Advanced metrics for Reports → Advanced Analytics
    """
    auth = await require_admin_access(request, authorization)
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Bonus Conversion Ratio
    bonus_stats = await fetch_one("""
        SELECT 
            COALESCE(SUM(bonus_amount), 0) as issued,
            COALESCE(SUM(bonus_consumed), 0) as converted
        FROM orders WHERE status = 'APPROVED_EXECUTED' AND created_at >= $1
    """, since)
    
    bonus_conversion = (float(bonus_stats['converted'] or 0) / float(bonus_stats['issued'] or 1)) * 100
    
    # Average time from deposit to withdrawal
    avg_time = await fetch_one("""
        WITH deposit_times AS (
            SELECT user_id, MIN(approved_at) as first_deposit
            FROM orders 
            WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED' AND approved_at >= $1
            GROUP BY user_id
        ),
        withdrawal_times AS (
            SELECT user_id, MIN(approved_at) as first_withdrawal
            FROM orders 
            WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED' AND approved_at >= $1
            GROUP BY user_id
        )
        SELECT AVG(EXTRACT(EPOCH FROM (w.first_withdrawal - d.first_deposit)) / 3600) as avg_hours
        FROM deposit_times d
        JOIN withdrawal_times w ON d.user_id = w.user_id
        WHERE w.first_withdrawal > d.first_deposit
    """, since)
    
    # % Clients never withdrawing
    total_depositors = await fetch_one("""
        SELECT COUNT(DISTINCT user_id) as count
        FROM orders 
        WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED' AND created_at >= $1
    """, since)
    
    withdrawers = await fetch_one("""
        SELECT COUNT(DISTINCT user_id) as count
        FROM orders 
        WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED' AND created_at >= $1
    """, since)
    
    never_withdrawn_pct = 100 - (float(withdrawers['count'] or 0) / float(total_depositors['count'] or 1)) * 100
    
    # % Bonus-only players (only have bonus balance, no cash)
    bonus_only = await fetch_one("""
        SELECT 
            COUNT(*) FILTER (WHERE real_balance <= 0 AND bonus_balance > 0) as bonus_only,
            COUNT(*) as total
        FROM users WHERE role = 'user' AND is_active = TRUE
    """)
    
    bonus_only_pct = (float(bonus_only['bonus_only'] or 0) / float(bonus_only['total'] or 1)) * 100
    
    # Average multiplier reached (payout / deposit ratio)
    multiplier_data = await fetch_one("""
        WITH user_totals AS (
            SELECT 
                user_id,
                SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED') as deposited,
                SUM(payout_amount) FILTER (WHERE order_type = 'withdrawal' AND status = 'APPROVED_EXECUTED') as withdrawn
            FROM orders
            WHERE created_at >= $1
            GROUP BY user_id
            HAVING SUM(amount) FILTER (WHERE order_type = 'deposit' AND status = 'APPROVED_EXECUTED') > 0
        )
        SELECT AVG(withdrawn / NULLIF(deposited, 0)) as avg_multiplier
        FROM user_totals
        WHERE withdrawn > 0
    """, since)
    
    return {
        "period_days": days,
        "metrics": {
            "bonus_conversion_ratio": {
                "value": round(bonus_conversion, 1),
                "unit": "percent",
                "description": "Percentage of bonus issued that was converted to cash"
            },
            "avg_multiplier_reached": {
                "value": round(float(multiplier_data['avg_multiplier'] or 0), 2),
                "unit": "x",
                "description": "Average withdrawal / deposit ratio for users who withdrew"
            },
            "avg_deposit_to_withdrawal_hours": {
                "value": round(float(avg_time['avg_hours'] or 0), 1),
                "unit": "hours",
                "description": "Average time between first deposit and first withdrawal"
            },
            "clients_never_withdrawing_pct": {
                "value": round(never_withdrawn_pct, 1),
                "unit": "percent",
                "description": "Percentage of depositing clients who never withdrew"
            },
            "bonus_only_players_pct": {
                "value": round(bonus_only_pct, 1),
                "unit": "percent",
                "description": "Percentage of active clients with only bonus balance"
            }
        }
    }
