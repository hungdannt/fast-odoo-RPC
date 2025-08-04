"""
AI Assistant for Zenoo RPC client integration.

This module provides the main AI interface that integrates with ZenooClient,
offering natural language queries, error diagnosis, and intelligent assistance.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

from .ai_client import AIClient, AIConfig, AIProvider
from ..query.nl_to_query import NaturalLanguageQueryProcessor
from ..diagnostics.error_analyzer import AIErrorAnalyzer

if TYPE_CHECKING:
    from ...client import ZenooClient
    from ...query.builder import QueryBuilder

logger = logging.getLogger(__name__)


class AIAssistant:
    """AI Assistant for Zenoo RPC client.
    
    This class provides the main interface for AI-powered features in Zenoo RPC,
    including natural language queries, error diagnosis, and code generation.
    
    The assistant integrates seamlessly with ZenooClient and provides:
    - Natural language to Odoo query conversion
    - Intelligent error analysis and solutions
    - Smart code generation and optimization
    - Performance recommendations
    
    Example:
        >>> async with ZenooClient("localhost") as client:
        ...     await client.setup_ai(
        ...         provider="gemini",
        ...         model="gemini-2.5-flash-lite",
        ...         api_key="your-key"
        ...     )
        ...     
        ...     # Natural language queries
        ...     partners = await client.ai.query("Find all companies in Vietnam")
        ...     
        ...     # Error diagnosis
        ...     try:
        ...         result = await client.search("invalid.model", [])
        ...     except Exception as e:
        ...         diagnosis = await client.ai.diagnose(e)
        ...         print(f"Problem: {diagnosis.problem}")
        ...         print(f"Solution: {diagnosis.solution}")
    """
    
    def __init__(self, zenoo_client: "ZenooClient"):
        """Initialize AI assistant with Zenoo client reference.
        
        Args:
            zenoo_client: The ZenooClient instance to assist
        """
        self.client = zenoo_client
        self.ai_client: Optional[AIClient] = None
        self.query_processor: Optional[NaturalLanguageQueryProcessor] = None
        self.error_analyzer: Optional[AIErrorAnalyzer] = None
        self._initialized = False
    
    async def initialize(
        self,
        provider: Union[str, AIProvider] = "gemini",
        model: str = "gemini-2.5-flash-lite",
        api_key: str = "",
        **config_kwargs
    ) -> None:
        """Initialize AI capabilities.
        
        Args:
            provider: AI provider (gemini, openai, anthropic, azure)
            model: Model name (e.g., "gemini-2.5-flash-lite")
            api_key: API key for the provider
            **config_kwargs: Additional configuration parameters
            
        Raises:
            ValueError: If required parameters are missing
            ImportError: If AI dependencies are not installed
        """
        if not api_key:
            raise ValueError("API key is required for AI features")
        
        # Convert string provider to enum
        if isinstance(provider, str):
            try:
                provider = AIProvider(provider.lower())
            except ValueError:
                raise ValueError(f"Unsupported provider: {provider}")
        
        # Create AI configuration
        config = AIConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            **config_kwargs
        )
        
        # Initialize AI client
        self.ai_client = AIClient(config)
        await self.ai_client.initialize()
        
        # Initialize AI components
        self.query_processor = NaturalLanguageQueryProcessor(self.ai_client, self.client)
        self.error_analyzer = AIErrorAnalyzer(self.ai_client, self.client)
        
        self._initialized = True
        logger.info(f"AI assistant initialized with {provider.value}/{model}")
    
    async def query(
        self,
        natural_language: str,
        model_hint: Optional[str] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[Any]:
        """Convert natural language to Odoo query and execute.
        
        Args:
            natural_language: Natural language description of the query
            model_hint: Hint about which Odoo model to query
            limit: Maximum number of records to return
            **kwargs: Additional query parameters
            
        Returns:
            List of records matching the query
            
        Raises:
            RuntimeError: If AI assistant is not initialized
            ValueError: If query cannot be processed
            
        Example:
            >>> partners = await client.ai.query(
            ...     "Find all companies in Vietnam with revenue > 1M USD"
            ... )
            >>> 
            >>> users = await client.ai.query(
            ...     "Show me active users created this month",
            ...     model_hint="res.users"
            ... )
        """
        self._ensure_initialized()
        
        return await self.query_processor.process_query(
            natural_language=natural_language,
            model_hint=model_hint,
            limit=limit,
            **kwargs
        )
    
    async def explain_query(self, natural_language: str) -> Dict[str, Any]:
        """Explain how a natural language query would be converted.
        
        Args:
            natural_language: Natural language description
            
        Returns:
            Dictionary with query explanation, Odoo domain, and model info
            
        Example:
            >>> explanation = await client.ai.explain_query(
            ...     "Find companies in Vietnam"
            ... )
            >>> print(f"Model: {explanation['model']}")
            >>> print(f"Domain: {explanation['domain']}")
            >>> print(f"Explanation: {explanation['explanation']}")
        """
        self._ensure_initialized()
        
        return await self.query_processor.explain_query(natural_language)
    
    async def diagnose(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Diagnose an error and provide solutions.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            Dictionary with problem analysis, solutions, and examples
            
        Example:
            >>> try:
            ...     result = await client.search("invalid.model", [])
            ... except Exception as e:
            ...     diagnosis = await client.ai.diagnose(e)
            ...     print(f"Problem: {diagnosis['problem']}")
            ...     print(f"Solution: {diagnosis['solution']}")
            ...     print(f"Example: {diagnosis['example']}")
        """
        self._ensure_initialized()
        
        return await self.error_analyzer.analyze_error(error, context)
    
    async def suggest_optimization(self, query_stats: Dict[str, Any]) -> List[str]:
        """Suggest optimizations for query performance.
        
        Args:
            query_stats: Statistics about query performance
            
        Returns:
            List of optimization suggestions
            
        Example:
            >>> stats = {"execution_time": 2.5, "record_count": 10000}
            >>> suggestions = await client.ai.suggest_optimization(stats)
            >>> for suggestion in suggestions:
            ...     print(f"💡 {suggestion}")
        """
        self._ensure_initialized()
        
        return await self.error_analyzer.suggest_optimization(query_stats)
    

    
    async def chat(self, message: str, context: Optional[str] = None) -> str:
        """Have a conversation about Odoo development.
        
        Args:
            message: User message or question
            context: Additional context for the conversation
            
        Returns:
            AI response with helpful information
            
        Example:
            >>> response = await client.ai.chat(
            ...     "How do I create a Many2one field in Odoo?",
            ...     context="I'm working with res.partner model"
            ... )
            >>> print(response)
        """
        self._ensure_initialized()
        
        system_prompt = """You are an expert Odoo developer assistant. Help users with:
        - Odoo model development and relationships
        - Domain filters and search queries  
        - Best practices for Odoo development
        - Troubleshooting common issues
        - Performance optimization
        
        Provide clear, practical answers with code examples when helpful."""
        
        if context:
            message = f"Context: {context}\n\nQuestion: {message}"
        
        response = await self.ai_client.complete(
            prompt=message,
            system=system_prompt,
            temperature=0.3
        )
        
        return response.content
    
    def _ensure_initialized(self) -> None:
        """Ensure AI assistant is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "AI assistant not initialized. Call client.setup_ai() first."
            )
    
    async def close(self) -> None:
        """Clean up AI resources."""
        if self.ai_client:
            await self.ai_client.close()
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if AI assistant is initialized."""
        return self._initialized
    
    @property
    def provider_info(self) -> Optional[Dict[str, str]]:
        """Get information about the AI provider."""
        if not self.ai_client:
            return None
        
        return {
            "provider": self.ai_client.provider_name,
            "model": self.ai_client.model_name,
            "initialized": str(self._initialized)
        }
