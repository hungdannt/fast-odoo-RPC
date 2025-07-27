import pytest
from unittest.mock import MagicMock
from src.zenoo_rpc.models.base import OdooModel
from src.zenoo_rpc.models.common import ResPartner
from pydantic import Field, ValidationError


def test_odoo_model_basic():
    """Test basic OdooModel functionality."""
    partner = ResPartner(
        id=1, name="Test Partner", email="test@example.com", is_company=True
    )

    assert partner.id == 1
    assert partner.name == "Test Partner"
    assert partner.email == "test@example.com"
    assert partner.is_company is True


def test_odoo_model_validation():
    """Test OdooModel validation."""
    # ID is required
    with pytest.raises(ValidationError):
        ResPartner(name="Test")

    # Email validation
    with pytest.raises(ValidationError):
        ResPartner(id=1, name="Test", email="invalid-email")


def test_odoo_model_with_client():
    """Test OdooModel with client."""
    client = MagicMock()
    partner = ResPartner(id=1, name="Test Partner", client=client)

    assert partner.client == client
    assert partner.loaded_fields == {"id", "name", "client"}


def test_odoo_model_loaded_fields():
    """Test tracking loaded fields."""
    partner = ResPartner(id=1, name="Test Partner", email="test@example.com")

    assert partner.is_field_loaded("id")
    assert partner.is_field_loaded("name")
    assert partner.is_field_loaded("email")
    assert not partner.is_field_loaded("phone")

    loaded = partner.get_loaded_fields()
    assert "id" in loaded
    assert "name" in loaded
    assert "email" in loaded


def test_odoo_model_to_odoo_dict():
    """Test converting to Odoo dict format."""
    partner = ResPartner(
        id=1, name="Test Partner", email="test@example.com", is_company=True
    )

    # Convert to dict (excluding ID for create operations)
    odoo_dict = partner.to_odoo_dict()

    assert "id" not in odoo_dict  # ID excluded by default
    assert odoo_dict["name"] == "Test Partner"
    assert odoo_dict["email"] == "test@example.com"
    assert odoo_dict["is_company"] is True


def test_odoo_model_get_odoo_name():
    """Test getting Odoo model name."""
    assert ResPartner.get_odoo_name() == "res.partner"

    partner = ResPartner(id=1, name="Test")
    # Instance should also have access to class method
    assert partner.get_odoo_name() == "res.partner"


def test_odoo_model_repr_str():
    """Test string representations."""
    partner = ResPartner(id=1, name="Test Company")

    assert repr(partner) == "ResPartner(id=1, name='Test Company')"
    assert str(partner) == "Test Company"

    # Without name
    partner_no_name = ResPartner(id=2, email="test@example.com")
    assert repr(partner_no_name) == "ResPartner(id=2)"
    assert str(partner_no_name) == "ResPartner(2)"


def test_odoo_model_relationship_manager():
    """Test relationship manager initialization."""
    client = MagicMock()
    partner = ResPartner(id=1, name="Test Partner", client=client)

    assert partner.relationship_manager is not None
    assert partner.relationship_manager.client == client


def test_odoo_model_custom_subclass():
    """Test creating custom OdooModel subclass."""

    class CustomModel(OdooModel):
        custom_field: str = Field(description="Custom field")

    # Should inherit OdooModel validation (id required)
    with pytest.raises(ValidationError):
        CustomModel(custom_field="value")

    # Valid instance
    instance = CustomModel(id=1, custom_field="test value")
    assert instance.id == 1
    assert instance.custom_field == "test value"


def test_odoo_model_optional_fields():
    """Test optional field handling."""
    # Create with minimal required fields
    partner = ResPartner(id=1, name="Minimal Partner")

    # Optional fields should have defaults
    assert partner.email is None
    assert partner.phone is None
    assert partner.is_company is False

    # Only provided fields should be in loaded_fields
    loaded = partner.get_loaded_fields()
    assert "id" in loaded
    assert "name" in loaded
    assert "email" not in loaded  # Not provided


def test_odoo_model_refresh_save_placeholders():
    """Test refresh and save placeholder methods."""
    client = MagicMock()
    partner = ResPartner(id=1, name="Test", client=client)

    # These are placeholders, should just pass
    partner.refresh()
    partner.save()

    # Without client should raise
    partner_no_client = ResPartner(id=1, name="Test")

    with pytest.raises(ValueError, match="Cannot refresh"):
        partner_no_client.refresh()

    with pytest.raises(ValueError, match="Cannot save"):
        partner_no_client.save()
