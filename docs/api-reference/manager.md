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
    """Manages transactions for a Zenoo RPC client."""

    def __init__(self, client: ZenooClient):
        """Initialize the transaction manager.

        Args:
            client: Zenoo RPC client instance
        """
        self.client = client
        self.active_transactions = {}
        self.current_transaction = None
        self.successful_transactions = 0
        self.failed_transactions = 0

    @asynccontextmanager
    async def transaction(self, transaction_id: str = None, auto_commit: bool = True):
        """Create a new transaction context.

        Args:
            transaction_id: Optional transaction identifier
            auto_commit: Whether to auto-commit on success

        Yields:
            Transaction instance
        """
        # Implementation details...
        pass

    def get_current_transaction(self) -> Optional[Transaction]:
        """Get the current active transaction.

        Returns:
            Current transaction or None
        """
        return self.current_transaction

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID.

        Args:
            transaction_id: Transaction identifier

        Returns:
            Transaction instance or None
        """
        return self.active_transactions.get(transaction_id)

    async def rollback_all(self) -> None:
        """Rollback all active transactions."""
        for transaction in list(self.active_transactions.values()):
            if transaction.is_active:
                await transaction.rollback()
```

### Usage Examples

```python
async def use_transaction_manager():
    """Demonstrate transaction manager usage."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup transaction manager
        await client.setup_transaction_manager()

        # Use transaction context manager (recommended)
        async with client.transaction() as tx:
            # Perform operations within transaction
            partner_id = await client.create("res.partner", {
                "name": "Managed Transaction Partner"
            })

            # Create savepoint within transaction
            savepoint_id = await tx.create_savepoint("after_partner")

            try:
                product_id = await client.create("product.product", {
                    "name": "Managed Transaction Product"
                })

                # Transaction auto-commits on success
                print("Transaction committed successfully")

            except Exception as e:
                # Rollback to savepoint
                await tx.rollback_to_savepoint(savepoint_id)
                print(f"Rolled back to savepoint: {e}")

