# Field Types API Reference

Specialized field types for Odoo models with proper validation, serialization, and relationship handling using Pydantic field types that correspond to Odoo field types.

## Overview

Field types provide:

- **Type Safety**: Full type hints and validation
- **Odoo Compatibility**: Direct mapping to Odoo field types
- **Relationship Support**: Lazy loading and relationship descriptors
- **Validation**: Automatic data validation with Pydantic
- **Serialization**: JSON serialization/deserialization

## Relationship Fields

### Many2OneField

Creates a many-to-one relationship field for single record references.

```python
def Many2OneField(
    model_name: str, 
    description: str = "", 
    **kwargs: Any
) -> FieldInfo:
    """Create a Many2one field for Odoo relationships."""
```

**Parameters:**

- `model_name` (str): Target Odoo model name (e.g., "res.partner")
- `description` (str): Field description
- `**kwargs`: Additional field parameters

**Returns:** `FieldInfo` configured for Many2one relationships

**Example:**

```python
from zenoo_rpc.models.fields import Many2OneField
from typing import Optional, Union

class SaleOrder(OdooModel):
    _odoo_name: ClassVar[str] = "sale.order"
    
    # Many2one relationship to partner
    partner_id: Optional[Union[int, "ResPartner"]] = Many2OneField(
        "res.partner",
        description="Customer"
    )
    
    # Many2one with additional constraints
    company_id: Optional[Union[int, "ResCompany"]] = Many2OneField(
        "res.company",
        description="Company",
        required=True
    )
    
    # Access relationship
    async def get_customer(self) -> Optional["ResPartner"]:
        """Get the customer partner."""
        return await self.partner_id
```

### One2ManyField

Creates a one-to-many relationship field for collections of related records.

```python
def One2ManyField(
    model_name: str, 
    inverse_field: str, 
    description: str = "", 
    **kwargs: Any
) -> FieldInfo:
    """Create a One2many field for Odoo relationships."""
```

**Parameters:**

- `model_name` (str): Target Odoo model name
- `inverse_field` (str): Field name in target model that points back
- `description` (str): Field description
- `**kwargs`: Additional field parameters

**Example:**

```python
from zenoo_rpc.models.fields import One2ManyField
from typing import List

class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    # One2many relationship to child partners
    child_ids: List["ResPartner"] = One2ManyField(
        "res.partner",
        "parent_id",
        description="Child companies"
    )
    
    # One2many to orders
    sale_order_ids: List["SaleOrder"] = One2ManyField(
        "sale.order",
        "partner_id",
        description="Sales orders"
    )
    
    # Access related records
    async def get_children(self) -> List["ResPartner"]:
        """Get all child partners."""
        return await self.child_ids
    
    async def get_orders(self) -> List["SaleOrder"]:
        """Get all sales orders."""
        return await self.sale_order_ids
```

### Many2ManyField

Creates a many-to-many relationship field for multiple record references.

```python
def Many2ManyField(
    model_name: str,
    relation_table: Optional[str] = None,
    description: str = "",
    **kwargs: Any,
) -> FieldInfo:
    """Create a Many2many field for Odoo relationships."""
```

**Parameters:**

- `model_name` (str): Target Odoo model name
- `relation_table` (str, optional): Relation table name
- `description` (str): Field description
- `**kwargs`: Additional field parameters

**Example:**

```python
from zenoo_rpc.models.fields import Many2ManyField
from typing import List

class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    # Many2many relationship to categories
    category_id: List["ResPartnerCategory"] = Many2ManyField(
        "res.partner.category",
        description="Partner categories"
    )
    
    # Many2many with custom relation table
    tag_ids: List["ResPartnerTag"] = Many2ManyField(
        "res.partner.tag",
        relation_table="partner_tag_rel",
        description="Partner tags"
    )
    
    # Access related records
    async def get_categories(self) -> List["ResPartnerCategory"]:
        """Get all partner categories."""
        return await self.category_id
    
    async def add_category(self, category_id: int):
        """Add a category to this partner."""
        current_categories = await self.category_id
        if category_id not in [cat.id for cat in current_categories]:
            # Update through client
            await self._client.write(
                "res.partner", 
                [self.id], 
                {"category_id": [(4, category_id)]}
            )
```

