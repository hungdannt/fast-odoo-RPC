"""
Comprehensive tests for query/expressions.py.

This module tests all query expression classes and functionality with focus on:
- Expression creation and validation
- Domain generation for Odoo compatibility
- Logical operators (AND, OR, NOT)
- Comparison operators (=, !=, >, <, etc.)
- String pattern matching (LIKE, ILIKE, contains, etc.)
- Field fluent interface
- Expression composition and nesting
"""

import pytest
from typing import List, Tuple, Any, Union

from src.zenoo_rpc.query.expressions import (
    Expression,
    Field,
    ComparisonExpression,
    LogicalExpression,
    Equal,
    NotEqual,
    GreaterThan,
    GreaterEqual,
    LessThan,
    LessEqual,
    Like,
    ILike,
    In,
    NotIn,
    Contains,
    StartsWith,
    EndsWith,
    AndExpression,
    OrExpression,
    NotExpression,
)


class TestField:
    """Test Field class and fluent interface."""

    def test_field_creation(self):
        """Test basic field creation."""
        field = Field("name")
        assert field.name == "name"

    def test_field_with_dot_notation(self):
        """Test field with related field notation."""
        field = Field("partner_id.name")
        assert field.name == "partner_id.name"

    def test_equality_operator(self):
        """Test equality operator (==)."""
        field = Field("name")
        expr = field == "Test"
        
        assert isinstance(expr, Equal)
        assert expr.field == "name"
        assert expr.operator == "="
        assert expr.value == "Test"

    def test_not_equal_operator(self):
        """Test not equal operator (!=)."""
        field = Field("name")
        expr = field != "Test"
        
        assert isinstance(expr, NotEqual)
        assert expr.field == "name"
        assert expr.operator == "!="
        assert expr.value == "Test"

    def test_greater_than_operator(self):
        """Test greater than operator (>)."""
        field = Field("age")
        expr = field > 18
        
        assert isinstance(expr, GreaterThan)
        assert expr.field == "age"
        assert expr.operator == ">"
        assert expr.value == 18

    def test_greater_equal_operator(self):
        """Test greater than or equal operator (>=)."""
        field = Field("age")
        expr = field >= 18
        
        assert isinstance(expr, GreaterEqual)
        assert expr.field == "age"
        assert expr.operator == ">="
        assert expr.value == 18

    def test_less_than_operator(self):
        """Test less than operator (<)."""
        field = Field("age")
        expr = field < 65
        
        assert isinstance(expr, LessThan)
        assert expr.field == "age"
        assert expr.operator == "<"
        assert expr.value == 65

    def test_less_equal_operator(self):
        """Test less than or equal operator (<=)."""
        field = Field("age")
        expr = field <= 65
        
        assert isinstance(expr, LessEqual)
        assert expr.field == "age"
        assert expr.operator == "<="
        assert expr.value == 65

    def test_like_method(self):
        """Test LIKE method (case-sensitive)."""
        field = Field("name")
        expr = field.like("Test%")
        
        assert isinstance(expr, Like)
        assert expr.field == "name"
        assert expr.operator == "like"
        assert expr.value == "Test%"

    def test_ilike_method(self):
        """Test ILIKE method (case-insensitive)."""
        field = Field("name")
        expr = field.ilike("test%")
        
        assert isinstance(expr, ILike)
        assert expr.field == "name"
        assert expr.operator == "ilike"
        assert expr.value == "test%"

    def test_in_method(self):
        """Test IN method."""
        field = Field("state")
        expr = field.in_(["draft", "confirmed", "done"])
        
        assert isinstance(expr, In)
        assert expr.field == "state"
        assert expr.operator == "in"
        assert expr.value == ["draft", "confirmed", "done"]

    def test_not_in_method(self):
        """Test NOT IN method."""
        field = Field("state")
        expr = field.not_in(["cancelled", "rejected"])
        
        assert isinstance(expr, NotIn)
        assert expr.field == "state"
        assert expr.operator == "not in"
        assert expr.value == ["cancelled", "rejected"]

    def test_contains_method(self):
        """Test contains method."""
        field = Field("name")
        expr = field.contains("company")
        
        assert isinstance(expr, Contains)
        assert expr.field == "name"
        assert expr.operator == "ilike"
        assert expr.value == "%company%"

    def test_startswith_method(self):
        """Test startswith method."""
        field = Field("name")
        expr = field.startswith("ABC")
        
        assert isinstance(expr, StartsWith)
        assert expr.field == "name"
        assert expr.operator == "ilike"
        assert expr.value == "ABC%"

    def test_endswith_method(self):
        """Test endswith method."""
        field = Field("name")
        expr = field.endswith("Corp")
        
        assert isinstance(expr, EndsWith)
        assert expr.field == "name"
        assert expr.operator == "ilike"
        assert expr.value == "%Corp"

    def test_is_null_method(self):
        """Test is_null method."""
        field = Field("description")
        expr = field.is_null()
        
        assert isinstance(expr, Equal)
        assert expr.field == "description"
        assert expr.operator == "="
        assert expr.value is False

    def test_is_not_null_method(self):
        """Test is_not_null method."""
        field = Field("description")
        expr = field.is_not_null()
        
        assert isinstance(expr, NotEqual)
        assert expr.field == "description"
        assert expr.operator == "!="
        assert expr.value is False


