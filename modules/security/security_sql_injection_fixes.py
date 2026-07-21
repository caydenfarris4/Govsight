"""
Comprehensive SQL Injection Prevention Module
Fixes all identified SQL injection vulnerabilities in GovSight application
"""

import sqlite3
import re
from typing import Optional, List, Dict, Any, Union
import logging

# Configure security logging
logging.basicConfig(level=logging.INFO)
security_logger = logging.getLogger('govsight.security')

class SQLSecurityValidator:
    """Advanced SQL injection prevention and query validation"""
    
    # Whitelist of allowed table names (prevents table injection)
    ALLOWED_TABLES = {
        'departments', 'DepartmentPerformance', 'tblTransaction', 
        'saved_scenarios', 'audit_log', 'security_events', 'rbac_policies'
    }
    
    # Whitelist of allowed column names
    ALLOWED_COLUMNS = {
        'ID', 'Name', 'Department', 'DepartmentName', 'Budget', 'Actual', 
        'Variance', 'FiscalYear', 'Type', 'GLAccount', 'Amount', 'Date',
        'Organization', 'DepartmentID', 'TransactionID'
    }
    
    # Dangerous SQL patterns to block
    DANGEROUS_PATTERNS = [
        r'(\b(drop|delete|update|insert|alter|create|exec|execute)\b)',
        r'(;|\|\||&&)',  # SQL injection terminators and operators
        r'(\/\*|\*\/)',  # SQL comments
        r'(\bxp_|\bsp_)',  # SQL Server extended procedures
        r'(\bunion\b.*\bselect\b)',  # UNION-based injections
        r'(\binto\b.*\boutfile\b)',  # File operations
        r'(\bload_file\b|\binto\s+dumpfile\b)',  # MySQL file functions
        r'(\bor\b.*1\s*=\s*1)',  # Common OR injection
        r'(\'.*\'.*or.*\'.*\')',  # Quote-based OR injection
    ]
    
    @classmethod
    def validate_table_name(cls, table_name: str) -> str:
        """Validate and sanitize table name"""
        if not table_name or not isinstance(table_name, str):
            raise ValueError("Invalid table name")
        
        # Remove any non-alphanumeric characters except underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', table_name)
        
        if sanitized not in cls.ALLOWED_TABLES:
            security_logger.warning(f"Blocked access to unauthorized table: {table_name}")
            raise ValueError(f"Access to table '{table_name}' not authorized")
        
        return sanitized
    
    @classmethod
    def validate_column_name(cls, column_name: str) -> str:
        """Validate and sanitize column name"""
        if not column_name or not isinstance(column_name, str):
            raise ValueError("Invalid column name")
        
        # Remove any non-alphanumeric characters except underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', column_name)
        
        if sanitized not in cls.ALLOWED_COLUMNS:
            security_logger.warning(f"Blocked access to unauthorized column: {column_name}")
            raise ValueError(f"Access to column '{column_name}' not authorized")
        
        return sanitized
    
    @classmethod
    def validate_organization_name(cls, org_name: str) -> str:
        """Validate and sanitize organization name"""
        if not org_name or not isinstance(org_name, str):
            raise ValueError("Invalid organization name")
        
        # Only allow alphanumeric and basic characters
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', org_name)
        
        if len(sanitized) < 2 or len(sanitized) > 50:
            raise ValueError("Organization name must be 2-50 characters")
        
        return sanitized
    
    @classmethod
    def scan_for_sql_injection(cls, query: str) -> None:
        """Scan query for SQL injection patterns"""
        if not query:
            return
        
        query_lower = query.lower()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                security_logger.error(f"SQL injection attempt detected: {pattern}")
                raise ValueError(f"Query contains dangerous pattern and was blocked")
    
    @classmethod
    def build_safe_select_query(cls, 
                               table: str, 
                               columns: List[str] = None,
                               where_conditions: Dict[str, Any] = None,
                               limit: int = None) -> tuple:
        """Build a parameterized SELECT query safely"""
        
        # Validate table name
        safe_table = cls.validate_table_name(table)
        
        # Validate columns
        if columns:
            safe_columns = [cls.validate_column_name(col) for col in columns]
            column_str = ', '.join(safe_columns)
        else:
            column_str = '*'
        
        # Start building query
        query = f"SELECT {column_str} FROM {safe_table}"
        params = []
        
        # Add WHERE conditions with parameters
        if where_conditions:
            where_clauses = []
            for column, value in where_conditions.items():
                safe_column = cls.validate_column_name(column)
                where_clauses.append(f"{safe_column} = ?")
                params.append(value)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        # Add limit
        if limit and isinstance(limit, int) and limit > 0:
            query += f" LIMIT {min(limit, 1000)}"  # Cap at 1000 rows max
        
        return query, tuple(params)

# Secure database connection functions
def execute_safe_query(query: str, 
                      params: tuple = (), 
                      db_path: str = None,
                      fetchall: bool = True) -> Optional[Union[List[Dict], Dict]]:
    """Execute a parameterized query safely"""
    
    # Validate the query for injection attempts
    SQLSecurityValidator.scan_for_sql_injection(query)
    
    conn = None
    try:
        conn = sqlite3.connect(db_path or "databases/core/caselle_gl0_mock.db")
        conn.row_factory = sqlite3.Row  # Enable column name access
        cursor = conn.cursor()
        
        # Execute with parameters
        cursor.execute(query, params)
        
        if fetchall:
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []
        else:
            result = cursor.fetchone()
            return dict(result) if result else None
            
    except sqlite3.Error as e:
        security_logger.error(f"Database error: {e}")
        return None
    except Exception as e:
        security_logger.error(f"Query execution error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def load_department_data_secure(org: str, 
                               department: str = None,
                               limit: int = 500) -> List[Dict]:
    """Securely load department data with parameterization"""
    
    try:
        # Validate inputs
        safe_org = SQLSecurityValidator.validate_organization_name(org)
        
        where_conditions = {'Organization': safe_org}
        
        if department:
            safe_dept = SQLSecurityValidator.validate_column_name(department)
            where_conditions['Department'] = safe_dept
        
        # Build safe query
        query, params = SQLSecurityValidator.build_safe_select_query(
            table='DepartmentPerformance',
            where_conditions=where_conditions,
            limit=limit
        )
        
        # Execute safely
        results = execute_safe_query(query, params, fetchall=True)
        
        return results or []
        
    except ValueError as e:
        security_logger.warning(f"Invalid input blocked: {e}")
        return []
    except Exception as e:
        security_logger.error(f"Error loading department data: {e}")
        return []

def get_available_tables_secure(db_path: str = None) -> List[str]:
    """Get list of available tables securely"""
    
    query = """
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name NOT LIKE 'sqlite_%'
    ORDER BY name
    """
    
    try:
        results = execute_safe_query(query, (), db_path, fetchall=True)
        
        # Filter to only allowed tables
        if results:
            available_tables = [row['name'] for row in results]
            return [table for table in available_tables 
                   if table in SQLSecurityValidator.ALLOWED_TABLES]
        return []
        
    except Exception as e:
        security_logger.error(f"Error getting table list: {e}")
        return []

def check_table_exists_secure(table_name: str, db_path: str = None) -> bool:
    """Check if table exists securely"""
    
    try:
        # Validate table name first
        safe_table = SQLSecurityValidator.validate_table_name(table_name)
        
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name = ?"
        result = execute_safe_query(query, (safe_table,), db_path, fetchall=False)
        
        return result is not None
        
    except Exception as e:
        security_logger.error(f"Error checking table existence: {e}")
        return False