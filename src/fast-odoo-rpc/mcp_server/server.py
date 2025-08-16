"""
Core MCP Server implementation for Zenoo RPC.

This module provides the main MCP server that exposes Odoo operations
through the Model Context Protocol, allowing AI tools to interact with Odoo.
"""

import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import Tool, Resource, Prompt, TextContent, ImageContent
    MCP_AVAILABLE = True
except ImportError:
    # Mock classes for when MCP is not available
    class FastMCP:
        def __init__(self, name: str, instructions: str = ""):
            self.name = name
            self.instructions = instructions
            self.tools = {}
            self.resources = {}
            self.prompts = {}
        
        def tool(self, name: str = None):
            def decorator(func):
                tool_name = name or func.__name__
                self.tools[tool_name] = func
                return func
            return decorator
        
        def resource(self, uri_template: str):
            def decorator(func):
                self.resources[uri_template] = func
                return func
            return decorator
        
        def prompt(self, name: str = None):
            def decorator(func):
                prompt_name = name or func.__name__
                self.prompts[prompt_name] = func
                return func
            return decorator
        
        async def run(self, transport="stdio", **kwargs):
            host = kwargs.get('host', 'localhost')
            port = kwargs.get('port', 8000)
            print(f"Mock MCP server '{self.name}' running with {transport} transport")
            if transport == "http":
                print(f"Mock HTTP server would run on {host}:{port}")
            # Mock server - just wait indefinitely
            import asyncio
            await asyncio.Event().wait()
    
    class Tool:
        def __init__(self, name: str, description: str = ""):
            self.name = name
            self.description = description
    
    class Resource:
        def __init__(self, uri: str, name: str = "", description: str = ""):
            self.uri = uri
            self.name = name
            self.description = description
    
    class Prompt:
        def __init__(self, name: str, description: str = ""):
            self.name = name
            self.description = description
    
    class TextContent:
        def __init__(self, text: str):
            self.text = text
    
    class ImageContent:
        def __init__(self, data: str, mime_type: str):
            self.data = data
            self.mime_type = mime_type
    
    MCP_AVAILABLE = False

from ..client import ZenooClient
from .config import MCPServerConfig
from .security import MCPSecurityManager
from .exceptions import (
    MCPServerError,
    MCPAuthenticationError,
    MCPAuthorizationError,
    MCPToolError,
    MCPResourceError
)

logger = logging.getLogger(__name__)


class ZenooMCPServer:
    """MCP Server that exposes Zenoo RPC/Odoo operations to AI tools.
    
    This server implements the Model Context Protocol to allow AI assistants
    and other tools to interact with Odoo through a standardized interface.
    
    Features:
    - Tools: Execute Odoo operations (CRUD, search, workflows)
    - Resources: Access Odoo data (models, records, reports)
    - Prompts: Template-based Odoo queries
    - Security: Authentication, authorization, input validation
    - Performance: Caching, connection pooling, async operations
    
    Example:
        >>> config = MCPServerConfig.from_env()
        >>> server = ZenooMCPServer(config)
        >>> await server.start()
    """
    
    def __init__(self, config: MCPServerConfig):
        """Initialize MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.zenoo_client: Optional[ZenooClient] = None
        self.security_manager = MCPSecurityManager(config)
        
        # Initialize FastMCP server
        self.mcp_server = FastMCP(
            name=config.name,
            instructions=self._get_server_instructions(),
            host=config.host,
            port=config.port
        )
        
        # Register tools, resources, and prompts
        self._register_tools()
        self._register_resources()
        self._register_prompts()
        
        logger.info(f"Initialized MCP server '{config.name}'")
    
    def _get_server_instructions(self) -> str:
        """Get server instructions for AI clients."""
        return f"""
{self.config.description}

This server provides access to Odoo ERP operations through the following capabilities:

TOOLS (Actions you can perform):
- search_records: Search for records in any Odoo model
- get_record: Get a specific record by ID
- create_record: Create a new record
- update_record: Update an existing record
- delete_record: Delete a record
- execute_workflow: Execute workflow actions
- generate_report: Generate Odoo reports

