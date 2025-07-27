"""
Comprehensive tests for cache/keys.py.

This module tests all cache key generation and management functionality with focus on:
- CacheKey class behavior and validation
- Key generation functions for different operations
- Parameter hashing and normalization
- Key validation and parsing
- Redis-compatible key formats
"""

import pytest
import hashlib
import json
from typing import Dict, Any, List

from src.zenoo_rpc.cache.keys import (
    CacheKey,
    make_cache_key,
    make_model_cache_key,
    make_query_cache_key,
    validate_cache_key,
    parse_cache_key,
    _hash_params,
)
from src.zenoo_rpc.cache.exceptions import CacheKeyError


class TestCacheKey:
    """Test CacheKey class."""

    def test_basic_instantiation(self):
        """Test basic CacheKey creation."""
        key = CacheKey(key="test:key", namespace="test")
        
        assert key.key == "test:key"
        assert key.namespace == "test"
        assert key.model is None
        assert key.operation is None
        assert key.params is None

    def test_full_instantiation(self):
        """Test CacheKey with all parameters."""
        params = {"domain": [("active", "=", True)]}
        key = CacheKey(
            key="res.partner:search:abc123",
            namespace="odooflow",
            model="res.partner",
            operation="search",
            params=params
        )
        
        assert key.key == "res.partner:search:abc123"
        assert key.namespace == "odooflow"
        assert key.model == "res.partner"
        assert key.operation == "search"
        assert key.params == params

    def test_validation_empty_key(self):
        """Test validation with empty key."""
        with pytest.raises(CacheKeyError, match="Cache key must be a non-empty string"):
            CacheKey(key="", namespace="test")

    def test_validation_none_key(self):
        """Test validation with None key."""
        with pytest.raises(CacheKeyError, match="Cache key must be a non-empty string"):
            CacheKey(key=None, namespace="test")

    def test_validation_empty_namespace(self):
        """Test validation with empty namespace."""
        with pytest.raises(CacheKeyError, match="Cache namespace must be a non-empty string"):
            CacheKey(key="test", namespace="")

    def test_validation_none_namespace(self):
        """Test validation with None namespace."""
        with pytest.raises(CacheKeyError, match="Cache namespace must be a non-empty string"):
            CacheKey(key="test", namespace=None)

    def test_validation_key_with_spaces(self):
        """Test validation with spaces in key."""
        with pytest.raises(CacheKeyError, match="Cache key cannot contain spaces"):
            CacheKey(key="test key", namespace="test")

    def test_str_representation(self):
        """Test string representation."""
        key = CacheKey(key="test:key", namespace="test")
        assert str(key) == "test:key"

    def test_hash_method(self):
        """Test hash method."""
        key1 = CacheKey(key="test:key", namespace="test")
        key2 = CacheKey(key="test:key", namespace="other")
        key3 = CacheKey(key="other:key", namespace="test")
        
        # Same key should have same hash
        assert hash(key1) == hash(key2)
        # Different key should have different hash
        assert hash(key1) != hash(key3)

    def test_equality_with_cache_key(self):
        """Test equality with another CacheKey."""
        key1 = CacheKey(key="test:key", namespace="test")
        key2 = CacheKey(key="test:key", namespace="other")
        key3 = CacheKey(key="other:key", namespace="test")
        
        assert key1 == key2  # Same key
        assert key1 != key3  # Different key

    def test_equality_with_string(self):
        """Test equality with string."""
        key = CacheKey(key="test:key", namespace="test")
        
        assert key == "test:key"
        assert key != "other:key"

    def test_equality_with_other_types(self):
        """Test equality with other types."""
        key = CacheKey(key="test:key", namespace="test")
        
        assert key != 123
        assert key != None
        assert key != ["test:key"]

    def test_full_key_property(self):
        """Test full_key property."""
        key = CacheKey(key="test:key", namespace="odooflow")
        assert key.full_key == "odooflow:test:key"

    def test_with_suffix(self):
        """Test with_suffix method."""
        original = CacheKey(
            key="res.partner:search",
            namespace="odooflow",
            model="res.partner",
            operation="search",
            params={"test": "value"}
        )
        
        suffixed = original.with_suffix("abc123")
        
        assert suffixed.key == "res.partner:search:abc123"
        assert suffixed.namespace == original.namespace
        assert suffixed.model == original.model
        assert suffixed.operation == original.operation
        assert suffixed.params == original.params
        # Original should be unchanged
        assert original.key == "res.partner:search"

    def test_with_prefix(self):
        """Test with_prefix method."""
        original = CacheKey(
            key="search:abc123",
            namespace="odooflow",
            model="res.partner",
            operation="search",
            params={"test": "value"}
        )
        
        prefixed = original.with_prefix("res.partner")
        
        assert prefixed.key == "res.partner:search:abc123"
        assert prefixed.namespace == original.namespace
        assert prefixed.model == original.model
        assert prefixed.operation == original.operation
        assert prefixed.params == original.params
        # Original should be unchanged
        assert original.key == "search:abc123"


