"""
AI-powered features for Zenoo RPC.

This module provides intelligent capabilities including:
- Natural language to Odoo query conversion
- AI-powered error diagnosis and solutions
- Smart code generation and optimization
- Performance analysis and recommendations

The AI features are optional and require LiteLLM installation:
    pip install zenoo-rpc[ai]

Example:
    >>> async with ZenooClient("localhost") as client:
    ...     await client.setup_ai(provider="gemini", api_key="your-key")
    ...     
    ...     # Natural language queries
    ...     partners = await client.ai.query("Find all companies in Vietnam")
    ...     
    ...     # Error diagnosis
    ...     diagnosis = await client.ai.diagnose(error)
"""

from typing import TYPE_CHECKING

# Optional imports for AI features
try:
    from .core.ai_client import AIClient
    from .core.ai_assistant import AIAssistant
    from .query.nl_to_query import NaturalLanguageQueryProcessor
    from .diagnostics.error_analyzer import AIErrorAnalyzer
    
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    _import_error = e

if TYPE_CHECKING or AI_AVAILABLE:
    from .core.ai_client import AIClient
    from .core.ai_assistant import AIAssistant
    from .query.nl_to_query import NaturalLanguageQueryProcessor
    from .diagnostics.error_analyzer import AIErrorAnalyzer

__all__ = [
    "AIClient",
    "AIAssistant",
    "NaturalLanguageQueryProcessor",
    "AIErrorAnalyzer",
    "AI_AVAILABLE",
]


def check_ai_availability() -> bool:
    """Check if AI features are available.
    
    Returns:
        True if AI dependencies are installed, False otherwise
    """
    return AI_AVAILABLE


def get_ai_import_error() -> Exception:
    """Get the import error if AI features are not available.
    
    Returns:
        The import exception that occurred
        
    Raises:
        RuntimeError: If AI features are actually available
    """
    if AI_AVAILABLE:
        raise RuntimeError("AI features are available")
    return _import_error


class AINotAvailableError(ImportError):
    """Raised when AI features are requested but not available."""
    
    def __init__(self):
        super().__init__(
            "AI features are not available. Install with: pip install zenoo-rpc[ai]"
        )
