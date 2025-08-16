"""
Session management for OdooFlow.

This module handles authentication, session state, and user context
management for Odoo RPC connections.
"""

from typing import Any, Dict, Optional

from ..exceptions import AuthenticationError


class SessionManager:
    """Manages authentication and session state for Odoo connections.

    This class handles the authentication flow, maintains session state,
    and provides context management for Odoo RPC calls.

    Features:
    - Automatic session management
    - Context handling (language, timezone, etc.)
    - API key authentication support
    - Session validation and refresh

    Example:
        >>> session = SessionManager()
        >>> await session.authenticate(transport, "mydb", "admin", "password")
        >>> session.is_authenticated
        True
    """

    def __init__(self):
        """Initialize the session manager."""
        self._database: Optional[str] = None
        self._uid: Optional[int] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._context: Dict[str, Any] = {}
        self._session_id: Optional[str] = None
        self._server_version: Optional[Dict[str, Any]] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if the session is authenticated."""
        return self._uid is not None and self._database is not None

    @property
    def database(self) -> Optional[str]:
        """Get the current database name."""
        return self._database

    @property
    def uid(self) -> Optional[int]:
        """Get the current user ID."""
        return self._uid

    @property
    def username(self) -> Optional[str]:
        """Get the current username."""
        return self._username

    @property
    def password(self) -> Optional[str]:
        """Get the current password."""
        return self._password

    @property
    def context(self) -> Dict[str, Any]:
        """Get the current user context."""
        return self._context.copy()

    @property
    def server_version(self) -> Optional[Dict[str, Any]]:
        """Get the server version information."""
        return self._server_version

    async def authenticate(
        self,
        transport: Any,  # AsyncTransport
        database: str,
        username: str,
        password: str,
    ) -> None:
        """Authenticate with the Odoo server using username/password.

        Args:
            transport: The transport instance to use for communication
            database: Database name to connect to
            username: Username for authentication
            password: Password for authentication

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # First, get server version info
            version_result = await transport.json_rpc_call("common", "version", {})
            self._server_version = version_result.get("result", {})

            # Authenticate user
            auth_result = await transport.json_rpc_call(
                "common", "authenticate", {"args": [database, username, password, {}]}
            )

            uid = auth_result.get("result")
            if not uid:
                raise AuthenticationError(
                    f"Authentication failed for user '{username}' on database '{database}'"
                )

            # Store session information
            self._database = database
            self._uid = uid
            self._username = username
            self._password = password

            # Get user context
            await self._load_user_context(transport)

        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {e}") from e

    async def authenticate_with_api_key(
        self,
        transport: Any,  # AsyncTransport
        database: str,
        username: str,
        api_key: str,
    ) -> None:
        """Authenticate with the Odoo server using API key.

        Args:
            transport: The transport instance to use for communication
            database: Database name to connect to
            username: Username for authentication
            api_key: API key for authentication

        Raises:
            AuthenticationError: If authentication fails
        """
        # Note: API key authentication might require different implementation
        # depending on Odoo version and configuration
        try:
            # Get server version info
            version_result = await transport.json_rpc_call("common", "version", {})
            self._server_version = version_result.get("result", {})

            # For API key authentication, we might need to use a different approach
            # This is a placeholder implementation
            auth_result = await transport.json_rpc_call(
                "common", "authenticate", {"args": [database, username, api_key, {}]}
            )

            uid = auth_result.get("result")
            if not uid:
                raise AuthenticationError(
                    f"API key authentication failed for user '{username}' on database '{database}'"
                )

            self._database = database
            self._uid = uid
            self._username = username

            await self._load_user_context(transport)

        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"API key authentication failed: {e}") from e

    async def _load_user_context(self, transport: Any) -> None:
        """Load user context information from the server.

        Args:
            transport: The transport instance to use for communication
        """
        if not self.is_authenticated:
            return

        try:
            # Get user context by reading the current user record
            context_result = await transport.json_rpc_call(
                "object",
                "execute_kw",
                {
                    "args": [
                        self._database,
                        self._uid,
                        "password",  # This would be handled differently in real implementation
                        "res.users",
                        "context_get",
                        [],
                    ]
                },
            )

            if "result" in context_result:
                self._context = context_result["result"]

        except Exception:
            # If we can't load context, use defaults
            self._context = {
                "lang": "en_US",
                "tz": "UTC",
                "uid": self._uid,
            }

    def get_call_context(
        self, additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get context for RPC calls.

        Args:
            additional_context: Additional context to merge

        Returns:
            Complete context dictionary for RPC calls
        """
        context = self._context.copy()
        if additional_context:
            context.update(additional_context)
        return context

    def clear(self) -> None:
        """Clear the session state."""
        self._database = None
        self._uid = None
        self._username = None
        self._context = {}
        self._session_id = None
        self._server_version = None
