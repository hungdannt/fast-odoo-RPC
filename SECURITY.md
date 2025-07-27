# Security Policy

## Supported Versions

We actively support the following versions of Zenoo RPC with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in Zenoo RPC, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

**Security Contact**: [justin.le.1105@gmail.com](mailto:justin.le.1105@gmail.com)

### What to Include

When reporting a vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Impact**: The potential impact and severity
3. **Reproduction**: Step-by-step instructions to reproduce the issue
4. **Environment**: Version of Zenoo RPC, Python version, OS, etc.
5. **Proof of Concept**: If applicable, include a minimal proof of concept
6. **Suggested Fix**: If you have ideas for how to fix the issue

### Example Report

```
Subject: [SECURITY] SQL Injection vulnerability in query builder

Description:
The query builder does not properly sanitize user input when building
Odoo domain filters, potentially allowing SQL injection attacks.

Impact:
An attacker could potentially execute arbitrary SQL queries on the
Odoo database, leading to data theft or corruption.

Reproduction:
1. Create a query with user-controlled input
2. Include SQL injection payload in the filter value
3. Execute the query

Environment:
- Zenoo RPC version: 1.2.0
- Python version: 3.11.0
- Odoo version: 16.0
- OS: Ubuntu 22.04

Proof of Concept:
[Include minimal code example]

Suggested Fix:
Implement proper input validation and parameterized queries.
```

## Response Timeline

We aim to respond to security reports according to the following timeline:

- **Initial Response**: Within 24 hours
- **Confirmation**: Within 72 hours
- **Fix Development**: Within 2 weeks for critical issues
- **Release**: As soon as possible after fix is ready
- **Public Disclosure**: 90 days after fix is released

## Security Best Practices

When using Zenoo RPC in production, please follow these security best practices:

### Authentication & Authorization

- Use strong, unique passwords for Odoo accounts
- Implement proper access controls and user permissions
- Regularly rotate API credentials
- Use environment variables for sensitive configuration

```python
# ✅ Good: Use environment variables
import os

client = ZenooClient(
    host=os.getenv("ODOO_HOST"),
    port=int(os.getenv("ODOO_PORT", "8069"))
)

await client.login(
    database=os.getenv("ODOO_DATABASE"),
    username=os.getenv("ODOO_USERNAME"),
    password=os.getenv("ODOO_PASSWORD")
)

# ❌ Bad: Hardcoded credentials
client = ZenooClient("production-server.com")
await client.login("production_db", "admin", "password123")
```

### Network Security

- Always use HTTPS in production
- Validate SSL certificates
- Use proper firewall rules
- Consider VPN for database access

```python
# ✅ Good: Secure HTTPS connection
client = ZenooClient(
    "https://odoo.company.com",
    port=443,
    verify_ssl=True
)

# ❌ Bad: Insecure HTTP or disabled SSL verification
client = ZenooClient(
    "http://odoo.company.com",  # HTTP instead of HTTPS
    verify_ssl=False  # Disabled SSL verification
)
```

### Input Validation

- Validate all user inputs
- Use parameterized queries
- Sanitize data before processing
- Implement rate limiting

```python
# ✅ Good: Input validation
def validate_partner_data(data):
    if not isinstance(data.get("name"), str):
        raise ValueError("Name must be a string")
    
    if len(data["name"]) > 100:
        raise ValueError("Name too long")
    
    if "email" in data and not is_valid_email(data["email"]):
        raise ValueError("Invalid email format")

# ❌ Bad: No validation
await client.create("res.partner", user_input)  # Direct user input
```

### Error Handling

- Don't expose sensitive information in error messages
- Log security events appropriately
- Implement proper exception handling

```python
# ✅ Good: Safe error handling
try:
    result = await client.search("res.partner", domain)
except AuthenticationError:
    logger.warning("Authentication failed for user %s", username)
    raise ValueError("Invalid credentials")  # Generic message
except Exception as e:
    logger.error("Unexpected error: %s", str(e))
    raise ValueError("Operation failed")  # Don't expose details

# ❌ Bad: Exposing sensitive information
try:
    result = await client.search("res.partner", domain)
except Exception as e:
    raise e  # Exposes internal details
```

### Dependency Management

- Keep dependencies up to date
- Regularly audit for vulnerabilities
- Use dependency scanning tools
- Pin dependency versions

```bash
# Check for vulnerabilities
pip audit

# Update dependencies
pip install --upgrade zenoo-rpc

# Use requirements.txt with pinned versions
zenoo-rpc==1.2.0
httpx==0.24.1
pydantic==2.0.0
```

## Security Features

Zenoo RPC includes several built-in security features:

### Connection Security

- HTTPS/TLS support with certificate validation
- Connection timeout and retry mechanisms
- Secure session management

### Input Validation

- Pydantic model validation
- Type checking and sanitization
- Domain filter validation

### Error Handling

- Custom exception hierarchy
- Secure error messages
- Comprehensive logging

### Rate Limiting

- Built-in rate limiting capabilities
- Configurable thresholds
- Circuit breaker patterns

## Vulnerability Disclosure

When we receive a security report, we follow this process:

1. **Acknowledge** the report within 24 hours
2. **Investigate** and confirm the vulnerability
3. **Develop** a fix in a private repository
4. **Test** the fix thoroughly
5. **Release** a security update
6. **Notify** users about the update
7. **Publish** details after users have had time to update

## Security Updates

Security updates are released as patch versions (e.g., 1.2.1) and include:

- Fix for the vulnerability
- Updated dependencies if needed
- Security advisory with details
- Migration guide if breaking changes are required

## Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities:

<!-- Security researchers will be listed here -->

*No vulnerabilities have been reported yet.*

## Contact

For security-related questions or concerns:

- **Security Email**: [justin.le.1105@gmail.com](mailto:justin.le.1105@gmail.com)
- **General Issues**: [GitHub Issues](https://github.com/tuanle96/zenoo-rpc/issues)
- **Documentation**: [Security Guide](docs/advanced/security.md)

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Guidelines](https://python.org/dev/security/)
- [Odoo Security Documentation](https://www.odoo.com/documentation/16.0/administration/security.html)
- [CVE Database](https://cve.mitre.org/)

---

**Note**: This security policy is subject to change. Please check back regularly for updates.