"""
AI-powered query processing for Zenoo RPC.

This module provides natural language to Odoo query conversion,
query optimization, and intelligent query assistance.
"""

from .nl_to_query import NaturalLanguageQueryProcessor
from .query_optimizer import AIQueryOptimizer

__all__ = [
    "NaturalLanguageQueryProcessor",
    "AIQueryOptimizer",
]
