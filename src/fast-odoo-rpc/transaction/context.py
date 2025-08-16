"""
Transaction context managers and decorators for OdooFlow.

This module provides convenient context managers and decorators
for transaction management, similar to Django's @transaction.atomic.
"""

import functools
from typing import Any, Callable, Optional, TypeVar, Union
from contextlib import asynccontextmanager

from .manager import TransactionManager, Transaction
from .exceptions import TransactionError

F = TypeVar("F", bound=Callable[..., Any])


@asynccontextmanager
async def transaction(
    client: Any,
    transaction_id: Optional[str] = None,
    auto_commit: bool = True,
    auto_rollback: bool = True,
):
    """Async context manager for transaction handling.

    This is a convenience function that creates a transaction context
    without requiring direct access to the TransactionManager.

    Args:
        client: OdooFlow client instance
        transaction_id: Optional transaction identifier
        auto_commit: Whether to auto-commit on success
        auto_rollback: Whether to auto-rollback on exception

    Yields:
        Transaction instance

    Example:
        >>> from odooflow.transaction import transaction
        >>>
        >>> async with transaction(client) as tx:
        ...     partner = await client.model(ResPartner).create(name="Test")
        ...     await client.model(ResPartner).filter(id=partner.id).update(email="test@example.com")
        ...     # Auto-commit on success
    """
    if not hasattr(client, "transaction_manager"):
        raise TransactionError("Client does not support transactions")

    async with client.transaction_manager.transaction(
        transaction_id=transaction_id, auto_commit=auto_commit
    ) as tx:
        yield tx


def atomic(
    client: Optional[Any] = None, auto_commit: bool = True, auto_rollback: bool = True
) -> Union[Callable[[F], F], Any]:
    """Decorator for atomic transaction execution.

    This decorator ensures that the decorated function runs within
    a transaction context. Similar to Django's @transaction.atomic.

    Args:
        client: OdooFlow client instance (can be passed at decoration or runtime)
        auto_commit: Whether to auto-commit on success
        auto_rollback: Whether to auto-rollback on exception

    Returns:
        Decorated function or decorator

    Example:
        >>> @atomic
        ... async def create_partner_with_contacts(client, company_data, contacts_data):
        ...     # This entire function runs in a transaction
        ...     company = await client.model(ResPartner).create(**company_data)
        ...
        ...     for contact_data in contacts_data:
        ...         contact_data['parent_id'] = company.id
        ...         await client.model(ResPartner).create(**contact_data)
        ...
        ...     return company
        ...
        >>> # Usage
        >>> company = await create_partner_with_contacts(
        ...     client,
        ...     {"name": "ACME Corp", "is_company": True},
        ...     [{"name": "John Doe"}, {"name": "Jane Smith"}]
        ... )
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to find client in arguments
            actual_client = client
            if actual_client is None:
                # Look for client in args or kwargs
                for arg in args:
                    if hasattr(arg, "transaction_manager"):
                        actual_client = arg
                        break

                if actual_client is None and "client" in kwargs:
                    actual_client = kwargs["client"]

                if actual_client is None:
                    raise TransactionError(
                        "No client provided for atomic transaction. "
                        "Pass client as decorator argument or function parameter."
                    )

            # Execute function within transaction
            async with transaction(
                actual_client, auto_commit=auto_commit, auto_rollback=auto_rollback
            ) as tx:
                # Add transaction to kwargs for function access
                kwargs["_transaction"] = tx
                return await func(*args, **kwargs)

        return wrapper

    # Support both @atomic and @atomic(client=...)
    if client is not None and callable(client):
        # Called as @atomic without parentheses
        func = client
        client = None
        return decorator(func)
    else:
        # Called as @atomic(...) with arguments
        return decorator


class TransactionContext:
    """Context manager for manual transaction control.

    This class provides more explicit control over transaction
    lifecycle compared to the simple context managers.

    Example:
        >>> ctx = TransactionContext(client)
        >>> async with ctx.begin() as tx:
        ...     # Manual transaction control
        ...     await tx.create(ResPartner, name="Test")
        ...
        ...     if some_condition:
        ...         await tx.rollback()
        ...         return
        ...
        ...     await tx.commit()
    """

    def __init__(self, client: Any):
        """Initialize transaction context.

        Args:
            client: OdooFlow client instance
        """
        self.client = client
        self.transaction: Optional[Transaction] = None

    @asynccontextmanager
    async def begin(
        self, transaction_id: Optional[str] = None, auto_commit: bool = False
    ):
        """Begin a new transaction.

        Args:
            transaction_id: Optional transaction identifier
            auto_commit: Whether to auto-commit (default: False for manual control)

        Yields:
            Transaction instance
        """
        async with self.client.transaction_manager.transaction(
            transaction_id=transaction_id, auto_commit=auto_commit
        ) as tx:
            self.transaction = tx
            try:
                yield tx
            finally:
                self.transaction = None

    def get_current_transaction(self) -> Optional[Transaction]:
        """Get the current transaction.

        Returns:
            Current transaction or None
        """
        return self.transaction


class SavepointContext:
    """Context manager for savepoint handling.

    This class provides convenient savepoint management
    within transactions for nested transaction support.

    Example:
        >>> async with transaction(client) as tx:
        ...     await tx.create(ResPartner, name="Company")
        ...
        ...     async with SavepointContext(tx, "contacts") as sp:
        ...         await tx.create(ResPartner, name="Contact 1")
        ...         await tx.create(ResPartner, name="Contact 2")
        ...
        ...         if error_condition:
        ...             await sp.rollback()  # Only rollback contacts
        ...
        ...     # Company creation is still valid
    """

    def __init__(self, transaction: Transaction, savepoint_name: Optional[str] = None):
        """Initialize savepoint context.

        Args:
            transaction: Transaction instance
            savepoint_name: Optional savepoint name
        """
        self.transaction = transaction
        self.savepoint_name = savepoint_name
        self.created_savepoint: Optional[str] = None

    async def __aenter__(self):
        """Enter savepoint context."""
        if not self.transaction.is_active:
            raise TransactionError("Cannot create savepoint in inactive transaction")

        self.created_savepoint = await self.transaction.create_savepoint(
            self.savepoint_name
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit savepoint context."""
        if exc_type is not None and self.created_savepoint:
            # Auto-rollback to savepoint on exception
            try:
                await self.transaction.rollback_to_savepoint(self.created_savepoint)
            except Exception:
                # If savepoint rollback fails, let the original exception propagate
                pass  # nosec B110

        return False  # Don't suppress exceptions

    async def rollback(self) -> None:
        """Manually rollback to this savepoint.

        Raises:
            TransactionError: If savepoint was not created
        """
        if not self.created_savepoint:
            raise TransactionError("No savepoint to rollback to")

        await self.transaction.rollback_to_savepoint(self.created_savepoint)


# Convenience aliases
savepoint = SavepointContext
tx_context = TransactionContext
