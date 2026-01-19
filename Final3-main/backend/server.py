"""
Gaming Platform API - Production-Ready Unified Backend
Single authoritative backend with versioned REST API

Production features:
- Centralized exception handling with safe error responses
- Structured logging with collision-safe correlation IDs
- CORS hardening with production validation
- API docs gating (disabled in production by default)
- Platform security middleware (TrustedHost, security headers)
- Global rate limiting
- Configurable database pool
- Graceful degradation on external service failures
"""
import sys
import logging
import uuid
import base64

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Load environment variables from .env file (development only)
# In production, env vars should be set by the deployment system
from dotenv import load_dotenv
load_dotenv()

# Import API v1 - the ONLY backend
from api.v1 import api_v1_router, init_api_v1_db, close_api_v1_db
from api.v1.core.config import get_api_settings

# Import centralized exception handler and structured logging
from api.v1.core.exception_handler import register_exception_handlers
from api.v1.core.structured_logging import set_correlation_id, generate_correlation_id

# Import middleware
from api.v1.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from api.v1.middleware.security_headers import SecurityHeadersMiddleware
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load settings (Pydantic Settings as single source of truth)
settings = get_api_settings()

# ==================== STARTUP VALIDATION ====================

def validate_production_config():
    """
    Validate critical configuration for production.
    Fail fast with clear errors if misconfigured.
    
    This function is called at module load time for production deployments.
    It validates:
    - All required secrets are set and strong
    - CORS origins are not wildcards
    - Trusted hosts are not wildcards
    """
    logger.info(f"Environment: {settings.env}")
    logger.info("Running production configuration validation...")
    
    # Comprehensive production validation (fails with RuntimeError if invalid)
    settings.validate_all_for_production()
    
    logger.info("✓ Production configuration validated successfully")


# Run validation on module load for production
if settings.is_production:
    validate_production_config()
else:
    logger.info(f"Environment: {settings.env} (skipping strict validation)")


# ==================== CORS CONFIGURATION ====================

def get_cors_config():
    """
    Get CORS configuration with safety checks.
    
    CRITICAL RULES:
    1. Parse origins safely (comma-split, trim whitespace)
    2. Disallow wildcard "*" when allow_credentials=True
    3. Fail fast in production if misconfigured
    """
    origins = settings.get_cors_origins()
    allow_credentials = True
    
    # Security check: wildcard with credentials is dangerous
    if "*" in origins and allow_credentials:
        if settings.is_production:
            # In production, this should have been caught by validate_cors_for_production()
            # But double-check here as a safety net
            raise SystemExit(
                "CRITICAL: Cannot use wildcard '*' CORS origin with credentials in production"
            )
        else:
            # In development, log a warning but allow it
            logger.warning(
                "WARNING: Using wildcard CORS with credentials. "
                "This is insecure and should NOT be used in production."
            )
    
    logger.info(f"CORS origins configured: {origins}")
    return origins, allow_credentials


# ==================== DOCUMENTATION GATING ====================

def get_docs_config():
    """
    Get API documentation configuration.
    
    - Disabled in production by default
    - Can be enabled via ENABLE_DOCS=true
    - Always enabled in development
    """
    enable_docs = settings.should_enable_docs()
    
    if settings.is_production and enable_docs:
        logger.warning("API documentation is ENABLED in production (ENABLE_DOCS=true)")
    elif settings.is_production:
        logger.info("API documentation is DISABLED in production")
    else:
        logger.info("API documentation is ENABLED (development mode)")
    
    return enable_docs


# Get configurations
cors_origins, cors_credentials = get_cors_config()
docs_enabled = get_docs_config()

# ==================== CREATE FASTAPI APP ====================

