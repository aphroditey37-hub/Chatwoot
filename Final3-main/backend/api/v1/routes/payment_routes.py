"""
API v1 Payment Routes - UNIFIED
Payment proof handling using NotificationRouter (no direct Telegram calls)
NO PROOF IMAGE STORAGE - images forwarded to Telegram only
"""
from fastapi import APIRouter, Request, HTTPException, Header, Form
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import json
import logging

from ..core.database import fetch_one, fetch_all, execute, get_pool
from ..core.config import get_api_settings
from ..core.notification_router import emit_event, EventType
from .dependencies import check_rate_limiting, require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])
settings = get_api_settings()


# ==================== MODELS ====================

class PaymentProofUpload(BaseModel):
    """Payment proof upload request"""
    order_id: str
    image_data: str = Field(..., description="Base64 encoded image")
    image_type: str = Field(default="image/jpeg", description="MIME type")


class OrderActionRequest(BaseModel):
    """Order action request (approve/reject)"""
    action: str = Field(..., description="approve or reject")
    reason: Optional[str] = Field(None, description="Rejection reason")
    admin_notes: Optional[str] = None


# ==================== ENDPOINTS ====================


@router.get("/methods", summary="Get available payment methods")
async def get_payment_methods(request: Request):
    """Get all active payment methods with QR codes"""
    methods = await fetch_all("""
        SELECT pm.method_id, pm.title, pm.tags, pm.instructions, pm.enabled, pm.priority
        FROM payment_methods pm
        WHERE pm.enabled = TRUE
        ORDER BY pm.priority ASC
    """)
    
    result = []
    for method in methods:
        # Get QR codes for this method - join by title since that's how QR codes are linked
        qr_codes = await fetch_all("""
            SELECT qr_id, label, account_name, account_number, image_url, is_default
            FROM payment_qr
            WHERE payment_method = $1 AND is_active = TRUE
            ORDER BY is_default DESC, label ASC
        """, method['title'])
        
        result.append({
            "method_id": method['method_id'],
            "title": method['title'],
            "tags": method['tags'],
            "instructions": method['instructions'],
            "enabled": method['enabled'],
            "qr_codes": [dict(qr) for qr in qr_codes]
        })
    
    return {"success": True, "methods": result}


@router.post(
    "/proof/{order_id}",
    summary="Upload payment proof",
    description="""
    Upload a payment screenshot for an order.
    Image is forwarded to Telegram via NotificationRouter and NOT stored in DB.
    """
)
async def upload_payment_proof(
    request: Request,
    order_id: str,
    image_data: str = Form(..., description="Base64 encoded image"),
    image_type: str = Form(default="image/jpeg"),
    authorization: str = Header(None, alias="Authorization")
):
    """Upload payment proof image - forwards to Telegram, does NOT store"""
    await check_rate_limiting(request)
    
    # Get order
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check order status
    if order['status'] not in ['initiated', 'awaiting_payment_proof']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload proof for order in '{order['status']}' status"
        )
    
    now = datetime.now(timezone.utc)
    
    # Update order status to PENDING_REVIEW (NO proof_url stored)
    # CANONICAL STATUS: PENDING_REVIEW (awaiting admin approval)
    await execute('''
        UPDATE orders 
        SET payment_proof_uploaded_at = $1,
            status = 'PENDING_REVIEW',
            updated_at = NOW()
        WHERE order_id = $2
    ''', now, order_id)
    
    # Log audit
    await log_audit(order['user_id'], order['username'], "payment.proof_uploaded", "order", order_id)
    
    # Emit notification via NotificationRouter with image
    # The router will forward the image to Telegram
    try:
        await emit_event(
            event_type=EventType.ORDER_CREATED,
            title=f"💰 New {order['order_type'].upper()} Request",
            message=f"User: @{order['username']}\nGame: {order.get('game_display_name', order.get('game_name', 'N/A'))}\nAmount: ₱{order['amount']:,.2f}\nBonus: ₱{order['bonus_amount']:,.2f}\nTotal: ₱{order['total_amount']:,.2f}",
            reference_id=order_id,
            reference_type="order",
            user_id=order['user_id'],
            username=order['username'],
            display_name=order.get('display_name'),
            amount=order['amount'],
            extra_data={
                "order_type": order['order_type'],
                "game_name": order.get('game_name'),
                "bonus_amount": order['bonus_amount'],
                "image_data": image_data,  # Image passed to router for Telegram
                "image_type": image_type
            },
            requires_action=True
        )
        telegram_sent = True
    except Exception as e:
        logger.error(f"Failed to emit notification: {e}")
        telegram_sent = False
    
    return {
        "success": True,
        "message": "Payment proof submitted successfully",
        "order_id": order_id,
        "status": "pending_review",
        "telegram_sent": telegram_sent
    }


