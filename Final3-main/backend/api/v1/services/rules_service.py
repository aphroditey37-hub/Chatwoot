"""
API v1 Rules Service
AUTHORITATIVE Rules Engine with CLIENT > GAME > GLOBAL priority
Handles deposit rules, withdrawal/cashout rules, and bonus calculations
"""
import json
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

from ..core.database import fetch_one, fetch_all, execute


# ==================== RULE PRIORITY CONSTANTS ====================
SCOPE_PRIORITY = {
    'client': 100,   # Highest priority
    'game': 50,      # Medium priority
    'global': 0      # Lowest priority (fallback)
}


# ==================== HELPER FUNCTIONS ====================

async def get_system_settings() -> Dict[str, Any]:
    """Get global system settings"""
    settings = await fetch_one("SELECT * FROM system_settings WHERE id = 'global'")
    if not settings:
        return {
            'signup_bonus': 0.0,
            'default_deposit_bonus': 0.0,
            'default_referral_bonus': 5.0,
            'deposit_block_balance': 5.0,  # Block deposits if game balance > $5
            'min_cashout_multiplier': 1.0,
            'max_cashout_multiplier': 3.0,
            'auto_approve_deposits': False,
            'auto_approve_withdrawals': False
        }
    return settings


async def get_game_rules(game_name: str) -> Dict[str, Any]:
    """Get game-specific rules"""
    game = await fetch_one(
        "SELECT * FROM games WHERE game_name = $1",
        game_name.lower()
    )
    if not game:
        return None
    
    deposit_rules = game.get('deposit_rules', {})
    if isinstance(deposit_rules, str):
        deposit_rules = json.loads(deposit_rules)
    
    withdrawal_rules = game.get('withdrawal_rules', {})
    if isinstance(withdrawal_rules, str):
        withdrawal_rules = json.loads(withdrawal_rules)
    
    bonus_rules = game.get('bonus_rules', {})
    if isinstance(bonus_rules, str):
        bonus_rules = json.loads(bonus_rules)
    
    return {
        'game_id': game['game_id'],
        'game_name': game['game_name'],
        'display_name': game['display_name'],
        'min_deposit_amount': game.get('min_deposit_amount', 10.0),
        'max_deposit_amount': game.get('max_deposit_amount', 10000.0),
        'min_withdrawal_amount': game.get('min_withdrawal_amount', 20.0),
        'max_withdrawal_amount': game.get('max_withdrawal_amount', 10000.0),
        'deposit_rules': deposit_rules,
        'withdrawal_rules': withdrawal_rules,
        'bonus_rules': bonus_rules
    }


async def get_client_rules(user_id: str) -> Dict[str, Any]:
    """Get client-specific rules/overrides"""
    user = await fetch_one(
        "SELECT user_id, username, bonus_percentage, signup_bonus_claimed, "
        "deposit_count, total_deposited, total_withdrawn, real_balance, bonus_balance, "
        "deposit_locked, withdraw_locked FROM users WHERE user_id = $1",
        user_id
    )
    if not user:
        return None
    
    # Get any client-specific rules from rules table
    client_rules = await fetch_all(
        "SELECT * FROM rules WHERE scope = 'client' AND scope_id = $1 AND is_active = TRUE "
        "ORDER BY priority DESC",
        user_id
    )
    
    return {
        'user_id': user['user_id'],
        'username': user['username'],
        'bonus_percentage_override': user.get('bonus_percentage'),
        'signup_bonus_claimed': user.get('signup_bonus_claimed', False),
        'deposit_count': user.get('deposit_count', 0),
        'total_deposited': user.get('total_deposited', 0.0),
        'total_withdrawn': user.get('total_withdrawn', 0.0),
        'real_balance': user.get('real_balance', 0.0),
        'bonus_balance': user.get('bonus_balance', 0.0),
        'deposit_locked': user.get('deposit_locked', False),
        'withdraw_locked': user.get('withdraw_locked', False),
        'custom_rules': [{
            'rule_id': r['rule_id'],
            'rule_type': r['rule_type'],
            'conditions': json.loads(r['conditions']) if isinstance(r['conditions'], str) else r['conditions'],
            'actions': json.loads(r['actions']) if isinstance(r['actions'], str) else r['actions'],
            'priority': r['priority']
        } for r in client_rules]
    }


