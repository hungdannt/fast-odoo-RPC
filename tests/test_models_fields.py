"""
Comprehensive tests for models/fields.py.

This module tests all field types and descriptors with focus on:
- Field creation and validation
- Relationship descriptors and lazy loading
- Type safety and serialization
- Odoo-specific field behaviors
- Integration with Pydantic validation
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Union
from unittest.mock import Mock, AsyncMock

from src.zenoo_rpc.models.fields import (
    RelationshipDescriptor,
    Many2OneDescriptor,
    One2ManyDescriptor,
    Many2ManyDescriptor,
    Many2OneField,
    One2ManyField,
    Many2ManyField,
    SelectionField,
    BinaryField,
    DateField,
    DateTimeField,
    MonetaryField,
    FloatField,
    IntegerField,
    TextField,
    CharField,
    BooleanField,
)
from src.zenoo_rpc.models.base import OdooModel
from pydantic import BaseModel, ValidationError


class MockOdooModel(OdooModel):
    """Mock Odoo model for testing."""
    
    odoo_name = "test.model"
    
    def __init__(self, **data):
        super().__init__(**data)
        self.client = Mock()


class TestRelationshipDescriptor:
    """Test RelationshipDescriptor base class."""

    def test_basic_instantiation(self):
        """Test basic RelationshipDescriptor creation."""
        field_info = Many2OneField("res.partner")
        descriptor = RelationshipDescriptor("partner_id", "res.partner", field_info)
        
        assert descriptor.field_name == "partner_id"
        assert descriptor.comodel_name == "res.partner"
        assert descriptor.field_info == field_info
        assert descriptor.is_collection is False

    def test_get_with_none_instance(self):
        """Test descriptor behavior when instance is None."""
        field_info = Many2OneField("res.partner")
        descriptor = RelationshipDescriptor("partner_id", "res.partner", field_info)
        
        # When called on class, should return descriptor itself
        result = descriptor.__get__(None, MockOdooModel)
        assert result is descriptor

    def test_get_with_no_value(self):
        """Test descriptor behavior when field has no value."""
        field_info = Many2OneField("res.partner")
        descriptor = RelationshipDescriptor("partner_id", "res.partner", field_info)
        
        instance = MockOdooModel(id=1)
        result = descriptor.__get__(instance, MockOdooModel)
        
        assert result is None

    def test_get_with_collection_no_value(self):
        """Test descriptor behavior for collection fields with no value."""
        field_info = One2ManyField("res.partner", "parent_id")
        descriptor = RelationshipDescriptor("child_ids", "res.partner", field_info)
        descriptor.is_collection = True
        
        instance = MockOdooModel(id=1)
        result = descriptor.__get__(instance, MockOdooModel)
        
        assert result == []

    def test_get_with_model_instance(self):
        """Test descriptor behavior when value is already a model instance."""
        field_info = Many2OneField("res.partner")
        descriptor = RelationshipDescriptor("partner_id", "res.partner", field_info)
        
        # Create mock partner instance
        partner = Mock()
        partner.id = 123
        partner.odoo_name = "res.partner"
        
        instance = MockOdooModel(id=1)
        instance.__dict__["partner_id"] = partner
        
        result = descriptor.__get__(instance, MockOdooModel)
        assert result is partner

    def test_get_with_integer_id(self):
        """Test descriptor behavior when value is an integer ID."""
        field_info = Many2OneField("res.partner")
        descriptor = RelationshipDescriptor("partner_id", "res.partner", field_info)
        
        instance = MockOdooModel(id=1)
        instance.__dict__["partner_id"] = 123
        
        result = descriptor.__get__(instance, MockOdooModel)
        
        # Should create LazyRelationship
        assert hasattr(result, "relation_ids")
        assert result.relation_ids == 123

    def test_get_with_list_of_ids(self):
        """Test descriptor behavior when value is a list of IDs."""
        field_info = One2ManyField("res.partner", "parent_id")
        descriptor = RelationshipDescriptor("child_ids", "res.partner", field_info)
        descriptor.is_collection = True
        
        instance = MockOdooModel(id=1)
        instance.__dict__["child_ids"] = [123, 456, 789]
        
        result = descriptor.__get__(instance, MockOdooModel)
        
        # Should create LazyRelationship
        assert hasattr(result, "relation_ids")
        assert result.relation_ids == [123, 456, 789]

    def test_set_value(self):
        """Test descriptor __set__ method."""
        field_info = Many2OneField("res.partner")
        descriptor = RelationshipDescriptor("partner_id", "res.partner", field_info)
        
        instance = MockOdooModel(id=1)
        instance._loaded_relationships = {"partner_id": "cached_value"}
        
        # Set new value
        descriptor.__set__(instance, 456)
        
        # Should update __dict__ and clear cache
        assert instance.__dict__["partner_id"] == 456
        assert "partner_id" not in instance._loaded_relationships

    def test_caching_behavior(self):
        """Test that relationships are properly cached."""
        field_info = Many2OneField("res.partner")
        descriptor = RelationshipDescriptor("partner_id", "res.partner", field_info)
        
        instance = MockOdooModel(id=1)
        instance.__dict__["partner_id"] = 123
        
        # First access should create lazy relationship
        result1 = descriptor.__get__(instance, MockOdooModel)
        
        # Second access should return cached value
        result2 = descriptor.__get__(instance, MockOdooModel)
        
        assert result1 is result2
        assert "partner_id" in instance._loaded_relationships


class TestMany2OneDescriptor:
    """Test Many2OneDescriptor class."""

    def test_inheritance(self):
        """Test that Many2OneDescriptor inherits from RelationshipDescriptor."""
        assert issubclass(Many2OneDescriptor, RelationshipDescriptor)

    def test_is_collection_false(self):
        """Test that Many2OneDescriptor is not a collection."""
        field_info = Many2OneField("res.partner")
        descriptor = Many2OneDescriptor("partner_id", "res.partner", field_info)
        
        assert descriptor.is_collection is False


class TestOne2ManyDescriptor:
    """Test One2ManyDescriptor class."""

    def test_inheritance(self):
        """Test that One2ManyDescriptor inherits from RelationshipDescriptor."""
        assert issubclass(One2ManyDescriptor, RelationshipDescriptor)

    def test_is_collection_true(self):
        """Test that One2ManyDescriptor is a collection."""
        field_info = One2ManyField("res.partner", "parent_id")
        descriptor = One2ManyDescriptor("child_ids", "res.partner", field_info)
        
        assert descriptor.is_collection is True


class TestMany2ManyDescriptor:
    """Test Many2ManyDescriptor class."""

    def test_inheritance(self):
        """Test that Many2ManyDescriptor inherits from RelationshipDescriptor."""
        assert issubclass(Many2ManyDescriptor, RelationshipDescriptor)

    def test_is_collection_true(self):
        """Test that Many2ManyDescriptor is a collection."""
        field_info = Many2ManyField("product.category")
        descriptor = Many2ManyDescriptor("category_ids", "product.category", field_info)
        
        assert descriptor.is_collection is True


class TestMany2OneField:
    """Test Many2OneField function."""

    def test_basic_creation(self):
        """Test basic Many2OneField creation."""
        field = Many2OneField("res.partner", description="Partner")
        
        assert field.default is None
        assert field.description == "Partner"
        assert field.json_schema_extra["odoo_type"] == "many2one"
        assert field.json_schema_extra["odoo_relation"] == "res.partner"

    def test_with_additional_kwargs(self):
        """Test Many2OneField with additional parameters."""
        field = Many2OneField(
            "res.partner",
            description="Partner",
            required=True,
            domain="[('is_company', '=', True)]"
        )
        
        assert field.json_schema_extra["required"] is True
        assert field.json_schema_extra["domain"] == "[('is_company', '=', True)]"

    def test_field_validation(self):
        """Test Many2OneField validation in a model."""
        class TestModel(BaseModel):
            partner_id: Optional[Union[int, dict]] = Many2OneField(
                "res.partner",
                description="Partner"
            )
        
        # Test with None
        model = TestModel(partner_id=None)
        assert model.partner_id is None
        
        # Test with integer ID
        model = TestModel(partner_id=123)
        assert model.partner_id == 123
        
        # Test with dict (simulating Odoo record)
        partner_data = {"id": 123, "name": "Test Partner"}
        model = TestModel(partner_id=partner_data)
        assert model.partner_id == partner_data


class TestOne2ManyField:
    """Test One2ManyField function."""

    def test_basic_creation(self):
        """Test basic One2ManyField creation."""
        field = One2ManyField("res.partner", "parent_id", description="Children")
        
        assert field.default_factory == list
        assert field.description == "Children"
        assert field.json_schema_extra["odoo_type"] == "one2many"
        assert field.json_schema_extra["odoo_relation"] == "res.partner"
        assert field.json_schema_extra["odoo_inverse"] == "parent_id"

    def test_field_validation(self):
        """Test One2ManyField validation in a model."""
        class TestModel(BaseModel):
            child_ids: List[Union[int, dict]] = One2ManyField(
                "res.partner",
                "parent_id",
                description="Children"
            )
        
        # Test with empty list (default)
        model = TestModel()
        assert model.child_ids == []
        
        # Test with list of IDs
        model = TestModel(child_ids=[123, 456])
        assert model.child_ids == [123, 456]
        
        # Test with list of dicts
        children_data = [
            {"id": 123, "name": "Child 1"},
            {"id": 456, "name": "Child 2"}
        ]
        model = TestModel(child_ids=children_data)
        assert model.child_ids == children_data


class TestMany2ManyField:
    """Test Many2ManyField function."""

    def test_basic_creation(self):
        """Test basic Many2ManyField creation."""
        field = Many2ManyField("product.category", description="Categories")
        
        assert field.default_factory == list
        assert field.description == "Categories"
        assert field.json_schema_extra["odoo_type"] == "many2many"
        assert field.json_schema_extra["odoo_relation"] == "product.category"

    def test_with_relation_table(self):
        """Test Many2ManyField with custom relation table."""
        field = Many2ManyField(
            "product.category",
            relation_table="product_category_rel",
            description="Categories"
        )
        
        assert field.json_schema_extra["odoo_relation_table"] == "product_category_rel"

    def test_field_validation(self):
        """Test Many2ManyField validation in a model."""
        class TestModel(BaseModel):
            category_ids: List[Union[int, dict]] = Many2ManyField(
                "product.category",
                description="Categories"
            )
        
        # Test with empty list (default)
        model = TestModel()
        assert model.category_ids == []
        
        # Test with list of IDs
        model = TestModel(category_ids=[1, 2, 3])
        assert model.category_ids == [1, 2, 3]


class TestSelectionField:
    """Test SelectionField function."""

    def test_basic_creation(self):
        """Test basic SelectionField creation."""
        choices = [("draft", "Draft"), ("confirmed", "Confirmed"), ("done", "Done")]
        field = SelectionField(choices, description="State")
        
        assert field.description == "State"
        assert field.json_schema_extra["odoo_type"] == "selection"
        assert field.json_schema_extra["odoo_choices"] == choices

    def test_field_validation(self):
        """Test SelectionField validation in a model."""
        choices = [("draft", "Draft"), ("confirmed", "Confirmed")]
        
        class TestModel(BaseModel):
            state: str = SelectionField(choices, description="State")
        
        # Test with valid choice
        model = TestModel(state="draft")
        assert model.state == "draft"
        
        # Test with another valid choice
        model = TestModel(state="confirmed")
        assert model.state == "confirmed"


class TestBinaryField:
    """Test BinaryField function."""

    def test_basic_creation(self):
        """Test basic BinaryField creation."""
        field = BinaryField(description="Image data")

        assert field.default is None
        assert field.description == "Image data"
        assert field.json_schema_extra["odoo_type"] == "binary"

    def test_field_validation(self):
        """Test BinaryField validation in a model."""
        class TestModel(BaseModel):
            image: Optional[bytes] = BinaryField(description="Image")

        # Test with None
        model = TestModel(image=None)
        assert model.image is None

        # Test with bytes
        image_data = b"fake_image_data"
        model = TestModel(image=image_data)
        assert model.image == image_data


class TestDateField:
    """Test DateField function."""

    def test_basic_creation(self):
        """Test basic DateField creation."""
        field = DateField(description="Birth date")

        assert field.default is None
        assert field.description == "Birth date"
        assert field.json_schema_extra["odoo_type"] == "date"

    def test_field_validation(self):
        """Test DateField validation in a model."""
        class TestModel(BaseModel):
            birth_date: Optional[date] = DateField(description="Birth date")

        # Test with None
        model = TestModel(birth_date=None)
        assert model.birth_date is None

        # Test with date
        test_date = date(2023, 1, 15)
        model = TestModel(birth_date=test_date)
        assert model.birth_date == test_date


class TestDateTimeField:
    """Test DateTimeField function."""

    def test_basic_creation(self):
        """Test basic DateTimeField creation."""
        field = DateTimeField(description="Creation date")

        assert field.default is None
        assert field.description == "Creation date"
        assert field.json_schema_extra["odoo_type"] == "datetime"

    def test_field_validation(self):
        """Test DateTimeField validation in a model."""
        class TestModel(BaseModel):
            create_date: Optional[datetime] = DateTimeField(
                description="Creation date"
            )

        # Test with None
        model = TestModel(create_date=None)
        assert model.create_date is None

        # Test with datetime
        test_datetime = datetime(2023, 1, 15, 10, 30, 45)
        model = TestModel(create_date=test_datetime)
        assert model.create_date == test_datetime


class TestMonetaryField:
    """Test MonetaryField function."""

    def test_basic_creation(self):
        """Test basic MonetaryField creation."""
        field = MonetaryField(description="Total amount")

        assert field.default == Decimal("0.0")
        assert field.description == "Total amount"
        assert field.json_schema_extra["odoo_type"] == "monetary"
        assert field.json_schema_extra["odoo_currency_field"] == "currency_id"

    def test_custom_currency_field(self):
        """Test MonetaryField with custom currency field."""
        field = MonetaryField(
            currency_field="company_currency_id",
            description="Company amount"
        )

        assert field.json_schema_extra["odoo_currency_field"] == (
            "company_currency_id"
        )

    def test_field_validation(self):
        """Test MonetaryField validation in a model."""
        class TestModel(BaseModel):
            amount_total: Decimal = MonetaryField(description="Total")

        # Test with default
        model = TestModel()
        assert model.amount_total == Decimal("0.0")

        # Test with Decimal
        model = TestModel(amount_total=Decimal("123.45"))
        assert model.amount_total == Decimal("123.45")


class TestFloatField:
    """Test FloatField function."""

    def test_basic_creation(self):
        """Test basic FloatField creation."""
        field = FloatField(description="Weight")

        assert field.default == 0.0
        assert field.description == "Weight"
        assert field.json_schema_extra["odoo_type"] == "float"

    def test_with_digits(self):
        """Test FloatField with precision digits."""
        field = FloatField(digits=(16, 3), description="Weight")

        assert field.json_schema_extra["odoo_digits"] == (16, 3)

    def test_field_validation(self):
        """Test FloatField validation in a model."""
        class TestModel(BaseModel):
            weight: float = FloatField(description="Weight")

        # Test with default
        model = TestModel()
        assert model.weight == 0.0

        # Test with float
        model = TestModel(weight=12.345)
        assert model.weight == 12.345


class TestIntegerField:
    """Test IntegerField function."""

    def test_basic_creation(self):
        """Test basic IntegerField creation."""
        field = IntegerField(description="Sequence")

        assert field.default == 0
        assert field.description == "Sequence"
        assert field.json_schema_extra["odoo_type"] == "integer"

    def test_field_validation(self):
        """Test IntegerField validation in a model."""
        class TestModel(BaseModel):
            sequence: int = IntegerField(description="Sequence")

        # Test with default
        model = TestModel()
        assert model.sequence == 0

        # Test with integer
        model = TestModel(sequence=42)
        assert model.sequence == 42


class TestTextField:
    """Test TextField function."""

    def test_basic_creation(self):
        """Test basic TextField creation."""
        field = TextField(description="Description")

        assert field.default is None
        assert field.description == "Description"
        assert field.json_schema_extra["odoo_type"] == "text"

    def test_field_validation(self):
        """Test TextField validation in a model."""
        class TestModel(BaseModel):
            description: Optional[str] = TextField(description="Description")

        # Test with None
        model = TestModel(description=None)
        assert model.description is None

        # Test with text
        long_text = "This is a very long text description..."
        model = TestModel(description=long_text)
        assert model.description == long_text


class TestCharField:
    """Test CharField function."""

    def test_basic_creation(self):
        """Test basic CharField creation."""
        field = CharField(description="Name")

        assert field.description == "Name"
        assert field.json_schema_extra["odoo_type"] == "char"

    def test_with_max_length(self):
        """Test CharField with max_length."""
        field = CharField(max_length=100, description="Name")

        # FieldInfo stores max_length in constraints, not as direct attribute
        assert field.json_schema_extra["odoo_size"] == 100

    def test_field_validation(self):
        """Test CharField validation in a model."""
        class TestModel(BaseModel):
            name: str = CharField(max_length=50, description="Name")

        # Test with valid string
        model = TestModel(name="Test Name")
        assert model.name == "Test Name"


class TestBooleanField:
    """Test BooleanField function."""

    def test_basic_creation(self):
        """Test basic BooleanField creation."""
        field = BooleanField(description="Active")

        assert field.default is False
        assert field.description == "Active"
        assert field.json_schema_extra["odoo_type"] == "boolean"

    def test_field_validation(self):
        """Test BooleanField validation in a model."""
        class TestModel(BaseModel):
            active: bool = BooleanField(description="Active")

        # Test with default
        model = TestModel()
        assert model.active is False

        # Test with True
        model = TestModel(active=True)
        assert model.active is True


class TestFieldIntegration:
    """Test integration between different field types."""

    def test_complex_model_with_all_fields(self):
        """Test a complex model using various field types."""
        class ComplexModel(BaseModel):
            # Basic fields
            name: str = CharField(max_length=100, description="Name")
            active: bool = BooleanField(description="Active")
            sequence: int = IntegerField(description="Sequence")
            weight: float = FloatField(digits=(16, 3), description="Weight")

            # Date fields
            birth_date: Optional[date] = DateField(description="Birth date")
            create_date: Optional[datetime] = DateTimeField(
                description="Creation date"
            )

            # Monetary and text fields
            amount_total: Decimal = MonetaryField(description="Total")
            description: Optional[str] = TextField(description="Description")

            # Selection field
            state: str = SelectionField([
                ("draft", "Draft"),
                ("confirmed", "Confirmed")
            ], description="State")

            # Relationship fields
            partner_id: Optional[Union[int, dict]] = Many2OneField(
                "res.partner", description="Partner"
            )
            child_ids: List[Union[int, dict]] = One2ManyField(
                "res.partner", "parent_id", description="Children"
            )

        # Test model creation with all fields
        model_data = {
            "name": "Test Model",
            "active": True,
            "sequence": 10,
            "weight": 12.345,
            "birth_date": date(1990, 1, 1),
            "create_date": datetime(2023, 1, 1, 12, 0, 0),
            "amount_total": Decimal("999.99"),
            "description": "Test description",
            "state": "draft",
            "partner_id": 123,
            "child_ids": [456, 789]
        }

        model = ComplexModel(**model_data)

        # Verify all fields
        assert model.name == "Test Model"
        assert model.active is True
        assert model.sequence == 10
        assert model.weight == 12.345
        assert model.birth_date == date(1990, 1, 1)
        assert model.create_date == datetime(2023, 1, 1, 12, 0, 0)
        assert model.amount_total == Decimal("999.99")
        assert model.description == "Test description"
        assert model.state == "draft"
        assert model.partner_id == 123
        assert model.child_ids == [456, 789]

    def test_field_serialization(self):
        """Test that fields serialize correctly."""
        class TestModel(BaseModel):
            name: str = CharField(description="Name")
            amount: Decimal = MonetaryField(description="Amount")
            create_date: Optional[datetime] = DateTimeField(description="Date")

        model = TestModel(
            name="Test",
            amount=Decimal("123.45"),
            create_date=datetime(2023, 1, 1, 12, 0, 0)
        )

        # Test model_dump
        data = model.model_dump()
        assert data["name"] == "Test"
        assert data["amount"] == Decimal("123.45")
        assert data["create_date"] == datetime(2023, 1, 1, 12, 0, 0)

    def test_field_json_schema_extra(self):
        """Test that all fields have proper Odoo metadata."""
        # Test various field types
        fields_to_test = [
            (CharField(description="Name"), "char"),
            (IntegerField(description="Sequence"), "integer"),
            (FloatField(description="Weight"), "float"),
            (BooleanField(description="Active"), "boolean"),
            (DateField(description="Date"), "date"),
            (DateTimeField(description="DateTime"), "datetime"),
            (TextField(description="Text"), "text"),
            (BinaryField(description="Binary"), "binary"),
            (MonetaryField(description="Monetary"), "monetary"),
            (
                SelectionField([("a", "A")], description="Selection"),
                "selection"
            ),
            (Many2OneField("res.partner", description="Partner"), "many2one"),
            (
                One2ManyField(
                    "res.partner", "parent_id", description="Children"
                ),
                "one2many"
            ),
            (
                Many2ManyField("product.category", description="Categories"),
                "many2many"
            ),
        ]

        for field, expected_type in fields_to_test:
            assert field.json_schema_extra["odoo_type"] == expected_type