## Basic Field Types

### CharField

Short text field with optional length constraint.

```python
def CharField(
    max_length: Optional[int] = None, 
    description: str = "", 
    **kwargs: Any
) -> FieldInfo:
    """Create a Char field for short text content."""
```

**Example:**

```python
from zenoo_rpc.models.fields import CharField

class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    # Basic char field
    name: str = CharField(description="Partner name")
    
    # Char field with length constraint
    ref: Optional[str] = CharField(
        max_length=50,
        description="Internal reference"
    )
    
    # Email field (special char field)
    email: Optional[str] = CharField(
        max_length=254,
        description="Email address"
    )

    # Phone field
    phone: Optional[str] = CharField(
        max_length=32,
        description="Phone number"
    )
```

### TextField

Long text field for multi-line content.

```python
def TextField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Text field for long text content."""
```

**Example:**

```python
from zenoo_rpc.models.fields import TextField

class ProductTemplate(OdooModel):
    _odoo_name: ClassVar[str] = "product.template"
    
    # Long text field
    description: Optional[str] = TextField(
        description="Product description"
    )
    
    # Notes field
    note: Optional[str] = TextField(
        description="Internal notes"
    )
```

### BooleanField

Boolean field for true/false values.

```python
def BooleanField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Boolean field."""
```

**Example:**

```python
from zenoo_rpc.models.fields import BooleanField

class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    # Boolean fields
    active: bool = BooleanField(description="Is record active")
    is_company: bool = BooleanField(description="Is a company")
    customer_rank: int = IntegerField(description="Customer rank")
    
    # Computed property using boolean field
    @property
    def is_customer(self) -> bool:
        """Check if partner is a customer."""
        return self.customer_rank > 0
```

### IntegerField

Integer field for whole numbers.

```python
def IntegerField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create an Integer field."""
```

**Example:**

```python
from zenoo_rpc.models.fields import IntegerField

class ProductTemplate(OdooModel):
    _odoo_name: ClassVar[str] = "product.template"
    
    # Integer fields
    sequence: int = IntegerField(description="Display sequence")
    sale_delay: int = IntegerField(description="Customer lead time")
    
    # Ranking fields
    customer_rank: int = IntegerField(description="Customer rank")
    supplier_rank: int = IntegerField(description="Vendor rank")
```

### FloatField

Float field with optional precision control.

```python
def FloatField(
    digits: Optional[Tuple[int, int]] = None, 
    description: str = "", 
    **kwargs: Any
) -> FieldInfo:
    """Create a Float field with precision control."""
```

**Parameters:**

- `digits` (Tuple[int, int], optional): (precision, scale) for decimal places

**Example:**

```python
from zenoo_rpc.models.fields import FloatField

class ProductTemplate(OdooModel):
    _odoo_name: ClassVar[str] = "product.template"
    
    # Basic float field
    list_price: float = FloatField(description="Sales price")
    
    # Float field with precision
    weight: float = FloatField(
        digits=(16, 3),
        description="Product weight in kg"
    )
    
    # Volume with high precision
    volume: float = FloatField(
        digits=(16, 6),
        description="Product volume in m³"
    )
```

## Specialized Field Types

### SelectionField

Selection field for predefined choices.

```python
def SelectionField(
    choices: List[Tuple[str, str]], 
    description: str = "", 
    **kwargs: Any
) -> FieldInfo:
    """Create a Selection field for Odoo choice fields."""
```

**Parameters:**

- `choices` (List[Tuple[str, str]]): List of (value, label) tuples

**Example:**

```python
from zenoo_rpc.models.fields import SelectionField

class SaleOrder(OdooModel):
    _odoo_name: ClassVar[str] = "sale.order"
    
    # Selection field with choices
    state: str = SelectionField([
        ("draft", "Quotation"),
        ("sent", "Quotation Sent"),
        ("sale", "Sales Order"),
        ("done", "Locked"),
        ("cancel", "Cancelled")
    ], description="Order status")
    
    # Priority selection
    priority: str = SelectionField([
        ("0", "Normal"),
        ("1", "Low"),
        ("2", "High"),
        ("3", "Very High")
    ], description="Priority")
    
    # Check state
    @property
    def is_confirmed(self) -> bool:
        """Check if order is confirmed."""
        return self.state in ["sale", "done"]
```

