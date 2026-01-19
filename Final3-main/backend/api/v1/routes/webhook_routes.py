"""
API v1 Webhook Routes
Webhook registration and management
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional, List

from ..models import (
    WebhookRegisterRequest, WebhookRegisterResponse,
    WebhookResponse, WebhookDeliveryResponse,
    APIError
)
from ..services import (
    register_webhook as register_webhook_service,
    get_user_webhooks, delete_webhook, get_webhook_deliveries
)
from ..core.config import ErrorCodes
from .dependencies import authenticate_request

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/register",
    response_model=WebhookRegisterResponse,
    responses={
        400: {"model": APIError, "description": "Registration failed"},
        401: {"model": APIError, "description": "Invalid credentials"},
        429: {"model": APIError, "description": "Rate limited"}
    },
    summary="Register a webhook",
    description="""
    Register a webhook URL to receive event notifications.
    
    **Authentication**: Requires username + password OR Bearer token
    
    **Available Events**:
    - `order.created` - Triggered when a new order is created
    - `order.confirmed` - Triggered when an order is confirmed
    - `order.completed` - Triggered when an order is completed
    - `order.cancelled` - Triggered when an order is cancelled
    
    **Webhook Payload**:
    ```json
    {
        "event": "order.created",
        "timestamp": "2024-01-15T12:00:00Z",
        "data": {
            "order_id": "...",
            "username": "...",
            "referral_code": "...",
            "game": "...",
            "amount": 100.00,
            "bonus_amount": 10.00,
            "total_amount": 110.00,
            "created_at": "2024-01-15T12:00:00Z"
        }
    }
    ```
    
    **Security**:
    - Provide a `signing_secret` (min 16 characters)
    - Webhooks are signed with HMAC SHA256
    - Signature header: `X-Webhook-Signature: sha256=<signature>`
    
    **Retry Policy**:
    - 3 retry attempts
    - Exponential backoff (5s, 10s, 20s)
    - Webhook disabled after 10 consecutive failures
    """
)
async def register_webhook(
    request: Request,
    data: WebhookRegisterRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Register a webhook"""
    auth = await authenticate_request(
        request,
        data.username,
        data.password,
        authorization
    )
    
    # Convert events to strings
    events = [e.value for e in data.subscribed_events]
    
    success, result = await register_webhook_service(
        user_id=auth.user_id,
        username=auth.username,
        webhook_url=data.webhook_url,
        subscribed_events=events,
        signing_secret=data.signing_secret
    )
    
    if not success:
        return WebhookRegisterResponse(
            success=False,
            message=result.get('message', 'Registration failed'),
            error_code=result.get('error_code')
        )
    
    webhook = WebhookResponse(
        webhook_id=result['webhook_id'],
        webhook_url=result['webhook_url'],
        subscribed_events=result['subscribed_events'],
        is_active=result['is_active'],
        created_at=result['created_at']
    )
    
    return WebhookRegisterResponse(
        success=True,
        message="Webhook registered successfully",
        webhook=webhook
    )


@router.get(
    "/list",
    response_model=List[WebhookResponse],
    responses={
        401: {"model": APIError, "description": "Invalid credentials"}
    },
    summary="List user webhooks",
    description="Get all webhooks registered by the authenticated user"
)
async def list_webhooks(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List user webhooks"""
    auth = await authenticate_request(request, None, None, authorization)
    
    webhooks = await get_user_webhooks(auth.user_id)
    
    result = []
    for w in webhooks:
        result.append(WebhookResponse(
            webhook_id=w['webhook_id'],
            webhook_url=w['webhook_url'],
            subscribed_events=w['subscribed_events'],
            is_active=w['is_active'],
            created_at=w['created_at']
        ))
    
    return result


@router.delete(
    "/{webhook_id}",
    responses={
        401: {"model": APIError, "description": "Invalid credentials"},
        404: {"model": APIError, "description": "Webhook not found"}
    },
    summary="Delete a webhook",
    description="Deactivate a webhook registration"
)
async def delete_webhook_endpoint(
    request: Request,
    webhook_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete a webhook"""
    auth = await authenticate_request(request, None, None, authorization)
    
    await delete_webhook(auth.user_id, webhook_id)
    
    return {"success": True, "message": "Webhook deleted"}


@router.get(
    "/{webhook_id}/deliveries",
    response_model=List[WebhookDeliveryResponse],
    responses={
        401: {"model": APIError, "description": "Invalid credentials"}
    },
    summary="Get webhook delivery history",
    description="Get the delivery history for a specific webhook"
)
async def list_deliveries(
    request: Request,
    webhook_id: str,
    limit: int = 50,
    authorization: str = Header(..., alias="Authorization")
):
    """Get webhook delivery history"""
    auth = await authenticate_request(request, None, None, authorization)
    
    deliveries = await get_webhook_deliveries(webhook_id, limit)
    
    result = []
    for d in deliveries:
        result.append(WebhookDeliveryResponse(
            delivery_id=d['delivery_id'],
            webhook_id=webhook_id,
            event_type=d['event_type'],
            status=d['status'],
            attempt_count=d['attempt_count'],
            delivered_at=d.get('delivered_at'),
            created_at=d['created_at']
        ))
    
    return result
