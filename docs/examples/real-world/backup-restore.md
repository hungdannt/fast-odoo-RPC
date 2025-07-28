# Backup and Restore

Automated backup and restore procedures for Odoo data using Zenoo RPC.

## Overview

This example demonstrates:
- Automated data backup
- Incremental backup strategies
- Data restoration procedures
- Backup validation and integrity checks
- Scheduled backup operations

## Implementation

```python
import asyncio
import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from zenoo_rpc import ZenooClient

class BackupManager:
    """Automated backup and restore system."""
    
    def __init__(self, client: ZenooClient, backup_dir: str = "./backups"):
        self.client = client
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    async def create_full_backup(self, models: List[str] = None) -> str:
        """Create a full backup of specified models."""
        
        if models is None:
            models = ["res.partner", "product.product", "sale.order"]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"full_backup_{timestamp}.json.gz"
        
        backup_data = {
            "backup_type": "full",
            "timestamp": timestamp,
            "models": {}
        }
        
        for model_name in models:
            print(f"Backing up {model_name}...")
            
            records = await self.client.model(model_name).all()
            
            backup_data["models"][model_name] = [
                {
                    "id": record.id,
                    "data": record._data
                }
                for record in records
            ]
        
        # Compress and save
        with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
            json.dump(backup_data, f, default=str, indent=2)
        
        print(f"✅ Backup created: {backup_file}")
        return str(backup_file)
    
    async def restore_from_backup(self, backup_file: str, models: List[str] = None) -> Dict[str, int]:
        """Restore data from backup file."""
        
        results = {"restored": 0, "skipped": 0, "errors": 0}
        
        # Load backup data
        with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        models_to_restore = models or list(backup_data["models"].keys())
        
        for model_name in models_to_restore:
            if model_name not in backup_data["models"]:
                continue
            
            print(f"Restoring {model_name}...")
            
            for record_data in backup_data["models"][model_name]:
                try:
                    # Check if record exists
                    existing = await self.client.model(model_name).filter(
                        id=record_data["id"]
                    ).first()
                    
                    if existing:
                        results["skipped"] += 1
                    else:
                        # Create new record
                        await self.client.model(model_name).create(record_data["data"])
                        results["restored"] += 1
                
                except Exception as e:
                    print(f"Error restoring record {record_data['id']}: {e}")
                    results["errors"] += 1
        
        return results
    
    async def validate_backup(self, backup_file: str) -> Dict[str, Any]:
        """Validate backup file integrity."""
        
        try:
            with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            validation = {
                "valid": True,
                "backup_type": backup_data.get("backup_type"),
                "timestamp": backup_data.get("timestamp"),
                "models_count": len(backup_data.get("models", {})),
                "total_records": sum(
                    len(records) for records in backup_data.get("models", {}).values()
                )
            }
            
            return validation
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

# Usage Example
async def main():
    """Demonstrate backup and restore operations."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        backup_manager = BackupManager(client)
        
        # Create backup
        backup_file = await backup_manager.create_full_backup([
            "res.partner", "product.product"
        ])
        
        # Validate backup
        validation = await backup_manager.validate_backup(backup_file)
        print(f"📋 Backup validation: {validation}")
        
        # Restore from backup (example)
        # results = await backup_manager.restore_from_backup(backup_file)
        # print(f"🔄 Restore results: {results}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Scheduled Backups

```python
import schedule
import time

def schedule_backups():
    """Schedule automated backups."""
    
    async def daily_backup():
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            backup_manager = BackupManager(client)
            await backup_manager.create_full_backup()
    
    schedule.every().day.at("02:00").do(lambda: asyncio.run(daily_backup()))
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

## Next Steps

- [Migration Scripts](migration-scripts.md) - Data migration
- [Data Synchronization](data-sync.md) - Real-time sync
- [ETL Pipeline](etl-pipeline.md) - Data processing
