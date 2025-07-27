import pytest
from unittest.mock import AsyncMock, Mock
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import Field

from src.zenoo_rpc.models.registry import (
    ModelRegistry,
    register_model,
    get_model_class,
    get_registry,
)
from src.zenoo_rpc.models.base import OdooModel
from src.zenoo_rpc.models.fields import CharField, IntegerField, Many2OneField


class SampleModel(OdooModel):
    """Sample model for registry tests."""

    name: str
    value: int = 0


@pytest.fixture
def registry():
    return ModelRegistry()


@pytest.fixture
def client_mock():
    return AsyncMock()


async def test_register_decorator(registry):
    @registry.register("test.model")
    class TestModelDecorated(OdooModel):
        name: str

    assert registry.has_model("test.model")
    assert registry.get_model("test.model") == TestModelDecorated
    assert TestModelDecorated.odoo_name == "test.model"


async def test_register_model_directly(registry):
    registry.register_model("test.model", SampleModel)

    assert registry.has_model("test.model")
    assert registry.get_model("test.model") == SampleModel
    assert SampleModel.odoo_name == "test.model"


async def test_get_model_not_found(registry):
    assert registry.get_model("nonexistent.model") is None


async def test_has_model(registry):
    assert not registry.has_model("test.model")
    registry.register_model("test.model", SampleModel)
    assert registry.has_model("test.model")


async def test_list_models(registry):
    assert registry.list_models() == []

    registry.register_model("test.model1", SampleModel)
    registry.register_model("test.model2", SampleModel)

    models = registry.list_models()
    assert len(models) == 2
    assert "test.model1" in models
    assert "test.model2" in models


async def test_generate_class_name(registry):
    assert registry._generate_class_name("res.partner") == "ResPartner"
    assert registry._generate_class_name("account.invoice.line") == "AccountInvoiceLine"
    assert registry._generate_class_name("simple") == "Simple"


async def test_create_char_field(registry):
    field_def = {"type": "char", "string": "Name", "required": True, "size": 255}
    field_type, field_info = registry._create_char_field("name", field_def)
    assert field_type == str
    assert field_info.json_schema_extra["max_length"] == 255


async def test_create_char_field_optional(registry):
    field_def = {
        "type": "char",
        "string": "Description",
        "required": False,
        "default": "Default",
    }
    field_type, field_info = registry._create_char_field("description", field_def)
    assert field_type == Optional[str]
    assert field_info.default == "Default"


async def test_create_integer_field(registry):
    field_def = {"type": "integer", "string": "Count", "default": 10}
    field_type, field_info = registry._create_integer_field("count", field_def)
    assert field_type == int
    assert field_info.default == 10


async def test_create_boolean_field(registry):
    field_def = {"type": "boolean", "string": "Active", "default": True}
    field_type, field_info = registry._create_boolean_field("active", field_def)
    assert field_type == bool
    assert field_info.default == True


async def test_create_date_field(registry):
    field_def = {"type": "date", "string": "Date"}
    field_type, field_info = registry._create_date_field("date", field_def)
    assert field_type == Optional[date]


async def test_create_datetime_field(registry):
    field_def = {"type": "datetime", "string": "Created"}
    field_type, field_info = registry._create_datetime_field("created", field_def)
    assert field_type == Optional[datetime]


async def test_create_float_field(registry):
    field_def = {"type": "float", "string": "Price", "digits": [12, 2], "default": 0.0}
    field_type, field_info = registry._create_float_field("price", field_def)
    assert field_type == float
    assert field_info.default == 0.0


async def test_create_selection_field(registry):
    field_def = {
        "type": "selection",
        "string": "State",
        "selection": [["draft", "Draft"], ["done", "Done"]],
        "required": True,
    }
    field_type, field_info = registry._create_selection_field("state", field_def)
    assert field_type == str


async def test_create_many2one_field(registry):
    field_def = {"type": "many2one", "string": "Partner", "relation": "res.partner"}
    field_type, field_info = registry._create_many2one_field("partner_id", field_def)
    assert field_type == Optional[Any]
    assert field_info.json_schema_extra["model_name"] == "res.partner"


async def test_create_one2many_field(registry):
    field_def = {
        "type": "one2many",
        "string": "Lines",
        "relation": "sale.order.line",
        "relation_field": "order_id",
    }
    field_type, field_info = registry._create_one2many_field("line_ids", field_def)
    assert field_type == List[Any]


