"""
Query builder for OdooFlow.

This module provides a fluent, chainable query interface for building
and executing Odoo queries with type safety and performance optimization.
"""

from .builder import QueryBuilder, QuerySet
from .filters import FilterExpression, Q
from .lazy import LazyLoader, LazyCollection
from .expressions import (
    Field,
    Equal,
    NotEqual,
    GreaterThan,
    LessThan,
    GreaterEqual,
    LessEqual,
    Like,
    ILike,
    In,
    NotIn,
    Contains,
    StartsWith,
    EndsWith,
)

__all__ = [
    # Core query building
    "QueryBuilder",
    "QuerySet",
    # Filtering
    "FilterExpression",
    "Q",
    # Lazy loading
    "LazyLoader",
    "LazyCollection",
    # Field expressions
    "Field",
    "Equal",
    "NotEqual",
    "GreaterThan",
    "LessThan",
    "GreaterEqual",
    "LessEqual",
    "Like",
    "ILike",
    "In",
    "NotIn",
    "Contains",
    "StartsWith",
    "EndsWith",
]
