"""
API v1 Routes Package - UNIFIED BACKEND
All routes for the Gaming Platform API

Supports feature flags for optional route disabling:
- ENABLE_BOT_ROUTES (default: true)
- ENABLE_ADMIN_ROUTES (default: true)  
- ENABLE_PUBLIC_ROUTES (default: true)
"""
import logging
from fastapi import APIRouter
from ..core.config import get_api_settings

logger = logging.getLogger(__name__)
settings = get_api_settings()

# Core routes (always enabled)
from .auth_routes import router as auth_router
from .referral_routes import router as referral_router
from .order_routes_v2 import router as order_router  # Use v2 with withdrawal support
from .webhook_routes import router as webhook_router
from .identity_routes import router as identity_router
from .payment_routes import router as payment_router
from .analytics_routes import router as analytics_router  # Analytics endpoints
from .portal_routes import router as portal_router  # Client portal enhanced endpoints
from .reward_routes import router as reward_router  # Rewards management
from .wallet_routes import router as wallet_router  # Wallet funding system
from .game_routes import router as game_router  # Game loading (wallet-only)
from .telegram_routes import router as telegram_router  # Multi-bot Telegram system
from .telegram_webhook import router as telegram_webhook_router  # Telegram webhook handler
from .wallet_load_routes import router as wallet_load_router  # Wallet load (no game)
from .withdrawal_routes import router as withdrawal_router  # Withdrawals
from .game_account_routes import router as game_account_router  # Game account management
from .credit_routes import router as credit_router  # Welcome credits
from .promotions_routes import router as promotions_router  # Promotions & banners

# Feature-flagged routes (can be disabled via env)
# Bot routes
if settings.enable_bot_routes:
    from .bot_routes import router as bot_router
else:
    bot_router = None
    logger.info("Bot routes DISABLED via ENABLE_BOT_ROUTES=false")

# Admin routes
if settings.enable_admin_routes:
    from .admin_routes_v2 import router as admin_router  # Use restructured admin
    from .admin_system_routes import router as admin_system_router  # System config endpoints
    from .admin_balance_control import router as admin_balance_router  # Admin balance control
    from .referral_tier_routes import router as referral_tier_router  # Referral tier system
else:
    admin_router = None
    admin_system_router = None
    admin_balance_router = None
    referral_tier_router = None
    logger.info("Admin routes DISABLED via ENABLE_ADMIN_ROUTES=false")

# Public routes
if settings.enable_public_routes:
    from .public_routes import router as public_router  # Public site (no auth)
else:
    public_router = None
    logger.info("Public routes DISABLED via ENABLE_PUBLIC_ROUTES=false")

# Create main v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Include core sub-routers (always enabled)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(identity_router)
api_v1_router.include_router(referral_router)
api_v1_router.include_router(order_router)
api_v1_router.include_router(payment_router)
api_v1_router.include_router(webhook_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(portal_router)  # Client portal
api_v1_router.include_router(reward_router)  # Rewards
api_v1_router.include_router(wallet_router)  # Wallet funding
api_v1_router.include_router(game_router)    # Game loading
api_v1_router.include_router(telegram_router)  # Telegram bots
api_v1_router.include_router(telegram_webhook_router)  # Telegram webhook
api_v1_router.include_router(wallet_load_router)  # Wallet load (Payment IN)
api_v1_router.include_router(withdrawal_router)  # Withdrawals (Payment OUT)
api_v1_router.include_router(game_account_router)  # Game accounts
api_v1_router.include_router(credit_router)  # Welcome credits
api_v1_router.include_router(promotions_router)  # Promotions & banners

# Include feature-flagged routers (if enabled)
if admin_router:
    api_v1_router.include_router(admin_router)
if admin_system_router:
    api_v1_router.include_router(admin_system_router)
if admin_balance_router:
    api_v1_router.include_router(admin_balance_router)
if referral_tier_router:
    api_v1_router.include_router(referral_tier_router)
if bot_router:
    api_v1_router.include_router(bot_router)
if public_router:
    api_v1_router.include_router(public_router)

# DEV-ONLY: Wiring audit routes (never in production)
import os
_env = os.environ.get("ENV", "development").lower()
if _env != "production":
    try:
        from .dev_wiring_audit_routes import router as dev_wiring_router
        api_v1_router.include_router(dev_wiring_router)
        logger.info("DEV: Wiring audit routes ENABLED (ENV=%s)", _env)
    except ImportError as e:
        logger.warning("DEV: Could not load wiring audit routes: %s", e)
else:
    logger.info("PROD: Wiring audit routes DISABLED")

__all__ = ["api_v1_router"]
