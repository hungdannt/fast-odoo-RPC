# Examples Overview

Welcome to the Zenoo RPC examples section! Here you'll find practical examples and patterns for using Zenoo RPC in real-world scenarios.

## 📁 Example Categories

### 🌍 [Real-World Examples](real-world/index.md)

Complete, production-ready examples that demonstrate how to use Zenoo RPC in real applications:

- **[FastAPI Integration](real-world/fastapi-integration.md)**: Building REST APIs with FastAPI and Zenoo RPC
- **Customer Management**: Complete customer management system
- **E-commerce Integration**: Product catalog and order management
- **Inventory Management**: Stock tracking and warehouse management
- **Financial Reporting**: Automated financial reports and analytics

### 🔧 [Common Patterns](patterns/index.md)

Reusable patterns and best practices for common use cases:

- **Repository Pattern**: Clean data access layer
- **Service Layer**: Business logic organization
- **Event-Driven Architecture**: Async event handling
- **Caching Strategies**: Effective caching patterns
- **Error Handling**: Robust error handling patterns

### 🔌 [Integration Examples](integrations/index.md)

Examples of integrating Zenoo RPC with popular frameworks and tools:

- **Django Integration**: Using Zenoo RPC in Django applications
- **Flask Integration**: Building Flask APIs with Zenoo RPC
- **Celery Integration**: Background task processing
- **Database Integration**: Working with multiple databases

## 🚀 Quick Start Examples

### Basic CRUD Operations

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def basic_crud_example():
    async with ZenooClient("https://your-odoo-server.com") as client:
        await client.login("your_database", "your_username", "your_password")
        
        # Create
        partner = await client.model(ResPartner).create({
            "name": "Example Company",
            "email": "contact@example.com",
            "is_company": True
        })
        
        # Read
        companies = await (
            client.model(ResPartner)
            .filter(is_company=True)
            .limit(10)
            .all()
        )
        
        # Update
        await partner.update({"phone": "+1-555-0123"})
        
        # Delete
        await partner.delete()

asyncio.run(basic_crud_example())
```

### Async Batch Operations

```python
async def batch_operations_example():
    async with ZenooClient("https://your-odoo-server.com") as client:
        await client.login("your_database", "your_username", "your_password")
        
        # Batch create multiple records
        async with client.batch() as batch:
            for i in range(100):
                batch.create(ResPartner, {
                    "name": f"Customer {i}",
                    "email": f"customer{i}@example.com"
                })
        
        # Batch operations are executed efficiently
        results = await batch.execute()
        print(f"Created {len(results)} customers")

asyncio.run(batch_operations_example())
```

### Caching and Performance

```python
from zenoo_rpc.cache import TTLCache

async def caching_example():
    # Configure caching
    cache = TTLCache(max_size=1000, ttl=300)  # 5 minutes TTL
    
    async with ZenooClient("localhost", cache=cache) as client:
        await client.login("demo", "admin", "admin")
        
        # First call - hits database
        users = await client.model("res.users").search([])
        
        # Second call - served from cache
        users_cached = await client.model("res.users").search([])
        
        print(f"Cache hit ratio: {cache.hit_ratio:.2%}")

asyncio.run(caching_example())
```

### Transaction Management

```python
async def transaction_example():
    async with ZenooClient("localhost") as client:
        await client.login("demo", "admin", "admin")
        
        # Atomic transaction
        async with client.transaction() as tx:
            # Create customer
            customer = await tx.create(ResPartner, {
                "name": "Transaction Customer",
                "email": "tx@example.com"
            })
            
            # Create related records
            await tx.create("res.partner.bank", {
                "partner_id": customer.id,
                "acc_number": "123456789"
            })
            
            # If any operation fails, entire transaction is rolled back
            # Transaction is committed automatically on success

asyncio.run(transaction_example())
```

## 📚 Learning Path

### 1. **Start with Basics**
   - [Installation Guide](../getting-started/installation.md)
   - [Quick Start Tutorial](../getting-started/quickstart.md)
   - [Basic CRUD Operations](../tutorials/basic-crud.md)

### 2. **Explore Core Features**
   - [Models and Type Safety](../user-guide/models.md)
   - [Query Builder](../user-guide/queries.md)
   - [Caching System](../user-guide/caching.md)

### 3. **Advanced Patterns**
   - [Batch Operations](../user-guide/batch-operations.md)
   - [Transaction Management](../user-guide/transactions.md)
   - [Performance Optimization](../tutorials/performance-optimization.md)

### 4. **Production Deployment**
   - [Production Best Practices](../tutorials/production-deployment.md)
   - [Monitoring and Observability](../troubleshooting/monitoring.md)
   - [Security Considerations](../advanced/security.md)

## 🎯 Use Case Examples

### Web Applications
- **REST API**: Building scalable REST APIs
- **GraphQL**: GraphQL resolvers with Zenoo RPC
- **WebSocket**: Real-time data synchronization

### Data Processing
- **ETL Pipelines**: Extract, transform, load operations
- **Data Synchronization**: Keeping systems in sync
- **Reporting**: Automated report generation

### Microservices
- **Service Communication**: Inter-service communication
- **Event Sourcing**: Event-driven architectures
- **CQRS**: Command Query Responsibility Segregation

## 🔗 External Resources

- **[GitHub Repository](https://github.com/tuanle96/zenoo-rpc)**: Source code and issues
- **[PyPI Package](https://pypi.org/project/zenoo-rpc/)**: Installation and releases
- **[Documentation](https://zenoo-rpc.readthedocs.io)**: Complete documentation
- **[Community Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)**: Ask questions and share ideas

## 🤝 Contributing Examples

Have a great example to share? We'd love to include it!

1. **Fork the repository**
2. **Create your example** in the appropriate category
3. **Add documentation** explaining the use case
4. **Submit a pull request**

See our [Contributing Guidelines](../contributing/documentation.md) for more details.

---

**Ready to dive in?** Start with our [Real-World Examples](real-world/index.md) or explore [Common Patterns](patterns/index.md)!
