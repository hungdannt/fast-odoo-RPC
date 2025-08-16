"""
Specialized field types for Odoo models.

This module provides Pydantic field types that correspond to Odoo field types,
with proper validation and serialization behavior.
"""

from typing import Any, Dict, List, Optional, Union, Tuple, Type, TypeVar, TYPE_CHECKING
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pydantic import Field, field_validator, ConfigDict
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from .base import OdooModel
    from .relationships import LazyRelationship

T = TypeVar("T")


class RelationshipDescriptor:
    """Base descriptor for relationship fields with lazy loading."""

    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        self.field_name = field_name
        self.comodel_name = comodel_name
        self.field_info = field_info
        self.is_collection = False

    def __get__(self, instance: Optional["OdooModel"], owner: Type["OdooModel"]) -> Any:
        if instance is None:
            return self

        # Check if relationship is already loaded
        if hasattr(instance, "_loaded_relationships"):
            if self.field_name in instance._loaded_relationships:
                return instance._loaded_relationships[self.field_name]
        else:
            instance._loaded_relationships = {}

        # Get raw field value from instance __dict__ to avoid recursion
        raw_value = instance.__dict__.get(self.field_name, None)
        if raw_value is None:
            return None if not self.is_collection else []

        # If it's already a model instance, return it
        if hasattr(raw_value, "id") and hasattr(raw_value, "odoo_name"):
            return raw_value

        # If it's an ID or list of IDs, create lazy relationship
        if isinstance(raw_value, (int, list)):
            from .relationships import LazyRelationship

            lazy_rel = LazyRelationship(
                parent_record=instance,
                field_name=self.field_name,
                relation_model=self.comodel_name,
                relation_ids=raw_value,
                client=instance.client,
                is_collection=self.is_collection,
            )

            # Cache the lazy relationship
            instance._loaded_relationships[self.field_name] = lazy_rel
            return lazy_rel

        return raw_value

    def __set__(self, instance: "OdooModel", value: Any) -> None:
        # Store raw value in instance __dict__
        instance.__dict__[self.field_name] = value

        # Clear cached relationship
        if hasattr(instance, "_loaded_relationships"):
            instance._loaded_relationships.pop(self.field_name, None)


class Many2OneDescriptor(RelationshipDescriptor):
    """Descriptor for Many2One relationships."""

    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        super().__init__(field_name, comodel_name, field_info)
        self.is_collection = False


class One2ManyDescriptor(RelationshipDescriptor):
    """Descriptor for One2Many relationships."""

    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        super().__init__(field_name, comodel_name, field_info)
        self.is_collection = True


class Many2ManyDescriptor(RelationshipDescriptor):
    """Descriptor for Many2Many relationships."""

    def __init__(self, field_name: str, comodel_name: str, field_info: FieldInfo):
        super().__init__(field_name, comodel_name, field_info)
        self.is_collection = True


