"""
API v1 Core Configuration
Production-ready settings for the referral-based gaming order system

SINGLE SOURCE OF TRUTH for all configuration.
Uses Pydantic Settings with env file loading for local/dev only.

PRODUCTION SAFETY:
- All secrets MUST be set explicitly in production
- No insecure defaults are used when ENV=production
- Fail-fast validation prevents startup with misconfigured secrets
"""
import os
import sys
import logging
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Known insecure placeholder strings that MUST NOT be used in production
INSECURE_PLACEHOLDERS = {
    "super-secret-key-change-in-production-v1",
    "system-bot-secret-key-v1",
    "system-bot-secret-key",
    "default-webhook-secret-change-me",
    "change-me",
    "changeme",
    "secret",
    "password",
    "test",
    "dev",
    "development",
    "",
}

MIN_SECRET_LENGTH = 32  # Minimum length for production secrets


class APIv1Settings(BaseSettings):
    """
    API v1 Configuration - Pydantic Settings as single source of truth.
    
    All configuration is loaded from environment variables.
    .env file is loaded only in development for convenience.
    
    PRODUCTION REQUIREMENTS:
    - JWT_SECRET_KEY: >= 32 chars, not a placeholder
    - INTERNAL_API_SECRET: >= 32 chars, not a placeholder  
    - WEBHOOK_SIGNING_SECRET: >= 32 chars, not a placeholder
    - BOT_API_TOKEN: >= 32 chars (for production bot auth)
    - CORS_ORIGINS: specific origins, no "*"
    - TRUSTED_HOSTS: specific hosts, no "*"
    """
    
    # ==================== ENVIRONMENT ====================
    env: str = "development"  # development | staging | production
    
    # ==================== DATABASE ====================
    database_url: str = "postgresql://postgres:postgres@localhost:5432/portal_db"
    
    # Database pool configuration (configurable via env)
    db_pool_min: int = 2
    db_pool_max: int = 10
    db_command_timeout: int = 60
    
    # ==================== JWT Settings ====================
    # DEV DEFAULT: Insecure placeholder - MUST be overridden in production
    jwt_secret_key: str = "super-secret-key-change-in-production-v1"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # ==================== Magic Link ====================
    magic_link_expire_minutes: int = 15
    magic_link_base_url: str = "http://localhost:3000/auth/verify"
    
    # ==================== Rate Limiting ====================
    rate_limit_requests: int = 100  # requests per window
    rate_limit_window_seconds: int = 60
    brute_force_max_attempts: int = 5
    brute_force_lockout_minutes: int = 15
    
    # ==================== Webhook ====================
    webhook_retry_attempts: int = 3
    webhook_retry_delay_seconds: int = 5
    webhook_timeout_seconds: int = 10
    # DEV DEFAULT: Insecure placeholder - MUST be overridden in production
    webhook_signing_secret: str = "default-webhook-secret-change-me"
    
    # ==================== Security ====================
    password_min_length: int = 8
    referral_code_length: int = 8
    
    # ==================== Bot/Internal API ====================
    # DEV DEFAULT: Insecure placeholder - MUST be overridden in production
    internal_api_secret: str = "system-bot-secret-key-v1"
    # Production bot token (static bearer token for bot auth)
    # Must be set in production, token issuance endpoint disabled
    bot_api_token: Optional[str] = None
    
    # ==================== Telegram ====================
    telegram_bot_token: Optional[str] = None
    telegram_webhook_secret: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # ==================== CORS ====================
    cors_origins: str = "*"  # Comma-separated origins - MUST NOT be "*" in production
    
    # ==================== API Documentation ====================
    enable_docs: Optional[bool] = None  # None = auto (disabled in prod, enabled in dev)
    
    # ==================== Trusted Hosts ====================
    trusted_hosts: str = "*"  # Comma-separated hosts - MUST NOT be "*" in production
    
    # ==================== Feature Flags (Router Control) ====================
    enable_bot_routes: bool = True
    enable_admin_routes: bool = True
    enable_public_routes: bool = True
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env.lower() == "production"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.env.lower() == "staging"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env.lower() in ("development", "dev", "local")
    
    def get_cors_origins(self) -> List[str]:
        """
        Parse and return CORS origins safely.
        - Split by comma
        - Trim whitespace
        - Filter empty strings
        """
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def get_trusted_hosts(self) -> List[str]:
        """
        Parse and return trusted hosts.
        - Split by comma
        - Trim whitespace
        - Returns ["*"] for development if not specified
        """
        if not self.trusted_hosts or self.trusted_hosts.strip() == "*":
            if self.is_development:
                return ["*"]  # Allow all in development
            return ["*"]  # Default to allow all if not specified
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]
    
    def should_enable_docs(self) -> bool:
        """
        Determine if API docs should be enabled.
        - Explicit ENABLE_DOCS=true/false takes precedence
        - Default: enabled in dev, disabled in production
        """
        if self.enable_docs is not None:
            return self.enable_docs
        # Default behavior: disabled in production, enabled elsewhere
        return not self.is_production
    
    # ==================== PRODUCTION VALIDATION ====================
    
    def _is_insecure_secret(self, value: Optional[str]) -> bool:
        """Check if a secret value is insecure (placeholder or too short)."""
        if not value:
            return True
        if len(value) < MIN_SECRET_LENGTH:
            return True
        if value.lower() in INSECURE_PLACEHOLDERS:
            return True
        return False
    
    def validate_production_secrets(self) -> List[str]:
        """
        Validate all secrets for production.
        Returns list of error messages for invalid secrets.
        """
        errors = []
        
        # JWT Secret
        if self._is_insecure_secret(self.jwt_secret_key):
            errors.append(
                f"JWT_SECRET_KEY is insecure (must be >= {MIN_SECRET_LENGTH} chars and not a placeholder)"
            )
        
        # Internal API Secret
        if self._is_insecure_secret(self.internal_api_secret):
            errors.append(
                f"INTERNAL_API_SECRET is insecure (must be >= {MIN_SECRET_LENGTH} chars and not a placeholder)"
            )
        
        # Webhook Signing Secret
        if self._is_insecure_secret(self.webhook_signing_secret):
            errors.append(
                f"WEBHOOK_SIGNING_SECRET is insecure (must be >= {MIN_SECRET_LENGTH} chars and not a placeholder)"
            )
        
        # Bot API Token (required for production bot auth)
        if self.enable_bot_routes and self._is_insecure_secret(self.bot_api_token):
            errors.append(
                f"BOT_API_TOKEN is required in production when bot routes are enabled (must be >= {MIN_SECRET_LENGTH} chars)"
            )
        
        # Telegram secrets (if Telegram features are used)
        if self.telegram_bot_token and self._is_insecure_secret(self.telegram_webhook_secret):
            errors.append(
                f"TELEGRAM_WEBHOOK_SECRET is required when TELEGRAM_BOT_TOKEN is set (must be >= {MIN_SECRET_LENGTH} chars)"
            )
        
        return errors
    
    def validate_cors_for_production(self) -> List[str]:
        """
        Validate CORS configuration for production.
        Returns list of error messages.
        """
        errors = []
        origins = self.get_cors_origins()
        
        if not origins:
            errors.append("CORS_ORIGINS cannot be empty in production")
        elif "*" in origins:
            errors.append(
                "CORS_ORIGINS cannot contain '*' in production. "
                "Set CORS_ORIGINS to specific allowed origins (comma-separated)."
            )
        
        return errors
    
    def validate_trusted_hosts_for_production(self) -> List[str]:
        """
        Validate trusted hosts for production.
        Returns list of error messages.
        """
        errors = []
        hosts = self.get_trusted_hosts()
        
        if not hosts:
            errors.append("TRUSTED_HOSTS cannot be empty in production")
        elif "*" in hosts:
            errors.append(
                "TRUSTED_HOSTS cannot contain '*' in production. "
                "Set TRUSTED_HOSTS to specific allowed hosts (comma-separated)."
            )
        
        return errors
    
    def validate_all_for_production(self) -> None:
        """
        Comprehensive production validation.
        Raises RuntimeError with all validation errors if any fail.
        
        CALL THIS AT STARTUP when ENV=production.
        """
        if not self.is_production:
            return  # Skip validation in non-production
        
        all_errors = []
        
        # Validate secrets
        all_errors.extend(self.validate_production_secrets())
        
        # Validate CORS
        all_errors.extend(self.validate_cors_for_production())
        
        # Validate trusted hosts
        all_errors.extend(self.validate_trusted_hosts_for_production())
        
        if all_errors:
            error_msg = (
                "\n\n" + "=" * 60 + "\n"
                "FATAL: Production configuration validation failed!\n"
                "=" * 60 + "\n\n"
                "The following environment variables are misconfigured:\n\n"
            )
            for i, err in enumerate(all_errors, 1):
                error_msg += f"  {i}. {err}\n"
            
            error_msg += (
                "\n" + "=" * 60 + "\n"
                "Fix the above issues and restart the application.\n"
                "See .env.example for required variables.\n"
                "=" * 60 + "\n"
            )
            
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info("Production configuration validated successfully")


