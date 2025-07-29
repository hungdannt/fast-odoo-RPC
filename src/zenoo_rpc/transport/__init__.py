"""
Transport layer for Zenoo RPC.

This module provides the HTTP transport layer using httpx for async
communication with Odoo servers. It handles connection management,
session handling, and low-level RPC communication.
"""

from .httpx_transport import AsyncTransport
from .session import SessionManager
from .pool import ConnectionPool

__all__ = [
    "AsyncTransport",
    "SessionManager",
    "ConnectionPool",
]
