# Models & Type Safety

Zenoo RPC provides type-safe Pydantic models for Odoo records, giving you IDE support, runtime validation, and a better development experience.

## Overview

Instead of working with raw dictionaries like in odoorpc, Zenoo RPC uses Pydantic models that provide:

- **Type Safety**: Full type hints and validation
- **IDE Support**: Autocomplete and error detection
- **Runtime Validation**: Automatic data validation
- **Documentation**: Self-documenting code
- **Serialization**: Easy conversion to/from JSON

## Built-in Models

Zenoo RPC includes pre-defined models for common Odoo objects:

```python
from zenoo_rpc.models.common import (
    ResPartner,          # res.partner
    ResCountry,          # res.country
    ResCountryState,     # res.country.state
    ResCurrency,         # res.currency
    ResUsers,            # res.users
    ResGroups,           # res.groups
    ProductProduct,      # product.product
    ProductCategory,     # product.category
    SaleOrder,           # sale.order
    SaleOrderLine,       # sale.order.line
)
```

## Using Models

### Basic Model Usage

```python
from zenoo_rpc.models.common import ResPartner

async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    
    # Get typed results
    partners = await client.model(ResPartner).filter(
        is_company=True
    ).limit(5).all()
    
    # Type-safe field access
    for partner in partners:
        print(f"Name: {partner.name}")           # str
        print(f"Email: {partner.email}")         # Optional[str]
        print(f"Is Company: {partner.is_company}") # bool
        print(f"ID: {partner.id}")               # int
```

### Field Types and Validation

```python
# ResPartner model fields (examples)
class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    # Basic fields
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_company: bool = False
    active: bool = True
    
    # Date fields
    create_date: Optional[datetime] = None
    write_date: Optional[datetime] = None
    
    # Numeric fields
    customer_rank: int = 0
    supplier_rank: int = 0
    
    # Selection fields
    lang: Optional[str] = None
    
    # Relationship fields
    country_id: Optional[Many2OneField[ResCountry]] = None
    state_id: Optional[Many2OneField[ResCountryState]] = None
    child_ids: One2ManyField[List[ResPartner]] = []
    category_id: Many2ManyField[List[ResPartnerCategory]] = []
```

## Field Types

### Basic Field Types

```python
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

class ExampleModel(OdooModel):
    # Text fields
    name: str                           # Required string
    description: Optional[str] = None   # Optional string
    
    # Numeric fields
    sequence: int = 0                   # Integer with default
    price: float = 0.0                  # Float
    amount: Decimal = Decimal('0.00')   # Decimal for precision
    
    # Boolean fields
    active: bool = True                 # Boolean with default
    
    # Date/Time fields
    date_field: Optional[date] = None
    datetime_field: Optional[datetime] = None
    
    # Selection fields (using Literal)
    state: Literal['draft', 'confirmed', 'done'] = 'draft'
```

### Relationship Fields

```python
from zenoo_rpc.models.fields import Many2OneField, One2ManyField, Many2ManyField

class ResPartner(OdooModel):
    # Many2One - Single related record
    country_id: Optional[Many2OneField[ResCountry]] = None
    parent_id: Optional[Many2OneField["ResPartner"]] = None  # Self-reference
    
    # One2Many - List of related records
    child_ids: One2ManyField[List["ResPartner"]] = []
    invoice_ids: One2ManyField[List[AccountMove]] = []
    
    # Many2Many - List of related records
    category_id: Many2ManyField[List[ResPartnerCategory]] = []
    user_ids: Many2ManyField[List[ResUsers]] = []
```

## Working with Relationships

### Many2One Fields

```python
# Access Many2One relationships
partner = await client.model(ResPartner).get(1)

# Check if relationship exists
if partner.country_id:
    # Lazy loading - loads when accessed
    country = await partner.country_id
    print(f"Country: {country.name}")
    print(f"Country Code: {country.code}")

# Direct access to ID without loading
if partner.country_id:
    country_id = partner.country_id.id
    print(f"Country ID: {country_id}")
```

### One2Many Fields

```python
# Access One2Many relationships
partner = await client.model(ResPartner).get(1)

# Get all children
children = await partner.child_ids.all()
for child in children:
    print(f"Child: {child.name}")

# Filter children
active_children = await partner.child_ids.filter(active=True).all()

# Count children
child_count = await partner.child_ids.count()
```

### Many2Many Fields

```python
# Access Many2Many relationships
partner = await client.model(ResPartner).get(1)

# Get all categories
categories = await partner.category_id.all()
for category in categories:
    print(f"Category: {category.name}")

# Add categories
await partner.category_id.add([category1.id, category2.id])

# Remove categories
await partner.category_id.remove([category1.id])

# Set categories (replace all)
await partner.category_id.set([category1.id, category2.id])
```

## Creating Custom Models

### Basic Custom Model

```python
from zenoo_rpc.models.base import OdooModel
from typing import ClassVar, Optional

class CustomModel(OdooModel):
    _odoo_name: ClassVar[str] = "custom.model"
    
    # Define fields
    name: str
    description: Optional[str] = None
    active: bool = True
    
    # Custom methods
    def display_name(self) -> str:
        return f"{self.name} ({'Active' if self.active else 'Inactive'})"

# Register the model
from zenoo_rpc.models.registry import register_model
register_model(CustomModel)

# Use the model
async with ZenooClient("localhost", port=8069) as client:
    await client.login("demo", "admin", "admin")
    
    records = await client.model(CustomModel).all()
    for record in records:
        print(record.display_name())
```