class TestComparisonExpressions:
    """Test comparison expression classes."""

    def test_equal_expression(self):
        """Test Equal expression."""
        expr = Equal("name", "Test")
        domain = expr.to_domain()
        
        assert domain == [("name", "=", "Test")]

    def test_not_equal_expression(self):
        """Test NotEqual expression."""
        expr = NotEqual("name", "Test")
        domain = expr.to_domain()
        
        assert domain == [("name", "!=", "Test")]

    def test_greater_than_expression(self):
        """Test GreaterThan expression."""
        expr = GreaterThan("age", 18)
        domain = expr.to_domain()
        
        assert domain == [("age", ">", 18)]

    def test_greater_equal_expression(self):
        """Test GreaterEqual expression."""
        expr = GreaterEqual("age", 18)
        domain = expr.to_domain()
        
        assert domain == [("age", ">=", 18)]

    def test_less_than_expression(self):
        """Test LessThan expression."""
        expr = LessThan("age", 65)
        domain = expr.to_domain()
        
        assert domain == [("age", "<", 65)]

    def test_less_equal_expression(self):
        """Test LessEqual expression."""
        expr = LessEqual("age", 65)
        domain = expr.to_domain()
        
        assert domain == [("age", "<=", 65)]

    def test_like_expression(self):
        """Test Like expression."""
        expr = Like("name", "Test%")
        domain = expr.to_domain()
        
        assert domain == [("name", "like", "Test%")]

    def test_ilike_expression(self):
        """Test ILike expression."""
        expr = ILike("name", "test%")
        domain = expr.to_domain()
        
        assert domain == [("name", "ilike", "test%")]

    def test_in_expression(self):
        """Test In expression."""
        expr = In("state", ["draft", "confirmed"])
        domain = expr.to_domain()
        
        assert domain == [("state", "in", ["draft", "confirmed"])]

    def test_not_in_expression(self):
        """Test NotIn expression."""
        expr = NotIn("state", ["cancelled"])
        domain = expr.to_domain()
        
        assert domain == [("state", "not in", ["cancelled"])]

    def test_contains_expression(self):
        """Test Contains expression."""
        expr = Contains("name", "company")
        domain = expr.to_domain()
        
        assert domain == [("name", "ilike", "%company%")]

    def test_startswith_expression(self):
        """Test StartsWith expression."""
        expr = StartsWith("name", "ABC")
        domain = expr.to_domain()
        
        assert domain == [("name", "ilike", "ABC%")]

    def test_endswith_expression(self):
        """Test EndsWith expression."""
        expr = EndsWith("name", "Corp")
        domain = expr.to_domain()
        
        assert domain == [("name", "ilike", "%Corp")]


