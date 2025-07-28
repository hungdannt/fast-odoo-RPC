# Manager Classes

Core manager classes for Zenoo RPC operations.

## Overview

Manager classes provide high-level interfaces for:
- Transaction management
- Cache management
- Connection management
- Resource lifecycle management

## TransactionManager

### Class Reference

```python
class TransactionManager:
    """Manages database transactions and savepoints."""
    
    def __init__(self, client: ZenooClient):
        """Initialize transaction manager.
        
        Args:
            client: Zenoo RPC client instance
        """
        self.client = client
        self.active_transactions = {}
        self.transaction_counter = 0
    
    async def begin_transaction(self, isolation_level: str = None) -> Transaction:
        """Begin a new transaction.
        
        Args:
            isolation_level: Transaction isolation level
            
        Returns:
            Transaction instance
        """
        pass
    
    async def commit_transaction(self, transaction_id: str):
        """Commit a transaction.
        
        Args:
            transaction_id: ID of transaction to commit
        """
        pass
    
    async def rollback_transaction(self, transaction_id: str):
        """Rollback a transaction.
        
        Args:
            transaction_id: ID of transaction to rollback
        """
        pass
    
    async def create_savepoint(self, transaction_id: str, savepoint_name: str) -> str:
        """Create a savepoint within a transaction.
        
        Args:
            transaction_id: ID of parent transaction
            savepoint_name: Name for the savepoint
            
        Returns:
            Savepoint ID
        """
        pass
```

### Usage Examples

```python
async def use_transaction_manager():
    """Demonstrate transaction manager usage."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        tx_manager = TransactionManager(client)
        
        # Begin transaction
        tx = await tx_manager.begin_transaction()
        
        try:
            # Perform operations
            partner = await client.model("res.partner").create({
                "name": "Managed Transaction Partner"
            })
            
            # Create savepoint
            savepoint = await tx_manager.create_savepoint(tx.id, "after_partner")
            
            try:
                product = await client.model("product.product").create({
                    "name": "Managed Transaction Product"
                })
                
                # Commit transaction
                await tx_manager.commit_transaction(tx.id)
                print("Transaction committed successfully")
                
            except Exception as e:
                # Rollback to savepoint
                await tx_manager.rollback_to_savepoint(tx.id, savepoint)
                print(f"Rolled back to savepoint: {e}")
                
        except Exception as e:
            # Rollback entire transaction
            await tx_manager.rollback_transaction(tx.id)
            print(f"Transaction rolled back: {e}")
```

## CacheManager

### Class Reference

```python
class CacheManager:
    """Manages caching operations and backends."""
    
    def __init__(self, client: ZenooClient):
        """Initialize cache manager.
        
        Args:
            client: Zenoo RPC client instance
        """
        self.client = client
        self.backends = {}
        self.default_backend = None
        self.cache_stats = CacheStats()
    
    def add_backend(self, name: str, backend: CacheBackend, is_default: bool = False):
        """Add a cache backend.
        
        Args:
            name: Backend name
            backend: Cache backend instance
            is_default: Whether this is the default backend
        """
        pass
    
    async def get(self, key: str, backend_name: str = None) -> Any:
        """Get value from cache.
        
        Args:
            key: Cache key
            backend_name: Specific backend to use
            
        Returns:
            Cached value or None
        """
        pass
    
    async def set(self, key: str, value: Any, ttl: int = None, backend_name: str = None):
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            backend_name: Specific backend to use
        """
        pass
    
    async def invalidate(self, pattern: str = None, backend_name: str = None):
        """Invalidate cache entries.
        
        Args:
            pattern: Key pattern to invalidate
            backend_name: Specific backend to use
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics dictionary
        """
        pass
```

### Usage Examples

```python
from zenoo_rpc.cache.backends import MemoryBackend, RedisBackend

async def use_cache_manager():
    """Demonstrate cache manager usage."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        cache_manager = CacheManager(client)
        
        # Add cache backends
        memory_backend = MemoryBackend(max_size=1000)
        redis_backend = RedisBackend("redis://localhost:6379")
        
        cache_manager.add_backend("memory", memory_backend, is_default=True)
        cache_manager.add_backend("redis", redis_backend)
        
        # Cache operations
        await cache_manager.set("partner_1", {"name": "Cached Partner"}, ttl=300)
        
        # Get from cache
        cached_data = await cache_manager.get("partner_1")
        print(f"Cached data: {cached_data}")
        
        # Use specific backend
        await cache_manager.set("redis_key", {"data": "Redis data"}, backend_name="redis")
        
        # Get cache statistics
        stats = cache_manager.get_stats()
        print(f"Cache stats: {stats}")
        
        # Invalidate cache
        await cache_manager.invalidate("partner_*")
```

## ConnectionManager

### Class Reference

```python
class ConnectionManager:
    """Manages client connections and connection pooling."""
    
    def __init__(self, max_connections: int = 10):
        """Initialize connection manager.
        
        Args:
            max_connections: Maximum number of concurrent connections
        """
        self.max_connections = max_connections
        self.active_connections = {}
        self.connection_pool = []
        self.connection_counter = 0
    
    async def get_connection(self, host: str, port: int, **kwargs) -> ZenooClient:
        """Get a connection from the pool.
        
        Args:
            host: Odoo server host
            port: Odoo server port
            **kwargs: Additional connection parameters
            
        Returns:
            ZenooClient instance
        """
        pass
    
    async def release_connection(self, connection: ZenooClient):
        """Release a connection back to the pool.
        
        Args:
            connection: Connection to release
        """
        pass
    
    async def close_all_connections(self):
        """Close all active connections."""
        pass
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics.
        
        Returns:
            Connection statistics dictionary
        """
        pass
```

### Usage Examples

