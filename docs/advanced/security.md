# Security Considerations

Comprehensive security guide for Zenoo RPC applications covering authentication, authorization, encryption, secure coding practices, and production deployment security following OWASP guidelines.

## Overview

Security in Zenoo RPC applications involves multiple layers:

- **Authentication & Authorization**: Secure user verification and access control
- **Data Protection**: Encryption in transit and at rest
- **Input Validation**: Protection against injection attacks
- **Session Management**: Secure session handling and token management
- **Network Security**: HTTPS, rate limiting, and API protection
- **Dependency Security**: Secure third-party library management

## Authentication Security

### Secure Authentication Implementation

```python
import hashlib
import secrets
import time
from typing import Optional
from cryptography.fernet import Fernet
from passlib.context import CryptContext

class SecureAuthManager:
    """Secure authentication manager for Zenoo RPC."""
    
    def __init__(self):
        # Use bcrypt for password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Session management
        self.active_sessions = {}
        self.failed_attempts = {}
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5 minutes
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    async def authenticate(self, username: str, password: str, database: str) -> Optional[str]:
        """Secure authentication with rate limiting."""
        
        # Check for account lockout
        if self._is_account_locked(username):
            raise SecurityError("Account temporarily locked due to failed attempts")
        
        try:
            # Authenticate with Odoo
            client = ZenooClient("localhost", port=8069)
            await client.login(database, username, password)
            
            # Generate secure session token
            session_token = self._generate_session_token(username, database)
            
            # Store session with expiration
            self.active_sessions[session_token] = {
                "username": username,
                "database": database,
                "created_at": time.time(),
                "last_activity": time.time(),
                "expires_at": time.time() + 3600  # 1 hour
            }
            
            # Clear failed attempts on successful login
            self.failed_attempts.pop(username, None)
            
            return session_token
            
        except AuthenticationError:
            # Track failed attempts
            self._record_failed_attempt(username)
            raise SecurityError("Invalid credentials")
    
    def _generate_session_token(self, username: str, database: str) -> str:
        """Generate cryptographically secure session token."""
        token_data = f"{username}:{database}:{time.time()}:{secrets.token_hex(16)}"
        encrypted_token = self.cipher_suite.encrypt(token_data.encode())
        return encrypted_token.hex()
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts."""
        if username not in self.failed_attempts:
            return False
        
        attempts_data = self.failed_attempts[username]
        if attempts_data["count"] >= self.max_failed_attempts:
            if time.time() - attempts_data["last_attempt"] < self.lockout_duration:
                return True
            else:
                # Lockout period expired, reset attempts
                del self.failed_attempts[username]
        
        return False
    
    def _record_failed_attempt(self, username: str):
        """Record failed authentication attempt."""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = {"count": 0, "last_attempt": 0}
        
        self.failed_attempts[username]["count"] += 1
        self.failed_attempts[username]["last_attempt"] = time.time()
    
    def _get_encryption_key(self) -> bytes:
        """Get encryption key from secure storage."""
        # In production, use environment variables or key management service
        key = os.getenv("ZENOO_ENCRYPTION_KEY")
        if not key:
            raise SecurityError("Encryption key not configured")
        return key.encode()
```

### Multi-Factor Authentication (MFA)

```python
import pyotp
import qrcode
from io import BytesIO

class MFAManager:
    """Multi-Factor Authentication manager."""
    
    def __init__(self):
        self.issuer_name = "Zenoo RPC"
    
    def generate_secret(self, username: str) -> str:
        """Generate TOTP secret for user."""
        return pyotp.random_base32()
    
    def generate_qr_code(self, username: str, secret: str) -> bytes:
        """Generate QR code for TOTP setup."""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name=self.issuer_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        return img_buffer.getvalue()
    
    def verify_totp(self, secret: str, token: str) -> bool:
        """Verify TOTP token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 30s window
    
    async def authenticate_with_mfa(self, username: str, password: str, 
                                   totp_token: str, database: str) -> str:
        """Authenticate with MFA."""
        # First, verify password
        auth_manager = SecureAuthManager()
        
        # Get user's MFA secret (from secure storage)
        mfa_secret = await self._get_user_mfa_secret(username)
        if not mfa_secret:
            raise SecurityError("MFA not configured for user")
        
        # Verify TOTP token
        if not self.verify_totp(mfa_secret, totp_token):
            raise SecurityError("Invalid MFA token")
        
        # Proceed with normal authentication
        return await auth_manager.authenticate(username, password, database)
    
    async def _get_user_mfa_secret(self, username: str) -> Optional[str]:
        """Get user's MFA secret from secure storage."""
        # Implementation depends on your storage solution
        pass
```

