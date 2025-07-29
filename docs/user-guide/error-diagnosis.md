# 🔍 AI Error Diagnosis Guide

Get instant, intelligent help when things go wrong with AI-powered error analysis!

## 🎯 Overview

Zenoo RPC's AI Error Diagnosis provides:
- **Instant error analysis** with root cause identification
- **Step-by-step solutions** with code examples
- **Prevention strategies** to avoid future issues
- **Contextual help** based on your specific situation

## 🚀 Basic Usage

### Simple Error Diagnosis

```python
import asyncio
from zenoo_rpc import ZenooClient

async def basic_error_diagnosis():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        await client.setup_ai(provider="gemini", api_key="your-key")
        
        try:
            # This will cause an error
            result = await client.search("res.partner", [("invalid_field", "=", "value")])
            
        except Exception as error:
            # Get AI diagnosis
            diagnosis = await client.ai.diagnose(error)
            
            print(f"🔍 Problem: {diagnosis['problem']}")
            print(f"🎯 Root Cause: {diagnosis['root_cause']}")
            print(f"✅ Solution: {diagnosis['solution']}")
            print(f"📝 Code Example: {diagnosis['code_example']}")
            print(f"🛡️ Prevention: {diagnosis['prevention']}")
            print(f"📊 Confidence: {diagnosis['confidence']}")
            print(f"⚠️ Severity: {diagnosis['severity']}")

asyncio.run(basic_error_diagnosis())
```

### Error Diagnosis with Context

```python
async def contextual_diagnosis():
    async with ZenooClient("http://localhost:8069") as client:
        await client.login("demo", "admin", "admin")
        await client.setup_ai(provider="gemini", api_key="your-key")
        
        try:
            # Complex operation that might fail
            partners = await client.search_read(
                "res.partner",
                [("customer_rank", ">", 0)],
                ["name", "email", "nonexistent_field"]
            )
            
        except Exception as error:
            # Provide context for better diagnosis
            context = {
                "operation": "search_read",
                "model": "res.partner",
                "domain": [("customer_rank", ">", 0)],
                "fields": ["name", "email", "nonexistent_field"],
                "user_intent": "Getting customer data for export"
            }
            
            diagnosis = await client.ai.diagnose(error, context)
            
            print("🔍 Detailed Diagnosis:")
            print(f"Problem: {diagnosis['problem']}")
            print(f"Solution: {diagnosis['solution']}")
```

## 🎨 Error Categories

### 1. Authentication Errors

```python
async def auth_error_example():
    try:
        await client.login("demo", "wrong_user", "wrong_password")
    except Exception as error:
        diagnosis = await client.ai.diagnose(error, {
            "operation": "login",
            "database": "demo"
        })
        
        # AI provides specific authentication troubleshooting
        print(diagnosis['solution'])
        # Example: "Check username/password, verify database exists..."
```

### 2. Model and Field Errors

```python
async def model_field_errors():
    try:
        # Wrong model name
        await client.search("res.invalid_model", [])
    except Exception as error:
        diagnosis = await client.ai.diagnose(error)
        print(f"Model Error: {diagnosis['solution']}")
    
    try:
        # Wrong field name
        await client.search("res.partner", [("invalid_field", "=", "test")])
    except Exception as error:
        diagnosis = await client.ai.diagnose(error, {"model": "res.partner"})
        print(f"Field Error: {diagnosis['solution']}")
```

### 3. Permission Errors

```python
async def permission_errors():
    try:
        # Insufficient permissions
        await client.unlink("res.partner", [1])
    except Exception as error:
        diagnosis = await client.ai.diagnose(error, {
            "operation": "delete",
            "model": "res.partner",
            "user_groups": ["base.group_user"]
        })
        
        print(f"Permission Issue: {diagnosis['solution']}")
        # AI suggests checking user groups, record rules, etc.
```

### 4. Data Validation Errors

```python
async def validation_errors():
    try:
        # Invalid data
        await client.create("res.partner", {
            "name": "",  # Required field empty
            "email": "invalid-email"  # Invalid format
        })
    except Exception as error:
        diagnosis = await client.ai.diagnose(error, {
            "operation": "create",
            "model": "res.partner",
            "data": {"name": "", "email": "invalid-email"}
        })
        
        print(f"Validation Error: {diagnosis['solution']}")
```

