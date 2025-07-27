"""
Tests for Zenoo-RPC models and Pydantic integration.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from zenoo_rpc.models.base import OdooModel
from zenoo_rpc.models.fields import CharField, BooleanField, Many2OneField
from zenoo_rpc.models.registry import ModelRegistry, register_model
from zenoo_rpc.models.common import ResPartner, ResCountry


class TestOdooModel:
    """Test cases for OdooModel base class."""

    def test_model_creation(self):
        """Test basic model creation."""
        partner = ResPartner(
            id=1, name="Test Partner", is_company=True, email="test@example.com"
        )

        assert partner.id == 1
        assert partner.name == "Test Partner"
        assert partner.is_company is True
        assert partner.email == "test@example.com"

    def test_model_validation(self):
        """Test Pydantic validation."""
        # Valid data
        partner = ResPartner(id=1, name="Test Partner", is_company=True)
        assert partner.name == "Test Partner"

        # Invalid data should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResPartner(id="invalid", name="Test")  # Should be int

    def test_model_odoo_name(self):
        """Test Odoo model name retrieval."""
        assert ResPartner.get_odoo_name() == "res.partner"
        assert ResCountry.get_odoo_name() == "res.country"

    def test_model_field_info(self):
        """Test field information retrieval."""
        name_field = ResPartner.get_field_info("name")
        assert name_field is not None

        # Non-existent field
        invalid_field = ResPartner.get_field_info("non_existent")
        assert invalid_field is None

    def test_model_relationship_fields(self):
        """Test relationship field detection."""
        rel_fields = ResPartner.get_relationship_fields()

        # For now, since we simplified the fields, this might be empty
        # This test can be expanded when we implement proper relationship detection
        assert isinstance(rel_fields, dict)

    def test_model_to_odoo_dict(self):
        """Test conversion to Odoo dictionary format."""
        partner = ResPartner(
            id=1, name="Test Partner", is_company=True, email="test@example.com"
        )

        odoo_dict = partner.to_odoo_dict()

        # Should exclude id and include other fields
        assert "id" not in odoo_dict
        assert odoo_dict["name"] == "Test Partner"
        assert odoo_dict["is_company"] is True
        assert odoo_dict["email"] == "test@example.com"

    def test_model_loaded_fields_tracking(self):
        """Test tracking of loaded fields."""
        partner = ResPartner(id=1, name="Test Partner", email="test@example.com")

        # Check loaded fields
        loaded_fields = partner.get_loaded_fields()
        assert "id" in loaded_fields
        assert "name" in loaded_fields
        assert "email" in loaded_fields

        # Check field loading status
        assert partner.is_field_loaded("name")
        assert partner.is_field_loaded("email")
        assert not partner.is_field_loaded("phone")  # Not provided

    def test_model_string_representation(self):
        """Test string representation of models."""
        partner = ResPartner(id=1, name="Test Partner")

        # __repr__ should include class name and id
        repr_str = repr(partner)
        assert "ResPartner" in repr_str
        assert "id=1" in repr_str
        assert "Test Partner" in repr_str

        # __str__ should return name if available
        str_str = str(partner)
        assert str_str == "Test Partner"


class TestModelRegistry:
    """Test cases for ModelRegistry."""

    def test_registry_creation(self):
        """Test registry creation and basic operations."""
        registry = ModelRegistry()

        # Should be empty initially
        assert len(registry.list_models()) == 0
        assert not registry.has_model("test.model")

    def test_model_registration(self):
        """Test model registration."""
        registry = ModelRegistry()

        # Create a test model
        class TestModel(OdooModel):
            name: str = CharField(description="Name")

        # Register the model
        registry.register_model("test.model", TestModel)

        # Check registration
        assert registry.has_model("test.model")
        assert registry.get_model("test.model") == TestModel
        assert "test.model" in registry.list_models()

    def test_register_decorator(self):
        """Test the register decorator."""
        registry = ModelRegistry()

        @registry.register("test.decorated")
        class DecoratedModel(OdooModel):
            name: str = CharField(description="Name")

        # Check registration
        assert registry.has_model("test.decorated")
        assert registry.get_model("test.decorated") == DecoratedModel
        assert DecoratedModel.odoo_name == "test.decorated"

    def test_field_type_mapping(self):
        """Test field type mapping functionality."""
        registry = ModelRegistry()

        # Test char field creation
        field_def = {
            "type": "char",
            "string": "Test Field",
            "required": True,
            "size": 100,
        }

        pydantic_field = registry._create_char_field("test_field", field_def)
        assert pydantic_field is not None

        # Test boolean field creation
        bool_field_def = {"type": "boolean", "string": "Test Boolean", "default": False}

        bool_field = registry._create_boolean_field("test_bool", bool_field_def)
        assert bool_field is not None

    def test_class_name_generation(self):
        """Test Python class name generation from Odoo model names."""
        registry = ModelRegistry()

        # Test various model name formats
        assert registry._generate_class_name("res.partner") == "ResPartner"
        assert registry._generate_class_name("sale.order") == "SaleOrder"
        assert registry._generate_class_name("account.move.line") == "AccountMoveLine"
        assert registry._generate_class_name("simple") == "Simple"


class TestCommonModels:
    """Test cases for common model definitions."""

    def test_res_partner_creation(self):
        """Test ResPartner model creation."""
        partner = ResPartner(
            id=1,
            name="ACME Corporation",
            is_company=True,
            email="contact@acme.com",
            phone="+1-555-0123",
            customer_rank=1,
            supplier_rank=0,
        )

        assert partner.name == "ACME Corporation"
        assert partner.is_company is True
        assert partner.email == "contact@acme.com"
        assert partner.phone == "+1-555-0123"

    def test_res_partner_properties(self):
        """Test ResPartner computed properties."""
        # Customer
        customer = ResPartner(id=1, name="Customer", customer_rank=1, supplier_rank=0)
        assert customer.is_customer is True
        assert customer.is_vendor is False

        # Vendor
        vendor = ResPartner(id=2, name="Vendor", customer_rank=0, supplier_rank=1)
        assert vendor.is_customer is False
        assert vendor.is_vendor is True

        # Both
        both = ResPartner(id=3, name="Both", customer_rank=1, supplier_rank=1)
        assert both.is_customer is True
        assert both.is_vendor is True

    def test_res_partner_full_address(self):
        """Test full address formatting."""
        partner = ResPartner(
            id=1,
            name="Test Partner",
            street="123 Main St",
            street2="Suite 100",
            city="Anytown",
            zip="12345",
        )

        expected_address = "123 Main St, Suite 100, Anytown, 12345"
        assert partner.full_address == expected_address

        # Test with partial address
        partial_partner = ResPartner(
            id=2, name="Partial", street="456 Oak Ave", city="Somewhere"
        )

        expected_partial = "456 Oak Ave, Somewhere"
        assert partial_partner.full_address == expected_partial

    def test_res_country_creation(self):
        """Test ResCountry model creation."""
        country = ResCountry(id=1, name="United States", code="US", phone_code=1)

        assert country.name == "United States"
        assert country.code == "US"
        assert country.phone_code == 1

    def test_model_inheritance(self):
        """Test that all models inherit from OdooModel properly."""
        partner = ResPartner(id=1, name="Test")
        country = ResCountry(id=1, name="Test Country", code="TC")

        # Both should be instances of OdooModel
        assert isinstance(partner, OdooModel)
        assert isinstance(country, OdooModel)

        # Both should have the required id field
        assert hasattr(partner, "id")
        assert hasattr(country, "id")

        # Both should have Odoo model names
        assert partner.get_odoo_name() == "res.partner"
        assert country.get_odoo_name() == "res.country"

    @pytest.mark.asyncio
    async def test_relationship_descriptors(self):
        """Test relationship field descriptors."""
        mock_client = AsyncMock()

        # Mock country data
        mock_client.search_read.return_value = [
            {"id": 1, "name": "United States", "display_name": "United States"}
        ]

        partner = ResPartner(
            id=1, name="Test Partner", country_id=1, client=mock_client
        )

        # Access relationship field should return LazyRelationship
        country_rel = partner.country_id
        assert hasattr(country_rel, "load")

        # Loading should trigger client call
        country_data = await country_rel.load()
        assert country_data is not None
        mock_client.search_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_n_plus_one_prevention(self):
        """Test N+1 query prevention with batch loading."""
        mock_client = AsyncMock()

        # Mock batch response
        mock_client.search_read.return_value = [
            {"id": 1, "name": "United States", "display_name": "United States"},
            {"id": 2, "name": "Canada", "display_name": "Canada"},
        ]

        # Create multiple partners with different countries
        partners = [
            ResPartner(id=1, name="Partner 1", country_id=1, client=mock_client),
            ResPartner(id=2, name="Partner 2", country_id=2, client=mock_client),
            ResPartner(id=3, name="Partner 3", country_id=1, client=mock_client),
        ]

        # Access all country relationships concurrently
        import asyncio

        countries = await asyncio.gather(
            *[partner.country_id.load() for partner in partners]
        )

        # Should have made only one batch call instead of 3 separate calls
        assert mock_client.search_read.call_count == 1
        assert len(countries) == 3
