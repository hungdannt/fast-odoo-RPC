"""
Pydantic models for OdooFlow.

This module provides type-safe data models for Odoo records using Pydantic.
It includes base model classes, field types, and relationship handling.
"""

from .base import OdooModel, OdooRecord
from .fields import (
    Many2OneField,
    One2ManyField,
    Many2ManyField,
    SelectionField,
    BinaryField,
    DateField,
    DateTimeField,
)
from .registry import ModelRegistry, register_model, get_model_class
from .relationships import LazyRelationship, RelationshipManager

__all__ = [
    # Base classes
    "OdooModel",
    "OdooRecord",
    # Field types
    "Many2OneField",
    "One2ManyField",
    "Many2ManyField",
    "SelectionField",
    "BinaryField",
    "DateField",
    "DateTimeField",
    # Registry
    "ModelRegistry",
    "register_model",
    "get_model_class",
    # Relationships
    "LazyRelationship",
    "RelationshipManager",
]