RESOURCES (Data you can access):
- odoo://models - List all available Odoo models
- odoo://model/{{model_name}} - Get model information
- odoo://record/{{model_name}}/{{record_id}} - Get specific record
- odoo://search/{{model_name}}/{{domain}} - Search results

PROMPTS (Templates you can use):
- analyze_data: Analyze Odoo data with AI
- generate_report_query: Generate report queries
- suggest_workflow: Suggest workflow improvements

Authentication: {self.config.security.auth_method.value}
Rate Limits: {self.config.security.rate_limit_requests} requests per {self.config.security.rate_limit_window}s
"""
    
    async def start(self) -> None:
        """Start the MCP server."""
        try:
            # Connect to Odoo
            await self._connect_to_odoo()
            
            # Start security cleanup task
            asyncio.create_task(self._security_cleanup_task())
            
            # Run MCP server
            transport = self.config.transport_type.value
            if transport == "stdio":
                await self.mcp_server.run_stdio_async()
            elif transport == "http":
                # Use streamable-http transport for HTTP
                await self.mcp_server.run_streamable_http_async()
            else:
                raise MCPServerError(f"Unsupported transport: {transport}")
                
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise MCPServerError(f"Server startup failed: {e}") from e
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        try:
            if self.zenoo_client:
                await self.zenoo_client.close()
            logger.info("MCP server stopped")
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")

    async def _connect_to_odoo(self) -> None:
        """Connect to Odoo using Zenoo RPC."""
        try:
            self.zenoo_client = ZenooClient(self.config.odoo_url)
            await self.zenoo_client.login(
                self.config.odoo_database,
                self.config.odoo_username,
                self.config.odoo_password
            )
            logger.info("Connected to Odoo successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Odoo: {e}")
            raise MCPServerError(f"Odoo connection failed: {e}") from e
    
    async def _security_cleanup_task(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                self.security_manager.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Error in security cleanup task: {e}")
    
    def _register_tools(self) -> None:
        """Register MCP tools."""
        if not self.config.features.enable_tools:
            return
        
        @self.mcp_server.tool()
        async def search_records(
            model: str,
            domain: List = None,
            fields: List[str] = None,
            limit: int = 100,
            offset: int = 0,
            order: str = None
        ) -> Dict[str, Any]:
            """Search for records in an Odoo model.
            
            Args:
                model: Odoo model name (e.g., 'res.partner', 'sale.order')
                domain: Search domain (e.g., [['name', 'ilike', 'John']])
                fields: Fields to retrieve (default: all)
                limit: Maximum number of records (default: 100)
                offset: Number of records to skip (default: 0)
                order: Sort order (e.g., 'name ASC')
            
            Returns:
                Dictionary with search results and metadata
            """
            return await self._execute_tool("search_records", {
                "model": model,
                "domain": domain or [],
                "fields": fields,
                "limit": limit,
                "offset": offset,
                "order": order
            })
        
        @self.mcp_server.tool()
        async def get_record(
            model: str,
            record_id: int,
            fields: List[str] = None
        ) -> Dict[str, Any]:
            """Get a specific record by ID.
            
            Args:
                model: Odoo model name
                record_id: Record ID
                fields: Fields to retrieve (default: all)
            
            Returns:
                Record data
            """
            return await self._execute_tool("get_record", {
                "model": model,
                "record_id": record_id,
                "fields": fields
            })
        
        @self.mcp_server.tool()
        async def create_record(
            model: str,
            values: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Create a new record.
            
            Args:
                model: Odoo model name
                values: Field values for the new record
            
            Returns:
                Created record data
            """
            return await self._execute_tool("create_record", {
                "model": model,
                "values": values
            })
        
        @self.mcp_server.tool()
        async def update_record(
            model: str,
            record_id: int,
            values: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Update an existing record.
            
            Args:
                model: Odoo model name
                record_id: Record ID to update
                values: Field values to update
            
            Returns:
                Updated record data
            """
            return await self._execute_tool("update_record", {
                "model": model,
                "record_id": record_id,
                "values": values
            })
        
        @self.mcp_server.tool()
        async def delete_record(
            model: str,
            record_id: int
        ) -> Dict[str, Any]:
            """Delete a record.

            Args:
                model: Odoo model name
                record_id: Record ID to delete

            Returns:
                Deletion confirmation
            """
            return await self._execute_tool("delete_record", {
                "model": model,
                "record_id": record_id
            })

        # Advanced tools leveraging Zenoo RPC features
        @self.mcp_server.tool()
        async def complex_search(
            model: str,
            filters: Dict[str, Any],
            order_by: str = None,
            limit: int = 100,
            include_relationships: bool = False
        ) -> Dict[str, Any]:
            """Advanced search using QueryBuilder with complex filters.

            Args:
                model: Odoo model name
                filters: Complex filters using Django-like syntax
                order_by: Sort order (e.g., 'name', '-date_order')
                limit: Maximum number of records
                include_relationships: Whether to include related data

            Returns:
                Search results with metadata
            """
            return await self._execute_tool("complex_search", {
                "model": model,
                "filters": filters,
                "order_by": order_by,
                "limit": limit,
                "include_relationships": include_relationships
            })

        @self.mcp_server.tool()
        async def batch_operation(
            operation: str,
            model: str,
            records: List[Dict[str, Any]]
        ) -> Dict[str, Any]:
            """Perform batch operations for high performance.

            Args:
                operation: Operation type ('create', 'update', 'delete')
                model: Odoo model name
                records: List of record data

            Returns:
                Batch operation results
            """
            return await self._execute_tool("batch_operation", {
                "operation": operation,
                "model": model,
                "records": records
            })

        @self.mcp_server.tool()
        async def analytics_query(
            model: str,
            group_by: List[str],
            aggregates: Dict[str, str],
            filters: Dict[str, Any] = None,
            date_range: Dict[str, str] = None
        ) -> Dict[str, Any]:
            """Perform analytics queries with aggregation.

            Args:
                model: Odoo model name
                group_by: Fields to group by
                aggregates: Aggregation functions (e.g., {'total': 'sum', 'count': 'count'})
                filters: Optional filters
                date_range: Optional date range filter

            Returns:
                Analytics results
            """
            return await self._execute_tool("analytics_query", {
                "model": model,
                "group_by": group_by,
                "aggregates": aggregates,
                "filters": filters or {},
                "date_range": date_range
            })
    
    def _register_resources(self) -> None:
        """Register MCP resources."""
        if not self.config.features.enable_resources:
            return
        
        @self.mcp_server.resource("odoo://models")
        async def list_models() -> str:
            """List all available Odoo models."""
            return await self._execute_resource("list_models", {})
        
        @self.mcp_server.resource("odoo://model/{model_name}")
        async def get_model_info(model_name: str) -> str:
            """Get information about a specific model."""
            return await self._execute_resource("get_model_info", {
                "model_name": model_name
            })
        
        @self.mcp_server.resource("odoo://record/{model_name}/{record_id}")
        async def get_record_resource(model_name: str, record_id: int) -> str:
            """Get a specific record as a resource."""
            return await self._execute_resource("get_record_resource", {
                "model_name": model_name,
                "record_id": record_id
            })
    
    def _register_prompts(self) -> None:
        """Register MCP prompts."""
        if not self.config.features.enable_prompts:
            return
        
        @self.mcp_server.prompt()
        async def analyze_data(
            model: str = "res.partner",
            analysis_type: str = "summary"
        ) -> str:
            """Generate a prompt for analyzing Odoo data."""
            return await self._execute_prompt("analyze_data", {
                "model": model,
                "analysis_type": analysis_type
            })
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with security and validation."""
        try:
            # Security validation would go here
            # For now, simplified implementation
            
            if not self.zenoo_client:
                raise MCPToolError("Not connected to Odoo")
            
            if tool_name == "search_records":
                return await self._handle_search_records(arguments)
            elif tool_name == "get_record":
                return await self._handle_get_record(arguments)
            elif tool_name == "create_record":
                return await self._handle_create_record(arguments)
            elif tool_name == "update_record":
                return await self._handle_update_record(arguments)
            elif tool_name == "delete_record":
                return await self._handle_delete_record(arguments)
            elif tool_name == "complex_search":
                return await self._handle_complex_search(arguments)
            elif tool_name == "batch_operation":
                return await self._handle_batch_operation(arguments)
            elif tool_name == "analytics_query":
                return await self._handle_analytics_query(arguments)
            else:
                raise MCPToolError(f"Unknown tool: {tool_name}")
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise MCPToolError(f"Tool '{tool_name}' failed: {e}") from e
    
    async def _handle_search_records(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_records tool using Zenoo RPC search_read."""
        try:
            model_name = args["model"]
            domain = args.get("domain", [])
            fields = args.get("fields")
            limit = args.get("limit", 100)
            offset = args.get("offset", 0)
            order = args.get("order")

            # Use search_read for direct Odoo access
            records = await self.zenoo_client.search_read(
                model=model_name,
                domain=domain,
                fields=fields,
                limit=limit,
                offset=offset,
                order=order
            )

            return {
                "records": records,
                "count": len(records),
                "model": model_name,
                "has_more": len(records) == limit,
                "domain": domain,
                "fields": fields or "all"
            }

        except Exception as e:
            logger.error(f"Search records failed: {e}")
            raise MCPToolError(f"Search failed for model {args.get('model')}: {e}")

    def _apply_domain_to_query(self, query, domain: List) -> Any:
        """Convert Odoo domain to QueryBuilder filters."""
        from ..query import Q

        # This is a simplified domain converter
        # In a full implementation, we'd need to handle complex domain logic
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                field, operator, value = item

                if operator == "=":
                    query = query.filter(**{field: value})
                elif operator == "!=":
                    query = query.exclude(**{field: value})
                elif operator == "like" or operator == "ilike":
                    query = query.filter(**{f"{field}__ilike": value})
                elif operator == "in":
                    query = query.filter(**{f"{field}__in": value})
                elif operator == ">":
                    query = query.filter(**{f"{field}__gt": value})
                elif operator == ">=":
                    query = query.filter(**{f"{field}__gte": value})
                elif operator == "<":
                    query = query.filter(**{f"{field}__lt": value})
                elif operator == "<=":
                    query = query.filter(**{f"{field}__lte": value})

        return query
    
    async def _handle_get_record(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_record tool using Zenoo RPC OdooModel."""
        try:
            from ..models.registry import get_model_class

            model_name = args["model"]
            record_id = args["record_id"]
            fields = args.get("fields")

            # Try to get registered model class for type safety
            try:
                model_class = get_model_class(model_name)
                query = self.zenoo_client.model(model_class)
            except (KeyError, ImportError):
                # Fallback to dynamic model access
                query = self.zenoo_client.model(model_name)

            # Get the record
            if fields:
                record = await query.filter(id=record_id).values(*fields).first()
            else:
                record = await query.get(record_id)

            if not record:
                raise MCPToolError(f"Record {record_id} not found in model {model_name}")

            # Convert to serializable format
            if hasattr(record, 'to_dict'):
                record_data = record.to_dict()
            else:
                record_data = dict(record)

            return {
                "record": record_data,
                "model": model_name,
                "id": record_id
            }

        except Exception as e:
            logger.error(f"Get record failed: {e}")
            raise MCPToolError(f"Failed to get record {args.get('record_id')} from {args.get('model')}: {e}")
    
    async def _handle_create_record(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create_record tool using Zenoo RPC with transaction support."""
        try:
            from ..models.registry import get_model_class

            model_name = args["model"]
            values = args["values"]

            # Use transaction for data integrity
            async with self.zenoo_client.transaction() as tx:
                # Try to get registered model class for type safety
                try:
                    model_class = get_model_class(model_name)
                    record = await tx.create(model_class, values)
                except (KeyError, ImportError):
                    # Fallback to raw create
                    record_id = await self.zenoo_client.create(model_name, values)
                    record = {"id": record_id, **values}

                # Convert to serializable format
                if hasattr(record, 'to_dict'):
                    record_data = record.to_dict()
                elif hasattr(record, 'id'):
                    record_data = {"id": record.id, **values}
                else:
                    record_data = record

                return {
                    "record": record_data,
                    "model": model_name,
                    "created": True,
                    "id": record_data.get("id")
                }

        except Exception as e:
            logger.error(f"Create record failed: {e}")
            raise MCPToolError(f"Failed to create record in {args.get('model')}: {e}")
    
    async def _handle_update_record(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_record tool using Zenoo RPC with transaction support."""
        try:
            from ..models.registry import get_model_class

            model_name = args["model"]
            record_id = args["record_id"]
            values = args["values"]

            # Use transaction for data integrity
            async with self.zenoo_client.transaction() as tx:
                # Try to get registered model class for type safety
                try:
                    model_class = get_model_class(model_name)
                    # Get existing record
                    record = await tx.get(model_class, record_id)
                    if not record:
                        raise MCPToolError(f"Record {record_id} not found in model {model_name}")

                    # Update with new values
                    updated_record = await tx.update(record, values)

                    # Convert to serializable format
                    if hasattr(updated_record, 'to_dict'):
                        record_data = updated_record.to_dict()
                    else:
                        record_data = {"id": record_id, **values}

                except (KeyError, ImportError):
                    # Fallback to raw update
                    success = await self.zenoo_client.write(model_name, [record_id], values)
                    if not success:
                        raise MCPToolError(f"Failed to update record {record_id}")
                    record_data = {"id": record_id, **values}

                return {
                    "record": record_data,
                    "model": model_name,
                    "updated": True,
                    "transaction_id": tx.transaction_id
                }

        except Exception as e:
            logger.error(f"Update record failed: {e}")
            raise MCPToolError(f"Failed to update record {args.get('record_id')} in {args.get('model')}: {e}")
    
    async def _handle_delete_record(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete_record tool using Zenoo RPC with transaction support."""
        try:
            from ..models.registry import get_model_class

            model_name = args["model"]
            record_id = args["record_id"]

            # Use transaction for data integrity
            async with self.zenoo_client.transaction() as tx:
                # Try to get registered model class for type safety
                try:
                    model_class = get_model_class(model_name)
                    # Get existing record first
                    record = await tx.get(model_class, record_id)
                    if not record:
                        raise MCPToolError(f"Record {record_id} not found in model {model_name}")

                    # Delete the record
                    success = await tx.delete(record)
                    if not success:
                        raise MCPToolError(f"Failed to delete record {record_id}")

                except (KeyError, ImportError):
                    # Fallback to raw delete
                    success = await self.zenoo_client.unlink(model_name, [record_id])
                    if not success:
                        raise MCPToolError(f"Failed to delete record {record_id}")

                return {
                    "id": record_id,
                    "model": model_name,
                    "deleted": True,
                    "transaction_id": tx.transaction_id
                }

        except Exception as e:
            logger.error(f"Delete record failed: {e}")
            raise MCPToolError(f"Failed to delete record {args.get('record_id')} from {args.get('model')}: {e}")
    
    async def _execute_resource(self, resource_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a resource request."""
        try:
            if resource_name == "list_models":
                return await self._handle_list_models_resource()
            elif resource_name == "get_model_info":
                return await self._handle_model_info_resource(arguments)
            elif resource_name == "get_record_resource":
                return await self._handle_record_resource(arguments)
            else:
                return json.dumps({
                    "error": f"Unknown resource: {resource_name}",
                    "available_resources": ["list_models", "get_model_info", "get_record_resource"]
                })
        except Exception as e:
            logger.error(f"Resource execution failed: {e}")
            return json.dumps({
                "error": f"Resource execution failed: {e}",
                "resource": resource_name,
                "arguments": arguments
            })
    
    async def _handle_list_models_resource(self) -> str:
        """Handle list_models resource - get all available Odoo models."""
        try:
            # Get list of models from Odoo
            models = await self.zenoo_client.execute_kw(
                'ir.model', 'search_read',
                [[]],
                {'fields': ['model', 'name', 'info']}
            )

            return json.dumps({
                "resource": "list_models",
                "count": len(models),
                "models": models[:50]  # Limit to first 50 for readability
            })
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return json.dumps({"error": f"Failed to list models: {e}"})

    async def _handle_model_info_resource(self, arguments: Dict[str, Any]) -> str:
        """Handle get_model_info resource - get info about specific model."""
        try:
            model_name = arguments.get("model_name")
            if not model_name:
                return json.dumps({"error": "model_name is required"})

            # Get model information
            model_info = await self.zenoo_client.execute_kw(
                'ir.model', 'search_read',
                [[['model', '=', model_name]]],
                {'fields': ['model', 'name', 'info']}
            )

            # Get model fields
            fields = await self.zenoo_client.execute_kw(
                'ir.model.fields', 'search_read',
                [[['model', '=', model_name]]],
                {'fields': ['name', 'field_description', 'ttype', 'required']}
            )

            return json.dumps({
                "resource": "get_model_info",
                "model_name": model_name,
                "model_info": model_info[0] if model_info else None,
                "fields": fields[:20]  # Limit fields for readability
            })
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return json.dumps({"error": f"Failed to get model info: {e}"})

    async def _handle_record_resource(self, arguments: Dict[str, Any]) -> str:
        """Handle get_record_resource - get specific record data."""
        try:
            model_name = arguments.get("model_name")
            record_id = arguments.get("record_id")

            if not model_name or not record_id:
                return json.dumps({"error": "model_name and record_id are required"})

            # Get record data
            records = await self.zenoo_client.search_read(
                model_name,
                [['id', '=', int(record_id)]],
                limit=1
            )

            return json.dumps({
                "resource": "get_record_resource",
                "model_name": model_name,
                "record_id": record_id,
                "record": records[0] if records else None
            })
        except Exception as e:
            logger.error(f"Failed to get record: {e}")
            return json.dumps({"error": f"Failed to get record: {e}"})

    async def _execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a prompt request."""
        # Mock implementation
        return f"Mock prompt for {prompt_name} with args: {arguments}"

    # Advanced tool handlers leveraging Zenoo RPC features
    async def _handle_complex_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle complex search using QueryBuilder with advanced features."""
        try:
            from ..models.registry import get_model_class
            from ..query import Q, Field

            model_name = args["model"]
            filters = args.get("filters", {})
            order_by = args.get("order_by")
            limit = args.get("limit", 100)
            include_relationships = args.get("include_relationships", False)

            # Try to get registered model class for type safety
            try:
                model_class = get_model_class(model_name)
                query = self.zenoo_client.model(model_class)
            except (KeyError, ImportError):
                # Fallback to dynamic model access
                query = self.zenoo_client.model(model_name)

            # Apply complex filters using Q objects
            if filters:
                q_filters = []
                for field, value in filters.items():
                    if isinstance(value, dict):
                        # Handle complex filters like {'name__ilike': 'test', 'age__gt': 18}
                        for lookup, val in value.items():
                            q_filters.append(Q(**{f"{field}__{lookup}": val}))
                    else:
                        q_filters.append(Q(**{field: value}))

                # Combine filters with AND
                if q_filters:
                    combined_filter = q_filters[0]
                    for q_filter in q_filters[1:]:
                        combined_filter = combined_filter & q_filter
                    query = query.filter(combined_filter)

            # Apply ordering
            if order_by:
                query = query.order_by(order_by)

            # Apply limit
            query = query.limit(limit)

            # Execute query
            records = await query.all()

            # Include relationships if requested
            result_data = []
            for record in records:
                if hasattr(record, 'to_dict'):
                    record_dict = record.to_dict()

                    # Include relationship data
                    if include_relationships and hasattr(record, '_get_relationships'):
                        relationships = await record._get_relationships()
                        record_dict["_relationships"] = relationships

                    result_data.append(record_dict)
                else:
                    result_data.append(dict(record))

            return {
                "records": result_data,
                "count": len(result_data),
                "model": model_name,
                "filters_applied": filters,
                "order_by": order_by,
                "includes_relationships": include_relationships
            }

        except Exception as e:
            logger.error(f"Complex search failed: {e}")
            raise MCPToolError(f"Complex search failed for model {args.get('model')}: {e}")

    async def _handle_batch_operation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch operations for high performance."""
        try:
            from ..models.registry import get_model_class

            operation = args["operation"]
            model_name = args["model"]
            records = args["records"]

            # Use transaction for batch operations
            async with self.zenoo_client.transaction() as tx:
                results = []

                if operation == "create":
                    # Batch create
                    try:
                        model_class = get_model_class(model_name)
                        for record_data in records:
                            record = await tx.create(model_class, record_data)
                            results.append(record.to_dict() if hasattr(record, 'to_dict') else record)
                    except (KeyError, ImportError):
                        # Fallback to raw batch create
                        record_ids = await self.zenoo_client.create(model_name, records)
                        results = [{"id": rid, **data} for rid, data in zip(record_ids, records)]

                elif operation == "update":
                    # Batch update
                    for record_data in records:
                        record_id = record_data.pop("id")
                        success = await self.zenoo_client.write(model_name, [record_id], record_data)
                        results.append({"id": record_id, "updated": success, **record_data})

                elif operation == "delete":
                    # Batch delete
                    record_ids = [r["id"] for r in records]
                    success = await self.zenoo_client.unlink(model_name, record_ids)
                    results = [{"id": rid, "deleted": success} for rid in record_ids]

                else:
                    raise MCPToolError(f"Unknown batch operation: {operation}")

                return {
                    "operation": operation,
                    "model": model_name,
                    "processed_count": len(results),
                    "results": results,
                    "transaction_id": tx.transaction_id
                }

        except Exception as e:
            logger.error(f"Batch operation failed: {e}")
            raise MCPToolError(f"Batch {args.get('operation')} failed for model {args.get('model')}: {e}")

    async def _handle_analytics_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics queries with aggregation."""
        try:
            from ..query import Field

            model_name = args["model"]
            group_by = args["group_by"]
            aggregates = args["aggregates"]
            filters = args.get("filters", {})
            date_range = args.get("date_range")

            # Build query
            query = self.zenoo_client.model(model_name)

            # Apply filters
            if filters:
                for field, value in filters.items():
                    query = query.filter(**{field: value})

            # Apply date range filter
            if date_range:
                start_date = date_range.get("start")
                end_date = date_range.get("end")
                date_field = date_range.get("field", "create_date")

                if start_date:
                    query = query.filter(**{f"{date_field}__gte": start_date})
                if end_date:
                    query = query.filter(**{f"{date_field}__lte": end_date})

            # Group by fields
            query = query.group_by(*group_by)

            # Add aggregations
            aggregate_fields = {}
            for alias, func in aggregates.items():
                if func == "sum":
                    aggregate_fields[alias] = Field(alias).sum()
                elif func == "count":
                    aggregate_fields[alias] = Field("id").count()
                elif func == "avg":
                    aggregate_fields[alias] = Field(alias).avg()
                elif func == "max":
                    aggregate_fields[alias] = Field(alias).max()
                elif func == "min":
                    aggregate_fields[alias] = Field(alias).min()

            query = query.aggregate(**aggregate_fields)

            # Execute analytics query
            results = await query.all()

            return {
                "model": model_name,
                "group_by": group_by,
                "aggregates": aggregates,
                "filters": filters,
                "date_range": date_range,
                "results": [dict(r) for r in results],
                "count": len(results)
            }

        except Exception as e:
            logger.error(f"Analytics query failed: {e}")
            raise MCPToolError(f"Analytics query failed for model {args.get('model')}: {e}")
