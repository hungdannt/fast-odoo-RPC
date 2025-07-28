# Database Integration

Integrate Zenoo RPC with various database systems for data synchronization and caching.

## Overview

This example demonstrates:
- PostgreSQL integration for data caching
- SQLite for local data storage
- MongoDB for document storage
- Redis for session and cache management
- Database synchronization patterns

## PostgreSQL Integration

```python
import asyncio
import asyncpg
from typing import Dict, List, Any, Optional
from zenoo_rpc import ZenooClient

class PostgreSQLSync:
    """PostgreSQL integration for Odoo data synchronization."""
    
    def __init__(self, pg_dsn: str, odoo_client: ZenooClient):
        self.pg_dsn = pg_dsn
        self.odoo_client = odoo_client
        self.pool = None
    
    async def initialize(self):
        """Initialize PostgreSQL connection pool."""
        self.pool = await asyncpg.create_pool(self.pg_dsn)
        
        # Create tables if they don't exist
        await self.create_tables()
    
    async def create_tables(self):
        """Create necessary tables."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS partners (
                    id SERIAL PRIMARY KEY,
                    odoo_id INTEGER UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    last_sync TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    odoo_id INTEGER UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    default_code VARCHAR(100),
                    list_price DECIMAL(10, 2),
                    last_sync TIMESTAMP DEFAULT NOW()
                )
            ''')
    
    async def sync_partners_from_odoo(self) -> int:
        """Sync partners from Odoo to PostgreSQL."""
        
        # Get partners from Odoo
        partners = await self.odoo_client.model("res.partner").filter(
            customer_rank__gt=0
        ).only("name", "email", "phone").all()
        
        synced_count = 0
        
        async with self.pool.acquire() as conn:
            for partner in partners:
                await conn.execute('''
                    INSERT INTO partners (odoo_id, name, email, phone)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (odoo_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        last_sync = NOW()
                ''', partner.id, partner.name, partner.email or '', partner.phone or '')
                
                synced_count += 1
        
        return synced_count
    
    async def get_cached_partners(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get cached partners from PostgreSQL."""
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM partners ORDER BY last_sync DESC LIMIT $1',
                limit
            )
            
            return [dict(row) for row in rows]
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

# Usage
async def main():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        pg_sync = PostgreSQLSync("postgresql://user:pass@localhost/dbname", client)
        await pg_sync.initialize()
        
        # Sync data
        count = await pg_sync.sync_partners_from_odoo()
        print(f"Synced {count} partners")
        
        # Get cached data
        partners = await pg_sync.get_cached_partners()
        print(f"Retrieved {len(partners)} cached partners")
        
        await pg_sync.close()
```

## SQLite Integration

```python
import sqlite3
import aiosqlite
from typing import Dict, List, Any

class SQLiteCache:
    """SQLite-based local cache for Odoo data."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize SQLite database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at INTEGER,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            await db.commit()
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set cache entry with TTL."""
        import time
        expires_at = int(time.time()) + ttl
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO cache_entries (key, value, expires_at)
                VALUES (?, ?, ?)
            ''', (key, value, expires_at))
            await db.commit()
    
    async def get(self, key: str) -> Optional[str]:
        """Get cache entry if not expired."""
        import time
        current_time = int(time.time())
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT value FROM cache_entries
                WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
            ''', (key, current_time))
            
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def cleanup_expired(self):
        """Remove expired cache entries."""
        import time
        current_time = int(time.time())
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'DELETE FROM cache_entries WHERE expires_at IS NOT NULL AND expires_at <= ?',
                (current_time,)
            )
            await db.commit()

# Usage with Odoo data
class OdooSQLiteCache:
    """Odoo-specific SQLite cache."""
    
    def __init__(self, db_path: str, odoo_client: ZenooClient):
        self.cache = SQLiteCache(db_path)
        self.odoo_client = odoo_client
    
    async def initialize(self):
        await self.cache.initialize()
    
    async def get_partner(self, partner_id: int) -> Optional[Dict[str, Any]]:
        """Get partner from cache or Odoo."""
        import json
        
        cache_key = f"partner_{partner_id}"
        cached_data = await self.cache.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # Fetch from Odoo
        partner = await self.odoo_client.model("res.partner").filter(
            id=partner_id
        ).first()
        
        if partner:
            partner_data = {
                "id": partner.id,
                "name": partner.name,
                "email": partner.email
            }
            
            # Cache for 1 hour
            await self.cache.set(cache_key, json.dumps(partner_data), ttl=3600)
            return partner_data
        
        return None
```