## Authorization & Access Control

### Role-Based Access Control (RBAC)

```python
from enum import Enum
from typing import Set, Dict, List

class Permission(Enum):
    """System permissions."""
    READ_PARTNERS = "read_partners"
    WRITE_PARTNERS = "write_partners"
    DELETE_PARTNERS = "delete_partners"
    READ_PRODUCTS = "read_products"
    WRITE_PRODUCTS = "write_products"
    ADMIN_ACCESS = "admin_access"

class Role(Enum):
    """System roles."""
    VIEWER = "viewer"
    EDITOR = "editor"
    MANAGER = "manager"
    ADMIN = "admin"

class AccessControlManager:
    """Role-based access control manager."""
    
    def __init__(self):
        # Define role permissions
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.VIEWER: {
                Permission.READ_PARTNERS,
                Permission.READ_PRODUCTS
            },
            Role.EDITOR: {
                Permission.READ_PARTNERS,
                Permission.WRITE_PARTNERS,
                Permission.READ_PRODUCTS,
                Permission.WRITE_PRODUCTS
            },
            Role.MANAGER: {
                Permission.READ_PARTNERS,
                Permission.WRITE_PARTNERS,
                Permission.DELETE_PARTNERS,
                Permission.READ_PRODUCTS,
                Permission.WRITE_PRODUCTS
            },
            Role.ADMIN: set(Permission)  # All permissions
        }
        
        # User role assignments
        self.user_roles: Dict[str, Set[Role]] = {}
    
    def assign_role(self, username: str, role: Role):
        """Assign role to user."""
        if username not in self.user_roles:
            self.user_roles[username] = set()
        self.user_roles[username].add(role)
    
    def revoke_role(self, username: str, role: Role):
        """Revoke role from user."""
        if username in self.user_roles:
            self.user_roles[username].discard(role)
    
    def has_permission(self, username: str, permission: Permission) -> bool:
        """Check if user has specific permission."""
        user_roles = self.user_roles.get(username, set())
        
        for role in user_roles:
            if permission in self.role_permissions.get(role, set()):
                return True
        
        return False
    
    def get_user_permissions(self, username: str) -> Set[Permission]:
        """Get all permissions for user."""
        user_roles = self.user_roles.get(username, set())
        permissions = set()
        
        for role in user_roles:
            permissions.update(self.role_permissions.get(role, set()))
        
        return permissions

# Authorization decorator
def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from context
            current_user = get_current_user()
            
            access_manager = AccessControlManager()
            if not access_manager.has_permission(current_user, permission):
                raise SecurityError(f"Permission denied: {permission.value}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage example
@require_permission(Permission.WRITE_PARTNERS)
async def create_partner(client: ZenooClient, partner_data: dict):
    """Create partner with permission check."""
    return await client.create("res.partner", partner_data)
```

### Object-Level Authorization

