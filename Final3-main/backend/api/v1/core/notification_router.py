"""
Notification Router - Multi-Telegram-Bot Event System
Central service for emitting events and routing to subscribed Telegram bots

This is a DELIVERY CHANNEL, not business logic.
All events are standardized and reusable for future channels (email, webhook, etc)

PROOF IMAGE POLICY:
- Base64 image data is sent DIRECTLY to Telegram via sendDocument
- Image data is NEVER stored in database (only hashes for duplicate detection)
- Images in extra_data['proof_image'] are handled specially
"""
import asyncio
import uuid
import json
import logging
import httpx
import base64
import io
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

from .database import fetch_one, fetch_all, execute, get_pool

logger = logging.getLogger(__name__)


# ==================== EVENT TYPE DEFINITIONS ====================

class EventType(str, Enum):
    """Standardized event types for notification routing"""
    
    # User Events
    USER_REGISTERED = "USER_REGISTERED"
    USER_LOGIN = "USER_LOGIN"
    
    # Order Events
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_PROOF_SUBMITTED = "ORDER_PROOF_SUBMITTED"
    ORDER_APPROVED = "ORDER_APPROVED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_AMOUNT_ADJUSTED = "ORDER_AMOUNT_ADJUSTED"
    
    # Wallet Load Events
    WALLET_LOAD_REQUESTED = "WALLET_LOAD_REQUESTED"
    WALLET_LOAD_APPROVED = "WALLET_LOAD_APPROVED"
    WALLET_LOAD_REJECTED = "WALLET_LOAD_REJECTED"
    WALLET_TOPUP_REQUESTED = "WALLET_TOPUP_REQUESTED"
    WALLET_TOPUP_APPROVED = "WALLET_TOPUP_APPROVED"
    WALLET_TOPUP_REJECTED = "WALLET_TOPUP_REJECTED"
    
    # Game Load Events
    GAME_LOAD_REQUESTED = "GAME_LOAD_REQUESTED"
    GAME_LOAD_SUCCESS = "GAME_LOAD_SUCCESS"
    GAME_LOAD_FAILED = "GAME_LOAD_FAILED"
    
    # Game Credentials Events
    GAME_ID_CREATED = "GAME_ID_CREATED"
    GAME_ID_RESET = "GAME_ID_RESET"
    
    # Withdrawal Events
    WITHDRAW_REQUESTED = "WITHDRAW_REQUESTED"
    WITHDRAW_APPROVED = "WITHDRAW_APPROVED"
    WITHDRAW_REJECTED = "WITHDRAW_REJECTED"
    
    # Referral Events
    REFERRAL_JOINED = "REFERRAL_JOINED"
    REFERRAL_MILESTONE_REACHED = "REFERRAL_MILESTONE_REACHED"
    REFERRAL_REWARD_GRANTED = "REFERRAL_REWARD_GRANTED"
    
    # Promo Code Events
    PROMO_CODE_REDEEMED = "PROMO_CODE_REDEEMED"
    PROMO_CODE_CREATED = "PROMO_CODE_CREATED"
    
    # Transaction Events
    TRANSACTION_LOGGED = "TRANSACTION_LOGGED"
    
    # System Events
    SECURITY_ALERT = "SECURITY_ALERT"
    SYSTEM_ALERT = "SYSTEM_ALERT"


