"""Memory transport for testing."""

from typing import Dict, Any, List, Optional, Callable
import json
import asyncio
from collections import defaultdict


class MemoryTransport:
    """In-memory transport for testing RPC calls."""

    def __init__(self, latency: float = 0.0):
        self._responses: Dict[str, Any] = {}
        self._call_history: List[Dict[str, Any]] = []
        self._error_responses: Dict[str, Exception] = {}
        self._latency = latency
        self._call_count = defaultdict(int)
        self._response_callbacks: Dict[str, Callable] = {}

    async def call(
        self, method: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        """Simulate an RPC call."""
        call_info = {"method": method, "params": params or {}, "kwargs": kwargs}
        self._call_history.append(call_info)
        self._call_count[method] += 1

        # Simulate network latency
        if self._latency > 0:
            await asyncio.sleep(self._latency)

        # Check for error responses
        if method in self._error_responses:
            raise self._error_responses[method]

        # Check for callbacks
        if method in self._response_callbacks:
            return self._response_callbacks[method](params)

        # Return predefined response
        if method in self._responses:
            return self._responses[method]

        # Default response
        return {"status": "ok", "method": method, "params": params}

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Simulate Odoo execute_kw call."""
        # Record as execute_kw call
        call_info = {
            "method": "execute_kw",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs or {},
            },
        }
        self._call_history.append(call_info)
        self._call_count["execute_kw"] += 1

        # Simulate network latency
        if self._latency > 0:
            await asyncio.sleep(self._latency)

        # Check for error responses
        if "execute_kw" in self._error_responses:
            raise self._error_responses["execute_kw"]

        # Check for callbacks
        if "execute_kw" in self._response_callbacks:
            return self._response_callbacks["execute_kw"](call_info["params"])

        # Return predefined response
        if "execute_kw" in self._responses:
            return self._responses["execute_kw"]

        # Default responses based on method
        if method == "create":
            # Return fake IDs for created records
            if isinstance(args[0], list):
                return list(range(1, len(args[0]) + 1))
            return 1
        elif method in ("write", "unlink"):
            return True

        # Default response
        return {"status": "ok", "model": model, "method": method}

    def set_response(self, method: str, response: Any):
        """Set a predefined response for a method."""
        self._responses[method] = response

    def set_error(self, method: str, error: Exception):
        """Set an error response for a method."""
        self._error_responses[method] = error

    def set_callback(self, method: str, callback: Callable):
        """Set a callback function for dynamic responses."""
        self._response_callbacks[method] = callback

    def get_call_history(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get call history, optionally filtered by method."""
        if method:
            return [call for call in self._call_history if call["method"] == method]
        return self._call_history.copy()

    def get_call_count(self, method: str) -> int:
        """Get the number of times a method was called."""
        return self._call_count[method]

    def was_called(self, method: str) -> bool:
        """Check if a method was called."""
        return self._call_count[method] > 0

    def reset(self):
        """Reset all state."""
        self._responses.clear()
        self._call_history.clear()
        self._error_responses.clear()
        self._call_count.clear()
        self._response_callbacks.clear()

    def set_latency(self, latency: float):
        """Set simulated network latency."""
        self._latency = latency

    def to_json(self) -> str:
        """Convert call history to JSON."""
        return json.dumps(self._call_history, indent=2)
