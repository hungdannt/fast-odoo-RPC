# 🔒 Security Setup Guide

## 🚨 Important Security Notice

All hardcoded credentials have been removed from the codebase for security reasons. This document explains how to properly configure credentials for testing and development.

## 🔧 Environment Variables Setup

### Required Environment Variables

For testing with real Odoo servers, set the following environment variables:

```bash
export ODOO_HOST="https://your-odoo-server.com"
export ODOO_DATABASE="your_database_name"
export ODOO_USERNAME="your_username"
export ODOO_PASSWORD="your_password"
```

### Setting Environment Variables

#### Option 1: Command Line (Temporary)
```bash
# Set for current session
export ODOO_HOST="https://demo.odoo.com"
export ODOO_DATABASE="demo_db"
export ODOO_USERNAME="admin"
export ODOO_PASSWORD="admin"

# Run tests
python examples/simple_odoo_test.py
```

#### Option 2: .env File (Recommended)
Create a `.env` file in the project root:

```bash
# .env file (DO NOT COMMIT TO GIT)
ODOO_HOST=https://your-odoo-server.com
ODOO_DATABASE=your_database_name
ODOO_USERNAME=your_username
ODOO_PASSWORD=your_password
```

Then load it in your Python scripts:
```python
from dotenv import load_dotenv
load_dotenv()

import os
ODOO_CONFIG = {
    "host": os.getenv("ODOO_HOST"),
    "database": os.getenv("ODOO_DATABASE"),
    "username": os.getenv("ODOO_USERNAME"),
    "password": os.getenv("ODOO_PASSWORD")
}
```

#### Option 3: IDE/Editor Configuration
Most IDEs allow setting environment variables:

**VS Code:**
```json
// .vscode/launch.json
{
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "env": {
                "ODOO_HOST": "https://demo.odoo.com",
                "ODOO_DATABASE": "demo_db",
                "ODOO_USERNAME": "admin",
                "ODOO_PASSWORD": "admin"
            }
        }
    ]
}
```

**PyCharm:**
1. Go to Run → Edit Configurations
2. Add environment variables in the Environment Variables section

## 🧪 Testing Configuration

### Files That Require Environment Variables

The following files now use environment variables instead of hardcoded credentials:

1. **Test Files:**
   - `tests/test_real_odoo_integration.py`
   - `tests/test_simple_odoo_integration.py`
   - `tests/test_enhanced_integration.py`

2. **Example Files:**
   - `examples/simple_odoo_test.py`
   - `examples/real_odoo_test.py`
   - `examples/nested_query_test.py`

3. **Performance Tests:**
   - `tests/performance/benchmark_config.py`
   - `tests/performance/comprehensive_test_runner.py`

### Default Values

If environment variables are not set, the following defaults are used:
- **Host:** `https://demo.odoo.com`
- **Database:** `demo_database`
- **Username:** `demo_user`
- **Password:** `demo_password`

## 🔐 Security Best Practices

### 1. Never Commit Credentials
```bash
# Add to .gitignore (already included)
.env
.secrets
config.ini
secrets.json
```

### 2. Use Different Credentials for Different Environments
```bash
# Development
export ODOO_HOST="https://dev.odoo.com"

# Staging
export ODOO_HOST="https://staging.odoo.com"

# Production
export ODOO_HOST="https://prod.odoo.com"
```

### 3. Rotate Credentials Regularly
- Change passwords periodically
- Use strong, unique passwords
- Consider using API keys instead of passwords when available

### 4. Limit Access Permissions
- Use dedicated test users with minimal permissions
- Avoid using admin accounts for testing
- Create specific database users for different purposes

## 🚀 Quick Start for Testing

### 1. Set Up Test Environment
```bash
# Clone repository
git clone https://github.com/tuanle96/odooflow.git
cd odooflow

# Install dependencies
pip install -e ".[dev,test]"

# Set environment variables
export ODOO_HOST="https://demo.odoo.com"
export ODOO_DATABASE="demo_db"
export ODOO_USERNAME="admin"
export ODOO_PASSWORD="admin"
```

