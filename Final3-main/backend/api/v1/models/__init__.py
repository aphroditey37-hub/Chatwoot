"""
API v1 Models Package
"""
from .schemas import (
    # Base
    APIResponse,
    PaginatedResponse,
    APIError,
    
    # Auth
    AuthCredentials,
    SignupRequest,
    SignupResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    MagicLinkConsumeResponse,
    TokenValidationResponse,
    
    # Referral
    ValidateReferralRequest,
    ValidateReferralResponse,
    ReferralPerk,
    
    # Order
    OrderValidateRequest,
    OrderValidateResponse,
    OrderCreateRequest,
    OrderCreateResponse,
    OrderResponse,
    OrderListRequest,
    BonusCalculation,
    OrderStatus,
    
    # Webhook
    WebhookRegisterRequest,
    WebhookRegisterResponse,
    WebhookResponse,
    WebhookPayload,
    WebhookDeliveryResponse,
    WebhookEvent,
    
    # Game
    GameInfo,
    GameListResponse,
)

__all__ = [
    "APIResponse",
    "PaginatedResponse", 
    "APIError",
    "AuthCredentials",
    "SignupRequest",
    "SignupResponse",
    "MagicLinkRequest",
    "MagicLinkResponse",
    "MagicLinkConsumeResponse",
    "TokenValidationResponse",
    "ValidateReferralRequest",
    "ValidateReferralResponse",
    "ReferralPerk",
    "OrderValidateRequest",
    "OrderValidateResponse",
    "OrderCreateRequest",
    "OrderCreateResponse",
    "OrderResponse",
    "OrderListRequest",
    "BonusCalculation",
    "OrderStatus",
    "WebhookRegisterRequest",
    "WebhookRegisterResponse",
    "WebhookResponse",
    "WebhookPayload",
    "WebhookDeliveryResponse",
    "WebhookEvent",
    "GameInfo",
    "GameListResponse",
]