```python
class ObjectLevelAuthManager:
    """Prevent BOLA (Broken Object Level Authorization) attacks."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def check_object_access(self, username: str, model_name: str, 
                                 record_id: int, operation: str) -> bool:
        """Check if user can access specific object."""
        
        # Get user's accessible record IDs for this model
        accessible_ids = await self._get_accessible_record_ids(
            username, model_name, operation
        )
        
        return record_id in accessible_ids
    
    async def _get_accessible_record_ids(self, username: str, model_name: str, 
                                       operation: str) -> Set[int]:
        """Get record IDs accessible to user."""
        # Implementation depends on your business logic
        # Example: Users can only access their own records
        
        if model_name == "res.partner":
            # Get partners created by or assigned to user
            domain = [
                "|",
                ("create_uid", "=", username),
                ("user_id", "=", username)
            ]
            
            records = await self.client.search(model_name, domain)
            return set(records)
        
        return set()

# Secure object access decorator
def secure_object_access(model_name: str, operation: str):
    """Decorator for secure object-level access."""
    def decorator(func):
        async def wrapper(client: ZenooClient, record_id: int, *args, **kwargs):
            current_user = get_current_user()
            
            auth_manager = ObjectLevelAuthManager(client)
            if not await auth_manager.check_object_access(
                current_user, model_name, record_id, operation
            ):
                raise SecurityError(f"Access denied to {model_name} record {record_id}")
            
            return await func(client, record_id, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@secure_object_access("res.partner", "read")
async def get_partner(client: ZenooClient, partner_id: int):
    """Get partner with object-level security check."""
    return await client.read("res.partner", [partner_id])
```

## Data Protection & Encryption

