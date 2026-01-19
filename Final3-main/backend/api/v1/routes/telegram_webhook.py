"""
Telegram Webhook Handler - Full 6-button system with Edit Amount
Payment IN: Approve, Failed, Duplicate, Suspicious, Tag Changed, Edit Amount
Payment OUT: Sent, Failed, Duplicate, Suspicious, Tag Changed

SECURITY:
- Secret token verification (X-Telegram-Bot-Api-Secret-Token header)
- Replay protection (update_id deduplication)
- Timestamp validation
- All tokens from environment variables
"""
from fastapi import APIRouter, Request, Header, HTTPException
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional
import logging
import json
from datetime import datetime, timezone
import uuid
from ..core.database import get_pool
from ..core.webhook_security import (
    verify_telegram_webhook,
    get_telegram_bot_token,
    get_telegram_chat_id,
    telegram_replay_cache
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])

# Store pending edit amounts (in production, use Redis or database)
pending_edits = {}


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Handle Telegram webhook callbacks.
    
    Security:
    - Validates X-Telegram-Bot-Api-Secret-Token header
    - Rejects duplicate update_ids (replay protection)
    - Validates message timestamps (max 5 min old)
    """
    try:
        data = await request.json()
        logger.info(f"Telegram webhook received: {json.dumps(data)[:500]}")
        
        # ==================== SECURITY VERIFICATION ====================
        is_valid, error_msg = verify_telegram_webhook(data, x_telegram_bot_api_secret_token)
        if not is_valid:
            logger.warning(f"Telegram webhook security check failed: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)
        
        # Get bot token from environment (not hardcoded)
        bot_token = get_telegram_bot_token()
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            return {"status": "error", "message": "Bot not configured"}
        
        bot = Bot(token=bot_token)
        update = Update.de_json(data, bot)
        
        # Handle callback queries (button presses)
        if update.callback_query:
            query = update.callback_query
            callback_data = query.data
            admin_chat_id = str(query.from_user.id)
            admin_username = query.from_user.username or query.from_user.first_name
            
            logger.info(f"Callback received: {callback_data} from admin {admin_chat_id}")
            
            # ==================== ADMIN WHITELIST CHECK ====================
            from ..models.approval_security import verify_admin
            is_admin, admin_error = verify_admin(admin_chat_id)
            if not is_admin:
                await query.answer(f"❌ {admin_error}", show_alert=True)
                logger.warning(f"Unauthorized approval attempt: {admin_chat_id}")
                return {"status": "unauthorized"}
            
            # Parse: action_orderid or editset_orderid_amount
            if callback_data.startswith("editset_"):
                # Format: editset_{order_id}_{amount}
                parts = callback_data.split("_")
                if len(parts) >= 3:
                    order_id = parts[1]
                    new_amount = float(parts[2])
                    await handle_edit_amount_confirm(bot, order_id, new_amount, query, admin_chat_id, admin_username)
            elif "_" in callback_data:
                parts = callback_data.split("_", 1)
                action = parts[0]
                order_id = parts[1] if len(parts) > 1 else ""
                
                # Payment IN
                if action == "approve":
                    await handle_approve(bot, order_id, query, admin_chat_id, admin_username)
                elif action == "failed":
                    await handle_failed(bot, order_id, query, "Failed", admin_chat_id, admin_username)
                elif action == "duplicate":
                    await handle_failed(bot, order_id, query, "Duplicate", admin_chat_id, admin_username)
                elif action == "suspicious":
                    await handle_failed(bot, order_id, query, "Suspicious", admin_chat_id, admin_username)
                elif action == "tagchanged":
                    await handle_failed(bot, order_id, query, "Tag Changed", admin_chat_id, admin_username)
                elif action == "editamount":
                    await handle_edit_amount_show_options(bot, order_id, query)
                elif action == "editcancel":
                    await handle_edit_cancel(bot, order_id, query)
                
                # Payment OUT
                elif action == "sent":
                    await handle_sent(bot, order_id, query, admin_chat_id, admin_username)
                elif action == "wfailed":
                    await handle_withdrawal_failed(bot, order_id, query, "Failed", admin_chat_id, admin_username)
                elif action == "wduplicate":
                    await handle_withdrawal_failed(bot, order_id, query, "Duplicate", admin_chat_id, admin_username)
                elif action == "wsuspicious":
                    await handle_withdrawal_failed(bot, order_id, query, "Suspicious", admin_chat_id, admin_username)
                elif action == "wtagchanged":
                    await handle_withdrawal_failed(bot, order_id, query, "Tag Changed", admin_chat_id, admin_username)
            
            await query.answer()
        
        # Handle text messages (for custom amount input)
        elif update.message and update.message.text:
            chat_id = str(update.message.chat_id)
            text = update.message.text.strip()
            
            # Check if user is in edit mode for an order
            if chat_id in pending_edits:
                order_id = pending_edits[chat_id]
                try:
                    new_amount = float(text.replace("$", "").strip())
                    if new_amount > 0:
                        await handle_edit_amount_confirm(bot, order_id, new_amount, None, chat_id)
                        del pending_edits[chat_id]
                except ValueError:
                    await bot.send_message(
                        chat_id=chat_id,
                        text="❌ Invalid amount. Please enter a valid number (e.g., 50 or 50.00)"
                    )
        
        return {"status": "ok"}
    
    except HTTPException:
        # Re-raise HTTP exceptions (security rejections) 
        raise
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ==================== PAYMENT IN HANDLERS ====================

async def handle_approve(bot: Bot, order_id: str, query, admin_chat_id: str, admin_username: str):
    """
    Approve Payment IN - USES ORDER LIFECYCLE STATE MACHINE
    
    Flow: pending_approval -> approved -> processing -> completed
    
    Security:
    - Admin whitelist verified (done in main handler)
    - Expiry check
    - Single-use button check
    - All transitions via lifecycle helpers (idempotent)
    """
    from ..models.approval_security import (
        is_approval_expired, approval_token_cache, log_approval_action
    )
    from ..core.order_lifecycle import (
        approve_order, start_processing, complete_order, fail_order,
        OrderStatus, OrderErrorCode
    )
    from ..core.database import fetch_one, get_pool
    
    pool = await get_pool()
    
    try:
        # Get order for validation
        order = await fetch_one("""
            SELECT o.*, u.real_balance, u.user_id, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = $1
        """, order_id)
        
        if not order:
            await query.edit_message_text("❌ Order not found")
            return
        
        current_status = order.get('status', '')
        order_type = order.get('order_type', 'wallet_load')
        
        # ==================== EXPIRY CHECK ====================
        created_at = order.get('created_at')
        if created_at:
            is_expired, mins_remaining = is_approval_expired(created_at)
            if is_expired:
                await query.answer("❌ Approval request has expired", show_alert=True)
                logger.warning(f"Expired approval attempt: order={order_id}")
                return
        
        # ==================== SINGLE-USE CHECK ====================
        if not approval_token_cache.mark_used(order_id, "approve"):
            await query.answer("❌ This button has already been used", show_alert=True)
            logger.warning(f"Button reuse attempt: order={order_id}, action=approve")
            return
        
        # ==================== IDEMPOTENCY: Already approved? ====================
        normalized_status = OrderStatus.normalize(current_status)
        if normalized_status in [OrderStatus.APPROVED.value, OrderStatus.COMPLETED.value, OrderStatus.PROCESSING.value]:
            logger.info(f"Order {order_id} already approved (status={current_status}), no-op")
            await query.answer("✓ Already approved", show_alert=False)
            return
        
        if normalized_status in [OrderStatus.REJECTED.value, OrderStatus.FAILED.value, OrderStatus.CANCELLED.value]:
            await query.answer(f"❌ Order already {current_status}", show_alert=True)
            return
        
        # ==================== STEP 1: APPROVE (via lifecycle) ====================
        adjusted_amount = order.get('adjusted_amount')
        final_amount = float(adjusted_amount) if adjusted_amount else float(order['amount'])
        
        approve_result = await approve_order(
            order_id=order_id,
            actor_id=f"telegram:{admin_chat_id}",
            actor_type="telegram_bot",
            final_amount=final_amount if adjusted_amount else None,
            reason=f"Approved by @{admin_username}"
        )
        
        if not approve_result.success and not approve_result.is_noop:
            await query.answer(f"❌ Approval failed: {approve_result.message}", show_alert=True)
            return
        
        # ==================== STEP 2: PROCESS (via lifecycle) ====================
        processing_result = await start_processing(
            order_id=order_id,
            actor_id=f"telegram:{admin_chat_id}",
            actor_type="telegram_bot"
        )
        
        if not processing_result.success and not processing_result.is_noop:
            # Approval succeeded but processing failed - order is in approved state
            await query.answer(f"⚠️ Approved but processing failed: {processing_result.message}", show_alert=True)
            return
        
        # ==================== STEP 3: EXECUTE SIDE EFFECTS (wallet credit) ====================
        execution_success = False
        execution_error = None
        new_balance = 0
        
        async with pool.acquire() as conn:
            try:
                async with conn.transaction():
                    # Lock user row for balance update
                    user_locked = await conn.fetchrow("""
                        SELECT user_id, real_balance FROM users 
                        WHERE user_id = $1 FOR UPDATE
                    """, order['user_id'])
                    
                    current_balance = float(user_locked['real_balance'])
                    new_balance = current_balance + final_amount
                    
                    # Update user balance
                    await conn.execute("""
                        UPDATE users 
                        SET real_balance = $1, updated_at = NOW()
                        WHERE user_id = $2
                    """, new_balance, order['user_id'])
                    
                    # Record in ledger
                    await conn.execute("""
                        INSERT INTO wallet_ledger 
                        (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                         reference_type, reference_id, description, created_at)
                        VALUES ($1, $2, 'credit', $3, $4, $5, 'order', $6, $7, NOW())
                    """, str(uuid.uuid4()), order['user_id'], final_amount,
                         current_balance, new_balance, order_id,
                         f"Approved load - {order.get('game_name', 'wallet')}")
                    
                    execution_success = True
                    
            except Exception as e:
                execution_error = str(e)
                logger.error(f"Order {order_id} execution failed: {e}")
        
        # ==================== STEP 4: COMPLETE OR FAIL (via lifecycle) ====================
        if execution_success:
            await complete_order(
                order_id=order_id,
                actor_id=f"telegram:{admin_chat_id}",
                actor_type="telegram_bot",
                execution_result=f"Balance credited: ₱{final_amount:,.2f}"
            )
            
            # ==================== AUDIT LOG ====================
            await log_approval_action(
                None, order_id, "approve", admin_chat_id, admin_username,
                current_status, "completed", final_amount, order['user_id'],
                {"balance_before": current_balance, "balance_after": new_balance}
            )
            
            # Build success message
            adjustment_note = ""
            if adjusted_amount and float(adjusted_amount) != float(order['amount']):
                adjustment_note = f"\n📝 <b>Original:</b> ${float(order['amount']):.2f} → ${final_amount:.2f}"
            
            message = f"""
