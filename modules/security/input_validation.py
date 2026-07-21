"""
Input Validation Module for GovSight Financial Analyzer

This module provides comprehensive input validation and sanitization
to prevent injection attacks and ensure data integrity.
"""

import re
import html
import urllib.parse
from typing import Union, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_file_upload(uploaded_file, allowed_extensions: Optional[List[str]] = None, max_size_mb: int = 10) -> bool:
    """
    Validate uploaded file for security
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        allowed_extensions: List of allowed file extensions
        max_size_mb: Maximum file size in MB
        
    Returns:
        bool: True if file is valid, False otherwise
        
    Raises:
        ValueError: If file validation fails
    """
    if not uploaded_file:
        return False
    
    # Default allowed extensions for government documents
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.txt', '.docx', '.xlsx', '.csv']
    
    # Check file extension
    file_extension = uploaded_file.name.lower().split('.')[-1]
    if f'.{file_extension}' not in [ext.lower() for ext in allowed_extensions]:
        raise ValueError(f"File type '.{file_extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}")
    
    # Check file size
    if uploaded_file.size > max_size_mb * 1024 * 1024:
        raise ValueError(f"File size ({uploaded_file.size / (1024*1024):.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)")
    
    # Check for suspicious file names
    suspicious_patterns = [
        r'\.\./', r'\.\.\\',  # Directory traversal
        r'<script', r'javascript:',  # Script injection
        r'<%', r'<?php',  # Server-side scripts
        r'\.exe$', r'\.bat$', r'\.cmd$'  # Executable files
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, uploaded_file.name, re.IGNORECASE):
            raise ValueError("File name contains suspicious patterns")
    
    return True

def sanitize_html_input(user_input: str) -> str:
    """
    Sanitize HTML input to prevent XSS attacks
    
    Args:
        user_input (str): Raw user input
        
    Returns:
        str: Sanitized input
    """
    if not isinstance(user_input, str):
        return str(user_input)
    
    # HTML escape dangerous characters
    sanitized = html.escape(user_input)
    
    # Remove potentially dangerous HTML tags and attributes
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'javascript:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'onclick=',
        r'onmouseover='
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    return sanitized.strip()

def validate_numeric_input(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
    """
    Validate and sanitize numeric input
    
    Args:
        value: Input value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        float: Validated numeric value
        
    Raises:
        ValueError: If value is invalid
    """
    try:
        # Convert to float
        if isinstance(value, str):
            # Remove common formatting characters
            cleaned = re.sub(r'[,$\s]', '', value)
            numeric_value = float(cleaned)
        else:
            numeric_value = float(value)
        
        # Check bounds
        if min_value is not None and numeric_value < min_value:
            raise ValueError(f"Value {numeric_value} is below minimum {min_value}")
        
        if max_value is not None and numeric_value > max_value:
            raise ValueError(f"Value {numeric_value} is above maximum {max_value}")
        
        return numeric_value
        
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid numeric value: {value}")

def validate_email_address(email: str) -> str:
    """
    Validate email address format
    
    Args:
        email (str): Email address to validate
        
    Returns:
        str: Validated email address
        
    Raises:
        ValueError: If email format is invalid
    """
    if not email or not isinstance(email, str):
        raise ValueError("Email address is required")
    
    email = email.strip().lower()
    
    # Basic email validation pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email address format")
    
    # Check for suspicious patterns
    if '..' in email or email.startswith('.') or email.endswith('.'):
        raise ValueError("Invalid email address format")
    
    return email

def validate_phone_number(phone: str) -> str:
    """
    Validate and format phone number
    
    Args:
        phone (str): Phone number to validate
        
    Returns:
        str: Formatted phone number
        
    Raises:
        ValueError: If phone number is invalid
    """
    if not phone or not isinstance(phone, str):
        raise ValueError("Phone number is required")
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check length (US phone numbers)
    if len(digits_only) == 10:
        # Format as (XXX) XXX-XXXX
        return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # Format as +1 (XXX) XXX-XXXX
        return f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
    else:
        raise ValueError("Invalid phone number format. Must be 10 or 11 digits.")

def validate_date_input(date_str: str, date_format: str = "%Y-%m-%d") -> str:
    """
    Validate date input format
    
    Args:
        date_str (str): Date string to validate
        date_format (str): Expected date format
        
    Returns:
        str: Validated date string
        
    Raises:
        ValueError: If date format is invalid
    """
    import datetime
    
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date is required")
    
    try:
        # Parse date to validate format
        parsed_date = datetime.datetime.strptime(date_str.strip(), date_format)
        
        # Check for reasonable date range (1900-2100)
        if parsed_date.year < 1900 or parsed_date.year > 2100:
            raise ValueError("Date must be between 1900 and 2100")
        
        return date_str.strip()
        
    except ValueError as e:
        raise ValueError(f"Invalid date format. Expected {date_format}")

def sanitize_search_query(query: str, max_length: int = 200) -> str:
    """
    Sanitize search query input
    
    Args:
        query (str): Search query to sanitize
        max_length (int): Maximum query length
        
    Returns:
        str: Sanitized search query
        
    Raises:
        ValueError: If query is invalid
    """
    if not query or not isinstance(query, str):
        raise ValueError("Search query cannot be empty")
    
    query = query.strip()
    
    if len(query) > max_length:
        raise ValueError(f"Search query too long (max {max_length} characters)")
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';\\]', '', query)
    
    # Remove excessive whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    if not sanitized:
        raise ValueError("Search query contains only invalid characters")
    
    return sanitized

def validate_url(url: str) -> str:
    """
    Validate URL format and safety
    
    Args:
        url (str): URL to validate
        
    Returns:
        str: Validated URL
        
    Raises:
        ValueError: If URL is invalid or unsafe
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL is required")
    
    url = url.strip()
    
    # Basic URL validation
    url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    
    if not re.match(url_pattern, url):
        raise ValueError("Invalid URL format")
    
    # Parse URL components
    parsed = urllib.parse.urlparse(url)
    
    # Security checks
    if parsed.hostname:
        # Block private/local IPs
        private_patterns = [
            r'^127\.',  # localhost
            r'^10\.',   # private class A
            r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # private class B
            r'^192\.168\.',  # private class C
            r'^169\.254\.',  # link-local
            r'^0\.',    # invalid
        ]
        
        for pattern in private_patterns:
            if re.match(pattern, parsed.hostname):
                raise ValueError("URLs to private/local addresses are not allowed")
    
    return url

def create_input_validator_decorator(validation_func):
    """
    Create a decorator for input validation
    
    Args:
        validation_func: Function to validate input
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Apply validation to function arguments
            validated_args = []
            for arg in args:
                if isinstance(arg, str):
                    validated_args.append(validation_func(arg))
                else:
                    validated_args.append(arg)
            
            validated_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    validated_kwargs[key] = validation_func(value)
                else:
                    validated_kwargs[key] = value
            
            return func(*validated_args, **validated_kwargs)
        return wrapper
    return decorator