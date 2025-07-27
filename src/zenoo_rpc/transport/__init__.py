"""
Transport layer for OdooFlow.

This module provides the HTTP transport layer using httpx for async communication
with Odoo servers. It handles connection management, session handling, and
low-level RPC communication.
"""

from .httpx_transport import AsyncTransport
from .session import SessionManager

__all__ = [
    "AsyncTransport",
    "SessionManager",
]