### 2. Run Tests
```bash
# Run simple test
python examples/simple_odoo_test.py

# Run comprehensive tests
python -m pytest tests/test_simple_odoo_integration.py -v

# Run performance tests
python tests/performance/comprehensive_test_runner.py
```

### 3. Verify Configuration
```python
import os
print("ODOO_HOST:", os.getenv("ODOO_HOST", "Not set"))
print("ODOO_DATABASE:", os.getenv("ODOO_DATABASE", "Not set"))
print("ODOO_USERNAME:", os.getenv("ODOO_USERNAME", "Not set"))
print("ODOO_PASSWORD:", "***" if os.getenv("ODOO_PASSWORD") else "Not set")
```

## 🛡️ Production Deployment

### 1. Use Secrets Management
For production deployments, use proper secrets management:

**Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: odoo-credentials
type: Opaque
data:
  host: <base64-encoded-host>
  database: <base64-encoded-database>
  username: <base64-encoded-username>
  password: <base64-encoded-password>
```

**Docker:**
```bash
docker run -e ODOO_HOST="$ODOO_HOST" \
           -e ODOO_DATABASE="$ODOO_DATABASE" \
           -e ODOO_USERNAME="$ODOO_USERNAME" \
           -e ODOO_PASSWORD="$ODOO_PASSWORD" \
           zenoo-rpc
```

**AWS/Azure/GCP:**
- Use AWS Secrets Manager
- Use Azure Key Vault
- Use Google Secret Manager

### 2. Environment-Specific Configuration
```python
import os

def get_odoo_config():
    """Get Odoo configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return {
            "host": os.getenv("ODOO_PROD_HOST"),
            "database": os.getenv("ODOO_PROD_DATABASE"),
            "username": os.getenv("ODOO_PROD_USERNAME"),
            "password": os.getenv("ODOO_PROD_PASSWORD")
        }
    elif env == "staging":
        return {
            "host": os.getenv("ODOO_STAGING_HOST"),
            "database": os.getenv("ODOO_STAGING_DATABASE"),
            "username": os.getenv("ODOO_STAGING_USERNAME"),
            "password": os.getenv("ODOO_STAGING_PASSWORD")
        }
    else:  # development
        return {
            "host": os.getenv("ODOO_HOST", "https://demo.odoo.com"),
            "database": os.getenv("ODOO_DATABASE", "demo_database"),
            "username": os.getenv("ODOO_USERNAME", "demo_user"),
            "password": os.getenv("ODOO_PASSWORD", "demo_password")
        }
```

## ⚠️ Troubleshooting

### Common Issues

1. **Environment Variables Not Set**
   ```
   Error: Cannot connect to Odoo: Authentication failed
   ```
   **Solution:** Verify environment variables are set correctly

2. **Wrong Credentials**
   ```
   Error: Access denied
   ```
   **Solution:** Check username/password and database name

3. **Network Issues**
   ```
   Error: Connection timeout
   ```
   **Solution:** Verify host URL and network connectivity

### Debug Commands
```bash
# Check environment variables
env | grep ODOO

# Test connection
curl -I $ODOO_HOST

# Verify Python can access variables
python -c "import os; print(os.getenv('ODOO_HOST'))"
```

## 📞 Support

If you encounter issues with credential setup:

1. Check this documentation first
2. Verify environment variables are set correctly
3. Test with demo credentials first
4. Check network connectivity to Odoo server
5. Review Odoo server logs if available

## 🔄 Migration from Hardcoded Credentials

If you're migrating from an older version with hardcoded credentials:

1. **Backup your current configuration**
2. **Set environment variables** as described above
3. **Test thoroughly** with your credentials
4. **Update CI/CD pipelines** to use environment variables
5. **Update documentation** for your team

---

**Remember:** Security is everyone's responsibility. Always follow your organization's security policies and best practices when handling credentials and sensitive information.
