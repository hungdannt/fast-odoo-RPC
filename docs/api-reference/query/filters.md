# Query Filters API Reference

Advanced filtering capabilities with Q objects, field lookups, and logical operators for building complex Odoo queries with Django-like syntax.

## Overview

The filtering system provides:

- **Q Objects**: Django-like query objects for complex logical operations
- **Field Lookups**: Rich field lookup syntax with operators
- **Logical Operators**: AND, OR, NOT operations with proper precedence
- **FilterExpression**: Keyword-based filtering with automatic conversion
- **Domain Generation**: Automatic conversion to Odoo domain format

## Q Objects

Django-like Q objects for building complex queries with logical operators.

### Constructor

```python
class Q:
    """Django-like Q object for building complex queries."""
    
    def __init__(self, **filters: Any):
        """Initialize Q object with filters."""
        self.filters = filters
        self.children = []
        self.connector = "AND"
        self.negated = False
```

**Parameters:**

- `**filters` (Any): Field filters using Django-like syntax

**Example:**

```python
from zenoo_rpc.query.filters import Q

# Simple Q object
q1 = Q(name="ACME Corp")
q2 = Q(is_company=True)

# Field lookups
q3 = Q(name__ilike="acme%")
q4 = Q(customer_rank__gte=1)
```

### Logical Operators

#### `__and__` (& operator)

Combine Q objects with AND operator.

**Returns:** `Q` - New Q object with AND logic

**Example:**

```python
# AND operation
q_and = Q(is_company=True) & Q(active=True)

# Multiple AND operations
q_complex = Q(is_company=True) & Q(active=True) & Q(customer_rank__gt=0)

# Use in query
partners = await client.model(ResPartner).filter(q_and).all()
```

#### `__or__` (| operator)

Combine Q objects with OR operator.

**Returns:** `Q` - New Q object with OR logic

**Example:**

```python
# OR operation
q_or = Q(name__ilike="acme%") | Q(name__ilike="corp%")

# Multiple OR operations
q_search = Q(name__ilike="john%") | Q(email__ilike="john%") | Q(phone__ilike="john%")

# Use in query
partners = await client.model(ResPartner).filter(q_or).all()
```

#### `__invert__` (~ operator)

Negate Q object with NOT operator.

**Returns:** `Q` - New Q object with NOT logic

**Example:**

```python
# NOT operation
q_not = ~Q(active=False)

# NOT with complex expression
q_not_complex = ~(Q(name__ilike="test%") | Q(name__ilike="demo%"))

# Use in query
partners = await client.model(ResPartner).filter(q_not).all()
```

### Complex Query Building

#### Combining Multiple Operators

```python
from zenoo_rpc.query.filters import Q

# Complex query with mixed operators
complex_query = (
    (Q(name__ilike="acme%") | Q(name__ilike="corp%")) &
    Q(is_company=True) &
    ~Q(active=False)
)

# Use in query
partners = await client.model(ResPartner).filter(complex_query).all()

# Equivalent to SQL:
# WHERE ((name ILIKE 'acme%' OR name ILIKE 'corp%') 
#        AND is_company = true 
#        AND NOT (active = false))
```

#### Nested Conditions

```python
# Nested OR conditions within AND
customer_query = (
    Q(customer_rank__gt=0) &
    (Q(country_id__code="US") | Q(country_id__code="CA")) &
    (Q(email__isnull=False) | Q(phone__isnull=False))
)

customers = await client.model(ResPartner).filter(customer_query).all()
```

### Domain Conversion

#### `to_domain()`

Convert Q object to Odoo domain format.

**Returns:** `List[Union[str, Tuple[str, str, Any]]]` - Odoo domain

**Example:**

```python
# Simple Q object
q = Q(name="ACME Corp", is_company=True)
domain = q.to_domain()
# Result: [('name', '=', 'ACME Corp'), ('is_company', '=', True)]

# Complex Q object with OR
q_complex = Q(name__ilike="acme%") | Q(email__contains="acme")
domain = q_complex.to_domain()
# Result: ['|', ('name', 'ilike', 'acme%'), ('email', 'ilike', '%acme%')]

# Q object with NOT
q_not = ~Q(active=False)
domain = q_not.to_domain()
# Result: ['!', ('active', '=', False)]
```

