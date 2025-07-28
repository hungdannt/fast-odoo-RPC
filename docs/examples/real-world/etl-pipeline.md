# ETL Pipeline

Extract, Transform, and Load data from external systems into Odoo using Zenoo RPC.

## Overview

This example demonstrates:
- Data extraction from various sources
- Data transformation and validation
- Efficient bulk loading into Odoo
- Error handling and logging
- Incremental data synchronization

## Implementation

```python
import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

class ETLPipeline:
    """ETL pipeline for data integration."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.batch_size = 100
    
    async def extract_from_csv(self, file_path: str) -> pd.DataFrame:
        """Extract data from CSV file."""
        return pd.read_csv(file_path)
    
    async def transform_customer_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Transform customer data for Odoo."""
        
        transformed_data = []
        
        for _, row in df.iterrows():
            customer_data = {
                "name": row.get("company_name") or f"{row.get('first_name', '')} {row.get('last_name', '')}".strip(),
                "email": row.get("email"),
                "phone": row.get("phone"),
                "street": row.get("address"),
                "city": row.get("city"),
                "zip": row.get("postal_code"),
                "country_id": await self._get_country_id(row.get("country")),
                "customer_rank": 1,
                "is_company": bool(row.get("company_name"))
            }
            
            # Clean and validate data
            customer_data = {k: v for k, v in customer_data.items() if v is not None}
            transformed_data.append(customer_data)
        
        return transformed_data
    
    async def load_customers(self, customer_data: List[Dict[str, Any]]) -> List[int]:
        """Load customer data into Odoo."""
        
        created_ids = []
        
        # Process in batches
        for i in range(0, len(customer_data), self.batch_size):
            batch = customer_data[i:i + self.batch_size]
            
            async with self.client.batch() as batch_manager:
                for customer in batch:
                    batch_manager.create("res.partner", customer)
                
                results = await batch_manager.execute()
                created_ids.extend([r.id for r in results if hasattr(r, 'id')])
        
        return created_ids
    
    async def _get_country_id(self, country_name: str) -> Optional[int]:
        """Get country ID by name."""
        if not country_name:
            return None
        
        country = await self.client.model("res.country").filter(
            name__ilike=country_name
        ).first()
        
        return country.id if country else None

# Usage Example
async def main():
    """Demonstrate ETL pipeline."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        pipeline = ETLPipeline(client)
        
        # Extract data
        df = await pipeline.extract_from_csv("customers.csv")
        print(f"📥 Extracted {len(df)} records")
        
        # Transform data
        transformed = await pipeline.transform_customer_data(df)
        print(f"🔄 Transformed {len(transformed)} records")
        
        # Load data
        created_ids = await pipeline.load_customers(transformed)
        print(f"📤 Loaded {len(created_ids)} customers")

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced ETL Features

### Incremental Sync

```python
async def incremental_sync(self, pipeline: ETLPipeline, last_sync_date: datetime):
    """Perform incremental data synchronization."""
    
    # Extract only new/modified records
    new_data = await pipeline.extract_incremental_data(last_sync_date)
    
    # Transform and load
    transformed = await pipeline.transform_customer_data(new_data)
    created_ids = await pipeline.load_customers(transformed)
    
    return created_ids
```

## Next Steps

- [Data Synchronization](data-sync.md) - Real-time sync
- [Migration Scripts](migration-scripts.md) - Legacy system migration
- [Backup and Restore](backup-restore.md) - Data backup strategies
