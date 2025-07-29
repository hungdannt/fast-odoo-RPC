# 🚀 AI Quick Start Guide

Get started with Zenoo RPC's AI-powered features in minutes!

## 📋 Prerequisites

1. **Install Zenoo RPC with AI support:**
   ```bash
   pip install zenoo-rpc[ai]
   ```

2. **Get an AI API key:**
   - **Gemini (Recommended)**: Get free API key from [Google AI Studio](https://aistudio.google.com/)
   - **OpenAI**: Get API key from [OpenAI Platform](https://platform.openai.com/)
   - **Anthropic**: Get API key from [Anthropic Console](https://console.anthropic.com/)

## ⚡ Quick Setup

### Basic Setup

```python
import asyncio
from zenoo_rpc import ZenooClient

async def main():
    # Connect to Odoo
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        
        # Setup AI with Gemini (recommended)
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key="your-gemini-api-key"
        )
        
        # You're ready to use AI features!
        print("🤖 AI features are now available!")

asyncio.run(main())
```

### Environment Variables (Recommended)

```bash
# Set in your .env file or environment
export GEMINI_API_KEY="your-gemini-api-key"
export OPENAI_API_KEY="your-openai-api-key"  # Optional
```

```python
import os
from zenoo_rpc import ZenooClient

async def main():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        
        # AI will automatically use environment variables
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key=os.getenv("GEMINI_API_KEY")
        )
```

## 🎯 Core AI Features

### 1. Natural Language Queries

Convert plain English to Odoo queries:

```python
# Find companies in Vietnam
companies = await client.ai.query("Find all companies in Vietnam")

# Get recent customers
customers = await client.ai.query("Show me customers created this month")

# Complex queries
partners = await client.ai.query(
    "Find active partners with email addresses who are companies"
)
```

### 2. Intelligent Error Diagnosis

Get instant help when errors occur:

```python
try:
    result = await client.search("res.partner", [("invalid_field", "=", "value")])
except Exception as error:
    # Get AI diagnosis
    diagnosis = await client.ai.diagnose(error)
    
    print(f"Problem: {diagnosis['problem']}")
    print(f"Solution: {diagnosis['solution']}")
    print(f"Code Example: {diagnosis['code_example']}")
```

### 3. Smart Model Generation

Generate typed Python models from Odoo schemas:

```python
# Generate Pydantic model for res.partner
model_code = await client.ai.generate_model("res.partner")

# Save to file
with open("models/partner.py", "w") as f:
    f.write(model_code)

print("✅ Model generated successfully!")
```

### 4. AI Chat Assistant

Get expert advice on Odoo development:

```python
# Ask questions about Odoo
response = await client.ai.chat(
    "How do I create a Many2one field in Odoo?",
    context="Working with res.partner model"
)

print(response)
```

### 5. Performance Optimization

Get AI-powered performance suggestions:

```python
# Analyze slow queries
query_stats = {
    "execution_time": 3.2,
    "record_count": 15000,
    "model": "res.partner",
    "domain": [("customer_rank", ">", 0)]
}

suggestions = await client.ai.suggest_optimization(query_stats)

for suggestion in suggestions:
    print(f"💡 {suggestion}")
```

## 🔧 Configuration Options

### Provider Options

```python
# Gemini (Google) - Recommended
await client.setup_ai(
    provider="gemini",
    model="gemini-2.5-flash-lite",  # Fast and efficient
    api_key="your-key",
    temperature=0.1,  # More deterministic
    max_tokens=4096
)

# OpenAI
await client.setup_ai(
    provider="openai",
    model="gpt-4o-mini",  # Cost-effective
    api_key="your-key"
)

# Anthropic Claude
await client.setup_ai(
    provider="anthropic",
    model="claude-3-haiku-20240307",  # Fast
    api_key="your-key"
)
```

### Advanced Configuration

```python
await client.setup_ai(
    provider="gemini",
    model="gemini-2.5-flash-lite",
    api_key="your-key",
    temperature=0.1,        # Creativity level (0.0-1.0)
    max_tokens=4096,        # Response length limit
    timeout=30.0,           # Request timeout
    max_retries=3           # Retry attempts
)
```

## 🎯 Complete Example

```python
import asyncio
import os
from zenoo_rpc import ZenooClient

async def ai_demo():
    """Complete AI features demonstration."""
    
    async with ZenooClient("http://localhost:8069") as client:
        # Connect to Odoo
        await client.login("demo", "admin", "admin")
        
        # Setup AI
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        print("🤖 AI Features Demo")
        print("=" * 40)
        
        # 1. Natural Language Query
        print("\n1. Natural Language Query:")
        companies = await client.ai.query("Find all companies")
        print(f"Found {len(companies)} companies")
        
        # 2. Query Explanation
        print("\n2. Query Explanation:")
        explanation = await client.ai.explain_query("Find active users")
        print(f"Model: {explanation['model']}")
        print(f"Domain: {explanation['domain']}")
        
        # 3. AI Chat
        print("\n3. AI Chat:")
        response = await client.ai.chat("What is a domain filter in Odoo?")
        print(f"Answer: {response[:100]}...")
        
        # 4. Model Generation
        print("\n4. Model Generation:")
        model_code = await client.ai.generate_model("res.users")
        print(f"Generated {len(model_code)} characters of model code")
        
        # 5. Performance Analysis
        print("\n5. Performance Analysis:")
        stats = {
            "execution_time": 2.1,
            "record_count": 5000,
            "model": "res.partner"
        }
        suggestions = await client.ai.suggest_optimization(stats)
        print(f"Got {len(suggestions)} optimization suggestions")
        
        print("\n✅ AI Demo completed successfully!")

if __name__ == "__main__":
    asyncio.run(ai_demo())
```

## 🚨 Troubleshooting

### Common Issues

1. **ImportError: No module named 'litellm'**
   ```bash
   pip install zenoo-rpc[ai]
   ```

2. **Authentication Error**
   - Check your API key is correct
   - Verify the key has proper permissions
   - Check rate limits

3. **AI Features Not Available**
   ```python
   from zenoo_rpc.ai import AI_AVAILABLE, check_ai_availability
   
   if not AI_AVAILABLE:
       print("AI dependencies not installed")
       print("Run: pip install zenoo-rpc[ai]")
   ```

### Getting Help

- 📖 **Documentation**: Check detailed guides in this directory
- 🐛 **Issues**: Report bugs on GitHub
- 💬 **Discussions**: Join community discussions
- 📧 **Support**: Contact support for enterprise features

## 🎯 Next Steps

1. **📖 Read Detailed Guides**:
   - [Natural Language Queries](./natural-language-queries.md)
   - [Error Diagnosis](./error-diagnosis.md)
   - [Model Generation](./model-generation.md)
   - [AI Chat Assistant](./ai-chat-assistant.md)

2. **🔧 Advanced Configuration**:
   - [AI Configuration](./ai-configuration.md)
   - [Performance Optimization](./performance-optimization.md)
   - [Advanced Features](./advanced-ai-features.md)

3. **🚀 Production Deployment**:
   - Set up environment variables
   - Configure rate limiting
   - Monitor AI usage and costs
   - Implement error handling

---

**🎉 You're now ready to supercharge your Odoo development with AI!**
