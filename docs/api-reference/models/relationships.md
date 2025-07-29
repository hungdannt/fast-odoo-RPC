# Relationship Management API Reference

Comprehensive relationship handling and lazy loading for Odoo models with efficient data fetching, caching, and N+1 query prevention.

## Overview

The relationship system provides:

- **Lazy Loading**: Automatic loading of related records on access
- **Batch Loading**: N+1 query prevention through intelligent batching
- **Caching**: Efficient caching of loaded relationship data
- **Prefetching**: Explicit prefetching for performance optimization
- **Collection Support**: Handling of both single and collection relationships

## LazyRelationship

Represents a lazy-loaded relationship field that acts as a proxy for relationship data.

### Constructor

```python
class LazyRelationship:
    """Represents a lazy-loaded relationship field."""
    
    def __init__(
        self,
        parent_record: Any,
        field_name: str,
        relation_model: str,
        relation_ids: Union[int, List[int], None],
        client: Any,
        is_collection: bool = False,
    ):
        """Initialize a lazy relationship."""
```

**Parameters:**

- `parent_record` (Any): The record that owns this relationship
- `field_name` (str): Name of the relationship field
- `relation_model` (str): Name of the related Odoo model
- `relation_ids` (Union[int, List[int], None]): ID(s) of related records
- `client` (Any): Zenoo RPC client for data fetching
- `is_collection` (bool): Whether this is a collection (One2many/Many2many)

**Features:**

- Lazy loading on first access
- Caching of loaded data
- Support for both single records and collections
- Async loading with proper error handling
- N+1 query prevention through batch loading

### Loading Methods

#### `async load()`

Load the relationship data from the server.

**Returns:** `Any` - The loaded record(s) or None if no data

**Example:**

```python
# Get partner data with relationship IDs
partner = await client.model(ResPartner).filter(id=1).first()
country_rel = partner.country_id  # Returns LazyRelationship

# Load the actual data
country = await country_rel.load()  # Returns ResCountry instance
print(f"Country: {country.name}")

# Or use await directly
country = await partner.country_id  # Same as above
```

#### `is_loaded()`

Check if the relationship data has been loaded.

**Returns:** `bool` - True if data is loaded, False otherwise

**Example:**

```python
partner = await client.model(ResPartner).filter(id=1).first()

# Check if relationship is loaded
if partner.country_id.is_loaded():
    print("Country data is already loaded")
else:
    print("Country data needs to be loaded")
    country = await partner.country_id
```

#### `get_cached_data()`

Get cached data without triggering a load.

**Returns:** `Any` - Cached data or None if not loaded

**Example:**

```python
partner = await client.model(ResPartner).filter(id=1).first()

# Get cached data without loading
cached_country = partner.country_id.get_cached_data()
if cached_country:
    print(f"Cached country: {cached_country.name}")
else:
    print("No cached data available")
```

#### `invalidate()`

Invalidate the cached data, forcing a reload on next access.

**Example:**

```python
partner = await client.model(ResPartner).filter(id=1).first()

# Load country data
country = await partner.country_id

# Invalidate cache
partner.country_id.invalidate()

# Next access will reload from server
country_fresh = await partner.country_id
```

### Batch Loading

LazyRelationship automatically prevents N+1 queries through intelligent batch loading.

**Example:**

```python
# Get multiple partners with batch loading
partners = await client.model(ResPartner).filter(is_company=True).limit(100).all()

# All country relationships will be loaded in a single batch query
countries = []
for partner in partners:
    country = await partner.country_id  # Batched loading
    if country:
        countries.append(country)

print(f"Loaded {len(countries)} countries in batch")
```

### Awaitable Interface

LazyRelationship implements the awaitable protocol for convenient access.

**Example:**

```python
# These are equivalent:
country1 = await partner.country_id.load()
country2 = await partner.country_id

# Both trigger loading and return the actual data
assert country1 == country2
```

## RelationshipManager

Manages relationships for an Odoo model instance with prefetching and caching strategies.

### Constructor

```python
class RelationshipManager:
    """Manages relationships for an Odoo model instance."""
    
    def __init__(self, record: Any, client: Any):
        """Initialize the relationship manager."""
        self.record = record
        self.client = client
        self._relationships: Dict[str, LazyRelationship] = {}
```

**Parameters:**

- `record` (Any): The model instance that owns the relationships
- `client` (Any): Zenoo RPC client for data operations

### Relationship Creation

#### `create_relationship(field_name, relation_model, relation_data, is_collection=False)`

Create a lazy relationship for a field.

**Parameters:**

- `field_name` (str): Name of the relationship field
- `relation_model` (str): Name of the related Odoo model
- `relation_data` (Any): Raw relationship data from Odoo
- `is_collection` (bool): Whether this is a collection relationship

**Returns:** `LazyRelationship` - Lazy relationship instance

**Example:**

```python
# Usually called automatically by field descriptors
relationship_manager = RelationshipManager(partner, client)

# Create Many2one relationship
country_rel = relationship_manager.create_relationship(
    field_name="country_id",
    relation_model="res.country",
    relation_data=1,  # Country ID
    is_collection=False
)

# Create One2many relationship
children_rel = relationship_manager.create_relationship(
    field_name="child_ids",
    relation_model="res.partner",
    relation_data=[2, 3, 4],  # Child IDs
    is_collection=True
)
```

