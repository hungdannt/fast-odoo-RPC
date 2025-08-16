"""
Common Odoo model definitions.

This module provides pre-defined model classes for common Odoo models
with proper field definitions and type safety.
"""

from typing import List, Optional, Union, ClassVar
from datetime import date, datetime
from decimal import Decimal

from .base import OdooModel
from .fields import (
    CharField,
    TextField,
    BooleanField,
    IntegerField,
    FloatField,
    DateField,
    DateTimeField,
    MonetaryField,
    SelectionField,
    Many2OneField,
    One2ManyField,
    Many2ManyField,
)
from .registry import register_model


@register_model("res.partner")
class ResPartner(OdooModel):
    odoo_name: ClassVar[str] = "res.partner"
    """Partner (Customer/Vendor/Contact) model.
    
    This model represents partners in Odoo, including customers,
    vendors, and contacts with full type safety and relationship handling.
    
    Example:
        >>> # Create a partner
        >>> partner = ResPartner(
        ...     id=1,
        ...     name="ACME Corporation",
        ...     is_company=True,
        ...     email="contact@acme.com"
        ... )
        >>> 
        >>> # Access fields with type safety
        >>> print(partner.name)  # str
        >>> print(partner.is_company)  # bool
    """

    # Basic fields
    name: str
    display_name: Optional[str] = None

    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    website: Optional[str] = None

    # Address fields
    street: Optional[str] = None
    street2: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    state_id: Optional[Union[int, "ResCountryState"]] = Many2OneField(
        "res.country.state", description="State"
    )
    country_id: Optional[Union[int, "ResCountry"]] = Many2OneField(
        "res.country", description="Country"
    )

    # Partner type and status
    is_company: bool = False
    person_type: Optional[str] = None

    # Business fields
    customer_rank: int = 0
    supplier_rank: int = 0

    # Relationships
    parent_id: Optional[Union[int, "ResPartner"]] = Many2OneField(
        "res.partner", description="Parent Company"
    )
    child_ids: Union[List[int], List["ResPartner"]] = One2ManyField(
        "res.partner", "parent_id", description="Child Companies"
    )

    # System fields
    active: bool = True
    create_date: Optional[datetime] = None
    write_date: Optional[datetime] = None

    # Additional info
    comment: Optional[str] = None
    ref: Optional[str] = None

    @property
    def is_customer(self) -> bool:
        """Check if this partner is a customer."""
        return self.customer_rank > 0

    @property
    def is_vendor(self) -> bool:
        """Check if this partner is a vendor."""
        return self.supplier_rank > 0

    @property
    def full_address(self) -> str:
        """Get the full formatted address."""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.street2:
            parts.append(self.street2)
        if self.city:
            parts.append(self.city)
        if self.zip:
            parts.append(self.zip)
        return ", ".join(parts)


@register_model("res.country")
class ResCountry(OdooModel):
    """Country model."""

    name: str = CharField(description="Country Name")
    code: str = CharField(max_length=2, description="Country Code")
    phone_code: Optional[int] = IntegerField(description="Phone Code")
    currency_id: Optional["ResCurrency"] = Many2OneField(
        "res.currency", description="Currency"
    )


@register_model("res.country.state")
class ResCountryState(OdooModel):
    """Country State model."""

    name: str = CharField(description="State Name")
    code: str = CharField(max_length=3, description="State Code")
    country_id: "ResCountry" = Many2OneField("res.country", description="Country")


@register_model("res.currency")
class ResCurrency(OdooModel):
    """Currency model."""

    name: str = CharField(description="Currency")
    symbol: str = CharField(description="Symbol")
    rate: float = FloatField(description="Current Rate")
    active: bool = BooleanField(description="Active")


@register_model("res.users")
class ResUsers(OdooModel):
    """User model."""

    name: str = CharField(description="Name")
    login: str = CharField(description="Login")
    email: Optional[str] = CharField(description="Email")
    active: bool = BooleanField(description="Active")

    # Relationship to partner
    partner_id: "ResPartner" = Many2OneField(
        "res.partner", description="Related Partner"
    )

    # Groups and permissions
    groups_id: List["ResGroups"] = Many2ManyField("res.groups", description="Groups")


@register_model("res.groups")
class ResGroups(OdooModel):
    """User Groups model."""

    name: str = CharField(description="Name")
    category_id: Optional["ResGroupsCategory"] = Many2OneField(
        "ir.module.category", description="Application"
    )
    users: List[ResUsers] = Many2ManyField("res.users", description="Users")


@register_model("ir.module.category")
class ResGroupsCategory(OdooModel):
    """Module Category model."""

    name: str = CharField(description="Name")
    description: Optional[str] = TextField(description="Description")


@register_model("product.product")
class ProductProduct(OdooModel):
    """Product model."""

    name: str = CharField(description="Name")
    default_code: Optional[str] = CharField(description="Internal Reference")
    barcode: Optional[str] = CharField(description="Barcode")

    # Product type
    type: str = SelectionField(
        [
            ("consu", "Consumable"),
            ("service", "Service"),
            ("product", "Storable Product"),
        ],
        description="Product Type",
    )

    # Pricing
    list_price: Decimal = MonetaryField(description="Sales Price")
    standard_price: Decimal = MonetaryField(description="Cost")

    # Categorization
    categ_id: "ProductCategory" = Many2OneField(
        "product.category", description="Product Category"
    )

    # Status
    active: bool = BooleanField(description="Active")
    sale_ok: bool = BooleanField(description="Can be Sold")
    purchase_ok: bool = BooleanField(description="Can be Purchased")


@register_model("product.category")
class ProductCategory(OdooModel):
    """Product Category model."""

    name: str = CharField(description="Name")
    parent_id: Optional["ProductCategory"] = Many2OneField(
        "product.category", description="Parent Category"
    )
    child_id: List["ProductCategory"] = One2ManyField(
        "product.category", "parent_id", description="Child Categories"
    )


@register_model("sale.order")
class SaleOrder(OdooModel):
    """Sales Order model."""

    name: str = CharField(description="Order Reference")
    partner_id: ResPartner = Many2OneField("res.partner", description="Customer")

    # Dates
    date_order: datetime = DateTimeField(description="Order Date")
    commitment_date: Optional[datetime] = DateTimeField(description="Delivery Date")

    # Status
    state: str = SelectionField(
        [
            ("draft", "Quotation"),
            ("sent", "Quotation Sent"),
            ("sale", "Sales Order"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        description="Status",
    )

    # Financial
    amount_untaxed: Decimal = MonetaryField(description="Untaxed Amount")
    amount_tax: Decimal = MonetaryField(description="Taxes")
    amount_total: Decimal = MonetaryField(description="Total")

    # Order lines
    order_line: List["SaleOrderLine"] = One2ManyField(
        "sale.order.line", "order_id", description="Order Lines"
    )


@register_model("sale.order.line")
class SaleOrderLine(OdooModel):
    """Sales Order Line model."""

    order_id: SaleOrder = Many2OneField("sale.order", description="Order Reference")
    product_id: ProductProduct = Many2OneField("product.product", description="Product")

    name: str = TextField(description="Description")
    product_uom_qty: float = FloatField(description="Quantity")
    price_unit: Decimal = MonetaryField(description="Unit Price")
    price_subtotal: Decimal = MonetaryField(description="Subtotal")