✅ <b>APPROVED - Payment IN</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> @{order['username']}
💰 <b>Amount:</b> ${final_amount:.2f}{adjustment_note}
💵 <b>Balance:</b> ${current_balance:.2f} → ${new_balance:.2f}
🕐 <b>Approved:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
👮 <b>By:</b> @{admin_username}
"""
            await query.edit_message_text(text=message, parse_mode="HTML")
            
        else:
            await fail_order(
                order_id=order_id,
                actor_id=f"telegram:{admin_chat_id}",
                actor_type="telegram_bot",
                error_message=execution_error
            )
            await query.answer(f"❌ Execution failed: {execution_error}", show_alert=True)
    
    except Exception as e:
        logger.error(f"Approval error for {order_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)


async def handle_failed(bot: Bot, order_id: str, query, reason: str, admin_chat_id: str, admin_username: str):
    """
    Handle failed Payment IN - USES ORDER LIFECYCLE STATE MACHINE
    
    Flow: pending_approval -> rejected
    """
    from ..models.approval_security import (
        is_approval_expired, approval_token_cache, log_approval_action
    )
    from ..core.order_lifecycle import reject_order, OrderStatus
    from ..core.database import fetch_one
    
    try:
        # Get order for validation
        order = await fetch_one("""
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = $1
        """, order_id)
        
        if not order:
            await query.edit_message_text("❌ Order not found")
            return
        
        current_status = order.get('status', '')
        
        # Expiry check
        created_at = order.get('created_at')
        if created_at:
            is_expired, _ = is_approval_expired(created_at)
            if is_expired:
                await query.answer("❌ Approval request has expired", show_alert=True)
                return
        
        # Single-use check
        if not approval_token_cache.mark_used(order_id, f"failed_{reason}"):
            await query.answer("❌ This button has already been used", show_alert=True)
            return
        
        # IDEMPOTENCY: Already processed?
        normalized_status = OrderStatus.normalize(current_status)
        if OrderStatus.is_terminal(normalized_status):
            await query.answer(f"✓ Order already {current_status}", show_alert=False)
            return
        
        # USE LIFECYCLE: Reject the order
        reject_result = await reject_order(
            order_id=order_id,
            actor_id=f"telegram:{admin_chat_id}",
            actor_type="telegram_bot",
            reason=reason
        )
        
        if not reject_result.success and not reject_result.is_noop:
            await query.answer(f"❌ Rejection failed: {reject_result.message}", show_alert=True)
            return
        
        # Audit log
        await log_approval_action(
            None, order_id, f"failed:{reason}", admin_chat_id, admin_username,
            current_status, "rejected", float(order['amount']), order['user_id']
        )
        
        message = f"""