@router.post(
    "/action/{order_id}",
    summary="Process order action",
    description="Admin: Approve or reject an order"
)
async def process_order_action(
    request: Request,
    order_id: str,
    data: OrderActionRequest,
    authorization: str = Header(..., alias="Authorization")
):
    """Process order approval/rejection"""
    auth = await require_auth(request, authorization=authorization)
    
    # Check admin role
    admin = await fetch_one("SELECT role FROM users WHERE user_id = $1", auth.user_id)
    if not admin or admin['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get order
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Accept both legacy and canonical pending statuses
    valid_pending_statuses = ['pending_review', 'PENDING_REVIEW', 'awaiting_payment_proof', 'initiated', 'pending']
    if order['status'] not in valid_pending_statuses:
        raise HTTPException(status_code=400, detail=f"Cannot process order in '{order['status']}' status")
    
    now = datetime.now(timezone.utc)
    
    if data.action == 'approve':
        # CANONICAL STATUS: APPROVED_EXECUTED
        new_status = 'APPROVED_EXECUTED'
        
        # Update user balances based on order type
        if order['order_type'] == 'deposit':
            await execute('''
                UPDATE users 
                SET real_balance = real_balance + $1,
                    bonus_balance = bonus_balance + $2,
                    deposit_count = deposit_count + 1,
                    total_deposited = total_deposited + $3,
                    updated_at = NOW()
                WHERE user_id = $4
            ''', order['amount'], order['bonus_amount'], order['amount'], order['user_id'])
        elif order['order_type'] == 'withdrawal':
            await execute('''
                UPDATE users 
                SET real_balance = real_balance - $1,
                    total_withdrawn = total_withdrawn + $1,
                    updated_at = NOW()
                WHERE user_id = $2
            ''', order['amount'], order['user_id'])
        
        await execute('''
            UPDATE orders 
            SET status = $1, approved_by = $2, approved_at = $3, executed_at = $4, 
                execution_result = 'Executed via admin UI', updated_at = NOW()
            WHERE order_id = $5
        ''', new_status, auth.user_id, now, now, order_id)
        
        await log_audit(auth.user_id, auth.username, "order.approved", "order", order_id, {
            "amount": order['amount'],
            "type": order['order_type'],
            "final_status": "APPROVED_EXECUTED"
        })
        
        # Emit ORDER_APPROVED notification
        await emit_event(
            event_type=EventType.ORDER_APPROVED,
            title="✅ Order Approved & Executed",
            message=f"Order for @{order['username']} approved\nAmount: ₱{order['amount']:,.2f}",
            reference_id=order_id,
            reference_type="order",
            user_id=order['user_id'],
            username=order['username'],
            amount=order['amount'],
            extra_data={"final_status": "APPROVED_EXECUTED"},
            requires_action=False
        )
        
    elif data.action == 'reject':
        # CANONICAL STATUS: REJECTED
        new_status = 'REJECTED'
        
        await execute('''
            UPDATE orders 
            SET status = $1, rejection_reason = $2, approved_by = $3, approved_at = $4, updated_at = NOW()
            WHERE order_id = $5
        ''', new_status, data.reason or 'Rejected by admin', auth.user_id, now, order_id)
        
        await log_audit(auth.user_id, auth.username, "order.rejected", "order", order_id, {
            "reason": data.reason
        })
        
        # Emit ORDER_REJECTED notification
        await emit_event(
            event_type=EventType.ORDER_REJECTED,
            title="❌ Order Rejected",
            message=f"Order for @{order['username']} rejected\nReason: {data.reason or 'Admin rejection'}",
            reference_id=order_id,
            reference_type="order",
            user_id=order['user_id'],
            username=order['username'],
            amount=order['amount'],
            extra_data={"reason": data.reason, "final_status": "REJECTED"},
            requires_action=False
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
    
    return {
        "success": True,
        "message": f"Order {new_status}",
        "order_id": order_id,
        "status": new_status
    }


# ==================== HELPER ====================

async def log_audit(user_id, username, action, resource_type, resource_id, details=None):
    """Log audit event"""
    log_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO audit_logs (log_id, user_id, username, action, resource_type, resource_id, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    ''', log_id, user_id, username, action, resource_type, resource_id,
       json.dumps(details) if details else None)
