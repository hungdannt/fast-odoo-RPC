# 🏗️ AI Model Generation Guide

Automatically generate typed Python models from Odoo schemas with AI assistance!

## 🎯 Overview

Zenoo RPC's AI Model Generation provides:
- **Automatic Pydantic model generation** from Odoo model schemas
- **Proper type hints** for all fields including relationships
- **Field validation** with descriptions and constraints
- **Clean, production-ready code** following Python best practices

## 🚀 Basic Usage

### Simple Model Generation

```python
import asyncio
from zenoo_rpc import ZenooClient

async def basic_model_generation():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        await client.setup_ai(provider="gemini", api_key="your-key")
        
        # Generate model for res.partner
        model_code = await client.ai.generate_model("res.partner")
        
        # Save to file
        with open("models/partner.py", "w") as f:
            f.write(model_code)
        
        print("✅ Partner model generated successfully!")
        print(f"Generated {len(model_code)} characters of code")

asyncio.run(basic_model_generation())
```

### Generated Model Example

```python
# Example output for res.partner
from typing import Optional, List, ClassVar
from datetime import date, datetime
from pydantic import BaseModel, Field

class ResPartner(BaseModel):
    """Contact/Partner model for managing customers, suppliers, and contacts."""
    
    _name: ClassVar[str] = "res.partner"
    
    # Basic Information
    name: str = Field(..., description="Contact Name")
    display_name: Optional[str] = Field(None, description="Display Name")
    email: Optional[str] = Field(None, description="Email Address")
    phone: Optional[str] = Field(None, description="Phone Number")
    mobile: Optional[str] = Field(None, description="Mobile Number")
    
    # Company Information
    is_company: Optional[bool] = Field(False, description="Is a Company")
    company_type: Optional[str] = Field("person", description="Company Type")
    
    # Address Information
    street: Optional[str] = Field(None, description="Street Address")
    street2: Optional[str] = Field(None, description="Street Address 2")
    city: Optional[str] = Field(None, description="City")
    zip: Optional[str] = Field(None, description="ZIP Code")
    
    # Relationships
    country_id: Optional[int] = Field(None, description="Country")
    state_id: Optional[int] = Field(None, description="State")
    parent_id: Optional[int] = Field(None, description="Related Company")
    
    # Business Information
    customer_rank: Optional[int] = Field(0, description="Customer Rank")
    supplier_rank: Optional[int] = Field(0, description="Supplier Rank")
    
    # System Fields
    active: Optional[bool] = Field(True, description="Active")
    create_date: Optional[datetime] = Field(None, description="Created On")
    write_date: Optional[datetime] = Field(None, description="Last Updated")
```

## 🎨 Generation Options

### Include Relationships

```python
async def generate_with_relationships():
    # Include relationship fields
    model_code = await client.ai.generate_model(
        "res.partner",
        include_relationships=True
    )
    
    # Generated code will include Many2one, One2many, Many2many fields
    # with proper type hints and foreign key references
```

### Include Computed Fields

```python
async def generate_with_computed():
    # Include computed/function fields
    model_code = await client.ai.generate_model(
        "res.partner",
        include_computed_fields=True
    )
    
    # Generated code will include computed fields like display_name
    # with appropriate Optional typing
```

### Full Generation

```python
async def generate_complete_model():
    # Generate complete model with all features
    model_code = await client.ai.generate_model(
        "res.partner",
        include_relationships=True,
        include_computed_fields=True
    )
    
    print("Generated complete model with all fields and relationships")
```

## 🏭 Batch Model Generation

### Generate Multiple Models

```python
async def batch_generation():
    models_to_generate = [
        "res.partner",
        "res.users", 
        "product.product",
        "sale.order",
        "account.invoice"
    ]
    
    for model_name in models_to_generate:
        print(f"Generating {model_name}...")
        
        model_code = await client.ai.generate_model(model_name)
        
        # Create filename from model name
        filename = model_name.replace(".", "_") + ".py"
        filepath = f"models/{filename}"
        
        with open(filepath, "w") as f:
            f.write(model_code)
        
        print(f"✅ {model_name} → {filepath}")
    
    print("🎉 Batch generation completed!")
```

