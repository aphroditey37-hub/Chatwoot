"""
Wallet Load Routes - Payment IN (no game involved)
Supports idempotency keys to prevent duplicate submissions.

USES ORDER LIFECYCLE: All orders go through canonical state machine.
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import hashlib
from datetime import datetime, timezone
import json
import logging

from ..core.database import get_pool
from ..core.auth import get_current_user, AuthenticatedUser
from ..core.order_lifecycle import (
    create_order, OrderType, OrderStatus, 
    requires_approval, OrderErrorCode
)

router = APIRouter(prefix="/wallet-load", tags=["wallet_load"])
logger = logging.getLogger(__name__)


class WalletLoadRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount to load")
    payment_method: str = Field(description="Payment method: GCASH, PAYMAYA, BANK, etc")
    proof_image: str = Field(description="Base64 encoded proof of payment")
    notes: Optional[str] = None


def generate_idempotency_key(user_id: str, amount: float, payment_method: str) -> str:
    """Generate a deterministic idempotency key from request params"""
    # Include timestamp rounded to minute to allow retry within same minute
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    key_string = f"wallet_load:{user_id}:{amount}:{payment_method}:{timestamp}"
    return hashlib.sha256(key_string.encode()).hexdigest()[:64]


@router.post("/request")
async def create_wallet_load_request(
    data: WalletLoadRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    authorization: str = Header(..., alias="Authorization"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Create a wallet load request (Payment IN)
    - No game involved
    - Sends to Telegram for approval
    - When approved, adds to wallet balance
    
    USES ORDER LIFECYCLE STATE MACHINE:
    - Initial status: pending_approval (requires Telegram approval)
    - Supports Idempotency-Key header to prevent duplicate submissions.
    
    Security: Requires authenticated user session.
    """
    # Generate or use provided idempotency key
    if not idempotency_key:
        idempotency_key = generate_idempotency_key(
            user.user_id, data.amount, data.payment_method
        )
    
    # Build metadata
    metadata = {
        'payment_method': data.payment_method,
        'notes': data.notes,
        'payment_proof_url': data.proof_image[:100] if data.proof_image else None  # Truncate for metadata
    }
    
    # CREATE ORDER VIA CANONICAL FUNCTION
    success, result = await create_order(
        user_id=user.user_id,
        username=user.username,
        order_type=OrderType.WALLET_LOAD.value,
        amount=data.amount,
        idempotency_key=idempotency_key,
        metadata=metadata,
        payment_method=data.payment_method
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail={"message": result.get('message', 'Failed to create order'), "error_code": result.get('error_code')}
        )
    
    # Check if duplicate
    if result.get('duplicate'):
        logger.info(f"Duplicate wallet load request (idempotency_key={idempotency_key})")
        return {
            "success": True,
            "order_id": result['order_id'],
            "message": "Request already submitted (duplicate detected)",
            "status": result['status'],
            "duplicate": True
        }
    
    order_id = result['order_id']
    
    # Update order with payment proof
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders SET payment_proof_url = $1 WHERE order_id = $2
        """, data.proof_image, order_id)
    
    # Send to Telegram for approval
    background_tasks.add_task(send_telegram_notification, order_id)
    
    return {
        "success": True,
        "order_id": order_id,
        "message": "Wallet load request created. Awaiting approval.",
        "status": OrderStatus.PENDING_APPROVAL.value,
        "idempotency_key": idempotency_key,
        "requires_approval": True  # Explicit flow contract
    }


async def send_telegram_notification(order_id: str):
    """Send notification to Telegram"""
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    import os
    
    # Get tokens from environment (not hardcoded)
    BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Telegram not configured - skipping notification")
        return
    
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            order = await conn.fetchrow("""
                SELECT order_id, username, amount, metadata
                FROM orders WHERE order_id = $1
            """, order_id)
            
            if not order:
                return
            
            metadata = order['metadata'] or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            payment_method = metadata.get('payment_method', 'N/A')
            
            bot = Bot(token=BOT_TOKEN)
            
            message = f"""
💵 <b>Payment IN - Wallet Load</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
💰 <b>Amount:</b> ${order['amount']:.2f}
💳 <b>Method:</b> {payment_method}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>💡 This is a WALLET LOAD (no game involved)</i>
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
                    InlineKeyboardButton("❌ Failed", callback_data=f"failed_{order_id}"),
                ],
                [
                    InlineKeyboardButton("🔄 Duplicate", callback_data=f"duplicate_{order_id}"),
                    InlineKeyboardButton("⚠️ Suspicious", callback_data=f"suspicious_{order_id}"),
                ],
                [
                    InlineKeyboardButton("🏷️ Tag Changed", callback_data=f"tagchanged_{order_id}"),
                    InlineKeyboardButton("✏️ Edit Amount", callback_data=f"editamount_{order_id}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            sent = await bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            await conn.execute("""
                UPDATE orders 
                SET telegram_message_id = $1, telegram_chat_id = $2
                WHERE order_id = $3
            """, str(sent.message_id), str(CHAT_ID), order_id)
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
