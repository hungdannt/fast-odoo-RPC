# 🤖 AI-Powered Features

Zenoo RPC includes cutting-edge AI capabilities that revolutionize Odoo development by providing intelligent assistance, natural language queries, and automated code generation.

## 🚀 Quick Start

### Installation

Install Zenoo RPC with AI features:

```bash
pip install zenoo-rpc[ai]
```

### Setup

```python
import asyncio
from zenoo_rpc import ZenooClient

async def main():
    async with ZenooClient("http://localhost:8069") as client:
        # Login to Odoo
        await client.login("demo", "admin", "admin")
        
        # Setup AI with Gemini
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key="your-gemini-api-key"
        )
        
        # Use AI features
        partners = await client.ai.query("Find all companies in Vietnam")
        print(f"Found {len(partners)} companies")

asyncio.run(main())
```

## 🎯 Core Features

### 1. Natural Language Queries

Convert natural language descriptions into optimized Odoo queries:

```python
# Natural language to Odoo queries
partners = await client.ai.query("Find all companies in Vietnam with revenue > 1M USD")

# Equivalent to:
# client.search_read("res.partner", [
#     ("is_company", "=", True),
#     ("country_id.name", "ilike", "vietnam"),
#     ("revenue", ">", 1000000)
# ])

# Get query explanations
explanation = await client.ai.explain_query("Find active users created this month")
print(f"Model: {explanation['model']}")
print(f"Domain: {explanation['domain']}")
print(f"Explanation: {explanation['explanation']}")
```

**Supported Query Types:**
- Entity searches: "Find all companies", "Show active users"
- Filtered searches: "Products with price > 100", "Customers in Vietnam"
- Date ranges: "Invoices from last week", "Users created this month"
- Complex conditions: "Companies with revenue > 1M and employees < 50"

### 2. Intelligent Error Diagnosis

Get AI-powered error analysis with actionable solutions:

```python
try:
    result = await client.search("invalid.model", [])
except Exception as error:
    diagnosis = await client.ai.diagnose(error)
    
    print(f"Problem: {diagnosis['problem']}")
    print(f"Root Cause: {diagnosis['root_cause']}")
    print(f"Solution: {diagnosis['solution']}")
    print(f"Code Example: {diagnosis['code_example']}")
    print(f"Confidence: {diagnosis['confidence']:.1%}")
```

**Error Types Supported:**
- Authentication errors
- Validation errors
- Connection issues
- Model access problems
- Domain syntax errors
- Performance issues

### 3. Smart Code Generation

Generate Python models from Odoo schemas automatically:

```python
# Generate typed Pydantic model
model_code = await client.ai.generate_model("res.partner")

# Generated code example:
"""
from typing import Optional, List, ClassVar
from datetime import date, datetime
from pydantic import BaseModel, Field

class ResPartner(BaseModel):
    '''Contact/Partner model for customers, suppliers, and companies.'''
    
    _name: ClassVar[str] = "res.partner"
    
    name: str = Field(..., description="Contact Name")
    email: Optional[str] = Field(None, description="Email Address")
    phone: Optional[str] = Field(None, description="Phone Number")
    is_company: bool = Field(False, description="Is a Company")
    customer_rank: int = Field(0, description="Customer Rank")
    supplier_rank: int = Field(0, description="Supplier Rank")
    
    # Relationships
    company_id: Optional[int] = Field(None, description="Related Company")
    child_ids: List[int] = Field(default_factory=list, description="Contacts")
"""

# Customize generation
model_code = await client.ai.generate_model(
    "res.partner",
    include_relationships=True,
    include_computed_fields=False
)
```

### 4. Performance Optimization

Get AI-powered performance analysis and suggestions:

```python
# Analyze query performance
query_stats = {
    "execution_time": 2.5,
    "record_count": 10000,
    "model": "res.partner",
    "domain": [("customer_rank", ">", 0)]
}

suggestions = await client.ai.suggest_optimization(query_stats)

for suggestion in suggestions:
    print(f"💡 {suggestion}")

# Example output:
# 💡 Add pagination with limit/offset for large result sets
# 💡 Consider caching this query with TTL=300 seconds
# 💡 Use specific field selection instead of reading all fields
# 💡 Add database index on customer_rank field for better performance
```

### 5. Interactive AI Chat

Get expert advice on Odoo development:

```python
# Ask development questions
response = await client.ai.chat(
    "How do I create a Many2one field in Odoo?",
    context="I'm working with res.partner model"
)

print(response)
# Provides detailed explanation with code examples
```

## ⚙️ Configuration

### AI Providers

Zenoo RPC supports multiple AI providers through LiteLLM:

