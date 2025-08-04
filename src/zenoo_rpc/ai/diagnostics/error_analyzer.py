"""
AI-powered error analysis and diagnosis for Zenoo RPC.

This module provides intelligent error analysis, root cause identification,
and actionable solution suggestions for common Odoo and Zenoo RPC issues.
"""

import json
import logging
import traceback
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.ai_client import AIClient
    from ...client import ZenooClient

logger = logging.getLogger(__name__)


class AIErrorAnalyzer:
    """AI-powered error analysis and diagnosis.
    
    This analyzer uses AI to understand errors, identify root causes,
    and provide actionable solutions with code examples.
    
    Features:
    - Intelligent error categorization
    - Root cause analysis
    - Step-by-step solutions
    - Code examples and best practices
    - Performance optimization suggestions
    - Prevention recommendations
    
    Example:
        >>> analyzer = AIErrorAnalyzer(ai_client, zenoo_client)
        >>> 
        >>> try:
        ...     result = await client.search("invalid.model", [])
        ... except Exception as e:
        ...     diagnosis = await analyzer.analyze_error(e)
        ...     print(f"Problem: {diagnosis['problem']}")
        ...     print(f"Solution: {diagnosis['solution']}")
    """
    
    def __init__(self, ai_client: "AIClient", zenoo_client: "ZenooClient"):
        """Initialize the error analyzer.
        
        Args:
            ai_client: AI client for error analysis
            zenoo_client: Zenoo client for context
        """
        self.ai_client = ai_client
        self.zenoo_client = zenoo_client
        
        # Common error patterns and their categories
        self.error_categories = {
            "authentication": [
                "AuthenticationError",
                "login failed",
                "invalid credentials",
                "access denied"
            ],
            "validation": [
                "ValidationError",
                "invalid field",
                "required field",
                "constraint violation"
            ],
            "connection": [
                "ConnectionError",
                "timeout",
                "network error",
                "server unreachable"
            ],
            "model": [
                "model not found",
                "invalid model",
                "access rights",
                "permission denied"
            ],
            "query": [
                "invalid domain",
                "syntax error",
                "field not found",
                "operator error"
            ],
            "performance": [
                "timeout",
                "memory error",
                "too many records",
                "slow query"
            ]
        }
    
    async def analyze_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze an error and provide diagnosis with solutions.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            Dictionary with comprehensive error analysis
            
        Example:
            >>> diagnosis = await analyzer.analyze_error(
            ...     AuthenticationError("Login failed"),
            ...     context={"database": "demo", "username": "admin"}
            ... )
            >>> print(diagnosis['problem'])
            >>> print(diagnosis['solution'])
            >>> print(diagnosis['example'])
        """
        # Extract error information
        error_info = self._extract_error_info(error, context)
        
        # Categorize the error
        category = self._categorize_error(error_info)
        
        # Get AI analysis
        analysis = await self._get_ai_analysis(error_info, category)
        
        # Enhance with specific solutions
        enhanced_analysis = await self._enhance_with_solutions(analysis, error_info)
        
        return enhanced_analysis
    
    async def suggest_optimization(self, query_stats: Dict[str, Any]) -> List[str]:
        """Suggest performance optimizations based on query statistics.
        
        Args:
            query_stats: Statistics about query performance
            
        Returns:
            List of optimization suggestions
            
        Example:
            >>> stats = {
            ...     "execution_time": 2.5,
            ...     "record_count": 10000,
            ...     "model": "res.partner",
            ...     "domain": [("is_company", "=", True)]
            ... }
            >>> suggestions = await analyzer.suggest_optimization(stats)
        """
        schema = {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of optimization suggestions"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Priority level for optimization"
                },
                "estimated_improvement": {
                    "type": "string",
                    "description": "Estimated performance improvement"
                }
            },
            "required": ["suggestions", "priority"]
        }
        
        prompt = f"""Analyze these query performance statistics and suggest optimizations:

Query Statistics:
{json.dumps(query_stats, indent=2)}

Consider:
1. Execution time and whether it's acceptable
2. Number of records and potential for pagination
3. Domain filters and indexing opportunities
4. Field selection optimization
5. Caching strategies
6. Batch processing possibilities

