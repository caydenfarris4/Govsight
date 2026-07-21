"""
Security utilities for SQL injection prevention and input validation
"""
import re
import sqlite3
from typing import Any, List, Tuple, Union
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifiers (table names, column names) to prevent injection
    
    Args:
        identifier (str): The identifier to sanitize
        
    Returns:
        str: Sanitized identifier
        
    Raises:
        ValueError: If identifier contains invalid characters
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty")
    
    # Allow only alphanumeric characters, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', identifier):
        raise ValueError(f"Invalid identifier: {identifier}. Only alphanumeric, underscore, and hyphen characters allowed.")
    
    # Prevent SQL keywords as identifiers
    sql_keywords = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TABLE', 'DATABASE', 'INDEX', 'VIEW', 'TRIGGER', 'PROCEDURE', 
        'FUNCTION', 'UNION', 'WHERE', 'ORDER', 'GROUP', 'HAVING'
    }
    
    if identifier.upper() in sql_keywords:
        raise ValueError(f"SQL keyword '{identifier}' cannot be used as identifier")
    
    return identifier

def validate_and_sanitize_input(user_input: str, max_length: int = 1000) -> str:
    """
    Validate and sanitize user input to prevent injection attacks
    
    Args:
        user_input (str): Raw user input
        max_length (int): Maximum allowed length
        
    Returns:
        str: Sanitized input
        
    Raises:
        ValueError: If input is invalid or dangerous
    """
    if not isinstance(user_input, str):
        raise ValueError("Input must be a string")
    
    if len(user_input) > max_length:
        raise ValueError(f"Input too long (max {max_length} characters)")
    
    # Remove dangerous SQL injection patterns
    dangerous_patterns = [
        r';.*--',  # SQL comments
        r'\/\*.*\*\/',  # SQL block comments
        r'\bUNION\b.*\bSELECT\b',  # UNION SELECT
        r'\bDROP\b.*\bTABLE\b',  # DROP TABLE
        r'\bDELETE\b.*\bFROM\b',  # DELETE FROM
        r'\bINSERT\b.*\bINTO\b',  # INSERT INTO
        r'\bUPDATE\b.*\bSET\b',  # UPDATE SET
        r'\bEXEC\b',  # EXEC
        r'\bxp_\w+',  # SQL Server extended procedures
        r'\bsp_\w+',  # SQL Server stored procedures
    ]
    
    original_input = user_input
    for pattern in dangerous_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            logger.warning(f"Dangerous pattern detected in input: {pattern}")
            raise ValueError("Input contains potentially dangerous SQL patterns")
    
    # Basic sanitization - remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', user_input)
    sanitized = sanitized.strip()
    
    return sanitized

def execute_safe_query(
    conn: sqlite3.Connection, 
    query: str, 
    params: Tuple[Any, ...] = (), 
    fetchall: bool = True
) -> Union[List[Tuple], Tuple, None]:
    """
    Execute a parameterized query safely
    
    Args:
        conn: Database connection
        query: SQL query with placeholders
        params: Parameters for the query
        fetchall: Whether to fetch all results
        
    Returns:
        Query results or None if error
    """
    try:
        cursor = conn.cursor()
        
        # Log query for audit (without parameters for security)
        logger.info(f"Executing query: {query}")
        
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            if fetchall:
                return cursor.fetchall()
            else:
                return cursor.fetchone()
        else:
            conn.commit()
            return cursor.rowcount
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

def validate_organization_name(org_name: str) -> str:
    """
    Validate organization name to prevent injection
    
    Args:
        org_name (str): Organization name to validate
        
    Returns:
        str: Validated organization name
        
    Raises:
        ValueError: If organization name is invalid
    """
    if not org_name:
        raise ValueError("Organization name cannot be empty")
    
    # Allow alphanumeric, spaces, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9\s_-]+$', org_name):
        raise ValueError("Invalid organization name format")
    
    return org_name.strip()

def validate_department_name(dept_name: str) -> str:
    """
    Validate department name to prevent injection
    
    Args:
        dept_name (str): Department name to validate
        
    Returns:
        str: Validated department name
        
    Raises:
        ValueError: If department name is invalid
    """
    if not dept_name:
        raise ValueError("Department name cannot be empty")
    
    # Allow alphanumeric, spaces, hyphens, underscores, ampersands
    if not re.match(r'^[a-zA-Z0-9\s_&-]+$', dept_name):
        raise ValueError("Invalid department name format")
    
    return dept_name.strip()

def log_security_event(event_type: str, details: str, user: str = "unknown"):
    """
    Log security-related events for audit trail
    
    Args:
        event_type (str): Type of security event
        details (str): Event details
        user (str): User associated with the event
    """
    logger.warning(f"SECURITY EVENT - Type: {event_type}, User: {user}, Details: {details}")