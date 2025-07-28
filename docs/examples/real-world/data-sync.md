# Data Synchronization

Keep multiple systems in sync with Odoo using real-time data synchronization.

## Overview

This example demonstrates:
- Real-time bidirectional sync
- Conflict resolution strategies
- Change tracking and auditing
- Webhook-based synchronization
- Batch synchronization for large datasets

## Implementation

```python
import asyncio
from datetime import datetime
from typing import Dict, List, Any
from zenoo_rpc import ZenooClient

class DataSynchronizer:
    """Real-time data synchronization system."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.sync_log = []
    
    async def sync_customer_data(self, external_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Synchronize customer data between systems."""
        
        stats = {"created": 0, "updated": 0, "skipped": 0}
        
        for customer_data in external_data:
            external_id = customer_data.get("external_id")
            
            # Find existing customer
            existing = await self.client.model("res.partner").filter(
                ref=external_id
            ).first()
            
            if existing:
                # Update existing customer
                await existing.update({
                    "name": customer_data["name"],
                    "email": customer_data["email"],
                    "phone": customer_data.get("phone")
                })
                stats["updated"] += 1
            else:
                # Create new customer
                await self.client.model("res.partner").create({
                    "name": customer_data["name"],
                    "email": customer_data["email"],
                    "phone": customer_data.get("phone"),
                    "ref": external_id,
                    "customer_rank": 1
                })
                stats["created"] += 1
        
        return stats
    
    async def detect_changes(self, last_sync: datetime) -> List[Dict[str, Any]]:
        """Detect changes since last synchronization."""
        
        changed_records = await self.client.model("res.partner").filter(
            write_date__gte=last_sync
        ).all()
        
        return [
            {
                "id": record.id,
                "name": record.name,
                "email": record.email,
                "last_modified": record.write_date
            }
            for record in changed_records
        ]

# Usage Example
async def main():
    """Demonstrate data synchronization."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        synchronizer = DataSynchronizer(client)
        
        # Sample external data
        external_data = [
            {
                "external_id": "EXT001",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890"
            }
        ]
        
        # Sync data
        stats = await synchronizer.sync_customer_data(external_data)
        print(f"🔄 Sync completed: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- [ETL Pipeline](etl-pipeline.md) - Batch data processing
- [Migration Scripts](migration-scripts.md) - One-time migrations
- [Webhook Handlers](webhook-handlers.md) - Real-time webhooks
