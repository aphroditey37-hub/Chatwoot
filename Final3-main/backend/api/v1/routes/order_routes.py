"""
API v1 Order Routes
Order validation and creation with bonus calculations
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional

from ..models import (
    OrderValidateRequest, OrderValidateResponse,
    OrderCreateRequest, OrderCreateResponse,
    OrderResponse, OrderListRequest, OrderStatus,
    BonusCalculation, APIError, PaginatedResponse,
    GameListResponse, GameInfo
)
from ..services import (
    validate_order as validate_order_service,
    create_order as create_order_service,
    get_order, get_user_orders, list_games,
    trigger_webhooks, log_audit
)
from ..core.config import ErrorCodes
from .dependencies import get_client_ip, authenticate_request

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/validate",
    response_model=OrderValidateResponse,
    responses={
        400: {"model": APIError, "description": "Validation failed"},
        401: {"model": APIError, "description": "Invalid credentials"},
        429: {"model": APIError, "description": "Rate limited"}
    },
    summary="Validate an order without creating it",
    description="""
    Validate an order and calculate bonus amounts without actually creating the order.
    
    **Authentication**: Requires username + password OR Bearer token
    
    **Validation checks**:
    - Game exists and is active
    - Amount is within allowed range for the game
    - Referral code is valid (if provided)
    
    **Bonus calculation**:
    - Applies game-specific bonus rules
    - Applies referral perks if code provided
    - First recharge bonuses are calculated
    
    Returns detailed bonus breakdown including rule applied.
    """
)
async def validate_order(
    request: Request,
    data: OrderValidateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Validate an order without creating it"""
    # Authenticate
    auth = await authenticate_request(
        request,
        data.username,
        data.password,
        authorization
    )
    
    # Validate order
    success, result = await validate_order_service(
        user_id=auth.user_id,
        username=auth.username,
        game_name=data.game_name,
        recharge_amount=data.recharge_amount,
        referral_code=data.referral_code
    )
    
    if not success:
        return OrderValidateResponse(
            success=False,
            message=result.get('message', 'Validation failed'),
            valid=False,
            error_code=result.get('error_code')
        )
    
    # Build bonus calculation response
    bonus_calc = None
    if result.get('bonus_calculation'):
        bc = result['bonus_calculation']
        bonus_calc = BonusCalculation(
            base_amount=bc['base_amount'],
            percent_bonus=bc['percent_bonus'],
            flat_bonus=bc['flat_bonus'],
            referral_bonus=bc['referral_bonus'],
            total_bonus=bc['total_bonus'],
            rule_applied=bc['rule_applied'],
            rule_details=bc['rule_details']
        )
    
    return OrderValidateResponse(
        success=True,
        message="Order is valid",
        valid=True,
        game_name=result['game_name'],
        game_display_name=result['game_display_name'],
        recharge_amount=result['recharge_amount'],
        bonus_amount=result['bonus_amount'],
        total_amount=result['total_amount'],
        bonus_calculation=bonus_calc
    )


