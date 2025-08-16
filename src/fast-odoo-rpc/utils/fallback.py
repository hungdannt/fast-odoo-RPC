"""
Fallback mechanisms for Zenoo-RPC operations.

This module provides utilities for graceful degradation when operations fail
due to permissions, access restrictions, or other issues.
"""

from typing import Any, Dict, List, Optional, Callable, Union
import logging
from ..exceptions import AccessError, ValidationError, ZenooError

logger = logging.getLogger(__name__)


class FallbackManager:
    """Manager for handling operation fallbacks and graceful degradation."""

    def __init__(self, client):
        """Initialize fallback manager with client reference.
        
        Args:
            client: ZenooClient instance
        """
        self.client = client
        self._permission_cache = {}

    async def safe_operation(
        self,
        operation: Callable,
        fallback_operation: Optional[Callable] = None,
        fallback_value: Any = None,
        log_errors: bool = True,
        raise_on_critical: bool = False,
    ) -> Any:
        """Execute operation with fallback handling.
        
        Args:
            operation: Primary operation to execute
            fallback_operation: Alternative operation if primary fails
            fallback_value: Value to return if all operations fail
            log_errors: Whether to log errors
            raise_on_critical: Whether to raise critical errors
            
        Returns:
            Result of successful operation or fallback value
        """
        try:
            return await operation()
        except (AccessError, ValidationError) as e:
            if log_errors:
                logger.warning(f"Primary operation failed: {e}")
            
            # Try fallback operation if provided
            if fallback_operation:
                try:
                    return await fallback_operation()
                except Exception as fallback_error:
                    if log_errors:
                        logger.warning(f"Fallback operation failed: {fallback_error}")
            
            # Return fallback value or raise if critical
            if raise_on_critical:
                raise e
            return fallback_value
        except Exception as e:
            if log_errors:
                logger.error(f"Unexpected error in operation: {e}")
            if raise_on_critical:
                raise e
            return fallback_value

    async def get_accessible_records(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get only accessible records, filtering out inaccessible ones.
        
        Args:
            model: Odoo model name
            ids: List of record IDs
            fields: Fields to retrieve
            context: Optional context
            
        Returns:
            List of accessible records
        """
        try:
            # Use search_read to get only accessible records
            return await self.client.search_read(
                model,
                domain=[("id", "in", ids)],
                fields=fields,
                context=context
            )
        except Exception as e:
            logger.warning(f"Failed to get accessible records for {model}: {e}")
            return []

    async def safe_create_with_fallback(
        self,
        model: str,
        values: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        required_fields_only: bool = False,
    ) -> Optional[int]:
        """Create record with fallback to minimal required fields.
        
        Args:
            model: Odoo model name
            values: Field values for creation
            context: Optional context
            required_fields_only: Whether to fallback to required fields only
            
        Returns:
            Created record ID or None if failed
        """
        # Try full creation first
        try:
            return await self.client.create(model, values, context)
        except ValidationError as e:
            logger.warning(f"Full create failed for {model}: {e}")
            
            if required_fields_only:
                # Try with only required fields
                try:
                    required_values = await self._get_required_fields_only(model, values)
                    if required_values:
                        return await self.client.create(model, required_values, context)
                except Exception as fallback_error:
                    logger.warning(f"Required fields create failed: {fallback_error}")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error in safe_create: {e}")
            return None

    async def _get_required_fields_only(
        self, 
        model: str, 
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract only required fields from values.
        
        Args:
            model: Odoo model name
            values: Original field values
            
        Returns:
            Dictionary with only required fields
        """
        try:
            fields_info = await self.client.get_model_fields(model)
            required_values = {}
            
            for field_name, field_info in fields_info.items():
                if (field_info.get("required", False) and 
                    field_name in values and
                    field_name not in ["id", "create_date", "write_date", "create_uid", "write_uid"]):
                    required_values[field_name] = values[field_name]
            
            return required_values
        except Exception:
            return {}

    async def check_operation_permission(
        self,
        model: str,
        operation: str,
        use_cache: bool = True,
    ) -> bool:
        """Check if user has permission for operation with caching.
        
        Args:
            model: Odoo model name
            operation: Operation to check (create, read, write, unlink)
            use_cache: Whether to use cached results
            
        Returns:
            True if user has permission
        """
        cache_key = f"{model}:{operation}"
        
        if use_cache and cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        try:
            has_permission = await self.client.check_model_access(model, operation)
            if use_cache:
                self._permission_cache[cache_key] = has_permission
            return has_permission
        except Exception:
            return False

    async def get_user_capabilities(
        self, 
        models: List[str]
    ) -> Dict[str, Dict[str, bool]]:
        """Get user capabilities for multiple models.
        
        Args:
            models: List of model names to check
            
        Returns:
            Dictionary mapping model names to their permission dictionaries
        """
        capabilities = {}
        
        for model in models:
            try:
                capabilities[model] = await self.client.get_user_permissions(model)
            except Exception as e:
                logger.warning(f"Failed to get capabilities for {model}: {e}")
                capabilities[model] = {
                    "create": False,
                    "read": False,
                    "write": False,
                    "unlink": False
                }
        
        return capabilities

    def clear_permission_cache(self):
        """Clear the permission cache."""
        self._permission_cache.clear()

    async def adaptive_read(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Adaptive read that tries different strategies based on access.
        
        Args:
            model: Odoo model name
            ids: Record IDs to read
            fields: Fields to retrieve
            context: Optional context
            
        Returns:
            List of accessible records
        """
        # Strategy 1: Try direct read
        try:
            return await self.client.read(model, ids, fields, context)
        except AccessError:
            logger.info(f"Direct read failed for {model}, trying search_read")
            
            # Strategy 2: Use search_read as fallback
            try:
                return await self.client.search_read(
                    model,
                    domain=[("id", "in", ids)],
                    fields=fields,
                    context=context
                )
            except Exception as e:
                logger.warning(f"Search_read also failed for {model}: {e}")
                return []

    async def batch_operation_with_fallback(
        self,
        operation_func: Callable,
        items: List[Any],
        batch_size: int = 10,
        continue_on_error: bool = True,
    ) -> Dict[str, List[Any]]:
        """Execute batch operation with individual fallback.
        
        Args:
            operation_func: Function to execute for each item
            items: List of items to process
            batch_size: Size of each batch
            continue_on_error: Whether to continue processing on errors
            
        Returns:
            Dictionary with 'success' and 'failed' lists
        """
        results = {"success": [], "failed": []}
        
        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            for item in batch:
                try:
                    result = await operation_func(item)
                    results["success"].append({"item": item, "result": result})
                except Exception as e:
                    logger.warning(f"Batch operation failed for item {item}: {e}")
                    results["failed"].append({"item": item, "error": str(e)})
                    
                    if not continue_on_error:
                        break
        
        return results
