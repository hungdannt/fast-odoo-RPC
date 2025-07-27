"""
Query expressions for building Odoo domains.

This module provides type-safe query expressions that can be combined
to build complex Odoo domain filters with a fluent interface.
"""

from typing import Any, List, Union, Tuple
from abc import ABC, abstractmethod


class Expression(ABC):
    """Base class for all query expressions."""

    @abstractmethod
    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert the expression to Odoo domain format.

        Returns:
            List representing the domain expression
        """
        pass

    def __and__(self, other: "Expression") -> "AndExpression":
        """Combine expressions with AND operator."""
        return AndExpression(self, other)

    def __or__(self, other: "Expression") -> "OrExpression":
        """Combine expressions with OR operator."""
        return OrExpression(self, other)

    def __invert__(self) -> "NotExpression":
        """Negate the expression with NOT operator."""
        return NotExpression(self)


class Field:
    """Represents a field in query expressions.

    This class provides a fluent interface for building field-based
    query conditions with type safety and IDE support.

    Example:
        >>> from odooflow.query import Field
        >>>
        >>> # Create field expressions
        >>> name_field = Field('name')
        >>> is_company = Field('is_company')
        >>>
        >>> # Build conditions
        >>> condition = name_field.ilike('company%') & is_company == True
    """

    def __init__(self, name: str):
        """Initialize a field reference.

        Args:
            name: The field name (supports dot notation for related fields)
        """
        self.name = name

    def __eq__(self, value: Any) -> "Equal":
        """Create an equality condition."""
        return Equal(self.name, value)

    def __ne__(self, value: Any) -> "NotEqual":
        """Create a not-equal condition."""
        return NotEqual(self.name, value)

    def __gt__(self, value: Any) -> "GreaterThan":
        """Create a greater-than condition."""
        return GreaterThan(self.name, value)

    def __ge__(self, value: Any) -> "GreaterEqual":
        """Create a greater-than-or-equal condition."""
        return GreaterEqual(self.name, value)

    def __lt__(self, value: Any) -> "LessThan":
        """Create a less-than condition."""
        return LessThan(self.name, value)

    def __le__(self, value: Any) -> "LessEqual":
        """Create a less-than-or-equal condition."""
        return LessEqual(self.name, value)

    def like(self, pattern: str) -> "Like":
        """Create a LIKE condition (case-sensitive)."""
        return Like(self.name, pattern)

    def ilike(self, pattern: str) -> "ILike":
        """Create an ILIKE condition (case-insensitive)."""
        return ILike(self.name, pattern)

    def in_(self, values: List[Any]) -> "In":
        """Create an IN condition."""
        return In(self.name, values)

    def not_in(self, values: List[Any]) -> "NotIn":
        """Create a NOT IN condition."""
        return NotIn(self.name, values)

    def contains(self, value: str) -> "Contains":
        """Create a contains condition (field contains value)."""
        return Contains(self.name, value)

    def startswith(self, value: str) -> "StartsWith":
        """Create a starts-with condition."""
        return StartsWith(self.name, value)

    def endswith(self, value: str) -> "EndsWith":
        """Create an ends-with condition."""
        return EndsWith(self.name, value)

    def is_null(self) -> "Equal":
        """Create an IS NULL condition."""
        return Equal(self.name, False)

    def is_not_null(self) -> "NotEqual":
        """Create an IS NOT NULL condition."""
        return NotEqual(self.name, False)


# Comparison expressions
class ComparisonExpression(Expression):
    """Base class for comparison expressions."""

    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator
        self.value = value

    def to_domain(self) -> List[Tuple[str, str, Any]]:
        """Convert to domain tuple."""
        return [(self.field, self.operator, self.value)]


class Equal(ComparisonExpression):
    """Equality expression (=)."""

    def __init__(self, field: str, value: Any):
        super().__init__(field, "=", value)


class NotEqual(ComparisonExpression):
    """Not equal expression (!=)."""

    def __init__(self, field: str, value: Any):
        super().__init__(field, "!=", value)


class GreaterThan(ComparisonExpression):
    """Greater than expression (>)."""

    def __init__(self, field: str, value: Any):
        super().__init__(field, ">", value)


class GreaterEqual(ComparisonExpression):
    """Greater than or equal expression (>=)."""

    def __init__(self, field: str, value: Any):
        super().__init__(field, ">=", value)


class LessThan(ComparisonExpression):
    """Less than expression (<)."""

    def __init__(self, field: str, value: Any):
        super().__init__(field, "<", value)


class LessEqual(ComparisonExpression):
    """Less than or equal expression (<=)."""

    def __init__(self, field: str, value: Any):
        super().__init__(field, "<=", value)


class Like(ComparisonExpression):
    """LIKE expression (case-sensitive pattern matching)."""

    def __init__(self, field: str, pattern: str):
        super().__init__(field, "like", pattern)


class ILike(ComparisonExpression):
    """ILIKE expression (case-insensitive pattern matching)."""

    def __init__(self, field: str, pattern: str):
        super().__init__(field, "ilike", pattern)


class In(ComparisonExpression):
    """IN expression (value in list)."""

    def __init__(self, field: str, values: List[Any]):
        super().__init__(field, "in", values)


class NotIn(ComparisonExpression):
    """NOT IN expression (value not in list)."""

    def __init__(self, field: str, values: List[Any]):
        super().__init__(field, "not in", values)


class Contains(ComparisonExpression):
    """Contains expression (field contains substring)."""

    def __init__(self, field: str, value: str):
        # Convert to ILIKE pattern
        pattern = f"%{value}%"
        super().__init__(field, "ilike", pattern)


class StartsWith(ComparisonExpression):
    """Starts with expression (field starts with substring)."""

    def __init__(self, field: str, value: str):
        # Convert to ILIKE pattern
        pattern = f"{value}%"
        super().__init__(field, "ilike", pattern)


class EndsWith(ComparisonExpression):
    """Ends with expression (field ends with substring)."""

    def __init__(self, field: str, value: str):
        # Convert to ILIKE pattern
        pattern = f"%{value}"
        super().__init__(field, "ilike", pattern)


# Logical expressions
class LogicalExpression(Expression):
    """Base class for logical expressions."""

    def __init__(self, *expressions: Expression):
        self.expressions = expressions


class AndExpression(LogicalExpression):
    """AND expression combining multiple conditions."""

    def __init__(self, *expressions: Expression):
        super().__init__(*expressions)

    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert to domain with AND logic."""
        domain = []
        for expr in self.expressions:
            expr_domain = expr.to_domain()
            domain.extend(expr_domain)
        return domain


class OrExpression(LogicalExpression):
    """OR expression combining multiple conditions."""

    def __init__(self, *expressions: Expression):
        super().__init__(*expressions)

    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert to domain with OR logic."""
        if len(self.expressions) <= 1:
            return self.expressions[0].to_domain() if self.expressions else []

        domain = ["|"]  # OR operator
        for expr in self.expressions:
            expr_domain = expr.to_domain()
            domain.extend(expr_domain)
        return domain


class NotExpression(Expression):
    """NOT expression negating a condition."""

    def __init__(self, expression: Expression):
        self.expression = expression

    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert to domain with NOT logic."""
        expr_domain = self.expression.to_domain()
        return ["!"] + expr_domain  # NOT operator
