# Query Builder

The Zenoo RPC Query Builder provides a fluent, type-safe interface for constructing complex Odoo queries. It eliminates the need to write raw domain filters and provides IDE support with autocompletion.

## Overview

The query builder allows you to:

- **Build complex filters** with a fluent API
- **Chain operations** for readable code
- **Get type safety** with IDE support
- **Optimize performance** with intelligent query planning
- **Use Q objects** for complex logical operations

## Basic Queries

### Simple Filtering

```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async with ZenooClient("localhost", port=8069) as client:
    await client.login("my_database", "admin", "admin")

    # Get QueryBuilder from client.model()
    partner_builder = client.model(ResPartner)

    # Simple equality filter - returns QuerySet
    companies_queryset = partner_builder.filter(is_company=True)
    companies = await companies_queryset.all()

    # Multiple conditions (AND by default)
    active_companies = await partner_builder.filter(
        is_company=True,
        active=True
    ).all()
```

### Field Lookups

Zenoo RPC supports Django-style field lookups for more expressive queries:

```python
# String operations
partner_builder = client.model(ResPartner)
partners = await partner_builder.filter(
    name__ilike="company%",           # Case-insensitive LIKE
    email__contains="@gmail.com",     # Contains substring
    phone__startswith="+1"            # Starts with
).all()

# Numeric operations
partners = await partner_builder.filter(
    id__gt=100,                       # Greater than
    id__lte=1000,                     # Less than or equal
    credit_limit__gte=5000.0          # Greater than or equal
).all()

# Date operations
from datetime import datetime, timedelta

recent_partners = await partner_builder.filter(
    create_date__gte=datetime.now() - timedelta(days=30),
    write_date__lt=datetime.now()
).all()

# List operations
partner_ids = [1, 2, 3, 4, 5]
selected_partners = await partner_builder.filter(
    id__in=partner_ids,               # In list
    state__not_in=["draft", "cancel"] # Not in list
).all()
```

### Supported Lookups

| Lookup | Description | Example |
|--------|-------------|---------|
| `exact` | Exact match (default) | `name__exact="John"` |
| `iexact` | Case-insensitive exact | `name__iexact="john"` |
| `contains` | Contains substring | `name__contains="John"` |
| `icontains` | Case-insensitive contains | `name__icontains="john"` |
| `startswith` | Starts with | `name__startswith="J"` |
| `istartswith` | Case-insensitive starts with | `name__istartswith="j"` |
| `endswith` | Ends with | `name__endswith="son"` |
| `iendswith` | Case-insensitive ends with | `name__iendswith="SON"` |
| `like` | SQL LIKE pattern | `name__like="J%"` |
| `ilike` | Case-insensitive LIKE | `name__ilike="j%"` |
| `regex` | Regular expression | `name__regex=r"^J.*n$"` |
| `iregex` | Case-insensitive regex | `name__iregex=r"^j.*n$"` |
| `gt` | Greater than | `id__gt=100` |
| `gte` | Greater than or equal | `id__gte=100` |
| `lt` | Less than | `id__lt=100` |
| `lte` | Less than or equal | `id__lte=100` |
| `in` | In list | `id__in=[1,2,3]` |
| `not_in` | Not in list | `id__not_in=[1,2,3]` |
| `isnull` | Is null/false | `parent_id__isnull=True` |

## Q Objects for Complex Logic

For complex logical operations, use Q objects to build sophisticated queries:

```python
from zenoo_rpc.query.filters import Q

partner_builder = client.model(ResPartner)

# OR conditions
partners = await partner_builder.filter(
    Q(is_company=True) | Q(parent_id__isnull=False)
).all()

# Complex nested logic
partners = await partner_builder.filter(
    (Q(is_company=True) & Q(active=True)) |
    (Q(is_company=False) & Q(parent_id__isnull=False))
).all()

# NOT conditions
partners = await partner_builder.filter(
    ~Q(state="draft")  # NOT draft
).all()

# Combining Q objects with regular filters
partners = await partner_builder.filter(
    Q(name__ilike="company%") | Q(name__ilike="corp%"),
    active=True,  # Regular filter (AND)
    is_company=True
).all()
```

## Query Methods

### Retrieving Results

```python
partner_builder = client.model(ResPartner)

# Get all results
all_partners = await partner_builder.filter(
    is_company=True
).all()

# Get first result
first_partner = await partner_builder.filter(
    is_company=True
).first()

# Get specific record by ID
partner = await partner_builder.get(123)

# Get or create
partner, created = await partner_builder.get_or_create(
    email="new@company.com",
    defaults={"name": "New Company", "is_company": True}
)

# Check existence
exists = await partner_builder.filter(
    email="test@company.com"
).exists()

# Count records
count = await client.model(ResPartner).filter(
    is_company=True
).count()
```

### Limiting and Pagination

```python
# Limit results
top_10 = await client.model(ResPartner).filter(
    is_company=True
).limit(10).all()

# Offset for pagination
page_2 = await client.model(ResPartner).filter(
    is_company=True
).offset(20).limit(10).all()

# Helper for pagination
async def paginate_partners(page_size=50):
    offset = 0
    while True:
        partners = await client.model(ResPartner).filter(
            is_company=True
        ).offset(offset).limit(page_size).all()
        
        if not partners:
            break
            
        yield partners
        offset += page_size

# Usage
async for partner_batch in paginate_partners():
    for partner in partner_batch:
        print(f"Processing {partner.name}")
```