# Event metadata for UI display
EVENT_METADATA = {
    EventType.USER_REGISTERED: {
        "label": "New Client Registered",
        "description": "A new user signed up on the platform",
        "category": "Users",
        "requires_approval": False
    },
    EventType.USER_LOGIN: {
        "label": "User Login",
        "description": "User logged into the platform",
        "category": "Users",
        "requires_approval": False
    },
    EventType.ORDER_CREATED: {
        "label": "Order Created",
        "description": "New game load order created",
        "category": "Orders",
        "requires_approval": True
    },
    EventType.ORDER_PROOF_SUBMITTED: {
        "label": "Order Proof Submitted",
        "description": "Payment proof submitted for order",
        "category": "Orders",
        "requires_approval": True
    },
    EventType.ORDER_APPROVED: {
        "label": "Order Approved",
        "description": "Order approved by admin/reviewer",
        "category": "Orders",
        "requires_approval": False
    },
    EventType.ORDER_REJECTED: {
        "label": "Order Rejected",
        "description": "Order rejected by admin/reviewer",
        "category": "Orders",
        "requires_approval": False
    },
    EventType.ORDER_AMOUNT_ADJUSTED: {
        "label": "Order Amount Adjusted",
        "description": "Order amount edited before approval",
        "category": "Orders",
        "requires_approval": False
    },
    EventType.WALLET_LOAD_REQUESTED: {
        "label": "Wallet Load Request",
        "description": "Client requested wallet funding (site)",
        "category": "Wallet",
        "requires_approval": True
    },
    EventType.WALLET_LOAD_APPROVED: {
        "label": "Wallet Load Approved",
        "description": "Wallet load approved and credited",
        "category": "Wallet",
        "requires_approval": False
    },
    EventType.WALLET_LOAD_REJECTED: {
        "label": "Wallet Load Rejected",
        "description": "Wallet load rejected",
        "category": "Wallet",
        "requires_approval": False
    },
    EventType.WALLET_TOPUP_REQUESTED: {
        "label": "Wallet Top-up Request",
        "description": "Client requested wallet top-up",
        "category": "Wallet",
        "requires_approval": True
    },
    EventType.WALLET_TOPUP_APPROVED: {
        "label": "Wallet Top-up Approved",
        "description": "Wallet top-up approved",
        "category": "Wallet",
        "requires_approval": False
    },
    EventType.WALLET_TOPUP_REJECTED: {
        "label": "Wallet Top-up Rejected",
        "description": "Wallet top-up rejected",
        "category": "Wallet",
        "requires_approval": False
    },
    EventType.GAME_LOAD_REQUESTED: {
        "label": "Game Load Request",
        "description": "Client requested game load",
        "category": "Games",
        "requires_approval": False
    },
    EventType.GAME_LOAD_SUCCESS: {
        "label": "Game Load Success",
        "description": "Game loaded successfully",
        "category": "Games",
        "requires_approval": False
    },
    EventType.GAME_LOAD_FAILED: {
        "label": "Game Load Failed",
        "description": "Game load failed",
        "category": "Games",
        "requires_approval": False
    },
    EventType.GAME_ID_CREATED: {
        "label": "Game ID Created",
        "description": "New game credentials created",
        "category": "Games",
        "requires_approval": False
    },
    EventType.GAME_ID_RESET: {
        "label": "Game ID Reset",
        "description": "Game credentials reset",
        "category": "Games",
        "requires_approval": False
    },
    EventType.WITHDRAW_REQUESTED: {
        "label": "Withdrawal Request",
        "description": "Client requested withdrawal (site only)",
        "category": "Withdrawals",
        "requires_approval": True
    },
    EventType.WITHDRAW_APPROVED: {
        "label": "Withdrawal Approved",
        "description": "Withdrawal approved and processed",
        "category": "Withdrawals",
        "requires_approval": False
    },
    EventType.WITHDRAW_REJECTED: {
        "label": "Withdrawal Rejected",
        "description": "Withdrawal rejected",
        "category": "Withdrawals",
        "requires_approval": False
    },
    EventType.REFERRAL_JOINED: {
        "label": "Referral Joined",
        "description": "New user joined via referral",
        "category": "Referrals",
        "requires_approval": False
    },
    EventType.REFERRAL_MILESTONE_REACHED: {
        "label": "Referral Milestone",
        "description": "Referral milestone reached",
        "category": "Referrals",
        "requires_approval": False
    },
    EventType.REFERRAL_REWARD_GRANTED: {
        "label": "Referral Reward",
        "description": "Referral reward granted",
        "category": "Referrals",
        "requires_approval": False
    },
    EventType.PROMO_CODE_REDEEMED: {
        "label": "Promo Code Redeemed",
        "description": "A user redeemed a promotional code",
        "category": "Promo Codes",
        "requires_approval": False
    },
    EventType.PROMO_CODE_CREATED: {
        "label": "Promo Code Created",
        "description": "New promotional code created",
        "category": "Promo Codes",
        "requires_approval": False
    },
    EventType.TRANSACTION_LOGGED: {
        "label": "Transaction Logged",
        "description": "Transaction recorded in ledger",
        "category": "Transactions",
        "requires_approval": False
    },
    EventType.SECURITY_ALERT: {
        "label": "Security Alert",
        "description": "Security-related alert",
        "category": "System",
        "requires_approval": False
    },
    EventType.SYSTEM_ALERT: {
        "label": "System Alert",
        "description": "System notification",
        "category": "System",
        "requires_approval": False
    }
}