## Field Lookups

Rich field lookup syntax for precise filtering conditions.

### Supported Lookups

| Lookup | Operator | Description | Example |
|--------|----------|-------------|---------|
| `exact` | `=` | Exact match (default) | `name__exact="ACME"` |
| `iexact` | `ilike` | Case-insensitive exact | `name__iexact="acme"` |
| `contains` | `ilike` | Contains substring | `name__contains="corp"` |
| `icontains` | `ilike` | Case-insensitive contains | `name__icontains="CORP"` |
| `startswith` | `ilike` | Starts with | `name__startswith="ACME"` |
| `istartswith` | `ilike` | Case-insensitive starts | `name__istartswith="acme"` |
| `endswith` | `ilike` | Ends with | `name__endswith="Corp"` |
| `iendswith` | `ilike` | Case-insensitive ends | `name__iendswith="corp"` |
| `like` | `like` | SQL LIKE pattern | `name__like="ACME%"` |
| `ilike` | `ilike` | SQL ILIKE pattern | `name__ilike="acme%"` |
| `gt` | `>` | Greater than | `customer_rank__gt=0` |
| `gte` | `>=` | Greater than or equal | `customer_rank__gte=1` |
| `lt` | `<` | Less than | `customer_rank__lt=5` |
| `lte` | `<=` | Less than or equal | `customer_rank__lte=10` |
| `ne` | `!=` | Not equal | `state__ne="draft"` |
| `in` | `in` | In list | `id__in=[1,2,3]` |
| `not_in` | `not in` | Not in list | `id__not_in=[1,2,3]` |
| `isnull` | `=` | Is null/false | `parent_id__isnull=True` |
| `isnotnull` | `!=` | Is not null/false | `email__isnotnull=True` |

### String Lookups

```python
# Exact match (case-sensitive)
partners = await client.model(ResPartner).filter(
    Q(name__exact="ACME Corporation")
).all()

# Case-insensitive exact match
partners = await client.model(ResPartner).filter(
    Q(name__iexact="acme corporation")
).all()

# Contains substring
partners = await client.model(ResPartner).filter(
    Q(name__contains="Corp")
).all()

# Case-insensitive contains
partners = await client.model(ResPartner).filter(
    Q(name__icontains="corp")
).all()

# Starts with
partners = await client.model(ResPartner).filter(
    Q(name__startswith="ACME")
).all()

# Ends with
partners = await client.model(ResPartner).filter(
    Q(name__endswith="Inc")
).all()

# SQL LIKE pattern
partners = await client.model(ResPartner).filter(
    Q(name__like="ACME%")
).all()

# SQL ILIKE pattern (case-insensitive)
partners = await client.model(ResPartner).filter(
    Q(name__ilike="acme%")
).all()
```

### Numeric Lookups

```python
# Greater than
partners = await client.model(ResPartner).filter(
    Q(customer_rank__gt=0)
).all()

# Greater than or equal
partners = await client.model(ResPartner).filter(
    Q(customer_rank__gte=1)
).all()

# Less than
partners = await client.model(ResPartner).filter(
    Q(customer_rank__lt=5)
).all()

# Less than or equal
partners = await client.model(ResPartner).filter(
    Q(customer_rank__lte=10)
).all()

# Not equal
partners = await client.model(ResPartner).filter(
    Q(customer_rank__ne=0)
).all()

# Range query (combining gte and lte)
partners = await client.model(ResPartner).filter(
    Q(customer_rank__gte=1) & Q(customer_rank__lte=5)
).all()
```

### List Lookups

```python
# In list
partners = await client.model(ResPartner).filter(
    Q(id__in=[1, 2, 3, 4, 5])
).all()

# Not in list
partners = await client.model(ResPartner).filter(
    Q(name__not_in=["Test Company", "Demo Company"])
).all()

# Multiple values with OR
partners = await client.model(ResPartner).filter(
    Q(country_id__code__in=["US", "CA", "GB"])
).all()
```

### Null Checks

```python
# Is null (for optional fields)
partners = await client.model(ResPartner).filter(
    Q(parent_id__isnull=True)
).all()

# Is not null
partners = await client.model(ResPartner).filter(
    Q(email__isnotnull=True)
).all()

# Combine null checks
partners = await client.model(ResPartner).filter(
    Q(email__isnotnull=True) & Q(phone__isnotnull=True)
).all()
```