### DateField

Date field for date-only values.

```python
def DateField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Date field with proper validation."""
```

**Example:**

```python
from zenoo_rpc.models.fields import DateField
from datetime import date

class SaleOrder(OdooModel):
    _odoo_name: ClassVar[str] = "sale.order"
    
    # Date fields
    date_order: Optional[date] = DateField(description="Order date")
    commitment_date: Optional[date] = DateField(description="Delivery date")
    
    # Computed properties
    @property
    def is_overdue(self) -> bool:
        """Check if order is overdue."""
        if not self.commitment_date:
            return False
        return self.commitment_date < date.today()
```

### DateTimeField

DateTime field for timestamp values.

```python
def DateTimeField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a DateTime field with proper validation."""
```

**Example:**

```python
from zenoo_rpc.models.fields import DateTimeField
from datetime import datetime

class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    # DateTime fields
    create_date: Optional[datetime] = DateTimeField(description="Created on")
    write_date: Optional[datetime] = DateTimeField(description="Last updated")
    
    # Computed properties
    @property
    def age_in_days(self) -> int:
        """Get age in days since creation."""
        if not self.create_date:
            return 0
        return (datetime.now() - self.create_date).days
```

### MonetaryField

Monetary field for currency amounts.

```python
def MonetaryField(
    currency_field: str = "currency_id", 
    description: str = "", 
    **kwargs: Any
) -> FieldInfo:
    """Create a Monetary field for currency amounts."""
```

**Parameters:**

- `currency_field` (str): Name of the currency field (default: "currency_id")

**Example:**

```python
from zenoo_rpc.models.fields import MonetaryField, Many2OneField
from decimal import Decimal

class SaleOrder(OdooModel):
    _odoo_name: ClassVar[str] = "sale.order"
    
    # Currency field
    currency_id: Optional["ResCurrency"] = Many2OneField(
        "res.currency",
        description="Currency"
    )
    
    # Monetary fields
    amount_untaxed: Decimal = MonetaryField(description="Untaxed amount")
    amount_tax: Decimal = MonetaryField(description="Tax amount")
    amount_total: Decimal = MonetaryField(description="Total amount")
    
    # Computed properties
    @property
    def tax_percentage(self) -> float:
        """Calculate tax percentage."""
        if self.amount_untaxed == 0:
            return 0.0
        return float(self.amount_tax / self.amount_untaxed * 100)
```

### BinaryField

Binary field for file/image data.

```python
def BinaryField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Binary field for file/image data."""
```

**Example:**

```python
from zenoo_rpc.models.fields import BinaryField
from typing import Optional

class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    # Image fields
    image_1920: Optional[bytes] = BinaryField(description="Image")
    image_1024: Optional[bytes] = BinaryField(description="Image 1024")
    image_512: Optional[bytes] = BinaryField(description="Image 512")
    
    # Document attachment
    attachment: Optional[bytes] = BinaryField(description="Attachment")
    
    # Helper methods
    def has_image(self) -> bool:
        """Check if partner has an image."""
        return self.image_1920 is not None
    
    def get_image_size(self) -> int:
        """Get image size in bytes."""
        return len(self.image_1920) if self.image_1920 else 0
```

## Field Descriptors

### RelationshipDescriptor

Base descriptor for relationship fields with lazy loading.

```python
class RelationshipDescriptor:
    """Base descriptor for relationship fields with lazy loading."""
    
    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        self.field_name = field_name
        self.comodel_name = comodel_name
        self.field_info = field_info
        self.is_collection = False
```

**Features:**

- Lazy loading of related records
- Caching of loaded relationships
- Automatic relationship resolution

### Many2OneDescriptor

Descriptor for Many2One relationships.

```python
class Many2OneDescriptor(RelationshipDescriptor):
    """Descriptor for Many2One relationships."""
    
    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        super().__init__(field_name, comodel_name, field_info)
        self.is_collection = False
```

### One2ManyDescriptor

Descriptor for One2Many relationships.

```python
class One2ManyDescriptor(RelationshipDescriptor):
    """Descriptor for One2Many relationships."""
    
    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        super().__init__(field_name, comodel_name, field_info)
        self.is_collection = True
```

