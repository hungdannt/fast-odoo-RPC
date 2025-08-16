"""
Main Zenoo-RPC client implementation.

This module provides the primary interface for interacting with Odoo servers
through the Zenoo-RPC library. It combines transport, session management,
and high-level API features with zen-like simplicity.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, TYPE_CHECKING, Union

from .exceptions import AuthenticationError, ZenooError
from .transport import AsyncTransport, SessionManager

if TYPE_CHECKING:
    from .models.base import OdooModel
    from .models.registry import get_model_class, get_registry
    from .query.builder import QueryBuilder
    from .transaction.manager import TransactionManager
    from .cache.manager import CacheManager
    from .batch.manager import BatchManager
    from .ai.core.ai_assistant import AIAssistant

T = TypeVar("T")


class ZenooClient:
    """Main async client for Zenoo-RPC.

    This is the primary interface for interacting with Odoo servers. It provides
    a zen-like, modern async API with type safety, intelligent caching, and
    superior developer experience.

    Features:
    - Async-first design with httpx transport
    - Type-safe operations with Pydantic models
    - Fluent query builder
    - Intelligent caching and batch operations
    - Structured exception handling
    - Transaction management

    Examples:
        >>> # Using full URL
        >>> async with ZenooClient("https://demo.odoo.com") as client:
        ...     await client.login("demo", "admin", "admin")
        ...     partners = await client.model(ResPartner).filter(
        ...         is_company=True
        ...     ).limit(10).all()

        >>> # Using host with parameters
        >>> async with ZenooClient("localhost", port=8069,
        ...                        protocol="http") as client:
        ...     await client.login("mydb", "admin", "password")
        ...     # ... operations ...
    """

    def __init__(
        self,
        host_or_url: str,
        port: Optional[int] = None,
        protocol: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        """Initialize the OdooFlow client.

        This constructor supports multiple initialization patterns:

        1. Full URL:
            >>> client = OdooFlowClient("https://demo.odoo.com")
            >>> client = OdooFlowClient("http://localhost:8069")

        2. Host with separate parameters:
            >>> client = OdooFlowClient("demo.odoo.com", protocol="https")
            >>> client = OdooFlowClient("localhost", port=8069, protocol="http")

        3. Host only (defaults to http://host:8069):
            >>> client = OdooFlowClient("localhost")

        Args:
            host_or_url: Either a full URL or just the hostname/IP
            port: Port number (auto-detected from URL or defaults to 8069)
            protocol: Protocol ("http" or "https", auto-detected from URL or defaults to "http")
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        # Parse the input to determine if it's a URL or just a host
        base_url = self._parse_host_or_url(host_or_url, port, protocol)

        # Store parsed components for reference
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == "https" else 8069)
        self.protocol = parsed.scheme

        # Initialize transport and session manager
        self._transport = AsyncTransport(
            base_url=base_url,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )
        self._session = SessionManager()

        # Phase 3 features - initialized lazily
        self.transaction_manager: Optional["TransactionManager"] = None
        self.cache_manager: Optional["CacheManager"] = None
        self.batch_manager: Optional["BatchManager"] = None
        self._fallback_manager = None

        # AI features - initialized lazily
        self.ai: Optional["AIAssistant"] = None

    def _parse_host_or_url(
        self,
        host_or_url: str,
        port: Optional[int] = None,
        protocol: Optional[str] = None,
    ) -> str:
        """Parse host_or_url and return a complete base URL.

        Args:
            host_or_url: Either a full URL or just hostname/IP
            port: Optional port override
            protocol: Optional protocol override

        Returns:
            Complete base URL
        """
        from urllib.parse import urlparse

        # Check if input looks like a URL (has protocol)
        if "://" in host_or_url:
            parsed = urlparse(host_or_url)

            # Use provided overrides or parsed values
            final_protocol = protocol or parsed.scheme
            final_host = parsed.hostname
            final_port = port or parsed.port

            # Set default port if not specified
            if final_port is None:
                final_port = 443 if final_protocol == "https" else 8069

            return f"{final_protocol}://{final_host}:{final_port}"

        else:
            # Input is just a hostname/IP
            final_protocol = protocol or "http"
            final_host = host_or_url
            final_port = port or (443 if final_protocol == "https" else 8069)

            return f"{final_protocol}://{final_host}:{final_port}"

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self._session.is_authenticated

    @property
    def database(self) -> Optional[str]:
        """Get the current database name."""
        return self._session.database

    @property
    def uid(self) -> Optional[int]:
        """Get the current user ID."""
        return self._session.uid

    @property
    def username(self) -> Optional[str]:
        """Get the current username."""
        return self._session.username

    @property
    def server_version(self) -> Optional[Dict[str, Any]]:
        """Get server version information."""
        return self._session.server_version

    async def login(self, database: str, username: str, password: str) -> None:
        """Authenticate with the Odoo server.

        Args:
            database: Database name to connect to
            username: Username for authentication
            password: Password for authentication

        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection to server fails
        """
        await self._session.authenticate(self._transport, database, username, password)

    async def login_with_api_key(
        self, database: str, username: str, api_key: str
    ) -> None:
        """Authenticate with the Odoo server using API key.

        Args:
            database: Database name to connect to
            username: Username for authentication
            api_key: API key for authentication

        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection to server fails
        """
        await self._session.authenticate_with_api_key(
            self._transport, database, username, api_key
        )

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a method on an Odoo model.

        This is the low-level method for calling Odoo model methods directly.
        Higher-level APIs should be preferred when available.

        Args:
            model: Name of the Odoo model (e.g., "res.partner")
            method: Method name to call (e.g., "search", "read", "write")
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method
            context: Additional context for the call

        Returns:
            The result of the method call

        Raises:
            AuthenticationError: If not authenticated
            ZenooError: If the server returns an error
        """
        if not self.is_authenticated:
            raise AuthenticationError("Not authenticated. Call login() first.")

        # Prepare call context
        call_context = self._session.get_call_context(context)

        # Prepare parameters
        params = {
            "args": [
                self._session.database,
                self._session.uid,
                self._session.password,  # Use stored password
                model,
                method,
                args,
                kwargs or {},
            ]
        }

        # Add context if provided
        if call_context:
            if len(params["args"]) >= 7:
                params["args"][6]["context"] = call_context
            else:
                params["args"].append({"context": call_context})

        # Make the RPC call
        result = await self._transport.json_rpc_call("object", "execute_kw", params)
        return result.get("result")

    async def execute(
        self,
        model: str,
        method: str,
        *args: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a method on an Odoo model (simplified interface).

        Args:
            model: Name of the Odoo model
            method: Method name to call
            *args: Arguments for the method
            context: Additional context for the call

        Returns:
            The result of the method call
        """
        return await self.execute_kw(model, method, list(args), context=context)

    async def search_read(
        self,
        model: str,
        domain: List[Any],
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search and read records in a single call (optimized).

        This method combines search and read operations into a single RPC call
        for better performance, which is one of the key improvements over odoorpc.

        Args:
            model: Name of the Odoo model
            domain: Search domain (list of tuples)
            fields: Fields to read (None for all fields)
            limit: Maximum number of records to return
            offset: Number of records to skip
            order: Sort order specification
            context: Additional context for the call

        Returns:
            List of record dictionaries
        """
        kwargs = {}
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if offset:
            kwargs["offset"] = offset
        if order:
            kwargs["order"] = order

        return await self.execute_kw(
            model, "search_read", [domain], kwargs, context=context
        )

    async def search_count(
        self,
        model: str,
        domain: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count records matching the domain.

        Args:
            model: Name of the Odoo model
            domain: Search domain (list of tuples)
            context: Optional context for the operation

        Returns:
            Number of records matching the domain

        Raises:
            AuthenticationError: If not authenticated
            ZenooError: If the server returns an error
        """
        return await self.execute_kw(
            model,
            "search_count",
            [domain],
            context=context,
        )

    async def read(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Read records by IDs.

        Args:
            model: Name of the Odoo model
            ids: List of record IDs to read
            fields: List of field names to read (None for all fields)
            context: Optional context for the operation

        Returns:
            List of record data dictionaries

        Raises:
            AuthenticationError: If not authenticated
            ZenooError: If the server returns an error
        """
        kwargs = {}
        if fields:
            kwargs["fields"] = fields

        return await self.execute_kw(
            model,
            "read",
            [ids],
            kwargs,
            context=context,
        )

    async def get_model_fields(
        self,
        model: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Get field definitions for a model.

        Args:
            model: Name of the Odoo model
            context: Optional context for the operation

        Returns:
            Dictionary mapping field names to field definitions

        Raises:
            AuthenticationError: If not authenticated
            ZenooError: If the server returns an error
        """
        return await self.execute_kw(
            model,
            "fields_get",
            [],
            context=context,
        )

    # CRUD Operations
    async def create(
        self,
        model: str,
        values: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        validate_required: bool = True,
    ) -> int:
        """Create a new record with enhanced validation and error handling.

        Args:
            model: Name of the Odoo model (e.g., "res.partner")
            values: Dictionary of field values for the new record
            context: Optional context for the operation
            validate_required: Whether to validate required fields before creation

        Returns:
            ID of the newly created record

        Raises:
            AuthenticationError: If not authenticated
            ValidationError: If invalid values are provided or required fields missing
            AccessError: If user lacks create permissions
            ZenooError: If the server returns an error

        Example:
            >>> partner_id = await client.create(
            ...     "res.partner",
            ...     {"name": "New Partner", "email": "partner@example.com"}
            ... )
        """
        if not self.is_authenticated:
            raise AuthenticationError("Not authenticated. Call login() first.")

        # Validate required fields if requested
        if validate_required:
            await self._validate_required_fields(model, values)

        try:
            return await self.execute_kw(
                model,
                "create",
                [values],
                context=context,
            )
        except Exception as e:
            # Enhanced error handling for create operations
            raise await self._handle_crud_error(e, "create", model, values)

    async def write(
        self,
        model: str,
        ids: List[int],
        values: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        check_access: bool = True,
    ) -> bool:
        """Update existing records with enhanced error handling.

        Args:
            model: Name of the Odoo model (e.g., "res.partner")
            ids: List of record IDs to update
            values: Dictionary of field values to update
            context: Optional context for the operation
            check_access: Whether to check record access before update

        Returns:
            True if successful

        Raises:
            AuthenticationError: If not authenticated
            ValidationError: If invalid values are provided
            AccessError: If user lacks write permissions or record access
            ZenooError: If the server returns an error

        Example:
            >>> success = await client.write(
            ...     "res.partner",
            ...     [1, 2, 3],
            ...     {"active": False}
            ... )
        """
        if not self.is_authenticated:
            raise AuthenticationError("Not authenticated. Call login() first.")

        # Check if records exist and are accessible if requested
        if check_access and ids:
            await self._check_record_access(model, ids, "write")

        try:
            return await self.execute_kw(
                model,
                "write",
                [ids, values],
                context=context,
            )
        except Exception as e:
            # Enhanced error handling for write operations
            raise await self._handle_crud_error(e, "write", model, {"ids": ids, "values": values})

    async def unlink(
        self,
        model: str,
        ids: List[int],
        context: Optional[Dict[str, Any]] = None,
        check_references: bool = True,
    ) -> bool:
        """Delete records with enhanced error handling.

        Args:
            model: Name of the Odoo model (e.g., "res.partner")
            ids: List of record IDs to delete
            context: Optional context for the operation
            check_references: Whether to check for referential constraints

        Returns:
            True if successful

        Raises:
            AuthenticationError: If not authenticated
            AccessError: If user lacks delete permissions
            ValidationError: If records have referential constraints
            ZenooError: If the server returns an error

        Example:
            >>> success = await client.unlink("res.partner", [1, 2, 3])
        """
        if not self.is_authenticated:
            raise AuthenticationError("Not authenticated. Call login() first.")

        # Check if records exist and are accessible
        if ids:
            await self._check_record_access(model, ids, "unlink")

        try:
            return await self.execute_kw(
                model,
                "unlink",
                [ids],
                context=context,
            )
        except Exception as e:
            # Enhanced error handling for unlink operations
            raise await self._handle_crud_error(e, "unlink", model, {"ids": ids})

    async def health_check(self) -> bool:
        """Check if the Odoo server is healthy and reachable.

        Returns:
            True if server is healthy, False otherwise
        """
        return await self._transport.health_check()

    async def get_server_version(self) -> Dict[str, Any]:
        """Get server version information.

        Returns:
            Dictionary containing server version details
        """
        result = await self._transport.json_rpc_call("common", "version", {})
        return result.get("result", {})

    async def list_databases(self) -> List[str]:
        """List available databases on the server.

        Returns:
            List of database names
        """
        result = await self._transport.json_rpc_call("db", "list", {})
        return result.get("result", [])

    async def close(self) -> None:
        """Close the client and clean up resources."""
        # Close AI assistant if initialized
        if self.ai is not None:
            await self.ai.close()

        # Close other managers
        if self.cache_manager is not None:
            await self.cache_manager.close()

        # Close transport and clear session
        await self._transport.close()
        self._session.clear()

    async def __aenter__(self) -> "ZenooClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def model(self, model_class: Type[T]) -> "QueryBuilder[T]":
        """Get a query builder for a model class.

        Args:
            model_class: The model class to query

        Returns:
            QueryBuilder instance for the model

        Example:
            >>> from odooflow.models import ResPartner
            >>>
            >>> # Get query builder
            >>> partners = client.model(ResPartner)
            >>>
            >>> # Build and execute query
            >>> companies = await partners.filter(is_company=True).all()
        """
        if not self.is_authenticated:
            raise AuthenticationError("Not authenticated. Call login() first.")

        from .query.builder import QueryBuilder

        return QueryBuilder(model_class, self)

    async def get_or_create_model(self, model_name: str) -> Type["OdooModel"]:
        """Get or create a model class for the given Odoo model name.

        Args:
            model_name: The Odoo model name (e.g., "res.partner")

        Returns:
            Model class (either registered or dynamically created)
        """
        from .models.registry import get_registry

        registry = get_registry()

        # Check if model is already registered
        model_class = registry.get_model(model_name)
        if model_class:
            return model_class

        # Create dynamic model
        return await registry.create_dynamic_model(model_name, self)

    # Phase 3 Features

    async def setup_transaction_manager(
        self,
        max_active_transactions: int = 100,
        default_timeout: int = 300,
        **kwargs
    ) -> "TransactionManager":
        """Setup transaction manager for the client.

        Args:
            max_active_transactions: Maximum concurrent transactions
            default_timeout: Default transaction timeout in seconds
            **kwargs: Additional transaction manager options

        Returns:
            TransactionManager instance
        """
        if self.transaction_manager is None:
            from .transaction.manager import TransactionManager

            self.transaction_manager = TransactionManager(client=self)

        return self.transaction_manager

    async def setup_cache_manager(
        self,
        backend: str = "memory",
        url: Optional[str] = None,
        enable_fallback: bool = True,
        circuit_breaker_threshold: int = 5,
        max_size: int = 1000,
        ttl: int = 300,
        **kwargs
    ) -> "CacheManager":
        """Setup cache manager for the client.

        Args:
            backend: Cache backend ("memory" or "redis")
            url: Redis URL (for redis backend)
            enable_fallback: Enable fallback to memory cache
            circuit_breaker_threshold: Circuit breaker failure threshold
            max_size: Maximum cache size (for memory backend)
            ttl: Default TTL in seconds
            **kwargs: Backend-specific configuration

        Returns:
            CacheManager instance
        """
        if self.cache_manager is None:
            from .cache.manager import CacheManager

            self.cache_manager = CacheManager()

            if backend == "memory":
                await self.cache_manager.setup_memory_cache(
                    max_size=max_size,
                    default_ttl=ttl,
                    **kwargs
                )
            elif backend == "redis":
                await self.cache_manager.setup_redis_cache(
                    url=url or "redis://localhost:6379/0",
                    enable_fallback=enable_fallback,
                    circuit_breaker_threshold=circuit_breaker_threshold,
                    ttl=ttl,
                    **kwargs
                )

        return self.cache_manager

    async def setup_batch_manager(
        self,
        max_chunk_size: int = 100,
        max_concurrency: int = 5,
        timeout: Optional[int] = None,
    ) -> "BatchManager":
        """Setup batch manager for the client.

        Args:
            max_chunk_size: Maximum records per chunk
            max_concurrency: Maximum concurrent operations
            timeout: Operation timeout in seconds

        Returns:
            BatchManager instance
        """
        if self.batch_manager is None:
            from .batch.manager import BatchManager

            self.batch_manager = BatchManager(
                client=self,
                max_chunk_size=max_chunk_size,
                max_concurrency=max_concurrency,
                timeout=timeout,
            )

        return self.batch_manager

    async def setup_ai(
        self,
        provider: str = "gemini",
        model: str = "gemini-2.5-flash-lite",
        api_key: str = "",
        **config_kwargs
    ) -> "AIAssistant":
        """Setup AI capabilities for the client.

        This method initializes AI-powered features including:
        - Natural language to Odoo query conversion
        - Intelligent error diagnosis and solutions
        - Smart code generation and optimization
        - Performance analysis and recommendations

        Args:
            provider: AI provider (gemini, openai, anthropic, azure)
            model: Model name (e.g., "gemini-2.5-flash-lite")
            api_key: API key for the provider
            **config_kwargs: Additional configuration parameters

        Returns:
            AIAssistant instance

        Raises:
            ImportError: If AI dependencies are not installed
            ValueError: If required parameters are missing

        Example:
            >>> async with ZenooClient("localhost") as client:
            ...     await client.login("demo", "admin", "admin")
            ...
            ...     # Setup AI with Gemini
            ...     await client.setup_ai(
            ...         provider="gemini",
            ...         model="gemini-2.5-flash-lite",
            ...         api_key="your-api-key"
            ...     )
            ...
            ...     # Use AI features
            ...     partners = await client.ai.query("Find all companies in Vietnam")
            ...     diagnosis = await client.ai.diagnose(error)
        """
        if self.ai is None:
            try:
                from .ai.core.ai_assistant import AIAssistant

                self.ai = AIAssistant(self)
                await self.ai.initialize(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    **config_kwargs
                )

            except ImportError as e:
                raise ImportError(
                    "AI features require additional dependencies. "
                    "Install with: pip install zenoo-rpc[ai]"
                ) from e

        return self.ai

    # Removed old transaction method - see new implementation below

    # Removed old batch method - see new implementation below

    # Enhanced Error Handling and Validation Methods

    async def _validate_required_fields(
        self, model: str, values: Dict[str, Any]
    ) -> None:
        """Validate that all required fields are provided for create operation.

        Args:
            model: The Odoo model name
            values: The values dictionary for creation

        Raises:
            ValidationError: If required fields are missing
        """
        try:
            # Get model fields to check required ones
            fields_info = await self.get_model_fields(model)

            missing_required = []
            for field_name, field_info in fields_info.items():
                if (field_info.get("required", False) and
                    field_name not in values and
                    field_name not in ["id", "create_date", "write_date", "create_uid", "write_uid"]):
                    missing_required.append(field_name)

            if missing_required:
                from .exceptions import ValidationError
                raise ValidationError(
                    f"Missing required fields for {model}: {', '.join(missing_required)}",
                    context={"model": model, "missing_fields": missing_required}
                )

        except Exception as e:
            # If we can't validate, log warning but don't fail
            # This allows operation to proceed and let Odoo handle validation
            pass  # nosec B110

    async def _handle_crud_error(
        self,
        error: Exception,
        operation: str,
        model: str,
        data: Any = None
    ) -> Exception:
        """Enhanced error handling for CRUD operations.

        Args:
            error: The original exception
            operation: The CRUD operation (create, read, write, unlink)
            model: The Odoo model name
            data: The data involved in the operation

        Returns:
            Enhanced exception with better context
        """
        from .exceptions import AccessError, ValidationError, ZenooError

        error_msg = str(error)

        # Handle common permission errors
        if "access" in error_msg.lower() or "permission" in error_msg.lower():
            return AccessError(
                f"Access denied for {operation} operation on {model}. "
                f"Please check user permissions and access rights.",
                context={
                    "operation": operation,
                    "model": model,
                    "original_error": error_msg
                }
            )

        # Handle validation errors
        if "validation" in error_msg.lower() or "constraint" in error_msg.lower():
            return ValidationError(
                f"Validation failed for {operation} operation on {model}: {error_msg}",
                context={
                    "operation": operation,
                    "model": model,
                    "data": data,
                    "original_error": error_msg
                }
            )

        # Handle referential integrity errors (for unlink)
        if operation == "unlink" and ("foreign key" in error_msg.lower() or
                                     "referenced" in error_msg.lower()):
            return ValidationError(
                f"Cannot delete {model} record(s) because they are referenced by other records. "
                f"Please remove the references first or use cascade delete if appropriate.",
                context={
                    "operation": operation,
                    "model": model,
                    "data": data,
                    "original_error": error_msg
                }
            )

        # Return original error if no specific handling applies
        return error

    async def check_model_access(
        self,
        model: str,
        operation: str = "read"
    ) -> bool:
        """Check if current user has access to perform operation on model.

        Args:
            model: The Odoo model name
            operation: The operation to check (create, read, write, unlink)

        Returns:
            True if user has access, False otherwise
        """
        try:
            # Try to perform a minimal operation to check access
            if operation == "read":
                await self.execute_kw(model, "search", [[]], {"limit": 1})
            elif operation == "create":
                # Try to get fields (this requires some level of access)
                await self.get_model_fields(model)
            elif operation in ["write", "unlink"]:
                # For write/unlink, we need to find a record first
                ids = await self.execute_kw(model, "search", [[]], {"limit": 1})
                if ids and operation == "write":
                    # Try to write with empty values (should fail gracefully if no access)
                    await self.execute_kw(model, "check_access_rights", [operation])
                elif ids and operation == "unlink":
                    await self.execute_kw(model, "check_access_rights", [operation])

            return True

        except Exception:
            return False

    async def get_user_permissions(self, model: str) -> Dict[str, bool]:
        """Get user permissions for a specific model.

        Args:
            model: The Odoo model name

        Returns:
            Dictionary with permission flags for create, read, write, unlink
        """
        permissions = {
            "create": False,
            "read": False,
            "write": False,
            "unlink": False
        }

        for operation in permissions.keys():
            permissions[operation] = await self.check_model_access(model, operation)

        return permissions

    async def _check_record_access(
        self,
        model: str,
        ids: List[int],
        operation: str
    ) -> None:
        """Check if user has access to specific records.

        Args:
            model: The Odoo model name
            ids: List of record IDs to check
            operation: The operation to check (read, write, unlink)

        Raises:
            AccessError: If user lacks access to any of the records
        """
        try:
            # Try to read the records to check access
            # This is more efficient than checking each record individually
            accessible_records = await self.execute_kw(
                model,
                "search_read",
                [[("id", "in", ids)]],
                {"fields": ["id"], "limit": len(ids)}
            )

            accessible_ids = [r["id"] for r in accessible_records]
            inaccessible_ids = [id for id in ids if id not in accessible_ids]

            if inaccessible_ids:
                from .exceptions import AccessError
                raise AccessError(
                    f"Access denied to {model} records {inaccessible_ids} for {operation} operation. "
                    f"Records may not exist or user lacks permissions.",
                    context={
                        "model": model,
                        "operation": operation,
                        "inaccessible_ids": inaccessible_ids,
                        "accessible_ids": accessible_ids
                    }
                )

        except Exception as e:
            # If it's already an AccessError, re-raise it
            if "AccessError" in str(type(e)):
                raise e
            # For other errors, we'll let the main operation handle them
            pass

    async def safe_create(
        self,
        model: str,
        values: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        fallback_on_error: bool = True,
    ) -> Optional[int]:
        """Safe create operation with fallback handling.

        Args:
            model: Name of the Odoo model
            values: Dictionary of field values for the new record
            context: Optional context for the operation
            fallback_on_error: Whether to return None on error instead of raising

        Returns:
            ID of the newly created record, or None if failed and fallback enabled
        """
        try:
            return await self.create(model, values, context, validate_required=False)
        except Exception as e:
            if fallback_on_error:
                # Log the error but don't raise
                return None
            else:
                raise e

    async def safe_read(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        use_search_read: bool = True,
    ) -> List[Dict[str, Any]]:
        """Safe read operation using search_read as fallback.

        Args:
            model: Name of the Odoo model
            ids: List of record IDs to read
            fields: List of field names to read
            context: Optional context for the operation
            use_search_read: Whether to use search_read instead of direct read

        Returns:
            List of record dictionaries
        """
        try:
            if use_search_read:
                # Use search_read which handles access control better
                return await self.search_read(
                    model,
                    domain=[("id", "in", ids)],
                    fields=fields,
                    context=context
                )
            else:
                # Try direct read first
                return await self.read(model, ids, fields, context)
        except Exception:
            # Fallback to search_read if direct read fails
            if not use_search_read:
                return await self.search_read(
                    model,
                    domain=[("id", "in", ids)],
                    fields=fields,
                    context=context
                )
            else:
                # If search_read also fails, return empty list
                return []

    @property
    def fallback_manager(self):
        """Get or create fallback manager instance.

        Returns:
            FallbackManager instance for handling operation fallbacks
        """
        if self._fallback_manager is None:
            from .utils.fallback import FallbackManager
            self._fallback_manager = FallbackManager(self)
        return self._fallback_manager

    # Convenience methods using fallback manager

    async def safe_create_record(
        self,
        model: str,
        values: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Create record with automatic fallback handling.

        Args:
            model: Odoo model name
            values: Field values for creation
            context: Optional context

        Returns:
            Created record ID or None if failed
        """
        return await self.fallback_manager.safe_create_with_fallback(
            model, values, context, required_fields_only=True
        )

    async def get_accessible_records(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get only records that are accessible to current user.

        Args:
            model: Odoo model name
            ids: List of record IDs
            fields: Fields to retrieve
            context: Optional context

        Returns:
            List of accessible records
        """
        return await self.fallback_manager.get_accessible_records(
            model, ids, fields, context
        )

    async def adaptive_read_records(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Read records with adaptive strategy based on access permissions.

        Args:
            model: Odoo model name
            ids: Record IDs to read
            fields: Fields to retrieve
            context: Optional context

        Returns:
            List of accessible records
        """
        return await self.fallback_manager.adaptive_read(
            model, ids, fields, context
        )

    # Transaction and Batch Management Setup Methods

    async def setup_transaction_manager(
        self,
        isolation_level: str = "READ_COMMITTED",
        auto_commit: bool = False,
        max_retries: int = 3
    ) -> None:
        """Setup transaction manager for ACID transaction support.

        Args:
            isolation_level: Database isolation level
            auto_commit: Whether to auto-commit transactions
            max_retries: Maximum number of retry attempts

        Note:
            This method initializes the transaction manager but doesn't
            start a transaction. Use client.transaction() context manager
            to start actual transactions.
        """
        # Import here to avoid circular imports
        from .transaction.manager import TransactionManager

        if not hasattr(self, '_transaction_manager'):
            self._transaction_manager = TransactionManager(client=self)

        # Transaction manager is ready to use

    async def setup_batch_manager(
        self,
        max_chunk_size: int = 100,
        max_concurrent_batches: int = 5,
        retry_failed_operations: bool = True
    ) -> None:
        """Setup batch manager for efficient bulk operations.

        Args:
            max_chunk_size: Maximum number of records per batch
            max_concurrent_batches: Maximum concurrent batch operations
            retry_failed_operations: Whether to retry failed operations

        Note:
            This method initializes the batch manager. Use client.batch()
            context manager to perform actual batch operations.
        """
        # Import here to avoid circular imports
        from .batch.manager import BatchManager

        if not hasattr(self, '_batch_manager'):
            self._batch_manager = BatchManager(
                client=self,
                max_chunk_size=max_chunk_size,
                max_concurrency=max_concurrent_batches,
                timeout=None  # Use default timeout
            )

        # Batch manager is ready to use

    def transaction(self):
        """Create a transaction context manager.

        Returns:
            Transaction context manager for ACID operations

        Raises:
            RuntimeError: If transaction manager is not initialized

        Example:
            >>> await client.setup_transaction_manager()
            >>> async with client.transaction() as tx:
            ...     partner = await client.model(ResPartner).create(name="Test")
            ...     await partner.update(phone="+123456789")
            ...     # Automatically committed on successful exit
        """
        if not hasattr(self, '_transaction_manager'):
            raise RuntimeError(
                "Transaction manager not initialized. "
                "Call setup_transaction_manager() first."
            )

        return self._transaction_manager.transaction()

    def batch(self):
        """Create a batch context manager.

        Returns:
            Batch context manager for bulk operations

        Raises:
            RuntimeError: If batch manager is not initialized

        Example:
            >>> await client.setup_batch_manager(max_chunk_size=50)
            >>> async with client.batch() as batch:
            ...     partners_data = [{"name": f"Partner {i}"} for i in range(100)]
            ...     partners = await batch.create_many(ResPartner, partners_data)
        """
        if not hasattr(self, '_batch_manager'):
            raise RuntimeError(
                "Batch manager not initialized. "
                "Call setup_batch_manager() first."
            )

        return self._batch_manager.batch()
