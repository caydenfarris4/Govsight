"""
Security Module for GovSight Financial Analyzer

This module provides comprehensive security features including:
- SQL injection prevention
- Password security and hashing
- Input validation and sanitization
- Security logging and audit trails
"""

from .security_utils import (
    sanitize_sql_identifier,
    validate_and_sanitize_input,
    execute_safe_query,
    validate_organization_name,
    validate_department_name,
    log_security_event
)

from .password_security import (
    generate_salt,
    hash_password,
    verify_password,
    generate_secure_password,
    validate_password_strength,
    create_session_token,
    migrate_plain_text_passwords,
    secure_compare
)

from .input_validation import (
    validate_file_upload,
    sanitize_html_input,
    validate_numeric_input,
    validate_email_address,
    validate_phone_number,
    validate_date_input,
    sanitize_search_query,
    validate_url
)

from .audit_logger import (
    SecurityAuditLogger,
    SecurityEventType,
    ThreatLevel,
    SecurityEvent,
    get_security_logger,
    log_security_event
)

from .session_manager import (
    SessionManager,
    UserSession,
    get_session_manager
)

from .rbac_manager import (
    RBACManager,
    ResourceType,
    Permission,
    Role,
    UserRole,
    get_rbac_manager,
    require_permission
)

from .enhanced_auth import (
    EnhancedAuth,
    get_enhanced_auth,
    enhanced_require_login,
    enhanced_require_permission
)

from .secret_manager import (
    UnifiedSecretManager,
    get_secret_manager,
    get_secret
)

__all__ = [
    # Security utilities
    'sanitize_sql_identifier',
    'validate_and_sanitize_input',
    'execute_safe_query',
    'validate_organization_name',
    'validate_department_name',
    'log_security_event',
    
    # Password security
    'generate_salt',
    'hash_password',
    'verify_password',
    'generate_secure_password',
    'validate_password_strength',
    'create_session_token',
    'migrate_plain_text_passwords',
    'secure_compare',
    
    # Input validation
    'validate_file_upload',
    'sanitize_html_input',
    'validate_numeric_input',
    'validate_email_address',
    'validate_phone_number',
    'validate_date_input',
    'sanitize_search_query',
    'validate_url',
    
    # Security audit logging
    'SecurityAuditLogger',
    'SecurityEventType',
    'ThreatLevel',
    'SecurityEvent',
    'get_security_logger',
    'log_security_event',
    
    # Session management
    'SessionManager',
    'UserSession',
    'get_session_manager',
    
    # RBAC management
    'RBACManager',
    'ResourceType',
    'Permission',
    'Role',
    'UserRole',
    'get_rbac_manager',
    'require_permission',
    
    # Enhanced authentication
    'EnhancedAuth',
    'get_enhanced_auth',
    'enhanced_require_login',
    'enhanced_require_permission',
    
    # Secret management
    'UnifiedSecretManager',
    'get_secret_manager',
    'get_secret'
]