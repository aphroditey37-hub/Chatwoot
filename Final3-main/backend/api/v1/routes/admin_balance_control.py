"""
Admin Balance Control - Manual load/withdraw for clients
All operations go through approval_service and emit Telegram notifications

SECURITY: All endpoints require admin authentication.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, Header
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone
import logging
import json

from ..core.database import get_pool
from ..core.auth import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/admin/balance-control", tags=["admin_balance"])
logger = logging.getLogger(__name__)


# ==================== AUTH HELPER ====================

async def require_admin_for_balance(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
) -> AuthenticatedUser:
    """Require admin role for balance control operations."""
    user = await get_current_user(request, authorization, None)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail={"message": "Admin access required for balance control", "error_code": "E1007"}
        )
    
    return user


class ManualBalanceRequest(BaseModel):
    user_id: str
    amount: float = Field(gt=0)
    reason: str = Field(min_length=5, description="Required reason for manual adjustment")


@router.post("/load")
async def admin_manual_load(
    request_data: ManualBalanceRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    authorization: str = Header(..., alias="Authorization"),
    admin: AuthenticatedUser = Depends(require_admin_for_balance)
):
    """
    Admin manually loads client balance
    - Creates order (type: admin_manual_load)
    - Directly approves and executes (no Telegram approval needed)
    - Logs in ledger immediately
    
    SECURITY: Requires admin authentication.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get user
        user = await conn.fetchrow("""
            SELECT user_id, username, real_balance, display_name
            FROM users WHERE user_id = $1
        """, request_data.user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create order with immediate approval
        order_id = str(uuid.uuid4())
        balance_before = float(user['real_balance'] or 0)
        balance_after = balance_before + request_data.amount
        
        # Insert order as approved and executed
        await conn.execute("""
            INSERT INTO orders (
                order_id, user_id, username,
                order_type, amount, total_amount,
                status, metadata, created_at, approved_by, approved_at, executed_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9, NOW(), NOW())
        """, order_id, user['user_id'], user['username'],
             'admin_load', request_data.amount, request_data.amount,
             'APPROVED_EXECUTED', json.dumps({
                 'reason': request_data.reason,
                 'admin_action': True,
                 'initiated_by': admin.username,
                 'auto_approved': True,
                 'balance_before': balance_before,
                 'balance_after': balance_after
             }), admin.user_id)
        
        # Update user balance immediately
        await conn.execute("""
            UPDATE users 
            SET real_balance = COALESCE(real_balance, 0) + $1,
                updated_at = NOW()
            WHERE user_id = $2
        """, request_data.amount, user['user_id'])
        
        # Log to wallet_ledger
        ledger_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO wallet_ledger (
                ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                reference_id, reference_type, description, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
        """, ledger_id, user['user_id'], 'admin_load', request_data.amount, balance_before, balance_after,
             order_id, 'admin_load', f"Admin load by {admin.username}: {request_data.reason}")
        
        # Log audit
        await conn.execute("""
            INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, str(uuid.uuid4()), admin.user_id, admin.username, 'admin.balance.load', 'user', user['user_id'],
             json.dumps({
                 'client_username': user['username'],
                 'amount': request_data.amount,
                 'reason': request_data.reason,
                 'balance_before': balance_before,
                 'balance_after': balance_after
             }))
        
        return {
            "success": True,
            "order_id": order_id,
            "message": f"Balance loaded successfully! ${request_data.amount:.2f} added to {user['username']}'s account.",
            "user": user['username'],
            "balance_before": balance_before,
            "balance_after": balance_after
        }


@router.post("/withdraw")
async def admin_manual_withdraw(
    request_data: ManualBalanceRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    authorization: str = Header(..., alias="Authorization"),
    admin: AuthenticatedUser = Depends(require_admin_for_balance)
):
    """
    Admin manually withdraws client balance
    - Creates order (type: admin_manual_withdraw)
    - Directly approves and executes (no Telegram approval needed)
    - Deducts balance immediately
    
    SECURITY: Requires admin authentication.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get user
        user = await conn.fetchrow("""
            SELECT user_id, username, real_balance, display_name
            FROM users WHERE user_id = $1
        """, request_data.user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        balance_before = float(user['real_balance'] or 0)
        
        if balance_before < request_data.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient balance. Current balance: ${balance_before:.2f}")
        
        balance_after = balance_before - request_data.amount
        
        # Create order with immediate approval
        order_id = str(uuid.uuid4())
        
        # Insert order as approved and executed
        await conn.execute("""
            INSERT INTO orders (
                order_id, user_id, username,
                order_type, amount, total_amount,
                status, metadata, created_at, approved_by, approved_at, executed_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9, NOW(), NOW())
        """, order_id, user['user_id'], user['username'],
             'admin_withdraw', request_data.amount, request_data.amount,
             'APPROVED_EXECUTED', json.dumps({
                 'reason': request_data.reason,
                 'admin_action': True,
                 'initiated_by': admin.username,
                 'auto_approved': True,
                 'balance_before': balance_before,
                 'balance_after': balance_after
             }), admin.user_id)
        
        # Update user balance immediately
        await conn.execute("""
            UPDATE users 
            SET real_balance = COALESCE(real_balance, 0) - $1,
                updated_at = NOW()
            WHERE user_id = $2
        """, request_data.amount, user['user_id'])
        
        # Log to wallet_ledger
        ledger_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO wallet_ledger (
                ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                reference_id, reference_type, description, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
        """, ledger_id, user['user_id'], 'admin_withdraw', -request_data.amount, balance_before, balance_after,
             order_id, 'admin_withdraw', f"Admin withdraw by {admin.username}: {request_data.reason}")
        
        # Log audit
        await conn.execute("""
            INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, str(uuid.uuid4()), admin.user_id, admin.username, 'admin.balance.withdraw', 'user', user['user_id'],
             json.dumps({
                 'client_username': user['username'],
                 'amount': request_data.amount,
                 'reason': request_data.reason,
                 'balance_before': balance_before,
                 'balance_after': balance_after
             }))
        
        return {
            "success": True,
            "order_id": order_id,
            "message": f"Balance withdrawn successfully! ${request_data.amount:.2f} deducted from {user['username']}'s account.",
            "user": user['username'],
            "balance_before": balance_before,
            "balance_after": balance_after
        }


async def send_admin_action_telegram(order_id: str, action_type: str, reason: str):
    """Send admin manual action to Telegram for approval"""
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
                SELECT order_id, username, amount
                FROM orders WHERE order_id = $1
            """, order_id)
            
            if not order:
                return
            
            bot = Bot(token=BOT_TOKEN)
            
            if action_type == 'load':
                emoji = "➕"
                title = "Admin Manual Load"
            else:
                emoji = "➖"
                title = "Admin Manual Withdraw"
            
            message = f"""
{emoji} <b>{title}</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
💰 <b>Amount:</b> ${order['amount']:.2f}
📝 <b>Reason:</b> {reason}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>⚠️ Admin-initiated balance adjustment</i>
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"failed_{order_id}"),
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
