"""
Natural Language to Odoo Query Processor.

This module converts natural language descriptions into optimized Odoo queries
using AI-powered analysis and domain generation.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.ai_client import AIClient
    from ...client import ZenooClient

logger = logging.getLogger(__name__)


class NaturalLanguageQueryProcessor:
    """Converts natural language to Odoo queries using AI.
    
    This processor analyzes natural language descriptions and converts them
    into optimized Odoo domain filters and search queries.
    
    Features:
    - Intelligent model detection from context
    - Domain filter generation with proper operators
    - Field mapping and validation
    - Query optimization suggestions
    - Support for complex queries with multiple conditions
    
    Example:
        >>> processor = NaturalLanguageQueryProcessor(ai_client, zenoo_client)
        >>> 
        >>> # Simple query
        >>> result = await processor.process_query("Find all companies")
        >>> 
        >>> # Complex query
        >>> result = await processor.process_query(
        ...     "Show customers in Vietnam with revenue > 1M created this year"
        ... )
    """
    
    def __init__(self, ai_client: "AIClient", zenoo_client: "ZenooClient"):
        """Initialize the query processor.
        
        Args:
            ai_client: AI client for language processing
            zenoo_client: Zenoo client for Odoo operations
        """
        self.ai_client = ai_client
        self.zenoo_client = zenoo_client
        
        # Common Odoo models and their typical fields
        self.common_models = {
            "partner": "res.partner",
            "customer": "res.partner", 
            "supplier": "res.partner",
            "company": "res.partner",
            "contact": "res.partner",
            "user": "res.users",
            "employee": "hr.employee",
            "product": "product.product",
            "invoice": "account.move",
            "sale": "sale.order",
            "purchase": "purchase.order",
            "project": "project.project",
            "task": "project.task",
            "lead": "crm.lead",
            "opportunity": "crm.lead",
        }
        
        # Common field mappings
        self.field_mappings = {
            "name": ["name", "display_name"],
            "email": ["email", "email_from"],
            "phone": ["phone", "mobile"],
            "address": ["street", "street2"],
            "city": ["city"],
            "country": ["country_id"],
            "state": ["state_id"],
            "revenue": ["revenue", "amount_total"],
            "amount": ["amount_total", "amount_untaxed"],
            "date": ["date", "create_date", "write_date"],
            "created": ["create_date"],
            "modified": ["write_date"],
            "active": ["active"],
            "company": ["is_company"],
            "customer": ["customer_rank"],
            "supplier": ["supplier_rank"],
        }
    
    async def process_query(
        self,
        natural_language: str,
        model_hint: Optional[str] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[Any]:
        """Process natural language query and return results.
        
        Args:
            natural_language: Natural language description
            model_hint: Hint about which model to query
            limit: Maximum number of records to return
            **kwargs: Additional query parameters
            
        Returns:
            List of records matching the query
            
        Raises:
            ValueError: If query cannot be processed
            Exception: If Odoo query fails
        """
        # Parse the natural language query
        query_info = await self._parse_query(natural_language, model_hint)
        
        model_name = query_info["model"]
        domain = query_info["domain"]
        fields = query_info.get("fields", [])
        
        # Apply limit if specified
        if limit:
            query_info["limit"] = limit
        
        logger.info(f"Executing query: {model_name} with domain {domain}")
        
        try:
            # Execute the query using ZenooClient
            if fields:
                results = await self.zenoo_client.search_read(
                    model_name,
                    domain,
                    fields,
                    limit=limit or 100
                )
            else:
                # Use execute_kw to call search method directly
                ids = await self.zenoo_client.execute_kw(
                    model_name,
                    "search",
                    [domain],
                    {"limit": limit or 100}
                )
                results = await self.zenoo_client.read(model_name, ids)

            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def explain_query(self, natural_language: str) -> Dict[str, Any]:
        """Explain how natural language converts to Odoo query.

        Args:
            natural_language: Natural language description

        Returns:
            Dictionary with explanation, model, domain, and fields
        """
        try:
            query_info = await self._parse_query(natural_language)

            explanation = await self._generate_explanation(natural_language, query_info)

            return {
                "natural_language": natural_language,
                "explanation": explanation,
                "model": query_info.get("model", "res.partner"),  # Safe fallback
                "domain": query_info.get("domain", []),
                "fields": query_info.get("fields", []),
                "estimated_records": query_info.get("estimated_records", "unknown")
            }
        except Exception as e:
            logger.error(f"Query explanation failed: {e}")
            # Return safe fallback explanation
            return {
                "natural_language": natural_language,
                "explanation": f"Unable to explain query: {str(e)}",
                "model": "res.partner",
                "domain": [],
                "fields": [],
                "estimated_records": "unknown"
            }
    
    async def _parse_query(
        self,
        natural_language: str,
        model_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse natural language into Odoo query components.
        
        Args:
            natural_language: Natural language description
            model_hint: Optional model hint
            
        Returns:
            Dictionary with model, domain, fields, and other query info
        """
        # Create schema for structured response
        schema = {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Odoo model name (e.g., 'res.partner')"
                },
                "domain": {
                    "type": "array",
                    "description": "Odoo domain filter as list of tuples",
                    "items": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3
                    }
                },
                "fields": {
                    "type": "array",
                    "description": "List of fields to retrieve",
                    "items": {"type": "string"}
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of the query interpretation"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score (0-1) for the interpretation"
                }
            },
            "required": ["model", "domain", "reasoning", "confidence"]
        }
        
        # Build prompt with context
        prompt = self._build_query_prompt(natural_language, model_hint)
        
        # Get structured response from AI
        response = await self.ai_client.complete_structured(
            prompt=prompt,
            schema=schema,
            system=self._get_system_prompt(),
            temperature=0.1
        )

        # Validate and process response with error handling
        if not isinstance(response, dict):
            logger.error(f"Invalid response type: {type(response)}")
            return self._get_fallback_query_response(prompt)

        # Check required fields
        required_fields = ["model", "domain"]
        missing_fields = [field for field in required_fields if field not in response]

        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            # Try to infer missing fields
            if "model" not in response:
                response["model"] = self._infer_model_from_query(prompt)
            if "domain" not in response:
                response["domain"] = []

        # Validate model exists
        model_name = response.get("model", "")
        if model_name and not await self._validate_model_exists(model_name):
            logger.warning(f"Model '{model_name}' may not exist, using fallback")
            response["model"] = "res.partner"  # Safe fallback

        # Handle optional confidence field
        confidence = response.get("confidence", 0.8)  # Default confidence
        if confidence < 0.7:
            logger.warning(f"Low confidence query interpretation: {confidence}")

        # Ensure response has all expected fields
        response.setdefault("fields", [])
        response.setdefault("reasoning", "AI query interpretation")
        response.setdefault("confidence", confidence)

        return response

    def _get_fallback_query_response(self, query: str) -> Dict[str, Any]:
        """Generate fallback response for failed queries."""
        return {
            "model": "res.partner",
            "domain": [],
            "fields": [],
            "reasoning": f"Unable to parse query: {query}",
            "confidence": 0.1
        }

    def _infer_model_from_query(self, query: str) -> str:
        """Infer Odoo model from query text."""
        query_lower = query.lower()

        # Common model mappings
        model_keywords = {
            "partner": "res.partner",
            "customer": "res.partner",
            "company": "res.partner",
            "contact": "res.partner",
            "user": "res.users",
            "product": "product.product",
            "sale": "sale.order",
            "purchase": "purchase.order",
            "invoice": "account.move",
            "lead": "crm.lead",
            "opportunity": "crm.lead"
        }

        for keyword, model in model_keywords.items():
            if keyword in query_lower:
                return model

        return "res.partner"  # Default fallback

    async def _validate_model_exists(self, model_name: str) -> bool:
        """Validate if model exists in Odoo."""
        try:
            # Try to get model info
            await self.zenoo_client.execute_kw(
                "ir.model",
                "search_count",
                [[["model", "=", model_name]]],
                {}
            )
            return True
        except Exception:
            return False

    def _build_query_prompt(self, natural_language: str, model_hint: Optional[str] = None) -> str:
        """Build prompt for query parsing."""
        prompt = f"""Convert this natural language query to an Odoo domain filter:

Query: "{natural_language}"
"""
        
        if model_hint:
            prompt += f"\nModel hint: {model_hint}"
        
        prompt += f"""

Available models and their common use cases:
{self._format_model_info()}

Common field mappings:
{self._format_field_mappings()}

Important rules:
1. Use exact Odoo model names (e.g., 'res.partner', not 'partner')
2. Domain filters must be valid Odoo syntax: [('field', 'operator', 'value')]
3. Use appropriate operators: =, !=, >, <, >=, <=, like, ilike, in, not in
4. For text searches, prefer 'ilike' for case-insensitive matching
5. For boolean fields, use True/False (not 1/0)
6. For date ranges, use proper date format: 'YYYY-MM-DD'
7. For Many2one fields, you can filter by name using field_id.name

Examples:
- "companies in Vietnam" → model: "res.partner", domain: [('is_company', '=', True), ('country_id.name', 'ilike', 'vietnam')]
- "active users" → model: "res.users", domain: [('active', '=', True)]
- "products with price > 100" → model: "product.product", domain: [('list_price', '>', 100)]
"""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for query processing."""
        return """You are an expert Odoo developer who converts natural language queries into precise Odoo domain filters.

