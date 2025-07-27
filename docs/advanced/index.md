# Advanced Topics

This section covers advanced concepts, patterns, and techniques for building production-grade applications with Zenoo RPC. These topics are designed for experienced developers who need to implement complex, scalable, and robust solutions.

## Overview

Advanced topics include:

- **[Architecture Patterns](architecture.md)**: Scalable application architectures
- **[Performance Optimization](performance.md)**: Advanced performance tuning
- **[Security Best Practices](security.md)**: Enterprise security implementation
- **[Custom Extensions](extensions.md)**: Extending Zenoo RPC functionality
- **[Monitoring and Observability](monitoring.md)**: Production monitoring strategies

## Architecture Patterns

### Microservices with Zenoo RPC

Design microservices that efficiently communicate with Odoo while maintaining service boundaries.

```python
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

@dataclass
class ServiceConfig:
    """Configuration for Odoo-connected microservice."""
    odoo_host: str
    odoo_database: str
    odoo_username: str
    odoo_password: str
    service_name: str
    cache_backend: str = "redis"
    cache_url: str = "redis://localhost:6379/0"

class OdooMicroservice:
    """Base class for Odoo-connected microservices."""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.client: Optional[ZenooClient] = None
        self._health_status = {"status": "starting"}
    
    async def startup(self):
        """Initialize service and Odoo connection."""
        try:
            # Initialize Zenoo client
            self.client = ZenooClient(
                self.config.odoo_host,
                timeout=30.0,
                verify_ssl=True
            )
            await self.client.__aenter__()
            
            # Authenticate
            await self.client.login(
                self.config.odoo_database,
                self.config.odoo_username,
                self.config.odoo_password
            )
            
            # Setup cache
            if self.config.cache_backend == "redis":
                await self.client.cache_manager.setup_redis_cache(
                    name=f"{self.config.service_name}_cache",
                    url=self.config.cache_url,
                    namespace=self.config.service_name
                )
            
            self._health_status = {"status": "healthy", "odoo_connected": True}
            
        except Exception as e:
            self._health_status = {
                "status": "unhealthy", 
                "error": str(e),
                "odoo_connected": False
            }
            raise
    
    async def shutdown(self):
        """Cleanup service resources."""
        if self.client:
            await self.client.__aexit__(None, None, None)
        self._health_status = {"status": "shutdown"}
    
    async def health_check(self) -> Dict[str, Any]:
        """Service health check."""
        if self.client and self.client.is_authenticated:
            try:
                # Test Odoo connection
                await self.client.search_count("res.users", [])
                self._health_status.update({
                    "status": "healthy",
                    "odoo_connected": True
                })
            except Exception as e:
                self._health_status.update({
                    "status": "degraded",
                    "odoo_connected": False,
                    "error": str(e)
                })
        
        return self._health_status

class CustomerService(OdooMicroservice):
    """Customer management microservice."""
    
    async def get_customer(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer by ID with caching."""
        if not self.client:
            raise RuntimeError("Service not initialized")
        
        # Try cache first
        cache_key = f"customer:{customer_id}"
        cached = await self.client.cache_manager.get(cache_key)
        if cached:
            return cached
        
        # Fetch from Odoo
        partner = await self.client.model(ResPartner).filter(
            id=customer_id
        ).first()
        
        if partner:
            customer_data = {
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "is_company": partner.is_company
            }
            
            # Cache result
            await self.client.cache_manager.set(
                cache_key, customer_data, ttl=300
            )
            
            return customer_data
        
        return None
    
    async def search_customers(
        self, 
        query: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search customers with intelligent caching."""
        if not self.client:
            raise RuntimeError("Service not initialized")
        
        # Cache key based on query parameters
        cache_key = f"search:{hash(query)}:{limit}"
        cached = await self.client.cache_manager.get(cache_key)
        if cached:
            return cached
        
        # Search in Odoo
        from zenoo_rpc.query.filters import Q
        partners = await self.client.model(ResPartner).filter(
            Q(name__ilike=f"%{query}%") | Q(email__ilike=f"%{query}%")
        ).limit(limit).all()
        
        results = [
            {
                "id": p.id,
                "name": p.name,
                "email": p.email,
                "is_company": p.is_company
            }
            for p in partners
        ]
        
        # Cache search results
        await self.client.cache_manager.set(
            cache_key, results, ttl=60  # Shorter TTL for search results
        )
        
        return results
```