class TestMakeCacheKey:
    """Test make_cache_key function."""

    def test_basic_key_generation(self):
        """Test basic cache key generation."""
        key = make_cache_key(
            model="res.partner",
            operation="search",
            namespace="test"
        )
        
        assert key.key == "res.partner:search"
        assert key.namespace == "test"
        assert key.model == "res.partner"
        assert key.operation == "search"
        assert key.params is None

    def test_key_with_params_no_hash(self):
        """Test key generation with params but no hash."""
        params = {"domain": [("active", "=", True)]}
        key = make_cache_key(
            model="res.partner",
            operation="search",
            params=params,
            include_hash=False
        )
        
        assert key.key == "res.partner:search"
        assert key.params == params

    def test_key_with_params_and_hash(self):
        """Test key generation with params and hash."""
        params = {"domain": [("active", "=", True)], "limit": 10}
        key = make_cache_key(
            model="res.partner",
            operation="search",
            params=params,
            include_hash=True
        )
        
        # Should include hash
        parts = key.key.split(":")
        assert len(parts) == 3
        assert parts[0] == "res.partner"
        assert parts[1] == "search"
        assert len(parts[2]) == 8  # Hash should be 8 characters
        assert key.params == params

    def test_empty_model_error(self):
        """Test error with empty model."""
        with pytest.raises(CacheKeyError, match="Model name is required"):
            make_cache_key(model="", operation="search")

    def test_empty_operation_error(self):
        """Test error with empty operation."""
        with pytest.raises(CacheKeyError, match="Operation is required"):
            make_cache_key(model="res.partner", operation="")

    def test_default_namespace(self):
        """Test default namespace."""
        key = make_cache_key(model="res.partner", operation="search")
        assert key.namespace == "odooflow"

    def test_consistent_hashing(self):
        """Test that same params produce same hash."""
        params = {"domain": [("active", "=", True)], "limit": 10}
        
        key1 = make_cache_key("res.partner", "search", params)
        key2 = make_cache_key("res.partner", "search", params)
        
        assert key1.key == key2.key

    def test_different_params_different_hash(self):
        """Test that different params produce different hash."""
        params1 = {"domain": [("active", "=", True)], "limit": 10}
        params2 = {"domain": [("active", "=", False)], "limit": 10}
        
        key1 = make_cache_key("res.partner", "search", params1)
        key2 = make_cache_key("res.partner", "search", params2)
        
        assert key1.key != key2.key


class TestMakeModelCacheKey:
    """Test make_model_cache_key function."""

    def test_single_record_id(self):
        """Test key generation for single record ID."""
        key = make_model_cache_key("res.partner", 123)
        
        assert key.key == "res.partner:record:123"
        assert key.model == "res.partner"
        assert key.operation == "read"
        assert key.params["ids"] == 123

    def test_multiple_record_ids(self):
        """Test key generation for multiple record IDs."""
        key = make_model_cache_key("res.partner", [123, 456, 789])
        
        assert key.key == "res.partner:record:123,456,789"
        assert key.params["ids"] == [123, 456, 789]

    def test_record_ids_sorted(self):
        """Test that record IDs are sorted in key."""
        key = make_model_cache_key("res.partner", [789, 123, 456])
        
        # IDs should be sorted in the key
        assert key.key == "res.partner:record:123,456,789"

    def test_with_fields(self):
        """Test key generation with fields."""
        key = make_model_cache_key(
            "res.partner", 
            123, 
            fields=["name", "email", "phone"]
        )
        
        assert key.key == "res.partner:record:123:email,name,phone"
        assert key.params["fields"] == ["name", "email", "phone"]

    def test_fields_sorted(self):
        """Test that fields are sorted in key."""
        key = make_model_cache_key(
            "res.partner", 
            123, 
            fields=["phone", "name", "email"]
        )
        
        # Fields should be sorted in the key
        assert key.key == "res.partner:record:123:email,name,phone"

    def test_custom_namespace(self):
        """Test with custom namespace."""
        key = make_model_cache_key("res.partner", 123, namespace="custom")
        
        assert key.namespace == "custom"


