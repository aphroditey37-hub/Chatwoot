"""
API v1 Pydantic Models
Request/Response schemas for the referral-based gaming order system
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Import canonical status from order_types (single source of truth)
from .order_types import OrderStatus, OrderType


# ==================== ENUMS ====================

class WebhookEvent(str, Enum):
    ORDER_CREATED = "order.created"
    ORDER_CONFIRMED = "order.confirmed"
    ORDER_COMPLETED = "order.completed"
    ORDER_CANCELLED = "order.cancelled"


# ==================== BASE MODELS ====================

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now())


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    success: bool
    data: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_more: bool


# ==================== AUTH MODELS ====================

class AuthCredentials(BaseModel):
    """Base auth credentials required for all authenticated endpoints"""
    username: str = Field(..., min_length=3, max_length=50, description="Username for authentication")
    password: str = Field(..., min_length=1, description="Password for authentication")


class SignupRequest(BaseModel):
    """User signup request"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    referred_by_code: Optional[str] = Field(None, max_length=20)
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscores allowed)')
        return v.lower()


class SignupResponse(BaseModel):
    """User signup response"""
    success: bool
    message: str
    user_id: str
    username: str
    display_name: str
    referral_code: str
    referred_by_code: Optional[str] = None


class MagicLinkRequest(AuthCredentials):
    """Request magic link"""
    pass


class MagicLinkResponse(BaseModel):
    """Magic link response"""
    success: bool
    message: str
    magic_link: Optional[str] = None
    expires_in_seconds: int


class MagicLinkConsumeResponse(BaseModel):
    """Magic link consumption response"""
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in_seconds: Optional[int] = None
    user: Optional[Dict[str, Any]] = None


class TokenValidationResponse(BaseModel):
    """Token validation response"""
    valid: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    referral_code: Optional[str] = None
    role: Optional[str] = None
    expires_at: Optional[datetime] = None
    user: Optional[Dict[str, Any]] = None


# ==================== REFERRAL MODELS ====================

class ValidateReferralRequest(AuthCredentials):
    """Validate referral code request"""
    referral_code: str = Field(..., min_length=4, max_length=20)


class ReferralPerk(BaseModel):
    """Referral perk details"""
    perk_id: Optional[str] = None
    percent_bonus: float = 0.0
    flat_bonus: float = 0.0
    max_bonus: Optional[float] = None
    min_amount: Optional[float] = None
    valid_until: Optional[datetime] = None
    applicable_games: Optional[List[str]] = None


class ValidateReferralResponse(BaseModel):
    """Validate referral code response"""
    success: bool
    message: str
    valid: bool
    referrer_username: Optional[str] = None
    referrer_display_name: Optional[str] = None
    perks: Optional[List[ReferralPerk]] = None
    error_code: Optional[str] = None


# ==================== ORDER MODELS ====================

class OrderValidateRequest(AuthCredentials):
    """Order validation request"""
    game_name: str = Field(..., min_length=1, max_length=100)
    recharge_amount: float = Field(..., gt=0)
    referral_code: Optional[str] = Field(None, max_length=20)


class BonusCalculation(BaseModel):
    """Bonus calculation details"""
    base_amount: float
    percent_bonus: float = 0.0
    flat_bonus: float = 0.0
    referral_bonus: float = 0.0
    total_bonus: float
    rule_applied: str
    rule_details: Dict[str, Any] = {}


class OrderValidateResponse(BaseModel):
    """Order validation response"""
    success: bool
    message: str
    valid: bool
    game_name: Optional[str] = None
    game_display_name: Optional[str] = None
    recharge_amount: Optional[float] = None
    bonus_amount: Optional[float] = None
    total_amount: Optional[float] = None
    bonus_calculation: Optional[BonusCalculation] = None
    error_code: Optional[str] = None


class OrderCreateRequest(AuthCredentials):
    """Order creation request"""
    game_name: str = Field(..., min_length=1, max_length=100)
    recharge_amount: float = Field(..., gt=0)
    referral_code: Optional[str] = Field(None, max_length=20)
    metadata: Optional[Dict[str, Any]] = None


class OrderResponse(BaseModel):
    """Order response"""
    model_config = ConfigDict(extra='ignore')
    
    order_id: str
    username: str
    game_name: str
    game_display_name: Optional[str] = None
    recharge_amount: float
    bonus_amount: float
    total_amount: float
    referral_code: Optional[str] = None
    referral_bonus_applied: bool = False
    rule_applied: Optional[str] = None
    status: OrderStatus
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class OrderCreateResponse(BaseModel):
    """Order creation response"""
    success: bool
    message: str
    order: Optional[OrderResponse] = None
    error_code: Optional[str] = None


class OrderListRequest(AuthCredentials):
    """Order list request"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    status: Optional[OrderStatus] = None


# ==================== WEBHOOK MODELS ====================

class WebhookRegisterRequest(AuthCredentials):
    """Webhook registration request"""
    webhook_url: str = Field(..., min_length=10, max_length=500)
    subscribed_events: List[WebhookEvent] = [WebhookEvent.ORDER_CREATED]
    signing_secret: str = Field(..., min_length=16, max_length=255)
    
    @field_validator('webhook_url')
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Webhook URL must start with http:// or https://')
        return v


class WebhookResponse(BaseModel):
    """Webhook response"""
    webhook_id: str
    webhook_url: str
    subscribed_events: List[str]
    is_active: bool
    created_at: datetime


class WebhookRegisterResponse(BaseModel):
    """Webhook registration response"""
    success: bool
    message: str
    webhook: Optional[WebhookResponse] = None
    error_code: Optional[str] = None


class WebhookPayload(BaseModel):
    """Webhook payload"""
    event: str
    timestamp: datetime
    data: Dict[str, Any]


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery status"""
    delivery_id: str
    webhook_id: str
    event_type: str
    status: str
    attempt_count: int
    delivered_at: Optional[datetime] = None
    created_at: datetime


# ==================== GAME MODELS ====================

class GameInfo(BaseModel):
    """Game information"""
    game_id: str
    game_name: str
    display_name: str
    description: Optional[str] = None
    min_recharge_amount: float
    max_recharge_amount: float
    bonus_rules: Dict[str, Any] = {}
    is_active: bool


class GameListResponse(BaseModel):
    """Game list response"""
    success: bool
    games: List[GameInfo]


# ==================== ERROR MODELS ====================

class APIError(BaseModel):
    """API Error response"""
    success: bool = False
    message: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