❌ <b>FAILED - Payment IN</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
🎯 <b>Type:</b> {order.get('order_type', 'load').upper()}
💰 <b>Amount:</b> ${float(order['amount']):.2f}
⚠️ <b>Reason:</b> {reason}
👮 <b>By:</b> @{admin_username or admin_chat_id}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✗ Order rejected
"""
        await query.edit_message_text(message, parse_mode='HTML')
        logger.info(f"Order {order_id} rejected: {reason} by {admin_chat_id}")
    
    except Exception as e:
        logger.error(f"Rejection error for {order_id}: {str(e)}")
        await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)


async def handle_edit_amount_show_options(bot: Bot, order_id: str, query):
    """Show edit amount options with quick buttons"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = $1
        """, order_id)
        
        if not order:
            await query.edit_message_text("❌ Order not found")
            return
        
        current_amount = float(order['amount'])
        
        # Generate quick edit buttons with common adjustments
        adjustments = [
            int(current_amount * 0.5),   # 50%
            int(current_amount * 0.75),  # 75%
            int(current_amount),         # 100%
            int(current_amount * 1.25),  # 125%
            int(current_amount * 1.5),   # 150%
        ]
        # Remove duplicates and sort
        adjustments = sorted(list(set([a for a in adjustments if a > 0])))
        
        keyboard = []
        # First row: percentage-based amounts
        row1 = []
        for amt in adjustments[:3]:
            row1.append(InlineKeyboardButton(f"${amt}", callback_data=f"editset_{order_id}_{amt}"))
        if row1:
            keyboard.append(row1)
        
        # Second row: more amounts
        row2 = []
        for amt in adjustments[3:]:
            row2.append(InlineKeyboardButton(f"${amt}", callback_data=f"editset_{order_id}_{amt}"))
        if row2:
            keyboard.append(row2)
        
        # Third row: cancel and back to original
        keyboard.append([
            InlineKeyboardButton("🔙 Cancel", callback_data=f"editcancel_{order_id}"),
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
✏️ <b>EDIT AMOUNT - Payment IN</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
💰 <b>Current Amount:</b> ${current_amount:.2f}

<b>Select new amount:</b>
(Or reply with a custom amount like "75" or "75.50")
"""
        
        # Store that this chat is expecting an amount
        chat_id = str(query.message.chat_id)
        pending_edits[chat_id] = order_id
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
        logger.info(f"Edit amount options shown for order {order_id}")


