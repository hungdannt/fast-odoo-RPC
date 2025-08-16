"""
Cache key management for OdooFlow.

This module provides utilities for generating, validating,
and managing cache keys with proper namespacing and hashing.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from .exceptions import CacheKeyError


@dataclass
class CacheKey:
    """Represents a cache key with metadata.

    This class encapsulates cache key information including
    the key itself, namespace, and metadata for debugging.

    Attributes:
        key: The actual cache key string
        namespace: Cache namespace for organization
        model: Odoo model name (if applicable)
        operation: Operation type (if applicable)
        params: Parameters used to generate the key
    """

    key: str
    namespace: str = "odooflow"
    model: Optional[str] = None
    operation: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate cache key after initialization.

        Raises:
            CacheKeyError: If key or namespace is invalid
        """
        # Validate key
        if not self.key or not isinstance(self.key, str):
            raise CacheKeyError("Cache key must be a non-empty string")

        # Validate namespace
        if not self.namespace or not isinstance(self.namespace, str):
            raise CacheKeyError("Cache namespace must be a non-empty string")

        # Check for invalid characters in key
        if " " in self.key:
            raise CacheKeyError("Cache key cannot contain spaces")

    def __str__(self) -> str:
        """Return the cache key string."""
        return self.key

    def __hash__(self) -> int:
        """Return hash of the cache key."""
        return hash(self.key)

    def __eq__(self, other) -> bool:
        """Check equality with another cache key."""
        if isinstance(other, CacheKey):
            return self.key == other.key
        elif isinstance(other, str):
            return self.key == other
        return False

    @property
    def full_key(self) -> str:
        """Get the full namespaced key."""
        return f"{self.namespace}:{self.key}"

    def with_suffix(self, suffix: str) -> "CacheKey":
        """Create a new cache key with a suffix.

        Args:
            suffix: Suffix to append

        Returns:
            New CacheKey instance
        """
        return CacheKey(
            key=f"{self.key}:{suffix}",
            namespace=self.namespace,
            model=self.model,
            operation=self.operation,
            params=self.params,
        )

    def with_prefix(self, prefix: str) -> "CacheKey":
        """Create a new cache key with a prefix.

        Args:
            prefix: Prefix to prepend

        Returns:
            New CacheKey instance
        """
        return CacheKey(
            key=f"{prefix}:{self.key}",
            namespace=self.namespace,
            model=self.model,
            operation=self.operation,
            params=self.params,
        )


def make_cache_key(
    model: str,
    operation: str,
    params: Optional[Dict[str, Any]] = None,
    namespace: str = "odooflow",
    include_hash: bool = True,
) -> CacheKey:
    """Generate a cache key for Odoo operations.

    This function creates a standardized cache key based on
    the model, operation, and parameters.

    Args:
        model: Odoo model name (e.g., "res.partner")
        operation: Operation type (e.g., "search", "read", "count")
        params: Operation parameters (filters, fields, etc.)
        namespace: Cache namespace
        include_hash: Whether to include parameter hash in key

    Returns:
        CacheKey instance

    Example:
        >>> key = make_cache_key(
        ...     model="res.partner",
        ...     operation="search",
        ...     params={"domain": [("is_company", "=", True)], "limit": 10}
        ... )
        >>> print(key.key)
        res.partner:search:a1b2c3d4
    """
    if not model:
        raise CacheKeyError("Model name is required for cache key")

    if not operation:
        raise CacheKeyError("Operation is required for cache key")

    # Start with model and operation
    key_parts = [model, operation]

    # Add parameter hash if requested and params exist
    if include_hash and params:
        param_hash = _hash_params(params)
        key_parts.append(param_hash)

    # Join parts with colon
    cache_key = ":".join(key_parts)

    return CacheKey(
        key=cache_key,
        namespace=namespace,
        model=model,
        operation=operation,
        params=params,
    )


