"""
Telegram Bot Helper
Provides consistent access to Telegram bot functionality across the application.
All tokens are loaded from environment variables.
"""
import os
import logging
from typing import Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


def get_bot_token() -> str:
    """Get Telegram bot token from environment."""
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set in environment")
    return token


def get_chat_id() -> str:
    """Get default Telegram chat ID from environment."""
    return os.environ.get('TELEGRAM_CHAT_ID', '')


async def send_telegram_message(
    text: str,
    chat_id: Optional[str] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = 'HTML'
) -> Optional[dict]:
    """
    Send a message to Telegram.
    
    Args:
        text: Message text (HTML supported)
        chat_id: Target chat ID (uses env default if not provided)
        reply_markup: Optional inline keyboard
        parse_mode: Parse mode (HTML or Markdown)
    
    Returns:
        Message dict on success, None on failure
    """
    bot_token = get_bot_token()
    if not bot_token:
        logger.error("Cannot send Telegram message: BOT_TOKEN not configured")
        return None
    
    target_chat = chat_id or get_chat_id()
    if not target_chat:
        logger.error("Cannot send Telegram message: No chat_id provided or configured")
        return None
    
    try:
        bot = Bot(token=bot_token)
        message = await bot.send_message(
            chat_id=target_chat,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        logger.info(f"Telegram message sent to {target_chat}")
        return {"message_id": message.message_id, "chat_id": target_chat}
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return None


def create_approval_buttons(order_id: str, order_type: str = "load") -> InlineKeyboardMarkup:
    """
    Create standard approval buttons for orders.
    
    Args:
        order_id: The order ID to include in callbacks
        order_type: 'load' for wallet loads, 'withdraw' for withdrawals
    
    Returns:
        InlineKeyboardMarkup with appropriate buttons
    """
    if order_type == "withdraw":
        buttons = [
            [
                InlineKeyboardButton("✅ Sent", callback_data=f"sent_{order_id}"),
                InlineKeyboardButton("❌ Failed", callback_data=f"failed_{order_id}")
            ],
            [
                InlineKeyboardButton("🔄 Duplicate", callback_data=f"duplicate_{order_id}"),
                InlineKeyboardButton("⚠️ Suspicious", callback_data=f"suspicious_{order_id}")
            ]
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
                InlineKeyboardButton("❌ Failed", callback_data=f"failed_{order_id}")
            ],
            [
                InlineKeyboardButton("🔄 Duplicate", callback_data=f"duplicate_{order_id}"),
                InlineKeyboardButton("⚠️ Suspicious", callback_data=f"suspicious_{order_id}")
            ],
            [
                InlineKeyboardButton("✏️ Edit Amount", callback_data=f"editamt_{order_id}")
            ]
        ]
    
    return InlineKeyboardMarkup(buttons)