### Relationship Field Lookups

```python
# Related field access
partners = await client.model(ResPartner).filter(
    Q(country_id__name="United States")
).all()

# Deep relationship traversal
partners = await client.model(ResPartner).filter(
    Q(parent_id__country_id__code="US")
).all()

# Multiple related field conditions
partners = await client.model(ResPartner).filter(
    Q(country_id__name="United States") &
    Q(state_id__name="California")
).all()

# Related field with lookups
partners = await client.model(ResPartner).filter(
    Q(country_id__name__ilike="united%")
).all()
```

## FilterExpression

Keyword-based filtering with automatic conversion to domain format.

### Constructor

```python
class FilterExpression(Expression):
    """Represents a filter expression built from keyword arguments."""
    
    def __init__(self, **filters: Any):
        """Initialize filter expression with keyword arguments."""
        self.filters = filters
```

**Example:**

```python
from zenoo_rpc.query.filters import FilterExpression

# Simple filters
expr = FilterExpression(name="ACME Corp", is_company=True)

# Field lookups
expr = FilterExpression(
    name__ilike="acme%",
    customer_rank__gte=1,
    email__isnotnull=True
)

# Convert to domain
domain = expr.to_domain()
```

### Domain Conversion

#### `to_domain()`

Convert filters to Odoo domain format.

**Returns:** `List[Tuple[str, str, Any]]` - List of domain tuples

**Example:**

```python
# Simple filters
expr = FilterExpression(name="ACME", active=True)
domain = expr.to_domain()
# Result: [('name', '=', 'ACME'), ('active', '=', True)]

# Field lookups
expr = FilterExpression(
    name__ilike="acme%",
    customer_rank__gt=0
)
domain = expr.to_domain()
# Result: [('name', 'ilike', 'acme%'), ('customer_rank', '>', 0)]
```

## Advanced Query Patterns

### Search Queries

```python
def build_search_query(search_term: str) -> Q:
    """Build a comprehensive search query."""
    return (
        Q(name__icontains=search_term) |
        Q(email__icontains=search_term) |
        Q(phone__icontains=search_term) |
        Q(ref__icontains=search_term)
    )

# Usage
search_query = build_search_query("acme")
partners = await client.model(ResPartner).filter(search_query).all()
```

### Dynamic Filtering

```python
def build_dynamic_filter(**criteria) -> Q:
    """Build dynamic filter based on criteria."""
    q = Q()
    
    if criteria.get("name"):
        q = q & Q(name__icontains=criteria["name"])
    
    if criteria.get("is_company") is not None:
        q = q & Q(is_company=criteria["is_company"])
    
    if criteria.get("country_codes"):
        q = q & Q(country_id__code__in=criteria["country_codes"])
    
    if criteria.get("min_rank"):
        q = q & Q(customer_rank__gte=criteria["min_rank"])
    
    return q

# Usage
criteria = {
    "name": "corp",
    "is_company": True,
    "country_codes": ["US", "CA"],
    "min_rank": 1
}

filter_query = build_dynamic_filter(**criteria)
partners = await client.model(ResPartner).filter(filter_query).all()
```

### Conditional Queries

```python
async def get_partners_by_type(
    partner_type: str,
    active_only: bool = True,
    country_code: str = None
) -> List[ResPartner]:
    """Get partners with conditional filtering."""
    
    # Base query
    query = Q()
    
    # Partner type filtering
    if partner_type == "customer":
        query = query & Q(customer_rank__gt=0)
    elif partner_type == "supplier":
        query = query & Q(supplier_rank__gt=0)
    elif partner_type == "company":
        query = query & Q(is_company=True)
    
    # Active filter
    if active_only:
        query = query & Q(active=True)
    
    # Country filter
    if country_code:
        query = query & Q(country_id__code=country_code)
    
    return await client.model(ResPartner).filter(query).all()

# Usage
customers = await get_partners_by_type("customer", country_code="US")
suppliers = await get_partners_by_type("supplier", active_only=False)
```

### Query Composition