def make_model_cache_key(
    model: str,
    record_id: Union[int, List[int]],
    fields: Optional[List[str]] = None,
    namespace: str = "odooflow",
) -> CacheKey:
    """Generate a cache key for model record(s).

    Args:
        model: Odoo model name
        record_id: Record ID or list of IDs
        fields: Fields to include in key
        namespace: Cache namespace

    Returns:
        CacheKey instance

    Example:
        >>> key = make_model_cache_key("res.partner", 123, ["name", "email"])
        >>> print(key.key)
        res.partner:record:123:name,email
    """
    if isinstance(record_id, list):
        id_str = ",".join(map(str, sorted(record_id)))
    else:
        id_str = str(record_id)

    key_parts = [model, "record", id_str]

    if fields:
        fields_str = ",".join(sorted(fields))
        key_parts.append(fields_str)

    cache_key = ":".join(key_parts)

    return CacheKey(
        key=cache_key,
        namespace=namespace,
        model=model,
        operation="read",
        params={"ids": record_id, "fields": fields},
    )


def make_query_cache_key(
    model: str,
    domain: List[Any],
    fields: Optional[List[str]] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order: Optional[str] = None,
    namespace: str = "odooflow",
) -> CacheKey:
    """Generate a cache key for query operations.

    Args:
        model: Odoo model name
        domain: Search domain
        fields: Fields to retrieve
        limit: Result limit
        offset: Result offset
        order: Sort order
        namespace: Cache namespace

    Returns:
        CacheKey instance
    """
    params = {
        "domain": domain,
        "fields": fields,
        "limit": limit,
        "offset": offset,
        "order": order,
    }

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    return make_cache_key(
        model=model, operation="search_read", params=params, namespace=namespace
    )


def _hash_params(params: Dict[str, Any]) -> str:
    """Generate a hash for cache parameters.

    Args:
        params: Parameters to hash

    Returns:
        Hexadecimal hash string (first 8 characters)
    """
    try:
        # Convert to JSON for consistent hashing
        json_str = json.dumps(params, sort_keys=True, default=str)

        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(json_str.encode("utf-8"))

        # Return first 8 characters of hex digest
        return hash_obj.hexdigest()[:8]

    except (TypeError, ValueError) as e:
        raise CacheKeyError(f"Failed to hash parameters: {e}")


def validate_cache_key(key: Union[str, CacheKey]) -> str:
    """Validate and normalize a cache key.

    Args:
        key: Cache key to validate

    Returns:
        Validated key string

    Raises:
        CacheKeyError: If key is invalid
    """
    if isinstance(key, CacheKey):
        key_str = key.key
    elif isinstance(key, str):
        key_str = key
    else:
        raise CacheKeyError(f"Invalid cache key type: {type(key)}")

    if not key_str:
        raise CacheKeyError("Cache key cannot be empty")

    if len(key_str) > 250:  # Redis key limit
        raise CacheKeyError(f"Cache key too long: {len(key_str)} > 250")

    # Check for invalid characters
    invalid_chars = [" ", "\n", "\r", "\t"]
    for char in invalid_chars:
        if char in key_str:
            raise CacheKeyError(f"Cache key contains invalid character: '{char}'")

    return key_str


def parse_cache_key(key: str) -> Dict[str, str]:
    """Parse a cache key into its components.

    Args:
        key: Cache key to parse

    Returns:
        Dictionary with key components

    Example:
        >>> components = parse_cache_key("res.partner:search:a1b2c3d4")
        >>> print(components)
        {"model": "res.partner", "operation": "search", "hash": "a1b2c3d4"}
    """
    parts = key.split(":")

    if len(parts) < 2:
        return {"raw_key": key}

    components = {"model": parts[0], "operation": parts[1]}

    if len(parts) > 2:
        components["hash"] = parts[2]

    if len(parts) > 3:
        components["extra"] = ":".join(parts[3:])

    return components