class TestLogicalExpressions:
    """Test logical expression classes."""

    def test_and_expression_two_conditions(self):
        """Test AND expression with two conditions."""
        expr1 = Equal("name", "Test")
        expr2 = Equal("active", True)
        and_expr = AndExpression(expr1, expr2)
        
        domain = and_expr.to_domain()
        expected = [("name", "=", "Test"), ("active", "=", True)]
        
        assert domain == expected

    def test_and_expression_multiple_conditions(self):
        """Test AND expression with multiple conditions."""
        expr1 = Equal("name", "Test")
        expr2 = Equal("active", True)
        expr3 = GreaterThan("age", 18)
        and_expr = AndExpression(expr1, expr2, expr3)
        
        domain = and_expr.to_domain()
        expected = [
            ("name", "=", "Test"),
            ("active", "=", True),
            ("age", ">", 18)
        ]
        
        assert domain == expected

    def test_or_expression_two_conditions(self):
        """Test OR expression with two conditions."""
        expr1 = Equal("state", "draft")
        expr2 = Equal("state", "confirmed")
        or_expr = OrExpression(expr1, expr2)
        
        domain = or_expr.to_domain()
        expected = ["|", ("state", "=", "draft"), ("state", "=", "confirmed")]
        
        assert domain == expected

    def test_or_expression_single_condition(self):
        """Test OR expression with single condition."""
        expr1 = Equal("name", "Test")
        or_expr = OrExpression(expr1)
        
        domain = or_expr.to_domain()
        expected = [("name", "=", "Test")]
        
        assert domain == expected

    def test_or_expression_empty(self):
        """Test OR expression with no conditions."""
        or_expr = OrExpression()
        
        domain = or_expr.to_domain()
        assert domain == []

    def test_not_expression(self):
        """Test NOT expression."""
        expr = Equal("active", False)
        not_expr = NotExpression(expr)
        
        domain = not_expr.to_domain()
        expected = ["!", ("active", "=", False)]
        
        assert domain == expected


class TestExpressionOperators:
    """Test expression operator overloading."""

    def test_and_operator_overload(self):
        """Test & operator for AND expressions."""
        expr1 = Equal("name", "Test")
        expr2 = Equal("active", True)
        combined = expr1 & expr2
        
        assert isinstance(combined, AndExpression)
        domain = combined.to_domain()
        expected = [("name", "=", "Test"), ("active", "=", True)]
        assert domain == expected

    def test_or_operator_overload(self):
        """Test | operator for OR expressions."""
        expr1 = Equal("state", "draft")
        expr2 = Equal("state", "confirmed")
        combined = expr1 | expr2
        
        assert isinstance(combined, OrExpression)
        domain = combined.to_domain()
        expected = ["|", ("state", "=", "draft"), ("state", "=", "confirmed")]
        assert domain == expected

    def test_not_operator_overload(self):
        """Test ~ operator for NOT expressions."""
        expr = Equal("active", False)
        negated = ~expr
        
        assert isinstance(negated, NotExpression)
        domain = negated.to_domain()
        expected = ["!", ("active", "=", False)]
        assert domain == expected

    def test_complex_operator_combination(self):
        """Test complex combination of operators."""
        name_field = Field("name")
        active_field = Field("active")
        state_field = Field("state")
        
        # (name = 'Test' AND active = True) OR state = 'draft'
        complex_expr = (
            (name_field == "Test") & (active_field == True)
        ) | (state_field == "draft")
        
        domain = complex_expr.to_domain()
        
        # Should be: ["|", ("name", "=", "Test"), ("active", "=", True), ("state", "=", "draft")]
        # Note: This tests the current implementation behavior
        assert "|" in domain
        assert ("name", "=", "Test") in domain
        assert ("active", "=", True) in domain
        assert ("state", "=", "draft") in domain


