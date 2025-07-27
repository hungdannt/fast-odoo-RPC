"""
Comprehensive tests for common Odoo model definitions.

This module tests all pre-defined model classes with focus on:
- Model instantiation and field validation
- Property methods and computed fields
- Relationship field handling
- Model registration and inheritance
- Field type validation and constraints
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.zenoo_rpc.models.common import (
    ResPartner,
    ResCountry,
    ResCountryState,
    ResCurrency,
    ResUsers,
    ResGroups,
    ResGroupsCategory,
    ProductProduct,
    ProductCategory,
    SaleOrder,
    SaleOrderLine,
)
from src.zenoo_rpc.models.base import OdooModel


class TestResPartner:
    """Test ResPartner model class."""

    def test_model_registration(self):
        """Test that ResPartner is properly registered."""
        assert ResPartner.odoo_name == "res.partner"
        assert issubclass(ResPartner, OdooModel)

    def test_basic_instantiation(self):
        """Test basic ResPartner instantiation."""
        partner = ResPartner(id=1, name="Test Partner")
        
        assert partner.id == 1
        assert partner.name == "Test Partner"
        assert partner.is_company is False
        assert partner.active is True
        assert partner.customer_rank == 0
        assert partner.supplier_rank == 0

    def test_company_partner(self):
        """Test company partner creation."""
        partner = ResPartner(
            id=2,
            name="ACME Corporation",
            is_company=True,
            email="contact@acme.com",
            customer_rank=1
        )
        
        assert partner.name == "ACME Corporation"
        assert partner.is_company is True
        assert partner.email == "contact@acme.com"
        assert partner.customer_rank == 1

    def test_is_customer_property(self):
        """Test is_customer property method."""
        # Test customer
        customer = ResPartner(id=1, name="Customer", customer_rank=1)
        assert customer.is_customer is True
        
        # Test non-customer
        non_customer = ResPartner(id=2, name="Non-Customer", customer_rank=0)
        assert non_customer.is_customer is False
        
        # Test high rank customer
        vip_customer = ResPartner(id=3, name="VIP", customer_rank=5)
        assert vip_customer.is_customer is True

    def test_is_vendor_property(self):
        """Test is_vendor property method."""
        # Test vendor
        vendor = ResPartner(id=1, name="Vendor", supplier_rank=1)
        assert vendor.is_vendor is True
        
        # Test non-vendor
        non_vendor = ResPartner(id=2, name="Non-Vendor", supplier_rank=0)
        assert non_vendor.is_vendor is False
        
        # Test high rank vendor
        preferred_vendor = ResPartner(id=3, name="Preferred", supplier_rank=3)
        assert preferred_vendor.is_vendor is True

    def test_customer_and_vendor(self):
        """Test partner that is both customer and vendor."""
        partner = ResPartner(
            id=1,
            name="Customer & Vendor",
            customer_rank=2,
            supplier_rank=1
        )
        
        assert partner.is_customer is True
        assert partner.is_vendor is True

    def test_full_address_property(self):
        """Test full_address property method."""
        # Test complete address
        partner = ResPartner(
            id=1,
            name="Test Partner",
            street="123 Main St",
            street2="Suite 100",
            city="New York",
            zip="10001"
        )
        
        expected = "123 Main St, Suite 100, New York, 10001"
        assert partner.full_address == expected

    def test_partial_address(self):
        """Test full_address with partial information."""
        # Test with only street and city
        partner = ResPartner(
            id=1,
            name="Partial Address",
            street="456 Oak Ave",
            city="Los Angeles"
        )
        
        assert partner.full_address == "456 Oak Ave, Los Angeles"

    def test_empty_address(self):
        """Test full_address with no address information."""
        partner = ResPartner(id=1, name="No Address")
        assert partner.full_address == ""

    def test_single_address_field(self):
        """Test full_address with single field."""
        partner = ResPartner(id=1, name="City Only", city="Chicago")
        assert partner.full_address == "Chicago"

    def test_address_with_none_values(self):
        """Test full_address handling None values."""
        partner = ResPartner(
            id=1,
            name="Mixed Address",
            street="789 Pine St",
            street2=None,  # Explicitly None
            city="Seattle",
            zip=None  # Explicitly None
        )
        
        assert partner.full_address == "789 Pine St, Seattle"

    def test_contact_information(self):
        """Test contact information fields."""
        partner = ResPartner(
            id=1,
            name="Contact Test",
            email="test@example.com",
            phone="+1-555-0123",
            mobile="+1-555-0124",
            website="https://example.com"
        )
        
        assert partner.email == "test@example.com"
        assert partner.phone == "+1-555-0123"
        assert partner.mobile == "+1-555-0124"
        assert partner.website == "https://example.com"

    def test_system_fields(self):
        """Test system fields like create_date, write_date."""
        now = datetime.now()
        partner = ResPartner(
            id=1,
            name="System Fields Test",
            create_date=now,
            write_date=now
        )
        
        assert partner.create_date == now
        assert partner.write_date == now
        assert partner.active is True  # Default value

    def test_reference_field(self):
        """Test reference and comment fields."""
        partner = ResPartner(
            id=1,
            name="Reference Test",
            ref="CUST-001",
            comment="Important customer"
        )
        
        assert partner.ref == "CUST-001"
        assert partner.comment == "Important customer"


class TestResCountry:
    """Test ResCountry model class."""

    def test_model_registration(self):
        """Test that ResCountry is properly registered."""
        assert issubclass(ResCountry, OdooModel)

    def test_basic_instantiation(self):
        """Test basic ResCountry instantiation."""
        country = ResCountry(
            id=1,
            name="United States",
            code="US",
            phone_code=1
        )
        
        assert country.name == "United States"
        assert country.code == "US"
        assert country.phone_code == 1

    def test_country_without_phone_code(self):
        """Test country without phone code."""
        country = ResCountry(id=1, name="Test Country", code="TC")

        assert country.name == "Test Country"
        assert country.code == "TC"
        # IntegerField may default to 0 instead of None
        assert country.phone_code == 0 or country.phone_code is None


class TestResCurrency:
    """Test ResCurrency model class."""

    def test_basic_instantiation(self):
        """Test basic ResCurrency instantiation."""
        currency = ResCurrency(
            id=1,
            name="USD",
            symbol="$",
            rate=1.0,
            active=True
        )
        
        assert currency.name == "USD"
        assert currency.symbol == "$"
        assert currency.rate == 1.0
        assert currency.active is True

    def test_inactive_currency(self):
        """Test inactive currency."""
        currency = ResCurrency(
            id=2,
            name="OLD",
            symbol="O",
            rate=0.5,
            active=False
        )
        
        assert currency.active is False


class TestProductProduct:
    """Test ProductProduct model class."""

    def test_basic_instantiation(self):
        """Test basic ProductProduct instantiation."""
        category = ProductCategory(id=1, name="Test Category")
        product = ProductProduct(
            id=1,
            name="Test Product",
            default_code="PROD-001",
            barcode="123456789",
            type="product",
            list_price=Decimal("99.99"),
            standard_price=Decimal("50.00"),
            categ_id=category,
            active=True,
            sale_ok=True,
            purchase_ok=True
        )

        assert product.name == "Test Product"
        assert product.default_code == "PROD-001"
        assert product.barcode == "123456789"
        assert product.type == "product"
        assert product.list_price == Decimal("99.99")
        assert product.standard_price == Decimal("50.00")
        assert product.categ_id == category
        assert product.active is True
        assert product.sale_ok is True
        assert product.purchase_ok is True

    def test_product_types(self):
        """Test different product types."""
        types = ["consu", "service", "product"]
        category = ProductCategory(id=1, name="Test Category")

        for product_type in types:
            product = ProductProduct(
                id=1,
                name=f"Test {product_type}",
                default_code=f"CODE{product_type}",
                barcode=f"BAR{product_type}",
                type=product_type,
                list_price=Decimal("10.00"),
                standard_price=Decimal("5.00"),
                categ_id=category,
                active=True,
                sale_ok=True,
                purchase_ok=True
            )
            assert product.type == product_type

    def test_product_flags(self):
        """Test product sale and purchase flags."""
        category = ProductCategory(id=1, name="Test Category")
        product = ProductProduct(
            id=1,
            name="Sellable Product",
            default_code="SELLABLE",
            barcode="SELLABLE123",
            type="product",
            list_price=Decimal("20.00"),
            standard_price=Decimal("10.00"),
            categ_id=category,
            sale_ok=True,
            purchase_ok=False,
            active=True
        )

        assert product.sale_ok is True
        assert product.purchase_ok is False
        assert product.active is True


class TestSaleOrder:
    """Test SaleOrder model class."""

    def test_basic_instantiation(self):
        """Test basic SaleOrder instantiation."""
        order_date = datetime.now()
        order = SaleOrder(
            id=1,
            name="SO001",
            date_order=order_date,
            state="draft",
            amount_untaxed=Decimal("100.00"),
            amount_tax=Decimal("10.00"),
            amount_total=Decimal("110.00")
        )
        
        assert order.name == "SO001"
        assert order.date_order == order_date
        assert order.state == "draft"
        assert order.amount_untaxed == Decimal("100.00")
        assert order.amount_tax == Decimal("10.00")
        assert order.amount_total == Decimal("110.00")

    def test_sale_order_states(self):
        """Test different sale order states."""
        states = ["draft", "sent", "sale", "done", "cancel"]
        
        for state in states:
            order = SaleOrder(
                id=1,
                name="SO001",
                date_order=datetime.now(),
                state=state
            )
            assert order.state == state


class TestModelIntegration:
    """Test integration between different models."""

    def test_model_inheritance(self):
        """Test that all models inherit from OdooModel."""
        models = [
            ResPartner, ResCountry, ResCountryState, ResCurrency,
            ResUsers, ResGroups, ResGroupsCategory,
            ProductProduct, ProductCategory,
            SaleOrder, SaleOrderLine
        ]
        
        for model_class in models:
            assert issubclass(model_class, OdooModel)

    def test_model_instantiation_with_defaults(self):
        """Test that models can be instantiated with minimal data."""
        # Test each model with minimal required fields
        partner = ResPartner(id=1, name="Test")
        assert partner.name == "Test"
        
        country = ResCountry(id=1, name="Test Country", code="TC")
        assert country.name == "Test Country"
        
        category = ProductCategory(id=1, name="Test Category")
        product = ProductProduct(
            id=1,
            name="Test Product",
            default_code="TEST",
            barcode="TEST123",
            type="product",
            list_price=Decimal("1.00"),
            standard_price=Decimal("0.50"),
            categ_id=category,
            active=True,
            sale_ok=True,
            purchase_ok=True
        )
        assert product.name == "Test Product"

    def test_decimal_field_handling(self):
        """Test proper handling of Decimal fields."""
        category = ProductCategory(id=1, name="Test Category")
        product = ProductProduct(
            id=1,
            name="Decimal Test",
            default_code="DECIMAL",
            barcode="DECIMAL123",
            type="product",
            list_price=Decimal("123.45"),
            standard_price=Decimal("67.89"),
            categ_id=category,
            active=True,
            sale_ok=True,
            purchase_ok=True
        )
        
        assert isinstance(product.list_price, Decimal)
        assert isinstance(product.standard_price, Decimal)
        assert product.list_price == Decimal("123.45")
        assert product.standard_price == Decimal("67.89")

    def test_datetime_field_handling(self):
        """Test proper handling of datetime fields."""
        now = datetime.now()
        partner = ResPartner(id=1, name="Test Customer")
        order = SaleOrder(
            id=1,
            name="DT001",
            partner_id=partner,  # Required field
            date_order=now,
            commitment_date=now,
            state="draft",  # Required field
            amount_untaxed=Decimal("100.00"),  # Required field
            amount_tax=Decimal("10.00"),  # Required field
            amount_total=Decimal("110.00")  # Required field
        )
        
        assert isinstance(order.date_order, datetime)
        assert isinstance(order.commitment_date, datetime)
        assert order.date_order == now
        assert order.commitment_date == now