class TestMakeQueryCacheKey:
    """Test make_query_cache_key function."""

    def test_basic_query_key(self):
        """Test basic query key generation."""
        domain = [("active", "=", True)]
        key = make_query_cache_key("res.partner", domain)
        
        assert key.model == "res.partner"
        assert key.operation == "search_read"
        assert key.params["domain"] == domain

    def test_query_with_all_params(self):
        """Test query key with all parameters."""
        domain = [("active", "=", True)]
        fields = ["name", "email"]
        key = make_query_cache_key(
            model="res.partner",
            domain=domain,
            fields=fields,
            limit=10,
            offset=5,
            order="name ASC"
        )
        
        expected_params = {
            "domain": domain,
            "fields": fields,
            "limit": 10,
            "offset": 5,
            "order": "name ASC"
        }
        assert key.params == expected_params

    def test_none_values_filtered(self):
        """Test that None values are filtered from params."""
        domain = [("active", "=", True)]
        key = make_query_cache_key(
            model="res.partner",
            domain=domain,
            fields=None,
            limit=None,
            offset=0,  # 0 is not None, should be included
            order=None
        )
        
        expected_params = {
            "domain": domain,
            "offset": 0
        }
        assert key.params == expected_params


class TestHashParams:
    """Test _hash_params function."""

    def test_basic_hashing(self):
        """Test basic parameter hashing."""
        params = {"key": "value", "number": 123}
        hash_result = _hash_params(params)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 8  # Should be 8 characters

    def test_consistent_hashing(self):
        """Test that same params produce same hash."""
        params = {"key": "value", "number": 123}

        hash1 = _hash_params(params)
        hash2 = _hash_params(params)

        assert hash1 == hash2

    def test_order_independence(self):
        """Test that parameter order doesn't affect hash."""
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}

        hash1 = _hash_params(params1)
        hash2 = _hash_params(params2)

        assert hash1 == hash2

    def test_different_values_different_hash(self):
        """Test that different values produce different hash."""
        params1 = {"key": "value1"}
        params2 = {"key": "value2"}

        hash1 = _hash_params(params1)
        hash2 = _hash_params(params2)

        assert hash1 != hash2

    def test_complex_params(self):
        """Test hashing with complex parameter structures."""
        params = {
            "domain": [("active", "=", True), ("name", "ilike", "test")],
            "fields": ["name", "email", "phone"],
            "limit": 10,
            "context": {"lang": "en_US", "tz": "UTC"}
        }

        hash_result = _hash_params(params)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 8

    def test_none_values_in_params(self):
        """Test hashing with None values."""
        params = {"key": "value", "none_key": None, "number": 123}

        # Should not raise error
        hash_result = _hash_params(params)
        assert isinstance(hash_result, str)

    def test_unhashable_params_handled(self):
        """Test that unhashable parameters are handled gracefully."""
        # Create a mock object that will be converted to string
        class CustomObject:
            def __str__(self):
                return "custom_object_string"

        params = {"key": "value", "custom_object": CustomObject()}

        # Should not raise error due to default=str in json.dumps
        hash_result = _hash_params(params)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 8


class TestValidateCacheKey:
    """Test validate_cache_key function."""

    def test_valid_string_key(self):
        """Test validation with valid string key."""
        key = "res.partner:search:abc123"
        result = validate_cache_key(key)
        assert result == key

    def test_valid_cache_key_object(self):
        """Test validation with CacheKey object."""
        cache_key = CacheKey(key="res.partner:search", namespace="test")
        result = validate_cache_key(cache_key)
        assert result == "res.partner:search"

    def test_empty_string_error(self):
        """Test error with empty string."""
        with pytest.raises(CacheKeyError, match="Cache key cannot be empty"):
            validate_cache_key("")

    def test_none_key_error(self):
        """Test error with None key."""
        with pytest.raises(CacheKeyError, match="Invalid cache key type"):
            validate_cache_key(None)

    def test_invalid_type_error(self):
        """Test error with invalid key type."""
        with pytest.raises(CacheKeyError, match="Invalid cache key type"):
            validate_cache_key(123)

    def test_too_long_key_error(self):
        """Test error with key that's too long."""
        long_key = "a" * 251  # Exceeds 250 character limit
        with pytest.raises(CacheKeyError, match="Cache key too long"):
            validate_cache_key(long_key)

    def test_key_with_spaces_error(self):
        """Test error with spaces in key."""
        with pytest.raises(
            CacheKeyError, match="Cache key contains invalid character"
        ):
            validate_cache_key("key with spaces")

    def test_key_with_newline_error(self):
        """Test error with newline in key."""
        with pytest.raises(
            CacheKeyError, match="Cache key contains invalid character"
        ):
            validate_cache_key("key\nwith\nnewline")

    def test_key_with_tab_error(self):
        """Test error with tab in key."""
        with pytest.raises(
            CacheKeyError, match="Cache key contains invalid character"
        ):
            validate_cache_key("key\twith\ttab")

    def test_key_with_carriage_return_error(self):
        """Test error with carriage return in key."""
        with pytest.raises(
            CacheKeyError, match="Cache key contains invalid character"
        ):
            validate_cache_key("key\rwith\rcarriage")

    def test_maximum_valid_length(self):
        """Test key with maximum valid length."""
        max_key = "a" * 250  # Exactly 250 characters
        result = validate_cache_key(max_key)
        assert result == max_key