## 🔧 Advanced Diagnosis Features

### Batch Error Analysis

```python
async def batch_error_analysis():
    errors = []
    
    # Collect multiple errors
    operations = [
        ("res.partner", [("invalid1", "=", "test")]),
        ("res.invalid", []),
        ("res.partner", [("name", "=", None)])
    ]
    
    for model, domain in operations:
        try:
            await client.search(model, domain)
        except Exception as error:
            errors.append((error, {"model": model, "domain": domain}))
    
    # Analyze all errors
    for error, context in errors:
        diagnosis = await client.ai.diagnose(error, context)
        print(f"Error: {diagnosis['problem']}")
        print(f"Fix: {diagnosis['solution']}")
        print("-" * 50)
```

### Error Pattern Recognition

```python
async def pattern_recognition():
    # AI can identify patterns in recurring errors
    error_history = []
    
    for i in range(5):
        try:
            await client.search("res.partner", [("field_" + str(i), "=", "test")])
        except Exception as error:
            error_history.append(error)
    
    # Analyze pattern
    if len(error_history) > 2:
        diagnosis = await client.ai.diagnose(
            error_history[-1],
            {
                "pattern": "Multiple similar field errors",
                "frequency": len(error_history),
                "context": "Iterating through dynamic field names"
            }
        )
        
        print(f"Pattern Detected: {diagnosis['problem']}")
        print(f"Systematic Solution: {diagnosis['solution']}")
```

## 📊 Diagnosis Output Structure

### Complete Diagnosis Response

```python
diagnosis = await client.ai.diagnose(error, context)

# Available fields:
print(f"Problem: {diagnosis['problem']}")           # Clear problem description
print(f"Root Cause: {diagnosis['root_cause']}")     # Why it happened
print(f"Solution: {diagnosis['solution']}")         # How to fix it
print(f"Code Example: {diagnosis['code_example']}")  # Working code
print(f"Prevention: {diagnosis['prevention']}")     # Avoid future issues
print(f"Confidence: {diagnosis['confidence']}")     # AI confidence (0-1)
print(f"Severity: {diagnosis['severity']}")         # low/medium/high/critical
```

### Severity Levels

- **Low**: Minor issues, warnings, or cosmetic problems
- **Medium**: Functional issues that don't break core operations
- **High**: Significant problems affecting main functionality
- **Critical**: System-breaking errors requiring immediate attention

## 🎯 Real-World Examples

### E-commerce Integration Error

```python
async def ecommerce_error():
    try:
        # Syncing products from e-commerce platform
        product_data = {
            "name": "Laptop",
            "list_price": "invalid_price",  # Should be float
            "categ_id": 999,  # Non-existent category
            "default_code": None  # Missing SKU
        }
        
        await client.create("product.product", product_data)
        
    except Exception as error:
        diagnosis = await client.ai.diagnose(error, {
            "operation": "product_sync",
            "source": "ecommerce_platform",
            "data_type": "product_import",
            "batch_size": 100
        })
        
        print("E-commerce Sync Error Analysis:")
        print(f"Issue: {diagnosis['problem']}")
        print(f"Fix: {diagnosis['solution']}")
        print(f"Prevention: {diagnosis['prevention']}")
```

### API Integration Error

```python
async def api_integration_error():
    try:
        # External API integration
        customer_data = await external_api.get_customer(123)
        
        # Map to Odoo format
        partner_data = {
            "name": customer_data["full_name"],
            "email": customer_data["email_address"],
            "phone": customer_data["phone_number"],
            "country_id": customer_data["country_code"]  # Wrong format
        }
        
        await client.create("res.partner", partner_data)
        
    except Exception as error:
        diagnosis = await client.ai.diagnose(error, {
            "operation": "api_integration",
            "external_system": "CRM_API",
            "data_mapping": "customer_to_partner",
            "field_causing_issue": "country_id"
        })
        
        print("API Integration Error:")
        print(diagnosis['solution'])
```

### Migration Error

