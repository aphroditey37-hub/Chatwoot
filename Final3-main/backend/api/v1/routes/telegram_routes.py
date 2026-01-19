"""
API v1 Telegram Bot Management Routes
UNIFIED Multi-bot notification system - SINGLE SOURCE OF TRUTH

Security features:
- No bot token in webhook URLs
- Bot permission validation on all callbacks
- Standardized callback data format: action:entity_type:entity_id
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import json
import logging
import hashlib
import hmac

from ..core.database import fetch_one, fetch_all, execute, get_pool
from ..core.config import get_api_settings
from ..core.notification_router import EventType, EVENT_METADATA

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/telegram", tags=["Telegram Bots"])
settings = get_api_settings()

# Webhook secret for signature validation
WEBHOOK_SECRET = settings.internal_api_secret


# ==================== AUTH ====================

async def require_admin_access(request: Request, authorization: str):
    """
    Verify admin authentication using canonical auth module.
    
    SECURITY: Consistent admin verification across all routes.
    """
    from ..core.auth import get_current_user
    
    # Get authenticated user via canonical auth
    user = await get_current_user(request, authorization, None)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail={"message": "Admin access required", "error_code": "E1007"}
        )
    
    # Get full user record for legacy compatibility
    user_record = await fetch_one("SELECT * FROM users WHERE user_id = $1", user.user_id)
    return user_record


# ==================== MODELS ====================

class TelegramBotCreate(BaseModel):
    """Create a new Telegram bot"""
    name: str = Field(..., min_length=1, max_length=100)
    bot_token: str = Field(..., min_length=10)
    chat_id: str = Field(..., min_length=1)
    is_active: bool = True
    can_approve_payments: bool = False
    can_approve_wallet_loads: bool = False
    can_approve_withdrawals: bool = False
    description: Optional[str] = None


class TelegramBotUpdate(BaseModel):
    """Update a Telegram bot"""
    name: Optional[str] = None
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    is_active: Optional[bool] = None
    can_approve_payments: Optional[bool] = None
    can_approve_wallet_loads: Optional[bool] = None
    can_approve_withdrawals: Optional[bool] = None
    description: Optional[str] = None


class EventPermissionUpdate(BaseModel):
    """Update event permissions for a bot"""
    event_type: str
    enabled: bool


class BulkPermissionUpdate(BaseModel):
    """Bulk update permissions"""
    permissions: List[EventPermissionUpdate]


# ==================== BOT CRUD ====================

@router.get("/bots")
async def list_bots(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all Telegram bots with their permissions"""
    await require_admin_access(request, authorization)
    
    bots = await fetch_all("""
        SELECT bot_id, name, chat_id, is_active, 
               can_approve_payments, can_approve_wallet_loads, can_approve_withdrawals,
               description, created_at, updated_at
        FROM telegram_bots
        ORDER BY created_at DESC
    """)
    
    result = []
    for bot in bots:
        # Get permissions for this bot
        perms = await fetch_all("""
            SELECT event_type, enabled 
            FROM telegram_bot_event_permissions 
            WHERE bot_id = $1
        """, bot['bot_id'])
        
        perm_dict = {p['event_type']: p['enabled'] for p in perms}
        
        # Verify bot token (masked)
        verified = False
        try:
            full_bot = await fetch_one("SELECT bot_token FROM telegram_bots WHERE bot_id = $1", bot['bot_id'])
            if full_bot and full_bot['bot_token']:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"https://api.telegram.org/bot{full_bot['bot_token']}/getMe")
                    verified = resp.json().get('ok', False)
        except:
            pass
        
        result.append({
            "bot_id": bot['bot_id'],
            "name": bot['name'],
            "chat_id": bot['chat_id'],
            "is_active": bot['is_active'],
            "verified": verified,
            "can_approve_payments": bot['can_approve_payments'],
            "can_approve_wallet_loads": bot['can_approve_wallet_loads'],
            "can_approve_withdrawals": bot['can_approve_withdrawals'],
            "description": bot['description'],
            "permissions": perm_dict,
            "created_at": bot['created_at'].isoformat() if bot['created_at'] else None
        })
    
    return {"bots": result}


