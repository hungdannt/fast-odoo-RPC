# 💬 AI Chat Assistant Guide

Get expert Odoo development advice and interactive help with the AI Chat Assistant!

## 🎯 Overview

Zenoo RPC's AI Chat Assistant provides:
- **Expert Odoo development guidance** on demand
- **Interactive problem-solving** with context awareness
- **Code examples and best practices** for common tasks
- **Real-time assistance** during development

## 🚀 Basic Usage

### Simple Questions

```python
import asyncio
from zenoo_rpc import ZenooClient

async def basic_chat():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        await client.setup_ai(provider="gemini", api_key="your-key")
        
        # Ask basic questions
        response = await client.ai.chat("What is a domain filter in Odoo?")
        print(response)
        
        # Get code examples
        response = await client.ai.chat("How do I create a Many2one field?")
        print(response)
        
        # Ask about best practices
        response = await client.ai.chat("What are Odoo development best practices?")
        print(response)

asyncio.run(basic_chat())
```

### Contextual Questions

```python
async def contextual_chat():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        await client.setup_ai(provider="gemini", api_key="your-key")
        
        # Provide context for better answers
        response = await client.ai.chat(
            "How do I add a computed field?",
            context="Working with res.partner model for customer analytics"
        )
        print(response)
        
        # Follow-up questions maintain context
        response = await client.ai.chat(
            "What about making it searchable?",
            context="Previous question about computed fields in res.partner"
        )
        print(response)
```

## 🎨 Question Categories

### 1. Model Development

```python
async def model_questions():
    # Field types and definitions
    response = await client.ai.chat(
        "What's the difference between Char and Text fields?"
    )
    
    # Relationships
    response = await client.ai.chat(
        "How do I create a One2many relationship?",
        context="Creating invoice lines for account.move"
    )
    
    # Constraints and validation
    response = await client.ai.chat(
        "How do I add field validation in Odoo?"
    )
    
    # Computed fields
    response = await client.ai.chat(
        "How do I create a computed field that calculates total amount?"
    )
```

### 2. Domain Filters and Queries

```python
async def query_questions():
    # Domain syntax
    response = await client.ai.chat(
        "How do I write a domain filter for active customers?"
    )
    
    # Complex domains
    response = await client.ai.chat(
        "How do I filter records by date range in domain?"
    )
    
    # Search methods
    response = await client.ai.chat(
        "What's the difference between search() and search_read()?"
    )
```

### 3. API and RPC

```python
async def api_questions():
    # RPC methods
    response = await client.ai.chat(
        "How do I call a custom method via RPC?"
    )
    
    # Batch operations
    response = await client.ai.chat(
        "How do I create multiple records efficiently?"
    )
    
    # Error handling
    response = await client.ai.chat(
        "How should I handle RPC errors in production?"
    )
```

### 4. Performance and Optimization

```python
async def performance_questions():
    # Query optimization
    response = await client.ai.chat(
        "How do I optimize slow search queries?"
    )
    
    # Caching strategies
    response = await client.ai.chat(
        "What are best practices for caching in Odoo?"
    )
    
    # Bulk operations
    response = await client.ai.chat(
        "How do I efficiently process large datasets?"
    )
```

## 🔧 Advanced Chat Features

### Interactive Problem Solving

```python
async def interactive_problem_solving():
    """Multi-turn conversation for complex problems."""
    
    # Start with a complex problem
    response = await client.ai.chat(
        "I need to create a custom workflow for purchase approvals"
    )
    print("AI:", response)
    
    # Follow up with specifics
    response = await client.ai.chat(
        "The workflow should have 3 approval levels based on amount",
        context="Purchase approval workflow discussion"
    )
    print("AI:", response)
    
    # Ask for implementation details
    response = await client.ai.chat(
        "Show me the code for the approval state machine",
        context="3-level purchase approval workflow"
    )
    print("AI:", response)
    
    # Get testing advice
    response = await client.ai.chat(
        "How do I test this workflow?",
        context="Purchase approval workflow with 3 levels"
    )
    print("AI:", response)
```