## MongoDB Integration

```python
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import json

class MongoDBSync:
    """MongoDB integration for document storage."""
    
    def __init__(self, mongo_uri: str, database_name: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[database_name]
    
    async def store_odoo_data(self, collection_name: str, data: List[Dict[str, Any]]):
        """Store Odoo data in MongoDB."""
        
        collection = self.db[collection_name]
        
        # Add metadata
        for item in data:
            item['_sync_timestamp'] = datetime.utcnow()
            item['_source'] = 'odoo'
        
        # Bulk insert
        if data:
            result = await collection.insert_many(data)
            return len(result.inserted_ids)
        
        return 0
    
    async def get_recent_data(self, collection_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recently synced data."""
        
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        collection = self.db[collection_name]
        cursor = collection.find({
            '_sync_timestamp': {'$gte': cutoff_time}
        }).sort('_sync_timestamp', -1)
        
        return await cursor.to_list(length=None)
    
    async def create_indexes(self):
        """Create useful indexes."""
        
        # Partners collection
        await self.db.partners.create_index([('email', 1)])
        await self.db.partners.create_index([('_sync_timestamp', -1)])
        
        # Products collection
        await self.db.products.create_index([('default_code', 1)])
        await self.db.products.create_index([('_sync_timestamp', -1)])
    
    async def close(self):
        """Close MongoDB connection."""
        self.client.close()

# Usage
async def sync_to_mongodb():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        mongo_sync = MongoDBSync("mongodb://localhost:27017", "odoo_sync")
        await mongo_sync.create_indexes()
        
        # Sync partners
        partners = await client.model("res.partner").filter(
            customer_rank__gt=0
        ).all()
        
        partner_data = [
            {
                "odoo_id": p.id,
                "name": p.name,
                "email": p.email,
                "phone": p.phone
            }
            for p in partners
        ]
        
        count = await mongo_sync.store_odoo_data("partners", partner_data)
        print(f"Stored {count} partners in MongoDB")
        
        await mongo_sync.close()
```

## Redis Integration

```python
import redis.asyncio as redis
import json
from typing import Optional, Dict, Any

class RedisCache:
    """Redis-based cache for Odoo data."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(self.redis_url)
    
    async def cache_odoo_query(self, query_key: str, data: Any, ttl: int = 300):
        """Cache Odoo query results."""
        
        serialized_data = json.dumps(data, default=str)
        await self.redis_client.setex(
            f"odoo_query:{query_key}",
            ttl,
            serialized_data
        )
    
    async def get_cached_query(self, query_key: str) -> Optional[Any]:
        """Get cached query results."""
        
        cached_data = await self.redis_client.get(f"odoo_query:{query_key}")
        if cached_data:
            return json.loads(cached_data)
        return None
    
    async def cache_partner_session(self, session_id: str, partner_data: Dict[str, Any], ttl: int = 1800):
        """Cache partner session data."""
        
        await self.redis_client.setex(
            f"partner_session:{session_id}",
            ttl,
            json.dumps(partner_data)
        )
    
    async def get_partner_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get partner session data."""
        
        session_data = await self.redis_client.get(f"partner_session:{session_id}")
        if session_data:
            return json.loads(session_data)
        return None
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

# Cached Odoo client wrapper
class CachedOdooClient:
    """Odoo client with Redis caching."""
    
    def __init__(self, odoo_client: ZenooClient, redis_cache: RedisCache):
        self.odoo_client = odoo_client
        self.cache = redis_cache
    
    async def get_partner_cached(self, partner_id: int) -> Optional[Dict[str, Any]]:
        """Get partner with caching."""
        
        cache_key = f"partner_{partner_id}"
        
        # Try cache first
        cached_partner = await self.cache.get_cached_query(cache_key)
        if cached_partner:
            return cached_partner
        
        # Fetch from Odoo
        partner = await self.odoo_client.model("res.partner").filter(
            id=partner_id
        ).first()
        
        if partner:
            partner_data = {
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "phone": partner.phone
            }
            
            # Cache for 5 minutes
            await self.cache.cache_odoo_query(cache_key, partner_data, ttl=300)
            return partner_data
        
        return None
```

