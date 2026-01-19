"""
API v1 Services Package
"""
from .auth_service import (
    create_user,
    authenticate_user,
    create_magic_link,
    consume_magic_link,
    validate_token,
    get_user_by_username,
    log_audit,
)

from .referral_service import (
    validate_referral_code,
    get_referral_perks,
    get_best_perk_for_order,
    increment_perk_usage,
    check_referral_eligibility,
)

from .order_service import (
    validate_order,
    create_order,
    get_order,
    get_user_orders,
    update_order_status,
    calculate_bonus,
    list_games,
    get_game,
)

from .webhook_service import (
    register_webhook,
    trigger_webhooks,
    get_user_webhooks,
    delete_webhook,
    get_webhook_deliveries,
)

from .rules_service import (
    resolve_deposit_rules,
    resolve_withdrawal_rules,
    calculate_deposit_bonus,
    validate_deposit_order,
    validate_withdrawal_order,
    get_system_settings,
    get_game_rules,
    get_client_rules,
    get_last_deposit,
)

__all__ = [
    # Auth
    "create_user",
    "authenticate_user",
    "create_magic_link",
    "consume_magic_link",
    "validate_token",
    "get_user_by_username",
    "log_audit",
    
    # Referral
    "validate_referral_code",
    "get_referral_perks",
    "get_best_perk_for_order",
    "increment_perk_usage",
    "check_referral_eligibility",
    
    # Order
    "validate_order",
    "create_order",
    "get_order",
    "get_user_orders",
    "update_order_status",
    "calculate_bonus",
    "list_games",
    "get_game",
    
    # Webhook
    "register_webhook",
    "trigger_webhooks",
    "get_user_webhooks",
    "delete_webhook",
    "get_webhook_deliveries",
    
    # Rules Engine
    "resolve_deposit_rules",
    "resolve_withdrawal_rules",
    "calculate_deposit_bonus",
    "validate_deposit_order",
    "validate_withdrawal_order",
    "get_system_settings",
    "get_game_rules",
    "get_client_rules",
    "get_last_deposit",
]
