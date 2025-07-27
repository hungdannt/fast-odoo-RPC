"""
Model registry for dynamic model creation and management.

This module provides a registry system for Odoo models, allowing for
dynamic model creation based on server field definitions and
efficient model lookup and caching.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Set
from weakref import WeakValueDictionary
import logging
from datetime import date, datetime
from decimal import Decimal

from pydantic import create_model, Field
from pydantic.fields import FieldInfo

from .base import OdooModel
from .fields import (
    CharField,
    TextField,
    IntegerField,
    FloatField,
    BooleanField,
    DateField,
    DateTimeField,
    MonetaryField,
    SelectionField,
    Many2OneField,
    One2ManyField,
    Many2ManyField,
    BinaryField,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=OdooModel)


class ModelRegistry:
    """Registry for managing Odoo model classes.

    This class provides a centralized registry for Odoo model classes,
    supporting both manually defined models and dynamically created ones
    based on server field definitions.

    Features:
    - Dynamic model creation from server field definitions
    - Model caching and efficient lookup
    - Field type mapping from Odoo to Pydantic
    - Relationship resolution and validation
    - Model inheritance support

    Example:
        >>> registry = ModelRegistry()
        >>>
        >>> # Register a manually defined model
        >>> @registry.register("res.partner")
        >>> class ResPartner(OdooModel):
        ...     name: str
        ...     email: Optional[str] = None
        >>>
        >>> # Get a model class
        >>> PartnerClass = registry.get_model("res.partner")
        >>> partner = PartnerClass(id=1, name="Test")
    """

    def __init__(self):
        """Initialize the model registry."""
        self._models: Dict[str, Type[OdooModel]] = {}
        self._field_cache: Dict[str, Dict[str, Any]] = {}
        self._weak_models: WeakValueDictionary = WeakValueDictionary()

        # Field type mapping from Odoo to Pydantic
        self._field_type_mapping = {
            "char": self._create_char_field,
            "text": self._create_text_field,
            "integer": self._create_integer_field,
            "float": self._create_float_field,
            "boolean": self._create_boolean_field,
            "date": self._create_date_field,
            "datetime": self._create_datetime_field,
            "monetary": self._create_monetary_field,
            "selection": self._create_selection_field,
            "many2one": self._create_many2one_field,
            "one2many": self._create_one2many_field,
            "many2many": self._create_many2many_field,
            "binary": self._create_binary_field,
        }

    def register(self, model_name: str) -> callable:
        """Decorator to register a model class.

        Args:
            model_name: The Odoo model name (e.g., "res.partner")

        Returns:
            Decorator function

        Example:
            >>> @registry.register("res.partner")
            >>> class ResPartner(OdooModel):
            ...     name: str
        """

        def decorator(cls: Type[OdooModel]) -> Type[OdooModel]:
            # Set the Odoo model name
            cls.odoo_name = model_name

            # Register the model
            self._models[model_name] = cls

            logger.debug(f"Registered model {model_name} -> {cls.__name__}")
            return cls

        return decorator

    def register_model(self, model_name: str, model_class: Type[OdooModel]) -> None:
        """Register a model class directly.

        Args:
            model_name: The Odoo model name
            model_class: The model class to register
        """
        model_class.odoo_name = model_name
        self._models[model_name] = model_class
        logger.debug(f"Registered model {model_name} -> {model_class.__name__}")

    def get_model(self, model_name: str) -> Optional[Type[OdooModel]]:
        """Get a registered model class.

        Args:
            model_name: The Odoo model name

        Returns:
            Model class or None if not found
        """
        return self._models.get(model_name)

    def has_model(self, model_name: str) -> bool:
        """Check if a model is registered.

        Args:
            model_name: The Odoo model name

        Returns:
            True if model is registered, False otherwise
        """
        return model_name in self._models

    def list_models(self) -> List[str]:
        """Get a list of all registered model names.

        Returns:
            List of model names
        """
        return list(self._models.keys())

    async def create_dynamic_model(
        self, model_name: str, client: Any, base_fields: Optional[List[str]] = None
    ) -> Type[OdooModel]:
        """Create a model class dynamically from server field definitions.

        Args:
            model_name: The Odoo model name
            client: OdooFlow client for field introspection
            base_fields: Optional list of fields to include (None for all)

        Returns:
            Dynamically created model class
        """
        # Check if we already have this model
        if model_name in self._models:
            return self._models[model_name]

        # Get field definitions from server
        field_definitions = await self._get_field_definitions(model_name, client)

        # Filter fields if base_fields is specified
        if base_fields:
            field_definitions = {
                name: definition
                for name, definition in field_definitions.items()
                if name in base_fields or name == "id"
            }

        # Create Pydantic fields
        pydantic_fields = self._create_pydantic_fields(field_definitions)

        # Create the model class
        class_name = self._generate_class_name(model_name)

        # Create the dynamic model
        DynamicModel = create_model(class_name, __base__=OdooModel, **pydantic_fields)

        # Set the Odoo model name
        DynamicModel.odoo_name = model_name

        # Register the model
        self._models[model_name] = DynamicModel

        logger.info(f"Created dynamic model {model_name} -> {class_name}")
        return DynamicModel

    async def _get_field_definitions(
        self, model_name: str, client: Any
    ) -> Dict[str, Dict[str, Any]]:
        """Get field definitions from the Odoo server.

        Args:
            model_name: The Odoo model name
            client: OdooFlow client

        Returns:
            Dictionary of field definitions
        """
        # Check cache first
        if model_name in self._field_cache:
            return self._field_cache[model_name]

        try:
            # Get field definitions from server
            field_definitions = await client.execute_kw(
                model_name, "fields_get", [], {}
            )

            # Cache the definitions
            self._field_cache[model_name] = field_definitions

            return field_definitions

        except Exception as e:
            logger.error(f"Failed to get field definitions for {model_name}: {e}")
            return {}

    def _create_pydantic_fields(
        self, field_definitions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Convert Odoo field definitions to Pydantic fields.

        Args:
            field_definitions: Field definitions from Odoo

        Returns:
            Dictionary of Pydantic field definitions
        """
        pydantic_fields = {}

        for field_name, field_def in field_definitions.items():
            # Skip computed fields without store
            if field_def.get("store") is False:
                continue

            # Get field type
            field_type = field_def.get("type", "char")

            # Create Pydantic field
            if field_type in self._field_type_mapping:
                try:
                    pydantic_field = self._field_type_mapping[field_type](
                        field_name, field_def
                    )
                    pydantic_fields[field_name] = pydantic_field
                except Exception as e:
                    logger.warning(f"Failed to create field {field_name}: {e}")
                    # Fallback to string field
                    pydantic_fields[field_name] = (Optional[str], None)
            else:
                logger.warning(f"Unknown field type {field_type} for {field_name}")
                # Fallback to string field
                pydantic_fields[field_name] = (Optional[str], None)

        return pydantic_fields

    def _generate_class_name(self, model_name: str) -> str:
        """Generate a Python class name from Odoo model name.

        Args:
            model_name: Odoo model name (e.g., "res.partner")

        Returns:
            Python class name (e.g., "ResPartner")
        """
        # Convert "res.partner" to "ResPartner"
        parts = model_name.split(".")
        return "".join(word.capitalize() for word in parts)

    # Field creation methods
    def _create_char_field(self, field_name: str, field_def: Dict[str, Any]) -> tuple:
        """Create a char field."""
        required = field_def.get("required", False)
        size = field_def.get("size")
        default = field_def.get("default")

        field_info = CharField(
            max_length=size, description=field_def.get("string", field_name)
        )

        if required:
            return (str, field_info)
        else:
            return (
                Optional[str],
                Field(default=default, **field_info.json_schema_extra),
            )

    def _create_text_field(self, field_name: str, field_def: Dict[str, Any]) -> tuple:
        """Create a text field."""
        required = field_def.get("required", False)
        default = field_def.get("default")

        field_info = TextField(description=field_def.get("string", field_name))

        if required:
            return (str, field_info)
        else:
            return (
                Optional[str],
                Field(default=default, **field_info.json_schema_extra),
            )

    def _create_integer_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create an integer field."""
        default = field_def.get("default", 0)
        field_info = IntegerField(description=field_def.get("string", field_name))
        return (int, Field(default=default, **field_info.json_schema_extra))

    def _create_float_field(self, field_name: str, field_def: Dict[str, Any]) -> tuple:
        """Create a float field."""
        default = field_def.get("default", 0.0)
        digits = field_def.get("digits")

        field_info = FloatField(
            digits=digits, description=field_def.get("string", field_name)
        )
        return (float, Field(default=default, **field_info.json_schema_extra))

    def _create_boolean_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create a boolean field."""
        default = field_def.get("default", False)
        field_info = BooleanField(description=field_def.get("string", field_name))
        return (bool, Field(default=default, **field_info.json_schema_extra))

    def _create_date_field(self, field_name: str, field_def: Dict[str, Any]) -> tuple:
        """Create a date field."""
        field_info = DateField(description=field_def.get("string", field_name))
        return (Optional[date], field_info)

    def _create_datetime_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create a datetime field."""
        field_info = DateTimeField(description=field_def.get("string", field_name))
        return (Optional[datetime], field_info)

    def _create_monetary_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create a monetary field."""
        currency_field = field_def.get("currency_field", "currency_id")
        field_info = MonetaryField(
            currency_field=currency_field,
            description=field_def.get("string", field_name),
        )
        return (Decimal, field_info)

    def _create_selection_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create a selection field."""
        selection = field_def.get("selection", [])
        required = field_def.get("required", False)

        field_info = SelectionField(
            choices=selection, description=field_def.get("string", field_name)
        )

        if required:
            return (str, field_info)
        else:
            return (Optional[str], field_info)

    def _create_many2one_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create a many2one field."""
        relation = field_def.get("relation", "")
        field_info = Many2OneField(
            model_name=relation, description=field_def.get("string", field_name)
        )
        return (Optional[Any], field_info)  # Will be resolved later

    def _create_one2many_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create a one2many field."""
        relation = field_def.get("relation", "")
        relation_field = field_def.get("relation_field", "")

        field_info = One2ManyField(
            model_name=relation,
            inverse_field=relation_field,
            description=field_def.get("string", field_name),
        )
        return (List[Any], field_info)  # Will be resolved later

    def _create_many2many_field(
        self, field_name: str, field_def: Dict[str, Any]
    ) -> tuple:
        """Create a many2many field."""
        relation = field_def.get("relation", "")
        relation_table = field_def.get("relation_table")

        field_info = Many2ManyField(
            model_name=relation,
            relation_table=relation_table,
            description=field_def.get("string", field_name),
        )
        return (List[Any], field_info)  # Will be resolved later

    def _create_binary_field(self, field_name: str, field_def: Dict[str, Any]) -> tuple:
        """Create a binary field."""
        field_info = BinaryField(description=field_def.get("string", field_name))
        return (Optional[bytes], field_info)


# Global registry instance
_global_registry = ModelRegistry()


def register_model(model_name: str) -> callable:
    """Decorator to register a model in the global registry.

    Args:
        model_name: The Odoo model name

    Returns:
        Decorator function
    """
    return _global_registry.register(model_name)


def get_model_class(model_name: str) -> Optional[Type[OdooModel]]:
    """Get a model class from the global registry.

    Args:
        model_name: The Odoo model name

    Returns:
        Model class or None if not found
    """
    return _global_registry.get_model(model_name)


def get_registry() -> ModelRegistry:
    """Get the global model registry.

    Returns:
        The global ModelRegistry instance
    """
    return _global_registry
