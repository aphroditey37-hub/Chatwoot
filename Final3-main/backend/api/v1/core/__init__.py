"""
API v1 Core Package
"""
from .config import get_api_settings, ErrorCodes, DEFAULT_BONUS_RULES, APIv1Settings
from .security import (
    hash_password, verify_password, generate_referral_code,
    generate_magic_link_token, generate_session_token, generate_idempotency_key,
    create_jwt_token, decode_jwt_token, generate_hmac_signature, verify_hmac_signature,
    check_rate_limit, check_brute_force, record_failed_attempt, clear_failed_attempts,
    sanitize_input
)
from .database import init_api_v1_db, close_api_v1_db, get_pool, fetch_one, fetch_all, execute

__all__ = [
    "get_api_settings", "ErrorCodes", "DEFAULT_BONUS_RULES", "APIv1Settings",
    "hash_password", "verify_password", "generate_referral_code",
    "generate_magic_link_token", "generate_session_token", "generate_idempotency_key",
    "create_jwt_token", "decode_jwt_token", "generate_hmac_signature", "verify_hmac_signature",
    "check_rate_limit", "check_brute_force", "record_failed_attempt", "clear_failed_attempts",
    "sanitize_input",
    "init_api_v1_db", "close_api_v1_db", "get_pool", "fetch_one", "fetch_all", "execute"
]
