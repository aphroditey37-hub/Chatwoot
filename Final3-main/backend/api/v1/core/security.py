"""
API v1 Security Utilities
Password hashing, token generation, HMAC signing, rate limiting
"""
import hashlib
import hmac
import secrets
import string
import time
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
from jose import JWTError, jwt
import asyncpg
from .config import get_api_settings, ErrorCodes

settings = get_api_settings()

# In-memory rate limiter (use Redis in production)
_rate_limit_store: Dict[str, list] = {}
_brute_force_store: Dict[str, Dict] = {}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def generate_referral_code(length: int = 8) -> str:
    """Generate a unique referral code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_magic_link_token() -> str:
    """Generate a secure magic link token"""
    return secrets.token_urlsafe(32)


def generate_session_token() -> str:
    """Generate a session access token"""
    return secrets.token_urlsafe(48)


def generate_idempotency_key() -> str:
    """Generate an idempotency key"""
    return secrets.token_hex(16)


def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def generate_hmac_signature(payload: str, secret: str) -> str:
    """Generate HMAC SHA256 signature for webhook payloads"""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify HMAC SHA256 signature"""
    expected = generate_hmac_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


def check_rate_limit(identifier: str) -> Tuple[bool, int]:
    """
    Check if request is rate limited.
    Returns (is_allowed, remaining_requests)
    """
    now = time.time()
    window_start = now - settings.rate_limit_window_seconds
    
    # Clean old entries
    if identifier in _rate_limit_store:
        _rate_limit_store[identifier] = [
            t for t in _rate_limit_store[identifier] if t > window_start
        ]
    else:
        _rate_limit_store[identifier] = []
    
    # Check limit
    current_count = len(_rate_limit_store[identifier])
    if current_count >= settings.rate_limit_requests:
        return False, 0
    
    # Record request
    _rate_limit_store[identifier].append(now)
    return True, settings.rate_limit_requests - current_count - 1


def check_brute_force(identifier: str) -> Tuple[bool, Optional[int]]:
    """
    Check if account is locked due to brute force attempts.
    Returns (is_allowed, lockout_remaining_seconds)
    """
    now = time.time()
    
    if identifier not in _brute_force_store:
        return True, None
    
    record = _brute_force_store[identifier]
    
    # Check if locked
    if record.get('locked_until'):
        if now < record['locked_until']:
            remaining = int(record['locked_until'] - now)
            return False, remaining
        else:
            # Lockout expired, reset
            del _brute_force_store[identifier]
            return True, None
    
    return True, None


def record_failed_attempt(identifier: str):
    """Record a failed authentication attempt"""
    now = time.time()
    
    if identifier not in _brute_force_store:
        _brute_force_store[identifier] = {'attempts': [], 'locked_until': None}
    
    record = _brute_force_store[identifier]
    
    # Clean old attempts (within last hour)
    record['attempts'] = [t for t in record['attempts'] if t > now - 3600]
    record['attempts'].append(now)
    
    # Check if should lock
    if len(record['attempts']) >= settings.brute_force_max_attempts:
        record['locked_until'] = now + (settings.brute_force_lockout_minutes * 60)


def clear_failed_attempts(identifier: str):
    """Clear failed attempts after successful login"""
    if identifier in _brute_force_store:
        del _brute_force_store[identifier]


def sanitize_input(value: str, max_length: int = 255) -> str:
    """Sanitize user input"""
    if not value:
        return ""
    return value.strip()[:max_length]