async def get_last_deposit(user_id: str, game_name: str) -> Optional[Dict]:
    """Get the user's last approved deposit for a specific game"""
    return await fetch_one('''
        SELECT * FROM orders 
        WHERE user_id = $1 AND game_name = $2 AND order_type = 'deposit' AND status = 'APPROVED_EXECUTED'
        ORDER BY approved_at DESC LIMIT 1
    ''', user_id, game_name.lower())


# ==================== DEPOSIT RULES ====================

async def resolve_deposit_rules(
    user_id: str,
    game_name: str,
    amount: float,
    current_game_balance: Optional[float] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Resolve deposit rules with CLIENT > GAME > GLOBAL priority
    
    BUSINESS RULE: Block deposit if GAME balance exceeds threshold.
    NOT wallet balance - GAME balance from provider or local tracking.
    
    Args:
        current_game_balance: The user's balance IN THE GAME (from API or game_accounts table)
                             If None, rule is skipped (caller should provide)
    
    Returns (eligible, result_dict)
    """
    # Get all rule sources
    system_settings = await get_system_settings()
    game_rules = await get_game_rules(game_name)
    client_rules = await get_client_rules(user_id)
    
    if not game_rules:
        return False, {
            'eligible': False,
            'message': f"Game '{game_name}' not found",
            'error_code': 'E3002'
        }
    
    if not client_rules:
        return False, {
            'eligible': False,
            'message': 'User not found',
            'error_code': 'E1002'
        }
    
    # Check client-level locks
    if client_rules.get('deposit_locked'):
        return False, {
            'eligible': False,
            'message': 'Deposits are locked for this account',
            'error_code': 'E3010',
            'rule_applied': 'client_lock'
        }
    
    # Resolve limits with priority: CLIENT > GAME > GLOBAL
    min_amount = game_rules['min_deposit_amount']
    max_amount = game_rules['max_deposit_amount']
    
    # Get block threshold from game-specific rules first, then system default
    game_deposit_rules = game_rules.get('deposit_rules', {})
    block_threshold = game_deposit_rules.get(
        'block_if_balance_above',
        system_settings.get('deposit_block_balance', 5.0)
    )
    
    # Check client-specific rule overrides (highest priority)
    for rule in client_rules.get('custom_rules', []):
        if rule['rule_type'] == 'deposit':
            conditions = rule.get('conditions', {})
            if 'min_amount' in conditions:
                min_amount = conditions['min_amount']
            if 'max_amount' in conditions:
                max_amount = conditions['max_amount']
            if 'block_if_balance_above' in conditions:
                block_threshold = conditions['block_if_balance_above']
    
    # Validate amount
    if amount < min_amount:
        return False, {
            'eligible': False,
            'message': f'Amount ${amount:.2f} is below minimum ${min_amount:.2f}',
            'error_code': 'E3003',
            'min_amount': min_amount,
            'max_amount': max_amount
        }
    
    if amount > max_amount:
        return False, {
            'eligible': False,
            'message': f'Amount ${amount:.2f} is above maximum ${max_amount:.2f}',
            'error_code': 'E3004',
            'min_amount': min_amount,
            'max_amount': max_amount
        }
    
    # CRITICAL RULE: Block deposit if GAME balance > threshold
    # This uses GAME balance (from provider/game_accounts), NOT wallet balance
    if current_game_balance is not None and current_game_balance > block_threshold:
        return False, {
            'eligible': False,
            'message': f'Cannot deposit when game balance (${current_game_balance:.2f}) exceeds ${block_threshold:.2f}. Please redeem excess funds first.',
            'error_code': 'E3011',
            'rule_applied': 'game_balance_block',
            'current_game_balance': current_game_balance,
            'block_threshold': block_threshold
        }
    
    return True, {
        'eligible': True,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'block_threshold': block_threshold,
        'current_game_balance': current_game_balance,
        'rules_applied': ['game_limits', 'game_balance_check']
    }


# ==================== WITHDRAWAL/CASHOUT RULES ====================

async def resolve_withdrawal_rules(
    user_id: str,
    game_name: str,
    requested_amount: Optional[float] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Resolve withdrawal/cashout rules with CLIENT > GAME > GLOBAL priority
    
    Key rules:
    - Min/Max cashout is based on multipliers of LAST DEPOSIT
    - ALL balance must be redeemed (payout + void)
    - payout_amount = MIN(balance, max_cashout)
    - void_amount = MAX(0, balance - max_cashout)
    
    Returns (eligible, result_dict with payout/void calculations)
    """
    # Get all rule sources
    system_settings = await get_system_settings()
    game_rules = await get_game_rules(game_name)
    client_rules = await get_client_rules(user_id)
    
    if not game_rules:
        return False, {
            'eligible': False,
            'message': f"Game '{game_name}' not found",
            'error_code': 'E3002'
        }
    
    if not client_rules:
        return False, {
            'eligible': False,
            'message': 'User not found',
            'error_code': 'E1002'
        }
    
    # Check client-level locks
    if client_rules.get('withdraw_locked'):
        return False, {
            'eligible': False,
            'message': 'Withdrawals are locked for this account',
            'error_code': 'E3012',
            'rule_applied': 'client_lock'
        }
    
    # Get current balance
    real_balance = float(client_rules['real_balance'])
    bonus_balance = float(client_rules['bonus_balance'])
    total_balance = real_balance + bonus_balance
    
    if total_balance <= 0:
        return False, {
            'eligible': False,
            'message': 'No balance available for withdrawal',
            'error_code': 'E3013',
            'current_balance': total_balance
        }
    
    # Get last deposit for this game to calculate multipliers
    last_deposit = await get_last_deposit(user_id, game_name)
    
    if not last_deposit:
        return False, {
            'eligible': False,
            'message': 'No approved deposit found for this game. You must deposit first.',
            'error_code': 'E3014',
            'rule_applied': 'no_deposit'
        }
    
    last_deposit_amount = float(last_deposit['amount'])
    
    # Resolve multipliers with priority: CLIENT > GAME > GLOBAL
    min_multiplier = system_settings.get('min_cashout_multiplier', 1.0)
    max_multiplier = system_settings.get('max_cashout_multiplier', 3.0)
    
    # Check game-specific withdrawal rules
    game_withdrawal_rules = game_rules.get('withdrawal_rules', {})
    if game_withdrawal_rules:
        min_multiplier = game_withdrawal_rules.get('min_multiplier_of_deposit', min_multiplier)
        max_multiplier = game_withdrawal_rules.get('max_multiplier_of_deposit', max_multiplier)
    
    # Check client-specific rule overrides (highest priority)
    for rule in client_rules.get('custom_rules', []):
        if rule['rule_type'] == 'withdrawal':
            conditions = rule.get('conditions', {})
            if 'min_multiplier_of_deposit' in conditions:
                min_multiplier = conditions['min_multiplier_of_deposit']
            if 'max_multiplier_of_deposit' in conditions:
                max_multiplier = conditions['max_multiplier_of_deposit']
    
    # Calculate cashout limits based on last deposit
    min_cashout = last_deposit_amount * min_multiplier
    max_cashout = last_deposit_amount * max_multiplier
    
    # Check if minimum requirement is met
    if total_balance < min_cashout:
        return False, {
            'eligible': False,
            'message': f'Balance ${total_balance:.2f} is below minimum cashout ${min_cashout:.2f} ({min_multiplier}x of last deposit ${last_deposit_amount:.2f})',
            'error_code': 'E3015',
            'rule_applied': 'min_multiplier',
            'current_balance': total_balance,
            'last_deposit': last_deposit_amount,
            'min_multiplier': min_multiplier,
            'min_cashout': min_cashout,
            'max_multiplier': max_multiplier,
            'max_cashout': max_cashout
        }
    
    # MANDATORY: ALL balance is redeemed
    # Calculate payout and void amounts
    payout_amount = min(total_balance, max_cashout)
    void_amount = max(0, total_balance - max_cashout)
    void_reason = 'EXCEEDS_MAX_CASHOUT' if void_amount > 0 else None
    
    # Calculate consumption order: CASH first, then BONUS
    cash_consumed = min(real_balance, payout_amount)
    bonus_consumed = payout_amount - cash_consumed
    
    # Calculate what gets voided from bonus (excess goes from bonus first)
    bonus_voided = min(bonus_balance - bonus_consumed, void_amount) if void_amount > 0 else 0
    cash_voided = void_amount - bonus_voided if void_amount > bonus_voided else 0
    
    return True, {
        'eligible': True,
        'last_deposit_amount': last_deposit_amount,
        'last_deposit_order_id': last_deposit['order_id'],
        'min_multiplier': min_multiplier,
        'max_multiplier': max_multiplier,
        'min_cashout': round(min_cashout, 2),
        'max_cashout': round(max_cashout, 2),
        'current_balance': {
            'real': round(real_balance, 2),
            'bonus': round(bonus_balance, 2),
            'total': round(total_balance, 2)
        },
        'cashout_calculation': {
            'payout_amount': round(payout_amount, 2),
            'void_amount': round(void_amount, 2),
            'void_reason': void_reason,
            'cash_consumed': round(cash_consumed, 2),
            'bonus_consumed': round(bonus_consumed, 2),
            'cash_voided': round(cash_voided, 2),
            'bonus_voided': round(bonus_voided, 2)
        },
        'explanation': f"Withdrawing ALL balance: ${payout_amount:.2f} payout" + 
                      (f", ${void_amount:.2f} voided ({void_reason})" if void_amount > 0 else ""),
        'rules_applied': ['multiplier_rule', 'full_redemption', 'cash_first_consumption']
    }


# ==================== BONUS ENGINE ====================

async def calculate_deposit_bonus(
    user_id: str,
    game_name: str,
    deposit_amount: float,
    referral_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate bonus for a deposit with priority: CLIENT > REFERRAL > FIRST_DEPOSIT > GAME_DEFAULT
    
    Bonus types:
    1. Signup Bonus (%) - Only on FIRST-EVER deposit (any game)
    2. Regular Deposit Bonus (%)
    3. Referral Bonus (%)
    
    Client-specific bonus OVERRIDES default.
    Bonus does NOT increase cashout multiplier base.
    Bonus IS withdrawable IF multiplier condition is met.
    """
    system_settings = await get_system_settings()
    game_rules = await get_game_rules(game_name)
    client_rules = await get_client_rules(user_id)
    
    if not game_rules or not client_rules:
        return {
            'total_bonus': 0,
            'breakdown': {},
            'error': 'Game or user not found'
        }
    
    bonus_breakdown = {
        'signup_bonus': 0.0,
        'signup_bonus_percent': 0.0,
        'deposit_bonus': 0.0,
        'deposit_bonus_percent': 0.0,
        'referral_bonus': 0.0,
        'referral_bonus_percent': 0.0,
        'client_bonus': 0.0,
        'client_bonus_percent': 0.0
    }
    
    rules_applied = []
    is_first_ever_deposit = client_rules['deposit_count'] == 0
    
    # 1. Check for SIGNUP BONUS (first-ever deposit on ANY game)
    if is_first_ever_deposit and not client_rules['signup_bonus_claimed']:
        signup_bonus_percent = system_settings.get('signup_bonus', 0)
        if signup_bonus_percent > 0:
            bonus_breakdown['signup_bonus'] = deposit_amount * (signup_bonus_percent / 100)
            bonus_breakdown['signup_bonus_percent'] = signup_bonus_percent
            rules_applied.append('signup_bonus')
    
    # 2. Check for CLIENT-SPECIFIC bonus override (highest priority)
    client_bonus_percent = client_rules.get('bonus_percentage_override', 0)
    if client_bonus_percent and client_bonus_percent > 0:
        bonus_breakdown['client_bonus'] = deposit_amount * (client_bonus_percent / 100)
        bonus_breakdown['client_bonus_percent'] = client_bonus_percent
        rules_applied.append('client_override')
    else:
        # 3. Apply GAME DEFAULT bonus
        game_bonus_rules = game_rules.get('bonus_rules', {})
        
        # Check for first-deposit bonus for this game
        is_first_game_deposit = await check_first_game_deposit(user_id, game_name)
        
        if is_first_game_deposit and 'first_deposit' in game_bonus_rules:
            rule = game_bonus_rules['first_deposit']
            percent = rule.get('percent_bonus', 0)
            flat = rule.get('flat_bonus', 0)
            max_cap = rule.get('max_bonus')
            
            bonus = deposit_amount * (percent / 100) + flat
            if max_cap and bonus > max_cap:
                bonus = max_cap
            
            bonus_breakdown['deposit_bonus'] = bonus
            bonus_breakdown['deposit_bonus_percent'] = percent
            rules_applied.append('first_game_deposit')
        elif 'default' in game_bonus_rules:
            rule = game_bonus_rules['default']
            percent = rule.get('percent_bonus', 0)
            flat = rule.get('flat_bonus', 0)
            max_cap = rule.get('max_bonus')
            
            bonus = deposit_amount * (percent / 100) + flat
            if max_cap and bonus > max_cap:
                bonus = max_cap
            
            bonus_breakdown['deposit_bonus'] = bonus
            bonus_breakdown['deposit_bonus_percent'] = percent
            rules_applied.append('game_default')
        else:
            # Use system default
            default_percent = system_settings.get('default_deposit_bonus', 0)
            if default_percent > 0:
                bonus_breakdown['deposit_bonus'] = deposit_amount * (default_percent / 100)
                bonus_breakdown['deposit_bonus_percent'] = default_percent
                rules_applied.append('system_default')
    
    # 4. Check for REFERRAL bonus
    if referral_code:
        referral_bonus = await calculate_referral_bonus(referral_code, game_name, deposit_amount)
        if referral_bonus > 0:
            bonus_breakdown['referral_bonus'] = referral_bonus
            # Calculate percent for display
            bonus_breakdown['referral_bonus_percent'] = (referral_bonus / deposit_amount) * 100
            rules_applied.append('referral')
    
    # Calculate total
    total_bonus = (
        bonus_breakdown['signup_bonus'] +
        bonus_breakdown['deposit_bonus'] +
        bonus_breakdown['referral_bonus'] +
        bonus_breakdown['client_bonus']
    )
    
    return {
        'deposit_amount': deposit_amount,
        'total_bonus': round(total_bonus, 2),
        'total_amount': round(deposit_amount + total_bonus, 2),
        'breakdown': {k: round(v, 2) for k, v in bonus_breakdown.items()},
        'is_first_ever_deposit': is_first_ever_deposit,
        'rules_applied': rules_applied,
        'note': 'Bonus is withdrawable if cashout multiplier requirement is met'
    }


async def check_first_game_deposit(user_id: str, game_name: str) -> bool:
    """Check if this is the user's first deposit for this specific game"""
    existing = await fetch_one('''
        SELECT order_id FROM orders 
        WHERE user_id = $1 AND game_name = $2 AND order_type = 'deposit' AND status = 'APPROVED_EXECUTED'
        LIMIT 1
    ''', user_id, game_name.lower())
    return existing is None


async def calculate_referral_bonus(referral_code: str, game_name: str, amount: float) -> float:
    """Calculate referral bonus from perks"""
    # Get best matching perk
    perk = await fetch_one('''
        SELECT * FROM referral_perks 
        WHERE referral_code = $1 AND is_active = TRUE
        AND (game_name IS NULL OR game_name = $2)
        AND (min_amount IS NULL OR min_amount <= $3)
        AND (valid_until IS NULL OR valid_until > NOW())
        AND (max_uses IS NULL OR current_uses < max_uses)
        ORDER BY 
            CASE WHEN game_name IS NOT NULL THEN 1 ELSE 2 END,
            percent_bonus DESC
        LIMIT 1
    ''', referral_code.upper(), game_name.lower(), amount)
    
    if not perk:
        # Use system default referral bonus
        settings = await get_system_settings()
        default_percent = settings.get('default_referral_bonus', 0)
        return amount * (default_percent / 100)
    
    bonus = amount * (perk['percent_bonus'] / 100) + perk.get('flat_bonus', 0)
    
    if perk.get('max_bonus') and bonus > perk['max_bonus']:
        bonus = perk['max_bonus']
    
    return bonus


# ==================== COMBINED VALIDATION ====================

async def validate_deposit_order(
    user_id: str,
    game_name: str,
    amount: float,
    referral_code: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Complete deposit validation including rules and bonus calculation
    """
    # Check deposit rules
    eligible, rules_result = await resolve_deposit_rules(user_id, game_name, amount)
    
    if not eligible:
        return False, rules_result
    
    # Calculate bonus
    bonus_result = await calculate_deposit_bonus(user_id, game_name, amount, referral_code)
    
    # Get game info
    game_rules = await get_game_rules(game_name)
    
    return True, {
        'valid': True,
        'game_name': game_rules['game_name'],
        'game_display_name': game_rules['display_name'],
        'deposit_amount': amount,
        'bonus_amount': bonus_result['total_bonus'],
        'total_amount': bonus_result['total_amount'],
        'bonus_calculation': bonus_result,
        'rules_applied': rules_result.get('rules_applied', []) + bonus_result.get('rules_applied', []),
        'explanation': f"Deposit ${amount:.2f} + Bonus ${bonus_result['total_bonus']:.2f} = ${bonus_result['total_amount']:.2f}"
    }


async def validate_withdrawal_order(
    user_id: str,
    game_name: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Complete withdrawal validation with cashout calculation
    Returns payout and void amounts based on multiplier rules
    """
    eligible, result = await resolve_withdrawal_rules(user_id, game_name)
    
    if not eligible:
        return False, result
    
    # Get game info
    game_rules = await get_game_rules(game_name)
    
    return True, {
        'valid': True,
        'game_name': game_rules['game_name'],
        'game_display_name': game_rules['display_name'],
        **result
    }