### Code Review and Suggestions

```python
async def code_review():
    """Get AI feedback on your code."""
    
    code_snippet = '''
    def create_invoice(self, partner_id, amount):
        invoice = self.env['account.move'].create({
            'partner_id': partner_id,
            'amount_total': amount,
            'state': 'draft'
        })
        return invoice.id
    '''
    
    response = await client.ai.chat(
        f"Please review this code and suggest improvements:\n\n{code_snippet}",
        context="Creating invoices in Odoo"
    )
    print("Code Review:", response)
```

### Architecture Guidance

```python
async def architecture_guidance():
    """Get advice on system architecture."""
    
    response = await client.ai.chat(
        "I'm building an e-commerce integration. What's the best architecture?",
        context="Odoo integration with external e-commerce platform"
    )
    print("Architecture Advice:", response)
    
    # Follow up with specific concerns
    response = await client.ai.chat(
        "How do I handle product synchronization conflicts?",
        context="E-commerce integration architecture discussion"
    )
    print("Sync Strategy:", response)
```

## 📚 Common Use Cases

### 1. Learning Odoo Development

```python
async def learning_session():
    """Structured learning conversation."""
    
    topics = [
        "What are the core concepts in Odoo development?",
        "How does the ORM work in Odoo?",
        "What are views and how do they work?",
        "How do I create custom modules?",
        "What are the security concepts I need to know?"
    ]
    
    for topic in topics:
        print(f"\n📚 Topic: {topic}")
        response = await client.ai.chat(topic)
        print(f"Answer: {response[:200]}...")
        
        # Ask for examples
        example_response = await client.ai.chat(
            "Can you show me a code example?",
            context=f"Learning about: {topic}"
        )
        print(f"Example: {example_response[:200]}...")
```

### 2. Debugging Help

```python
async def debugging_help():
    """Get help with debugging issues."""
    
    # Describe the problem
    problem = """
    I'm getting a 'field does not exist' error when trying to search partners.
    The field name is 'customer_type' but it's not found.
    """
    
    response = await client.ai.chat(
        f"Help me debug this issue: {problem}",
        context="Debugging field error in res.partner search"
    )
    print("Debug Help:", response)
    
    # Ask for troubleshooting steps
    response = await client.ai.chat(
        "What are the step-by-step troubleshooting steps?",
        context="Field does not exist error in partner search"
    )
    print("Troubleshooting:", response)
```

### 3. Migration Assistance

```python
async def migration_help():
    """Get help with Odoo migrations."""
    
    response = await client.ai.chat(
        "I'm migrating from Odoo 14 to 16. What are the key changes?",
        context="Odoo version migration planning"
    )
    print("Migration Guide:", response)
    
    # Specific migration concerns
    response = await client.ai.chat(
        "How do I handle deprecated API methods?",
        context="Odoo 14 to 16 migration"
    )
    print("API Changes:", response)
```

### 4. Performance Optimization

```python
async def performance_help():
    """Get performance optimization advice."""
    
    response = await client.ai.chat(
        "My partner search is very slow with 100k+ records. How to optimize?",
        context="Performance optimization for large partner database"
    )
    print("Performance Tips:", response)
    
    # Specific optimization techniques
    response = await client.ai.chat(
        "Should I use database indexes or change the search approach?",
        context="Optimizing slow partner search with 100k+ records"
    )
    print("Optimization Strategy:", response)
```

## 🎯 Chat Best Practices

### 1. Provide Clear Context

```python
# ✅ Good - Clear context
response = await client.ai.chat(
    "How do I validate email format?",
    context="Adding email validation to res.partner model in custom module"
)

# ❌ Poor - No context
response = await client.ai.chat("How do I validate email?")
```

### 2. Ask Specific Questions

```python
# ✅ Specific
response = await client.ai.chat(
    "How do I create a computed field that calculates partner's total invoice amount?"
)

# ❌ Too general
response = await client.ai.chat("How do I use computed fields?")
```

### 3. Build on Previous Questions