### Generate Model Package

```python
async def generate_model_package():
    """Generate a complete Python package with all models."""
    
    import os
    
    # Create models directory
    os.makedirs("generated_models", exist_ok=True)
    
    # Core models to generate
    core_models = [
        "res.partner", "res.users", "res.company",
        "product.product", "product.category", "product.template",
        "sale.order", "sale.order.line",
        "purchase.order", "purchase.order.line",
        "account.move", "account.move.line",
        "stock.picking", "stock.move"
    ]
    
    # Generate __init__.py
    init_content = '"""Generated Odoo Models Package"""\n\n'
    
    for model_name in core_models:
        print(f"Generating {model_name}...")
        
        try:
            model_code = await client.ai.generate_model(
                model_name,
                include_relationships=True
            )
            
            # Create filename
            class_name = "".join(word.capitalize() for word in model_name.split("."))
            filename = model_name.replace(".", "_") + ".py"
            
            # Save model file
            with open(f"generated_models/{filename}", "w") as f:
                f.write(model_code)
            
            # Add to __init__.py
            init_content += f"from .{filename[:-3]} import {class_name}\n"
            
            print(f"✅ Generated {class_name}")
            
        except Exception as e:
            print(f"❌ Failed to generate {model_name}: {e}")
    
    # Save __init__.py
    with open("generated_models/__init__.py", "w") as f:
        f.write(init_content)
    
    print("🎉 Model package generated successfully!")
```

## 🔧 Advanced Features

### Custom Field Types

The AI automatically maps Odoo field types to Python types:

```python
# Odoo Field Type → Python Type
# char, text → str
# integer → int
# float, monetary → float
# boolean → bool
# date → date
# datetime → datetime
# selection → str (with enum options in description)
# many2one → int (foreign key)
# one2many, many2many → List[int]
# binary → bytes
# html → str
```

### Validation Rules

```python
# Generated models include validation where appropriate
class ProductProduct(BaseModel):
    name: str = Field(..., min_length=1, description="Product Name")
    list_price: float = Field(0.0, ge=0, description="Sales Price")
    weight: Optional[float] = Field(None, ge=0, description="Weight")
    active: bool = Field(True, description="Active")
    
    # Custom validation
    @validator('list_price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return v
```

### Relationship Handling

```python
# One2many and Many2many relationships
class SaleOrder(BaseModel):
    _name: ClassVar[str] = "sale.order"
    
    # Many2one (foreign key)
    partner_id: int = Field(..., description="Customer")
    
    # One2many (reverse foreign key)
    order_line: List[int] = Field(default_factory=list, description="Order Lines")
    
    # Many2many (junction table)
    tag_ids: List[int] = Field(default_factory=list, description="Tags")
```

## 📊 Model Examples by Domain

### CRM Models

```python
async def generate_crm_models():
    crm_models = [
        "crm.lead",           # Leads and opportunities
        "crm.stage",          # Sales stages
        "crm.team",           # Sales teams
        "crm.activity.type",  # Activity types
    ]
    
    for model in crm_models:
        code = await client.ai.generate_model(model)
        # Save and use...
```

### Inventory Models

```python
async def generate_inventory_models():
    inventory_models = [
        "stock.location",     # Storage locations
        "stock.warehouse",    # Warehouses
        "stock.picking.type", # Operation types
        "stock.quant",        # Stock quantities
    ]
    
    for model in inventory_models:
        code = await client.ai.generate_model(model, include_relationships=True)
        # Save and use...
```

### Accounting Models

```python
async def generate_accounting_models():
    accounting_models = [
        "account.account",    # Chart of accounts
        "account.journal",    # Journals
        "account.payment",    # Payments
        "account.tax",        # Taxes
    ]
    
    for model in accounting_models:
        code = await client.ai.generate_model(model)
        # Save and use...
```

## 🎯 Using Generated Models

### Data Validation

