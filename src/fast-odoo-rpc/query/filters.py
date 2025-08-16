"""
Filter expressions for query building.

This module provides the Q object and filter expressions for building
complex queries with a Django-like interface.
"""

from typing import Any, Dict, List, Union, Tuple
from .expressions import Expression, Field


class FilterExpression(Expression):
    """Represents a filter expression built from keyword arguments.

    This class provides a Django-like interface for building filter
    conditions using keyword arguments with field lookups.

    Example:
        >>> # Simple equality
        >>> expr = FilterExpression(name="John", is_active=True)
        >>>
        >>> # Field lookups
        >>> expr = FilterExpression(name__ilike="john%", age__gte=18)
        >>>
        >>> # Related field access
        >>> expr = FilterExpression(company_id__name="ACME Corp")
    """

    # Supported field lookups
    LOOKUPS = {
        "exact": "=",
        "iexact": "ilike",  # Case-insensitive exact match
        "contains": "ilike",  # Contains (case-insensitive)
        "icontains": "ilike",  # Contains (case-insensitive)
        "startswith": "ilike",  # Starts with
        "istartswith": "ilike",  # Starts with (case-insensitive)
        "endswith": "ilike",  # Ends with
        "iendswith": "ilike",  # Ends with (case-insensitive)
        "like": "like",  # SQL LIKE
        "ilike": "ilike",  # SQL ILIKE
        "gt": ">",  # Greater than
        "gte": ">=",  # Greater than or equal
        "lt": "<",  # Less than
        "lte": "<=",  # Less than or equal
        "ne": "!=",  # Not equal
        "in": "in",  # In list
        "not_in": "not in",  # Not in list
        "isnull": "=",  # Is null (value should be False)
        "isnotnull": "!=",  # Is not null (value should be False)
    }

    def __init__(self, **filters: Any):
        """Initialize filter expression with keyword arguments.

        Args:
            **filters: Field filters using Django-like syntax
        """
        self.filters = filters

    def to_domain(self) -> List[Tuple[str, str, Any]]:
        """Convert filters to Odoo domain format.

        Returns:
            List of domain tuples
        """
        domain = []

        for field_lookup, value in self.filters.items():
            field_name, operator, processed_value = self._parse_lookup(
                field_lookup, value
            )
            domain.append((field_name, operator, processed_value))

        return domain

    def _parse_lookup(self, field_lookup: str, value: Any) -> Tuple[str, str, Any]:
        """Parse a field lookup into field name, operator, and value.

        Args:
            field_lookup: Field name with optional lookup (e.g., "name__ilike")
            value: The value to compare against

        Returns:
            Tuple of (field_name, operator, processed_value)
        """
        parts = field_lookup.split("__")
        field_name = "__".join(parts[:-1]) if len(parts) > 1 else parts[0]
        lookup = parts[-1] if len(parts) > 1 and parts[-1] in self.LOOKUPS else "exact"

        # If the last part is not a lookup, it's part of the field name
        if lookup == "exact" and len(parts) > 1 and parts[-1] not in self.LOOKUPS:
            field_name = field_lookup

        # Get the operator
        operator = self.LOOKUPS[lookup]

        # Process the value based on the lookup
        processed_value = self._process_value(lookup, value)

        return field_name, operator, processed_value

    def _process_value(self, lookup: str, value: Any) -> Any:
        """Process the value based on the lookup type.

        Args:
            lookup: The lookup type
            value: The original value

        Returns:
            Processed value for the domain
        """
        if lookup in ("isnull", "isnotnull"):
            # For null checks, use False as the value
            return False
        elif lookup in ("contains", "icontains"):
            # Add wildcards for contains
            return f"%{value}%"
        elif lookup in ("startswith", "istartswith"):
            # Add wildcard at the end
            return f"{value}%"
        elif lookup in ("endswith", "iendswith"):
            # Add wildcard at the beginning
            return f"%{value}"
        elif lookup == "iexact":
            # Case-insensitive exact match
            return value
        else:
            # Return value as-is for other lookups
            return value


class Q:
    """Django-like Q object for building complex queries.

    The Q object allows you to build complex queries using logical
    operators (AND, OR, NOT) with a clean, readable syntax.

    Example:
        >>> from odooflow.query import Q
        >>>
        >>> # Simple Q object
        >>> q1 = Q(name="John")
        >>> q2 = Q(age__gte=18)
        >>>
        >>> # Combine with AND
        >>> combined = q1 & q2
        >>>
        >>> # Combine with OR
        >>> combined = q1 | q2
        >>>
        >>> # Negate with NOT
        >>> negated = ~q1
        >>>
        >>> # Complex query
        >>> complex_q = (Q(name__ilike="john%") | Q(email__ilike="john%")) & Q(is_active=True)
    """

    def __init__(self, **filters: Any):
        """Initialize Q object with filters.

        Args:
            **filters: Field filters using Django-like syntax
        """
        self.filters = filters
        self.children = []
        self.connector = "AND"
        self.negated = False

    def __and__(self, other: "Q") -> "Q":
        """Combine Q objects with AND operator."""
        return self._combine(other, "AND")

    def __or__(self, other: "Q") -> "Q":
        """Combine Q objects with OR operator."""
        return self._combine(other, "OR")

    def __invert__(self) -> "Q":
        """Negate the Q object with NOT operator."""
        new_q = Q()
        new_q.children = [self]
        new_q.negated = True
        return new_q

    def _combine(self, other: "Q", connector: str) -> "Q":
        """Combine two Q objects with the given connector.

        Args:
            other: The other Q object to combine with
            connector: 'AND' or 'OR'

        Returns:
            New Q object representing the combination
        """
        new_q = Q()
        new_q.connector = connector
        new_q.children = [self, other]
        return new_q

    def to_domain(self) -> List[Union[str, Tuple[str, str, Any]]]:
        """Convert Q object to Odoo domain format.

        Returns:
            List representing the domain
        """
        # If this Q object has direct filters, convert them
        if self.filters:
            filter_expr = FilterExpression(**self.filters)
            domain = filter_expr.to_domain()
        else:
            domain = []

        # If this Q object has children, process them
        if self.children:
            child_domains = []
            for child in self.children:
                child_domain = child.to_domain()
                child_domains.append(child_domain)

            # Combine child domains based on connector
            if len(child_domains) == 1:
                domain.extend(child_domains[0])
            elif len(child_domains) > 1:
                if self.connector == "OR":
                    # Add OR operators between domains
                    combined_domain = []
                    for i, child_domain in enumerate(child_domains):
                        if i > 0:
                            combined_domain.append("|")
                        combined_domain.extend(child_domain)
                    domain.extend(combined_domain)
                else:  # AND
                    # Just concatenate domains (AND is implicit)
                    for child_domain in child_domains:
                        domain.extend(child_domain)

        # Apply negation if needed
        if self.negated and domain:
            domain = ["!"] + domain

        return domain

    def __repr__(self) -> str:
        """String representation of the Q object."""
        if self.filters:
            filter_strs = [f"{k}={v}" for k, v in self.filters.items()]
            content = ", ".join(filter_strs)
        elif self.children:
            child_strs = [repr(child) for child in self.children]
            content = f" {self.connector} ".join(child_strs)
        else:
            content = "empty"

        if self.negated:
            content = f"NOT ({content})"

        return f"Q({content})"