```python
async def conversation_flow():
    # Start with general question
    response1 = await client.ai.chat(
        "How do I create a wizard in Odoo?"
    )
    
    # Build on the answer
    response2 = await client.ai.chat(
        "How do I pass data from the wizard to a report?",
        context="Creating wizard for report generation"
    )
    
    # Get specific implementation details
    response3 = await client.ai.chat(
        "Show me the complete wizard code with report integration",
        context="Wizard that passes data to report"
    )
```

### 4. Ask for Examples

```python
async def get_examples():
    # Always ask for practical examples
    response = await client.ai.chat(
        "How do I create a scheduled action? Please include a complete example."
    )
    
    # Ask for variations
    response = await client.ai.chat(
        "Show me different ways to handle errors in scheduled actions",
        context="Creating robust scheduled actions"
    )
```

## 🛠️ Integration with Development Workflow

### 1. IDE Integration

```python
class OdooAIHelper:
    """Helper class for IDE integration."""
    
    def __init__(self, client):
        self.client = client
    
    async def quick_help(self, question: str, current_file: str = None):
        """Get quick help with current context."""
        context = f"Working in file: {current_file}" if current_file else None
        return await self.client.ai.chat(question, context=context)
    
    async def explain_code(self, code: str):
        """Explain code snippet."""
        return await self.client.ai.chat(
            f"Explain this Odoo code:\n\n{code}",
            context="Code explanation request"
        )
    
    async def suggest_improvements(self, code: str):
        """Get improvement suggestions."""
        return await self.client.ai.chat(
            f"How can I improve this code?\n\n{code}",
            context="Code improvement suggestions"
        )

# Usage
helper = OdooAIHelper(client)
help_text = await helper.quick_help("How do I add field validation?", "models/partner.py")
```

### 2. Documentation Generation

```python
async def generate_documentation():
    """Generate documentation with AI help."""
    
    response = await client.ai.chat(
        "Help me write documentation for a custom module that manages equipment rentals",
        context="Documentation writing for equipment rental module"
    )
    
    # Get specific sections
    api_docs = await client.ai.chat(
        "Write API documentation for the rental booking methods",
        context="Equipment rental module documentation"
    )
    
    user_guide = await client.ai.chat(
        "Write user guide for the rental management interface",
        context="Equipment rental module documentation"
    )
```

### 3. Testing Guidance

```python
async def testing_help():
    """Get help with testing strategies."""
    
    response = await client.ai.chat(
        "How do I write unit tests for Odoo models?",
        context="Testing custom rental management module"
    )
    
    integration_tests = await client.ai.chat(
        "What about integration tests for RPC calls?",
        context="Testing Odoo module with external integrations"
    )
```

## 🚨 Troubleshooting Chat Issues

### Chat Not Responding

```python
async def troubleshoot_chat():
    try:
        response = await client.ai.chat("Test question")
        print("Chat working:", response)
    except Exception as e:
        print(f"Chat error: {e}")
        
        # Check AI initialization
        if not client.ai.is_initialized:
            print("AI not initialized - call setup_ai() first")
        
        # Check API key
        provider_info = client.ai.provider_info
        print(f"Provider: {provider_info}")
```

### Improving Response Quality

```python
async def improve_responses():
    # Provide more context for better responses
    detailed_context = {
        "project": "E-commerce integration",
        "odoo_version": "16.0",
        "modules": ["sale", "stock", "account"],
        "current_task": "Implementing product sync",
        "experience_level": "intermediate"
    }
    
    response = await client.ai.chat(
        "How do I handle product variants in sync?",
        context=str(detailed_context)
    )
```

## 🎯 Next Steps

- **[Performance Optimization](./performance-optimization.md)** - Optimize based on AI suggestions
- **[Advanced AI Features](./advanced-ai-features.md)** - Explore advanced capabilities
- **[AI Configuration](./ai-configuration.md)** - Fine-tune chat behavior
- **[Error Diagnosis](./error-diagnosis.md)** - Combine chat with error analysis

---

**💡 Pro Tip**: The AI Chat Assistant learns from context! Provide details about your project, experience level, and specific goals for the most helpful responses.