```python
async def migration_error():
    try:
        # Data migration from old system
        legacy_records = [
            {"name": "Customer 1", "old_id": "CUST001"},
            {"name": "Customer 2", "old_id": "CUST002"}
        ]
        
        for record in legacy_records:
            await client.create("res.partner", record)
            
    except Exception as error:
        diagnosis = await client.ai.diagnose(error, {
            "operation": "data_migration",
            "source_system": "legacy_crm",
            "migration_phase": "customer_import",
            "record_count": len(legacy_records)
        })
        
        print("Migration Error Analysis:")
        print(diagnosis['solution'])
```

## 🛠️ Best Practices

### 1. Provide Rich Context

```python
# ✅ Good - Rich context
context = {
    "operation": "bulk_import",
    "model": "product.product",
    "data_source": "CSV file",
    "record_number": 150,
    "user_role": "inventory_manager",
    "business_process": "monthly_inventory_update"
}

diagnosis = await client.ai.diagnose(error, context)
```

### 2. Handle Diagnosis Gracefully

```python
async def robust_error_handling():
    try:
        result = await client.some_operation()
    except Exception as error:
        try:
            diagnosis = await client.ai.diagnose(error)
            
            # Log structured error info
            logger.error(f"Operation failed: {diagnosis['problem']}")
            logger.info(f"Suggested fix: {diagnosis['solution']}")
            
            # Show user-friendly message
            if diagnosis['severity'] == 'critical':
                print("❌ Critical error - please contact support")
            else:
                print(f"💡 Suggestion: {diagnosis['solution']}")
                
        except Exception as diag_error:
            # Fallback if AI diagnosis fails
            logger.error(f"Original error: {error}")
            logger.error(f"Diagnosis failed: {diag_error}")
            print("❌ An error occurred. Please check logs.")
```

### 3. Learn from Patterns

```python
class ErrorTracker:
    def __init__(self):
        self.error_patterns = {}
    
    async def track_and_diagnose(self, error, context):
        # Get AI diagnosis
        diagnosis = await client.ai.diagnose(error, context)
        
        # Track patterns
        error_type = diagnosis.get('problem', 'unknown')
        if error_type in self.error_patterns:
            self.error_patterns[error_type] += 1
        else:
            self.error_patterns[error_type] = 1
        
        # Alert on recurring issues
        if self.error_patterns[error_type] > 5:
            print(f"⚠️ Recurring issue detected: {error_type}")
            print(f"Consider: {diagnosis['prevention']}")
        
        return diagnosis
```

## 🚨 Troubleshooting AI Diagnosis

### When AI Diagnosis Fails

```python
async def fallback_diagnosis():
    try:
        result = await client.some_operation()
    except Exception as error:
        try:
            diagnosis = await client.ai.diagnose(error)
            print(diagnosis['solution'])
        except Exception as ai_error:
            # Manual error analysis
            print(f"Error type: {type(error).__name__}")
            print(f"Error message: {str(error)}")
            
            # Basic categorization
            if "authentication" in str(error).lower():
                print("💡 Likely authentication issue - check credentials")
            elif "field" in str(error).lower():
                print("💡 Likely field issue - check field names")
            elif "model" in str(error).lower():
                print("💡 Likely model issue - check model name")
```

### Improving Diagnosis Quality

```python
# Provide more context for better diagnosis
detailed_context = {
    "operation": "create",
    "model": "res.partner",
    "user_id": 1,
    "company_id": 1,
    "database": "production",
    "odoo_version": "16.0",
    "custom_modules": ["custom_crm", "custom_sales"],
    "recent_changes": "Updated partner fields yesterday",
    "environment": "production"
}

diagnosis = await client.ai.diagnose(error, detailed_context)
```

## 🎯 Next Steps

- **[Performance Optimization](./performance-optimization.md)** - Optimize based on error patterns
- **[AI Chat Assistant](./ai-chat-assistant.md)** - Get interactive help
- **[Advanced AI Features](./advanced-ai-features.md)** - Explore advanced capabilities
- **[AI Configuration](./ai-configuration.md)** - Fine-tune AI behavior

---

**💡 Pro Tip**: The more context you provide, the better the AI diagnosis. Include operation details, business context, and environment information for the most accurate help!