# ==================== NOTIFICATION PAYLOAD ====================

@dataclass
class NotificationPayload:
    """Standardized notification payload"""
    event_type: EventType
    title: str
    message: str
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    amount: Optional[float] = None
    extra_data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    requires_action: bool = False
    action_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "title": self.title,
            "message": self.message,
            "reference_id": self.reference_id,
            "reference_type": self.reference_type,
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "amount": self.amount,
            "extra_data": self.extra_data or {},
            "image_url": self.image_url,
            "requires_action": self.requires_action,
            "action_data": self.action_data or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ==================== NOTIFICATION ROUTER ====================

class NotificationRouter:
    """
    Central notification routing service
    
    Flow:
    1. System action completes
    2. emit() called with event_type and payload
    3. Router fetches active bots with event permission
    4. Sends formatted message to each bot
    5. Logs result
    """
    
    @staticmethod
    async def emit(
        event_type: EventType,
        payload: NotificationPayload,
        skip_logging: bool = False
    ) -> Dict[str, Any]:
        """
        Emit an event to all subscribed Telegram bots
        
        Args:
            event_type: The event type to emit
            payload: Notification payload
            skip_logging: Skip logging to notification_logs table
            
        Returns:
            Dict with sent_count, success_count, failed_count, details
        """
        log_id = str(uuid.uuid4())
        event_str = event_type.value if isinstance(event_type, EventType) else event_type
        
        try:
            # Get all active bots with this event enabled
            bots = await NotificationRouter._get_subscribed_bots(event_str)
            
            if not bots:
                logger.info(f"No bots subscribed to {event_str}")
                return {"sent_count": 0, "success_count": 0, "failed_count": 0, "details": []}
            
            # Determine if this event requires approval buttons
            event_meta = EVENT_METADATA.get(event_type, {})
            requires_approval = event_meta.get("requires_approval", False) and payload.requires_action
            
            sent_to = []
            success = []
            failed = []
            details = []
            
            for bot in bots:
                # For approval events, only bots with approval permission get buttons
                show_buttons = False
                if requires_approval:
                    if event_type in [EventType.ORDER_CREATED, EventType.WALLET_LOAD_REQUESTED]:
                        show_buttons = bot.get('can_approve_payments') or bot.get('can_approve_wallet_loads')
                    elif event_type == EventType.WITHDRAW_REQUESTED:
                        show_buttons = bot.get('can_approve_withdrawals')
                
                sent_to.append(bot['bot_id'])
                
                try:
                    result = await NotificationRouter._send_to_bot(
                        bot=bot,
                        payload=payload,
                        show_approval_buttons=show_buttons
                    )
                    
                    if result.get('success'):
                        success.append(bot['bot_id'])
                        details.append({
                            "bot_id": bot['bot_id'],
                            "bot_name": bot['name'],
                            "success": True,
                            "message_id": result.get('message_id')
                        })
                    else:
                        failed.append(bot['bot_id'])
                        details.append({
                            "bot_id": bot['bot_id'],
                            "bot_name": bot['name'],
                            "success": False,
                            "error": result.get('error')
                        })
                except Exception as e:
                    failed.append(bot['bot_id'])
                    details.append({
                        "bot_id": bot['bot_id'],
                        "bot_name": bot['name'],
                        "success": False,
                        "error": str(e)
                    })
            
            # Log the notification
            if not skip_logging:
                await NotificationRouter._log_notification(
                    log_id=log_id,
                    event_type=event_str,
                    payload=payload.to_dict(),
                    sent_to=sent_to,
                    success=success,
                    failed=failed,
                    details=details
                )
            
            return {
                "log_id": log_id,
                "sent_count": len(sent_to),
                "success_count": len(success),
                "failed_count": len(failed),
                "details": details
            }
            
        except Exception as e:
            logger.error(f"NotificationRouter.emit error: {e}")
            return {
                "log_id": log_id,
                "sent_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "error": str(e)
            }
    
    @staticmethod
    async def _get_subscribed_bots(event_type: str) -> List[Dict]:
        """Get all active bots subscribed to this event type"""
        bots = await fetch_all("""
            SELECT tb.bot_id, tb.name, tb.bot_token, tb.chat_id, 
                   tb.can_approve_payments, tb.can_approve_wallet_loads, tb.can_approve_withdrawals
            FROM telegram_bots tb
            JOIN telegram_bot_event_permissions tbep ON tb.bot_id = tbep.bot_id
            WHERE tb.is_active = TRUE 
              AND tbep.event_type = $1 
              AND tbep.enabled = TRUE
        """, event_type)
        return bots
    
    @staticmethod
    async def _send_to_bot(
        bot: Dict,
        payload: NotificationPayload,
        show_approval_buttons: bool = False
    ) -> Dict[str, Any]:
        """
        Send notification to a specific Telegram bot.
        
        PROOF IMAGE HANDLING:
        - Checks extra_data for 'proof_image' (base64) or 'image_url' (URL)
        - Base64 images are decoded and sent via sendDocument as file upload
        - URL images are sent via sendPhoto
        - Images are NEVER stored in database
        """
        try:
            bot_token = bot['bot_token']
            chat_id = bot['chat_id']
            
            # Build message
            message = NotificationRouter._format_message(payload)
            
            # Build inline keyboard if approval buttons needed
            # STANDARDIZED FORMAT: action:entity_type:entity_id
            reply_markup = None
            if show_approval_buttons and payload.action_data:
                entity_type = payload.action_data.get('entity_type', payload.reference_type or 'item')
                reference_id = payload.action_data.get('reference_id', payload.reference_id)
                
                buttons = [
                    [
                        {"text": "✅ Approve", "callback_data": f"approve:{entity_type}:{reference_id}"},
                        {"text": "❌ Reject", "callback_data": f"reject:{entity_type}:{reference_id}"}
                    ]
                ]
                
                # Add Edit Amount button for orders (reviewer bots)
                if entity_type == 'order':
                    buttons.append([
                        {"text": "✏️ Edit Amount", "callback_data": f"edit_amount:{entity_type}:{reference_id}"},
                        {"text": "👁 View Details", "callback_data": f"view:{entity_type}:{reference_id}"}
                    ])
                else:
                    buttons.append([
                        {"text": "👁 View Details", "callback_data": f"view:{entity_type}:{reference_id}"}
                    ])
                
                reply_markup = {"inline_keyboard": buttons}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send text message
                msg_data = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                if reply_markup:
                    msg_data["reply_markup"] = reply_markup
                
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json=msg_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get('result', {}).get('message_id')
                    
                    # Handle proof images - check both extra_data and payload.image_url
                    proof_image_sent = False
                    
                    # Check for base64 proof_image in extra_data (SITE UPLOADS)
                    extra_data = payload.extra_data or {}
                    base64_proof = extra_data.get('proof_image')
                    
                    if base64_proof:
                        try:
                            # Remove data URL prefix if present
                            if ',' in base64_proof:
                                base64_proof = base64_proof.split(',', 1)[1]
                            
                            # Decode base64 to bytes
                            image_bytes = base64.b64decode(base64_proof)
                            
                            # Determine file extension from image_type if available
                            image_type = extra_data.get('image_type', 'image/jpeg')
                            ext = 'jpg'
                            if 'png' in image_type:
                                ext = 'png'
                            elif 'gif' in image_type:
                                ext = 'gif'
                            
                            # Create filename
                            ref_short = payload.reference_id[:8] if payload.reference_id else 'proof'
                            filename = f"payment_proof_{ref_short}.{ext}"
                            
                            # Send as document (file upload) - more reliable for large images
                            files = {
                                'document': (filename, io.BytesIO(image_bytes), image_type)
                            }
                            form_data = {
                                'chat_id': chat_id,
                                'caption': f"📎 Payment Proof for {payload.reference_type or 'request'} {ref_short}..."
                            }
                            
                            img_response = await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendDocument",
                                data=form_data,
                                files=files
                            )
                            
                            if img_response.status_code == 200:
                                proof_image_sent = True
                                logger.info(f"Base64 proof image sent to bot {bot['name']} for {payload.reference_id}")
                            else:
                                logger.warning(f"Failed to send base64 proof image: {img_response.text}")
                                
                        except Exception as img_err:
                            logger.warning(f"Failed to decode/send base64 proof image to bot {bot['name']}: {img_err}")
                    
                    # Check for image_url in extra_data (CHATWOOT/WEBHOOK UPLOADS)
                    image_url = extra_data.get('image_url') or payload.image_url
                    if image_url and not proof_image_sent:
                        try:
                            await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                                json={
                                    "chat_id": chat_id,
                                    "photo": image_url,
                                    "caption": f"📎 Proof for {payload.reference_type or 'request'} {payload.reference_id[:8] if payload.reference_id else 'N/A'}..."
                                }
                            )
                            proof_image_sent = True
                            logger.info(f"URL proof image sent to bot {bot['name']} for {payload.reference_id}")
                        except Exception as img_err:
                            logger.warning(f"Failed to send URL image to bot {bot['name']}: {img_err}")
                    
                    return {"success": True, "message_id": message_id, "proof_image_sent": proof_image_sent}
                else:
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Failed to send to bot {bot.get('name')}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _format_message(payload: NotificationPayload) -> str:
        """Format notification payload into Telegram message"""
        event_meta = EVENT_METADATA.get(payload.event_type, {})
        category = event_meta.get("category", "System")
        
        # Emoji mapping
        emoji_map = {
            "Orders": "📦",
            "Wallet": "💰",
            "Games": "🎮",
            "Withdrawals": "💸",
            "Referrals": "👥",
            "Transactions": "📝",
            "System": "⚙️"
        }
        emoji = emoji_map.get(category, "📢")
        
        lines = [
            f"{emoji} *{payload.title}*",
            ""
        ]
        
        if payload.username:
            lines.append(f"👤 *User:* {payload.display_name or payload.username} (@{payload.username})")
        
        if payload.user_id:
            lines.append(f"🆔 *ID:* `{payload.user_id[:8]}...`")
        
        if payload.amount is not None:
            lines.append(f"💵 *Amount:* ₱{payload.amount:,.2f}")
        
        if payload.reference_id:
            lines.append(f"📋 *Ref:* `{payload.reference_id[:8]}...`")
        
        lines.append("")
        lines.append(payload.message)
        lines.append("")
        lines.append(f"⏰ _{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_")
        
        return "\n".join(lines)
    
    @staticmethod
    async def _log_notification(
        log_id: str,
        event_type: str,
        payload: Dict,
        sent_to: List[str],
        success: List[str],
        failed: List[str],
        details: List[Dict]
    ):
        """
        Log notification to database.
        
        PROOF IMAGE POLICY: 
        - NEVER store base64 image data or image URLs in notification_logs
        - Redact 'proof_image', 'image_data', 'image_url' from payload before storage
        """
        status = "success" if not failed else ("partial" if success else "failed")
        
        # REDACT sensitive image data before storing
        redacted_payload = payload.copy()
        
        # Redact from top level
        for key in ['proof_image', 'image_data', 'image_url']:
            if key in redacted_payload:
                redacted_payload[key] = '[REDACTED - sent to Telegram directly]'
        
        # Redact from extra_data if present
        if 'extra_data' in redacted_payload and isinstance(redacted_payload['extra_data'], dict):
            extra = redacted_payload['extra_data'].copy()
            for key in ['proof_image', 'image_data', 'image_url']:
                if key in extra:
                    extra[key] = '[REDACTED - sent to Telegram directly]'
            redacted_payload['extra_data'] = extra
        
        await execute("""
            INSERT INTO notification_logs 
            (log_id, event_type, payload, sent_to_bot_ids, success_bot_ids, failed_bot_ids, status, error_details, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
        """, log_id, event_type, json.dumps(redacted_payload), sent_to, success, failed, status, json.dumps(details))
    
    @staticmethod
    async def get_all_events() -> List[Dict]:
        """Get all available event types with metadata"""
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
        return events
    
    @staticmethod
    async def verify_bot_approval_permission(bot_id: str, event_type: str) -> bool:
        """Verify if a bot has permission to approve for this event type"""
        bot = await fetch_one("""
            SELECT tb.*, tbep.enabled as event_enabled
            FROM telegram_bots tb
            LEFT JOIN telegram_bot_event_permissions tbep 
              ON tb.bot_id = tbep.bot_id AND tbep.event_type = $2
            WHERE tb.bot_id = $1 AND tb.is_active = TRUE
        """, bot_id, event_type)
        
        if not bot or not bot.get('event_enabled'):
            return False
        
        # Check specific approval permissions
        if event_type in [EventType.ORDER_CREATED.value, EventType.WALLET_LOAD_REQUESTED.value]:
            return bot.get('can_approve_payments') or bot.get('can_approve_wallet_loads')
        elif event_type == EventType.WITHDRAW_REQUESTED.value:
            return bot.get('can_approve_withdrawals')
        
        return True