class TestFluentInterface:
    """Test fluent interface for building complex queries."""

    def test_simple_fluent_query(self):
        """Test simple fluent query building."""
        name = Field("name")
        active = Field("active")

        query = (name == "Test Company") & (active == True)  # noqa: E712
        domain = query.to_domain()

        expected = [("name", "=", "Test Company"), ("active", "=", True)]
        assert domain == expected

    def test_complex_fluent_query(self):
        """Test complex fluent query building."""
        name = Field("name")
        email = Field("email")
        is_company = Field("is_company")
        customer_rank = Field("customer_rank")

        # Companies with 'Corp' in name OR individuals with email and rank > 0
        query = (
            (name.contains("Corp") & (is_company == True)) |  # noqa: E712
            (
                (email.is_not_null()) &
                (customer_rank > 0) &
                (is_company == False)  # noqa: E712
            )
        )

        domain = query.to_domain()

        # Verify key components are present
        assert "|" in domain  # OR operator
        assert ("name", "ilike", "%Corp%") in domain
        assert ("is_company", "=", True) in domain
        assert ("email", "!=", False) in domain
        assert ("customer_rank", ">", 0) in domain
        assert ("is_company", "=", False) in domain

    def test_negated_fluent_query(self):
        """Test negated fluent query."""
        active = Field("active")
        state = Field("state")

        # NOT (active = False OR state = 'cancelled')
        query = ~((active == False) | (state == "cancelled"))  # noqa: E712
        domain = query.to_domain()

        # Should start with NOT operator
        assert domain[0] == "!"
        assert "|" in domain  # OR inside NOT
        assert ("active", "=", False) in domain
        assert ("state", "=", "cancelled") in domain

    def test_string_pattern_fluent_query(self):
        """Test string pattern matching in fluent queries."""
        name = Field("name")
        email = Field("email")

        query = (
            name.startswith("ABC") |
            name.endswith("Corp") |
            email.contains("@company.com")
        )

        domain = query.to_domain()

        assert ("name", "ilike", "ABC%") in domain
        assert ("name", "ilike", "%Corp") in domain
        assert ("email", "ilike", "%@company.com%") in domain

    def test_numeric_comparison_fluent_query(self):
        """Test numeric comparisons in fluent queries."""
        age = Field("age")
        salary = Field("salary")
        experience = Field("experience_years")

        # Age between 25 and 65, salary >= 50000, experience > 2
        query = (
            (age >= 25) & (age <= 65) &
            (salary >= 50000) &
            (experience > 2)
        )

        domain = query.to_domain()

        expected = [
            ("age", ">=", 25),
            ("age", "<=", 65),
            ("salary", ">=", 50000),
            ("experience_years", ">", 2)
        ]
        assert domain == expected

    def test_list_operations_fluent_query(self):
        """Test list operations in fluent queries."""
        state = Field("state")
        category_id = Field("category_id")
        tag_ids = Field("tag_ids")

        valid_states = ["draft", "confirmed", "done"]
        excluded_categories = [1, 2, 3]
        required_tags = [10, 20]

        query = (
            state.in_(valid_states) &
            category_id.not_in(excluded_categories) &
            tag_ids.in_(required_tags)
        )

        domain = query.to_domain()

        expected = [
            ("state", "in", valid_states),
            ("category_id", "not in", excluded_categories),
            ("tag_ids", "in", required_tags)
        ]
        assert domain == expected


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_field_name(self):
        """Test field with empty name."""
        field = Field("")
        expr = field == "test"

        assert expr.field == ""
        assert expr.value == "test"

    def test_none_values(self):
        """Test expressions with None values."""
        field = Field("description")
        expr = field == None  # noqa: E711
        domain = expr.to_domain()

        assert domain == [("description", "=", None)]

    def test_empty_list_in_expression(self):
        """Test IN expression with empty list."""
        field = Field("state")
        expr = field.in_([])
        domain = expr.to_domain()

        assert domain == [("state", "in", [])]

    def test_special_characters_in_patterns(self):
        """Test patterns with special characters."""
        field = Field("name")

        # Test with SQL wildcards
        expr1 = field.like("Test%_")
        assert expr1.to_domain() == [("name", "like", "Test%_")]

        # Test with special characters in contains
        expr2 = field.contains("100%")
        assert expr2.to_domain() == [("name", "ilike", "%100%%")]

    def test_unicode_values(self):
        """Test expressions with Unicode values."""
        field = Field("name")
        expr = field == "Café Münchën"
        domain = expr.to_domain()

        assert domain == [("name", "=", "Café Münchën")]

    def test_numeric_string_values(self):
        """Test expressions with numeric string values."""
        field = Field("reference")
        expr = field == "12345"
        domain = expr.to_domain()

        assert domain == [("reference", "=", "12345")]

    def test_boolean_values(self):
        """Test expressions with boolean values."""
        field = Field("active")

        expr_true = field == True  # noqa: E712
        assert expr_true.to_domain() == [("active", "=", True)]

        expr_false = field == False  # noqa: E712
        assert expr_false.to_domain() == [("active", "=", False)]

    def test_complex_nested_expressions(self):
        """Test deeply nested expressions."""
        a = Field("a")
        b = Field("b")
        c = Field("c")
        d = Field("d")

        # ((a = 1 AND b = 2) OR (c = 3 AND d = 4))
        nested = ((a == 1) & (b == 2)) | ((c == 3) & (d == 4))
        domain = nested.to_domain()

        # Verify structure contains all expected elements
        assert "|" in domain
        assert ("a", "=", 1) in domain
        assert ("b", "=", 2) in domain
        assert ("c", "=", 3) in domain
        assert ("d", "=", 4) in domain


