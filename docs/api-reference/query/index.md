# Query API Reference

The query module provides a fluent, chainable interface for building and executing Odoo queries with type safety, performance optimization, and advanced filtering capabilities.

## Overview

The query system consists of:

- **QueryBuilder**: Entry point for creating queries
- **QuerySet**: Chainable query operations and execution
- **Q Objects**: Complex query expressions
- **Field Expressions**: Advanced field operations
- **Lazy Loading**: Efficient relationship handling

## Core Classes

### `QueryBuilder`

Factory class for creating QuerySet instances.

```python
from zenoo_rpc.query.builder import QueryBuilder
from zenoo_rpc.models.common import ResPartner

# QueryBuilder is created automatically by client.model()
builder = client.model(ResPartner)
```

**Methods:**

```python
# Filter records (returns QuerySet)
def filter(*args, **kwargs) -> QuerySet[T]

# Get specific record by ID
async def get(id: int) -> T
```

**Usage:**

```python
# Get query builder from client
builder = client.model(ResPartner)

# Create filtered query
companies = await builder.filter(is_company=True).all()
```

### `QuerySet`

Chainable query interface with lazy evaluation.

```python
from zenoo_rpc.query.builder import QuerySet

class QuerySet:
    """Lazy, chainable query interface."""
    
    def __init__(self, model_class: Type[T], client: ZenooClient):
        self.model_class = model_class
        self.client = client
        self._domain = []
        self._fields = None
        self._limit = None
        self._offset = None
        self._order = None
```

## Filtering Methods

### `filter(*args, **kwargs)`

Add filters to the query.

**Parameters:**

- `*args`: Q objects or Expression objects
- `**kwargs`: Field-based filters

**Returns:** `QuerySet` - New filtered QuerySet

**Examples:**

```python
# Simple field filters
partners = await client.model(ResPartner).filter(
    is_company=True,
    active=True
).all()

# Field lookups
partners = await client.model(ResPartner).filter(
    name__ilike="acme%",
    email__contains="@acme.com"
).all()

# Multiple conditions
partners = await client.model(ResPartner).filter(
    is_company=True,
    customer_rank__gt=0,
    country_id__code="US"
).all()
```

### `exclude(*args, **kwargs)`

Exclude records matching criteria.

**Parameters:**

- `*args`: Q objects or Expression objects  
- `**kwargs`: Field-based filters

**Returns:** `QuerySet` - New QuerySet excluding matches

**Examples:**

```python
# Exclude inactive partners
active_partners = await client.model(ResPartner).exclude(
    active=False
).all()

# Exclude specific companies
partners = await client.model(ResPartner).exclude(
    name__in=["Test Company", "Demo Company"]
).all()
```

## Field Lookups

### Basic Lookups

```python
# Exact match (default)
partners = await client.model(ResPartner).filter(name="ACME Corp").all()
partners = await client.model(ResPartner).filter(name__exact="ACME Corp").all()

# Not equal
partners = await client.model(ResPartner).filter(name__ne="Test").all()

# Greater than / Less than
partners = await client.model(ResPartner).filter(
    customer_rank__gt=0,
    supplier_rank__lt=5
).all()

# Greater/Less than or equal
partners = await client.model(ResPartner).filter(
    customer_rank__gte=1,
    supplier_rank__lte=10
).all()
```

### String Lookups

```python
# Case-insensitive like
partners = await client.model(ResPartner).filter(
    name__ilike="acme%"
).all()

# Case-sensitive like
partners = await client.model(ResPartner).filter(
    name__like="ACME%"
).all()

# Contains
partners = await client.model(ResPartner).filter(
    email__contains="@acme.com"
).all()

# Starts with / Ends with
partners = await client.model(ResPartner).filter(
    name__startswith="ACME",
    email__endswith=".com"
).all()
```

### List Lookups

```python
# In list
partners = await client.model(ResPartner).filter(
    id__in=[1, 2, 3, 4, 5]
).all()

# Not in list
partners = await client.model(ResPartner).filter(
    name__not_in=["Test", "Demo"]
).all()
```

### Null Checks

```python
# Is null
partners = await client.model(ResPartner).filter(
    email__isnull=True
).all()

# Is not null
partners = await client.model(ResPartner).filter(
    email__isnull=False
).all()
```

### Relationship Lookups

```python
# Related field access
partners = await client.model(ResPartner).filter(
    country_id__name="United States",
    country_id__code="US"
).all()

# Deep relationship traversal
partners = await client.model(ResPartner).filter(
    parent_id__country_id__name="United States"
).all()
```