def Many2OneField(model_name: str, description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Many2one field for Odoo relationships.

    Args:
        model_name: The target Odoo model name (e.g., "res.partner")
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Many2one relationships

    Example:
        >>> company_id: Optional[Union[int, ResPartner]] = Many2OneField(
        ...     "res.partner",
        ...     description="Parent company"
        ... )
    """
    from typing import Union

    return Field(
        default=None,
        description=description,
        json_schema_extra={
            "odoo_type": "many2one",
            "odoo_relation": model_name,
            **kwargs,
        },
    )


def One2ManyField(
    model_name: str, inverse_field: str, description: str = "", **kwargs: Any
) -> FieldInfo:
    """Create a One2many field for Odoo relationships.

    Args:
        model_name: The target Odoo model name
        inverse_field: The field name in the target model that points back
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for One2many relationships

    Example:
        >>> child_ids: List[ResPartner] = One2ManyField(
        ...     "res.partner",
        ...     "parent_id",
        ...     description="Child companies"
        ... )
    """
    return Field(
        default_factory=list,
        description=description,
        json_schema_extra={
            "odoo_type": "one2many",
            "odoo_relation": model_name,
            "odoo_inverse": inverse_field,
            **kwargs,
        },
    )


def Many2ManyField(
    model_name: str,
    relation_table: Optional[str] = None,
    description: str = "",
    **kwargs: Any,
) -> FieldInfo:
    """Create a Many2many field for Odoo relationships.

    Args:
        model_name: The target Odoo model name
        relation_table: Optional relation table name
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Many2many relationships

    Example:
        >>> category_ids: List[ProductCategory] = Many2ManyField(
        ...     "product.category",
        ...     description="Product categories"
        ... )
    """
    extra = {"odoo_type": "many2many", "odoo_relation": model_name, **kwargs}
    if relation_table:
        extra["odoo_relation_table"] = relation_table

    return Field(default_factory=list, description=description, json_schema_extra=extra)


def SelectionField(
    choices: List[Tuple[str, str]], description: str = "", **kwargs: Any
) -> FieldInfo:
    """Create a Selection field for Odoo choice fields.

    Args:
        choices: List of (value, label) tuples
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Selection fields

    Example:
        >>> state: str = SelectionField([
        ...     ("draft", "Draft"),
        ...     ("confirmed", "Confirmed"),
        ...     ("done", "Done")
        ... ], description="Record state")
    """
    return Field(
        description=description,
        json_schema_extra={"odoo_type": "selection", "odoo_choices": choices, **kwargs},
    )


def BinaryField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Binary field for file/image data.

    Args:
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Binary fields

    Example:
        >>> image: Optional[bytes] = BinaryField(
        ...     description="Product image"
        ... )
    """
    return Field(
        default=None,
        description=description,
        json_schema_extra={"odoo_type": "binary", **kwargs},
    )


def DateField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Date field with proper validation.

    Args:
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Date fields

    Example:
        >>> birth_date: Optional[date] = DateField(
        ...     description="Date of birth"
        ... )
    """
    return Field(
        default=None,
        description=description,
        json_schema_extra={"odoo_type": "date", **kwargs},
    )


def DateTimeField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a DateTime field with proper validation.

    Args:
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for DateTime fields

    Example:
        >>> create_date: Optional[datetime] = DateTimeField(
        ...     description="Creation date"
        ... )
    """
    return Field(
        default=None,
        description=description,
        json_schema_extra={"odoo_type": "datetime", **kwargs},
    )


def MonetaryField(
    currency_field: str = "currency_id", description: str = "", **kwargs: Any
) -> FieldInfo:
    """Create a Monetary field for currency amounts.

    Args:
        currency_field: Name of the currency field
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Monetary fields

    Example:
        >>> amount_total: Decimal = MonetaryField(
        ...     description="Total amount"
        ... )
    """
    return Field(
        default=Decimal("0.0"),
        description=description,
        json_schema_extra={
            "odoo_type": "monetary",
            "odoo_currency_field": currency_field,
            **kwargs,
        },
    )


def FloatField(
    digits: Optional[Tuple[int, int]] = None, description: str = "", **kwargs: Any
) -> FieldInfo:
    """Create a Float field with precision control.

    Args:
        digits: Tuple of (precision, scale) for decimal places
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Float fields

    Example:
        >>> weight: float = FloatField(
        ...     digits=(16, 3),
        ...     description="Product weight in kg"
        ... )
    """
    extra = {"odoo_type": "float", **kwargs}
    if digits:
        extra["odoo_digits"] = digits

    return Field(default=0.0, description=description, json_schema_extra=extra)


def IntegerField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create an Integer field.

    Args:
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Integer fields

    Example:
        >>> sequence: int = IntegerField(
        ...     description="Display sequence"
        ... )
    """
    return Field(
        default=0,
        description=description,
        json_schema_extra={"odoo_type": "integer", **kwargs},
    )


def TextField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Text field for long text content.

    Args:
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Text fields

    Example:
        >>> description: Optional[str] = TextField(
        ...     description="Product description"
        ... )
    """
    return Field(
        default=None,
        description=description,
        json_schema_extra={"odoo_type": "text", **kwargs},
    )


def CharField(
    max_length: Optional[int] = None, description: str = "", **kwargs: Any
) -> FieldInfo:
    """Create a Char field for short text content.

    Args:
        max_length: Maximum length of the string
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Char fields

    Example:
        >>> name: str = CharField(
        ...     max_length=100,
        ...     description="Partner name"
        ... )
    """
    extra = {"odoo_type": "char", **kwargs}
    if max_length:
        extra["odoo_size"] = max_length

    return Field(
        description=description, max_length=max_length, json_schema_extra=extra
    )


def BooleanField(description: str = "", **kwargs: Any) -> FieldInfo:
    """Create a Boolean field.

    Args:
        description: Field description
        **kwargs: Additional field parameters

    Returns:
        FieldInfo configured for Boolean fields

    Example:
        >>> active: bool = BooleanField(
        ...     description="Is record active"
        ... )
    """
    return Field(
        default=False,
        description=description,
        json_schema_extra={"odoo_type": "boolean", **kwargs},
    )