@router.post("/bots")
async def create_bot(
    request: Request,
    data: TelegramBotCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a new Telegram bot"""
    await require_admin_access(request, authorization)
    
    # Validate bot token with Telegram
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"https://api.telegram.org/bot{data.bot_token}/getMe")
            result = response.json()
            
            if not result.get('ok'):
                raise HTTPException(status_code=400, detail="Invalid bot token")
            
            telegram_username = result['result'].get('username', 'unknown')
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Telegram API timeout")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to validate bot: {str(e)}")
    
    bot_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    await execute("""
        INSERT INTO telegram_bots 
        (bot_id, name, bot_token, chat_id, is_active, 
         can_approve_payments, can_approve_wallet_loads, can_approve_withdrawals,
         description, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10)
    """, bot_id, data.name, data.bot_token, data.chat_id, data.is_active,
       data.can_approve_payments, data.can_approve_wallet_loads, data.can_approve_withdrawals,
       data.description, now)
    
    # Initialize default permissions (all enabled)
    for event_type in EventType:
        perm_id = str(uuid.uuid4())
        await execute("""
            INSERT INTO telegram_bot_event_permissions 
            (permission_id, bot_id, event_type, enabled, created_at)
            VALUES ($1, $2, $3, $4, $5)
        """, perm_id, bot_id, event_type.value, True, now)
    
    return {
        "bot_id": bot_id,
        "message": "Telegram bot created successfully",
        "telegram_username": telegram_username
    }


@router.put("/bots/{bot_id}")
async def update_bot(
    request: Request,
    bot_id: str,
    data: TelegramBotUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update a Telegram bot"""
    await require_admin_access(request, authorization)
    
    bot = await fetch_one("SELECT * FROM telegram_bots WHERE bot_id = $1", bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    updates = []
    params = []
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            params.append(value)
            updates.append(f"{field} = ${len(params)}")
    
    if updates:
        params.append(bot_id)
        updates.append("updated_at = NOW()")
        await execute(
            f"UPDATE telegram_bots SET {', '.join(updates)} WHERE bot_id = ${len(params)}",
            *params
        )
    
    return {"message": "Bot updated successfully"}


@router.delete("/bots/{bot_id}")
async def delete_bot(
    request: Request,
    bot_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete a Telegram bot"""
    await require_admin_access(request, authorization)
    
    await execute("DELETE FROM telegram_bots WHERE bot_id = $1", bot_id)
    return {"message": "Bot deleted successfully"}


# ==================== PERMISSIONS ====================

@router.get("/events")
async def list_event_types(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all available event types"""
    await require_admin_access(request, authorization)
    
    events = []
    for event_type in EventType:
        meta = EVENT_METADATA.get(event_type, {})
        events.append({
            "event_type": event_type.value,
            "label": meta.get("label", event_type.value),
            "description": meta.get("description", ""),
            "category": meta.get("category", "Other"),
            "requires_approval": meta.get("requires_approval", False)
        })
    
    return {"events": events}


@router.post("/bots/{bot_id}/permissions")
async def update_bot_permissions(
    request: Request,
    bot_id: str,
    data: BulkPermissionUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update event permissions for a bot"""
    await require_admin_access(request, authorization)
    
    bot = await fetch_one("SELECT * FROM telegram_bots WHERE bot_id = $1", bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    for perm in data.permissions:
        # Upsert permission
        existing = await fetch_one("""
            SELECT permission_id FROM telegram_bot_event_permissions 
            WHERE bot_id = $1 AND event_type = $2
        """, bot_id, perm.event_type)
        
        if existing:
            await execute("""
                UPDATE telegram_bot_event_permissions 
                SET enabled = $1 WHERE permission_id = $2
            """, perm.enabled, existing['permission_id'])
        else:
            await execute("""
                INSERT INTO telegram_bot_event_permissions 
                (permission_id, bot_id, event_type, enabled, created_at)
                VALUES ($1, $2, $3, $4, NOW())
            """, str(uuid.uuid4()), bot_id, perm.event_type, perm.enabled)
    
    return {"message": "Permissions updated successfully"}


@router.get("/bots/{bot_id}/permissions")
async def get_bot_permissions(
    request: Request,
    bot_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Get all permissions for a bot"""
    await require_admin_access(request, authorization)
    
    perms = await fetch_all("""
        SELECT event_type, enabled 
        FROM telegram_bot_event_permissions 
        WHERE bot_id = $1
    """, bot_id)
    
    return {"permissions": {p['event_type']: p['enabled'] for p in perms}}


# ==================== NOTIFICATION LOGS ====================

@router.get("/logs")
async def get_notification_logs(
    request: Request,
    limit: int = 50,
    event_type: Optional[str] = None,
    authorization: str = Header(..., alias="Authorization")
):
    """Get notification logs"""
    await require_admin_access(request, authorization)
    
    query = "SELECT * FROM notification_logs WHERE 1=1"
    params = []
    
    if event_type:
        params.append(event_type)
        query += f" AND event_type = ${len(params)}"
    
    params.append(limit)
    query += f" ORDER BY created_at DESC LIMIT ${len(params)}"
    
    logs = await fetch_all(query, *params)
    
    return {
        "logs": [{
            "log_id": l['log_id'],
            "event_type": l['event_type'],
            "payload": json.loads(l['payload']) if isinstance(l['payload'], str) else l['payload'],
            "sent_to_bot_ids": l['sent_to_bot_ids'],
            "success_bot_ids": l['success_bot_ids'],
            "failed_bot_ids": l['failed_bot_ids'],
            "status": l['status'],
            "error_details": json.loads(l['error_details']) if isinstance(l.get('error_details'), str) else l.get('error_details'),
            "created_at": l['created_at'].isoformat() if l['created_at'] else None
        } for l in logs]
    }


# ==================== TEST NOTIFICATION ====================

@router.post("/bots/{bot_id}/test")
async def test_bot_notification(
    request: Request,
    bot_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Send a test notification to a specific bot"""
    await require_admin_access(request, authorization)
    
    bot = await fetch_one("SELECT * FROM telegram_bots WHERE bot_id = $1", bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            message = f"""🔔 <b>Test Notification</b>

This is a test message from the Gaming Platform.

Bot: {bot['name']}
Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

If you received this, your bot is configured correctly! ✅"""
            
            response = await client.post(
                f"https://api.telegram.org/bot{bot['bot_token']}/sendMessage",
                json={
                    "chat_id": bot['chat_id'],
                    "text": message,
                    "parse_mode": "HTML"
                }
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Test notification sent successfully"}
            else:
                return {"success": False, "error": response.text}
                
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== DEPRECATED WEBHOOK ====================
# The active webhook handler is at /api/v1/telegram/webhook (telegram_webhook.py)
# This endpoint is deprecated to avoid duplicate processing

@router.post("/webhook")
async def telegram_webhook_deprecated(request: Request):
    """
    DEPRECATED: Use /api/v1/telegram/webhook instead.
    
    This endpoint exists in /admin/telegram/ but the active webhook
    handler is at /api/v1/telegram/webhook (telegram_webhook.py).
    
    Returns 410 Gone to indicate deprecation.
    """
    from fastapi import HTTPException
    raise HTTPException(
        status_code=410,
        detail={
            "message": "This webhook endpoint is deprecated",
            "active_endpoint": "/api/v1/telegram/webhook",
            "reason": "Unified webhook processing"
        }
    )


async def handle_callback_query(callback: dict):
    """Handle callback button press with permission validation"""
    callback_id = callback.get('id')
    callback_data = callback.get('data', '')
    from_user = callback.get('from', {})
    message = callback.get('message', {})
    chat_id = message.get('chat', {}).get('id')
    message_id = message.get('message_id')
    
    logger.info(f"Callback: {callback_data} from chat {chat_id}")
    
    # Find bot by chat_id
    bot = await fetch_one("""
        SELECT * FROM telegram_bots 
        WHERE chat_id = $1 AND is_active = TRUE
    """, str(chat_id))
    
    if not bot:
        logger.warning(f"No active bot found for chat_id {chat_id}")
        return {"ok": True}
    
    # Parse callback data: action:entity_type:entity_id[:extra_value]
    parts = callback_data.split(':')
    if len(parts) < 2:
        await answer_callback(bot['bot_token'], callback_id, "Invalid callback format")
        return {"ok": True}
    
    action = parts[0]
    entity_type = parts[1] if len(parts) > 1 else None
    entity_id = parts[2] if len(parts) > 2 else parts[1]  # Backwards compat
    extra_value = parts[3] if len(parts) > 3 else None  # For set_amount:order:id:19.00
    
    # Validate permissions for approval actions
    if action in ['approve', 'reject', 'edit_amount', 'set_amount']:
        if entity_type == 'wallet_load' and not bot['can_approve_wallet_loads']:
            await answer_callback(bot['bot_token'], callback_id, "❌ This bot cannot approve wallet loads")
            return {"ok": True}
        
        if entity_type == 'order' and not bot['can_approve_payments']:
            await answer_callback(bot['bot_token'], callback_id, "❌ This bot cannot approve orders")
            return {"ok": True}
        
        if entity_type == 'withdrawal' and not bot['can_approve_withdrawals']:
            await answer_callback(bot['bot_token'], callback_id, "❌ This bot cannot approve withdrawals")
            return {"ok": True}
    
    # Process the action
    result = await process_callback_action(
        bot=bot,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        callback_id=callback_id,
        chat_id=chat_id,
        message_id=message_id,
        from_user=from_user,
        extra_value=extra_value
    )
    
    return {"ok": True, "result": result}


async def process_callback_action(
    bot: dict,
    action: str,
    entity_type: str,
    entity_id: str,
    callback_id: str,
    chat_id: int,
    message_id: int,
    from_user: dict,
    extra_value: str = None
):
    """Process callback actions with idempotency checks"""
    admin_name = from_user.get('first_name', 'Admin')
    admin_id = f"telegram:{from_user.get('id', 'unknown')}"
    
    try:
        # Handle wallet load actions
        if entity_type in ['wallet_load', 'wl'] or action.startswith('wl_'):
            # Normalize action for backwards compatibility
            if action.startswith('wl_'):
                action = action[3:]  # Remove 'wl_' prefix
                entity_id = entity_type if entity_type != 'wl' else entity_id
            
            return await handle_wallet_load_action(
                bot, action, entity_id, callback_id, message_id, admin_name, admin_id
            )
        
        # Handle order actions (including edit_amount, set_amount)
        if entity_type == 'order':
            return await handle_order_action(
                bot, action, entity_id, callback_id, message_id, admin_name, admin_id, extra_value
            )
        
        # View action
        if action == 'view':
            return await handle_view_action(bot, entity_type, entity_id, callback_id)
        
        await answer_callback(bot['bot_token'], callback_id, f"Unknown action: {action}")
        return {"success": False}
        
    except Exception as e:
        logger.error(f"Callback action error: {e}")
        await answer_callback(bot['bot_token'], callback_id, f"❌ Error: {str(e)[:50]}")
        return {"success": False, "error": str(e)}


async def handle_wallet_load_action(bot, action, request_id, callback_id, message_id, admin_name, admin_id):
    """Handle wallet load approve/reject using unified approval service"""
    from ..core.approval_service import approve_or_reject_wallet_load, ActorType
    
    if action == 'approve':
        result = await approve_or_reject_wallet_load(
            request_id=request_id,
            action="approve",
            actor_type=ActorType.TELEGRAM_BOT,
            actor_id=admin_id,
            bot_id=bot['bot_id']
        )
        
        if result.success:
            await answer_callback(
                bot['bot_token'], callback_id,
                f"✅ Approved! ₱{result.data.get('amount', 0):,.2f} credited"
            )
            await update_message_with_result(
                bot['bot_token'], bot['chat_id'], message_id,
                f"✅ APPROVED by {admin_name}\n💰 ₱{result.data.get('amount', 0):,.2f} credited"
            )
        else:
            already_processed = result.data.get('already_processed', False)
            await answer_callback(
                bot['bot_token'], callback_id,
                result.message, show_alert=already_processed
            )
        
        return {"success": result.success, **result.data}
    
    elif action == 'reject':
        result = await approve_or_reject_wallet_load(
            request_id=request_id,
            action="reject",
            actor_type=ActorType.TELEGRAM_BOT,
            actor_id=admin_id,
            rejection_reason="Rejected via Telegram",
            bot_id=bot['bot_id']
        )
        
        if result.success:
            await answer_callback(bot['bot_token'], callback_id, "❌ Request Rejected")
            await update_message_with_result(
                bot['bot_token'], bot['chat_id'], message_id,
                f"❌ REJECTED by {admin_name}"
            )
        else:
            await answer_callback(bot['bot_token'], callback_id, result.message, show_alert=True)
        
        return {"success": result.success, **result.data}
    
    return {"success": False}


async def handle_order_action(bot, action, order_id, callback_id, message_id, admin_name, admin_id, extra_value=None):
    """Handle order approve/reject/edit_amount using unified approval service"""
    from ..core.approval_service import approve_or_reject_order, ActorType
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    
    if not order:
        await answer_callback(bot['bot_token'], callback_id, "Order not found")
        return {"success": False}
    
    # Handle edit_amount action - show amount options
    if action == 'edit_amount':
        # Check if already processed
        if order['status'] not in ['pending_review', 'initiated', 'awaiting_payment_proof']:
            await answer_callback(bot['bot_token'], callback_id, f"Cannot edit - already {order['status']}")
            return {"success": False}
        
        # Check if already adjusted
        if order.get('amount_adjusted'):
            await answer_callback(bot['bot_token'], callback_id, "Amount already adjusted once")
            return {"success": False}
        
        # Show edit options
        current_amount = order['amount']
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot['bot_token']}/editMessageReplyMarkup",
                json={
                    "chat_id": bot['chat_id'],
                    "message_id": message_id,
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {"text": f"-₱1.00", "callback_data": f"set_amount:order:{order_id}:{current_amount - 1}"},
                                {"text": f"-₱0.50", "callback_data": f"set_amount:order:{order_id}:{current_amount - 0.5}"},
                            ],
                            [
                                {"text": f"-₱5.00", "callback_data": f"set_amount:order:{order_id}:{current_amount - 5}"},
                                {"text": f"-₱10.00", "callback_data": f"set_amount:order:{order_id}:{current_amount - 10}"},
                            ],
                            [
                                {"text": "🔙 Cancel Edit", "callback_data": f"cancel_edit:order:{order_id}"}
                            ]
                        ]
                    }
                }
            )
        await answer_callback(bot['bot_token'], callback_id, f"Select amount adjustment (current: ₱{current_amount:,.2f})")
        return {"success": True, "action": "edit_shown"}
    
    # Handle set_amount action
    if action == 'set_amount' and extra_value is not None:
        try:
            new_amount = float(extra_value)
        except:
            await answer_callback(bot['bot_token'], callback_id, "Invalid amount")
            return {"success": False}
        
        if new_amount <= 0:
            await answer_callback(bot['bot_token'], callback_id, "Amount must be > 0")
            return {"success": False}
        
        if order['status'] not in ['pending_review', 'initiated', 'awaiting_payment_proof']:
            await answer_callback(bot['bot_token'], callback_id, f"Cannot edit - already {order['status']}")
            return {"success": False}
        
        if order.get('amount_adjusted'):
            await answer_callback(bot['bot_token'], callback_id, "Amount already adjusted once")
            return {"success": False}
        
        old_amount = order['amount']
        now = datetime.now(timezone.utc)
        
        # Update order with new amount
        await execute('''
            UPDATE orders SET 
                amount = $1, 
                total_amount = $1 + bonus_amount,
                amount_adjusted = TRUE,
                adjusted_by = $2,
                adjusted_at = $3,
                updated_at = NOW()
            WHERE order_id = $4
        ''', new_amount, admin_id, now, order_id)
        
        # Restore approval buttons
        await update_message_with_edit_buttons(
            bot['bot_token'], bot['chat_id'], message_id, order_id,
            f"💰 Amount: ₱{old_amount:,.2f} → ₱{new_amount:,.2f} (Edited by {admin_name})"
        )
        await answer_callback(bot['bot_token'], callback_id, f"✏️ Amount adjusted: ₱{new_amount:,.2f}")
        
        # Emit notification
        from ..core.notification_router import emit_event
        await emit_event(
            event_type=EventType.ORDER_AMOUNT_ADJUSTED,
            title="Order Amount Adjusted",
            message=f"Amount changed from ₱{old_amount:,.2f} to ₱{new_amount:,.2f} by {admin_name}",
            reference_id=order_id,
            reference_type="order",
            user_id=order['user_id'],
            username=order['username'],
            amount=new_amount,
            extra_data={"old_amount": old_amount, "adjusted_by": admin_name},
            requires_action=True
        )
        
        return {"success": True, "old_amount": old_amount, "new_amount": new_amount}
    
    # Handle cancel_edit action
    if action == 'cancel_edit':
        await update_message_with_edit_buttons(
            bot['bot_token'], bot['chat_id'], message_id, order_id
        )
        await answer_callback(bot['bot_token'], callback_id, "Edit cancelled")
        return {"success": True}
    
    # Use centralized approval service for approve/reject
    if action == 'approve':
        result = await approve_or_reject_order(
            order_id=order_id,
            action="approve",
            actor_type=ActorType.TELEGRAM_BOT,
            actor_id=admin_id,
            bot_id=bot['bot_id']
        )
        
        if result.success:
            amount_note = ""
            if result.data.get('amount_adjusted'):
                amount_note = f" (adjusted to ₱{result.data.get('amount', 0):,.2f})"
            
            await answer_callback(bot['bot_token'], callback_id, f"✅ Order Approved!{amount_note}")
            await update_message_with_result(
                bot['bot_token'], bot['chat_id'], message_id,
                f"✅ APPROVED by {admin_name}{amount_note}"
            )
        else:
            already_processed = result.data.get('already_processed', False)
            await answer_callback(
                bot['bot_token'], callback_id,
                result.message, show_alert=already_processed
            )
        
        return {"success": result.success, **result.data}
    
    elif action == 'reject':
        result = await approve_or_reject_order(
            order_id=order_id,
            action="reject",
            actor_type=ActorType.TELEGRAM_BOT,
            actor_id=admin_id,
            rejection_reason="Rejected via Telegram",
            bot_id=bot['bot_id']
        )
        
        if result.success:
            await answer_callback(bot['bot_token'], callback_id, "❌ Order Rejected")
            await update_message_with_result(
                bot['bot_token'], bot['chat_id'], message_id,
                f"❌ REJECTED by {admin_name}"
            )
        else:
            await answer_callback(bot['bot_token'], callback_id, result.message, show_alert=True)
        
        return {"success": result.success, **result.data}
    
    return {"success": False}


async def handle_view_action(bot, entity_type, entity_id, callback_id):
    """Handle view details action"""
    if entity_type in ['wallet_load', 'wl']:
        result = await fetch_one("""
            SELECT wlr.*, u.username, u.display_name
            FROM wallet_load_requests wlr
            JOIN users u ON wlr.user_id = u.user_id
            WHERE wlr.request_id = $1
        """, entity_id)
        
        if result:
            details = f"""💰 Wallet Load Details:
ID: {entity_id[:8]}...
User: @{result['username']}
Amount: ₱{result['amount']:,.2f}
Method: {result['payment_method']}
Status: {result['status'].upper()}"""
            await answer_callback(bot['bot_token'], callback_id, details, show_alert=True)
        else:
            await answer_callback(bot['bot_token'], callback_id, "Request not found")
    
    elif entity_type == 'order':
        order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", entity_id)
        if order:
            details = f"""📋 Order Details:
ID: {entity_id[:8]}...
User: {order['username']}
Type: {order['order_type']}
Amount: ₱{order['amount']:,.2f}
Status: {order['status'].upper()}"""
            await answer_callback(bot['bot_token'], callback_id, details, show_alert=True)
        else:
            await answer_callback(bot['bot_token'], callback_id, "Order not found")
    
    return {"success": True}


async def handle_message(message: dict):
    """Handle regular Telegram messages (for /start, etc)"""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    if text.startswith('/start'):
        # Find any bot with this chat_id
        bot = await fetch_one("""
            SELECT * FROM telegram_bots WHERE chat_id = $1 LIMIT 1
        """, str(chat_id))
        
        if bot:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot['bot_token']}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": f"✅ Bot connected!\n\nChat ID: <code>{chat_id}</code>",
                        "parse_mode": "HTML"
                    }
                )
        else:
            logger.info(f"No bot configured for chat {chat_id}")
    
    return {"ok": True}


# ==================== TELEGRAM API HELPERS ====================

async def answer_callback(bot_token: str, callback_id: str, text: str, show_alert: bool = False):
    """Answer Telegram callback query"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_id,
                    "text": text[:200],
                    "show_alert": show_alert
                }
            )
    except Exception as e:
        logger.error(f"Answer callback error: {e}")


async def update_message_with_result(bot_token: str, chat_id: str, message_id: int, result_text: str):
    """Update Telegram message to show action result"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Remove inline keyboard and add result
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": result_text, "callback_data": "done"}]
                        ]
                    }
                }
            )
    except Exception as e:
        logger.error(f"Update message error: {e}")


async def update_message_with_edit_buttons(bot_token: str, chat_id: str, message_id: int, order_id: str, note: str = None):
    """Restore Telegram message with approval buttons after edit"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            buttons = [
                [
                    {"text": "✅ Approve", "callback_data": f"approve:order:{order_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject:order:{order_id}"}
                ],
                [
                    {"text": "✏️ Edit Amount", "callback_data": f"edit_amount:order:{order_id}"},
                    {"text": "👁 View Details", "callback_data": f"view:order:{order_id}"}
                ]
            ]
            
            # Add note if provided
            if note:
                buttons.append([{"text": note, "callback_data": "info"}])
            
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": buttons}
                }
            )
    except Exception as e:
        logger.error(f"Update message error: {e}")


