"""
Comprehensive tests for Zenoo-RPC models and relationships.

This module tests all aspects of the model system including:
- Model base classes and field validation
- Relationship management and lazy loading
- Model registry and dynamic model creation
- Field types and serialization
- Model inheritance and polymorphism
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

from zenoo_rpc.models.base import OdooModel
from zenoo_rpc.models.fields import (
    CharField,
    BooleanField,
    IntegerField,
    FloatField,
    DateField,
    DateTimeField,
    Many2OneField,
    One2ManyField,
    Many2ManyField,
    SelectionField,
    TextField,
)
from zenoo_rpc.models.registry import ModelRegistry, register_model, get_model_class
from zenoo_rpc.models.relationships import LazyRelationship, RelationshipManager
from zenoo_rpc.models.common import (
    ResPartner,
    ResCountry,
    ResCountryState,
    ResCurrency,
    ResUsers,
    ProductProduct,
    ProductCategory,
    SaleOrder,
    SaleOrderLine,
)


class TestModelFields:
    """Test model field types and validation."""

    def test_char_field(self):
        """Test CharField functionality."""
        field = CharField(max_length=100, required=True, description="Name field")

        assert field.max_length == 100
        assert field.required is True
        assert field.description == "Name field"

        # Test validation
        assert field.validate("Valid string") is True
        assert field.validate("") is False  # Required field
        assert field.validate("x" * 101) is False  # Too long

    def test_boolean_field(self):
        """Test BooleanField functionality."""
        field = BooleanField(default=False, description="Active flag")

        assert field.default is False
        assert field.description == "Active flag"

        # Test validation
        assert field.validate(True) is True
        assert field.validate(False) is True
        assert field.validate("true") is False  # Should be boolean

    def test_integer_field(self):
        """Test IntegerField functionality."""
        field = IntegerField(min_value=0, max_value=100, description="Count")

        assert field.min_value == 0
        assert field.max_value == 100

        # Test validation
        assert field.validate(50) is True
        assert field.validate(0) is True
        assert field.validate(100) is True
        assert field.validate(-1) is False  # Below min
        assert field.validate(101) is False  # Above max
        assert field.validate("50") is False  # Should be int

    def test_float_field(self):
        """Test FloatField functionality."""
        field = FloatField(min_value=0.0, max_value=100.0, precision=2)

        assert field.min_value == 0.0
        assert field.max_value == 100.0
        assert field.precision == 2

        # Test validation
        assert field.validate(50.5) is True
        assert field.validate(0.0) is True
        assert field.validate(100.0) is True
        assert field.validate(-0.1) is False  # Below min
        assert field.validate(100.1) is False  # Above max

    def test_date_field(self):
        """Test DateField functionality."""
        field = DateField(description="Birth date")

        assert field.description == "Birth date"

        # Test validation
        assert field.validate(date.today()) is True
        assert field.validate("2023-01-01") is True  # ISO format
        assert field.validate("invalid-date") is False
        assert field.validate(datetime.now()) is False  # Should be date, not datetime

    def test_datetime_field(self):
        """Test DateTimeField functionality."""
        field = DateTimeField(auto_now=True, description="Created at")

        assert field.auto_now is True
        assert field.description == "Created at"

        # Test validation
        assert field.validate(datetime.now()) is True
        assert field.validate("2023-01-01T10:00:00") is True  # ISO format
        assert field.validate("invalid-datetime") is False
        assert field.validate(date.today()) is False  # Should be datetime, not date

    def test_selection_field(self):
        """Test SelectionField functionality."""
        choices = [("draft", "Draft"), ("confirmed", "Confirmed"), ("done", "Done")]
        field = SelectionField(choices=choices, description="State")

        assert field.choices == choices
        assert field.description == "State"

        # Test validation
        assert field.validate("draft") is True
        assert field.validate("confirmed") is True
        assert field.validate("invalid") is False  # Not in choices

    def test_many2one_field(self):
        """Test Many2OneField functionality."""
        field = Many2OneField(comodel_name="res.country", description="Country")

        assert field.comodel_name == "res.country"
        assert field.description == "Country"
        assert field.is_relationship is True

        # Test validation
        assert field.validate(123) is True  # Valid ID
        assert field.validate(0) is False  # Invalid ID
        assert field.validate("string") is False  # Should be int

    def test_one2many_field(self):
        """Test One2ManyField functionality."""
        field = One2ManyField(
            comodel_name="res.partner", inverse_name="parent_id", description="Children"
        )

        assert field.comodel_name == "res.partner"
        assert field.inverse_name == "parent_id"
        assert field.description == "Children"
        assert field.is_relationship is True

        # Test validation
        assert field.validate([1, 2, 3]) is True  # List of IDs
        assert field.validate([]) is True  # Empty list
        assert field.validate("not-a-list") is False

    def test_many2many_field(self):
        """Test Many2ManyField functionality."""
        field = Many2ManyField(
            comodel_name="res.groups",
            relation="res_users_groups_rel",
            description="Groups",
        )

        assert field.comodel_name == "res.groups"
        assert field.relation == "res_users_groups_rel"
        assert field.description == "Groups"
        assert field.is_relationship is True

        # Test validation
        assert field.validate([1, 2, 3]) is True  # List of IDs
        assert field.validate([]) is True  # Empty list
        assert field.validate("not-a-list") is False


class TestModelBase:
    """Test OdooModel base class functionality."""

    def test_model_creation_with_validation(self):
        """Test model creation with field validation."""
        partner = ResPartner(
            id=1,
            name="Test Partner",
            is_company=True,
            email="test@example.com",
            customer_rank=1,
            supplier_rank=0,
        )

        assert partner.id == 1
        assert partner.name == "Test Partner"
        assert partner.is_company is True
        assert partner.email == "test@example.com"
        assert partner.customer_rank == 1
        assert partner.supplier_rank == 0

    def test_model_validation_errors(self):
        """Test model validation error handling."""
        # Test with invalid data types
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResPartner(id="invalid_id", name="Test")  # Should be int

        # Test with missing required fields
        with pytest.raises(Exception):  # Pydantic ValidationError
            ResPartner()  # Missing required id field

    def test_model_field_access(self):
        """Test model field access and modification."""
        partner = ResPartner(id=1, name="Original Name", email="original@example.com")

        # Test field access
        assert partner.name == "Original Name"
        assert partner.email == "original@example.com"

        # Test field modification
        partner.name = "Updated Name"
        partner.email = "updated@example.com"

        assert partner.name == "Updated Name"
        assert partner.email == "updated@example.com"

    def test_model_odoo_name(self):
        """Test Odoo model name functionality."""
        assert ResPartner.get_odoo_name() == "res.partner"
        assert ResCountry.get_odoo_name() == "res.country"
        assert ProductProduct.get_odoo_name() == "product.product"
        assert SaleOrder.get_odoo_name() == "sale.order"

    def test_model_field_info(self):
        """Test model field information retrieval."""
        # Test existing field
        name_field = ResPartner.get_field_info("name")
        assert name_field is not None

        # Test non-existent field
        invalid_field = ResPartner.get_field_info("non_existent_field")
        assert invalid_field is None

    def test_model_relationship_fields(self):
        """Test relationship field detection."""
        rel_fields = ResPartner.get_relationship_fields()

        assert isinstance(rel_fields, dict)
        # Should contain relationship fields like country_id, parent_id, etc.
        # The exact fields depend on the model definition

    def test_model_serialization(self):
        """Test model serialization to Odoo format."""
        partner = ResPartner(
            id=1,
            name="Test Partner",
            is_company=True,
            email="test@example.com",
            phone="+1-555-0123",
        )

        # Test to_odoo_dict (excludes id for create operations)
        odoo_dict = partner.to_odoo_dict()
        assert "id" not in odoo_dict
        assert odoo_dict["name"] == "Test Partner"
        assert odoo_dict["is_company"] is True
        assert odoo_dict["email"] == "test@example.com"
        assert odoo_dict["phone"] == "+1-555-0123"

        # Test to_odoo_dict with include_id
        odoo_dict_with_id = partner.to_odoo_dict(include_id=True)
        assert odoo_dict_with_id["id"] == 1

    def test_model_loaded_fields_tracking(self):
        """Test tracking of loaded fields."""
        partner = ResPartner(id=1, name="Test Partner", email="test@example.com")

        # Check loaded fields
        loaded_fields = partner.get_loaded_fields()
        assert "id" in loaded_fields
        assert "name" in loaded_fields
        assert "email" in loaded_fields

        # Check field loading status
        assert partner.is_field_loaded("name") is True
        assert partner.is_field_loaded("email") is True
        assert partner.is_field_loaded("phone") is False  # Not provided

        # Mark field as loaded
        partner.mark_field_loaded("phone")
        assert partner.is_field_loaded("phone") is True

    def test_model_string_representation(self):
        """Test model string representation."""
        partner = ResPartner(id=1, name="Test Partner")

        # Test __repr__
        repr_str = repr(partner)
        assert "ResPartner" in repr_str
        assert "id=1" in repr_str

        # Test __str__
        str_str = str(partner)
        assert str_str == "Test Partner"

        # Test with model without name field
        country = ResCountry(id=1, name="United States", code="US")

        str_country = str(country)
        assert str_country == "United States"


class TestModelRelationships:
    """Test model relationship functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()

    def test_lazy_relationship_creation(self):
        """Test lazy relationship creation."""
        partner = ResPartner(
            id=1, name="Test Partner", country_id=123, client=self.mock_client
        )

        # Should have relationship manager
        assert partner.relationship_manager is not None
        assert partner.relationship_manager.model == partner
        assert partner.relationship_manager.client == self.mock_client

    @pytest.mark.asyncio
    async def test_many2one_relationship_loading(self):
        """Test Many2One relationship lazy loading."""
        # Mock country data
        country_data = {"id": 123, "name": "United States", "code": "US"}
        self.mock_client.search_read.return_value = [country_data]

        partner = ResPartner(
            id=1, name="Test Partner", country_id=123, client=self.mock_client
        )

        # Access country relationship (should trigger lazy loading)
        country = await partner.country_id

        assert isinstance(country, ResCountry)
        assert country.id == 123
        assert country.name == "United States"
        assert country.code == "US"

        # Verify client was called
        self.mock_client.search_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_one2many_relationship_loading(self):
        """Test One2Many relationship lazy loading."""
        # Mock children data
        children_data = [
            {"id": 2, "name": "Child 1", "parent_id": 1},
            {"id": 3, "name": "Child 2", "parent_id": 1},
        ]
        self.mock_client.search_read.return_value = children_data

        partner = ResPartner(id=1, name="Parent Partner", client=self.mock_client)

        # Access children relationship
        children = await partner.child_ids.all()

        assert len(children) == 2
        assert all(isinstance(child, ResPartner) for child in children)
        assert children[0].name == "Child 1"
        assert children[1].name == "Child 2"

        # Verify client was called with correct domain
        call_args = self.mock_client.search_read.call_args
        assert call_args[0][1] == [("parent_id", "=", 1)]  # Domain filter

    @pytest.mark.asyncio
    async def test_many2many_relationship_loading(self):
        """Test Many2Many relationship lazy loading."""
        # Mock groups data
        groups_data = [
            {"id": 10, "name": "Sales Team"},
            {"id": 11, "name": "Admin Group"},
        ]
        self.mock_client.search_read.return_value = groups_data

        user = ResUsers(
            id=1,
            name="Test User",
            login="test@example.com",
            groups_id=[10, 11],
            client=self.mock_client,
        )

        # Access groups relationship
        groups = await user.groups_id.all()

        assert len(groups) == 2
        assert groups[0].name == "Sales Team"
        assert groups[1].name == "Admin Group"

        # Verify client was called with correct domain
        call_args = self.mock_client.search_read.call_args
        assert call_args[0][1] == [("id", "in", [10, 11])]  # Domain filter

    def test_relationship_manager_initialization(self):
        """Test relationship manager initialization."""
        partner = ResPartner(id=1, name="Test Partner", client=self.mock_client)

        manager = partner.relationship_manager
        assert manager is not None
        assert manager.model == partner
        assert manager.client == self.mock_client
        assert isinstance(manager.relationships, dict)