### Many2ManyDescriptor

Descriptor for Many2Many relationships.

```python
class Many2ManyDescriptor(RelationshipDescriptor):
    """Descriptor for Many2Many relationships."""
    
    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        super().__init__(field_name, comodel_name, field_info)
        self.is_collection = True
```

## Field Validation

### Automatic Validation

Fields automatically validate data using Pydantic validators.

```python
from pydantic import ValidationError

class ResPartner(OdooModel):
    _odoo_name: ClassVar[str] = "res.partner"
    
    name: str = CharField(description="Name")
    email: Optional[str] = CharField(description="Email")
    
    # Custom validator
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

# Usage
try:
    partner = ResPartner(
        name="Test Partner",
        email="invalid-email"  # Will raise ValidationError
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Custom Field Validation

```python
from pydantic import field_validator

class ProductTemplate(OdooModel):
    _odoo_name: ClassVar[str] = "product.template"
    
    list_price: float = FloatField(description="Sales price")
    cost_price: float = FloatField(description="Cost price")
    
    @field_validator('list_price')
    @classmethod
    def validate_list_price(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return v
    
    @field_validator('cost_price')
    @classmethod
    def validate_cost_price(cls, v):
        if v < 0:
            raise ValueError('Cost cannot be negative')
        return v
    
    # Cross-field validation
    def model_post_init(self, __context):
        if self.list_price < self.cost_price:
            raise ValueError('List price cannot be less than cost price')
```

## Field Serialization

### JSON Serialization

Fields automatically handle JSON serialization.

```python
# Model with various field types
partner = ResPartner(
    name="ACME Corp",
    email="contact@acme.com",
    is_company=True,
    create_date=datetime.now(),
    amount_total=Decimal("1000.50")
)

# Serialize to JSON
json_data = partner.model_dump_json()
print(json_data)

# Serialize to dict
dict_data = partner.model_dump()
print(dict_data)

# Create from JSON
partner_from_json = ResPartner.model_validate_json(json_data)

# Create from dict
partner_from_dict = ResPartner.model_validate(dict_data)
```

### Odoo Format Conversion

Convert between Zenoo models and Odoo data format.

```python
# From Odoo data format
odoo_data = {
    "id": 1,
    "name": "ACME Corp",
    "email": "contact@acme.com",
    "is_company": True,
    "country_id": [1, "United States"],  # Odoo many2one format
    "category_id": [1, 2, 3]  # Odoo many2many format
}

# Convert to model using Pydantic validation
partner = ResPartner.model_validate(odoo_data)

# Convert back to dict format
odoo_format = partner.model_dump()
```

## Best Practices

### 1. Use Appropriate Field Types

```python
# ✅ Good: Use specific field types
class Product(OdooModel):
    name: str = CharField(max_length=100)
    price: Decimal = MonetaryField()
    weight: float = FloatField(digits=(16, 3))
    active: bool = BooleanField()

# ❌ Avoid: Generic types without validation
class Product(OdooModel):
    name: str
    price: float  # Should be MonetaryField
    weight: str   # Should be FloatField
    active: int   # Should be BooleanField
```

### 2. Add Field Descriptions

```python
# ✅ Good: Descriptive field definitions
partner_id: Optional["ResPartner"] = Many2OneField(
    "res.partner",
    description="Customer or vendor"
)

# ❌ Avoid: Missing descriptions
partner_id: Optional["ResPartner"] = Many2OneField("res.partner")
```

### 3. Use Type Hints

```python
# ✅ Good: Proper type hints
from typing import Optional, List, Union

class SaleOrder(OdooModel):
    partner_id: Optional[Union[int, "ResPartner"]] = Many2OneField("res.partner")
    line_ids: List["SaleOrderLine"] = One2ManyField("sale.order.line", "order_id")

# ❌ Avoid: Missing type hints
class SaleOrder(OdooModel):
    partner_id = Many2OneField("res.partner")
    line_ids = One2ManyField("sale.order.line", "order_id")
```

## Next Steps

- Learn about [Relationship Management](relationships.md) for advanced relationship handling
- Explore [Model Validation](../validation.md) for custom validation patterns
- Check [Model Serialization](../serialization.md) for data conversion techniques
