"""
Game Account Management Routes
Clients can create accounts, load, and redeem for each game
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone
import json
import logging
from ..core.database import get_pool

router = APIRouter(prefix="/game-accounts", tags=["game_accounts"])
logger = logging.getLogger(__name__)


class CreateAccountRequest(BaseModel):
    game_id: str = Field(description="Game ID (juwa, firekirin, etc)")
    username_hint: Optional[str] = Field(None, description="Preferred username")
    nickname: Optional[str] = Field(None, description="Display nickname")


class LoadGameRequest(BaseModel):
    game_id: str = Field(description="Game ID")
    amount: float = Field(gt=0, description="Amount to load")


class RedeemGameRequest(BaseModel):
    game_id: str = Field(description="Game ID")
    amount: float = Field(gt=0, description="Amount to redeem")
    withdrawal_method: str = Field(description="BANK, GCASH, etc")
    account_number: str
    account_name: str


@router.post("/create")
async def create_game_account(request: CreateAccountRequest):
    """
    Create a game account for the user
    Calls Games API to create account
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get user (simplified auth - replace with actual auth)
        user = await conn.fetchrow("""
            SELECT user_id, username FROM users WHERE username = 'testclient'
        """)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get game
        game = await conn.fetchrow("""
            SELECT game_id, game_name, display_name
            FROM games WHERE game_id = $1 AND is_active = TRUE
        """, request.game_id)
        
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Check if game_accounts table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'game_accounts'
            )
        """)
        
        if not table_exists:
            # Create the table
            await conn.execute("""
                CREATE TABLE game_accounts (
                    account_id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                    game_id VARCHAR(36) REFERENCES games(game_id),
                    game_name VARCHAR(100) NOT NULL,
                    game_account_id VARCHAR(100),
                    game_username VARCHAR(100),
                    game_password VARCHAR(255),
                    balance FLOAT DEFAULT 0.0,
                    status VARCHAR(20) DEFAULT 'active',
                    api_response JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, game_id)
                )
            """)
        
        # Check if account already exists
        existing = await conn.fetchrow("""
            SELECT account_id FROM game_accounts
            WHERE user_id = $1 AND game_id = $2
        """, user['user_id'], request.game_id)
        
        if existing:
            raise HTTPException(status_code=400, detail="Game account already exists")
        
        try:
            # Call Games API
            from ..services.games_api_service import GamesAPIClient
            
            username_hint = request.username_hint or user['username']
            
            async with GamesAPIClient() as games_api:
                api_response = await games_api.create_account(
                    game_id=request.game_id,
                    username_hint=username_hint,
                    nickname=request.nickname
                )
            
            logger.info(f"Game account created: {api_response}")
            
            # Store in database
            account_id = str(uuid.uuid4())
            game_account_id = api_response.get('account_id', user['user_id'])
            game_username = api_response.get('username', username_hint)
            game_password = api_response.get('password', 'N/A')
            
            await conn.execute("""
                INSERT INTO game_accounts (
                    account_id, user_id, game_id, game_name,
                    game_account_id, game_username, game_password,
                    balance, status, api_response, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
            """, account_id, user['user_id'], game['game_id'], game['game_name'],
                 game_account_id, game_username, game_password, 0.0, 'active',
                 json.dumps(api_response))
            
            return {
                "success": True,
                "message": "Game account created successfully",
                "account_id": account_id,
                "game_username": game_username,
                "game_password": game_password,
                "game_account_id": game_account_id
            }
            
        except Exception as e:
            logger.error(f"Create account failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create account: {str(e)}")


@router.post("/load")
async def load_game_account(request: LoadGameRequest):
    """
    Load game from wallet balance
    Deducts wallet, calls Games API recharge(), credits game
    
    Business Rules:
    - Cannot load if existing GAME balance exceeds configured limit (per-game)
    - Tracks total loaded amount for wagering requirements
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT user_id, username, real_balance FROM users WHERE username = 'testclient'
        """)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check balance
        if float(user['real_balance']) < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        
        # Get game with rules config
        game = await conn.fetchrow("""
            SELECT game_id, game_name, display_name, deposit_rules, withdrawal_rules 
            FROM games 
            WHERE game_id = $1 AND is_active = TRUE
        """, request.game_id)
        
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Parse deposit rules for per-game config
        deposit_rules = game.get('deposit_rules', {})
        if isinstance(deposit_rules, str):
            import json
            deposit_rules = json.loads(deposit_rules)
        
        # Get game balance threshold from per-game config (default $5 for backwards compat)
        game_balance_threshold = deposit_rules.get('block_if_balance_above', 5.0)
        
        # Check game account exists and get current balance
        game_account = await conn.fetchrow("""
            SELECT account_id, game_account_id, balance FROM game_accounts
            WHERE user_id = $1 AND game_id = $2
        """, user['user_id'], request.game_id)
        
        if not game_account:
            raise HTTPException(status_code=404, detail="Game account not found. Create account first.")
        
        # RULE 1: Cannot load if GAME balance exceeds configured limit
        current_game_balance = float(game_account['balance'] or 0)
        if current_game_balance > game_balance_threshold:
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": f"Cannot load. Current game balance (${current_game_balance:.2f}) exceeds maximum allowed (${game_balance_threshold:.2f}). Please redeem excess funds first.",
                    "error_code": "E3011",
                    "current_game_balance": current_game_balance,
                    "max_allowed": game_balance_threshold
                }
            )
        
        load_id = str(uuid.uuid4())
        new_wallet_balance = float(user['real_balance']) - request.amount
        new_game_balance = current_game_balance + request.amount
        
        try:
            # Call Games API to load
            from ..services.games_api_service import GamesAPIClient
            
            async with GamesAPIClient() as games_api:
                recharge_response = await games_api.recharge(
                    game_id=game['game_id'],
                    user_id=game_account['game_account_id'],
                    amount=request.amount,
                    remark=f"Load - {load_id[:8]}"
                )
            
            logger.info(f"Game recharged: {recharge_response}")
            
            # Update database
            async with conn.transaction():
                # Deduct from wallet
                await conn.execute("""
                    UPDATE users SET real_balance = $1, updated_at = NOW()
                    WHERE user_id = $2
                """, new_wallet_balance, user['user_id'])
                
                # Update game account balance and track total loaded
                await conn.execute("""
                    UPDATE game_accounts 
                    SET balance = balance + $1,
                        updated_at = NOW()
                    WHERE account_id = $2
                """, request.amount, game_account['account_id'])
                
                # Record load with wagering tracking
                await conn.execute("""
                    INSERT INTO game_loads (
                        load_id, user_id, game_id, game_name, amount,
                        wallet_balance_before, wallet_balance_after,
                        game_balance_before, game_balance_after,
                        status, game_credentials, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
                """, load_id, user['user_id'], game['game_id'], game['game_name'],
                     request.amount, user['real_balance'], new_wallet_balance,
                     current_game_balance, new_game_balance,
                     'completed', json.dumps(recharge_response))
                
                # Wallet ledger
                await conn.execute("""
                    INSERT INTO wallet_ledger (
                        ledger_id, user_id, transaction_type, amount,
                        balance_before, balance_after, reference_type,
                        reference_id, description, created_at
                    ) VALUES ($1, $2, 'debit', $3, $4, $5, 'game_load', $6, $7, NOW())
                """, str(uuid.uuid4()), user['user_id'], request.amount,
                     user['real_balance'], new_wallet_balance, load_id,
                     f"Loaded {game['display_name']}")
            
            return {
                "success": True,
                "message": "Game loaded successfully",
                "load_id": load_id,
                "amount": request.amount,
                "new_wallet_balance": new_wallet_balance,
                "new_game_balance": new_game_balance,
                "game": game['display_name']
            }
            
        except Exception as e:
            logger.error(f"Game load failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to load game: {str(e)}")


@router.post("/redeem")
async def redeem_from_game(
    request: RedeemGameRequest,
    background_tasks: BackgroundTasks
):
    """
    Redeem from game account
    Calls Games API redeem(), adds to wallet, sends to Telegram
    
    Business Rules:
    - Must meet 3x wagering requirement (balance >= 3x loaded amount)
    - Cannot redeem if balance exceeds 5x loaded amount (voided)
    - Resets wagering tracking after successful redeem
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT user_id, username, real_balance FROM users WHERE username = 'testclient'
        """)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get game
        game = await conn.fetchrow("""
            SELECT game_id, game_name, display_name, withdrawal_rules FROM games 
            WHERE game_id = $1 AND is_active = TRUE
        """, request.game_id)
        
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Parse withdrawal rules for per-game config
        withdrawal_rules = game.get('withdrawal_rules', {})
        if isinstance(withdrawal_rules, str):
            import json
            withdrawal_rules = json.loads(withdrawal_rules)
        
        # Get multipliers from per-game config (defaults for backwards compat)
        min_multiplier = withdrawal_rules.get('min_multiplier_of_deposit', 3.0)
        max_multiplier = withdrawal_rules.get('max_multiplier_of_deposit', 5.0)
        
        # Get game account with balance
        game_account = await conn.fetchrow("""
            SELECT account_id, game_account_id, balance FROM game_accounts
            WHERE user_id = $1 AND game_id = $2
        """, user['user_id'], request.game_id)
        
        if not game_account:
            raise HTTPException(status_code=404, detail="Game account not found")
        
        current_game_balance = float(game_account['balance'] or 0)
        
        # Calculate total loaded amount from game_loads since last withdrawal
        total_loaded_result = await conn.fetchrow("""
            SELECT COALESCE(SUM(amount), 0) as total_loaded
            FROM game_loads
            WHERE user_id = $1 AND game_id = $2 AND status = 'completed'
            AND created_at > (
                SELECT COALESCE(MAX(created_at), '1970-01-01'::timestamptz)
                FROM orders
                WHERE user_id = $1 AND game_name = $3 
                AND order_type = 'withdrawal_game' AND status = 'approved'
            )
        """, user['user_id'], request.game_id, game['game_name'])
        
        total_loaded = float(total_loaded_result['total_loaded'] or 0)
        
        if total_loaded == 0:
            raise HTTPException(status_code=400, detail="No loads found. Must load before redeeming.")
        
        # RULE 2: Check minimum multiplier requirement (default 3x)
        min_cashout = total_loaded * min_multiplier
        if current_game_balance < min_cashout:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Minimum cashout not met. Loaded: ${total_loaded:.2f}, Current: ${current_game_balance:.2f}, Required: ${min_cashout:.2f} ({min_multiplier}x)",
                    "error_code": "E3015",
                    "total_loaded": total_loaded,
                    "current_balance": current_game_balance,
                    "min_multiplier": min_multiplier,
                    "required_min": min_cashout
                }
            )
        
        # RULE 3: Check maximum multiplier limit - VOID excess, don't block
        max_balance = total_loaded * max_multiplier
        voided_amount = 0.0
        redeemable_amount = current_game_balance
        
        if current_game_balance > max_balance:
            # Calculate void amount
            voided_amount = current_game_balance - max_balance
            redeemable_amount = max_balance
            
            logger.warning(f"Balance exceeds {max_multiplier}x limit. Voiding ${voided_amount:.2f}")
        
        # Validate redeem amount (use redeemable_amount after void calculation)
        actual_redeem = min(request.amount, redeemable_amount)
        if actual_redeem <= 0:
            raise HTTPException(status_code=400, detail="No redeemable balance after voiding excess")
        
        order_id = str(uuid.uuid4())
        # New game balance after payout + void
        new_game_balance = 0  # Full redemption clears game balance
        
        try:
            # Redeem FULL balance from game API (payout + voided)
            total_to_redeem = actual_redeem + voided_amount
            from ..services.games_api_service import GamesAPIClient
            
            async with GamesAPIClient() as games_api:
                redeem_response = await games_api.redeem(
                    game_id=game['game_id'],
                    user_id=game_account['game_account_id'],
                    amount=total_to_redeem,  # Redeem full balance
                    remark=f"Redeem - {order_id[:8]}" + (f" (void ${voided_amount:.2f})" if voided_amount > 0 else "")
                )
            
            logger.info(f"Game redeemed: {redeem_response}")
            
            # Add ONLY payout amount to wallet (voided amount is lost)
            new_wallet_balance = float(user['real_balance']) + actual_redeem
            
            async with conn.transaction():
                # Update wallet balance (only payout, not voided)
                await conn.execute("""
                    UPDATE users SET real_balance = $1, updated_at = NOW()
                    WHERE user_id = $2
                """, new_wallet_balance, user['user_id'])
                
                # Update game account balance to 0 (full redemption)
                await conn.execute("""
                    UPDATE game_accounts 
                    SET balance = 0, updated_at = NOW()
                    WHERE account_id = $1
                """, game_account['account_id'])
                
                # Create withdrawal order with void recording
                await conn.execute("""
                    INSERT INTO orders (
                        order_id, user_id, username, game_name, game_display_name,
                        order_type, amount, total_amount, status, metadata, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                """, order_id, user['user_id'], user['username'],
                     game['game_name'], game['display_name'],
                     'withdrawal_game', actual_redeem, actual_redeem,
                     'pending_approval', json.dumps({
                         'withdrawal_method': request.withdrawal_method,
                         'account_number': request.account_number,
                         'account_name': request.account_name,
                         'balance_deducted': False,
                         'game_redeem_response': redeem_response,
                         'wagering_met': True,
                         'total_loaded': total_loaded,
                         'min_multiplier': min_multiplier,
                         'max_multiplier': max_multiplier,
                         'min_cashout': min_cashout,
                         'max_cashout': max_balance,
                         'original_game_balance': current_game_balance,
                         'payout_amount': actual_redeem,
                         'voided_amount': voided_amount,
                         'void_reason': 'EXCEEDS_MAX_MULTIPLIER' if voided_amount > 0 else None
                     }))
                
                # Wallet ledger - record payout
                await conn.execute("""
                    INSERT INTO wallet_ledger (
                        ledger_id, user_id, transaction_type, amount,
                        balance_before, balance_after, reference_type,
                        reference_id, description, created_at
                    ) VALUES ($1, $2, 'credit', $3, $4, $5, 'game_redeem', $6, $7, NOW())
                """, str(uuid.uuid4()), user['user_id'], actual_redeem,
                     user['real_balance'], new_wallet_balance, order_id,
                     f"Redeemed from {game['display_name']}" + (f" (voided: ${voided_amount:.2f})" if voided_amount > 0 else ""))
                
                # If void occurred, record it in audit
                if voided_amount > 0:
                    await conn.execute("""
                        INSERT INTO audit_logs (
                            log_id, user_id, username, action, resource_type, resource_id, details, created_at
                        ) VALUES ($1, $2, $3, 'withdrawal.void', 'order', $4, $5, NOW())
                    """, str(uuid.uuid4()), user['user_id'], user['username'], order_id,
                         json.dumps({
                             'voided_amount': voided_amount,
                             'reason': 'EXCEEDS_MAX_MULTIPLIER',
                             'max_multiplier': max_multiplier,
                             'total_loaded': total_loaded,
                             'original_balance': current_game_balance,
                             'payout_amount': actual_redeem
                         }))
            
            # Send to Telegram
            background_tasks.add_task(send_redeem_telegram, order_id)
            
            return {
                "success": True,
                "message": "Redeemed successfully. Awaiting bank transfer approval." + (f" ${voided_amount:.2f} voided due to {max_multiplier}x limit." if voided_amount > 0 else ""),
                "order_id": order_id,
                "payout_amount": actual_redeem,
                "voided_amount": voided_amount,
                "wallet_balance": new_wallet_balance,
                "remaining_game_balance": new_game_balance,
                "wagering_info": {
                    "total_loaded": total_loaded,
                    "min_multiplier": min_multiplier,
                    "max_multiplier": max_multiplier,
                    "minimum_cashout": min_cashout,
                    "maximum_cashout": max_balance,
                    "wagering_met": True
                }
            }
            
        except Exception as e:
            logger.error(f"Redeem failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to redeem: {str(e)}")


@router.get("/my-accounts")
async def get_my_game_accounts():
    """Get user's game accounts"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT user_id FROM users WHERE username = 'testclient'
        """)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if game_accounts table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'game_accounts'
            )
        """)
        
        if not table_exists:
            return {"accounts": []}
        
        accounts = await conn.fetch("""
            SELECT ga.account_id, ga.game_id, ga.game_name, ga.game_username,
                   ga.game_password, ga.balance, ga.status, ga.created_at,
                   g.display_name
            FROM game_accounts ga
            JOIN games g ON ga.game_id = g.game_id
            WHERE ga.user_id = $1
            ORDER BY ga.created_at DESC
        """, user['user_id'])
        
        return {
            "accounts": [dict(acc) for acc in accounts]
        }


async def send_redeem_telegram(order_id: str):
    """Send redeem notification to Telegram"""
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
                SELECT order_id, username, game_name, amount, metadata
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
                UPDATE orders SET telegram_message_id = $1, telegram_chat_id = $2
                WHERE order_id = $3
            """, str(sent.message_id), str(CHAT_ID), order_id)
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
