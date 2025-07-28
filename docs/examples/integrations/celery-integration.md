# Celery Integration

Background task processing with Celery and Zenoo RPC.

## Overview

This example demonstrates:
- Asynchronous task processing with Celery
- Odoo operations in background tasks
- Task scheduling and monitoring
- Error handling and retries
- Task result tracking

## Installation

```bash
pip install celery redis
pip install zenoo-rpc
```

## Configuration

```python
# celery_config.py
from celery import Celery
import asyncio
from zenoo_rpc import ZenooClient

# Create Celery app
app = Celery('odoo_tasks')

# Configuration
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'odoo_tasks.sync_partner': {'queue': 'odoo_sync'},
        'odoo_tasks.bulk_import': {'queue': 'bulk_operations'},
    }
)

# Odoo client configuration
ODOO_CONFIG = {
    'host': 'localhost',
    'port': 8069,
    'database': 'demo',
    'username': 'admin',
    'password': 'admin'
}

async def get_odoo_client():
    """Get configured Odoo client."""
    client = ZenooClient(ODOO_CONFIG['host'], port=ODOO_CONFIG['port'])
    await client.login(
        ODOO_CONFIG['database'],
        ODOO_CONFIG['username'],
        ODOO_CONFIG['password']
    )
    return client
```

## Basic Tasks

```python
# tasks.py
from celery import Celery
import asyncio
from typing import Dict, List, Any
from .celery_config import app, get_odoo_client

@app.task(bind=True, max_retries=3)
def sync_partner_task(self, partner_data: Dict[str, Any]):
    """Sync partner data to Odoo."""
    
    try:
        async def sync_partner():
            async with await get_odoo_client() as client:
                # Create or update partner
                existing = await client.model("res.partner").filter(
                    email=partner_data["email"]
                ).first()
                
                if existing:
                    await existing.update(partner_data)
                    return {"action": "updated", "id": existing.id}
                else:
                    partner = await client.model("res.partner").create(partner_data)
                    return {"action": "created", "id": partner.id}
        
        result = asyncio.run(sync_partner())
        return result
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@app.task
def bulk_import_partners(partner_list: List[Dict[str, Any]]):
    """Bulk import partners to Odoo."""
    
    async def import_partners():
        async with await get_odoo_client() as client:
            results = []
            
            # Use batch operations for efficiency
            async with client.batch() as batch:
                for partner_data in partner_list:
                    batch.create("res.partner", partner_data)
                
                batch_results = await batch.execute()
                
                for i, result in enumerate(batch_results):
                    results.append({
                        "index": i,
                        "id": result.id if hasattr(result, 'id') else None,
                        "status": "success" if hasattr(result, 'id') else "failed"
                    })
            
            return results
    
    return asyncio.run(import_partners())

@app.task
def generate_report_task(report_type: str, filters: Dict[str, Any]):
    """Generate report from Odoo data."""
    
    async def generate_report():
        async with await get_odoo_client() as client:
            if report_type == "sales_summary":
                orders = await client.model("sale.order").filter(**filters).all()
                
                total_revenue = sum(order.amount_total for order in orders)
                order_count = len(orders)
                
                return {
                    "report_type": report_type,
                    "total_revenue": total_revenue,
                    "order_count": order_count,
                    "filters": filters
                }
            
            return {"error": f"Unknown report type: {report_type}"}
    
    return asyncio.run(generate_report())
```

## Advanced Task Patterns

```python
# advanced_tasks.py
from celery import group, chain, chord
from .tasks import sync_partner_task, generate_report_task

@app.task
def process_customer_onboarding(customer_data: Dict[str, Any]):
    """Process complete customer onboarding workflow."""
    
    # Chain of tasks for customer onboarding
    workflow = chain(
        sync_partner_task.s(customer_data),
        send_welcome_email.s(),
        create_initial_order.s(customer_data.get("initial_order", {}))
    )
    
    return workflow.apply_async()

@app.task
def send_welcome_email(partner_result: Dict[str, Any]):
    """Send welcome email to new partner."""
    
    async def send_email():
        # Email sending logic here
        print(f"Sending welcome email to partner {partner_result['id']}")
        return {"email_sent": True, "partner_id": partner_result["id"]}
    
    return asyncio.run(send_email())

@app.task
def create_initial_order(email_result: Dict[str, Any], order_data: Dict[str, Any]):
    """Create initial order for new customer."""
    
    async def create_order():
        async with await get_odoo_client() as client:
            order_vals = {
                "partner_id": email_result["partner_id"],
                **order_data
            }
            
            order = await client.model("sale.order").create(order_vals)
            return {"order_id": order.id}
    
    return asyncio.run(create_order())

@app.task
def parallel_data_sync(data_sources: List[str]):
    """Sync data from multiple sources in parallel."""
    
    # Create parallel tasks
    sync_tasks = group(
        sync_from_source.s(source) for source in data_sources
    )
    
    # Execute in parallel and collect results
    job = sync_tasks.apply_async()
    results = job.get()
    
    return {"synced_sources": len(data_sources), "results": results}

@app.task
def sync_from_source(source: str):
    """Sync data from specific source."""
    
    async def sync_data():
        # Source-specific sync logic
        print(f"Syncing data from {source}")
        return {"source": source, "records_synced": 100}
    
    return asyncio.run(sync_data())
```

