# ⚙️ AI Configuration Guide

Master the configuration and fine-tuning of Zenoo RPC's AI features for optimal performance!

## 🎯 Overview

This guide covers:
- **AI Provider Configuration** for different services
- **Performance Tuning** parameters and optimization
- **Security and API Key Management** best practices
- **Environment-Specific Settings** for development, staging, and production
- **Troubleshooting** common configuration issues

## 🔧 Provider Configuration

### Gemini (Google AI) Configuration

```python
import asyncio
from zenoo_rpc import ZenooClient

async def configure_gemini():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        
        # Basic Gemini configuration
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",  # Fast and cost-effective
            api_key="your-gemini-api-key",
            temperature=0.1,                # Low for deterministic responses
            max_tokens=4096,               # Reasonable limit
            timeout=30.0,                  # 30 second timeout
            max_retries=3                  # Retry failed requests
        )
        
        # Advanced Gemini configuration
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-pro",       # More capable but slower
            api_key="your-gemini-api-key",
            temperature=0.2,               # Slightly more creative
            max_tokens=8192,              # Higher token limit
            timeout=60.0,                 # Longer timeout for complex tasks
            max_retries=5,                # More retries for reliability
            # Additional Gemini-specific settings
            safety_settings={
                "harassment": "block_none",
                "hate_speech": "block_none",
                "sexually_explicit": "block_none",
                "dangerous_content": "block_none"
            }
        )

asyncio.run(configure_gemini())
```

### OpenAI Configuration

```python
async def configure_openai():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        
        # GPT-4o Mini (cost-effective)
        await client.setup_ai(
            provider="openai",
            model="gpt-4o-mini",
            api_key="your-openai-api-key",
            temperature=0.1,
            max_tokens=4096,
            timeout=30.0,
            max_retries=3,
            # OpenAI-specific settings
            frequency_penalty=0.0,
            presence_penalty=0.0,
            top_p=1.0
        )
        
        # GPT-4o (more capable)
        await client.setup_ai(
            provider="openai",
            model="gpt-4o",
            api_key="your-openai-api-key",
            temperature=0.2,
            max_tokens=8192,
            timeout=60.0,
            max_retries=5
        )
```

### Anthropic Claude Configuration

```python
async def configure_anthropic():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        
        # Claude 3 Haiku (fast and efficient)
        await client.setup_ai(
            provider="anthropic",
            model="claude-3-haiku-20240307",
            api_key="your-anthropic-api-key",
            temperature=0.1,
            max_tokens=4096,
            timeout=30.0,
            max_retries=3
        )
        
        # Claude 3.5 Sonnet (balanced performance)
        await client.setup_ai(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="your-anthropic-api-key",
            temperature=0.2,
            max_tokens=8192,
            timeout=60.0,
            max_retries=5
        )
```

### Azure OpenAI Configuration

```python
async def configure_azure_openai():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        
        await client.setup_ai(
            provider="azure",
            model="gpt-4o-mini",  # Your Azure deployment name
            api_key="your-azure-api-key",
            base_url="https://your-resource.openai.azure.com/",
            temperature=0.1,
            max_tokens=4096,
            timeout=30.0,
            max_retries=3,
            # Azure-specific settings
            api_version="2024-02-15-preview"
        )
```

## 🎛️ Performance Tuning

### Temperature Settings

```python
# Temperature controls creativity vs consistency
async def configure_temperature():
    
    # Deterministic responses (recommended for most business use)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key="your-key",
        temperature=0.0  # Most deterministic
    )
    
    # Balanced responses
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite", 
        api_key="your-key",
        temperature=0.3  # Good balance
    )
    
    # Creative responses (for brainstorming, content generation)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key="your-key",
        temperature=0.7  # More creative
    )
```

### Token Limits and Optimization