### Advanced Custom Model

```python
from pydantic import Field, validator
from datetime import datetime

class ProjectTask(OdooModel):
    _odoo_name: ClassVar[str] = "project.task"
    
    # Basic fields
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    
    # Dates
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    
    # Relationships
    project_id: Optional[Many2OneField[Project]] = None
    user_id: Optional[Many2OneField[ResUsers]] = None
    
    # Computed properties
    @property
    def is_overdue(self) -> bool:
        if not self.date_end:
            return False
        return datetime.now() > self.date_end
    
    # Validators
    @validator('date_end')
    def validate_end_date(cls, v, values):
        if v and values.get('date_start') and v < values['date_start']:
            raise ValueError('End date must be after start date')
        return v
    
    # Custom methods
    async def mark_done(self, client):
        """Mark task as done"""
        return await client.model(ProjectTask).update(self.id, {
            'stage_id': 'done_stage_id'  # Replace with actual stage ID
        })
```

## Model Validation

### Field Validation

```python
from pydantic import validator, Field

class ValidatedModel(OdooModel):
    _odoo_name: ClassVar[str] = "validated.model"
    
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    age: int = Field(..., ge=0, le=150)
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone must contain only digits, +, -, and spaces')
        return v
```

### Model-Level Validation

```python
from pydantic import root_validator

class OrderLine(OdooModel):
    _odoo_name: ClassVar[str] = "sale.order.line"
    
    product_id: Many2OneField[ProductProduct]
    quantity: float = Field(..., gt=0)
    price_unit: float = Field(..., ge=0)
    discount: float = Field(0, ge=0, le=100)
    
    @root_validator
    def validate_order_line(cls, values):
        # Custom business logic validation
        if values.get('discount', 0) > 50 and values.get('quantity', 0) < 10:
            raise ValueError('High discount only allowed for large quantities')
        return values
```

## Serialization and Deserialization

### Converting to/from Dictionaries

```python
# From Odoo data to model
odoo_data = {
    'id': 1,
    'name': 'Test Partner',
    'email': 'test@example.com',
    'is_company': True
}

partner = ResPartner(**odoo_data)

# Model to dictionary
partner_dict = partner.dict()
print(partner_dict)

# Model to dictionary (exclude None values)
partner_dict = partner.dict(exclude_none=True)

# Model to dictionary (only specific fields)
partner_dict = partner.dict(include={'name', 'email'})
```

### JSON Serialization

```python
import json

# Model to JSON
partner_json = partner.json()
print(partner_json)

# JSON to model
partner_from_json = ResPartner.parse_raw(partner_json)

# Pretty JSON
partner_json = partner.json(indent=2, exclude_none=True)
```

## Model Registry

### Registering Models

```python
from zenoo_rpc.models.registry import register_model, get_model_class

# Register custom model
register_model(CustomModel)

# Get model class by name
ModelClass = get_model_class("custom.model")

# Check if model is registered
from zenoo_rpc.models.registry import ModelRegistry
registry = ModelRegistry()
if "custom.model" in registry:
    print("Model is registered")
```

### Dynamic Model Creation

```python
from zenoo_rpc.models.base import create_model_class

# Create model dynamically
DynamicModel = create_model_class(
    "dynamic.model",
    {
        "name": (str, ...),
        "value": (int, 0),
        "active": (bool, True)
    }
)

# Register and use
register_model(DynamicModel)
```

## Best Practices

### 1. Use Type Hints

```python
# ✅ Good - Clear type hints
async def get_companies(client: ZenooClient) -> List[ResPartner]:
    return await client.model(ResPartner).filter(is_company=True).all()

# ❌ Bad - No type hints
async def get_companies(client):
    return await client.model(ResPartner).filter(is_company=True).all()
```

### 2. Handle Optional Fields

```python
# ✅ Good - Check for None
partner = await client.model(ResPartner).get(1)
if partner.email:
    send_email(partner.email)

# ❌ Bad - Might raise AttributeError
send_email(partner.email)  # Could be None
```

### 3. Use Relationship Loading Efficiently

```python
# ✅ Good - Load related data when needed
partners = await client.model(ResPartner).filter(is_company=True).all()
for partner in partners:
    if partner.country_id:
        country = await partner.country_id
        print(f"{partner.name} - {country.name}")

# ✅ Better - Prefetch related data
partners = await client.model(ResPartner).filter(
    is_company=True
).prefetch('country_id').all()
```

### 4. Validate Data Early

```python
# ✅ Good - Validate before saving
try:
    partner = ResPartner(
        name="Test Company",
        email="invalid-email"  # Will raise validation error
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Next Steps

- [Query Builder](queries.md) - Learn advanced querying
- [Relationships](relationships.md) - Master relationship handling
- [Caching](caching.md) - Optimize with caching
- [API Reference](../api-reference/models/index.md) - Complete model API