## Q Objects

Complex query expressions using Q objects.

```python
from zenoo_rpc.query.filters import Q

# OR conditions
partners = await client.model(ResPartner).filter(
    Q(name__ilike="acme%") | Q(name__ilike="corp%")
).all()

# AND conditions (default)
partners = await client.model(ResPartner).filter(
    Q(is_company=True) & Q(active=True)
).all()

# NOT conditions
partners = await client.model(ResPartner).filter(
    ~Q(name__ilike="test%")
).all()

# Complex combinations
partners = await client.model(ResPartner).filter(
    (Q(name__ilike="acme%") | Q(name__ilike="corp%")) &
    Q(is_company=True) &
    ~Q(active=False)
).all()
```

## Ordering

### `order_by(*fields)`

Order query results.

**Parameters:**

- `*fields`: Field names (prefix with "-" for descending)

**Returns:** `QuerySet` - Ordered QuerySet

**Examples:**

```python
# Single field ascending
partners = await client.model(ResPartner).order_by("name").all()

# Single field descending
partners = await client.model(ResPartner).order_by("-name").all()

# Multiple fields
partners = await client.model(ResPartner).order_by(
    "is_company", "-customer_rank", "name"
).all()

# Related field ordering
partners = await client.model(ResPartner).order_by(
    "country_id__name", "name"
).all()
```

## Pagination (QuerySet Methods)

### `limit(count)`

Limit number of results. **Note**: This is a QuerySet method, not QueryBuilder.

**Parameters:**

- `count` (int): Maximum number of records

**Returns:** `QuerySet` - Limited QuerySet

### `offset(count)`

Skip number of results. **Note**: This is a QuerySet method, not QueryBuilder.

**Parameters:**

- `count` (int): Number of records to skip

**Returns:** `QuerySet` - Offset QuerySet

**Examples:**

```python
# First 10 records
partners = await client.model(ResPartner).limit(10).all()

# Skip first 20, get next 10
partners = await client.model(ResPartner).offset(20).limit(10).all()

# Pagination helper
page = 3
page_size = 25
partners = await client.model(ResPartner).offset(
    (page - 1) * page_size
).limit(page_size).all()
```

## Field Selection

### `only(*fields)`

Select only specific fields.

**Parameters:**

- `*fields`: Field names to include

**Returns:** `QuerySet` - QuerySet with field selection

**Examples:**

```python
# Select specific fields
partners = await client.model(ResPartner).only(
    "id", "name", "email"
).all()

# Include related fields
partners = await client.model(ResPartner).only(
    "name", "email", "country_id__name"
).all()
```

### `defer(*fields)`

Exclude specific fields from selection.

**Parameters:**

- `*fields`: Field names to exclude

**Returns:** `QuerySet` - QuerySet with field exclusion

**Examples:**

```python
# Exclude large fields
partners = await client.model(ResPartner).defer(
    "image_1920", "comment"
).all()
```

## Relationship Loading

### `prefetch_related(*fields)`

Prefetch related objects to avoid N+1 queries.

**Parameters:**

- `*fields`: Relationship field names

**Returns:** `QuerySet` - QuerySet with prefetching

**Examples:**

```python
# Prefetch single relationship
partners = await client.model(ResPartner).prefetch_related(
    "country_id"
).all()

# Access prefetched data (no additional query)
for partner in partners:
    country = await partner.country_id  # Already loaded

# Prefetch multiple relationships
partners = await client.model(ResPartner).prefetch_related(
    "country_id", "state_id", "parent_id"
).all()

# Deep prefetching
partners = await client.model(ResPartner).prefetch_related(
    "country_id__currency_id"
).all()
```

### `select_related(*fields)`

Join related tables in single query.

**Parameters:**

- `*fields`: Relationship field names

**Returns:** `QuerySet` - QuerySet with joins

**Examples:**

```python
# Join country data
partners = await client.model(ResPartner).select_related(
    "country_id"
).all()

# Multiple joins
partners = await client.model(ResPartner).select_related(
    "country_id", "state_id"
).all()
```

## Query Execution

### `async all()`

Execute query and return all results.

**Returns:** `List[T]` - List of model instances

**Examples:**

```python
# Get all results
partners = await client.model(ResPartner).filter(
    is_company=True
).all()

# Empty list if no results
partners = await client.model(ResPartner).filter(
    name="NonExistent"
).all()  # Returns []
```