```python
from generated_models.res_partner import ResPartner

# Validate data before sending to Odoo
partner_data = {
    "name": "ACME Corp",
    "email": "contact@acme.com",
    "is_company": True,
    "customer_rank": 1
}

try:
    # Validate using Pydantic model
    partner = ResPartner(**partner_data)
    
    # Convert to dict for Odoo
    validated_data = partner.dict(exclude_unset=True)
    
    # Create in Odoo
    partner_id = await client.create("res.partner", validated_data)
    print(f"✅ Created partner: {partner_id}")
    
except ValidationError as e:
    print(f"❌ Validation failed: {e}")
```

### Type-Safe Operations

```python
from typing import List
from generated_models.sale_order import SaleOrder

async def create_typed_order(order_data: dict) -> int:
    """Create sale order with type validation."""
    
    # Validate data structure
    order = SaleOrder(**order_data)
    
    # Type-safe field access
    customer_id: int = order.partner_id
    order_lines: List[int] = order.order_line
    
    # Create in Odoo
    return await client.create("sale.order", order.dict(exclude_unset=True))
```

### IDE Support

```python
# Generated models provide excellent IDE support
from generated_models.product_product import ProductProduct

def process_product(product: ProductProduct):
    # IDE provides autocomplete and type checking
    name: str = product.name
    price: float = product.list_price
    is_active: bool = product.active
    
    # Type errors caught at development time
    # product.list_price = "invalid"  # IDE error!
```

## 🛠️ Best Practices

### 1. Organize Generated Models

```python
# Recommended directory structure
models/
├── __init__.py
├── base/
│   ├── res_partner.py
│   ├── res_users.py
│   └── res_company.py
├── sales/
│   ├── sale_order.py
│   └── crm_lead.py
├── inventory/
│   ├── product_product.py
│   └── stock_picking.py
└── accounting/
    ├── account_move.py
    └── account_payment.py
```

### 2. Version Control

```python
# Add generation metadata
async def generate_with_metadata():
    model_code = await client.ai.generate_model("res.partner")
    
    # Add header with generation info
    header = f'''"""
Generated by Zenoo RPC AI Model Generator
Model: res.partner
Generated: {datetime.now().isoformat()}
Odoo Version: {await client.get_server_version()}
"""

'''
    
    full_code = header + model_code
    
    with open("models/res_partner.py", "w") as f:
        f.write(full_code)
```

### 3. Custom Extensions

```python
# Extend generated models with custom logic
from generated_models.res_partner import ResPartner as BasePartner

class ResPartner(BasePartner):
    """Extended partner model with custom methods."""
    
    def is_customer(self) -> bool:
        """Check if partner is a customer."""
        return self.customer_rank > 0
    
    def is_supplier(self) -> bool:
        """Check if partner is a supplier."""
        return self.supplier_rank > 0
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.street, self.street2, self.city, self.zip]
        return ", ".join(filter(None, parts))
```

## 🚨 Troubleshooting

### Model Generation Fails

```python
async def robust_generation():
    try:
        model_code = await client.ai.generate_model("custom.model")
    except Exception as e:
        # Get AI help with the error
        diagnosis = await client.ai.diagnose(e, {
            "operation": "model_generation",
            "model": "custom.model"
        })
        
        print(f"Generation failed: {diagnosis['problem']}")
        print(f"Solution: {diagnosis['solution']}")
```

### Field Type Issues

```python
# Handle unknown field types
async def handle_custom_fields():
    try:
        model_code = await client.ai.generate_model("custom.model")
    except Exception as e:
        if "unknown field type" in str(e):
            print("Model has custom field types")
            print("Consider manual review of generated code")
```

## 🎯 Next Steps

- **[AI Chat Assistant](./ai-chat-assistant.md)** - Get help with generated models
- **[Error Diagnosis](./error-diagnosis.md)** - Debug model issues
- **[Performance Optimization](./performance-optimization.md)** - Optimize model usage
- **[Advanced AI Features](./advanced-ai-features.md)** - Explore advanced capabilities

---

**💡 Pro Tip**: Generated models are starting points! Review and customize them for your specific needs. The AI provides a solid foundation with proper types and validation.
