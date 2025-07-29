"""
Zenoo RPC AI Features Demo

This example demonstrates the AI-powered capabilities of Zenoo RPC including:
- Natural language to Odoo query conversion
- Intelligent error diagnosis and solutions
- Smart code generation from Odoo models
- Performance optimization suggestions
- Interactive AI chat for Odoo development

Requirements:
    pip install zenoo-rpc[ai]

Setup:
    1. Set your Gemini API key: export GEMINI_API_KEY="your-api-key"
    2. Update the Odoo connection details below
    3. Run: python examples/ai_features_demo.py
"""

import asyncio
import os
import logging
from typing import Any, Dict

from zenoo_rpc import ZenooClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ODOO_URL = "http://localhost:8069"
DATABASE = "demo"
USERNAME = "admin"
PASSWORD = "admin"

# Get API key from environment (REQUIRED)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


async def demo_natural_language_queries():
    """Demonstrate natural language query capabilities."""
    print("\n🤖 Natural Language Query Demo")
    print("=" * 50)
    
    async with ZenooClient(ODOO_URL) as client:
        # Login to Odoo
        await client.login(DATABASE, USERNAME, PASSWORD)
        
        # Setup AI capabilities
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key=GEMINI_API_KEY
        )
        
        # Example queries
        queries = [
            "Find all companies",
            "Show active users created this month",
            "Get products with price greater than 100",
            "Find customers in Vietnam",
            "Show invoices from last week"
        ]
        
        for query in queries:
            print(f"\n📝 Query: '{query}'")
            
            try:
                # First, explain how the query will be converted
                explanation = await client.ai.explain_query(query)
                print(f"   Model: {explanation['model']}")
                print(f"   Domain: {explanation['domain']}")
                print(f"   Explanation: {explanation['explanation']}")
                
                # Execute the query
                results = await client.ai.query(query, limit=5)
                print(f"   Results: Found {len(results)} records")
                
                if results:
                    # Show first result
                    first_result = results[0]
                    print(f"   Sample: {first_result.get('name', 'N/A')}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")


async def demo_error_diagnosis():
    """Demonstrate AI-powered error diagnosis."""
    print("\n🔍 Error Diagnosis Demo")
    print("=" * 50)
    
    async with ZenooClient(ODOO_URL) as client:
        await client.login(DATABASE, USERNAME, PASSWORD)
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key=GEMINI_API_KEY
        )
        
        # Simulate common errors
        error_scenarios = [
            {
                "description": "Invalid model name",
                "action": lambda: client.search("invalid.model", [])
            },
            {
                "description": "Invalid domain syntax",
                "action": lambda: client.search("res.partner", [("invalid_field", "=", "test")])
            },
            {
                "description": "Missing required field",
                "action": lambda: client.create("res.partner", {})
            }
        ]
        
        for scenario in error_scenarios:
            print(f"\n🧪 Testing: {scenario['description']}")
            
            try:
                await scenario["action"]()
                print("   ✅ No error occurred")
                
            except Exception as error:
                print(f"   ❌ Error: {type(error).__name__}: {error}")
                
                # Get AI diagnosis
                try:
                    diagnosis = await client.ai.diagnose(error)
                    
                    print(f"   🤖 AI Diagnosis:")
                    print(f"      Problem: {diagnosis['problem']}")
                    print(f"      Root Cause: {diagnosis['root_cause']}")
                    print(f"      Solution: {diagnosis['solution']}")
                    print(f"      Confidence: {diagnosis['confidence']:.1%}")
                    
                    if 'code_example' in diagnosis:
                        print(f"      Example: {diagnosis['code_example']}")
                    
                except Exception as diag_error:
                    print(f"   ❌ Diagnosis failed: {diag_error}")


