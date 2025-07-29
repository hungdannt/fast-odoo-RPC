# Field Expressions API Reference

Type-safe field expressions for building complex Odoo queries with fluent interface, comparison operators, and logical combinations.

## Overview

The expressions system provides:

- **Field Class**: Fluent interface for field-based conditions
- **Comparison Expressions**: Type-safe comparison operators
- **Logical Expressions**: AND, OR, NOT combinations
- **Pattern Matching**: LIKE, ILIKE, contains, starts/ends with
- **Domain Generation**: Automatic conversion to Odoo domain format

## Field Class

Represents a field in query expressions with fluent interface for building conditions.

### Constructor

```python
class Field:
    """Represents a field in query expressions."""
    
    def __init__(self, name: str):
        """Initialize a field reference."""
        self.name = name
```

**Parameters:**

- `name` (str): Field name (supports dot notation for related fields)

**Example:**

```python
from zenoo_rpc.query.expressions import Field
from zenoo_rpc.models.common import ResPartner

# Simple field
name_field = Field("name")
active_field = Field("active")

# Related field with dot notation
country_name = Field("country_id.name")
parent_email = Field("parent_id.email")
```

### Comparison Operators

#### Equality Operators

```python
# Equality (==)
def __eq__(self, value: Any) -> Equal:
    """Create an equality condition."""

# Not equal (!=)
def __ne__(self, value: Any) -> NotEqual:
    """Create a not-equal condition."""
```

**Example:**

```python
name_field = Field("name")
active_field = Field("active")

# Equality conditions
name_equals = name_field == "ACME Corp"
active_true = active_field == True

# Not equal conditions
name_not_test = name_field != "Test Company"
active_not_false = active_field != False

# Use in queries
partners = await client.model(ResPartner).filter(
    name_equals & active_true
).all()
```

#### Numeric Comparison Operators

```python
# Greater than (>)
def __gt__(self, value: Any) -> GreaterThan:
    """Create a greater-than condition."""

# Greater than or equal (>=)
def __ge__(self, value: Any) -> GreaterEqual:
    """Create a greater-than-or-equal condition."""

# Less than (<)
def __lt__(self, value: Any) -> LessThan:
    """Create a less-than condition."""

# Less than or equal (<=)
def __le__(self, value: Any) -> LessEqual:
    """Create a less-than-or-equal condition."""
```

**Example:**

```python
rank_field = Field("customer_rank")
age_field = Field("age")

# Numeric comparisons
high_rank = rank_field > 5
min_rank = rank_field >= 1
young = age_field < 30
adult = age_field >= 18

# Range conditions
adult_range = (age_field >= 18) & (age_field <= 65)

# Use in queries
customers = await client.model(ResPartner).filter(
    high_rank & adult_range
).all()
```

### String Pattern Methods

#### `like(pattern)`

Create a LIKE condition (case-sensitive pattern matching).

**Parameters:**

- `pattern` (str): SQL LIKE pattern with % and _ wildcards

**Returns:** `Like` - LIKE expression

**Example:**

```python
name_field = Field("name")

# Case-sensitive LIKE
starts_with_acme = name_field.like("ACME%")
contains_corp = name_field.like("%Corp%")
ends_with_inc = name_field.like("%Inc")

# Use wildcards
pattern_match = name_field.like("A_ME%")  # A + any char + ME + anything
```

#### `ilike(pattern)`

Create an ILIKE condition (case-insensitive pattern matching).

**Parameters:**

- `pattern` (str): SQL ILIKE pattern with % and _ wildcards

**Returns:** `ILike` - ILIKE expression

**Example:**

```python
name_field = Field("name")

# Case-insensitive ILIKE
starts_with_acme = name_field.ilike("acme%")
contains_corp = name_field.ilike("%corp%")
ends_with_inc = name_field.ilike("%inc")

# Mixed case patterns
mixed_pattern = name_field.ilike("AcMe%")
```

#### `contains(value)`

Create a contains condition (field contains substring).

**Parameters:**

- `value` (str): Substring to search for

**Returns:** `Contains` - Contains expression (uses ILIKE with % wildcards)

**Example:**