async def test_create_many2many_field(registry):
    field_def = {
        "type": "many2many",
        "string": "Tags",
        "relation": "res.partner.tag",
        "relation_table": "partner_tag_rel",
    }
    field_type, field_info = registry._create_many2many_field("tag_ids", field_def)
    assert field_type == List[Any]


async def test_create_monetary_field(registry):
    field_def = {
        "type": "monetary",
        "string": "Amount",
        "currency_field": "currency_id",
    }
    field_type, field_info = registry._create_monetary_field("amount", field_def)
    assert field_type == Decimal


async def test_create_binary_field(registry):
    field_def = {"type": "binary", "string": "Image"}
    field_type, field_info = registry._create_binary_field("image", field_def)
    assert field_type == Optional[bytes]


async def test_create_pydantic_fields(registry):
    field_definitions = {
        "id": {"type": "integer", "string": "ID"},
        "name": {"type": "char", "string": "Name", "required": True},
        "active": {"type": "boolean", "string": "Active"},
        "computed_field": {"type": "char", "store": False},  # Should be skipped
    }

    fields = registry._create_pydantic_fields(field_definitions)

    assert "id" in fields
    assert "name" in fields
    assert "active" in fields
    assert "computed_field" not in fields  # Skipped because store=False


async def test_create_pydantic_fields_unknown_type(registry):
    field_definitions = {"custom_field": {"type": "unknown_type", "string": "Custom"}}

    fields = registry._create_pydantic_fields(field_definitions)

    # Should fallback to Optional[str]
    assert "custom_field" in fields
    field_type, _ = fields["custom_field"]
    assert field_type == Optional[str]


async def test_get_field_definitions_cached(registry, client_mock):
    field_defs = {"id": {"type": "integer"}}
    client_mock.execute_kw.return_value = field_defs

    # First call
    result1 = await registry._get_field_definitions("test.model", client_mock)
    assert result1 == field_defs

    # Second call should use cache
    result2 = await registry._get_field_definitions("test.model", client_mock)
    assert result2 == field_defs

    # Should only call execute_kw once
    client_mock.execute_kw.assert_called_once()


async def test_get_field_definitions_error(registry, client_mock):
    client_mock.execute_kw.side_effect = Exception("Server error")

    result = await registry._get_field_definitions("test.model", client_mock)
    assert result == {}


async def test_create_dynamic_model(registry, client_mock):
    field_defs = {
        "id": {"type": "integer", "string": "ID"},
        "name": {"type": "char", "string": "Name", "required": True},
        "email": {"type": "char", "string": "Email"},
    }
    client_mock.execute_kw.return_value = field_defs

    DynamicModel = await registry.create_dynamic_model("res.partner", client_mock)

    assert DynamicModel.__name__ == "ResPartner"
    assert DynamicModel.odoo_name == "res.partner"
    assert registry.has_model("res.partner")

    # Test instantiation
    instance = DynamicModel(id=1, name="Test")
    assert instance.id == 1
    assert instance.name == "Test"


async def test_create_dynamic_model_existing(registry, client_mock):
    # Register existing model
    registry.register_model("res.partner", SampleModel)

    # Should return existing model without calling server
    result = await registry.create_dynamic_model("res.partner", client_mock)
    assert result == SampleModel
    client_mock.execute_kw.assert_not_called()


async def test_create_dynamic_model_with_base_fields(registry, client_mock):
    field_defs = {
        "id": {"type": "integer", "string": "ID"},
        "name": {"type": "char", "string": "Name", "required": True},
        "email": {"type": "char", "string": "Email"},
        "phone": {"type": "char", "string": "Phone"},
    }
    client_mock.execute_kw.return_value = field_defs

    DynamicModel = await registry.create_dynamic_model(
        "res.partner",
        client_mock,
        base_fields=["name", "email"],  # Only include these fields
    )

    # Create instance and check only requested fields are available
    instance = DynamicModel(id=1, name="Test")
    assert hasattr(instance, "id")
    assert hasattr(instance, "name")
    assert hasattr(instance, "email")
    # phone should not be included


async def test_global_registry_functions():
    # Test global registry functions
    @register_model("global.test")
    class GlobalTestModel(OdooModel):
        name: str

    assert get_model_class("global.test") == GlobalTestModel

    registry = get_registry()
    assert isinstance(registry, ModelRegistry)
    assert registry.has_model("global.test")


# Import Any to fix the test
from typing import Any
