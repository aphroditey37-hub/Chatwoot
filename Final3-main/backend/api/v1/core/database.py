"""
API v1 Database Module - UNIFIED DATABASE LAYER
PostgreSQL connection and complete table management
"""
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import json
import uuid

from .config import get_api_settings

logger = logging.getLogger(__name__)
settings = get_api_settings()

# Connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get the database connection pool"""
    global _pool
    if _pool is None:
        raise Exception("Database not connected. Call init_api_v1_db() first.")
    return _pool


async def init_api_v1_db():
    """Initialize the unified database schema"""
    global _pool
    
    logger.info("Initializing unified database...")
    logger.info(f"Database pool config: min={settings.db_pool_min}, max={settings.db_pool_max}, timeout={settings.db_command_timeout}")
    
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        command_timeout=settings.db_command_timeout
    )
    
    async with _pool.acquire() as conn:
        # ==================== USERS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(20),
                referral_code VARCHAR(20) UNIQUE NOT NULL,
                referred_by_code VARCHAR(20),
                referred_by_user_id VARCHAR(36),
                role VARCHAR(20) DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                -- Client-specific fields
                bonus_percentage FLOAT DEFAULT 0.0,
                signup_bonus_claimed BOOLEAN DEFAULT FALSE,
                deposit_count INTEGER DEFAULT 0,
                total_deposited FLOAT DEFAULT 0.0,
                total_withdrawn FLOAT DEFAULT 0.0,
                real_balance FLOAT DEFAULT 0.0,
                bonus_balance FLOAT DEFAULT 0.0,
                play_credits FLOAT DEFAULT 0.0,
                cash_balance FLOAT DEFAULT 0.0,
                withdraw_locked BOOLEAN DEFAULT FALSE,
                deposit_locked BOOLEAN DEFAULT FALSE,
                -- Risk flags
                is_suspicious BOOLEAN DEFAULT FALSE,
                manual_approval_only BOOLEAN DEFAULT FALSE,
                no_bonus BOOLEAN DEFAULT FALSE,
                visibility_level VARCHAR(20) DEFAULT 'full',
                -- Metadata
                last_ip VARCHAR(45),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Add missing columns to users table (for existing databases)
        user_columns = [
            ("play_credits", "FLOAT DEFAULT 0.0"),
            ("cash_balance", "FLOAT DEFAULT 0.0"),
            ("is_suspicious", "BOOLEAN DEFAULT FALSE"),
            ("manual_approval_only", "BOOLEAN DEFAULT FALSE"),
            ("no_bonus", "BOOLEAN DEFAULT FALSE"),
            ("visibility_level", "VARCHAR(20) DEFAULT 'full'"),
        ]
        for col_name, col_def in user_columns:
            try:
                await conn.execute(f'ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_def}')
            except Exception as e:
                logger.debug(f"Column {col_name} may already exist: {e}")
        
        # ==================== USER IDENTITIES (FB/Chatwoot) ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_identities (
                identity_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                provider VARCHAR(50) NOT NULL,
                external_id VARCHAR(255) NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'active',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(provider, external_id)
            )
        ''')
        
        # ==================== MAGIC LINKS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS magic_links (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                consumed BOOLEAN DEFAULT FALSE,
                consumed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== SESSIONS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                access_token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_used_at TIMESTAMPTZ
            )
        ''')
        
        # ==================== GAMES ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id VARCHAR(36) PRIMARY KEY,
                game_name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(200) NOT NULL,
                description TEXT,
                thumbnail VARCHAR(500),
                category VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                min_deposit_amount FLOAT DEFAULT 10.0,
                max_deposit_amount FLOAT DEFAULT 10000.0,
                min_withdrawal_amount FLOAT DEFAULT 20.0,
                max_withdrawal_amount FLOAT DEFAULT 10000.0,
                bonus_rules JSONB DEFAULT '{}',
                deposit_rules JSONB DEFAULT '{}',
                withdrawal_rules JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== RULES ENGINE ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                rule_id VARCHAR(36) PRIMARY KEY,
                rule_type VARCHAR(50) NOT NULL,
                scope VARCHAR(20) NOT NULL DEFAULT 'global',
                scope_id VARCHAR(36),
                priority INTEGER DEFAULT 0,
                conditions JSONB DEFAULT '{}',
                actions JSONB DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                valid_from TIMESTAMPTZ,
                valid_until TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== REFERRAL PERKS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS referral_perks (
                perk_id VARCHAR(36) PRIMARY KEY,
                referral_code VARCHAR(20) NOT NULL,
                game_name VARCHAR(100),
                percent_bonus FLOAT DEFAULT 0.0,
                flat_bonus FLOAT DEFAULT 0.0,
                max_bonus FLOAT,
                min_amount FLOAT,
                valid_from TIMESTAMPTZ DEFAULT NOW(),
                valid_until TIMESTAMPTZ,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== PROMO CODES ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code_id VARCHAR(36) PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                credit_amount FLOAT NOT NULL,
                max_redemptions INTEGER,
                current_redemptions INTEGER DEFAULT 0,
                expires_at TIMESTAMPTZ,
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== PROMO CODE REDEMPTIONS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                redemption_id VARCHAR(36) PRIMARY KEY,
                code_id VARCHAR(36) REFERENCES promo_codes(code_id) ON DELETE CASCADE,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                credit_amount FLOAT NOT NULL,
                redeemed_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(code_id, user_id)
            )
        ''')
        
        # ==================== ADMIN WEBHOOKS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_webhooks (
                webhook_id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                url VARCHAR(500) NOT NULL,
                events TEXT[] DEFAULT ARRAY[]::TEXT[],
                enabled BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_delivery_at TIMESTAMPTZ,
                failure_count INTEGER DEFAULT 0
            )
        ''')
        
        # ==================== API KEYS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                key_hash VARCHAR(64) NOT NULL,
                key_prefix VARCHAR(12) NOT NULL,
                scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_used_at TIMESTAMPTZ,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # ==================== PAYMENT METHODS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS payment_methods (
                method_id VARCHAR(36) PRIMARY KEY,
                title VARCHAR(100) NOT NULL,
                tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                instructions TEXT DEFAULT '',
                enabled BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 0,
                rotation_enabled BOOLEAN DEFAULT FALSE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== CLIENT OVERRIDES ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS client_overrides (
                override_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                custom_deposit_bonus FLOAT,
                custom_cashout_min FLOAT,
                custom_cashout_max FLOAT,
                manual_approval_required BOOLEAN DEFAULT FALSE,
                bonus_disabled BOOLEAN DEFAULT FALSE,
                withdraw_disabled BOOLEAN DEFAULT FALSE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id)
            )
        ''')
        
        # ==================== ORDERS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id),
                username VARCHAR(50) NOT NULL,
                order_type VARCHAR(20) NOT NULL,
                game_name VARCHAR(100),
                game_display_name VARCHAR(200),
                amount FLOAT NOT NULL,
                bonus_amount FLOAT DEFAULT 0.0,
                total_amount FLOAT NOT NULL,
                -- Extended amounts for withdrawals
                payout_amount FLOAT DEFAULT 0.0,
                void_amount FLOAT DEFAULT 0.0,
                void_reason TEXT,
                play_credits_added FLOAT DEFAULT 0.0,
                cash_consumed FLOAT DEFAULT 0.0,
                play_credits_consumed FLOAT DEFAULT 0.0,
                bonus_consumed FLOAT DEFAULT 0.0,
                -- Referral tracking
                referral_code VARCHAR(20),
                referral_bonus_applied BOOLEAN DEFAULT FALSE,
                rule_applied TEXT,
                -- Order status
                status VARCHAR(30) DEFAULT 'initiated',
                is_suspicious BOOLEAN DEFAULT FALSE,
                -- PROOF IMAGE POLICY: Never store base64/image data in DB
                -- payment_proof_url: For metadata/reference ONLY (e.g., Telegram file_id)
                -- Actual proof images forwarded to Telegram via notification_router
                payment_proof_url VARCHAR(500),
                payment_proof_uploaded_at TIMESTAMPTZ,
                telegram_message_id VARCHAR(100),
                telegram_chat_id VARCHAR(100),
                rejection_reason TEXT,
                approved_by VARCHAR(36),
                approved_at TIMESTAMPTZ,
                idempotency_key VARCHAR(100) UNIQUE,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Add missing columns to orders table (for existing databases)
        order_columns = [
            ("payout_amount", "FLOAT DEFAULT 0.0"),
            ("void_amount", "FLOAT DEFAULT 0.0"),
            ("void_reason", "TEXT"),
            ("play_credits_added", "FLOAT DEFAULT 0.0"),
            ("cash_consumed", "FLOAT DEFAULT 0.0"),
            ("play_credits_consumed", "FLOAT DEFAULT 0.0"),
            ("bonus_consumed", "FLOAT DEFAULT 0.0"),
            ("is_suspicious", "BOOLEAN DEFAULT FALSE"),
            ("amount_adjusted", "BOOLEAN DEFAULT FALSE"),
            ("adjusted_by", "VARCHAR(100)"),
            ("adjusted_at", "TIMESTAMPTZ"),
            ("executed_at", "TIMESTAMPTZ"),
            ("execution_result", "TEXT"),
        ]
        for col_name, col_def in order_columns:
            try:
                await conn.execute(f'ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col_name} {col_def}')
            except Exception as e:
                logger.debug(f"Column {col_name} may already exist: {e}")
        
        # ==================== WEBHOOKS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS webhooks (
                webhook_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                webhook_url VARCHAR(500) NOT NULL,
                signing_secret VARCHAR(255) NOT NULL,
                subscribed_events TEXT[] DEFAULT ARRAY['order.created'],
                is_active BOOLEAN DEFAULT TRUE,
                failure_count INTEGER DEFAULT 0,
                last_triggered_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== WEBHOOK DELIVERIES ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                delivery_id VARCHAR(36) PRIMARY KEY,
                webhook_id VARCHAR(36) REFERENCES webhooks(webhook_id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                payload JSONB NOT NULL,
                response_status INTEGER,
                response_body TEXT,
                attempt_count INTEGER DEFAULT 1,
                delivered_at TIMESTAMPTZ,
                next_retry_at TIMESTAMPTZ,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== LEGACY TELEGRAM CONFIG TABLE DELETED ====================
        # Table telegram_config REMOVED per system requirements.
        # Use telegram_bots table (multi-bot system) ONLY.
        # If upgrading from old system, manually migrate data to telegram_bots.
        
        # ==================== SYSTEM SETTINGS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id VARCHAR(36) PRIMARY KEY DEFAULT 'global',
                api_enabled BOOLEAN DEFAULT TRUE,
                telegram_enabled BOOLEAN DEFAULT FALSE,
                manual_verification BOOLEAN DEFAULT TRUE,
                auto_approve_deposits BOOLEAN DEFAULT FALSE,
                auto_approve_withdrawals BOOLEAN DEFAULT FALSE,
                referral_system_enabled BOOLEAN DEFAULT TRUE,
                bonus_system_enabled BOOLEAN DEFAULT TRUE,
                webhook_enabled BOOLEAN DEFAULT TRUE,
                default_deposit_bonus FLOAT DEFAULT 0.0,
                signup_bonus FLOAT DEFAULT 0.0,
                default_referral_bonus FLOAT DEFAULT 5.0,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== AUDIT LOGS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36),
                username VARCHAR(50),
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id VARCHAR(100),
                old_value JSONB,
                new_value JSONB,
                details JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== REWARD DEFINITIONS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS reward_definitions (
                reward_id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                trigger_type VARCHAR(50) NOT NULL,
                reward_type VARCHAR(20) DEFAULT 'play_credits',
                value FLOAT NOT NULL,
                value_type VARCHAR(20) DEFAULT 'fixed',
                enabled BOOLEAN DEFAULT TRUE,
                is_one_time BOOLEAN DEFAULT TRUE,
                visible_to_client BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== REWARD GRANTS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS reward_grants (
                grant_id VARCHAR(36) PRIMARY KEY,
                reward_id VARCHAR(36) REFERENCES reward_definitions(reward_id) ON DELETE CASCADE,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                amount FLOAT NOT NULL,
                granted_by VARCHAR(36),
                reason TEXT,
                granted_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== PORTAL SESSIONS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS portal_sessions (
                session_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                session_token VARCHAR(100) UNIQUE NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Add missing columns to promo_codes table
        promo_columns = [
            ("description", "TEXT"),
            ("min_deposits", "INTEGER"),
            ("max_uses", "INTEGER"),
        ]
        for col_name, col_def in promo_columns:
            try:
                await conn.execute(f'ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS {col_name} {col_def}')
            except Exception as e:
                logger.debug(f"Column {col_name} may already exist: {e}")
        
        # ==================== CREATE INDEXES ====================
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_identities_external ON user_identities(provider, external_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_identities_user ON user_identities(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_magic_links_token ON magic_links(token)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(access_token)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_idempotency ON orders(idempotency_key)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_rules_type_scope ON rules(rule_type, scope)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)')
        
        # ==================== SEED DEFAULT DATA ====================
        # Seed games if empty
        game_count = await conn.fetchval("SELECT COUNT(*) FROM games")
        if game_count == 0:
            default_games = [
                ("dragon_quest", "Dragon Quest Online", "Epic fantasy MMORPG", 10.0, 5000.0, 20.0, 5000.0),
                ("speed_racer", "Speed Racer Pro", "High-octane racing game", 5.0, 1000.0, 10.0, 1000.0),
                ("battle_arena", "Battle Arena", "Competitive PvP battle game", 20.0, 10000.0, 50.0, 10000.0),
                ("puzzle_master", "Puzzle Master", "Brain-teasing puzzle game", 1.0, 500.0, 5.0, 500.0),
            ]
            for game_name, display_name, desc, min_dep, max_dep, min_wd, max_wd in default_games:
                bonus_rules = {
                    "default": {"percent_bonus": 5.0, "flat_bonus": 0, "max_bonus": max_dep * 0.1},
                    "first_deposit": {"percent_bonus": 10.0, "flat_bonus": 5.0, "max_bonus": max_dep * 0.2}
                }
                deposit_rules = {
                    "min_amount": min_dep,
                    "max_amount": max_dep,
                    "block_if_balance_above": max_dep * 2
                }
                withdrawal_rules = {
                    "min_amount": min_wd,
                    "max_amount": max_wd,
                    "min_multiplier_of_deposit": 1.0,
                    "max_multiplier_of_deposit": 3.0,
                    "require_full_balance": False
                }
                await conn.execute('''
                    INSERT INTO games (game_id, game_name, display_name, description, 
                                      min_deposit_amount, max_deposit_amount, 
                                      min_withdrawal_amount, max_withdrawal_amount,
                                      bonus_rules, deposit_rules, withdrawal_rules)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ''', str(uuid.uuid4()), game_name, display_name, desc, 
                   min_dep, max_dep, min_wd, max_wd,
                   json.dumps(bonus_rules), json.dumps(deposit_rules), json.dumps(withdrawal_rules))
        
        # Seed system settings if not exists
        settings_exists = await conn.fetchval("SELECT COUNT(*) FROM system_settings WHERE id = 'global'")
        if not settings_exists:
            await conn.execute('''
                INSERT INTO system_settings (id) VALUES ('global')
            ''')
        
        # Note: Legacy telegram_config seeding removed - use multi-bot system (telegram_bots table)
        
        # ==================== PAYMENT QR CODES ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS payment_qr (
                qr_id VARCHAR(36) PRIMARY KEY,
                payment_method VARCHAR(50) NOT NULL,
                label VARCHAR(100) NOT NULL,
                account_name VARCHAR(100),
                account_number VARCHAR(100),
                image_url TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_default BOOLEAN DEFAULT FALSE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== WALLET LOAD REQUESTS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS wallet_load_requests (
                request_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                amount FLOAT NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                qr_id VARCHAR(36) REFERENCES payment_qr(qr_id),
                proof_image_url TEXT,
                proof_image_hash VARCHAR(64),
                status VARCHAR(20) DEFAULT 'pending',
                reviewed_by VARCHAR(36),
                reviewed_at TIMESTAMPTZ,
                rejection_reason TEXT,
                telegram_message_id VARCHAR(100),
                telegram_chat_id VARCHAR(100),
                ip_address VARCHAR(45),
                device_fingerprint VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== WALLET TRANSACTIONS LEDGER (IMMUTABLE) ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS wallet_ledger (
                ledger_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                transaction_type VARCHAR(30) NOT NULL,
                amount FLOAT NOT NULL,
                balance_before FLOAT NOT NULL,
                balance_after FLOAT NOT NULL,
                reference_type VARCHAR(30),
                reference_id VARCHAR(36),
                description TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== GAME LOAD HISTORY ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS game_loads (
                load_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(user_id) ON DELETE CASCADE,
                game_id VARCHAR(36) REFERENCES games(game_id),
                game_name VARCHAR(100) NOT NULL,
                amount FLOAT NOT NULL,
                wallet_balance_before FLOAT NOT NULL,
                wallet_balance_after FLOAT NOT NULL,
                status VARCHAR(20) DEFAULT 'completed',
                game_credentials JSONB DEFAULT '{}',
                ip_address VARCHAR(45),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Add indexes for new tables
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_wallet_load_user ON wallet_load_requests(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_wallet_load_status ON wallet_load_requests(status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user ON wallet_ledger(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_game_loads_user ON game_loads(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_payment_qr_method ON payment_qr(payment_method)')
        
        # ==================== TELEGRAM BOTS (MULTI-BOT SYSTEM) ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS telegram_bots (
                bot_id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                bot_token TEXT NOT NULL,
                chat_id VARCHAR(100) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                can_approve_payments BOOLEAN DEFAULT FALSE,
                can_approve_wallet_loads BOOLEAN DEFAULT FALSE,
                can_approve_withdrawals BOOLEAN DEFAULT FALSE,
                description TEXT,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # ==================== TELEGRAM BOT EVENT PERMISSIONS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS telegram_bot_event_permissions (
                permission_id VARCHAR(36) PRIMARY KEY,
                bot_id VARCHAR(36) REFERENCES telegram_bots(bot_id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(bot_id, event_type)
            )
        ''')
        
        # ==================== NOTIFICATION LOGS ====================
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS notification_logs (
                log_id VARCHAR(36) PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                payload JSONB NOT NULL,
                sent_to_bot_ids TEXT[],
                success_bot_ids TEXT[],
                failed_bot_ids TEXT[],
                status VARCHAR(20) DEFAULT 'pending',
                error_details JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Indexes for notification system
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_telegram_bots_active ON telegram_bots(is_active)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_bot_permissions_bot ON telegram_bot_event_permissions(bot_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_bot_permissions_event ON telegram_bot_event_permissions(event_type)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_notification_logs_event ON notification_logs(event_type)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_notification_logs_created ON notification_logs(created_at)')
        
        logger.info("Unified database initialized successfully")


async def close_api_v1_db():
    """Close the database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection closed")


# ==================== HELPER FUNCTIONS ====================

async def fetch_one(query: str, *args) -> Optional[Dict]:
    """Fetch a single row"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict]:
    """Fetch all rows"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def execute(query: str, *args) -> str:
    """Execute a query"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def execute_returning(query: str, *args) -> Optional[Dict]:
    """Execute a query and return the result"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def execute_transaction(queries: List[tuple]):
    """Execute multiple queries in a transaction"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for query, args in queries:
                await conn.execute(query, *args)