class TestModelRegistry:
    """Test model registry functionality."""

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
            name: str = CharField(max_length=100, description="Name")
            active: bool = BooleanField(default=True, description="Active")

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
            name: str = CharField(max_length=100, description="Name")
            value: int = IntegerField(min_value=0, description="Value")

        # Check registration
        assert registry.has_model("test.decorated")
        assert registry.get_model("test.decorated") == DecoratedModel
        assert DecoratedModel.odoo_name == "test.decorated"

    def test_dynamic_model_creation(self):
        """Test dynamic model creation from field definitions."""
        registry = ModelRegistry()

        field_definitions = {
            "name": {"type": "char", "string": "Name", "required": True, "size": 100},
            "active": {"type": "boolean", "string": "Active", "default": True},
            "value": {"type": "integer", "string": "Value", "required": False},
        }

        # Create model dynamically
        DynamicModel = registry.create_model_from_fields(
            "dynamic.model", field_definitions
        )

        # Test the created model
        assert DynamicModel.get_odoo_name() == "dynamic.model"

        # Create instance
        instance = DynamicModel(id=1, name="Test Instance", active=True, value=42)

        assert instance.name == "Test Instance"
        assert instance.active is True
        assert instance.value == 42

    def test_class_name_generation(self):
        """Test Python class name generation from Odoo model names."""
        registry = ModelRegistry()

        # Test various model name formats
        assert registry._generate_class_name("res.partner") == "ResPartner"
        assert registry._generate_class_name("sale.order") == "SaleOrder"
        assert registry._generate_class_name("account.move.line") == "AccountMoveLine"
        assert registry._generate_class_name("simple") == "Simple"
        assert registry._generate_class_name("multi.word.model") == "MultiWordModel"

    def test_field_type_mapping(self):
        """Test field type mapping functionality."""
        registry = ModelRegistry()

        # Test char field creation
        char_field_def = {
            "type": "char",
            "string": "Test Field",
            "required": True,
            "size": 100,
        }

        char_field = registry._create_char_field("test_field", char_field_def)
        assert char_field is not None

        # Test boolean field creation
        bool_field_def = {"type": "boolean", "string": "Test Boolean", "default": False}

        bool_field = registry._create_boolean_field("test_bool", bool_field_def)
        assert bool_field is not None

        # Test many2one field creation
        m2o_field_def = {
            "type": "many2one",
            "string": "Related Record",
            "relation": "res.partner",
            "required": False,
        }

        m2o_field = registry._create_many2one_field("partner_id", m2o_field_def)
        assert m2o_field is not None
