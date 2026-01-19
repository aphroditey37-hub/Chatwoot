"""
API v1 Referral Service
Handles referral code validation and perk management
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from ..models import ReferralPerk


async def validate_referral_code(
    referral_code: str,
    requesting_user_id: str,
    requesting_username: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a referral code and return referrer info with perks.
    Returns (success, data/error)
    """
    referral_code = referral_code.upper().strip()
    
    # Find referrer
    referrer = await fetch_one('''
        SELECT user_id, username, display_name, referral_code, is_active
        FROM users WHERE referral_code = $1
    ''', referral_code)
    
    if not referrer:
        return False, {
            "valid": False,
            "message": "Invalid referral code",
            "error_code": ErrorCodes.INVALID_REFERRAL_CODE
        }
    
    # Check if referrer is active
    if not referrer.get('is_active', True):
        return False, {
            "valid": False,
            "message": "Referral code is no longer active",
            "error_code": ErrorCodes.EXPIRED_REFERRAL_CODE
        }
    
    # Check self-referral
    if referrer['user_id'] == requesting_user_id:
        return False, {
            "valid": False,
            "message": "Cannot use your own referral code",
            "error_code": ErrorCodes.SELF_REFERRAL_NOT_ALLOWED
        }
    
    # Get perks for this referral code
    perks = await get_referral_perks(referral_code)
    
    return True, {
        "valid": True,
        "referrer_username": referrer['username'],
        "referrer_display_name": referrer['display_name'],
        "perks": perks
    }


async def get_referral_perks(referral_code: str, game_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all active perks for a referral code.
    Optionally filter by game.
    """
    now = datetime.now(timezone.utc)
    
    query = '''
        SELECT * FROM referral_perks
        WHERE referral_code = $1
        AND is_active = TRUE
        AND (valid_from IS NULL OR valid_from <= $2)
        AND (valid_until IS NULL OR valid_until > $2)
        AND (max_uses IS NULL OR current_uses < max_uses)
    '''
    params = [referral_code.upper(), now]
    
    if game_name:
        query += " AND (game_name IS NULL OR game_name = $3)"
        params.append(game_name)
    
    rows = await fetch_all(query, *params)
    
    perks = []
    for row in rows:
        perk = ReferralPerk(
            perk_id=row['perk_id'],
            percent_bonus=row.get('percent_bonus', 0.0),
            flat_bonus=row.get('flat_bonus', 0.0),
            max_bonus=row.get('max_bonus'),
            min_amount=row.get('min_amount'),
            valid_until=row.get('valid_until'),
            applicable_games=[row['game_name']] if row.get('game_name') else None
        )
        perks.append(perk.model_dump())
    
    # If no specific perks, return default referral perk
    if not perks:
        perks.append({
            "perk_id": None,
            "percent_bonus": 5.0,  # Default 5% referral bonus
            "flat_bonus": 0.0,
            "max_bonus": None,
            "min_amount": None,
            "valid_until": None,
            "applicable_games": None
        })
    
    return perks


async def get_best_perk_for_order(
    referral_code: str,
    game_name: str,
    amount: float
) -> Optional[Dict[str, Any]]:
    """
    Get the best applicable perk for an order.
    Returns the perk that gives the highest bonus.
    """
    perks = await get_referral_perks(referral_code, game_name)
    
    if not perks:
        return None
    
    best_perk = None
    best_bonus = 0.0
    
    for perk in perks:
        # Check minimum amount
        if perk.get('min_amount') and amount < perk['min_amount']:
            continue
        
        # Calculate potential bonus
        bonus = 0.0
        bonus += amount * (perk.get('percent_bonus', 0) / 100)
        bonus += perk.get('flat_bonus', 0)
        
        # Apply cap
        if perk.get('max_bonus') and bonus > perk['max_bonus']:
            bonus = perk['max_bonus']
        
        if bonus > best_bonus:
            best_bonus = bonus
            best_perk = perk
    
    return best_perk


async def increment_perk_usage(perk_id: str):
    """Increment the usage counter for a perk"""
    if perk_id:
        await execute('''
            UPDATE referral_perks SET current_uses = current_uses + 1 WHERE perk_id = $1
        ''', perk_id)


async def check_referral_eligibility(
    user_id: str,
    referral_code: str
) -> Tuple[bool, str]:
    """
    Check if a user is eligible to use a referral code.
    Returns (eligible, reason)
    """
    # Get user's own referral info
    user = await fetch_one(
        "SELECT referral_code, referred_by_code FROM users WHERE user_id = $1",
        user_id
    )
    
    if not user:
        return False, "User not found"
    
    # Can't use own code
    if user['referral_code'] == referral_code.upper():
        return False, "Cannot use your own referral code"
    
    # Check if user already has a referrer (one-time referral bonus)
    # This is optional - you might allow multiple referral uses
    # if user.get('referred_by_code'):
    #     return False, "You have already used a referral code"
    
    return True, "Eligible"