# ==================== HELPER FUNCTIONS ====================

async def emit_event(
    event_type: EventType,
    title: str,
    message: str,
    reference_id: str = None,
    reference_type: str = None,
    user_id: str = None,
    username: str = None,
    display_name: str = None,
    amount: float = None,
    extra_data: Dict = None,
    image_url: str = None,
    requires_action: bool = False,
    entity_type: str = None,  # STANDARDIZED: action:entity_type:entity_id
    action_prefix: str = None  # DEPRECATED: kept for backwards compatibility
) -> Dict[str, Any]:
    """
    Convenience function to emit an event
    
    Usage:
        from ..core.notification_router import emit_event, EventType
        
        await emit_event(
            event_type=EventType.WALLET_LOAD_REQUESTED,
            title="New Wallet Load Request",
            message="Please review the payment proof",
            reference_id=request_id,
            reference_type="wallet_load",
            user_id=user['user_id'],
            username=user['username'],
            amount=100.0,
            requires_action=True,
            entity_type="wallet_load"  # STANDARDIZED FORMAT
        )
    
    Callback format: action:entity_type:entity_id
    Examples: approve:wallet_load:abc123, reject:order:def456
    """
    # Use entity_type if provided, fall back to reference_type, then action_prefix for backwards compat
    effective_entity_type = entity_type or reference_type or action_prefix or "item"
    
    payload = NotificationPayload(
        event_type=event_type,
        title=title,
        message=message,
        reference_id=reference_id,
        reference_type=reference_type,
        user_id=user_id,
        username=username,
        display_name=display_name,
        amount=amount,
        extra_data=extra_data,
        image_url=image_url,
        requires_action=requires_action,
        action_data={
            "entity_type": effective_entity_type,  # STANDARDIZED
            "reference_id": reference_id
        } if requires_action else None
    )
    
    return await NotificationRouter.emit(event_type, payload)