class TestParseCacheKey:
    """Test parse_cache_key function."""

    def test_simple_key_parsing(self):
        """Test parsing simple cache key."""
        key = "res.partner:search"
        result = parse_cache_key(key)

        expected = {"model": "res.partner", "operation": "search"}
        assert result == expected

    def test_key_with_hash_parsing(self):
        """Test parsing key with hash."""
        key = "res.partner:search:abc12345"
        result = parse_cache_key(key)

        expected = {
            "model": "res.partner",
            "operation": "search",
            "hash": "abc12345"
        }
        assert result == expected

    def test_key_with_extra_parts_parsing(self):
        """Test parsing key with extra parts."""
        key = "res.partner:record:123:name,email"
        result = parse_cache_key(key)

        expected = {
            "model": "res.partner",
            "operation": "record",
            "hash": "123",
            "extra": "name,email"
        }
        assert result == expected

    def test_single_part_key(self):
        """Test parsing key with single part."""
        key = "simple_key"
        result = parse_cache_key(key)

        expected = {"raw_key": "simple_key"}
        assert result == expected

    def test_empty_key_parsing(self):
        """Test parsing empty key."""
        key = ""
        result = parse_cache_key(key)

        expected = {"raw_key": ""}
        assert result == expected

    def test_complex_key_parsing(self):
        """Test parsing complex key with multiple colons."""
        key = "product.product:search_read:abc123:name,categ_id:extra:data"
        result = parse_cache_key(key)

        expected = {
            "model": "product.product",
            "operation": "search_read",
            "hash": "abc123",
            "extra": "name,categ_id:extra:data"
        }
        assert result == expected


class TestCacheKeyIntegration:
    """Test integration between different cache key functions."""

    def test_make_and_validate_integration(self):
        """Test integration between make_cache_key and validate_cache_key."""
        params = {"domain": [("active", "=", True)], "limit": 10}
        cache_key = make_cache_key("res.partner", "search", params)

        # Should validate successfully
        validated = validate_cache_key(cache_key)
        assert validated == cache_key.key

    def test_make_and_parse_integration(self):
        """Test integration between make_cache_key and parse_cache_key."""
        params = {"domain": [("active", "=", True)]}
        cache_key = make_cache_key("res.partner", "search", params)

        parsed = parse_cache_key(cache_key.key)

        assert parsed["model"] == "res.partner"
        assert parsed["operation"] == "search"
        assert "hash" in parsed  # Should have hash from params

    def test_model_key_and_parse_integration(self):
        """Test make_model_cache_key and parse_cache_key integration."""
        cache_key = make_model_cache_key("res.partner", 123, ["name", "email"])

        parsed = parse_cache_key(cache_key.key)

        assert parsed["model"] == "res.partner"
        assert parsed["operation"] == "record"
        assert parsed["hash"] == "123"
        assert parsed["extra"] == "email,name"

    def test_query_key_and_validate_integration(self):
        """Test make_query_cache_key and validate_cache_key integration."""
        domain = [("active", "=", True)]
        cache_key = make_query_cache_key("res.partner", domain, limit=10)

        # Should validate successfully
        validated = validate_cache_key(cache_key)
        assert validated == cache_key.key

    def test_cache_key_methods_integration(self):
        """Test integration of CacheKey methods."""
        original = make_cache_key("res.partner", "search")

        # Test with_suffix
        suffixed = original.with_suffix("abc123")
        validated_suffixed = validate_cache_key(suffixed)
        assert "abc123" in validated_suffixed

        # Test with_prefix
        prefixed = original.with_prefix("cached")
        validated_prefixed = validate_cache_key(prefixed)
        assert validated_prefixed.startswith("cached:")

    def test_full_workflow(self):
        """Test complete cache key workflow."""
        # 1. Create cache key
        params = {
            "domain": [("is_company", "=", True)],
            "fields": ["name", "email", "phone"],
            "limit": 50
        }
        cache_key = make_cache_key("res.partner", "search_read", params)

        # 2. Validate key
        validated = validate_cache_key(cache_key)

        # 3. Parse key
        parsed = parse_cache_key(validated)

        # 4. Verify all components
        assert parsed["model"] == "res.partner"
        assert parsed["operation"] == "search_read"
        assert "hash" in parsed

        # 5. Test key modifications
        suffixed = cache_key.with_suffix("v2")
        prefixed = cache_key.with_prefix("temp")

        # Both should still be valid
        validate_cache_key(suffixed)
        validate_cache_key(prefixed)

        # 6. Test full key
        full_key = cache_key.full_key
        assert full_key.startswith("odooflow:")
        assert cache_key.key in full_key