```python
name_field = Field("name")
email_field = Field("email")

# Contains substring
name_contains_corp = name_field.contains("Corp")
email_contains_acme = email_field.contains("acme")

# Use in queries
partners = await client.model(ResPartner).filter(
    name_contains_corp | email_contains_acme
).all()
```

#### `startswith(value)`

Create a starts-with condition.

**Parameters:**

- `value` (str): Prefix to match

**Returns:** `StartsWith` - Starts-with expression

**Example:**

```python
name_field = Field("name")

# Starts with prefix
starts_with_acme = name_field.startswith("ACME")
starts_with_global = name_field.startswith("Global")

# Use in queries
companies = await client.model(ResPartner).filter(
    starts_with_acme | starts_with_global
).all()
```

#### `endswith(value)`

Create an ends-with condition.

**Parameters:**

- `value` (str): Suffix to match

**Returns:** `EndsWith` - Ends-with expression

**Example:**

```python
name_field = Field("name")

# Ends with suffix
ends_with_corp = name_field.endswith("Corp")
ends_with_inc = name_field.endswith("Inc")

# Use in queries
companies = await client.model(ResPartner).filter(
    ends_with_corp | ends_with_inc
).all()
```

### List Operations

#### `in_(values)`

Create an IN condition (value in list).

**Parameters:**

- `values` (List[Any]): List of values to match

**Returns:** `In` - IN expression

**Example:**

```python
id_field = Field("id")
country_code_field = Field("country_id.code")

# IN conditions
specific_ids = id_field.in_([1, 2, 3, 4, 5])
us_ca_partners = country_code_field.in_(["US", "CA"])

# Use in queries
partners = await client.model(ResPartner).filter(
    specific_ids & us_ca_partners
).all()
```

#### `not_in(values)`

Create a NOT IN condition (value not in list).

**Parameters:**

- `values` (List[Any]): List of values to exclude

**Returns:** `NotIn` - NOT IN expression

**Example:**

```python
name_field = Field("name")
state_field = Field("state")

# NOT IN conditions
not_test_names = name_field.not_in(["Test Company", "Demo Company"])
not_draft_cancelled = state_field.not_in(["draft", "cancel"])

# Use in queries
valid_partners = await client.model(ResPartner).filter(
    not_test_names & not_draft_cancelled
).all()
```

### Null Checks

#### `is_null()`

Create an IS NULL condition.

**Returns:** `Equal` - IS NULL expression (uses False value)

**Example:**

```python
parent_field = Field("parent_id")
email_field = Field("email")

# Null checks
no_parent = parent_field.is_null()
no_email = email_field.is_null()

# Use in queries
top_level_partners = await client.model(ResPartner).filter(
    no_parent
).all()
```

#### `is_not_null()`

Create an IS NOT NULL condition.

**Returns:** `NotEqual` - IS NOT NULL expression (uses False value)

**Example:**

```python
email_field = Field("email")
phone_field = Field("phone")

# Not null checks
has_email = email_field.is_not_null()
has_phone = phone_field.is_not_null()

# Use in queries
contactable_partners = await client.model(ResPartner).filter(
    has_email | has_phone
).all()
```

## Comparison Expressions

Base classes for all comparison operations.

### ComparisonExpression

Base class for comparison expressions.

```python
class ComparisonExpression(Expression):
    """Base class for comparison expressions."""
    
    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator
        self.value = value
    
    def to_domain(self) -> List[Tuple[str, str, Any]]:
        """Convert to domain tuple."""
        return [(self.field, self.operator, self.value)]
```

### Specific Comparison Classes

#### `Equal`

Equality expression (=).

```python
class Equal(ComparisonExpression):
    """Equality expression (=)."""
    
    def __init__(self, field: str, value: Any):
        super().__init__(field, "=", value)
```

#### `NotEqual`

Not equal expression (!=).

```python
class NotEqual(ComparisonExpression):
    """Not equal expression (!=)."""
    
    def __init__(self, field: str, value: Any):
        super().__init__(field, "!=", value)
```

#### `GreaterThan`, `GreaterEqual`, `LessThan`, `LessEqual`

Numeric comparison expressions.

```python
class GreaterThan(ComparisonExpression):
    """Greater than expression (>)."""

class GreaterEqual(ComparisonExpression):
    """Greater than or equal expression (>=)."""

class LessThan(ComparisonExpression):
    """Less than expression (<)."""

class LessEqual(ComparisonExpression):
    """Less than or equal expression (<=)."""
```