### Prefetching

#### `async prefetch_relationships(field_names, fields=None)`

Prefetch multiple relationships efficiently.

**Parameters:**

- `field_names` (List[str]): List of relationship field names to prefetch
- `fields` (List[str], optional): Specific fields to fetch for related records

**Example:**

```python
partner = await client.model(ResPartner).filter(id=1).first()

# Prefetch multiple relationships
await partner._relationship_manager.prefetch_relationships([
    "country_id",
    "state_id", 
    "parent_id"
])

# Now all relationships are loaded
country = await partner.country_id    # No database query
state = await partner.state_id        # No database query
parent = await partner.parent_id      # No database query

# Prefetch with specific fields
await partner._relationship_manager.prefetch_relationships(
    ["child_ids"],
    fields=["id", "name", "email", "phone"]
)

children = await partner.child_ids    # Loaded with specified fields
```

### Cache Management

#### `invalidate_all()`

Invalidate all cached relationships.

**Example:**

```python
partner = await client.model(ResPartner).filter(id=1).first()

# Load some relationships
country = await partner.country_id
children = await partner.child_ids

# Invalidate all cached relationships
partner._relationship_manager.invalidate_all()

# Next access will reload from server
country_fresh = await partner.country_id
children_fresh = await partner.child_ids
```

#### `invalidate_field(field_name)`

Invalidate a specific relationship field.

**Parameters:**

- `field_name` (str): Name of the field to invalidate

**Example:**

```python
partner = await client.model(ResPartner).filter(id=1).first()

# Load country
country = await partner.country_id

# Invalidate only country relationship
partner._relationship_manager.invalidate_field("country_id")

# Country will be reloaded, but other relationships remain cached
country_fresh = await partner.country_id
```

## Relationship Patterns

### Many2One Relationships

Single record relationships with lazy loading.

```python
class SaleOrder(OdooModel):
    _odoo_name: ClassVar[str] = "sale.order"
    
    partner_id: Optional["ResPartner"] = Many2OneField(
        "res.partner",
        description="Customer"
    )

# Usage
order_data = await client.search_read('sale.order', [('id', '=', 1)], limit=1)
order = SaleOrder.model_validate(order_data[0])

# Lazy loading
customer = await order.partner_id
if customer:
    print(f"Customer: {customer.name}")
```

### One2Many Relationships

Collection relationships with batch loading.

```python
class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    child_ids: List["ResPartner"] = One2ManyField(
        "res.partner",
        "parent_id",
        description="Child companies"
    )

# Usage
company = await client.model(ResPartner).filter(id=1).first()

# Load all children
children = await company.child_ids
print(f"Company has {len(children)} subsidiaries")

for child in children:
    print(f"- {child.name}")
```

### Many2Many Relationships

Multiple record relationships with efficient loading.

```python
class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    category_id: List["ResPartnerCategory"] = Many2ManyField(
        "res.partner.category",
        description="Partner categories"
    )

# Usage
partner = await client.model(ResPartner).filter(id=1).first()

# Load all categories
categories = await partner.category_id
print(f"Partner has {len(categories)} categories")

for category in categories:
    print(f"- {category.name}")
```

## Advanced Relationship Handling

### Prefetching with QuerySet

Use QuerySet prefetching for optimal performance.

```python
# Get partners and manually prefetch relationships
partners = await client.model(ResPartner).filter(is_company=True).limit(50).all()

# Prefetch relationships for all partners
for partner in partners:
    await partner._relationship_manager.prefetch_relationships([
        "country_id", "state_id", "child_ids"
    ])

# All relationships are pre-loaded
for partner in partners:
    country = await partner.country_id    # No database query
    state = await partner.state_id        # No database query
    children = await partner.child_ids    # No database query
    
    print(f"{partner.name} ({country.name if country else 'No country'})")
    print(f"  Children: {len(children)}")
```

### Deep Relationship Prefetching

Prefetch nested relationships efficiently.

```python
# Prefetch nested relationships
orders_data = await client.search_read('sale.order', [('state', '=', 'sale')])
orders = [SaleOrder.model_validate(data) for data in orders_data]

# Prefetch relationships for all orders
for order in orders:
    await order._relationship_manager.prefetch_relationships([
        "partner_id", "order_line"
    ])

# Access nested relationships without additional queries
for order in orders:
    customer = await order.partner_id
    country = await customer.country_id if customer else None
    lines = await order.order_line
    
    print(f"Order {order.name}")
    print(f"  Customer: {customer.name if customer else 'Unknown'}")
    print(f"  Country: {country.name if country else 'Unknown'}")
    print(f"  Lines: {len(lines)}")
    
    for line in lines:
        product = await line.product_id
        print(f"    - {product.name if product else 'Unknown product'}")
```

### Conditional Relationship Loading

Load relationships based on conditions.