async def demo_model_generation():
    """Demonstrate AI-powered model generation."""
    print("\n🏗️ Model Generation Demo")
    print("=" * 50)
    
    async with ZenooClient(ODOO_URL) as client:
        await client.login(DATABASE, USERNAME, PASSWORD)
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key=GEMINI_API_KEY
        )
        
        # Generate models for common Odoo models
        models_to_generate = [
            "res.partner",
            "res.users",
            "product.product"
        ]
        
        for model_name in models_to_generate:
            print(f"\n📋 Generating model for: {model_name}")
            
            try:
                model_code = await client.ai.generate_model(
                    model_name,
                    include_relationships=True,
                    include_computed_fields=False
                )
                
                print("   ✅ Generated successfully!")
                print("   📄 Code preview:")
                
                # Show first few lines of generated code
                lines = model_code.split('\n')
                for i, line in enumerate(lines[:15]):  # Show first 15 lines
                    print(f"      {line}")
                
                if len(lines) > 15:
                    print(f"      ... ({len(lines) - 15} more lines)")
                
            except Exception as e:
                print(f"   ❌ Generation failed: {e}")


async def demo_performance_optimization():
    """Demonstrate AI-powered performance optimization."""
    print("\n⚡ Performance Optimization Demo")
    print("=" * 50)
    
    async with ZenooClient(ODOO_URL) as client:
        await client.login(DATABASE, USERNAME, PASSWORD)
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key=GEMINI_API_KEY
        )
        
        # Simulate performance scenarios
        performance_scenarios = [
            {
                "description": "Slow query with many records",
                "stats": {
                    "execution_time": 3.5,
                    "record_count": 50000,
                    "model": "res.partner",
                    "domain": [("customer_rank", ">", 0)],
                    "fields": ["name", "email", "phone", "street", "city"]
                }
            },
            {
                "description": "Memory-intensive operation",
                "stats": {
                    "execution_time": 1.2,
                    "record_count": 100000,
                    "model": "account.move.line",
                    "memory_usage": "500MB",
                    "operation": "search_read"
                }
            }
        ]
        
        for scenario in performance_scenarios:
            print(f"\n🔍 Analyzing: {scenario['description']}")
            
            try:
                suggestions = await client.ai.suggest_optimization(scenario["stats"])
                
                print(f"   📊 Performance Analysis:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"      {i}. {suggestion}")
                
            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")


async def demo_ai_chat():
    """Demonstrate AI chat functionality."""
    print("\n💬 AI Chat Demo")
    print("=" * 50)
    
    async with ZenooClient(ODOO_URL) as client:
        await client.login(DATABASE, USERNAME, PASSWORD)
        await client.setup_ai(
            provider="gemini",
            model="gemini-2.5-flash-lite",
            api_key=GEMINI_API_KEY
        )
        
        # Example questions
        questions = [
            "How do I create a Many2one field in Odoo?",
            "What's the best way to handle large datasets in Odoo?",
            "How can I optimize domain filters for better performance?",
            "What are the common pitfalls when working with Odoo ORM?",
            "How do I implement custom validation in Odoo models?"
        ]
        
        for question in questions:
            print(f"\n❓ Question: {question}")
            
            try:
                response = await client.ai.chat(question)
                print(f"   🤖 AI Response:")
                
                # Format response for better readability
                lines = response.split('\n')
                for line in lines:
                    if line.strip():
                        print(f"      {line}")
                
            except Exception as e:
                print(f"   ❌ Chat failed: {e}")


async def main():
    """Run all AI feature demos."""
    print("🚀 Zenoo RPC AI Features Demo")
    print("=" * 60)
    
    try:
        # Check if AI features are available
        from zenoo_rpc.ai import AI_AVAILABLE
        
        if not AI_AVAILABLE:
            print("❌ AI features are not available.")
            print("   Install with: pip install zenoo-rpc[ai]")
            return
        
        if not GEMINI_API_KEY:
            print("❌ Gemini API key not found.")
            print("   Set environment variable: export GEMINI_API_KEY='your-key'")
            return
        
        # Run demos
        await demo_natural_language_queries()
        await demo_error_diagnosis()
        await demo_model_generation()
        await demo_performance_optimization()
        await demo_ai_chat()
        
        print("\n✅ All demos completed successfully!")
        print("\n🎯 Next Steps:")
        print("   1. Try your own natural language queries")
        print("   2. Experiment with different AI models")
        print("   3. Integrate AI features into your applications")
        print("   4. Explore advanced AI capabilities")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("\nTroubleshooting:")
        print("   1. Check your Odoo connection settings")
        print("   2. Verify your Gemini API key")
        print("   3. Ensure AI dependencies are installed")


if __name__ == "__main__":
    asyncio.run(main())