app = FastAPI(
    title="Gaming Platform API v1",
    description="""
## Production-Ready Gaming Order System API

A unified, production-ready REST API for managing gaming orders with referral bonuses.

**Base URL**: `/api/v1`

### Core Features
- **Authentication**: Magic link + password-based auth with JWT sessions
- **Identity Management**: FB/Chatwoot identity linking and resolution
- **Order System**: Deposit/withdrawal with rule engine validation
- **Bonus Engine**: Per-client, signup, and referral bonuses with caps
- **Telegram Integration**: Payment approval with inline buttons
- **Webhooks**: HMAC-signed notifications for order events

### Authentication
All endpoints (except signup) support:
- `username` + `password` in request body, OR
- `Authorization: Bearer <token>` header (takes precedence)

### Error Codes
- `E1xxx`: Authentication errors
- `E2xxx`: Referral errors
- `E3xxx`: Order errors
- `E4xxx`: Webhook errors
- `E5xxx`: Internal errors
""",
    version="1.0.0",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_tags=[
        {"name": "Authentication", "description": "User signup, magic link login, token management"},
        {"name": "Identity", "description": "External identity resolution and linking (FB/Chatwoot)"},
        {"name": "Referrals", "description": "Referral code validation and perk lookup"},
        {"name": "Orders", "description": "Order validation, creation, and management"},
        {"name": "Payments", "description": "Payment proof upload and verification"},
        {"name": "Webhooks", "description": "Webhook registration and delivery"},
        {"name": "Admin", "description": "Administrative operations"},
        {"name": "Games", "description": "Game catalog and configuration"},
    ]
)

# ==================== MIDDLEWARE STACK ====================
# Order matters: middleware is executed in reverse order of addition
# (last added = first executed)

# 1. Rate Limiter - Global rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 2. Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 3. Trusted Host Middleware
trusted_hosts = settings.get_trusted_hosts()
if trusted_hosts and trusted_hosts != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts
    )
    logger.info(f"TrustedHostMiddleware enabled with hosts: {trusted_hosts}")
else:
    logger.info("TrustedHostMiddleware: allowing all hosts (development mode or not configured)")

# 4. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=cors_credentials,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register centralized exception handlers (replaces manual exception handler)
register_exception_handlers(app)


# ==================== CORRELATION ID MIDDLEWARE ====================

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """
    Add correlation ID to each request for tracing.
    
    Uses collision-safe 22-character base64url-encoded UUID.
    - Accepts X-Correlation-ID header if valid (16+ chars)
    - Generates new ID otherwise
    """
    # Get correlation ID from header or generate new collision-safe one
    incoming_cid = request.headers.get("X-Correlation-ID")
    
    # Validate incoming ID length (must be 16+ chars for collision safety)
    if incoming_cid and len(incoming_cid) >= 16:
        cid = incoming_cid
    else:
        cid = generate_correlation_id()  # 22-char base64url UUID
    
    set_correlation_id(cid)
    request.state.correlation_id = cid
    
    response = await call_next(request)
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = cid
    return response


# ==================== STARTUP AND SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Application startup handler."""
    logger.info(f"Starting Gaming Platform API v1 (ENV={settings.env})")
    
    # Initialize database
    await init_api_v1_db()
    
    # Initialize order lifecycle audit table
    from api.v1.core.order_lifecycle import ensure_audit_table_exists
    await ensure_audit_table_exists()
    
    # Log configuration summary
    logger.info(f"Database pool: min={settings.db_pool_min}, max={settings.db_pool_max}")
    logger.info(f"API docs: {'enabled' if docs_enabled else 'disabled'}")
    logger.info(f"Bot routes: {'enabled' if settings.enable_bot_routes else 'disabled'}")
    logger.info(f"Admin routes: {'enabled' if settings.enable_admin_routes else 'disabled'}")
    logger.info(f"Public routes: {'enabled' if settings.enable_public_routes else 'disabled'}")
    
    logger.info("Application startup complete - API v1 ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown handler."""
    await close_api_v1_db()
    logger.info("Application shutdown complete")


# ==================== HEALTH CHECK ENDPOINTS ====================

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint (legacy path).
    Returns identical payload to /api/v1/health for backward compatibility.
    """
    return {
        "status": "healthy",
        "message": "Gaming Platform API v1",
        "version": "1.0.0",
        "database": "PostgreSQL"
    }


@app.get("/api/v1/health")
async def health_check_v1():
    """
    Health check endpoint (versioned path).
    Returns identical payload to /api/health for consistency.
    """
    return {
        "status": "healthy",
        "message": "Gaming Platform API v1",
        "version": "1.0.0",
        "database": "PostgreSQL"
    }


# ==================== ROOT ENDPOINTS ====================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Gaming Platform API",
        "version": "1.0.0",
        "docs": "/docs" if docs_enabled else "disabled",
        "api": "/api/v1"
    }


@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Gaming Platform API",
        "version": "v1",
        "base_url": "/api/v1",
        "docs": "/docs" if docs_enabled else "disabled"
    }


# ==================== INCLUDE API ROUTER ====================

# Include API v1 router - THE ONLY API
app.include_router(api_v1_router)
