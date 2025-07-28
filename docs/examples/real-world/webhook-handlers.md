# Webhook Handlers

Handle Odoo webhooks efficiently using Zenoo RPC.

## Overview

This example demonstrates:
- Webhook endpoint creation
- Event processing and validation
- Asynchronous webhook handling
- Error handling and retries
- Webhook security and authentication

## Implementation

```python
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
import asyncio
import hmac
import hashlib
from typing import Dict, Any
from zenoo_rpc import ZenooClient

app = FastAPI()
security = HTTPBearer()

class WebhookHandler:
    """Webhook event handler for Odoo integration."""
    
    def __init__(self, client: ZenooClient, webhook_secret: str):
        self.client = client
        self.webhook_secret = webhook_secret
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature."""
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    async def handle_customer_created(self, event_data: Dict[str, Any]):
        """Handle customer creation event."""
        
        customer_data = event_data.get("data", {})
        
        # Process customer creation
        await self.client.model("res.partner").create({
            "name": customer_data["name"],
            "email": customer_data["email"],
            "phone": customer_data.get("phone"),
            "customer_rank": 1,
            "ref": f"WEBHOOK_{customer_data['external_id']}"
        })
        
        print(f"Created customer: {customer_data['name']}")
    
    async def handle_order_updated(self, event_data: Dict[str, Any]):
        """Handle order update event."""
        
        order_data = event_data.get("data", {})
        order_id = order_data.get("order_id")
        
        # Update order status
        await self.client.model("sale.order").filter(
            id=order_id
        ).update({
            "state": order_data.get("status", "draft")
        })
        
        print(f"Updated order {order_id}: {order_data.get('status')}")
    
    async def process_webhook(self, event_type: str, event_data: Dict[str, Any]):
        """Process webhook event based on type."""
        
        handlers = {
            "customer.created": self.handle_customer_created,
            "order.updated": self.handle_order_updated
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(event_data)
        else:
            print(f"Unknown event type: {event_type}")

# Global webhook handler
webhook_handler = None

@app.on_event("startup")
async def startup_event():
    """Initialize webhook handler on startup."""
    
    global webhook_handler
    
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    
    webhook_handler = WebhookHandler(client, "your-webhook-secret")

@app.post("/webhook/odoo")
async def handle_odoo_webhook(request: Request):
    """Handle incoming Odoo webhook."""
    
    # Get request body and headers
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify signature
    if not webhook_handler.verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse event data
    event_data = await request.json()
    event_type = event_data.get("event_type")
    
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing event type")
    
    # Process webhook asynchronously
    asyncio.create_task(
        webhook_handler.process_webhook(event_type, event_data)
    )
    
    return {"status": "received"}

@app.post("/webhook/customer")
async def handle_customer_webhook(request: Request):
    """Handle customer-specific webhook."""
    
    event_data = await request.json()
    
    # Process customer event
    await webhook_handler.handle_customer_created(event_data)
    
    return {"status": "processed"}

@app.post("/webhook/order")
async def handle_order_webhook(request: Request):
    """Handle order-specific webhook."""
    
    event_data = await request.json()
    
    # Process order event
    await webhook_handler.handle_order_updated(event_data)
    
    return {"status": "processed"}

# Error handling middleware
@app.middleware("http")
async def webhook_error_handler(request: Request, call_next):
    """Handle webhook processing errors."""
    
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        print(f"Webhook error: {e}")
        # Log error and return success to prevent retries
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Webhook Security

```python
import jwt
from datetime import datetime, timedelta

class SecureWebhookHandler(WebhookHandler):
    """Enhanced webhook handler with JWT authentication."""
    
    def __init__(self, client: ZenooClient, jwt_secret: str):
        super().__init__(client, "")
        self.jwt_secret = jwt_secret
    
    def verify_jwt_token(self, token: str) -> bool:
        """Verify JWT token."""
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                return False
            
            return True
            
        except jwt.InvalidTokenError:
            return False

@app.post("/webhook/secure")
async def handle_secure_webhook(request: Request, token: str = Depends(security)):
    """Handle webhook with JWT authentication."""
    
    if not webhook_handler.verify_jwt_token(token.credentials):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    event_data = await request.json()
    
    # Process webhook
    await webhook_handler.process_webhook(
        event_data.get("event_type"),
        event_data
    )
    
    return {"status": "processed"}
```

## Webhook Testing

```python
import requests
import json

def test_webhook():
    """Test webhook endpoint."""
    
    test_data = {
        "event_type": "customer.created",
        "data": {
            "external_id": "TEST001",
            "name": "Test Customer",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
    }
    
    response = requests.post(
        "http://localhost:8000/webhook/customer",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    test_webhook()
```

## Next Steps

- [FastAPI Integration](fastapi-integration.md) - Advanced API features
- [Django Integration](django-integration.md) - Django webhooks
- [Automated Workflows](automated-workflows.md) - Workflow automation