```python
async def use_connection_manager():
    """Demonstrate connection manager usage."""
    
    conn_manager = ConnectionManager(max_connections=5)
    
    try:
        # Get connection from pool
        client = await conn_manager.get_connection("localhost", 8069)
        await client.login("demo", "admin", "admin")
        
        # Use connection
        partners = await client.model("res.partner").limit(10).all()
        print(f"Retrieved {len(partners)} partners")
        
        # Release connection back to pool
        await conn_manager.release_connection(client)
        
        # Get connection statistics
        stats = conn_manager.get_connection_stats()
        print(f"Connection stats: {stats}")
        
    finally:
        # Clean up all connections
        await conn_manager.close_all_connections()
```

## ResourceManager

### Class Reference

```python
class ResourceManager:
    """Manages application resources and lifecycle."""
    
    def __init__(self):
        """Initialize resource manager."""
        self.resources = {}
        self.cleanup_handlers = []
    
    def register_resource(self, name: str, resource: Any, cleanup_func: Callable = None):
        """Register a resource for management.
        
        Args:
            name: Resource name
            resource: Resource instance
            cleanup_func: Optional cleanup function
        """
        pass
    
    def get_resource(self, name: str) -> Any:
        """Get a managed resource.
        
        Args:
            name: Resource name
            
        Returns:
            Resource instance
        """
        pass
    
    async def cleanup_all(self):
        """Clean up all managed resources."""
        pass
    
    def add_cleanup_handler(self, handler: Callable):
        """Add a cleanup handler.
        
        Args:
            handler: Cleanup handler function
        """
        pass
```

### Usage Examples

```python
async def use_resource_manager():
    """Demonstrate resource manager usage."""
    
    resource_manager = ResourceManager()
    
    # Register resources
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    
    resource_manager.register_resource(
        "odoo_client",
        client,
        cleanup_func=lambda: client.close()
    )
    
    cache_backend = RedisBackend("redis://localhost:6379")
    resource_manager.register_resource(
        "redis_cache",
        cache_backend,
        cleanup_func=lambda: cache_backend.close()
    )
    
    # Use resources
    odoo_client = resource_manager.get_resource("odoo_client")
    redis_cache = resource_manager.get_resource("redis_cache")
    
    # Perform operations
    partners = await odoo_client.model("res.partner").limit(5).all()
    await redis_cache.set("partners_count", len(partners))
    
    # Cleanup all resources
    await resource_manager.cleanup_all()
```

## Integrated Manager Usage

### Application Manager

```python
class ApplicationManager:
    """High-level application manager combining all managers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize application manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.connection_manager = ConnectionManager(
            max_connections=config.get("max_connections", 10)
        )
        self.resource_manager = ResourceManager()
        self.transaction_manager = None
        self.cache_manager = None
    
    async def initialize(self):
        """Initialize all managers and resources."""
        
        # Get primary connection
        client = await self.connection_manager.get_connection(
            self.config["odoo_host"],
            self.config["odoo_port"]
        )
        
        await client.login(
            self.config["odoo_database"],
            self.config["odoo_username"],
            self.config["odoo_password"]
        )
        
        # Initialize managers
        self.transaction_manager = TransactionManager(client)
        self.cache_manager = CacheManager(client)
        
        # Setup cache backends
        if self.config.get("redis_url"):
            redis_backend = RedisBackend(self.config["redis_url"])
            self.cache_manager.add_backend("redis", redis_backend, is_default=True)
        
        memory_backend = MemoryBackend(max_size=self.config.get("memory_cache_size", 1000))
        self.cache_manager.add_backend("memory", memory_backend)
        
        # Register resources
        self.resource_manager.register_resource("client", client)
        self.resource_manager.register_resource("transaction_manager", self.transaction_manager)
        self.resource_manager.register_resource("cache_manager", self.cache_manager)
    
    async def shutdown(self):
        """Shutdown all managers and clean up resources."""
        
        await self.resource_manager.cleanup_all()
        await self.connection_manager.close_all_connections()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()

# Usage
async def use_application_manager():
    """Demonstrate integrated application manager usage."""
    
    config = {
        "odoo_host": "localhost",
        "odoo_port": 8069,
        "odoo_database": "demo",
        "odoo_username": "admin",
        "odoo_password": "admin",
        "redis_url": "redis://localhost:6379",
        "max_connections": 5,
        "memory_cache_size": 1000
    }
    
    async with ApplicationManager(config) as app:
        # Get managers
        client = app.resource_manager.get_resource("client")
        cache_manager = app.resource_manager.get_resource("cache_manager")
        tx_manager = app.resource_manager.get_resource("transaction_manager")
        
        # Use integrated functionality
        async with tx_manager.begin_transaction() as tx:
            # Create partner
            partner = await client.model("res.partner").create({
                "name": "Integrated Manager Partner"
            })
            
            # Cache partner data
            await cache_manager.set(f"partner_{partner.id}", {
                "id": partner.id,
                "name": partner.name
            })
            
            print(f"Created and cached partner: {partner.id}")
        
        # Get cache stats
        cache_stats = cache_manager.get_stats()
        print(f"Cache statistics: {cache_stats}")
        
        # Get connection stats
        conn_stats = app.connection_manager.get_connection_stats()
        print(f"Connection statistics: {conn_stats}")
```

## Best Practices

1. **Resource Management**: Always use managers for resource lifecycle
2. **Connection Pooling**: Use connection pooling for better performance
3. **Cache Strategy**: Implement appropriate caching strategies
4. **Error Handling**: Handle manager-level errors appropriately
5. **Monitoring**: Monitor manager statistics and performance

## Related

- [Transaction Context](transaction/context.md) - Transaction usage
- [Cache Backends](cache/backends.md) - Cache implementation
- [Client Usage](client.md) - Client operations
