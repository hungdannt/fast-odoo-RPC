# Migration Scripts

Migrate data from legacy systems to Odoo using Zenoo RPC.

## Overview

This example demonstrates:
- Legacy system data extraction
- Data mapping and transformation
- Validation and error handling
- Progress tracking and logging
- Rollback capabilities

## Implementation

```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from zenoo_rpc import ZenooClient

class DataMigrator:
    """Legacy system to Odoo data migration."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.migration_log = []
    
    async def migrate_customers(self, legacy_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Migrate customer data from legacy system."""
        
        results = {"success": 0, "failed": 0, "errors": []}
        
        for customer in legacy_data:
            try:
                # Transform legacy data to Odoo format
                odoo_customer = {
                    "name": customer["customer_name"],
                    "email": customer["email_address"],
                    "phone": customer["phone_number"],
                    "street": customer["address_line_1"],
                    "street2": customer.get("address_line_2"),
                    "city": customer["city"],
                    "zip": customer["postal_code"],
                    "customer_rank": 1,
                    "ref": f"LEGACY_{customer['legacy_id']}"
                }
                
                # Create customer in Odoo
                new_customer = await self.client.model("res.partner").create(odoo_customer)
                
                self.migration_log.append({
                    "legacy_id": customer["legacy_id"],
                    "odoo_id": new_customer.id,
                    "status": "success",
                    "timestamp": datetime.now()
                })
                
                results["success"] += 1
                
            except Exception as e:
                self.logger.error(f"Failed to migrate customer {customer.get('legacy_id')}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "legacy_id": customer.get("legacy_id"),
                    "error": str(e)
                })
        
        return results
    
    async def validate_migration(self) -> Dict[str, Any]:
        """Validate migration results."""
        
        validation_results = {
            "total_migrated": len(self.migration_log),
            "validation_errors": []
        }
        
        for log_entry in self.migration_log:
            if log_entry["status"] == "success":
                # Verify record exists in Odoo
                customer = await self.client.model("res.partner").filter(
                    id=log_entry["odoo_id"]
                ).first()
                
                if not customer:
                    validation_results["validation_errors"].append({
                        "legacy_id": log_entry["legacy_id"],
                        "error": "Record not found in Odoo"
                    })
        
        return validation_results

# Usage Example
async def main():
    """Demonstrate data migration."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        migrator = DataMigrator(client)
        
        # Sample legacy data
        legacy_customers = [
            {
                "legacy_id": "CUST001",
                "customer_name": "ABC Corp",
                "email_address": "contact@abc.com",
                "phone_number": "+1234567890",
                "address_line_1": "123 Main St",
                "city": "New York",
                "postal_code": "10001"
            }
        ]
        
        # Migrate data
        results = await migrator.migrate_customers(legacy_customers)
        print(f"📦 Migration completed: {results}")
        
        # Validate migration
        validation = await migrator.validate_migration()
        print(f"✅ Validation: {validation}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- [Data Synchronization](data-sync.md) - Ongoing sync
- [Backup and Restore](backup-restore.md) - Data protection
- [ETL Pipeline](etl-pipeline.md) - Regular data processing