async def handle_edit_amount_confirm(bot: Bot, order_id: str, new_amount: float, query=None, chat_id=None):
    """Confirm and save the edited amount"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = $1
        """, order_id)
        
        if not order:
            if query:
                await query.edit_message_text("❌ Order not found")
            return
        
        # Update the order with adjusted amount
        await conn.execute("""
            UPDATE orders 
            SET adjusted_amount = $1, adjusted_at = NOW(), adjusted_by = 'telegram_admin'
            WHERE order_id = $2
        """, new_amount, order_id)
        
        original_amount = float(order['amount'])
        
        # Build approval buttons
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
        
        message = f"""
💵 <b>AMOUNT UPDATED - Payment IN</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
🎯 <b>Type:</b> {order.get('order_type', 'load').upper()}

💰 <b>Original:</b> ${original_amount:.2f}
📝 <b>Adjusted to:</b> ${new_amount:.2f}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>Amount has been updated. Please approve or reject.</i>
"""
        
        if query:
            await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
        elif chat_id:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML', reply_markup=reply_markup)
        
        logger.info(f"Order {order_id} amount adjusted: ${original_amount} → ${new_amount}")


async def handle_edit_cancel(bot: Bot, order_id: str, query):
    """Cancel edit and show original buttons"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = $1
        """, order_id)
        
        if not order:
            await query.edit_message_text("❌ Order not found")
            return
        
        # Remove from pending edits
        chat_id = str(query.message.chat_id)
        if chat_id in pending_edits:
            del pending_edits[chat_id]
        
        # Show original message with buttons
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
        
        metadata = order['metadata'] or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        payment_method = metadata.get('payment_method', 'N/A')
        
        message = f"""
💵 <b>Payment IN - Wallet Load</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
💰 <b>Amount:</b> ${float(order['amount']):.2f}
💳 <b>Method:</b> {payment_method}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>Edit cancelled. Original amount restored.</i>
"""
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)


