"""
Tests for AI integration features in Zenoo RPC.

This module tests the AI-powered capabilities including natural language
queries, error diagnosis, and code generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from zenoo_rpc.ai import AI_AVAILABLE, AINotAvailableError
from zenoo_rpc.client import ZenooClient


class TestAIAvailability:
    """Test AI availability and import handling."""
    
    def test_ai_availability_check(self):
        """Test AI availability detection."""
        # This will depend on whether litellm is installed
        assert isinstance(AI_AVAILABLE, bool)
    
    @pytest.mark.skipif(AI_AVAILABLE, reason="AI is available")
    def test_ai_not_available_error(self):
        """Test error when AI features are not available."""
        from zenoo_rpc.ai import get_ai_import_error
        
        error = get_ai_import_error()
        assert isinstance(error, ImportError)


@pytest.mark.skipif(not AI_AVAILABLE, reason="AI features not available")
class TestAIClient:
    """Test AI client functionality."""
    
    @pytest.fixture
    def mock_ai_config(self):
        """Mock AI configuration."""
        from zenoo_rpc.ai.core.ai_client import AIConfig, AIProvider
        
        return AIConfig(
            provider=AIProvider.GEMINI,
            model="gemini-2.5-flash-lite",
            api_key="test-api-key",
            temperature=0.1,
            max_tokens=1000
        )
    
    @pytest.fixture
    def mock_ai_client(self, mock_ai_config):
        """Mock AI client."""
        from zenoo_rpc.ai.core.ai_client import AIClient
        
        with patch('zenoo_rpc.ai.core.ai_client.acompletion') as mock_completion:
            # Mock successful completion response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "gemini/gemini-2.5-flash-lite"
            mock_response.usage.dict.return_value = {"total_tokens": 100}
            
            mock_completion.return_value = mock_response
            
            client = AIClient(mock_ai_config)
            client._initialized = True  # Skip initialization
            
            yield client
    
    async def test_ai_client_initialization(self, mock_ai_config):
        """Test AI client initialization."""
        from zenoo_rpc.ai.core.ai_client import AIClient
        
        with patch('zenoo_rpc.ai.core.ai_client.acompletion') as mock_completion:
            # Mock initialization test
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "gemini/gemini-2.5-flash-lite"
            mock_response.usage.dict.return_value = {"total_tokens": 10}
            
            mock_completion.return_value = mock_response
            
            client = AIClient(mock_ai_config)
            await client.initialize()
            
            assert client.is_initialized()
            assert client.provider_name == "gemini"
            assert client.model_name == "gemini-2.5-flash-lite"
    
    async def test_ai_client_completion(self, mock_ai_client):
        """Test AI client completion."""
        response = await mock_ai_client.complete(
            prompt="Test prompt",
            system="Test system"
        )
        
        assert response.content == "Test response"
        assert response.model == "gemini/gemini-2.5-flash-lite"
        assert response.finish_reason == "stop"
    
    async def test_ai_client_structured_completion(self, mock_ai_client):
        """Test structured completion."""
        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"}
            }
        }
        
        with patch.object(mock_ai_client, 'complete') as mock_complete:
            mock_complete.return_value.content = '{"result": "test"}'
            
            result = await mock_ai_client.complete_structured(
                prompt="Test prompt",
                schema=schema
            )
            
            assert result == {"result": "test"}


@pytest.mark.skipif(not AI_AVAILABLE, reason="AI features not available")
class TestAIAssistant:
    """Test AI assistant functionality."""
    
    @pytest.fixture
    def mock_zenoo_client(self):
        """Mock Zenoo client."""
        client = MagicMock(spec=ZenooClient)
        client.search_read = AsyncMock(return_value=[
            {"id": 1, "name": "Test Company", "is_company": True}
        ])
        client.search = AsyncMock(return_value=[1, 2, 3])
        client.read = AsyncMock(return_value=[
            {"id": 1, "name": "Test 1"},
            {"id": 2, "name": "Test 2"},
            {"id": 3, "name": "Test 3"}
        ])
        return client
    
    @pytest.fixture
    def mock_ai_assistant(self, mock_zenoo_client):
        """Mock AI assistant."""
        from zenoo_rpc.ai.core.ai_assistant import AIAssistant
        
        assistant = AIAssistant(mock_zenoo_client)
        
        # Mock AI client
        mock_ai_client = MagicMock()
        mock_ai_client.complete_structured = AsyncMock(return_value={
            "model": "res.partner",
            "domain": [("is_company", "=", True)],
            "fields": ["name", "email"],
            "reasoning": "Test reasoning",
            "confidence": 0.9
        })
        mock_ai_client.complete = AsyncMock()
        mock_ai_client.complete.return_value.content = "Test response"
        
        assistant.ai_client = mock_ai_client
        assistant._initialized = True
        
        # Mock processors
        assistant.query_processor = MagicMock()
        assistant.query_processor.process_query = AsyncMock(return_value=[
            {"id": 1, "name": "Test Company"}
        ])
        assistant.query_processor.explain_query = AsyncMock(return_value={
            "model": "res.partner",
            "domain": [("is_company", "=", True)],
            "explanation": "Test explanation"
        })
        
        assistant.error_analyzer = MagicMock()
        assistant.error_analyzer.analyze_error = AsyncMock(return_value={
            "problem": "Test problem",
            "solution": "Test solution",
            "confidence": 0.9
        })
        
        assistant.model_generator = MagicMock()
        assistant.model_generator.generate_model = AsyncMock(return_value="""