```python
async def configure_tokens():
    
    # For quick responses (queries, simple analysis)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key="your-key",
        max_tokens=1024  # Quick responses
    )
    
    # For detailed analysis (error diagnosis, complex queries)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key="your-key",
        max_tokens=4096  # Detailed responses
    )
    
    # For comprehensive reports (model generation, documentation)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-pro",
        api_key="your-key",
        max_tokens=8192  # Comprehensive responses
    )
```

### Timeout and Retry Configuration

```python
async def configure_reliability():
    
    # Fast operations (development, testing)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key="your-key",
        timeout=15.0,     # Quick timeout
        max_retries=2     # Fewer retries
    )
    
    # Production operations (reliability focus)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key="your-key",
        timeout=60.0,     # Longer timeout
        max_retries=5     # More retries
    )
    
    # Critical operations (maximum reliability)
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-pro",
        api_key="your-key",
        timeout=120.0,    # Extended timeout
        max_retries=10    # Maximum retries
    )
```

## 🔐 Security and API Key Management

### Environment Variables

```bash
# .env file
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
AZURE_OPENAI_API_KEY=your-azure-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Optional: Environment-specific settings
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-flash-lite
AI_TEMPERATURE=0.1
AI_MAX_TOKENS=4096
AI_TIMEOUT=30.0
AI_MAX_RETRIES=3
```

```python
import os
from zenoo_rpc import ZenooClient

async def secure_ai_setup():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        
        # Load from environment variables
        await client.setup_ai(
            provider=os.getenv("AI_PROVIDER", "gemini"),
            model=os.getenv("AI_MODEL", "gemini-2.5-flash-lite"),
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
            timeout=float(os.getenv("AI_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("AI_MAX_RETRIES", "3"))
        )
```

### API Key Rotation

```python
class APIKeyManager:
    """Manage API key rotation and fallback."""
    
    def __init__(self):
        self.primary_keys = {
            "gemini": os.getenv("GEMINI_API_KEY_PRIMARY"),
            "openai": os.getenv("OPENAI_API_KEY_PRIMARY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY_PRIMARY")
        }
        
        self.fallback_keys = {
            "gemini": os.getenv("GEMINI_API_KEY_FALLBACK"),
            "openai": os.getenv("OPENAI_API_KEY_FALLBACK"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY_FALLBACK")
        }
    
    async def setup_ai_with_fallback(self, client, provider, **config):
        """Setup AI with automatic fallback on key failure."""
        
        try:
            # Try primary key
            await client.setup_ai(
                provider=provider,
                api_key=self.primary_keys[provider],
                **config
            )
            print(f"✅ AI setup successful with primary key for {provider}")
            
        except Exception as e:
            if "authentication" in str(e).lower() and self.fallback_keys[provider]:
                print(f"⚠️ Primary key failed, trying fallback for {provider}")
                
                await client.setup_ai(
                    provider=provider,
                    api_key=self.fallback_keys[provider],
                    **config
                )
                print(f"✅ AI setup successful with fallback key for {provider}")
            else:
                raise

# Usage
key_manager = APIKeyManager()
await key_manager.setup_ai_with_fallback(
    client,
    "gemini",
    model="gemini-2.5-flash-lite",
    temperature=0.1
)
```

## 🌍 Environment-Specific Configuration

### Development Environment

```python
async def development_config():
    """Optimized for development speed and cost."""
    
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",  # Fastest, cheapest
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.1,                # Consistent for testing
        max_tokens=2048,               # Moderate limit
        timeout=15.0,                  # Quick timeout
        max_retries=2,                 # Fewer retries
        # Development-specific settings
        debug_mode=True,               # Enable debug logging
        cache_responses=True           # Cache for faster iteration
    )
```

### Staging Environment

```python
async def staging_config():
    """Production-like configuration for testing."""
    
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.1,
        max_tokens=4096,               # Production-like limits
        timeout=30.0,                  # Production-like timeout
        max_retries=3,                 # Production-like retries
        # Staging-specific settings
        rate_limit_buffer=0.8,         # 80% of rate limit
        monitoring_enabled=True        # Enable monitoring
    )
```

### Production Environment