#### `Like`, `ILike`

Pattern matching expressions.

```python
class Like(ComparisonExpression):
    """LIKE expression (case-sensitive pattern matching)."""

class ILike(ComparisonExpression):
    """ILIKE expression (case-insensitive pattern matching)."""
```

#### `In`, `NotIn`

List membership expressions.

```python
class In(ComparisonExpression):
    """IN expression (value in list)."""

class NotIn(ComparisonExpression):
    """NOT IN expression (value not in list)."""
```

#### `Contains`, `StartsWith`, `EndsWith`

String pattern expressions (automatically convert to ILIKE patterns).

```python
class Contains(ComparisonExpression):
    """Contains expression (field contains substring)."""
    
    def __init__(self, field: str, value: str):
        # Convert to ILIKE pattern
        pattern = f"%{value}%"
        super().__init__(field, "ilike", pattern)

class StartsWith(ComparisonExpression):
    """Starts with expression (field starts with substring)."""
    
    def __init__(self, field: str, value: str):
        # Convert to ILIKE pattern
        pattern = f"{value}%"
        super().__init__(field, "ilike", pattern)

class EndsWith(ComparisonExpression):
    """Ends with expression (field ends with substring)."""
    
    def __init__(self, field: str, value: str):
        # Convert to ILIKE pattern
        pattern = f"%{value}"
        super().__init__(field, "ilike", pattern)
```

## Logical Expressions

Combine multiple expressions with logical operators.

### LogicalExpression

Base class for logical expressions.

```python
class LogicalExpression(Expression):
    """Base class for logical expressions."""
    
    def __init__(self, *expressions: Expression):
        self.expressions = expressions
```

### AndExpression

AND expression combining multiple conditions.

```python
class AndExpression(LogicalExpression):
    """AND expression combining multiple conditions."""
    
    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert to domain with AND logic."""
        domain = []
        for expr in self.expressions:
            expr_domain = expr.to_domain()
            domain.extend(expr_domain)
        return domain
```

**Example:**

```python
from zenoo_rpc.query.expressions import Field, AndExpression

name_field = Field("name")
active_field = Field("active")
rank_field = Field("customer_rank")

# Create individual conditions
name_condition = name_field.contains("Corp")
active_condition = active_field == True
rank_condition = rank_field > 0

# Combine with AND
and_expr = AndExpression(name_condition, active_condition, rank_condition)

# Use in query
partners = await client.model(ResPartner).filter(and_expr).all()

# Or use & operator
combined = name_condition & active_condition & rank_condition
```

### OrExpression

OR expression combining multiple conditions.

```python
class OrExpression(LogicalExpression):
    """OR expression combining multiple conditions."""
    
    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert to domain with OR logic."""
        if len(self.expressions) <= 1:
            return self.expressions[0].to_domain() if self.expressions else []

        domain = ["|"]  # OR operator
        for expr in self.expressions:
            expr_domain = expr.to_domain()
            domain.extend(expr_domain)
        return domain
```

**Example:**

```python
from zenoo_rpc.query.expressions import Field, OrExpression

name_field = Field("name")
email_field = Field("email")

# Create search conditions
name_search = name_field.contains("acme")
email_search = email_field.contains("acme")

# Combine with OR
or_expr = OrExpression(name_search, email_search)

# Use in query
partners = await client.model(ResPartner).filter(or_expr).all()

# Or use | operator
search_expr = name_search | email_search
```

### NotExpression

NOT expression negating a condition.

```python
class NotExpression(Expression):
    """NOT expression negating a condition."""
    
    def __init__(self, expression: Expression):
        self.expression = expression
    
    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert to domain with NOT logic."""
        expr_domain = self.expression.to_domain()
        return ["!"] + expr_domain  # NOT operator
```

**Example:**

```python
from zenoo_rpc.query.expressions import Field, NotExpression

active_field = Field("active")
name_field = Field("name")

# Create condition to negate
inactive_condition = active_field == False
test_name_condition = name_field.startswith("Test")

# Negate conditions
not_inactive = NotExpression(inactive_condition)
not_test = NotExpression(test_name_condition)

# Use in query
partners = await client.model(ResPartner).filter(
    not_inactive & not_test
).all()

# Or use ~ operator
active_partners = ~inactive_condition
non_test_partners = ~test_name_condition
```

