"""
Withdrawal Routes - Payment OUT
Two types: withdrawal_wallet (from wallet) and withdrawal_game (from game)

SECURITY: All endpoints require authentication. No hardcoded users.
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone
import json
import logging

from ..core.database import get_pool
from ..core.auth import get_current_user, AuthenticatedUser, enforce_ownership

router = APIRouter(prefix="/withdrawal", tags=["withdrawal"])
logger = logging.getLogger(__name__)


class WithdrawalWalletRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount to withdraw")
    withdrawal_method: str = Field(description="BANK, GCASH, PAYMAYA, etc")
    account_number: str = Field(description="Account number for withdrawal")
    account_name: str = Field(description="Account holder name")


class WithdrawalGameRequest(BaseModel):
    game_id: str = Field(description="Game to withdraw from")
    amount: float = Field(gt=0, description="Amount to withdraw")
    withdrawal_method: str = Field(description="BANK, GCASH, PAYMAYA, etc")
    account_number: str = Field(description="Account number for withdrawal")
    account_name: str = Field(description="Account holder name")


@router.post("/wallet")
async def withdraw_from_wallet(
    data: WithdrawalWalletRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Withdraw from wallet balance (Payment OUT)
    Flow: Deduct wallet → Send to Telegram → Admin marks Sent/Failed
    If Failed → Refund to wallet
    
    SECURITY: Uses authenticated user, no hardcoded identities.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get authenticated user's current balance
        user_record = await conn.fetchrow("""
            SELECT user_id, username, real_balance
            FROM users WHERE user_id = $1
        """, user.user_id)
        
        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check balance
        if float(user_record['real_balance']) < data.amount:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        
        order_id = str(uuid.uuid4())
        
        try:
            async with conn.transaction():
                # Deduct from wallet FIRST
                new_balance = float(user_record['real_balance']) - data.amount
                
                await conn.execute("""
                    UPDATE users 
                    SET real_balance = $1, updated_at = NOW()
                    WHERE user_id = $2
                """, new_balance, user.user_id)
                
                # Create withdrawal order
                await conn.execute("""
                    INSERT INTO orders (
                        order_id, user_id, username,
                        order_type, amount, total_amount,
                        status, metadata, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """, order_id, user.user_id, user.username,
                     'withdrawal_wallet', data.amount, data.amount,
                     'pending_approval', json.dumps({
                         'withdrawal_method': data.withdrawal_method,
                         'account_number': data.account_number,
                         'account_name': data.account_name,
                         'balance_deducted': True,  # IMPORTANT: Flag for refund
                         'balance_before': float(user_record['real_balance']),
                         'balance_after': new_balance
                     }))
                
                # Create ledger entry (debit - pending)
                await conn.execute("""
                    INSERT INTO wallet_ledger 
                    (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                     reference_type, reference_id, description, created_at)
                    VALUES ($1, $2, 'debit', $3, $4, $5, 'withdrawal', $6, $7, NOW())
                """, str(uuid.uuid4()), user.user_id, data.amount,
                     user_record['real_balance'], new_balance, order_id,
                     f"Withdrawal to {data.withdrawal_method} (pending)")
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")
        
        # Send to Telegram for approval
        background_tasks.add_task(send_withdrawal_telegram, order_id, 'wallet')
        
        return {
            "success": True,
            "order_id": order_id,
            "message": "Withdrawal request created. Balance deducted. Awaiting admin confirmation.",
            "status": "pending_approval",
            "new_balance": new_balance
        }


@router.post("/game")
async def withdraw_from_game(
    data: WithdrawalGameRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Withdraw from game account (Payment OUT)
    Flow: Redeem from game API → Add to wallet → Send to Telegram → Admin marks Sent
    
    SECURITY: Uses authenticated user, no hardcoded identities.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get authenticated user
        user_record = await conn.fetchrow("""
            SELECT user_id, username, real_balance
            FROM users WHERE user_id = $1
        """, user.user_id)
        
        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get game
        game = await conn.fetchrow("""
            SELECT game_id, game_name, display_name
            FROM games WHERE game_id = $1 AND is_active = TRUE
        """, data.game_id)
        
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        order_id = str(uuid.uuid4())
        
        try:
            # ==================== CALL GAMES API TO REDEEM ====================
            from ..services.games_api_service import GamesAPIClient
            
            async with GamesAPIClient() as games_api:
                redeem_response = await games_api.redeem(
                    game_id=game['game_id'],
                    user_id=user.user_id,
                    amount=data.amount,
                    remark=f"Withdrawal request - {order_id[:8]}"
                )
            
            logger.info(f"Game redeem successful: {redeem_response}")
            
            # Add redeemed amount to wallet
            async with conn.transaction():
                new_balance = float(user_record['real_balance']) + data.amount
                
                await conn.execute("""
                    UPDATE users 
                    SET real_balance = $1, updated_at = NOW()
                    WHERE user_id = $2
                """, new_balance, user.user_id)
                
                # Create withdrawal order
                await conn.execute("""
                    INSERT INTO orders (
                        order_id, user_id, username, game_name, game_display_name,
                        order_type, amount, total_amount,
                        status, metadata, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                """, order_id, user.user_id, user.username,
                     game['game_name'], game['display_name'],
                     'withdrawal_game', data.amount, data.amount,
                     'pending_approval', json.dumps({
                         'withdrawal_method': data.withdrawal_method,
                         'account_number': data.account_number,
                         'account_name': data.account_name,
                         'balance_deducted': False,  # Already in wallet
                         'game_redeem_response': redeem_response
                     }))
                
                # Create ledger entry (credit from game)
                await conn.execute("""
                    INSERT INTO wallet_ledger 
                    (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                     reference_type, reference_id, description, created_at)
                    VALUES ($1, $2, 'credit', $3, $4, $5, 'game_redeem', $6, $7, NOW())
                """, str(uuid.uuid4()), user.user_id, data.amount,
                     user_record['real_balance'], new_balance, order_id,
                     f"Redeemed from {game['display_name']}")
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Game redeem failed: {str(e)}")
        
        # Send to Telegram for final confirmation
        background_tasks.add_task(send_withdrawal_telegram, order_id, 'game')
        
        return {
            "success": True,
            "order_id": order_id,
            "message": "Game redeemed successfully. Awaiting bank transfer confirmation.",
            "status": "pending_approval",
            "wallet_balance": new_balance
        }


async def send_withdrawal_telegram(order_id: str, source: str):
    """Send withdrawal notification to Telegram"""
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
                SELECT order_id, username, amount, order_type, metadata, game_name
                FROM orders WHERE order_id = $1
            """, order_id)
            
            if not order:
                return
            
            metadata = order['metadata'] or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            method = metadata.get('withdrawal_method', 'N/A')
            account = metadata.get('account_number', 'N/A')
            
            bot = Bot(token=BOT_TOKEN)
            
            if source == 'wallet':
                message = f"""
💸 <b>Payment OUT - Wallet Withdrawal</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
💰 <b>Amount:</b> ${order['amount']:.2f}
💳 <b>Method:</b> {method}
🏦 <b>Account:</b> {account}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>⚠️ Balance ALREADY DEDUCTED from wallet</i>
<i>If failed, will auto-refund</i>
"""
            else:  # game
                message = f"""
💸 <b>Payment OUT - Game Withdrawal</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
🎯 <b>Game:</b> {order['game_name'].upper() if order['game_name'] else 'N/A'}
💰 <b>Amount:</b> ${order['amount']:.2f}
💳 <b>Method:</b> {method}
🏦 <b>Account:</b> {account}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>✓ Redeemed from game, now in wallet</i>
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Sent", callback_data=f"sent_{order_id}"),
                    InlineKeyboardButton("❌ Failed", callback_data=f"wfailed_{order_id}"),
                ],
                [
                    InlineKeyboardButton("🔄 Duplicate", callback_data=f"wduplicate_{order_id}"),
                    InlineKeyboardButton("⚠️ Suspicious", callback_data=f"wsuspicious_{order_id}"),
                ],
                [
                    InlineKeyboardButton("🏷️ Tag Changed", callback_data=f"wtagchanged_{order_id}"),
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
