"""
Welcome Credit System
One-time credit claim for new users
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone
import logging
from ..core.database import get_pool
from .dependencies import authenticate_request, AuthResult

router = APIRouter(prefix="/portal/credits", tags=["credits"])
logger = logging.getLogger(__name__)


@router.get("/welcome")
async def check_welcome_credit(auth: AuthResult = Depends(authenticate_request)):
    """
    Check if user has unclaimed welcome credit
    Returns credit details if available
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get user from auth
        user = await conn.fetchrow("""
            SELECT user_id FROM users WHERE user_id = $1
        """, auth.user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user_credits table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'user_credits'
            )
        """)
        
        if not table_exists:
            return {"has_credit": False}
        
        # Check for unclaimed welcome credit
        credit = await conn.fetchrow("""
            SELECT credit_id, amount, credit_type
            FROM user_credits
            WHERE user_id = $1 
            AND credit_type = 'welcome_bonus'
            AND claimed = FALSE
        """, user['user_id'])
        
        if credit:
            return {
                "has_credit": True,
                "credit_id": credit['credit_id'],
                "amount": float(credit['amount']),
                "type": credit['credit_type']
            }
        else:
            return {"has_credit": False}


@router.post("/welcome/claim")
async def claim_welcome_credit(auth: AuthResult = Depends(authenticate_request)):
    """
    Claim welcome credit (one-time only)
    Adds amount to user's wallet balance
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get user from auth
        user = await conn.fetchrow("""
            SELECT user_id, username, real_balance
            FROM users WHERE user_id = $1
        """, auth.user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user_credits table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'user_credits'
            )
        """)
        
        if not table_exists:
            raise HTTPException(status_code=400, detail="No welcome credit available")
        
        # Get unclaimed credit
        credit = await conn.fetchrow("""
            SELECT credit_id, amount
            FROM user_credits
            WHERE user_id = $1 
            AND credit_type = 'welcome_bonus'
            AND claimed = FALSE
        """, user['user_id'])
        
        if not credit:
            raise HTTPException(status_code=400, detail="No welcome credit available")
        
        try:
            async with conn.transaction():
                # Mark credit as claimed
                await conn.execute("""
                    UPDATE user_credits
                    SET claimed = TRUE, claimed_at = NOW()
                    WHERE credit_id = $1
                """, credit['credit_id'])
                
                # Add to wallet
                new_balance = float(user['real_balance']) + float(credit['amount'])
                await conn.execute("""
                    UPDATE users
                    SET real_balance = $1, updated_at = NOW()
                    WHERE user_id = $2
                """, new_balance, user['user_id'])
                
                # Create ledger entry
                await conn.execute("""
                    INSERT INTO wallet_ledger (
                        ledger_id, user_id, transaction_type, amount,
                        balance_before, balance_after, reference_type,
                        reference_id, description, created_at
                    ) VALUES ($1, $2, 'credit', $3, $4, $5, 'welcome_credit', $6, $7, NOW())
                """, str(uuid.uuid4()), user['user_id'], credit['amount'],
                     user['real_balance'], new_balance, credit['credit_id'],
                     'Welcome bonus claimed')
            
            return {
                "success": True,
                "message": f"Welcome credit claimed: ${float(credit['amount']):.2f}",
                "new_balance": new_balance
            }
            
        except Exception as e:
            logger.error(f"Credit claim failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to claim credit")