### Event-Driven Architecture

Implement event-driven patterns with Odoo data changes.

```python
import asyncio
from typing import Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    PARTNER_CREATED = "partner.created"
    PARTNER_UPDATED = "partner.updated"
    PARTNER_DELETED = "partner.deleted"
    ORDER_CREATED = "order.created"
    ORDER_CONFIRMED = "order.confirmed"

@dataclass
class DomainEvent:
    """Domain event for business logic."""
    event_type: EventType
    entity_id: int
    entity_data: Dict[str, Any]
    timestamp: float
    correlation_id: Optional[str] = None

class EventBus:
    """Simple event bus for domain events."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def publish(self, event: DomainEvent):
        """Publish an event to all subscribers."""
        handlers = self._handlers.get(event.event_type, [])
        
        # Execute all handlers concurrently
        tasks = [handler(event) for handler in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

class OdooEventService:
    """Service for handling Odoo data change events."""
    
    def __init__(self, client: ZenooClient, event_bus: EventBus):
        self.client = client
        self.event_bus = event_bus
    
    async def create_partner_with_events(
        self, 
        partner_data: Dict[str, Any]
    ) -> int:
        """Create partner and emit events."""
        # Create partner
        partner_id = await self.client.create("res.partner", partner_data)
        
        # Emit event
        event = DomainEvent(
            event_type=EventType.PARTNER_CREATED,
            entity_id=partner_id,
            entity_data=partner_data,
            timestamp=time.time()
        )
        await self.event_bus.publish(event)
        
        return partner_id

# Event handlers
async def send_welcome_email(event: DomainEvent):
    """Send welcome email when partner is created."""
    if event.event_type == EventType.PARTNER_CREATED:
        email = event.entity_data.get("email")
        if email:
            # Send email logic here
            print(f"Sending welcome email to {email}")

async def update_crm_system(event: DomainEvent):
    """Update external CRM when partner changes."""
    if event.event_type in [EventType.PARTNER_CREATED, EventType.PARTNER_UPDATED]:
        # Update external CRM logic here
        print(f"Updating CRM for partner {event.entity_id}")

# Setup event handling
event_bus = EventBus()
event_bus.subscribe(EventType.PARTNER_CREATED, send_welcome_email)
event_bus.subscribe(EventType.PARTNER_CREATED, update_crm_system)
event_bus.subscribe(EventType.PARTNER_UPDATED, update_crm_system)
```

## Performance Optimization

### Connection Pooling

Implement advanced connection pooling for high-throughput applications.

```python
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

class ZenooConnectionPool:
    """Advanced connection pool for Zenoo RPC clients."""
    
    def __init__(
        self,
        host: str,
        database: str,
        username: str,
        password: str,
        min_connections: int = 5,
        max_connections: int = 20,
        connection_timeout: float = 30.0
    ):
        self.host = host
        self.database = database
        self.username = username
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the connection pool."""
        # Create minimum connections
        for _ in range(self.min_connections):
            client = await self._create_client()
            await self._pool.put(client)
    
    async def _create_client(self) -> ZenooClient:
        """Create and authenticate a new client."""
        client = ZenooClient(
            self.host,
            timeout=self.connection_timeout
        )
        await client.__aenter__()
        await client.login(self.database, self.username, self.password)
        
        # Setup cache for each client
        await client.cache_manager.setup_memory_cache(
            name="pool_cache",
            max_size=500,
            strategy="lru"
        )
        
        self._created_connections += 1
        return client
    
    @asynccontextmanager
    async def get_client(self):
        """Get a client from the pool."""
        client = None
        try:
            # Try to get existing client
            try:
                client = self._pool.get_nowait()
            except asyncio.QueueEmpty:
                # Create new client if under limit
                async with self._lock:
                    if self._created_connections < self.max_connections:
                        client = await self._create_client()
                    else:
                        # Wait for available client
                        client = await self._pool.get()
            
            # Verify client is still authenticated
            if not client.is_authenticated:
                await client.login(self.database, self.username, self.password)
            
            yield client
            
        finally:
            # Return client to pool
            if client:
                await self._pool.put(client)
    
    async def close(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            client = await self._pool.get()
            await client.__aexit__(None, None, None)

# Usage
pool = ZenooConnectionPool(
    host="localhost",
    database="demo",
    username="admin",
    password="admin",
    min_connections=5,
    max_connections=20
)

await pool.initialize()

# Use pooled connections
async with pool.get_client() as client:
    partners = await client.model(ResPartner).all()
```

