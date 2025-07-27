# Migration from odoorpc

This guide helps you migrate from `odoorpc` to Zenoo RPC, highlighting the key differences and providing step-by-step migration instructions.

## Why Migrate?

| Feature | odoorpc | Zenoo RPC |
|---------|---------|-----------|
| **Async Support** | ❌ Synchronous only | ✅ Async-first with asyncio |
| **Type Safety** | ❌ Raw dicts/lists | ✅ Pydantic models with validation |
| **Query Builder** | ❌ Manual domain building | ✅ Fluent, chainable queries |
| **Caching** | ❌ No built-in caching | ✅ Intelligent TTL/LRU caching |
| **Transactions** | ❌ No transaction support | ✅ ACID transactions with rollback |
| **Batch Operations** | ❌ Manual batching | ✅ Built-in bulk operations |
| **Error Handling** | ❌ Generic exceptions | ✅ Structured exception hierarchy |
| **Performance** | ❌ Multiple RPC calls | ✅ Optimized single calls |
| **IDE Support** | ❌ No autocomplete | ✅ Full IntelliSense support |

## Quick Comparison

### Connection & Authentication

**odoorpc:**
```python
import odoorpc

# Connect
odoo = odoorpc.ODOO('localhost', port=8069)

# Login
odoo.login('demo', 'admin', 'admin')

# Access models
Partner = odoo.env['res.partner']
```

**Zenoo RPC:**
```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def main():
    # Connect with context manager
    async with ZenooClient("localhost", port=8069) as client:
        # Login
        await client.login("demo", "admin", "admin")
        
        # Access models (type-safe)
        partners = client.model(ResPartner)

asyncio.run(main())
```

### Basic Queries

**odoorpc:**
```python
# Search and browse (2 RPC calls)
partner_ids = Partner.search([('is_company', '=', True)], limit=10)
partners = Partner.browse(partner_ids)

# Access data
for partner in partners:
    print(partner.name)  # May trigger additional RPC calls
```

**Zenoo RPC:**
```python
# Single RPC call with type safety
partners = await client.model(ResPartner).filter(
    is_company=True
).limit(10).all()

# Type-safe access
for partner in partners:
    print(partner.name)  # No additional RPC calls
```

## Step-by-Step Migration

### 1. Update Dependencies

Replace in your `requirements.txt` or `pyproject.toml`:

```diff
- odoorpc>=0.9.0
+ zenoo-rpc>=0.3.0
```

### 2. Convert Connection Code

**Before (odoorpc):**
```python
import odoorpc

def connect_odoo():
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('demo', 'admin', 'admin')
    return odoo

odoo = connect_odoo()
```

**After (Zenoo RPC):**
```python
import asyncio
from zenoo_rpc import ZenooClient

async def connect_odoo():
    client = ZenooClient("localhost", port=8069)
    await client.login("demo", "admin", "admin")
    return client

# Use with context manager for automatic cleanup
async def main():
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        # Your code here
```

### 3. Convert Model Access

**Before (odoorpc):**
```python
Partner = odoo.env['res.partner']
Product = odoo.env['product.product']
```

**After (Zenoo RPC):**
```python
from zenoo_rpc.models.common import ResPartner, ProductProduct

# Type-safe model access
partners = client.model(ResPartner)
products = client.model(ProductProduct)
```

### 4. Convert Search Operations

**Before (odoorpc):**
```python
# Manual domain building
partner_ids = Partner.search([
    ('is_company', '=', True),
    ('name', 'ilike', 'acme%')
], limit=10, offset=20)

partners = Partner.browse(partner_ids)
```

**After (Zenoo RPC):**
```python
# Fluent query builder
partners = await client.model(ResPartner).filter(
    is_company=True,
    name__ilike="acme%"
).limit(10).offset(20).all()
```

### 5. Convert CRUD Operations

#### Create Records

**Before (odoorpc):**
```python
partner_id = Partner.create({
    'name': 'New Company',
    'is_company': True,
    'email': 'contact@company.com'
})
partner = Partner.browse(partner_id)
```

**After (Zenoo RPC):**
```python
partner = await client.model(ResPartner).create({
    "name": "New Company",
    "is_company": True,
    "email": "contact@company.com"
})
```

#### Update Records

**Before (odoorpc):**
```python
partner = Partner.browse(1)
partner.write({'email': 'new@email.com'})
```

**After (Zenoo RPC):**
```python
partner = await client.model(ResPartner).update(1, {
    "email": "new@email.com"
})
```

#### Delete Records

**Before (odoorpc):**
```python
Partner.unlink([1, 2, 3])
```

**After (Zenoo RPC):**
```python
await client.model(ResPartner).delete([1, 2, 3])
```

### 6. Convert Complex Queries

**Before (odoorpc):**
```python
# Complex domain with OR conditions
domain = [
    '|',
    ('name', 'ilike', 'acme%'),
    ('email', 'ilike', '%acme%'),
    ('is_company', '=', True)
]
partner_ids = Partner.search(domain)
```