@router.post(
    "/create",
    response_model=OrderCreateResponse,
    responses={
        400: {"model": APIError, "description": "Validation failed"},
        401: {"model": APIError, "description": "Invalid credentials"},
        429: {"model": APIError, "description": "Rate limited"}
    },
    summary="Create a new order",
    description="""
    Create a new order with bonus calculation.
    
    **Authentication**: Requires username + password OR Bearer token
    
    **Idempotency**: Use `Idempotency-Key` header to prevent duplicate orders.
    If the same key is used, the original order is returned.
    
    **Process**:
    1. Validates order (same as /validate endpoint)
    2. Creates order record with calculated bonus
    3. Triggers registered webhooks with order.created event
    
    Returns the created order with full details.
    """
)
async def create_order(
    request: Request,
    data: OrderCreateRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Create a new order"""
    # Authenticate
    auth = await authenticate_request(
        request,
        data.username,
        data.password,
        authorization
    )
    
    ip_address = await get_client_ip(request)
    
    # Create order
    success, result = await create_order_service(
        user_id=auth.user_id,
        username=auth.username,
        game_name=data.game_name,
        recharge_amount=data.recharge_amount,
        referral_code=data.referral_code,
        idempotency_key=idempotency_key,
        metadata=data.metadata,
        ip_address=ip_address
    )
    
    if not success:
        return OrderCreateResponse(
            success=False,
            message=result.get('message', 'Order creation failed'),
            error_code=result.get('error_code')
        )
    
    # Build order response
    order = OrderResponse(
        order_id=result['order_id'],
        username=result['username'],
        game_name=result['game_name'],
        game_display_name=result.get('game_display_name'),
        recharge_amount=result['recharge_amount'],
        bonus_amount=result['bonus_amount'],
        total_amount=result['total_amount'],
        referral_code=result.get('referral_code'),
        referral_bonus_applied=result.get('referral_bonus_applied', False),
        rule_applied=result.get('rule_applied'),
        status=OrderStatus(result['status']),
        created_at=result['created_at'],
        metadata=result.get('metadata')
    )
    
    # Trigger webhooks
    await trigger_webhooks("order.created", {
        "order_id": result['order_id'],
        "username": result['username'],
        "referral_code": result.get('referral_code'),
        "game": result['game_name'],
        "amount": result['recharge_amount'],
        "bonus_amount": result['bonus_amount'],
        "total_amount": result['total_amount'],
        "created_at": result['created_at']
    }, auth.user_id)
    
    return OrderCreateResponse(
        success=True,
        message="Order created successfully",
        order=order
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    responses={
        401: {"model": APIError, "description": "Invalid credentials"},
        404: {"model": APIError, "description": "Order not found"}
    },
    summary="Get order by ID",
    description="Retrieve a specific order by its ID"
)
async def get_order_endpoint(
    request: Request,
    order_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Get order by ID"""
    # For GET requests, we need token auth
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Authorization header required for GET requests",
                "error_code": ErrorCodes.INVALID_CREDENTIALS
            }
        )
    
    auth = await authenticate_request(request, None, None, authorization)
    
    order = await get_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Order not found",
                "error_code": ErrorCodes.ORDER_NOT_FOUND
            }
        )
    
    # Verify ownership
    if order['username'] != auth.username:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Order not found",
                "error_code": ErrorCodes.ORDER_NOT_FOUND
            }
        )
    
    return OrderResponse(
        order_id=order['order_id'],
        username=order['username'],
        game_name=order['game_name'],
        game_display_name=order.get('game_display_name'),
        recharge_amount=order['recharge_amount'],
        bonus_amount=order['bonus_amount'],
        total_amount=order['total_amount'],
        referral_code=order.get('referral_code'),
        referral_bonus_applied=order.get('referral_bonus_applied', False),
        rule_applied=order.get('rule_applied'),
        status=OrderStatus(order['status']),
        created_at=order['created_at'],
        metadata=order.get('metadata')
    )


@router.post(
    "/list",
    response_model=PaginatedResponse,
    responses={
        401: {"model": APIError, "description": "Invalid credentials"}
    },
    summary="List user orders",
    description="Get paginated list of orders for the authenticated user"
)
async def list_orders(
    request: Request,
    data: OrderListRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """List user orders"""
    auth = await authenticate_request(
        request,
        data.username,
        data.password,
        authorization
    )
    
    orders, total = await get_user_orders(
        user_id=auth.user_id,
        page=data.page,
        page_size=data.page_size,
        status=data.status.value if data.status else None
    )
    
    return PaginatedResponse(
        success=True,
        data=orders,
        total=total,
        page=data.page,
        page_size=data.page_size,
        has_more=(data.page * data.page_size) < total
    )


@router.get(
    "/games/list",
    response_model=GameListResponse,
    summary="List available games",
    description="Get list of all active games with their bonus rules"
)
async def list_games_endpoint(request: Request):
    """List available games (public endpoint)"""
    games = await list_games()
    
    game_list = []
    for g in games:
        game_list.append(GameInfo(
            game_id=g['game_id'],
            game_name=g['game_name'],
            display_name=g['display_name'],
            description=g.get('description'),
            min_recharge_amount=g['min_recharge_amount'],
            max_recharge_amount=g['max_recharge_amount'],
            bonus_rules=g.get('bonus_rules', {}),
            is_active=g['is_active']
        ))
    
    return GameListResponse(success=True, games=game_list)
