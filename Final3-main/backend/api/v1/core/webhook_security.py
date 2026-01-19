"""
Webhook Security Module
Provides signature verification, timestamp validation, and replay protection.

PRODUCTION REQUIREMENTS:
- WEBHOOK_SIGNING_SECRET must be set (>= 32 chars)
- TELEGRAM_WEBHOOK_SECRET must be set if Telegram is used
- No fallback secrets in production
"""
import hashlib
import hmac
import time
import logging
from typing import Optional
from collections import OrderedDict
from threading import Lock

from .config import get_api_settings

logger = logging.getLogger(__name__)

# Load settings
settings = get_api_settings()

# ==================== CONFIGURATION ====================

def _get_telegram_bot_token() -> str:
    """Get Telegram bot token from settings."""
    return settings.telegram_bot_token or ''


def _get_telegram_webhook_secret() -> str:
    """Get Telegram webhook secret from settings."""
    return settings.telegram_webhook_secret or ''


def _get_webhook_signing_secret() -> str:
    """
    Get webhook signing secret from settings.
    
    In production, this must be set and strong.
    In development, falls back to a placeholder (with warning).
    """
    secret = settings.webhook_signing_secret
    
    if settings.is_production:
        if not secret or len(secret) < 32:
            logger.error("WEBHOOK_SIGNING_SECRET not properly configured for production")
            return ''  # Will cause signature verification to fail
        return secret
    
    # Development: allow default but warn
    if secret == 'default-webhook-secret-change-me':
        logger.warning("Using default webhook secret - NOT SAFE FOR PRODUCTION")
    
    return secret


# Timestamp validation window (seconds)
TIMESTAMP_TOLERANCE = 300  # 5 minutes

# Replay protection cache size
REPLAY_CACHE_SIZE = 10000


# ==================== REPLAY PROTECTION ====================

class ReplayProtectionCache:
    """
    Thread-safe LRU cache for storing processed event IDs.
    Prevents replay attacks by rejecting duplicate event IDs.
    """
    
    def __init__(self, max_size: int = REPLAY_CACHE_SIZE):
        self.max_size = max_size
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._lock = Lock()
    
    def is_duplicate(self, event_id: str) -> bool:
        """Check if event ID was already processed."""
        with self._lock:
            if event_id in self._cache:
                return True
            return False
    
    def mark_processed(self, event_id: str) -> None:
        """Mark event ID as processed."""
        with self._lock:
            # Remove oldest if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[event_id] = time.time()
    
    def check_and_mark(self, event_id: str) -> bool:
        """
        Check if duplicate and mark as processed atomically.
        Returns True if this is a NEW event (not a replay).
        Returns False if this is a DUPLICATE (replay attack).
        """
        with self._lock:
            if event_id in self._cache:
                logger.warning(f"Replay attack detected: event_id={event_id}")
                return False
            
            # Remove oldest if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[event_id] = time.time()
            return True
    
    def cleanup_old(self, max_age_seconds: int = 3600) -> int:
        """Remove entries older than max_age_seconds. Returns count removed."""
        cutoff = time.time() - max_age_seconds
        removed = 0
        
        with self._lock:
            keys_to_remove = [k for k, v in self._cache.items() if v < cutoff]
            for key in keys_to_remove:
                del self._cache[key]
                removed += 1
        
        return removed


# Global replay protection caches
telegram_replay_cache = ReplayProtectionCache()
webhook_replay_cache = ReplayProtectionCache()


# ==================== TELEGRAM SECURITY ====================

def compute_telegram_secret_hash(bot_token: str) -> str:
    """
    Compute the secret token hash for Telegram webhook verification.
    Telegram sends this in X-Telegram-Bot-Api-Secret-Token header.
    """
    return hashlib.sha256(bot_token.encode()).hexdigest()[:32]