```python
class PartnerQueryBuilder:
    """Builder for complex partner queries."""
    
    def __init__(self):
        self.query = Q()
    
    def companies_only(self):
        """Filter for companies only."""
        self.query = self.query & Q(is_company=True)
        return self
    
    def customers_only(self):
        """Filter for customers only."""
        self.query = self.query & Q(customer_rank__gt=0)
        return self
    
    def active_only(self):
        """Filter for active records only."""
        self.query = self.query & Q(active=True)
        return self
    
    def in_country(self, country_code: str):
        """Filter by country code."""
        self.query = self.query & Q(country_id__code=country_code)
        return self
    
    def with_email(self):
        """Filter for records with email."""
        self.query = self.query & Q(email__isnotnull=True)
        return self
    
    def name_contains(self, text: str):
        """Filter by name containing text."""
        self.query = self.query & Q(name__icontains=text)
        return self
    
    def build(self) -> Q:
        """Build the final query."""
        return self.query

# Usage
query = (PartnerQueryBuilder()
         .companies_only()
         .customers_only()
         .active_only()
         .in_country("US")
         .with_email()
         .name_contains("tech")
         .build())

partners = await client.model(ResPartner).filter(query).all()
```

## Performance Considerations

### Query Optimization

```python
# ✅ Good: Use specific field lookups
partners = await client.model(ResPartner).filter(
    Q(name__ilike="acme%")  # Uses index on name field
).all()

# ❌ Avoid: Broad contains searches
partners = await client.model(ResPartner).filter(
    Q(name__contains="corp")  # May not use index efficiently
).all()

# ✅ Good: Combine filters efficiently
partners = await client.model(ResPartner).filter(
    Q(is_company=True) & Q(active=True) & Q(customer_rank__gt=0)
).all()

# ❌ Avoid: Multiple separate filter calls
partners = await client.model(ResPartner).filter(
    Q(is_company=True)
).filter(
    Q(active=True)
).filter(
    Q(customer_rank__gt=0)
).all()
```

### Index-Friendly Queries

```python
# ✅ Good: Use indexed fields for filtering
partners = await client.model(ResPartner).filter(
    Q(id__in=[1, 2, 3, 4, 5])  # Primary key lookup
).all()

# ✅ Good: Use exact matches when possible
partners = await client.model(ResPartner).filter(
    Q(email="contact@acme.com")  # Exact match
).all()

# ✅ Good: Use range queries efficiently
partners = await client.model(ResPartner).filter(
    Q(create_date__gte="2023-01-01") & Q(create_date__lt="2024-01-01")
).all()
```

## Best Practices

### 1. Use Q Objects for Complex Logic

```python
# ✅ Good: Clear logical structure
query = (
    (Q(name__ilike="acme%") | Q(name__ilike="corp%")) &
    Q(is_company=True) &
    ~Q(active=False)
)

# ❌ Avoid: Complex nested kwargs
# This is harder to read and maintain
```

### 2. Combine Related Conditions

```python
# ✅ Good: Group related conditions
customer_query = (
    Q(customer_rank__gt=0) &
    Q(active=True) &
    (Q(email__isnotnull=True) | Q(phone__isnotnull=True))
)

# ❌ Avoid: Scattered conditions
```

### 3. Use Appropriate Field Lookups

```python
# ✅ Good: Use specific lookups
Q(name__startswith="ACME")  # When you know it starts with ACME
Q(email__exact="user@domain.com")  # When you have exact email

# ❌ Avoid: Overly broad lookups
Q(name__contains="A")  # Too broad, may return too many results
```

## Ordering Results

### `order_by(*fields)`

Order query results by specified fields.

**Parameters:**

- `*fields` (str): Field names to order by. Prefix with `-` for descending order.

**Returns:** `QuerySet` - Ordered QuerySet

**Examples:**

```python
# Order by single field (ascending)
partners = await client.model(ResPartner).order_by("name").all()

# Order by multiple fields
partners = await client.model(ResPartner).order_by("country_id", "name").all()

# Descending order (prefix with -)
partners = await client.model(ResPartner).order_by("-create_date").all()

# Mixed ordering
partners = await client.model(ResPartner).order_by("country_id", "-name").all()
```

## Next Steps

- Learn about [Field Expressions](expressions.md) for advanced field operations
- Explore [Query Optimization](../performance/queries.md) for performance tuning
- Check [Query Builder](../builder.md) for fluent query construction