```python
async def production_config():
    """Optimized for production reliability and performance."""
    
    await client.setup_ai(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.1,
        max_tokens=4096,
        timeout=60.0,                  # Longer timeout for reliability
        max_retries=5,                 # More retries for reliability
        # Production-specific settings
        circuit_breaker_enabled=True,  # Enable circuit breaker
        rate_limit_buffer=0.7,         # Conservative rate limiting
        monitoring_enabled=True,       # Full monitoring
        alerting_enabled=True,         # Enable alerts
        fallback_provider="openai"     # Fallback provider
    )
```

## 📊 Monitoring and Observability

### Performance Monitoring

```python
class AIPerformanceMonitor:
    """Monitor AI performance and configuration effectiveness."""
    
    def __init__(self, client):
        self.client = client
        self.metrics = {
            "response_times": [],
            "token_usage": [],
            "error_rates": [],
            "cost_tracking": []
        }
    
    async def monitor_ai_performance(self):
        """Monitor AI performance metrics."""
        
        # Get AI provider info
        provider_info = self.client.ai.provider_info
        
        # Track performance metrics
        performance_data = {
            "provider": provider_info.get("provider"),
            "model": provider_info.get("model"),
            "average_response_time": sum(self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0,
            "total_tokens_used": sum(self.metrics["token_usage"]),
            "error_rate": len([e for e in self.metrics["error_rates"] if e]) / len(self.metrics["error_rates"]) if self.metrics["error_rates"] else 0
        }
        
        # Get AI analysis of performance
        analysis = await self.client.ai.chat(
            f"Analyze AI performance metrics and suggest optimizations:\n{performance_data}",
            context="AI performance monitoring and optimization"
        )
        
        return {
            "metrics": performance_data,
            "analysis": analysis
        }
    
    async def track_operation(self, operation_name, operation_func, *args, **kwargs):
        """Track individual AI operations."""
        
        start_time = time.time()
        
        try:
            result = await operation_func(*args, **kwargs)
            
            # Track success metrics
            response_time = time.time() - start_time
            self.metrics["response_times"].append(response_time)
            self.metrics["error_rates"].append(False)
            
            # Estimate token usage (simplified)
            estimated_tokens = len(str(result)) // 4  # Rough estimate
            self.metrics["token_usage"].append(estimated_tokens)
            
            return result
            
        except Exception as e:
            # Track error metrics
            response_time = time.time() - start_time
            self.metrics["response_times"].append(response_time)
            self.metrics["error_rates"].append(True)
            
            raise
```

### Configuration Validation

```python
async def validate_ai_configuration():
    """Validate AI configuration and suggest improvements."""
    
    # Test basic functionality
    try:
        test_response = await client.ai.chat("Test message")
        print("✅ Basic AI functionality working")
    except Exception as e:
        print(f"❌ Basic AI test failed: {e}")
        return False
    
    # Test performance
    start_time = time.time()
    performance_response = await client.ai.chat("Analyze this simple query performance test")
    response_time = time.time() - start_time
    
    if response_time > 10.0:
        print(f"⚠️ Slow response time: {response_time:.2f}s")
        print("Consider using a faster model or adjusting timeout settings")
    else:
        print(f"✅ Good response time: {response_time:.2f}s")
    
    # Test error handling
    try:
        await client.ai.chat("Test error handling with invalid context", context="invalid_context_test")
        print("✅ Error handling working")
    except Exception as e:
        print(f"⚠️ Error handling issue: {e}")
    
    # Get configuration recommendations
    provider_info = client.ai.provider_info
    recommendations = await client.ai.chat(
        f"Analyze this AI configuration and suggest improvements:\n{provider_info}",
        context="AI configuration optimization"
    )
    
    print(f"\n💡 Configuration Recommendations:\n{recommendations}")
    
    return True
```

## 🚨 Troubleshooting

### Common Configuration Issues

