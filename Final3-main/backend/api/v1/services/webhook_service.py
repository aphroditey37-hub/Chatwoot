"""
API v1 Webhook Service
Handles webhook registration, delivery, and retry logic
"""
import uuid
import json
import hmac
import hashlib
import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import get_api_settings, ErrorCodes
from ..core.security import generate_hmac_signature
from .auth_service import log_audit

settings = get_api_settings()


async def register_webhook(
    user_id: str,
    username: str,
    webhook_url: str,
    subscribed_events: List[str],
    signing_secret: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Register a new webhook.
    Returns (success, webhook/error)
    """
    # Validate URL format
    if not webhook_url.startswith(('http://', 'https://')):
        return False, {
            "message": "Invalid webhook URL format",
            "error_code": ErrorCodes.INVALID_WEBHOOK_URL
        }
    
    # Check for existing webhook with same URL
    existing = await fetch_one('''
        SELECT webhook_id FROM webhooks 
        WHERE user_id = $1 AND webhook_url = $2 AND is_active = TRUE
    ''', user_id, webhook_url)
    
    if existing:
        return False, {
            "message": "Webhook with this URL already exists",
            "error_code": ErrorCodes.WEBHOOK_REGISTRATION_FAILED
        }
    
    # Create webhook
    webhook_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    await execute('''
        INSERT INTO webhooks (webhook_id, user_id, webhook_url, signing_secret, subscribed_events)
        VALUES ($1, $2, $3, $4, $5)
    ''', webhook_id, user_id, webhook_url, signing_secret, subscribed_events)
    
    # Log audit
    await log_audit(user_id, username, "webhook.registered", "webhook", webhook_id, {
        "url": webhook_url,
        "events": subscribed_events
    })
    
    return True, {
        "webhook_id": webhook_id,
        "webhook_url": webhook_url,
        "subscribed_events": subscribed_events,
        "is_active": True,
        "created_at": now.isoformat()
    }


async def get_webhooks_for_event(event_type: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all active webhooks subscribed to an event"""
    query = '''
        SELECT * FROM webhooks 
        WHERE is_active = TRUE AND $1 = ANY(subscribed_events)
    '''
    params = [event_type]
    
    if user_id:
        query += " AND user_id = $2"
        params.append(user_id)
    
    return await fetch_all(query, *params)


async def trigger_webhooks(event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
    """
    Trigger webhooks for an event.
    This runs asynchronously in the background.
    """
    webhooks = await get_webhooks_for_event(event_type, user_id)
    
    for webhook in webhooks:
        # Create delivery record
        delivery_id = str(uuid.uuid4())
        payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        await execute('''
            INSERT INTO webhook_deliveries (delivery_id, webhook_id, event_type, payload, status)
            VALUES ($1, $2, $3, $4, 'pending')
        ''', delivery_id, webhook['webhook_id'], event_type, json.dumps(payload))
        
        # Schedule delivery (in production, use a task queue)
        asyncio.create_task(deliver_webhook(delivery_id))


async def deliver_webhook(delivery_id: str, attempt: int = 1):
    """
    Deliver a webhook with retry logic.
    """
    # Get delivery info
    delivery = await fetch_one('''
        SELECT d.*, w.webhook_url, w.signing_secret
        FROM webhook_deliveries d
        JOIN webhooks w ON d.webhook_id = w.webhook_id
        WHERE d.delivery_id = $1
    ''', delivery_id)
    
    if not delivery:
        return
    
    payload_str = delivery['payload'] if isinstance(delivery['payload'], str) else json.dumps(delivery['payload'])
    
    # Generate signature
    signature = generate_hmac_signature(payload_str, delivery['signing_secret'])
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Event": delivery['event_type'],
        "X-Webhook-Delivery-ID": delivery_id,
        "X-Webhook-Timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
            response = await client.post(
                delivery['webhook_url'],
                content=payload_str,
                headers=headers
            )
            
            # Update delivery status
            if 200 <= response.status_code < 300:
                await execute('''
                    UPDATE webhook_deliveries 
                    SET status = 'delivered', response_status = $1, response_body = $2, 
                        delivered_at = $3, attempt_count = $4
                    WHERE delivery_id = $5
                ''', response.status_code, response.text[:1000], datetime.now(timezone.utc), attempt, delivery_id)
                
                # Reset failure count on webhook
                await execute('''
                    UPDATE webhooks SET failure_count = 0, last_triggered_at = $1 
                    WHERE webhook_id = $2
                ''', datetime.now(timezone.utc), delivery['webhook_id'])
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
                
    except Exception as e:
        # Record failure
        await execute('''
            UPDATE webhook_deliveries 
            SET response_status = $1, response_body = $2, attempt_count = $3, status = 'failed'
            WHERE delivery_id = $4
        ''', 0, str(e)[:1000], attempt, delivery_id)
        
        # Increment webhook failure count
        await execute('''
            UPDATE webhooks SET failure_count = failure_count + 1 WHERE webhook_id = $1
        ''', delivery['webhook_id'])
        
        # Retry if under limit
        if attempt < settings.webhook_retry_attempts:
            delay = settings.webhook_retry_delay_seconds * (2 ** (attempt - 1))  # Exponential backoff
            
            await execute('''
                UPDATE webhook_deliveries SET next_retry_at = $1, status = 'retrying'
                WHERE delivery_id = $2
            ''', datetime.now(timezone.utc), delivery_id)
            
            await asyncio.sleep(delay)
            await deliver_webhook(delivery_id, attempt + 1)
        else:
            # Max retries reached
            await execute('''
                UPDATE webhook_deliveries SET status = 'failed' WHERE delivery_id = $1
            ''', delivery_id)
            
            # Deactivate webhook if too many failures
            webhook = await fetch_one(
                "SELECT failure_count FROM webhooks WHERE webhook_id = $1",
                delivery['webhook_id']
            )
            if webhook and webhook['failure_count'] >= 10:
                await execute('''
                    UPDATE webhooks SET is_active = FALSE WHERE webhook_id = $1
                ''', delivery['webhook_id'])


async def get_user_webhooks(user_id: str) -> List[Dict[str, Any]]:
    """Get all webhooks for a user"""
    webhooks = await fetch_all(
        "SELECT * FROM webhooks WHERE user_id = $1 ORDER BY created_at DESC",
        user_id
    )
    
    result = []
    for w in webhooks:
        result.append({
            "webhook_id": w['webhook_id'],
            "webhook_url": w['webhook_url'],
            "subscribed_events": w['subscribed_events'],
            "is_active": w['is_active'],
            "failure_count": w['failure_count'],
            "last_triggered_at": w['last_triggered_at'].isoformat() if w.get('last_triggered_at') else None,
            "created_at": w['created_at'].isoformat() if w.get('created_at') else None
        })
    
    return result


async def delete_webhook(user_id: str, webhook_id: str) -> bool:
    """Delete a webhook"""
    result = await execute('''
        UPDATE webhooks SET is_active = FALSE WHERE webhook_id = $1 AND user_id = $2
    ''', webhook_id, user_id)
    return True


async def get_webhook_deliveries(webhook_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get delivery history for a webhook"""
    deliveries = await fetch_all('''
        SELECT * FROM webhook_deliveries 
        WHERE webhook_id = $1 
        ORDER BY created_at DESC 
        LIMIT $2
    ''', webhook_id, limit)
    
    result = []
    for d in deliveries:
        result.append({
            "delivery_id": d['delivery_id'],
            "event_type": d['event_type'],
            "status": d['status'],
            "response_status": d.get('response_status'),
            "attempt_count": d['attempt_count'],
            "delivered_at": d['delivered_at'].isoformat() if d.get('delivered_at') else None,
            "created_at": d['created_at'].isoformat() if d.get('created_at') else None
        })
    
    return result