# ==================== WEBHOOK SETUP ====================

@router.post("/setup-webhook")
async def setup_webhook(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """Set up Telegram webhook for all active bots"""
    await require_admin_access(request, authorization)
    
    # Get backend URL
    import os
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', '')
    if not backend_url:
        backend_url = str(request.base_url).rstrip('/')
    
    # Secure webhook URL (no bot token!)
    webhook_url = f"{backend_url}/api/v1/admin/telegram/webhook"
    
    bots = await fetch_all("SELECT * FROM telegram_bots WHERE is_active = TRUE")
    results = []
    
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        for bot in bots:
            try:
                response = await client.post(
                    f"https://api.telegram.org/bot{bot['bot_token']}/setWebhook",
                    json={
                        "url": webhook_url,
                        "allowed_updates": ["callback_query", "message"]
                    }
                )
                result = response.json()
                results.append({
                    "bot_id": bot['bot_id'],
                    "name": bot['name'],
                    "success": result.get('ok', False),
                    "description": result.get('description', '')
                })
            except Exception as e:
                results.append({
                    "bot_id": bot['bot_id'],
                    "name": bot['name'],
                    "success": False,
                    "error": str(e)
                })
    
    return {
        "webhook_url": webhook_url,
        "results": results
    }


@router.get("/webhook-info")
async def get_webhook_info(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """Get webhook info for all bots"""
    await require_admin_access(request, authorization)
    
    bots = await fetch_all("SELECT bot_id, name, bot_token FROM telegram_bots WHERE is_active = TRUE")
    results = []
    
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        for bot in bots:
            try:
                response = await client.get(
                    f"https://api.telegram.org/bot{bot['bot_token']}/getWebhookInfo"
                )
                result = response.json()
                info = result.get('result', {})
                results.append({
                    "bot_id": bot['bot_id'],
                    "name": bot['name'],
                    "url": info.get('url', ''),
                    "has_custom_certificate": info.get('has_custom_certificate', False),
                    "pending_update_count": info.get('pending_update_count', 0),
                    "last_error_date": info.get('last_error_date'),
                    "last_error_message": info.get('last_error_message')
                })
            except Exception as e:
                results.append({
                    "bot_id": bot['bot_id'],
                    "name": bot['name'],
                    "error": str(e)
                })
    
    return {"bots": results}