**After (Zenoo RPC):**
```python
from zenoo_rpc import Q

partners = await client.model(ResPartner).filter(
    Q(name__ilike="acme%") | Q(email__ilike="%acme%"),
    is_company=True
).all()
```

### 7. Convert Relationship Access

**Before (odoorpc):**
```python
partner = Partner.browse(1)
country_id = partner.country_id.id
country_name = partner.country_id.name  # Additional RPC call
```

**After (Zenoo RPC):**
```python
partner = await client.model(ResPartner).get(1)

# Lazy loading - only loads when accessed
if partner.country_id:
    country = await partner.country_id
    print(country.name)
```

## Advanced Migration Patterns

### Batch Operations

**Before (odoorpc):**
```python
# Manual batching
data = [
    {'name': 'Company 1', 'is_company': True},
    {'name': 'Company 2', 'is_company': True},
    {'name': 'Company 3', 'is_company': True},
]

partner_ids = []
for item in data:
    partner_id = Partner.create(item)
    partner_ids.append(partner_id)
```

**After (Zenoo RPC):**
```python
# Built-in batch operations
data = [
    {"name": "Company 1", "is_company": True},
    {"name": "Company 2", "is_company": True},
    {"name": "Company 3", "is_company": True},
]

partners = await client.model(ResPartner).bulk_create(data)
```

### Error Handling

**Before (odoorpc):**
```python
try:
    partner = Partner.browse(1)
    partner.write({'email': 'invalid-email'})
except Exception as e:
    print(f"Error: {e}")
```

**After (Zenoo RPC):**
```python
from zenoo_rpc.exceptions import ValidationError, AccessError

try:
    await client.model(ResPartner).update(1, {
        "email": "invalid-email"
    })
except ValidationError as e:
    print(f"Validation error: {e}")
except AccessError as e:
    print(f"Access denied: {e}")
```

### Caching

**Before (odoorpc):**
```python
# Manual caching
_cache = {}

def get_partners():
    if 'partners' not in _cache:
        partner_ids = Partner.search([('is_company', '=', True)])
        _cache['partners'] = Partner.browse(partner_ids)
    return _cache['partners']
```

**After (Zenoo RPC):**
```python
# Built-in intelligent caching
async with ZenooClient("localhost", port=8069) as client:
    # Setup caching
    await client.cache_manager.setup_memory_cache(
        max_size=1000,
        default_ttl=300
    )
    
    # Automatic caching
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).all()  # Cached automatically
```

## Migration Checklist

### Phase 1: Preparation
- [ ] Install Zenoo RPC: `pip install zenoo-rpc`
- [ ] Review current odoorpc usage patterns
- [ ] Identify async/await conversion points
- [ ] Plan testing strategy

### Phase 2: Core Migration
- [ ] Convert connection and authentication code
- [ ] Migrate model access to type-safe models
- [ ] Convert search operations to query builder
- [ ] Update CRUD operations
- [ ] Migrate relationship access patterns

### Phase 3: Advanced Features
- [ ] Implement proper error handling
- [ ] Add caching where beneficial
- [ ] Convert to batch operations where applicable
- [ ] Add transaction support for data integrity
- [ ] Implement retry mechanisms for resilience

### Phase 4: Testing & Optimization
- [ ] Add comprehensive tests
- [ ] Performance testing and optimization
- [ ] Monitor and tune caching
- [ ] Review and optimize query patterns

## Common Migration Challenges

### 1. Async/Await Conversion

**Challenge:** Converting synchronous code to async
**Solution:** Use `asyncio.run()` for entry points and `await` for all Zenoo RPC calls

### 2. Type Safety Adoption

**Challenge:** Moving from dynamic dicts to typed models
**Solution:** Start with common models, gradually add custom models

### 3. Query Builder Learning

**Challenge:** Learning new query syntax
**Solution:** Use the migration examples above, refer to Django ORM patterns

### 4. Error Handling Updates

**Challenge:** Different exception hierarchy
**Solution:** Catch specific Zenoo RPC exceptions, use structured error handling

## Performance Improvements

After migration, you should see:

- **50-80% fewer RPC calls** due to optimized queries
- **Better response times** with intelligent caching
- **Improved reliability** with retry mechanisms
- **Better maintainability** with type safety

## Getting Help

If you encounter issues during migration:

1. Check the [Troubleshooting Guide](../troubleshooting/debugging.md)
2. Review [API Reference](../api-reference/index.md) for detailed documentation
3. Ask questions in [GitHub Discussions](https://github.com/tuanle96/zenoo-rpc/discussions)
4. Report bugs in [GitHub Issues](https://github.com/tuanle96/zenoo-rpc/issues)

## Next Steps

After migration:

1. **[User Guide](../user-guide/client.md)** - Learn advanced features
2. **[Performance Optimization](../tutorials/performance-optimization.md)** - Optimize your code
3. **[Testing Strategies](../tutorials/testing.md)** - Test your migrated code
4. **[Production Deployment](../tutorials/production-deployment.md)** - Deploy with confidence