# ==================== PAYMENT OUT HANDLERS ====================

async def handle_sent(bot: Bot, order_id: str, query, admin_chat_id: str, admin_username: str):
    """
    Mark withdrawal as sent - USES ORDER LIFECYCLE STATE MACHINE
    
    Flow: pending_approval -> approved -> processing -> completed
    """
    from ..models.approval_security import (
        is_approval_expired, approval_token_cache, log_approval_action
    )
    from ..core.order_lifecycle import (
        approve_order, start_processing, complete_order, OrderStatus
    )
    from ..core.database import fetch_one
    
    try:
        # Get order for validation
        order = await fetch_one("""
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = $1
        """, order_id)
        
        if not order:
            await query.edit_message_text("❌ Order not found")
            return
        
        current_status = order.get('status', '')
        
        # Expiry check
        created_at = order.get('created_at')
        if created_at:
            is_expired, _ = is_approval_expired(created_at)
            if is_expired:
                await query.answer("❌ Approval request has expired", show_alert=True)
                return
        
        # Single-use check
        if not approval_token_cache.mark_used(order_id, "sent"):
            await query.answer("❌ This button has already been used", show_alert=True)
            return
        
        # IDEMPOTENCY: Already completed?
        normalized_status = OrderStatus.normalize(current_status)
        if normalized_status == OrderStatus.COMPLETED.value:
            await query.answer("✓ Already marked as sent", show_alert=False)
            return
        
        if normalized_status in [OrderStatus.FAILED.value, OrderStatus.REJECTED.value]:
            await query.answer(f"❌ Order already {current_status}", show_alert=True)
            return
        
        # USE LIFECYCLE: Approve -> Processing -> Complete
        if normalized_status == OrderStatus.PENDING_APPROVAL.value:
            await approve_order(order_id, f"telegram:{admin_chat_id}", "telegram_bot")
        
        await start_processing(order_id, f"telegram:{admin_chat_id}", "telegram_bot")
        
        await complete_order(
            order_id=order_id,
            actor_id=f"telegram:{admin_chat_id}",
            actor_type="telegram_bot",
            execution_result="Withdrawal sent"
        )
        
        # Audit log
        await log_approval_action(
            None, order_id, "sent", admin_chat_id, admin_username,
            current_status, "completed", float(order['amount']), order['user_id']
        )
        
        message = f"""
✅ <b>SENT - Payment OUT</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
🎯 <b>Type:</b> {order.get('order_type', 'withdrawal').upper()}
💰 <b>Amount:</b> ${float(order['amount']):.2f}
👮 <b>By:</b> @{admin_username or admin_chat_id}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✓ Withdrawal completed
"""
        await query.edit_message_text(message, parse_mode='HTML')
        logger.info(f"Withdrawal {order_id} sent by {admin_chat_id}")
    
    except Exception as e:
        logger.error(f"Sent error for {order_id}: {str(e)}")
        await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)