## Database Synchronization Patterns

```python
class DatabaseSyncManager:
    """Manage synchronization across multiple databases."""
    
    def __init__(self, odoo_client: ZenooClient):
        self.odoo_client = odoo_client
        self.sync_targets = []
    
    def add_sync_target(self, target):
        """Add a synchronization target."""
        self.sync_targets.append(target)
    
    async def sync_all(self):
        """Synchronize data to all targets."""
        
        # Get data from Odoo
        partners = await self.odoo_client.model("res.partner").filter(
            customer_rank__gt=0
        ).all()
        
        products = await self.odoo_client.model("product.product").filter(
            active=True
        ).all()
        
        # Sync to all targets
        for target in self.sync_targets:
            if hasattr(target, 'sync_partners_from_odoo'):
                await target.sync_partners_from_odoo()
            
            if hasattr(target, 'store_odoo_data'):
                partner_data = [{"odoo_id": p.id, "name": p.name} for p in partners]
                await target.store_odoo_data("partners", partner_data)
    
    async def health_check(self):
        """Check health of all sync targets."""
        
        results = {}
        
        for i, target in enumerate(self.sync_targets):
            try:
                if hasattr(target, 'pool') and target.pool:
                    # PostgreSQL health check
                    async with target.pool.acquire() as conn:
                        await conn.fetchval('SELECT 1')
                    results[f"target_{i}"] = "healthy"
                
                elif hasattr(target, 'client') and target.client:
                    # MongoDB health check
                    await target.client.admin.command('ping')
                    results[f"target_{i}"] = "healthy"
                
                else:
                    results[f"target_{i}"] = "unknown"
                    
            except Exception as e:
                results[f"target_{i}"] = f"unhealthy: {str(e)}"
        
        return results

# Usage
async def main():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize sync targets
        pg_sync = PostgreSQLSync("postgresql://user:pass@localhost/db", client)
        await pg_sync.initialize()
        
        mongo_sync = MongoDBSync("mongodb://localhost:27017", "odoo_sync")
        await mongo_sync.create_indexes()
        
        redis_cache = RedisCache()
        await redis_cache.initialize()
        
        # Setup sync manager
        sync_manager = DatabaseSyncManager(client)
        sync_manager.add_sync_target(pg_sync)
        sync_manager.add_sync_target(mongo_sync)
        
        # Perform sync
        await sync_manager.sync_all()
        
        # Health check
        health = await sync_manager.health_check()
        print(f"Health check results: {health}")
        
        # Cleanup
        await pg_sync.close()
        await mongo_sync.close()
        await redis_cache.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

1. **Connection Pooling**: Use connection pools for database connections
2. **Batch Operations**: Process data in batches for better performance
3. **Error Handling**: Implement proper error handling and retries
4. **Indexing**: Create appropriate database indexes
5. **Monitoring**: Monitor database performance and sync status

## Next Steps

- [Django Integration](django-integration.md) - Django ORM integration
- [Celery Integration](celery-integration.md) - Background processing
- [Performance Optimization](../../advanced/performance.md) - Database optimization