### Query Optimization

Advanced query optimization techniques.

```python
class OptimizedQueryService:
    """Service with optimized query patterns."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def get_partners_with_orders(
        self, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Efficiently load partners with their orders."""
        
        # Step 1: Get partner IDs with orders
        partner_ids = await self.client.search(
            "res.partner",
            domain=[("sale_order_ids", "!=", False)],
            limit=limit
        )
        
        if not partner_ids:
            return []
        
        # Step 2: Batch load partners
        partners_data = await self.client.read(
            "res.partner",
            partner_ids,
            fields=["name", "email", "sale_order_ids"]
        )
        
        # Step 3: Batch load all orders
        all_order_ids = []
        for partner in partners_data:
            all_order_ids.extend(partner.get("sale_order_ids", []))
        
        orders_data = {}
        if all_order_ids:
            orders = await self.client.read(
                "sale.order",
                all_order_ids,
                fields=["name", "amount_total", "state", "partner_id"]
            )
            orders_data = {order["id"]: order for order in orders}
        
        # Step 4: Combine data
        result = []
        for partner in partners_data:
            partner_orders = [
                orders_data[order_id] 
                for order_id in partner.get("sale_order_ids", [])
                if order_id in orders_data
            ]
            
            result.append({
                "partner": partner,
                "orders": partner_orders,
                "total_orders": len(partner_orders),
                "total_amount": sum(
                    order.get("amount_total", 0) 
                    for order in partner_orders
                )
            })
        
        return result
    
    async def search_with_aggregation(
        self, 
        domain: List[Any],
        group_by: str
    ) -> Dict[str, Any]:
        """Perform search with aggregation using raw queries."""
        
        # Use raw Odoo methods for complex aggregation
        result = await self.client.call_method(
            "object",
            "execute_kw",
            self.client._session.database,
            self.client._session.uid,
            self.client._session.password,
            "res.partner",
            "read_group",
            [domain],
            {
                "fields": ["customer_rank:sum", "supplier_rank:sum"],
                "groupby": [group_by],
                "lazy": False
            }
        )
        
        return result
```

## Security Implementation

### Advanced Authentication

Implement enterprise-grade authentication patterns.

```python
import jwt
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class AuthToken:
    """Authentication token with metadata."""
    token: str
    user_id: int
    database: str
    expires_at: float
    permissions: List[str]

class SecureZenooClient:
    """Zenoo client with enhanced security features."""
    
    def __init__(
        self,
        host: str,
        jwt_secret: str,
        token_expiry: int = 3600  # 1 hour
    ):
        self.host = host
        self.jwt_secret = jwt_secret
        self.token_expiry = token_expiry
        self._client: Optional[ZenooClient] = None
        self._auth_token: Optional[AuthToken] = None
    
    async def authenticate_with_token(self, token: str) -> bool:
        """Authenticate using JWT token."""
        try:
            # Decode and verify JWT
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=["HS256"]
            )
            
            # Extract authentication info
            database = payload["database"]
            username = payload["username"]
            user_id = payload["user_id"]
            permissions = payload.get("permissions", [])
            
            # Create Zenoo client
            self._client = ZenooClient(self.host)
            await self._client.__aenter__()
            
            # Authenticate with Odoo
            success = await self._client.login(
                database, username, payload["password"]
            )
            
            if success:
                self._auth_token = AuthToken(
                    token=token,
                    user_id=user_id,
                    database=database,
                    expires_at=payload["exp"],
                    permissions=permissions
                )
                return True
            
            return False
            
        except jwt.InvalidTokenError:
            return False
    
    def check_permission(self, permission: str) -> bool:
        """Check if current user has permission."""
        if not self._auth_token:
            return False
        return permission in self._auth_token.permissions
    
    async def secure_operation(
        self, 
        operation: Callable,
        required_permission: str,
        *args, 
        **kwargs
    ):
        """Execute operation with permission check."""
        # Check authentication
        if not self._auth_token:
            raise AuthenticationError("Not authenticated")
        
        # Check token expiry
        if time.time() > self._auth_token.expires_at:
            raise AuthenticationError("Token expired")
        
        # Check permission
        if not self.check_permission(required_permission):
            raise AccessError(f"Permission denied: {required_permission}")
        
        # Execute operation
        return await operation(*args, **kwargs)
    
    async def create_partner_secure(self, partner_data: Dict[str, Any]) -> int:
        """Create partner with security checks."""
        return await self.secure_operation(
            self._client.create,
            "partner.create",
            "res.partner",
            partner_data
        )
```