class TestIntegration:
    """Test integration with real-world scenarios."""

    def test_partner_search_query(self):
        """Test realistic partner search query."""
        name = Field("name")
        email = Field("email")
        is_company = Field("is_company")
        active = Field("active")
        customer_rank = Field("customer_rank")

        # Active customers with name or email matching
        query = (
            (active == True) &  # noqa: E712
            (customer_rank > 0) &
            (
                (is_company == True) |  # noqa: E712
                (email.is_not_null())
            ) &
            (
                name.ilike("%company%") |
                email.ilike("%@business.com")
            )
        )

        domain = query.to_domain()

        # Verify all conditions are present
        assert ("active", "=", True) in domain
        assert ("customer_rank", ">", 0) in domain
        assert ("is_company", "=", True) in domain
        assert ("email", "!=", False) in domain
        assert ("name", "ilike", "%company%") in domain
        assert ("email", "ilike", "%@business.com") in domain

    def test_product_filter_query(self):
        """Test realistic product filter query."""
        name = Field("name")
        categ_id = Field("categ_id")
        list_price = Field("list_price")
        active = Field("active")
        sale_ok = Field("sale_ok")
        type = Field("type")

        # Active sellable products in specific categories with price range
        query = (
            (active == True) &  # noqa: E712
            (sale_ok == True) &  # noqa: E712
            (type.in_(["product", "consu"])) &
            (categ_id.in_([1, 2, 3, 4])) &
            (list_price >= 10.0) &
            (list_price <= 1000.0) &
            (name.is_not_null())
        )

        domain = query.to_domain()

        expected = [
            ("active", "=", True),
            ("sale_ok", "=", True),
            ("type", "in", ["product", "consu"]),
            ("categ_id", "in", [1, 2, 3, 4]),
            ("list_price", ">=", 10.0),
            ("list_price", "<=", 1000.0),
            ("name", "!=", False)
        ]
        assert domain == expected

    def test_sale_order_reporting_query(self):
        """Test realistic sale order reporting query."""
        state = Field("state")
        date_order = Field("date_order")
        amount_total = Field("amount_total")
        partner_id = Field("partner_id.is_company")
        user_id = Field("user_id")

        # Confirmed orders from last month with significant amounts
        query = (
            (state.in_(["sale", "done"])) &
            (date_order >= "2023-01-01") &
            (date_order < "2023-02-01") &
            (amount_total >= 1000.0) &
            (partner_id == True) &  # Company customers only  # noqa: E712
            (user_id.is_not_null())  # Has salesperson
        )

        domain = query.to_domain()

        expected = [
            ("state", "in", ["sale", "done"]),
            ("date_order", ">=", "2023-01-01"),
            ("date_order", "<", "2023-02-01"),
            ("amount_total", ">=", 1000.0),
            ("partner_id.is_company", "=", True),
            ("user_id", "!=", False)
        ]
        assert domain == expected
