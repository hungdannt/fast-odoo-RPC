# Relationships

Zenoo RPC provides intelligent relationship handling with lazy loading, type safety, and performance optimization. This eliminates the complexity of Odoo's tuple commands while maintaining full functionality.

## Overview

Zenoo RPC handles three types of relationships:

- **Many2one**: Single related record (e.g., partner → country)
- **One2many**: Collection of related records (e.g., partner → invoices)
- **Many2many**: Collection of linked records (e.g., partner → categories)

All relationships are **lazy-loaded** by default for optimal performance.

## Many2one Relationships

### Basic Usage

```python
from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner

async with ZenooClient("localhost", port=8069) as client:
    await client.login("my_database", "admin", "admin")
    
    # Get a partner
    partner = await client.model(ResPartner).get(1)
    
    # Access related country (lazy-loaded)
    country = await partner.country_id
    print(f"Partner {partner.name} is from {country.name}")
    
    # Access nested relationships
    state = await partner.state_id
    if state:
        country_via_state = await state.country_id
        print(f"State: {state.name}, Country: {country_via_state.name}")
```

### Checking for Existence

```python
# Check if relationship exists before accessing
partner = await client.model(ResPartner).get(1)

if partner.country_id:
    country = await partner.country_id
    print(f"Country: {country.name}")
else:
    print("No country set")

# Alternative: Handle None gracefully
country = await partner.country_id
if country:
    print(f"Country: {country.name}")
```

### Setting Many2one Relationships

```python
# Set by ID
partner.country_id = 233  # Set to specific country ID

# Set by record
country = await client.model(ResCountry).filter(code="US").first()
partner.country_id = country

# Clear relationship
partner.country_id = None

# Save changes
await partner.save()
```

## One2many Relationships

### Basic Usage

```python
from zenoo_rpc.models.common import ResPartner, SaleOrder

# Get partner with orders
partner = await client.model(ResPartner).get(1)

# Access all orders (lazy-loaded)
orders = await partner.sale_order_ids.all()
print(f"Partner has {len(orders)} orders")

# Iterate through orders
async for order in partner.sale_order_ids:
    print(f"Order {order.name}: {order.amount_total}")
```

### Filtering Related Records

```python
# Filter related records
recent_orders = await partner.sale_order_ids.filter(
    create_date__gte=datetime.now() - timedelta(days=30)
).all()

# Count related records
order_count = await partner.sale_order_ids.count()

# Check existence
has_orders = await partner.sale_order_ids.exists()

# Get first/last
first_order = await partner.sale_order_ids.order_by("create_date").first()
latest_order = await partner.sale_order_ids.order_by("-create_date").first()
```

### Adding Records to One2many

```python
# Create new related record
new_order = await partner.sale_order_ids.create({
    "name": "SO001",
    "date_order": datetime.now(),
    "state": "draft"
})

# Add existing record (if foreign key allows)
existing_order = await client.model(SaleOrder).get(123)
existing_order.partner_id = partner
await existing_order.save()
```

### Removing Records from One2many

```python
# Remove specific order
order_to_remove = await partner.sale_order_ids.filter(name="SO001").first()
if order_to_remove:
    await order_to_remove.delete()

# Bulk remove
await partner.sale_order_ids.filter(state="cancel").delete()

# Clear all (set foreign key to None)
await partner.sale_order_ids.update(partner_id=None)
```

## Many2many Relationships

### Basic Usage

```python
from zenoo_rpc.models.common import ResPartner, ResPartnerCategory

# Get partner with categories
partner = await client.model(ResPartner).get(1)

# Access all categories
categories = await partner.category_id.all()
print(f"Partner has {len(categories)} categories")

# Iterate through categories
async for category in partner.category_id:
    print(f"Category: {category.name}")
```

### Managing Many2many Relationships

```python
# Add categories
category1 = await client.model(ResPartnerCategory).get(1)
category2 = await client.model(ResPartnerCategory).get(2)

# Add single category
await partner.category_id.add(category1)

# Add multiple categories
await partner.category_id.add([category1, category2])

# Add by ID
await partner.category_id.add([1, 2, 3])

# Remove categories
await partner.category_id.remove(category1)
await partner.category_id.remove([1, 2])

# Clear all categories
await partner.category_id.clear()

# Set categories (replace all)
await partner.category_id.set([category1, category2])
await partner.category_id.set([1, 2, 3])  # By IDs
```

### Filtering Many2many

```python
# Filter categories
active_categories = await partner.category_id.filter(active=True).all()

# Check if specific category exists
has_vip_category = await partner.category_id.filter(name="VIP").exists()

# Count categories
category_count = await partner.category_id.count()
```

## Prefetching for Performance

### Single Level Prefetching

```python
# Prefetch related data to avoid N+1 queries
partners = await client.model(ResPartner).filter(
    is_company=True
).prefetch_related("country_id", "category_id").all()

# Now accessing relationships doesn't trigger additional queries
for partner in partners:
    country = await partner.country_id  # No additional query
    categories = await partner.category_id.all()  # No additional query
```

### Multi-level Prefetching