def verify_telegram_webhook(
    request_data: dict,
    secret_token_header: Optional[str] = None
) -> tuple[bool, str]:
    """
    Verify Telegram webhook request.
    
    Args:
        request_data: The JSON payload from Telegram
        secret_token_header: X-Telegram-Bot-Api-Secret-Token header value
    
    Returns:
        (is_valid, error_message)
    """
    telegram_secret = _get_telegram_webhook_secret()
    
    # Check 1: Secret token verification (if configured)
    if telegram_secret:
        if not secret_token_header:
            return False, "Missing X-Telegram-Bot-Api-Secret-Token header"
        
        # Use constant-time comparison
        if not hmac.compare_digest(secret_token_header, telegram_secret):
            logger.warning("Invalid Telegram webhook secret token")
            return False, "Invalid secret token"
    elif settings.is_production:
        # In production, Telegram secret is required if bot token is set
        if _get_telegram_bot_token():
            logger.error("TELEGRAM_WEBHOOK_SECRET not configured but TELEGRAM_BOT_TOKEN is set")
            return False, "Webhook secret not configured"
    
    # Check 2: Validate update_id exists (basic structure check)
    update_id = request_data.get('update_id')
    if not update_id:
        return False, "Missing update_id in payload"
    
    # Check 3: Replay protection using update_id
    event_id = f"tg_{update_id}"
    if not telegram_replay_cache.check_and_mark(event_id):
        return False, f"Duplicate update_id: {update_id} (replay attack)"
    
    # Check 4: Timestamp validation (if message has date)
    message = request_data.get('message') or request_data.get('callback_query', {}).get('message')
    if message and 'date' in message:
        msg_timestamp = message['date']
        current_timestamp = int(time.time())
        
        if abs(current_timestamp - msg_timestamp) > TIMESTAMP_TOLERANCE:
            logger.warning(f"Telegram message too old: {current_timestamp - msg_timestamp}s")
            return False, "Message timestamp too old"
    
    return True, ""


# ==================== GENERAL WEBHOOK SECURITY ====================

def compute_hmac_signature(payload: bytes, secret: str, algorithm: str = 'sha256') -> str:
    """Compute HMAC signature for webhook payload."""
    if algorithm == 'sha256':
        return hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
    elif algorithm == 'sha1':
        return hmac.new(
            secret.encode(),
            payload,
            hashlib.sha1
        ).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def verify_webhook_signature(
    payload: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None,
    algorithm: str = 'sha256'
) -> tuple[bool, str]:
    """
    Verify webhook HMAC signature.
    
    Args:
        payload: Raw request body bytes
        signature_header: The signature header value (format: "sha256=xxxx" or just "xxxx")
        secret: The signing secret (defaults to WEBHOOK_SIGNING_SECRET)
        algorithm: Hash algorithm (sha256 or sha1)
    
    Returns:
        (is_valid, error_message)
    """
    if secret is None:
        secret = _get_webhook_signing_secret()
    
    if not secret:
        logger.error("Webhook signing secret not configured")
        return False, "Webhook signing secret not configured"
    
    if not signature_header:
        return False, "Missing signature header"
    
    # Parse signature header (handle "sha256=xxxx" format)
    if '=' in signature_header:
        parts = signature_header.split('=', 1)
        algo_prefix = parts[0].lower()
        provided_signature = parts[1]
        
        # Verify algorithm matches
        if algo_prefix not in ('sha256', 'sha1'):
            return False, f"Unsupported signature algorithm: {algo_prefix}"
        algorithm = algo_prefix
    else:
        provided_signature = signature_header
    
    # Compute expected signature
    expected_signature = compute_hmac_signature(payload, secret, algorithm)
    
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, provided_signature):
        logger.warning("Webhook signature verification failed")
        return False, "Invalid signature"
    
    return True, ""


def verify_webhook_timestamp(
    timestamp: Optional[int],
    tolerance_seconds: int = TIMESTAMP_TOLERANCE
) -> tuple[bool, str]:
    """
    Verify webhook timestamp is within acceptable range.
    
    Args:
        timestamp: Unix timestamp from the webhook
        tolerance_seconds: Maximum age in seconds
    
    Returns:
        (is_valid, error_message)
    """
    if timestamp is None:
        return True, ""  # No timestamp provided, skip check
    
    current_time = int(time.time())
    age = abs(current_time - timestamp)
    
    if age > tolerance_seconds:
        logger.warning(f"Webhook timestamp too old: {age}s (max: {tolerance_seconds}s)")
        return False, f"Timestamp too old ({age}s > {tolerance_seconds}s)"
    
    return True, ""


def verify_webhook_replay(
    event_id: str,
    cache: ReplayProtectionCache = webhook_replay_cache
) -> tuple[bool, str]:
    """
    Check for replay attack using event ID.
    
    Args:
        event_id: Unique identifier for this webhook event
        cache: Replay protection cache to use
    
    Returns:
        (is_valid, error_message)
    """
    if not cache.check_and_mark(event_id):
        return False, f"Duplicate event_id: {event_id} (replay attack)"
    
    return True, ""


# ==================== BOT TOKEN HELPER ====================

def get_telegram_bot_token() -> str:
    """Get Telegram bot token from settings."""
    token = _get_telegram_bot_token()
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not configured in environment")
    return token


def get_telegram_chat_id() -> str:
    """Get Telegram chat ID from settings."""
    return settings.telegram_chat_id or ''
