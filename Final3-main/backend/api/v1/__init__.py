"""
API v1 Main Module
Referral-Based Gaming Order System API
"""
from .routes import api_v1_router
from .core.database import init_api_v1_db, close_api_v1_db
from .core.config import get_api_settings

__all__ = ["api_v1_router", "init_api_v1_db", "close_api_v1_db", "get_api_settings"]