Your task is to:
1. Identify the correct Odoo model from the natural language
2. Convert conditions into proper Odoo domain syntax
3. Suggest relevant fields to retrieve
4. Provide reasoning for your interpretation
5. Give a confidence score for the conversion

Always respond with valid JSON matching the provided schema.
Be precise with Odoo syntax and field names.
If unsure about a field name, use the most common equivalent."""
    
    def _format_model_info(self) -> str:
        """Format common models information."""
        lines = []
        for keyword, model in self.common_models.items():
            lines.append(f"  {keyword} → {model}")
        return "\n".join(lines)
    
    def _format_field_mappings(self) -> str:
        """Format field mappings information."""
        lines = []
        for concept, fields in self.field_mappings.items():
            lines.append(f"  {concept} → {', '.join(fields)}")
        return "\n".join(lines)
    
    async def _generate_explanation(
        self,
        natural_language: str,
        query_info: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of the query conversion."""
        prompt = f"""Explain how this natural language query was converted to an Odoo query:

Original: "{natural_language}"
Model: {query_info['model']}
Domain: {query_info['domain']}
Fields: {query_info.get('fields', [])}

Provide a clear, concise explanation of:
1. Why this model was chosen
2. How each condition in the domain relates to the original query
3. What fields will be retrieved and why

Keep the explanation under 3 sentences and make it understandable for developers."""
        
        response = await self.ai_client.complete(
            prompt=prompt,
            system="You are a helpful assistant explaining Odoo query conversions.",
            temperature=0.2,
            max_tokens=200
        )
        
        return response.content.strip()