## Monitoring and Observability

### Comprehensive Metrics

Implement detailed monitoring for production systems.

```python
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    'zenoo_rpc_requests_total',
    'Total RPC requests',
    ['method', 'model', 'status']
)

REQUEST_DURATION = Histogram(
    'zenoo_rpc_request_duration_seconds',
    'Request duration',
    ['method', 'model']
)

ACTIVE_CONNECTIONS = Gauge(
    'zenoo_rpc_active_connections',
    'Active connections'
)

CACHE_OPERATIONS = Counter(
    'zenoo_rpc_cache_operations_total',
    'Cache operations',
    ['operation', 'backend', 'status']
)

@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = False
    error: Optional[str] = None

class MonitoredZenooClient:
    """Zenoo client with comprehensive monitoring."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
        self._operation_metrics: Dict[str, OperationMetrics] = {}
    
    async def monitored_operation(
        self,
        operation_name: str,
        model: str,
        operation: Callable,
        *args,
        **kwargs
    ):
        """Execute operation with monitoring."""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        metrics = OperationMetrics()
        self._operation_metrics[operation_id] = metrics
        
        # Start monitoring
        ACTIVE_CONNECTIONS.inc()
        
        try:
            # Execute operation
            result = await operation(*args, **kwargs)
            
            # Record success
            metrics.success = True
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            
            # Update Prometheus metrics
            REQUESTS_TOTAL.labels(
                method=operation_name,
                model=model,
                status="success"
            ).inc()
            
            REQUEST_DURATION.labels(
                method=operation_name,
                model=model
            ).observe(metrics.duration)
            
            self.logger.info(
                f"Operation {operation_name} on {model} completed",
                extra={
                    "operation_id": operation_id,
                    "duration": metrics.duration,
                    "success": True
                }
            )
            
            return result
            
        except Exception as e:
            # Record failure
            metrics.success = False
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            metrics.error = str(e)
            
            # Update Prometheus metrics
            REQUESTS_TOTAL.labels(
                method=operation_name,
                model=model,
                status="error"
            ).inc()
            
            self.logger.error(
                f"Operation {operation_name} on {model} failed",
                extra={
                    "operation_id": operation_id,
                    "duration": metrics.duration,
                    "error": str(e),
                    "success": False
                },
                exc_info=True
            )
            
            raise
            
        finally:
            ACTIVE_CONNECTIONS.dec()
    
    async def create(self, model: str, data: Dict[str, Any]) -> int:
        """Monitored create operation."""
        return await self.monitored_operation(
            "create",
            model,
            self.client.create,
            model,
            data
        )
    
    async def search(self, model: str, domain: List[Any]) -> List[int]:
        """Monitored search operation."""
        return await self.monitored_operation(
            "search",
            model,
            self.client.search,
            model,
            domain
        )
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get operation statistics."""
        total_ops = len(self._operation_metrics)
        successful_ops = sum(
            1 for m in self._operation_metrics.values() 
            if m.success
        )
        
        durations = [
            m.duration for m in self._operation_metrics.values()
            if m.duration is not None
        ]
        
        return {
            "total_operations": total_ops,
            "successful_operations": successful_ops,
            "failed_operations": total_ops - successful_ops,
            "success_rate": successful_ops / total_ops if total_ops > 0 else 0,
            "average_duration": sum(durations) / len(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0
        }
```

## Next Steps

- Explore specific [Architecture Patterns](architecture.md) in detail
- Learn about [Performance Optimization](performance.md) techniques
- Implement [Security Best Practices](security.md)
- Set up [Monitoring and Observability](monitoring.md)
- Create [Custom Extensions](extensions.md) for your use case