```python
# Prefetch nested relationships
partners = await client.model(ResPartner).filter(
    is_company=True
).prefetch_related(
    "country_id",
    "state_id__country_id",  # Prefetch state's country
    "sale_order_ids__order_line"  # Prefetch order lines
).all()

# Access nested data without additional queries
for partner in partners:
    state = await partner.state_id
    if state:
        country = await state.country_id  # No additional query
    
    orders = await partner.sale_order_ids.all()
    for order in orders:
        lines = await order.order_line.all()  # No additional query
```

### Select Related

```python
# Include related field data in the main query
partners = await client.model(ResPartner).filter(
    is_company=True
).select_related("country_id", "state_id").all()

# Related data is immediately available
for partner in partners:
    # These don't trigger additional queries
    print(f"Partner: {partner.name}")
    print(f"Country: {partner.country_id.name}")
    print(f"State: {partner.state_id.name if partner.state_id else 'N/A'}")
```

## Advanced Relationship Patterns

### Reverse Relationships

```python
# Access reverse relationships
country = await client.model(ResCountry).get(233)  # United States

# Get all partners from this country
us_partners = await country.partner_ids.all()

# Filter reverse relationship
active_us_partners = await country.partner_ids.filter(active=True).all()
```

### Through Relationships

```python
# For many2many with additional fields, access the through model
from zenoo_rpc.models.common import ResPartnerCategoryRel

# Direct many2many access
categories = await partner.category_id.all()

# Through model access for additional fields
category_relations = await client.model(ResPartnerCategoryRel).filter(
    partner_id=partner.id
).all()

for rel in category_relations:
    category = await rel.category_id
    print(f"Category: {category.name}, Added: {rel.create_date}")
```

### Conditional Relationships

```python
# Load relationships conditionally
partner = await client.model(ResPartner).get(1)

# Only load orders if partner is a company
if partner.is_company:
    orders = await partner.sale_order_ids.all()
    print(f"Company has {len(orders)} orders")
else:
    print("Individual customer")
```

## Relationship Caching

### Cache Related Data

```python
# Cache relationship queries
partner = await client.model(ResPartner).get(1)

# Cache country data
country = await partner.country_id.cache(ttl=3600)  # Cache for 1 hour

# Cache order list
orders = await partner.sale_order_ids.cache(
    key=f"partner_{partner.id}_orders",
    ttl=300
).all()
```

### Invalidate Relationship Cache

```python
# Invalidate when data changes
await partner.sale_order_ids.cache_invalidate()

# Invalidate specific cache key
await client.cache_manager.invalidate(f"partner_{partner.id}_orders")
```

## Working with Computed Relationships

### Computed Fields

```python
# Some relationships might be computed
partner = await client.model(ResPartner).get(1)

# Access computed relationship
total_invoiced = await partner.total_invoiced  # Computed field
child_count = await partner.child_ids.count()  # Computed count
```

### Custom Relationship Logic

```python
# Implement custom relationship logic
class CustomPartner(ResPartner):
    async def get_recent_orders(self, days=30):
        """Get orders from the last N days"""
        return await self.sale_order_ids.filter(
            create_date__gte=datetime.now() - timedelta(days=days)
        ).all()
    
    async def get_top_categories(self, limit=5):
        """Get most used categories"""
        return await self.category_id.order_by("-usage_count").limit(limit).all()

# Usage
partner = await client.model(CustomPartner).get(1)
recent_orders = await partner.get_recent_orders(days=7)
top_categories = await partner.get_top_categories(limit=3)
```

## Error Handling

```python
from zenoo_rpc.exceptions import RelationshipError, NotFoundError

try:
    partner = await client.model(ResPartner).get(1)
    
    # Handle missing relationships gracefully
    country = await partner.country_id
    if country is None:
        print("No country set for this partner")
    
    # Handle relationship errors
    orders = await partner.sale_order_ids.all()
    
except NotFoundError:
    print("Partner not found")
    
except RelationshipError as e:
    print(f"Relationship error: {e}")
```

## Best Practices

### 1. Use Prefetching for Multiple Records

```python
# Good: Prefetch when accessing relationships for multiple records
partners = await client.model(ResPartner).prefetch_related("country_id").all()
for partner in partners:
    country = await partner.country_id  # No N+1 queries

# Avoid: Accessing relationships without prefetching
partners = await client.model(ResPartner).all()
for partner in partners:
    country = await partner.country_id  # N+1 queries!
```

### 2. Check Existence Before Access

```python
# Good: Check before accessing
if partner.country_id:
    country = await partner.country_id
    print(country.name)

# Avoid: Assuming relationship exists
country = await partner.country_id
print(country.name)  # Could raise AttributeError if None
```

### 3. Use Appropriate Relationship Methods

```python
# Good: Use count() for counting
order_count = await partner.sale_order_ids.count()

# Avoid: Loading all records just to count
orders = await partner.sale_order_ids.all()
order_count = len(orders)  # Inefficient
```

### 4. Cache Frequently Accessed Relationships

```python
# Good: Cache stable relationship data
country = await partner.country_id.cache(ttl=3600)

# Avoid: Caching frequently changing data
orders = await partner.sale_order_ids.cache(ttl=3600)  # Orders change often
```

## Next Steps

- Learn about [Caching](caching.md) for relationship performance optimization
- Explore [Batch Operations](batch-operations.md) for bulk relationship management
- Check [Query Builder](queries.md) for advanced relationship filtering