### Encryption at Rest

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    """Handle encryption of sensitive data."""
    
    def __init__(self):
        self.key = self._derive_key()
        self.cipher_suite = Fernet(self.key)
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from password and salt."""
        password = os.getenv("ENCRYPTION_PASSWORD", "").encode()
        salt = os.getenv("ENCRYPTION_SALT", "").encode()
        
        if not password or not salt:
            raise SecurityError("Encryption credentials not configured")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_data.decode()

class SecureDataHandler:
    """Handle sensitive data with encryption."""
    
    def __init__(self):
        self.encryption = DataEncryption()
    
    async def store_sensitive_partner_data(self, client: ZenooClient, partner_data: dict):
        """Store partner data with sensitive fields encrypted."""
        
        # Fields that should be encrypted
        sensitive_fields = ["email", "phone", "mobile", "vat"]
        
        encrypted_data = partner_data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encryption.encrypt_sensitive_data(
                    str(encrypted_data[field])
                )
        
        return await client.create("res.partner", encrypted_data)
    
    async def retrieve_sensitive_partner_data(self, client: ZenooClient, partner_id: int):
        """Retrieve and decrypt sensitive partner data."""
        
        partner_data = await client.read("res.partner", [partner_id])
        if not partner_data:
            return None
        
        partner = partner_data[0]
        sensitive_fields = ["email", "phone", "mobile", "vat"]
        
        for field in sensitive_fields:
            if field in partner and partner[field]:
                try:
                    partner[field] = self.encryption.decrypt_sensitive_data(partner[field])
                except Exception:
                    # Handle decryption errors gracefully
                    partner[field] = "[ENCRYPTED]"
        
        return partner
```

### Secure Configuration Management

```python
import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class SecurityConfig:
    """Security configuration with secure defaults."""
    
    # Authentication
    session_timeout: int = 3600  # 1 hour
    max_failed_attempts: int = 5
    lockout_duration: int = 300  # 5 minutes
    
    # Encryption
    encryption_key: Optional[str] = None
    encryption_salt: Optional[str] = None
    
    # API Security
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # 1 minute
    
    # HTTPS
    force_https: bool = True
    hsts_max_age: int = 31536000  # 1 year
    
    @classmethod
    def from_environment(cls) -> "SecurityConfig":
        """Load configuration from environment variables."""
        return cls(
            session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600")),
            max_failed_attempts=int(os.getenv("MAX_FAILED_ATTEMPTS", "5")),
            lockout_duration=int(os.getenv("LOCKOUT_DURATION", "300")),
            encryption_key=os.getenv("ENCRYPTION_KEY"),
            encryption_salt=os.getenv("ENCRYPTION_SALT"),
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            rate_limit_window=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
            force_https=os.getenv("FORCE_HTTPS", "true").lower() == "true",
            hsts_max_age=int(os.getenv("HSTS_MAX_AGE", "31536000"))
        )
    
    def validate(self):
        """Validate security configuration."""
        if not self.encryption_key:
            raise SecurityError("Encryption key must be configured")
        
        if not self.encryption_salt:
            raise SecurityError("Encryption salt must be configured")
        
        if self.session_timeout < 300:  # 5 minutes minimum
            raise SecurityError("Session timeout too short")
        
        if self.max_failed_attempts < 3:
            raise SecurityError("Max failed attempts too low")
```

## Input Validation & Sanitization

### Secure Input Validation

```python
import re
from typing import Any, Dict, List
from pydantic import BaseModel, validator, Field

class SecurePartnerInput(BaseModel):
    """Secure input validation for partner data."""
    
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=200)
    vat: Optional[str] = Field(None, max_length=32)
    
    @validator("name")
    def validate_name(cls, v):
        """Validate partner name."""
        # Remove potentially dangerous characters
        if re.search(r'[<>"\']', v):
            raise ValueError("Name contains invalid characters")
        return v.strip()
    
    @validator("email")
    def validate_email(cls, v):
        """Validate email format."""
        if v is None:
            return v
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        
        return v.lower().strip()
    
    @validator("phone")
    def validate_phone(cls, v):
        """Validate phone number."""
        if v is None:
            return v
        
        # Allow only digits, spaces, +, -, (, )
        if not re.match(r'^[+\-\s\d()]+$', v):
            raise ValueError("Invalid phone number format")
        
        return v.strip()
    
    @validator("website")
    def validate_website(cls, v):
        """Validate website URL."""
        if v is None:
            return v
        
        # Basic URL validation
        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        if not re.match(url_pattern, v):
            raise ValueError("Invalid website URL")
        
        return v.strip()
    
    @validator("vat")
    def validate_vat(cls, v):
        """Validate VAT number."""
        if v is None:
            return v
        
        # Allow only alphanumeric characters
        if not re.match(r'^[A-Z0-9]+$', v.upper()):
            raise ValueError("Invalid VAT format")
        
        return v.upper().strip()

class InputSanitizer:
    """Sanitize input data to prevent injection attacks."""
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove or escape potentially dangerous characters
        dangerous_chars = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;'
        }
        
        for char, replacement in dangerous_chars.items():
            value = value.replace(char, replacement)
        
        return value.strip()
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data."""
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            clean_key = InputSanitizer.sanitize_string(str(key))
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[clean_key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[clean_key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    InputSanitizer.sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[clean_key] = value
        
        return sanitized

# Secure API endpoint
async def create_partner_secure(client: ZenooClient, partner_data: dict):
    """Create partner with secure input validation."""
    
    # Sanitize input
    sanitized_data = InputSanitizer.sanitize_dict(partner_data)
    
    # Validate input
    try:
        validated_data = SecurePartnerInput(**sanitized_data)
    except ValidationError as e:
        raise SecurityError(f"Invalid input: {e}")
    
    # Create partner with validated data
    return await client.create("res.partner", validated_data.dict())
```

## API Security

### Rate Limiting & DDoS Protection

```python
import time
from collections import defaultdict, deque
from typing import Dict, Deque
import asyncio

class RateLimiter:
    """Rate limiting to prevent abuse."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for identifier."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        user_requests = self.requests[identifier]
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) >= self.max_requests:
            return False
        
        # Add current request
        user_requests.append(now)
        return True
    
    async def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        now = time.time()
        window_start = now - self.window_seconds
        
        user_requests = self.requests[identifier]
        # Count requests in current window
        current_requests = sum(1 for req_time in user_requests if req_time >= window_start)
        
        return max(0, self.max_requests - current_requests)

class SecurityMiddleware:
    """Security middleware for API protection."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        self.blocked_ips = set()
        self.suspicious_activity = defaultdict(int)
    
    async def process_request(self, request_info: dict) -> bool:
        """Process request through security checks."""
        client_ip = request_info.get("client_ip")
        user_agent = request_info.get("user_agent", "")
        
        # Check blocked IPs
        if client_ip in self.blocked_ips:
            raise SecurityError("IP address blocked")
        
        # Rate limiting
        if not await self.rate_limiter.is_allowed(client_ip):
            self.suspicious_activity[client_ip] += 1
            
            # Block IP after repeated rate limit violations
            if self.suspicious_activity[client_ip] > 5:
                self.blocked_ips.add(client_ip)
            
            raise SecurityError("Rate limit exceeded")
        
        # Check for suspicious user agents
        if self._is_suspicious_user_agent(user_agent):
            self.suspicious_activity[client_ip] += 1
            raise SecurityError("Suspicious request detected")
        
        return True
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check for suspicious user agent patterns."""
        suspicious_patterns = [
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
            "python-requests",  # Block generic requests
            "curl",             # Block curl unless whitelisted
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)
```

## Production Security Checklist

### Deployment Security

```python
class ProductionSecurityChecker:
    """Check production security configuration."""
    
    def __init__(self):
        self.checks = []
    
    def check_environment_variables(self):
        """Check required environment variables."""
        required_vars = [
            "ENCRYPTION_KEY",
            "ENCRYPTION_SALT",
            "DATABASE_PASSWORD",
            "SECRET_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.checks.append(f"❌ Missing environment variables: {missing_vars}")
        else:
            self.checks.append("✅ All required environment variables set")
    
    def check_https_configuration(self):
        """Check HTTPS configuration."""
        force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"
        
        if not force_https:
            self.checks.append("❌ HTTPS not enforced")
        else:
            self.checks.append("✅ HTTPS enforced")
    
    def check_debug_mode(self):
        """Check debug mode is disabled."""
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        if debug_mode:
            self.checks.append("❌ Debug mode enabled in production")
        else:
            self.checks.append("✅ Debug mode disabled")
    
    def check_default_credentials(self):
        """Check for default credentials."""
        default_passwords = ["admin", "password", "123456", "odoo"]
        admin_password = os.getenv("ADMIN_PASSWORD", "")
        
        if admin_password.lower() in default_passwords:
            self.checks.append("❌ Default or weak admin password")
        else:
            self.checks.append("✅ Strong admin password configured")
    
    def run_all_checks(self) -> List[str]:
        """Run all security checks."""
        self.checks = []
        
        self.check_environment_variables()
        self.check_https_configuration()
        self.check_debug_mode()
        self.check_default_credentials()
        
        return self.checks

# Usage
checker = ProductionSecurityChecker()
results = checker.run_all_checks()

for result in results:
    print(result)
```

### Security Headers

```python
class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers."""
        return {
            # HTTPS enforcement
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # XSS protection
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "media-src 'self'; "
                "frame-src 'none';"
            ),
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            )
        }
```

## Security Best Practices Summary

### 1. Authentication
- Use strong password hashing (bcrypt/Argon2)
- Implement MFA for sensitive accounts
- Use secure session management
- Implement account lockout policies

### 2. Authorization
- Follow principle of least privilege
- Implement RBAC with clear role definitions
- Prevent BOLA attacks with object-level checks
- Separate authorization logic from business logic

### 3. Data Protection
- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Implement secure key management
- Regular key rotation

### 4. Input Validation
- Validate all input data
- Use parameterized queries/ORMs
- Sanitize output data
- Implement rate limiting

### 5. Production Security
- Disable debug mode
- Use environment variables for secrets
- Implement security headers
- Regular security audits

## Next Steps

- Review [Architecture Overview](architecture.md) for security integration
- Explore [Extension Points](extensions.md) for custom security modules
- Check [Monitoring Setup](../troubleshooting/monitoring.md) for security monitoring
- Learn about [Performance Optimization](performance.md) with security considerations