### `async first()`

Get first result or None. **Note**: This is a QuerySet method, not QueryBuilder.

**Returns:** `Optional[T]` - First model instance or None

**Examples:**

```python
# Get first company
company = await client.model(ResPartner).filter(
    is_company=True
).first()

if company:
    print(f"Found: {company.name}")
else:
    print("No companies found")
```

### `async get()`

Get single result, raise exception if not found or multiple found.

**Returns:** `T` - Single model instance

**Raises:**
- `DoesNotExist`: If no record found
- `MultipleObjectsReturned`: If multiple records found

**Examples:**

```python
try:
    partner = await client.model(ResPartner).filter(
        email="unique@email.com"
    ).get()
    print(f"Found partner: {partner.name}")
except DoesNotExist:
    print("Partner not found")
except MultipleObjectsReturned:
    print("Multiple partners found")
```

### `async count()`

Count matching records without loading data.

**Returns:** `int` - Number of matching records

**Examples:**

```python
# Count all companies
company_count = await client.model(ResPartner).filter(
    is_company=True
).count()

# Count with complex filters
active_customers = await client.model(ResPartner).filter(
    active=True,
    customer_rank__gt=0
).count()
```

### `async exists()`

Check if any matching records exist.

**Returns:** `bool` - True if records exist

**Examples:**

```python
# Check if companies exist
has_companies = await client.model(ResPartner).filter(
    is_company=True
).exists()

if has_companies:
    print("Companies found in database")
```

## Iteration

### `async __aiter__()`

Async iteration support for large datasets.

**Examples:**

```python
# Iterate over all partners
async for partner in client.model(ResPartner).filter(active=True):
    print(f"Processing: {partner.name}")

# Iterate with chunking
query = client.model(ResPartner).filter(is_company=True)
async for partner in query.chunk(100):  # Process in chunks of 100
    print(f"Company: {partner.name}")
```

## Caching

### `cache(key=None, ttl=None, backend=None)`

Cache query results.

**Parameters:**

- `key` (str, optional): Cache key (auto-generated if None)
- `ttl` (int, optional): Time to live in seconds
- `backend` (str, optional): Cache backend name

**Returns:** `QuerySet` - Cached QuerySet

**Examples:**

```python
# Cache with auto-generated key
countries = await client.model(ResCountry).cache(
    ttl=3600  # Cache for 1 hour
).all()

# Cache with custom key
companies = await client.model(ResPartner).filter(
    is_company=True
).cache(
    key="all_companies",
    ttl=1800  # Cache for 30 minutes
).all()

# Use specific cache backend
partners = await client.model(ResPartner).cache(
    backend="redis",
    ttl=600
).all()
```

## Advanced Features

### Raw Queries

Execute raw domain queries.

```python
# Raw Odoo domain
partners = await client.model(ResPartner).raw([
    "|",
    ("name", "ilike", "acme%"),
    ("name", "ilike", "corp%"),
    ("is_company", "=", True)
]).all()
```

### Aggregation

Perform aggregation operations.

```python
# Count by field
stats = await client.model(ResPartner).aggregate(
    total_customers=Count("id", filter=Q(customer_rank__gt=0)),
    total_suppliers=Count("id", filter=Q(supplier_rank__gt=0))
)

# Group by field
country_stats = await client.model(ResPartner).group_by(
    "country_id"
).aggregate(
    partner_count=Count("id"),
    customer_count=Count("id", filter=Q(customer_rank__gt=0))
)
```

### Bulk Operations

Bulk update and delete operations.

```python
# Bulk update
updated_count = await client.model(ResPartner).filter(
    is_company=True,
    active=False
).update(active=True)

# Bulk delete
deleted_count = await client.model(ResPartner).filter(
    name__ilike="test%"
).delete()
```

## Performance Tips

1. **Use field selection** to load only needed data
2. **Prefetch relationships** to avoid N+1 queries
3. **Use caching** for frequently accessed data
4. **Limit results** for large datasets
5. **Use exists()** instead of count() > 0

**Example:**

```python
# Optimized query
partners = await client.model(ResPartner).filter(
    is_company=True,
    active=True
).only(
    "id", "name", "email"
).prefetch_related(
    "country_id"
).cache(
    ttl=300
).limit(100).all()
```

## Next Steps

- Learn about [Q Objects](q-objects.md) for complex queries
- Explore [Field Expressions](expressions.md) for advanced operations
- Check [Performance Optimization](../performance/queries.md) guide