```python
async def troubleshoot_ai_config():
    """Troubleshoot common AI configuration issues."""
    
    issues_found = []
    
    # Check AI availability
    from zenoo_rpc.ai import AI_AVAILABLE, check_ai_availability
    
    if not AI_AVAILABLE:
        issues_found.append("AI dependencies not installed")
        print("❌ AI not available - run: pip install zenoo-rpc[ai]")
    
    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        issues_found.append("Missing API key")
        print("❌ GEMINI_API_KEY environment variable not set")
    
    # Check network connectivity
    try:
        test_response = await client.ai.chat("Connection test", max_tokens=10)
        print("✅ Network connectivity working")
    except Exception as e:
        issues_found.append(f"Network connectivity issue: {e}")
        print(f"❌ Network test failed: {e}")
    
    # Check rate limits
    try:
        # Make multiple quick requests to test rate limiting
        for i in range(5):
            await client.ai.chat(f"Rate limit test {i}", max_tokens=5)
        print("✅ Rate limiting working normally")
    except Exception as e:
        if "rate limit" in str(e).lower():
            issues_found.append("Rate limit exceeded")
            print("⚠️ Rate limit exceeded - consider adjusting request frequency")
        else:
            issues_found.append(f"Rate limit test failed: {e}")
    
    # Check model availability
    provider_info = client.ai.provider_info
    if provider_info.get("model") not in ["gemini-2.5-flash-lite", "gemini-2.5-pro"]:
        issues_found.append("Unsupported model")
        print(f"⚠️ Model {provider_info.get('model')} may not be supported")
    
    if not issues_found:
        print("✅ All configuration checks passed!")
    else:
        print(f"\n⚠️ Found {len(issues_found)} issues:")
        for issue in issues_found:
            print(f"  • {issue}")
    
    return issues_found
```

### Performance Optimization

```python
async def optimize_ai_performance():
    """Optimize AI performance based on usage patterns."""
    
    # Measure current performance
    start_time = time.time()
    test_responses = []
    
    for i in range(3):
        response = await client.ai.chat(f"Performance test {i}")
        test_responses.append(response)
    
    avg_response_time = (time.time() - start_time) / 3
    
    # Get optimization suggestions
    optimization_suggestions = await client.ai.chat(
        f"Optimize AI configuration for better performance:\n"
        f"Current average response time: {avg_response_time:.2f}s\n"
        f"Provider: {client.ai.provider_info.get('provider')}\n"
        f"Model: {client.ai.provider_info.get('model')}",
        context="AI performance optimization"
    )
    
    print(f"📊 Current Performance: {avg_response_time:.2f}s average")
    print(f"💡 Optimization Suggestions:\n{optimization_suggestions}")
    
    return {
        "current_performance": avg_response_time,
        "suggestions": optimization_suggestions
    }
```

## 🎯 Best Practices Summary

### 1. **Choose the Right Model**
- **Development**: `gemini-2.5-flash-lite` for speed and cost
- **Production**: `gemini-2.5-pro` for accuracy and capability
- **High-volume**: Consider rate limits and costs

### 2. **Optimize Parameters**
- **Temperature**: 0.1 for consistent business logic, 0.3 for balanced responses
- **Max Tokens**: 1024 for quick responses, 4096 for detailed analysis
- **Timeout**: 30s for normal operations, 60s+ for complex tasks

### 3. **Security**
- Always use environment variables for API keys
- Implement key rotation for production
- Monitor API usage and costs

### 4. **Reliability**
- Configure appropriate retries and timeouts
- Implement fallback providers
- Monitor performance and error rates

### 5. **Cost Management**
- Use faster models for simple tasks
- Implement request caching where appropriate
- Monitor token usage and optimize prompts

## 🎯 Next Steps

- **[AI Quick Start](./ai-quick-start.md)** - Get started with basic configuration
- **[Performance Optimization](./performance-optimization.md)** - Advanced performance tuning
- **[Advanced AI Features](./advanced-ai-features.md)** - Explore advanced capabilities
- **Production Deployment** - Deploy with proper monitoring and alerting

---

**💡 Pro Tip**: Start with conservative settings and gradually optimize based on your specific use case and performance requirements!