## Expression Operators

All expressions support logical operators for easy combination.

### `__and__` (& operator)

Combine expressions with AND.

```python
def __and__(self, other: Expression) -> AndExpression:
    """Combine expressions with AND operator."""
    return AndExpression(self, other)
```

### `__or__` (| operator)

Combine expressions with OR.

```python
def __or__(self, other: Expression) -> OrExpression:
    """Combine expressions with OR operator."""
    return OrExpression(self, other)
```

### `__invert__` (~ operator)

Negate expression with NOT.

```python
def __invert__(self) -> NotExpression:
    """Negate the expression with NOT operator."""
    return NotExpression(self)
```

## Advanced Usage Patterns

### Complex Query Building

```python
from zenoo_rpc.query.expressions import Field

# Define fields
name = Field("name")
email = Field("email")
active = Field("active")
rank = Field("customer_rank")
country = Field("country_id.code")

# Build complex query
complex_query = (
    # Search in name or email
    (name.contains("acme") | email.contains("acme")) &
    # Must be active
    active == True &
    # Must be customer
    rank > 0 &
    # In specific countries
    country.in_(["US", "CA", "GB"]) &
    # Not test companies
    ~name.startswith("Test")
)

# Use in query
partners = await client.model(ResPartner).filter(complex_query).all()
```

### Dynamic Expression Building

```python
def build_search_expression(search_fields: List[str], search_term: str) -> Expression:
    """Build dynamic search expression across multiple fields."""
    if not search_fields or not search_term:
        return Field("id") > 0  # Always true condition
    
    # Create search conditions for each field
    conditions = []
    for field_name in search_fields:
        field = Field(field_name)
        condition = field.contains(search_term)
        conditions.append(condition)
    
    # Combine with OR
    if len(conditions) == 1:
        return conditions[0]
    else:
        result = conditions[0]
        for condition in conditions[1:]:
            result = result | condition
        return result

# Usage
search_expr = build_search_expression(
    ["name", "email", "phone", "ref"],
    "acme"
)

partners = await client.model(ResPartner).filter(search_expr).all()
```

### Range Queries

```python
def create_date_range(field_name: str, start_date: str, end_date: str) -> Expression:
    """Create date range expression."""
    field = Field(field_name)
    return (field >= start_date) & (field <= end_date)

def create_numeric_range(field_name: str, min_val: float, max_val: float) -> Expression:
    """Create numeric range expression."""
    field = Field(field_name)
    return (field >= min_val) & (field <= max_val)

# Usage
date_range = create_date_range("create_date", "2023-01-01", "2023-12-31")
rank_range = create_numeric_range("customer_rank", 1, 5)

partners = await client.model(ResPartner).filter(
    date_range & rank_range
).all()
```

## Best Practices

### 1. Use Field Objects for Reusability

```python
# ✅ Good: Define field objects once
name_field = Field("name")
email_field = Field("email")
active_field = Field("active")

# Reuse in multiple expressions
search_expr = name_field.contains("acme") | email_field.contains("acme")
active_expr = active_field == True

# ❌ Avoid: Creating fields repeatedly
search_expr = Field("name").contains("acme") | Field("email").contains("acme")
```

### 2. Use Appropriate Comparison Methods

```python
# ✅ Good: Use specific methods for clarity
name_field.startswith("ACME")  # Clear intent
rank_field >= 1                # Natural operator

# ❌ Avoid: Generic patterns when specific methods exist
name_field.like("ACME%")       # Less clear than startswith
```

### 3. Group Related Conditions

```python
# ✅ Good: Group logically related conditions
customer_conditions = (rank_field > 0) & (active_field == True)
location_conditions = country_field.in_(["US", "CA"])
search_conditions = name_field.contains("corp") | email_field.contains("corp")

final_query = customer_conditions & location_conditions & search_conditions

# ❌ Avoid: Flat, unstructured conditions
```

## Next Steps

- Learn about [Query Filters](filters.md) for Q objects and Django-like syntax
- Explore [Query Builder](../builder.md) for fluent query construction
- Check [Query Optimization](../performance/queries.md) for performance tuning