```python
# Google Gemini (recommended)
await client.setup_ai(
    provider="gemini",
    model="gemini-2.5-flash-lite",
    api_key="your-gemini-key",
    temperature=0.1,
    max_tokens=4096
)

# OpenAI
await client.setup_ai(
    provider="openai",
    model="gpt-4",
    api_key="your-openai-key"
)

# Anthropic Claude
await client.setup_ai(
    provider="anthropic",
    model="claude-3-sonnet",
    api_key="your-anthropic-key"
)
```

### Advanced Configuration

```python
await client.setup_ai(
    provider="gemini",
    model="gemini-2.5-flash-lite",
    api_key="your-key",
    temperature=0.1,        # Lower = more deterministic
    max_tokens=4096,        # Maximum response length
    timeout=30.0,           # Request timeout
    max_retries=3           # Retry attempts
)
```

## 🎯 Use Cases

### 1. Rapid Prototyping

```python
# Quickly explore data without learning Odoo syntax
customers = await client.ai.query("Show me top 10 customers by revenue")
recent_orders = await client.ai.query("Orders placed in the last 7 days")
```

### 2. Error Troubleshooting

```python
# Get instant help with errors
try:
    await client.create("res.partner", {"email": "invalid-email"})
except Exception as e:
    solution = await client.ai.diagnose(e)
    # Provides specific fix for email validation
```

### 3. Code Generation

```python
# Generate models for new projects
for model_name in ["res.partner", "product.product", "sale.order"]:
    code = await client.ai.generate_model(model_name)
    with open(f"models/{model_name.replace('.', '_')}.py", "w") as f:
        f.write(code)
```

### 4. Performance Optimization

```python
# Optimize slow queries
stats = await client.analyze_query_performance(complex_query)
optimizations = await client.ai.suggest_optimization(stats)
```

## 🔧 Best Practices

### 1. Natural Language Queries

- **Be specific**: "Find companies in Vietnam" vs "Find partners"
- **Use clear conditions**: "revenue > 1M USD" vs "high revenue"
- **Specify time ranges**: "created this month" vs "recent"

### 2. Error Diagnosis

- **Provide context**: Include relevant operation details
- **Use immediately**: Diagnose errors right after they occur
- **Review suggestions**: AI provides multiple solution approaches

### 3. Model Generation

- **Review generated code**: Always review before using in production
- **Customize options**: Use include_relationships and include_computed_fields
- **Add validation**: Enhance generated models with custom validation

### 4. Performance Optimization

- **Regular analysis**: Monitor query performance regularly
- **Implement suggestions**: Prioritize high-impact optimizations
- **Test improvements**: Measure performance before and after changes

## 🚨 Limitations

### Current Limitations

1. **Model Coverage**: AI works best with standard Odoo models
2. **Complex Queries**: Very complex business logic may need manual refinement
3. **Custom Fields**: Custom fields may not be fully understood
4. **Language Support**: Currently optimized for English queries

### Future Enhancements

- Multi-language support
- Custom model training
- Advanced query optimization
- Integration with Odoo Studio

## 🔒 Security & Privacy

### Data Handling

- **No data storage**: AI providers don't store your Odoo data
- **Query analysis only**: Only query structure is analyzed, not actual data
- **Secure transmission**: All communications use HTTPS/TLS

### Best Practices

- **Use environment variables**: Store API keys securely
- **Limit permissions**: Use dedicated API keys with minimal permissions
- **Monitor usage**: Track AI API usage and costs
- **Review outputs**: Always review AI-generated code before deployment

## 📊 Monitoring & Analytics

### Usage Tracking

```python
# Check AI provider info
info = client.ai.provider_info
print(f"Provider: {info['provider']}")
print(f"Model: {info['model']}")

# Monitor AI usage in your application
ai_calls = 0
successful_queries = 0

async def track_ai_usage():
    global ai_calls, successful_queries
    ai_calls += 1
    
    try:
        result = await client.ai.query("your query")
        successful_queries += 1
        return result
    except Exception as e:
        logger.error(f"AI query failed: {e}")
        raise
```

## 🎓 Learning Resources

### Examples

- [AI Features Demo](../examples/ai_features_demo.py) - Comprehensive examples
- [Natural Language Queries](../examples/nl_queries.py) - Query examples
- [Error Diagnosis](../examples/error_diagnosis.py) - Error handling examples

### Documentation

- [API Reference](api-reference.md) - Complete API documentation
- [Architecture Guide](architecture/ai-integration-proposal.md) - Technical details
- [Best Practices](best-practices.md) - Development guidelines

## 🤝 Contributing

We welcome contributions to improve AI features:

1. **Report Issues**: Share problems or suggestions
2. **Improve Prompts**: Help optimize AI prompts
3. **Add Examples**: Contribute usage examples
4. **Enhance Documentation**: Improve guides and tutorials

See [Contributing Guide](../CONTRIBUTING.md) for details.