async def handle_withdrawal_failed(bot: Bot, order_id: str, query, reason: str, admin_chat_id: str, admin_username: str):
    """
    Handle failed withdrawal with auto-refund - USES ORDER LIFECYCLE
    
    Flow: pending_approval -> rejected (with refund if balance was deducted)
    """
    from ..models.approval_security import (
        is_approval_expired, approval_token_cache, log_approval_action
    )
    from ..core.order_lifecycle import reject_order, fail_order, OrderStatus
    from ..core.database import fetch_one
    
    pool = await get_pool()
    
    try:
        # Get order for validation
        order = await fetch_one("""
            SELECT o.*, u.real_balance, u.user_id, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = $1
        """, order_id)
        
        if not order:
            await query.edit_message_text("❌ Order not found")
            return
        
        current_status = order.get('status', '')
        
        # Expiry check
        created_at = order.get('created_at')
        if created_at:
            is_expired, _ = is_approval_expired(created_at)
            if is_expired:
                await query.answer("❌ Approval request has expired", show_alert=True)
                return
        
        # Single-use check
        if not approval_token_cache.mark_used(order_id, f"wfailed_{reason}"):
            await query.answer("❌ This button has already been used", show_alert=True)
            return
        
        # IDEMPOTENCY: Already processed?
        normalized_status = OrderStatus.normalize(current_status)
        if OrderStatus.is_terminal(normalized_status):
            await query.answer(f"✓ Order already {current_status}", show_alert=False)
            return
        
        # USE LIFECYCLE: Reject the order
        reject_result = await reject_order(
            order_id=order_id,
            actor_id=f"telegram:{admin_chat_id}",
            actor_type="telegram_bot",
            reason=reason
        )
        
        if not reject_result.success and not reject_result.is_noop:
            await query.answer(f"❌ Rejection failed: {reject_result.message}", show_alert=True)
            return
        
        # Refund if metadata indicates balance was deducted
        metadata = order['metadata'] or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        refund_text = ""
        new_balance = float(order['real_balance'])
        
        if metadata.get('balance_deducted'):
            async with pool.acquire() as conn:
                async with conn.transaction():
                    new_balance = float(order['real_balance']) + float(order['amount'])
                    await conn.execute("""
                        UPDATE users 
                        SET real_balance = $1, updated_at = NOW()
                        WHERE user_id = $2
                    """, new_balance, order['user_id'])
                    
                    await conn.execute("""
                        INSERT INTO wallet_ledger 
                        (ledger_id, user_id, transaction_type, amount, balance_before, balance_after,
                         reference_type, reference_id, description, created_at)
                        VALUES ($1, $2, 'credit', $3, $4, $5, 'refund', $6, $7, NOW())
                    """, str(uuid.uuid4()), order['user_id'], order['amount'],
                         order['real_balance'], new_balance, order_id,
                         f"Refund: {reason}")
            
            refund_text = f"\n💳 <b>Refunded:</b> ${float(order['amount']):.2f}"
        
        # Audit log
        await log_approval_action(
            None, order_id, f"wfailed:{reason}", admin_chat_id, admin_username,
            current_status, "rejected", float(order['amount']), order['user_id'],
            {"refunded": metadata.get('balance_deducted', False), "new_balance": new_balance}
        )
        
        message = f"""
❌ <b>FAILED - Payment OUT</b>

📋 <b>Order:</b> <code>{order_id[:8]}</code>
👤 <b>User:</b> {order['username']}
🎯 <b>Type:</b> {order.get('order_type', 'withdrawal').upper()}
💰 <b>Amount:</b> ${float(order['amount']):.2f}
⚠️ <b>Reason:</b> {reason}
👮 <b>By:</b> @{admin_username or admin_chat_id}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{refund_text}

✗ Withdrawal rejected
"""
        await query.edit_message_text(message, parse_mode='HTML')
        logger.info(f"Withdrawal {order_id} failed: {reason} by {admin_chat_id}")
    
    except Exception as e:
        logger.error(f"Withdrawal failed error for {order_id}: {str(e)}")
        await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
