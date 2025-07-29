"""
AI-powered model generation for Zenoo RPC.

This module generates Python model code from Odoo model schemas,
including proper type hints, validation rules, and relationships.
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.ai_client import AIClient
    from ...client import ZenooClient

logger = logging.getLogger(__name__)


class AIModelGenerator:
    """AI-powered Python model generator from Odoo schemas.
    
    This generator analyzes Odoo model structures and creates
    corresponding Python Pydantic models with proper types,
    validation rules, and relationship definitions.
    
    Features:
    - Automatic field type detection and mapping
    - Relationship field generation (Many2one, One2many, Many2many)
    - Validation rule creation
    - Documentation generation
    - Import statement optimization
    - Code formatting and best practices
    
    Example:
        >>> generator = AIModelGenerator(ai_client, zenoo_client)
        >>> 
        >>> # Generate model for res.partner
        >>> model_code = await generator.generate_model("res.partner")
        >>> print(model_code)
        >>> 
        >>> # Generate with specific options
        >>> model_code = await generator.generate_model(
        ...     "res.partner",
        ...     include_relationships=True,
        ...     include_computed_fields=False
        ... )
    """
    
    def __init__(self, ai_client: "AIClient", zenoo_client: "ZenooClient"):
        """Initialize the model generator.
        
        Args:
            ai_client: AI client for code generation
            zenoo_client: Zenoo client for Odoo introspection
        """
        self.ai_client = ai_client
        self.zenoo_client = zenoo_client
        
        # Odoo to Python type mappings
        self.type_mappings = {
            "char": "str",
            "text": "str", 
            "html": "str",
            "integer": "int",
            "float": "float",
            "monetary": "float",
            "boolean": "bool",
            "date": "date",
            "datetime": "datetime",
            "binary": "bytes",
            "selection": "str",
            "many2one": "Optional[int]",
            "one2many": "List[int]",
            "many2many": "List[int]",
        }
    
    async def generate_model(
        self,
        model_name: str,
        include_relationships: bool = True,
        include_computed_fields: bool = False,
        include_documentation: bool = True
    ) -> str:
        """Generate Python model code from Odoo model.
        
        Args:
            model_name: Odoo model name (e.g., "res.partner")
            include_relationships: Whether to include relationship fields
            include_computed_fields: Whether to include computed fields
            include_documentation: Whether to include field documentation
            
        Returns:
            Generated Python model code as string
            
        Raises:
            ValueError: If model doesn't exist or cannot be analyzed
            Exception: If code generation fails
        """
        try:
            # Get model information from Odoo
            model_info = await self._get_model_info(model_name)
            
            # Filter fields based on options
            fields = self._filter_fields(
                model_info["fields"],
                include_relationships=include_relationships,
                include_computed_fields=include_computed_fields
            )
            
            # Generate code using AI
            model_code = await self._generate_code(
                model_name=model_name,
                fields=fields,
                model_info=model_info,
                include_documentation=include_documentation
            )
            
            return model_code
            
        except Exception as e:
            logger.error(f"Model generation failed for {model_name}: {e}")
            raise
    
    async def _get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get comprehensive model information from Odoo.
        
        Args:
            model_name: Odoo model name
            
        Returns:
            Dictionary with model information including fields, constraints, etc.
        """
        try:
            # Get field information
            fields_info = await self.zenoo_client.execute_kw(
                "ir.model.fields",
                "search_read",
                [[("model", "=", model_name)]],
                {"fields": ["name", "ttype", "required", "readonly", "help", "relation", "selection"]}
            )
            
            # Get model information
            model_info = await self.zenoo_client.execute_kw(
                "ir.model",
                "search_read", 
                [[("model", "=", model_name)]],
                {"fields": ["name", "info", "modules"]}
            )
            
            # Organize field information
            fields = {}
            for field in fields_info:
                fields[field["name"]] = {
                    "type": field["ttype"],
                    "required": field["required"],
                    "readonly": field["readonly"],
                    "help": field["help"],
                    "relation": field["relation"],
                    "selection": field["selection"]
                }
            
            return {
                "name": model_name,
                "info": model_info[0] if model_info else {},
                "fields": fields
            }
            
        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            raise ValueError(f"Cannot analyze model {model_name}: {e}")
    
    def _filter_fields(
        self,
        fields: Dict[str, Any],
        include_relationships: bool = True,
        include_computed_fields: bool = False
    ) -> Dict[str, Any]:
        """Filter fields based on generation options."""
        filtered_fields = {}
        
        for field_name, field_info in fields.items():
            field_type = field_info["type"]
            
            # Skip system fields
            if field_name in ["id", "create_date", "create_uid", "write_date", "write_uid", "__last_update"]:
                continue
            
            # Skip computed fields if not requested
            if not include_computed_fields and field_info.get("readonly"):
                continue
            
            # Skip relationship fields if not requested
            if not include_relationships and field_type in ["many2one", "one2many", "many2many"]:
                continue
            
            filtered_fields[field_name] = field_info
        
        return filtered_fields
    
    async def _generate_code(
        self,
        model_name: str,
        fields: Dict[str, Any],
        model_info: Dict[str, Any],
        include_documentation: bool = True
    ) -> str:
        """Generate Python model code using AI."""
        # Prepare field information for AI
        field_descriptions = []
        for field_name, field_info in fields.items():
            python_type = self._get_python_type(field_info)
            field_desc = {
                "name": field_name,
                "type": field_info["type"],
                "python_type": python_type,
                "required": field_info["required"],
                "help": field_info["help"],
                "relation": field_info.get("relation"),
                "selection": field_info.get("selection")
            }
            field_descriptions.append(field_desc)
        
        # Create prompt for code generation
        prompt = f"""Generate a complete Python Pydantic model for the Odoo model '{model_name}'.

Model Information:
- Name: {model_name}
- Description: {model_info.get('info', {}).get('info', 'Odoo model')}

Fields to include:
{json.dumps(field_descriptions, indent=2)}

Requirements:
1. Use Pydantic BaseModel as base class
2. Include proper type hints for all fields
3. Add Field() definitions with descriptions
4. Handle optional fields correctly
5. Include relationship fields with proper types
6. Add validation rules where appropriate
7. Include class docstring with model description
8. Use proper imports (typing, pydantic, datetime, etc.)
9. Follow Python naming conventions
10. Add _name class variable with Odoo model name

Example structure:
```python
from typing import Optional, List, ClassVar
from datetime import date, datetime
from pydantic import BaseModel, Field

class ModelName(BaseModel):
    \"\"\"Model description.\"\"\"
    
    _name: ClassVar[str] = "odoo.model.name"
    
    # Fields with proper types and descriptions
    field_name: str = Field(..., description="Field description")
    optional_field: Optional[str] = Field(None, description="Optional field")
```

Generate clean, production-ready code with proper formatting."""
        
        response = await self.ai_client.complete(
            prompt=prompt,
            system=self._get_generation_system_prompt(),
            temperature=0.1,
            max_tokens=2000
        )
        
        # Extract code from response (remove markdown formatting if present)
        code = response.content.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    
    def _get_python_type(self, field_info: Dict[str, Any]) -> str:
        """Get Python type for Odoo field."""
        field_type = field_info["type"]
        required = field_info["required"]
        
        # Get base type
        python_type = self.type_mappings.get(field_type, "Any")
        
        # Handle special cases
        if field_type == "selection" and field_info.get("selection"):
            # Create literal type for selection fields
            options = [opt[0] for opt in field_info["selection"] if opt]
            if options:
                python_type = f"Literal[{', '.join(repr(opt) for opt in options)}]"
        
        # Make optional if not required
        if not required and not python_type.startswith("Optional"):
            python_type = f"Optional[{python_type}]"
        
        return python_type
    
    def _get_generation_system_prompt(self) -> str:
        """Get system prompt for code generation."""
        return """You are an expert Python developer specializing in Pydantic models and Odoo integration.

Your expertise includes:
- Pydantic model design and best practices
- Python type hints and validation
- Odoo field types and relationships
- Clean code principles and formatting
- Documentation and code comments

When generating models:
1. Use precise type hints based on Odoo field types
2. Include comprehensive Field() definitions
3. Add clear, helpful docstrings
4. Follow Python naming conventions
5. Handle edge cases and validation properly
6. Generate clean, readable code
7. Include necessary imports
8. Use ClassVar for Odoo model name

Always generate production-ready code that follows best practices."""