### Ordering

```python
# Single field ordering
partners = await client.model(ResPartner).filter(
    is_company=True
).order_by("name").all()

# Descending order
partners = await client.model(ResPartner).filter(
    is_company=True
).order_by("-create_date").all()

# Multiple fields
partners = await client.model(ResPartner).filter(
    is_company=True
).order_by("country_id", "-create_date").all()

# Random ordering
partners = await client.model(ResPartner).filter(
    is_company=True
).order_by("?").limit(5).all()
```

## Field Selection

### Selecting Specific Fields

```python
# Select only specific fields for performance
partners = await client.model(ResPartner).filter(
    is_company=True
).fields("id", "name", "email").all()

# Exclude fields
partners = await client.model(ResPartner).filter(
    is_company=True
).exclude_fields("image_1920", "image_512").all()
```

### Related Field Access

```python
# Access related fields
partners = await client.model(ResPartner).filter(
    is_company=True
).fields("id", "name", "country_id.name", "state_id.name").all()

for partner in partners:
    print(f"{partner.name} - {partner.country_id.name}")
```

## Query Optimization

### Prefetch Related Objects

```python
# Prefetch related objects to avoid N+1 queries
partners = await client.model(ResPartner).filter(
    is_company=True
).prefetch_related("child_ids", "category_id").all()

# Access prefetched data without additional queries
for partner in partners:
    children = await partner.child_ids.all()  # No additional query
    categories = await partner.category_id.all()  # No additional query
```

### Query Caching

```python
# Cache query results
partners = await client.model(ResPartner).filter(
    is_company=True
).cache(ttl=300).all()  # Cache for 5 minutes

# Cache with custom key
partners = await client.model(ResPartner).filter(
    is_company=True
).cache(key="active_companies", ttl=600).all()
```

## Advanced Query Patterns

### Subqueries

```python
# Find partners with recent orders
from zenoo_rpc.models.common import SaleOrder

recent_order_partners = await client.model(ResPartner).filter(
    id__in=client.model(SaleOrder).filter(
        create_date__gte=datetime.now() - timedelta(days=30)
    ).values_list("partner_id", flat=True)
).all()
```

### Aggregation

```python
# Count by field
partner_counts = await client.model(ResPartner).filter(
    is_company=True
).aggregate(
    total_count=Count("id"),
    active_count=Count("id", filter=Q(active=True))
)

# Sum and average
order_stats = await client.model(SaleOrder).aggregate(
    total_amount=Sum("amount_total"),
    avg_amount=Avg("amount_total"),
    max_amount=Max("amount_total")
)
```

### Bulk Operations

```python
# Bulk update
updated_count = await client.model(ResPartner).filter(
    is_company=True,
    active=False
).update(active=True)

# Bulk delete
deleted_count = await client.model(ResPartner).filter(
    is_company=False,
    parent_id__isnull=True,
    create_date__lt=datetime.now() - timedelta(days=365)
).delete()
```

## Error Handling

```python
from zenoo_rpc.exceptions import ValidationError, NotFoundError

try:
    # Query that might fail
    partner = await client.model(ResPartner).filter(
        email="nonexistent@example.com"
    ).get()  # Raises NotFoundError if not found
    
except NotFoundError:
    print("Partner not found")
    
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Best Practices

### 1. Use Specific Field Selection

```python
# Good: Select only needed fields
partners = await client.model(ResPartner).filter(
    is_company=True
).fields("id", "name", "email").all()

# Avoid: Loading all fields when not needed
partners = await client.model(ResPartner).filter(
    is_company=True
).all()  # Loads all fields
```

### 2. Use Prefetching for Related Data

```python
# Good: Prefetch related data
partners = await client.model(ResPartner).filter(
    is_company=True
).prefetch_related("child_ids").all()

# Avoid: N+1 queries
partners = await client.model(ResPartner).filter(
    is_company=True
).all()

for partner in partners:
    children = await partner.child_ids.all()  # N additional queries
```

### 3. Use Appropriate Limits

```python
# Good: Use reasonable limits
partners = await client.model(ResPartner).filter(
    is_company=True
).limit(100).all()

# Avoid: Loading too many records
partners = await client.model(ResPartner).filter(
    is_company=True
).all()  # Could load thousands of records
```

### 4. Use Indexes Effectively

```python
# Good: Filter on indexed fields
partners = await client.model(ResPartner).filter(
    id__in=[1, 2, 3, 4, 5]  # ID is indexed
).all()

# Consider: Non-indexed field filters might be slow
partners = await client.model(ResPartner).filter(
    comment__ilike="%important%"  # Comment field might not be indexed
).all()
```

## Next Steps

- Learn about [Relationships](relationships.md) for working with related models
- Explore [Caching](caching.md) for query performance optimization
- Check [Batch Operations](batch-operations.md) for bulk data processing