```python
async def load_partner_details(partner: ResPartner, include_children: bool = False):
    """Load partner details with conditional relationship loading."""
    
    # Always load country
    country = await partner.country_id
    
    # Conditionally load children
    children = []
    if include_children:
        children = await partner.child_ids
    
    # Load orders only for companies
    orders = []
    if partner.is_company:
        orders = await partner.sale_order_ids
    
    return {
        "partner": partner,
        "country": country,
        "children": children,
        "orders": orders
    }

# Usage
partner = await client.model(ResPartner).filter(id=1).first()
details = await load_partner_details(partner, include_children=True)
```

### Relationship Caching Strategies

Implement custom caching strategies for relationships.

```python
class CachedPartner(ResPartner):
    """Partner with enhanced relationship caching."""
    
    def __init__(self, **data):
        super().__init__(**data)
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps = {}
    
    async def get_country_cached(self) -> Optional["ResCountry"]:
        """Get country with time-based caching."""
        import time
        
        current_time = time.time()
        cache_key = "country_id"
        
        # Check if cache is still valid
        if (cache_key in self._cache_timestamps and 
            current_time - self._cache_timestamps[cache_key] < self._cache_ttl and
            self.country_id.is_loaded()):
            return self.country_id.get_cached_data()
        
        # Load fresh data
        country = await self.country_id
        self._cache_timestamps[cache_key] = current_time
        
        return country
    
    async def refresh_relationships(self):
        """Refresh all cached relationships."""
        self._relationship_manager.invalidate_all()
        self._cache_timestamps.clear()
```

## Performance Optimization

### Batch Loading Optimization

```python
async def load_partners_with_countries(partner_ids: List[int]):
    """Efficiently load partners with their countries."""
    
    # Load all partners
    partners = await client.model(ResPartner).filter(id__in=partner_ids).all()
    
    # Batch load all countries in one query
    # This happens automatically due to batch loading
    countries = {}
    for partner in partners:
        country = await partner.country_id
        if country:
            countries[partner.id] = country
    
    return partners, countries
```

### Memory Management

```python
async def process_large_dataset():
    """Process large dataset with memory management."""
    
    # Process in chunks to manage memory
    chunk_size = 100
    offset = 0
    
    while True:
        partners_data = await client.search_read(
            'res.partner',
            [('is_company', '=', True)],
            offset=offset,
            limit=chunk_size
        )
        partners = [ResPartner.model_validate(data) for data in partners_data]
        
        if not partners:
            break
        
        # Process chunk
        for partner in partners:
            country = await partner.country_id
            # Process partner and country
            
        # Clear relationship caches to free memory
        for partner in partners:
            partner._relationship_manager.invalidate_all()
        
        offset += chunk_size
```

## Error Handling

### Relationship Loading Errors

```python
async def safe_relationship_access(partner: ResPartner):
    """Safely access relationships with error handling."""
    
    try:
        # Try to load country
        country = await partner.country_id
        country_name = country.name if country else "Unknown"
    except Exception as e:
        print(f"Failed to load country: {e}")
        country_name = "Error loading country"
    
    try:
        # Try to load children
        children = await partner.child_ids
        children_count = len(children)
    except Exception as e:
        print(f"Failed to load children: {e}")
        children_count = 0
    
    return {
        "country": country_name,
        "children_count": children_count
    }
```

### Timeout Handling

```python
import asyncio

async def load_with_timeout(relationship: LazyRelationship, timeout: float = 10.0):
    """Load relationship with timeout."""
    
    try:
        return await asyncio.wait_for(relationship.load(), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"Relationship loading timed out after {timeout} seconds")
        return None
    except Exception as e:
        print(f"Relationship loading failed: {e}")
        return None

# Usage
partner = await client.model(ResPartner).filter(id=1).first()
country = await load_with_timeout(partner.country_id, timeout=5.0)
```

## Best Practices

### 1. Use Prefetching for Known Access Patterns

```python
# ✅ Good: Prefetch known relationships
partners = await client.model(ResPartner).all()
for partner in partners:
    await partner._relationship_manager.prefetch_relationships(["country_id", "state_id"])

# ❌ Avoid: Loading relationships in loops
partners = await client.model(ResPartner).all()
for partner in partners:
    country = await partner.country_id  # N+1 queries
```

### 2. Invalidate Caches When Data Changes

```python
# ✅ Good: Invalidate after updates
await client.write("res.partner", [partner.id], {"country_id": new_country_id})
partner._relationship_manager.invalidate_field("country_id")

# ❌ Avoid: Using stale cached data
await client.write("res.partner", [partner.id], {"country_id": new_country_id})
country = await partner.country_id  # Returns old cached data
```

### 3. Handle Missing Relationships Gracefully

```python
# ✅ Good: Check for None values
country = await partner.country_id
country_name = country.name if country else "No country"

# ❌ Avoid: Assuming relationships exist
country = await partner.country_id
country_name = country.name  # May raise AttributeError
```

## Next Steps

- Learn about [Model Validation](../validation.md) for relationship validation
- Explore [Query Optimization](../../query/optimization.md) for efficient queries
- Check [Performance Tuning](../../performance/relationships.md) for relationship optimization