class ResPartner(BaseModel):
    name: str
    email: Optional[str]
""")
        
        return assistant
    
    async def test_ai_assistant_initialization(self, mock_zenoo_client):
        """Test AI assistant initialization."""
        from zenoo_rpc.ai.core.ai_assistant import AIAssistant
        
        assistant = AIAssistant(mock_zenoo_client)
        
        with patch('zenoo_rpc.ai.core.ai_client.AIClient') as mock_ai_client_class:
            mock_ai_client = MagicMock()
            mock_ai_client.initialize = AsyncMock()
            mock_ai_client_class.return_value = mock_ai_client
            
            await assistant.initialize(
                provider="gemini",
                model="gemini-2.5-flash-lite",
                api_key="test-key"
            )
            
            assert assistant.is_initialized
            assert assistant.ai_client == mock_ai_client
    
    async def test_natural_language_query(self, mock_ai_assistant):
        """Test natural language query processing."""
        result = await mock_ai_assistant.query("Find all companies")
        
        assert result == [{"id": 1, "name": "Test Company"}]
        mock_ai_assistant.query_processor.process_query.assert_called_once()
    
    async def test_query_explanation(self, mock_ai_assistant):
        """Test query explanation."""
        explanation = await mock_ai_assistant.explain_query("Find all companies")
        
        assert explanation["model"] == "res.partner"
        assert explanation["domain"] == [("is_company", "=", True)]
        mock_ai_assistant.query_processor.explain_query.assert_called_once()
    
    async def test_error_diagnosis(self, mock_ai_assistant):
        """Test error diagnosis."""
        test_error = ValueError("Test error")
        
        diagnosis = await mock_ai_assistant.diagnose(test_error)
        
        assert diagnosis["problem"] == "Test problem"
        assert diagnosis["solution"] == "Test solution"
        mock_ai_assistant.error_analyzer.analyze_error.assert_called_once_with(
            test_error, None
        )
    
    async def test_model_generation(self, mock_ai_assistant):
        """Test model generation."""
        model_code = await mock_ai_assistant.generate_model("res.partner")
        
        assert "class ResPartner" in model_code
        assert "name: str" in model_code
        mock_ai_assistant.model_generator.generate_model.assert_called_once()
    
    async def test_chat_functionality(self, mock_ai_assistant):
        """Test chat functionality."""
        response = await mock_ai_assistant.chat("How do I create a Many2one field?")
        
        assert response == "Test response"
        mock_ai_assistant.ai_client.complete.assert_called_once()


@pytest.mark.skipif(not AI_AVAILABLE, reason="AI features not available")
class TestZenooClientAIIntegration:
    """Test AI integration with ZenooClient."""
    
    @pytest.fixture
    def mock_zenoo_client(self):
        """Mock Zenoo client for testing."""
        with patch('zenoo_rpc.client.AsyncTransport'), \
             patch('zenoo_rpc.client.SessionManager'):
            
            client = ZenooClient("http://localhost:8069")
            return client
    
    async def test_setup_ai_success(self, mock_zenoo_client):
        """Test successful AI setup."""
        with patch('zenoo_rpc.ai.core.ai_assistant.AIAssistant') as mock_assistant_class:
            mock_assistant = MagicMock()
            mock_assistant.initialize = AsyncMock()
            mock_assistant_class.return_value = mock_assistant
            
            ai_assistant = await mock_zenoo_client.setup_ai(
                provider="gemini",
                model="gemini-2.5-flash-lite",
                api_key="test-key"
            )
            
            assert mock_zenoo_client.ai == mock_assistant
            assert ai_assistant == mock_assistant
            mock_assistant.initialize.assert_called_once()
    
    async def test_setup_ai_missing_dependencies(self, mock_zenoo_client):
        """Test AI setup with missing dependencies."""
        with patch('zenoo_rpc.client.ZenooClient.setup_ai') as mock_setup:
            mock_setup.side_effect = ImportError("AI dependencies not available")
            
            with pytest.raises(ImportError, match="AI dependencies not available"):
                await mock_zenoo_client.setup_ai(api_key="test-key")
    
    async def test_ai_cleanup_on_close(self, mock_zenoo_client):
        """Test AI cleanup when client is closed."""
        # Setup mock AI assistant
        mock_ai = MagicMock()
        mock_ai.close = AsyncMock()
        mock_zenoo_client.ai = mock_ai
        
        # Mock transport close
        mock_zenoo_client._transport.close = AsyncMock()
        
        await mock_zenoo_client.close()
        
        mock_ai.close.assert_called_once()


@pytest.mark.skipif(not AI_AVAILABLE, reason="AI features not available")
class TestAIErrorHandling:
    """Test AI error handling scenarios."""
    
    async def test_ai_client_initialization_failure(self):
        """Test AI client initialization failure."""
        from zenoo_rpc.ai.core.ai_client import AIClient, AIConfig, AIProvider
        
        config = AIConfig(
            provider=AIProvider.GEMINI,
            model="invalid-model",
            api_key="invalid-key"
        )
        
        with patch('zenoo_rpc.ai.core.ai_client.acompletion') as mock_completion:
            mock_completion.side_effect = Exception("API Error")
            
            client = AIClient(config)
            
            with pytest.raises(Exception, match="API Error"):
                await client.initialize()
    
    async def test_natural_language_query_failure(self):
        """Test natural language query processing failure."""
        from zenoo_rpc.ai.query.nl_to_query import NaturalLanguageQueryProcessor
        
        mock_ai_client = MagicMock()
        mock_ai_client.complete_structured = AsyncMock(side_effect=Exception("AI Error"))
        
        mock_zenoo_client = MagicMock()
        
        processor = NaturalLanguageQueryProcessor(mock_ai_client, mock_zenoo_client)
        
        with pytest.raises(Exception):
            await processor.process_query("Find all companies")
    
    async def test_error_analysis_low_confidence(self):
        """Test error analysis with low confidence."""
        from zenoo_rpc.ai.diagnostics.error_analyzer import AIErrorAnalyzer
        
        mock_ai_client = MagicMock()
        mock_ai_client.complete_structured = AsyncMock(return_value={
            "problem": "Unclear problem",
            "root_cause": "Unknown",
            "solution": "Try again",
            "confidence": 0.3,  # Low confidence
            "severity": "medium"
        })
        
        mock_zenoo_client = MagicMock()
        
        analyzer = AIErrorAnalyzer(mock_ai_client, mock_zenoo_client)
        
        test_error = ValueError("Ambiguous error")
        result = await analyzer.analyze_error(test_error)
        
        assert result["confidence"] == 0.3
        # Should still return result even with low confidence