Provide specific, actionable suggestions for improving performance."""
        
        response = await self.ai_client.complete_structured(
            prompt=prompt,
            schema=schema,
            system=self._get_optimization_system_prompt(),
            temperature=0.2
        )
        
        return response["suggestions"]
    
    def _extract_error_info(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract comprehensive information about the error."""
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        # Add specific error attributes if available
        if hasattr(error, 'args') and error.args:
            error_info["args"] = error.args
        
        if hasattr(error, 'code'):
            error_info["code"] = error.code
        
        if hasattr(error, 'response'):
            error_info["response"] = str(error.response)
        
        return error_info
    
    def _categorize_error(self, error_info: Dict[str, Any]) -> str:
        """Categorize the error based on patterns."""
        error_text = f"{error_info['type']} {error_info['message']}".lower()
        
        for category, patterns in self.error_categories.items():
            for pattern in patterns:
                if pattern.lower() in error_text:
                    return category
        
        return "unknown"
    
    async def _get_ai_analysis(
        self,
        error_info: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """Get AI analysis of the error."""
        schema = {
            "type": "object",
            "properties": {
                "problem": {
                    "type": "string",
                    "description": "Clear description of the problem"
                },
                "root_cause": {
                    "type": "string",
                    "description": "Root cause analysis"
                },
                "solution": {
                    "type": "string",
                    "description": "Step-by-step solution"
                },
                "code_example": {
                    "type": "string",
                    "description": "Code example showing the fix"
                },
                "prevention": {
                    "type": "string",
                    "description": "How to prevent this error in the future"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence in the analysis (0-1)"
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Error severity level"
                }
            },
            "required": ["problem", "root_cause", "solution", "confidence", "severity"]
        }
        
        prompt = f"""Analyze this error and provide a comprehensive diagnosis:

Error Information:
Type: {error_info['type']}
Message: {error_info['message']}
Category: {category}
Context: {json.dumps(error_info.get('context', {}), indent=2)}

Provide:
1. Clear problem description
2. Root cause analysis
3. Step-by-step solution
4. Code example if applicable
5. Prevention strategies
6. Confidence level in your analysis
7. Severity assessment

Focus on practical, actionable solutions for Odoo/Zenoo RPC development."""
        
        try:
            response = await self.ai_client.complete_structured(
                prompt=prompt,
                schema=schema,
                system=self._get_analysis_system_prompt(),
                temperature=0.1
            )

            # Validate response structure and provide defaults for missing fields
            validated_response = self._validate_analysis_response(response)
            return validated_response

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Return fallback response
            return self._get_fallback_analysis(error_info, category)
    
    async def _enhance_with_solutions(
        self,
        analysis: Dict[str, Any],
        error_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance analysis with specific solutions based on error type."""
        error_type = error_info['type']
        
        # Add specific enhancements based on error type
        if "Authentication" in error_type:
            analysis["quick_fixes"] = [
                "Check API credentials",
                "Verify database name",
                "Ensure user has proper permissions",
                "Test connection with simple query"
            ]
        elif "Validation" in error_type:
            analysis["quick_fixes"] = [
                "Check required fields",
                "Validate field types",
                "Review domain syntax",
                "Check field permissions"
            ]
        elif "Connection" in error_type:
            analysis["quick_fixes"] = [
                "Check network connectivity",
                "Verify server URL and port",
                "Test with curl or browser",
                "Check firewall settings"
            ]
        
        # Add documentation links
        analysis["documentation"] = self._get_relevant_docs(error_type)
        
        return analysis

    def _validate_analysis_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix AI analysis response structure."""
        # Ensure all required fields exist with defaults
        validated = {
            "problem": response.get("problem", "Unknown problem occurred"),
            "root_cause": response.get("root_cause", "Root cause analysis unavailable"),
            "solution": response.get("solution", "Please check error details and try again"),
            "confidence": response.get("confidence", 0.5),
            "severity": response.get("severity", "medium"),
            "code_example": response.get("code_example", ""),
            "prevention": response.get("prevention", "Follow best practices to prevent similar issues")
        }

        # Validate confidence is a number between 0 and 1
        try:
            confidence = float(validated["confidence"])
            validated["confidence"] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            validated["confidence"] = 0.5

        # Validate severity is one of allowed values
        allowed_severities = ["low", "medium", "high", "critical"]
        if validated["severity"] not in allowed_severities:
            validated["severity"] = "medium"

        return validated

    def _get_fallback_analysis(self, error_info: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Provide fallback analysis when AI fails."""
        error_type = error_info.get("type", "Unknown")
        error_message = error_info.get("message", "No message available")

        return {
            "problem": f"{error_type}: {error_message}",
            "root_cause": f"Error of type '{error_type}' occurred in category '{category}'",
            "solution": "Check the error message and context for specific details. Consult documentation or support if needed.",
            "confidence": 0.3,  # Low confidence for fallback
            "severity": "medium",
            "code_example": "# Check error details and context\n# Review relevant documentation\n# Test with simplified case",
            "prevention": "Follow error handling best practices and validate inputs before operations"
        }

    def _get_analysis_system_prompt(self) -> str:
        """Get system prompt for error analysis."""
        return """You are an expert Odoo developer and troubleshooting specialist.

Your expertise includes:
- Odoo framework internals and common issues
- Zenoo RPC library architecture and usage
- Python async programming and error handling
- Database operations and performance optimization
- Authentication and security best practices

When analyzing errors:
1. Be specific and actionable in your solutions
2. Provide code examples when helpful
3. Consider both immediate fixes and long-term prevention
4. Assess severity accurately
5. Give realistic confidence scores

Always focus on practical solutions that developers can implement immediately."""
    
    def _get_optimization_system_prompt(self) -> str:
        """Get system prompt for optimization suggestions."""
        return """You are a performance optimization expert for Odoo and database operations.

Your expertise includes:
- Query optimization and indexing strategies
- Caching patterns and best practices
- Batch processing and pagination
- Memory management and resource optimization
- Odoo-specific performance considerations

When suggesting optimizations:
1. Prioritize high-impact, low-effort improvements
2. Consider the specific context and constraints
3. Provide realistic performance estimates
4. Balance performance with code maintainability
5. Consider both immediate and long-term optimizations"""
    
    def _get_relevant_docs(self, error_type: str) -> List[str]:
        """Get relevant documentation links for error type."""
        docs = {
            "AuthenticationError": [
                "Authentication Guide",
                "API Key Setup",
                "User Permissions"
            ],
            "ValidationError": [
                "Field Validation",
                "Domain Syntax",
                "Model Constraints"
            ],
            "ConnectionError": [
                "Connection Setup",
                "Network Troubleshooting",
                "Server Configuration"
            ]
        }
        
        return docs.get(error_type, ["General Troubleshooting"])