# Alternative: Direct transaction manager access
async def use_transaction_manager_direct():
    """Direct transaction manager usage."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup and get transaction manager
        tx_manager = await client.setup_transaction_manager()

        # Use transaction manager directly
        async with tx_manager.transaction() as tx:
            partner_id = await client.create("res.partner", {
                "name": "Direct Transaction Partner"
            })

            # Transaction auto-commits on success
            print(f"Created partner: {partner_id}")
```

## CacheManager

### Class Reference

```python
class CacheManager:
    """Main cache manager for Zenoo RPC."""

    def __init__(self):
        """Initialize cache manager."""
        self.backends = {}
        self.strategies = {}
        self.default_backend = "memory"
        self.default_strategy = "ttl"
        self.config = {
            "enabled": True,
            "default_ttl": 300,
            "max_key_length": 250,
            "namespace": "zenoo_rpc",
        }
        self.stats = {
            "total_gets": 0,
            "total_sets": 0,
            "total_deletes": 0,
            "total_hits": 0,
            "total_misses": 0,
        }

    async def setup_memory_cache(
        self,
        name: str = "memory",
        max_size: int = 1000,
        default_ttl: int = None,
        strategy: str = "ttl"
    ) -> None:
        """Setup in-memory cache backend.

        Args:
            name: Backend name
            max_size: Maximum cache size
            default_ttl: Default TTL in seconds
            strategy: Cache strategy ("ttl", "lru", "lfu")
        """
        pass

    async def setup_redis_cache(
        self,
        name: str = "redis",
        url: str = "redis://localhost:6379/0",
        namespace: str = None,
        serializer: str = "json",
        strategy: str = "ttl",
        **kwargs
    ) -> None:
        """Setup Redis cache backend.

        Args:
            name: Backend name
            url: Redis connection URL
            namespace: Cache namespace
            serializer: Serialization method
            strategy: Cache strategy
            **kwargs: Additional Redis parameters
        """
        pass

    async def get(self, key: Union[str, CacheKey], backend: str = None) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)

        Returns:
            Cached value or None
        """
        pass

    async def set(
        self,
        key: Union[str, CacheKey],
        value: Any,
        ttl: int = None,
        backend: str = None
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            backend: Backend name (uses default if None)

        Returns:
            True if successful
        """
        pass

    async def delete(self, key: Union[str, CacheKey], backend: str = None) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key
            backend: Backend name (uses default if None)

        Returns:
            True if successful
        """
        pass

    async def clear(self, backend: str = None) -> bool:
        """Clear cache.

        Args:
            backend: Backend name (clears all if None)

        Returns:
            True if successful
        """
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        return self.stats
```

### Usage Examples

```python
async def use_cache_manager():
    """Demonstrate cache manager usage."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup cache manager (recommended)
        cache_manager = await client.setup_cache_manager(
            backend="memory",
            max_size=1000,
            ttl=300
        )

        # Or setup additional backends manually
        await cache_manager.setup_redis_cache(
            name="redis",
            url="redis://localhost:6379/0",
            namespace="zenoo_rpc"
        )

        # Cache operations
        await cache_manager.set("partner_1", {"name": "Cached Partner"}, ttl=300)

        # Get from cache
        cached_data = await cache_manager.get("partner_1")
        print(f"Cached data: {cached_data}")

        # Use specific backend
        await cache_manager.set("redis_key", {"data": "Redis data"}, backend="redis")

        # Get cache statistics
        stats = await cache_manager.get_stats()
        print(f"Cache stats: {stats}")

        # Invalidate cache patterns
        await cache_manager.invalidate_pattern("partner_*")

        # Invalidate all cache for a model
        await cache_manager.invalidate_model("res.partner")

        # Clear all cache
        await cache_manager.clear()

# Alternative: Direct cache manager setup
async def use_cache_manager_direct():
    """Direct cache manager setup."""

    from zenoo_rpc.cache.manager import CacheManager

    cache_manager = CacheManager()

    # Setup memory cache
    await cache_manager.setup_memory_cache(
        name="memory",
        max_size=1000,
        default_ttl=300
    )

    # Use cache
    await cache_manager.set("test_key", {"data": "test"})
    result = await cache_manager.get("test_key")
    print(f"Cached result: {result}")
```

## ConnectionPool

### Class Reference

```python
class ConnectionPool:
    """Connection pool with HTTP/2 support and health monitoring."""

    def __init__(
        self,
        base_url: str,
        pool_size: int = 10,
        max_connections: int = 20,
        http2: bool = True,
        timeout: float = 30.0,
        health_check_interval: float = 30.0,
        max_error_rate: float = 10.0,
        connection_ttl: float = 300.0,
    ):
        """Initialize connection pool.

        Args:
            base_url: Base URL for connections
            pool_size: Target pool size
            max_connections: Maximum connections
            http2: Enable HTTP/2 support
            timeout: Request timeout
            health_check_interval: Health check interval in seconds
            max_error_rate: Maximum error rate percentage
            connection_ttl: Connection time-to-live in seconds
        """
        pass

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        pass

    def get_connection(self) -> "ConnectionContext":
        """Get a connection from the pool.

        Returns:
            Connection context manager
        """
        pass

    async def close(self) -> None:
        """Close all connections in the pool."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.

        Returns:
            Pool statistics dictionary
        """
        pass
```

### Usage Examples

```python
from zenoo_rpc.transport.pool import ConnectionPool

async def use_connection_pool():
    """Demonstrate connection pool usage."""

    # Create connection pool
    pool = ConnectionPool(
        base_url="http://localhost:8069",
        pool_size=5,
        max_connections=10,
        http2=True,
        timeout=30.0
    )

    try:
        # Initialize the pool
        await pool.initialize()

        # Use connection from pool
        async with pool.get_connection() as client:
            # Make HTTP requests using the pooled connection
            response = await client.post("/jsonrpc", json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "common",
                    "method": "version"
                },
                "id": 1
            })

            result = response.json()
            print(f"Odoo version: {result}")

        # Get pool statistics
        stats = pool.get_stats()
        print(f"Pool stats: {stats}")

    finally:
        # Clean up all connections
        await pool.close()

# Alternative: Using with ZenooClient
async def use_with_zenoo_client():
    """Use connection pool with ZenooClient."""

    # ZenooClient uses connection pooling internally
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # All operations use the internal connection pool
        partners = await client.search("res.partner", [], limit=10)
        print(f"Retrieved {len(partners)} partners")

        # Connection pool is automatically managed
```

## Best Practices

### Resource Management

Since Zenoo RPC doesn't have a dedicated ResourceManager, here are recommended patterns for managing resources:

```python
async def resource_management_pattern():
    """Recommended resource management pattern."""

    # Use context managers for automatic cleanup
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup managers
        await client.setup_transaction_manager()
        await client.setup_cache_manager()

        try:
            # Use resources within context
            async with client.transaction() as tx:
                partners = await client.search("res.partner", [], limit=5)
                print(f"Found {len(partners)} partners")

        except Exception as e:
            print(f"Error: {e}")
            # Resources are automatically cleaned up

        # Client is automatically closed when exiting context

# Alternative: Manual resource management
class ApplicationResourceManager:
    """Custom resource manager for application-specific needs."""

    def __init__(self):
        self.resources = {}
        self.cleanup_handlers = []

    async def setup_client(self, host: str, port: int = 8069):
        """Setup and register ZenooClient."""
        client = ZenooClient(host, port=port)
        await client.__aenter__()

        self.resources["client"] = client
        self.cleanup_handlers.append(lambda: client.__aexit__(None, None, None))

        return client

    async def cleanup_all(self):
        """Clean up all registered resources."""
        for handler in reversed(self.cleanup_handlers):
            try:
                await handler()
            except Exception as e:
                print(f"Cleanup error: {e}")

        self.resources.clear()
        self.cleanup_handlers.clear()
```

## Integrated Usage Patterns

### Complete Application Setup

```python
async def setup_complete_application():
    """Complete application setup with all managers."""

    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")

        # Setup all managers
        await client.setup_transaction_manager()
        cache_manager = await client.setup_cache_manager(
            backend="memory",
            max_size=1000,
            ttl=300
        )

        # Optional: Setup Redis cache as well
        await cache_manager.setup_redis_cache(
            name="redis",
            url="redis://localhost:6379/0"
        )

        # Use all features together
        async with client.transaction() as tx:
            # Create partner with caching
            partner_data = {"name": "Integrated Test Partner"}
            partner_id = await client.create("res.partner", partner_data)

            # Cache the result
            await cache_manager.set(f"partner_{partner_id}", partner_data, ttl=600)

            # Verify cached data
            cached_partner = await cache_manager.get(f"partner_{partner_id}")
            print(f"Cached partner: {cached_partner}")

            # Transaction auto-commits on success

        # Get statistics
        cache_stats = await cache_manager.get_stats()
        print(f"Cache statistics: {cache_stats}")

### Production Application Manager

```python
class ProductionAppManager:
    """Production-ready application manager."""

    def __init__(self, config: dict):
        self.config = config
        self.client = None

    async def initialize(self):
        """Initialize application with all managers."""

        # Setup client
        self.client = ZenooClient(
            self.config["odoo_host"],
            port=self.config.get("odoo_port", 8069),
            timeout=self.config.get("timeout", 30.0)
        )

        await self.client.__aenter__()
        await self.client.login(
            self.config["odoo_database"],
            self.config["odoo_username"],
            self.config["odoo_password"]
        )

        # Setup managers
        await self.client.setup_transaction_manager()
        await self.client.setup_cache_manager(
            backend=self.config.get("cache_backend", "memory"),
            url=self.config.get("redis_url"),
            max_size=self.config.get("cache_size", 1000),
            ttl=self.config.get("cache_ttl", 300)
        )

        return self.client

    async def cleanup(self):
        """Clean up all resources."""
        if self.client:
            await self.client.__aexit__(None, None, None)
        
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