## Task Monitoring and Management

```python
# monitoring.py
from celery import Celery
from celery.events.state import State
from celery.events import EventReceiver

def monitor_tasks():
    """Monitor Celery task execution."""
    
    def on_task_sent(event):
        print(f"Task {event['uuid']} sent: {event['name']}")
    
    def on_task_received(event):
        print(f"Task {event['uuid']} received by worker")
    
    def on_task_started(event):
        print(f"Task {event['uuid']} started")
    
    def on_task_succeeded(event):
        print(f"Task {event['uuid']} succeeded in {event['runtime']}s")
    
    def on_task_failed(event):
        print(f"Task {event['uuid']} failed: {event['exception']}")
    
    # Set up event receiver
    state = State()
    
    with app.connection() as connection:
        recv = EventReceiver(connection, handlers={
            'task-sent': on_task_sent,
            'task-received': on_task_received,
            'task-started': on_task_started,
            'task-succeeded': on_task_succeeded,
            'task-failed': on_task_failed,
        })
        recv.capture(limit=None, timeout=None, wakeup=True)

@app.task
def cleanup_failed_tasks():
    """Clean up failed tasks and retry if appropriate."""
    
    # Get failed tasks from result backend
    # Implement cleanup logic
    pass

@app.task
def task_health_check():
    """Health check for task processing."""
    
    async def health_check():
        try:
            async with await get_odoo_client() as client:
                # Simple test query
                partners = await client.model("res.partner").limit(1).all()
                return {"status": "healthy", "odoo_connection": "ok"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    return asyncio.run(health_check())
```

## Periodic Tasks

```python
# periodic_tasks.py
from celery.schedules import crontab
from .tasks import generate_report_task, task_health_check

# Configure periodic tasks
app.conf.beat_schedule = {
    'daily-sales-report': {
        'task': 'tasks.generate_report_task',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
        'args': ('sales_summary', {'state': 'sale'})
    },
    'hourly-health-check': {
        'task': 'tasks.task_health_check',
        'schedule': crontab(minute=0),  # Every hour
    },
    'weekly-cleanup': {
        'task': 'tasks.cleanup_failed_tasks',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Monday 2 AM
    },
}

app.conf.timezone = 'UTC'
```

## Usage Examples

```python
# usage.py
from .tasks import sync_partner_task, bulk_import_partners, process_customer_onboarding

# Sync single partner
result = sync_partner_task.delay({
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
})

print(f"Task ID: {result.id}")
print(f"Result: {result.get()}")

# Bulk import
partners = [
    {"name": "Partner 1", "email": "p1@example.com"},
    {"name": "Partner 2", "email": "p2@example.com"},
]

bulk_result = bulk_import_partners.delay(partners)
print(f"Bulk import result: {bulk_result.get()}")

# Customer onboarding workflow
onboarding_result = process_customer_onboarding.delay({
    "name": "New Customer",
    "email": "new@example.com",
    "initial_order": {"product_id": 1, "quantity": 5}
})

print(f"Onboarding workflow started: {onboarding_result.id}")
```

## Error Handling and Retries

```python
# error_handling.py
from celery.exceptions import Retry
import logging

logger = logging.getLogger(__name__)

@app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5})
def robust_sync_task(self, data: Dict[str, Any]):
    """Robust sync task with comprehensive error handling."""
    
    try:
        async def sync_with_validation():
            # Validate data first
            if not data.get("email"):
                raise ValueError("Email is required")
            
            async with await get_odoo_client() as client:
                # Perform sync operation
                result = await client.model("res.partner").create(data)
                return {"success": True, "id": result.id}
        
        return asyncio.run(sync_with_validation())
        
    except ValueError as e:
        # Don't retry validation errors
        logger.error(f"Validation error: {e}")
        return {"success": False, "error": str(e)}
        
    except Exception as e:
        logger.warning(f"Task failed, retrying: {e}")
        # Exponential backoff
        countdown = 2 ** self.request.retries
        raise self.retry(exc=e, countdown=countdown)
```

## Best Practices

1. **Use Async Context Managers**: Always use `async with` for Odoo clients
2. **Batch Operations**: Use batch operations for bulk data processing
3. **Error Handling**: Implement proper error handling and retries
4. **Monitoring**: Set up task monitoring and alerting
5. **Resource Management**: Limit concurrent tasks to avoid overwhelming Odoo

## Next Steps

- [Django Integration](django-integration.md) - Django with Celery
- [Database Integration](database-integration.md) - Database patterns
- [Performance Optimization](../../advanced/performance.md) - Optimize task performance
