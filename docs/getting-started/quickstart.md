# Quick Start Tutorial

Get up and running with Zenoo RPC in just 5 minutes! This tutorial will guide you through the basics of connecting to Odoo and performing common operations.

## Prerequisites

- Python 3.9+ installed
- Odoo server running and accessible
- Zenoo RPC installed (`pip install zenoo-rpc`)

## Your First Zenoo RPC Script

Let's start with a simple script that connects to Odoo and fetches some data:

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async def main():
    # Create client and connect
    async with ZenooClient("https://your-odoo-server.com") as client:
        # Authenticate
        await client.login("your_database", "your_username", "your_password")
        
        # Fetch companies with type safety
        companies = await client.model(ResPartner).filter(
            is_company=True
        ).limit(5).all()
        
        # Print results
        for company in companies:
            print(f"Company: {company.name}")
            if company.email:
                print(f"  Email: {company.email}")
            if company.website:
                print(f"  Website: {company.website}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
```

## Step-by-Step Breakdown

### 1. Import Required Modules

```python
import asyncio
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner
```

- `asyncio` - Python's async/await support
- `ZenooClient` - Main client for Odoo connections
- `ResPartner` - Type-safe model for res.partner records

### 2. Create and Configure Client

```python
async with ZenooClient("localhost", port=8069) as client:
```

The client supports various connection options:

```python
# Basic connection
client = ZenooClient("localhost", port=8069)

# HTTPS connection
client = ZenooClient("https://myodoo.com")

# Custom configuration
client = ZenooClient(
    host="localhost",
    port=8069,
    protocol="http",
    timeout=30.0,
    max_connections=100
)
```

### 3. Authenticate

```python
await client.login("demo", "admin", "admin")
```

Replace with your actual credentials:
- `database` - Your Odoo database name
- `username` - Your Odoo username
- `password` - Your Odoo password

### 4. Query Data with Type Safety

```python
companies = await client.model(ResPartner).filter(
    is_company=True
).limit(5).all()
```

This single line:
- Creates a type-safe query for ResPartner model
- Filters for companies only
- Limits results to 5 records
- Executes the query and returns typed results

## Common Operations

### Basic Queries

```python
# Get all active partners
partners = await client.model(ResPartner).filter(active=True).all()

# Get partners with email
partners_with_email = await client.model(ResPartner).filter(
    email__isnull=False
).all()

# Get specific partner by ID
partner = await client.model(ResPartner).get(1)

# Search with complex conditions
from zenoo_rpc import Q

partners = await client.model(ResPartner).filter(
    Q(name__ilike="acme%") | Q(email__ilike="%acme%"),
    is_company=True
).all()
```

### Creating Records

```python
# Create a new partner
new_partner = await client.model(ResPartner).create({
    "name": "New Company",
    "is_company": True,
    "email": "contact@newcompany.com",
    "phone": "+1-555-0123"
})

print(f"Created partner with ID: {new_partner.id}")
```

### Updating Records

```python
# Update a partner
partner = await client.model(ResPartner).get(1)
updated_partner = await client.model(ResPartner).update(
    partner.id,
    {"email": "newemail@company.com"}
)

# Or update multiple records
await client.model(ResPartner).filter(
    is_company=True,
    email__isnull=True
).update({"active": False})
```

### Deleting Records

```python
# Delete a specific record
await client.model(ResPartner).delete(partner_id)

# Delete multiple records
await client.model(ResPartner).filter(
    active=False,
    is_company=False
).delete()
```

## Working with Relationships

Zenoo RPC provides lazy loading for relationship fields:

```python
# Get partner with country relationship
partner = await client.model(ResPartner).get(1)

# Access related country (lazy loaded)
if partner.country_id:
    country = await partner.country_id
    print(f"Partner is from {country.name}")

# Get children contacts (one2many)
children = await partner.child_ids.all()
for child in children:
    print(f"Contact: {child.name}")
```

## Error Handling

```python
from zenoo_rpc.exceptions import (
    ZenooError,
    AuthenticationError,
    ValidationError,
    AccessError
)

async def safe_operation():
    try:
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "wrong_password")
            
    except AuthenticationError as e:
        print(f"Login failed: {e}")
    except ValidationError as e:
        print(f"Data validation error: {e}")
    except AccessError as e:
        print(f"Access denied: {e}")
    except ZenooError as e:
        print(f"General Zenoo error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Performance Tips

### Use Batch Operations

```python
# Instead of multiple individual creates
partners_data = [
    {"name": "Company 1", "is_company": True},
    {"name": "Company 2", "is_company": True},
    {"name": "Company 3", "is_company": True},
]

# Use batch create
partners = await client.model(ResPartner).bulk_create(partners_data)
```

### Enable Caching

```python
# Configure caching for better performance
async with ZenooClient("localhost", port=8069) as client:
    # Setup memory cache
    await client.cache_manager.setup_memory_cache(
        max_size=1000,
        default_ttl=300  # 5 minutes
    )
    
    await client.login("demo", "admin", "admin")
    
    # Subsequent identical queries will be cached
    partners1 = await client.model(ResPartner).filter(is_company=True).all()
    partners2 = await client.model(ResPartner).filter(is_company=True).all()  # From cache
```

### Use Transactions

```python
# Ensure data consistency with transactions
async with client.transaction() as tx:
    # Create parent company
    company = await client.model(ResPartner).create({
        "name": "Parent Company",
        "is_company": True
    })
    
    # Create child contact
    contact = await client.model(ResPartner).create({
        "name": "John Doe",
        "parent_id": company.id,
        "email": "john@company.com"
    })
    
    # Both records are created atomically
    # Automatic commit on success, rollback on error
```

## Next Steps

Now that you've learned the basics, explore more advanced features:

1. **[Models & Type Safety](../user-guide/models.md)** - Learn about Pydantic models
2. **[Query Builder](../user-guide/queries.md)** - Master complex queries
3. **[Caching System](../user-guide/caching.md)** - Optimize performance
4. **[Transactions](../user-guide/transactions.md)** - Ensure data consistency
5. **[Batch Operations](../user-guide/batch-operations.md)** - Handle bulk data efficiently

## Complete Example

Here's a more comprehensive example that demonstrates multiple features:

```python
import asyncio
from zenoo_rpc import ZenooClient, Q
from zenoo_rpc.models.common import ResPartner, ResCountry

async def comprehensive_example():
    async with ZenooClient("localhost", port=8069) as client:
        # Setup caching
        await client.cache_manager.setup_memory_cache(max_size=500)

        # Setup transaction manager
        await client.setup_transaction_manager()

        # Authenticate
        await client.login("your_database", "your_username", "your_password")
        
        # Complex query with relationships
        us_companies = await client.model(ResPartner).filter(
            is_company=True,
            country_id__code="US",
            Q(customer_rank__gt=0) | Q(supplier_rank__gt=0)
        ).order_by("name").limit(10).all()
        
        print(f"Found {len(us_companies)} US companies")
        
        # Use transaction for data integrity
        async with client.transaction() as tx:
            for company in us_companies[:3]:
                # Create a contact for each company
                contact = await client.model(ResPartner).create({
                    "name": f"Contact for {company.name}",
                    "parent_id": company.id,
                    "email": f"contact@{company.name.lower().replace(' ', '')}.com",
                    "function": "Sales Representative"
                })
                print(f"Created contact: {contact.name}")

if __name__ == "__main__":
    asyncio.run(comprehensive_example())
```

This example shows:
- Caching setup for performance
- Complex queries with Q objects
- Relationship filtering
- Transaction usage for data integrity
- Batch operations

Ready to dive deeper? Check out our [User Guide](../user-guide/client.md) for comprehensive documentation on all features!