@lru_cache()
def get_api_settings() -> APIv1Settings:
    """
    Get cached API settings instance.
    Settings are loaded once and cached for performance.
    """
    return APIv1Settings()


# Bonus Engine Configuration
DEFAULT_BONUS_RULES = {
    "default": {
        "percent_bonus": 5.0,
        "flat_bonus": 0.0,
        "max_bonus": 100.0,
        "min_amount": 10.0,
        "max_amount": 10000.0
    }
}

# Error Codes
class ErrorCodes:
    # Auth Errors (1xxx)
    INVALID_CREDENTIALS = "E1001"
    USER_NOT_FOUND = "E1002"
    USER_ALREADY_EXISTS = "E1003"
    INVALID_TOKEN = "E1004"
    TOKEN_EXPIRED = "E1005"
    ACCOUNT_LOCKED = "E1006"
    RATE_LIMITED = "E1007"
    
    # Referral Errors (2xxx)
    INVALID_REFERRAL_CODE = "E2001"
    EXPIRED_REFERRAL_CODE = "E2002"
    SELF_REFERRAL_NOT_ALLOWED = "E2003"
    REFERRAL_ALREADY_USED = "E2004"
    
    # Order Errors (3xxx)
    GAME_NOT_FOUND = "E3001"
    INVALID_AMOUNT = "E3002"
    AMOUNT_BELOW_MINIMUM = "E3003"
    AMOUNT_ABOVE_MAXIMUM = "E3004"
    DUPLICATE_ORDER = "E3005"
    ORDER_NOT_FOUND = "E3006"
    
    # Webhook Errors (4xxx)
    WEBHOOK_REGISTRATION_FAILED = "E4001"
    WEBHOOK_NOT_FOUND = "E4002"
    INVALID_WEBHOOK_URL = "E4003"
    
    # General Errors (5xxx)
    VALIDATION_ERROR = "E5001"
    INTERNAL_ERROR = "E5002"
    DATABASE_ERROR = "E5003"
