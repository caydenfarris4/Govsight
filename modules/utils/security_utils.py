"""
Security Utilities Module

Provides security functions for input validation, error handling, and data sanitization
to protect against common web application vulnerabilities.
"""

import re
import logging
from typing import Any, Dict, Optional

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/security.log'),
        logging.StreamHandler()
    ]
)

security_logger = logging.getLogger('govsight.security')

# SQL Injection Prevention
SQL_INJECTION_KEYWORDS = [
    'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'EXEC', 
    'UNION', 'SELECT', '--', ';', 'SCRIPT', 'IFRAME', 'JAVASCRIPT',
    'ONLOAD', 'ONERROR', 'ONCLICK', 'EVAL', 'EXPRESSION'
]

def validate_project_name(name: str) -> Dict[str, Any]:
    """
    Validate project name input to prevent SQL injection and XSS
    
    Args:
        name (str): Project name to validate
        
    Returns:
        dict: Validation result with 'valid' boolean and 'message' string
    """
    if not name or not name.strip():
        return {'valid': False, 'message': 'Project name cannot be empty'}
    
    name = name.strip()
    
    # Length validation
    if len(name) > 100:
        return {'valid': False, 'message': 'Project name must be less than 100 characters'}
    
    # Character validation - allow alphanumeric, spaces, and safe punctuation
    if not re.match(r"^[a-zA-Z0-9\s\-\.'&()]+$", name):
        return {'valid': False, 'message': 'Project name contains invalid characters. Use only letters, numbers, spaces, and basic punctuation.'}
    
    # SQL injection keyword detection
    name_upper = name.upper()
    for keyword in SQL_INJECTION_KEYWORDS:
        if keyword in name_upper:
            security_logger.warning(f"SQL injection attempt detected in project name: {name}")
            return {'valid': False, 'message': 'Project name contains restricted keywords. Please use a different name.'}
    
    return {'valid': True, 'message': 'Valid project name'}

def validate_text_input(text: str, field_name: str, max_length: int = 500) -> Dict[str, Any]:
    """
    Validate text input to prevent XSS and injection attacks
    
    Args:
        text (str): Text to validate
        field_name (str): Name of the field for error messages
        max_length (int): Maximum allowed length
        
    Returns:
        dict: Validation result with 'valid' boolean and 'message' string
    """
    if not text:
        return {'valid': True, 'message': f'Valid {field_name}'}
    
    text = text.strip()
    
    # Length validation
    if len(text) > max_length:
        return {'valid': False, 'message': f'{field_name} must be less than {max_length} characters'}
    
    # XSS and SQL injection detection
    text_upper = text.upper()
    dangerous_patterns = [
        '<SCRIPT', '<IFRAME', '<OBJECT', '<EMBED', '<FORM',
        'JAVASCRIPT:', 'VBSCRIPT:', 'ONLOAD=', 'ONERROR=', 'ONCLICK=',
        'EVAL(', 'EXPRESSION('
    ] + SQL_INJECTION_KEYWORDS
    
    for pattern in dangerous_patterns:
        if pattern in text_upper:
            security_logger.warning(f"Potentially malicious content detected in {field_name}: {text[:50]}...")
            return {'valid': False, 'message': f'{field_name} contains restricted content. Please remove any HTML tags or SQL keywords.'}
    
    return {'valid': True, 'message': f'Valid {field_name}'}

def sanitize_for_database(text: str) -> str:
    """
    Sanitize text for safe database storage
    
    Args:
        text (str): Text to sanitize
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes and control characters
    sanitized = text.replace('\x00', '').strip()
    
    # Limit length
    sanitized = sanitized[:1000]
    
    return sanitized

def handle_error_safely(error: Exception, user_message: str = "An error occurred. Please try again.") -> str:
    """
    Handle errors safely without exposing system details to users
    
    Args:
        error (Exception): The exception that occurred
        user_message (str): Safe message to show to user
        
    Returns:
        str: Safe error message for user display
    """
    # Log the full error for developers
    security_logger.error(f"Application error: {str(error)}", exc_info=True)
    
    # Return generic message to user
    return user_message

def validate_numeric_input(value: Any, field_name: str, min_value: float = 0, max_value: float = 1e12) -> Dict[str, Any]:
    """
    Validate numeric input
    
    Args:
        value: Value to validate
        field_name (str): Name of the field
        min_value (float): Minimum allowed value
        max_value (float): Maximum allowed value
        
    Returns:
        dict: Validation result
    """
    try:
        num_value = float(value)
        
        if num_value < min_value:
            return {'valid': False, 'message': f'{field_name} must be at least {min_value:,.2f}'}
        
        if num_value > max_value:
            return {'valid': False, 'message': f'{field_name} cannot exceed {max_value:,.2f}'}
        
        return {'valid': True, 'message': f'Valid {field_name}', 'value': num_value}
        
    except (ValueError, TypeError):
        return {'valid': False, 'message': f'{field_name} must be a valid number'}

def create_safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing dangerous characters
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Safe filename
    """
    if not filename:
        return "unnamed_file"
    
    # Remove path separators and dangerous characters
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    
    # Limit length
    safe_name = safe_name[:100]
    
    # Ensure it doesn't start with a dot
    if safe_name.startswith('.'):
        safe_name = 'file_' + safe_name[1:]
    
    return safe_name or "unnamed_file"

def log_security_event(event_type: str, details: str, user_id: str = None):
    """
    Log security-related events
    
    Args:
        event_type (str): Type of security event
        details (str): Event details
        user_id (str): User ID if available
    """
    security_logger.info(f"Security Event: {event_type} | User: {user_id or 'Unknown'} | Details: {details}")