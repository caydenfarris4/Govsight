"""
Secure Database Operations Module

This module provides secure database operations with comprehensive
SQL injection prevention and parameter validation.
"""

import sqlite3
import pandas as pd
from typing import Any, List, Tuple, Union, Optional, Dict
import logging
from modules.security.security_utils import (
    sanitize_sql_identifier,
    validate_and_sanitize_input,
    execute_safe_query,
    log_security_event
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureDatabase:
    """
    Secure database connection class with SQL injection prevention
    """
    
    def __init__(self, db_path: str):
        """
        Initialize secure database connection
        
        Args:
            db_path (str): Path to the database file
        """
        self.db_path = db_path
        self.conn = None
    
    def __enter__(self):
        """Context manager entry"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable dictionary-like access
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.conn:
            self.conn.close()
    
    def execute_secure_query(
        self, 
        query: str, 
        params: Tuple[Any, ...] = (), 
        fetchall: bool = True
    ) -> Union[List[Dict], Dict, None]:
        """
        Execute a parameterized query securely
        
        Args:
            query (str): SQL query with placeholders
            params (Tuple): Parameters for the query
            fetchall (bool): Whether to fetch all results
            
        Returns:
            Query results as dictionaries or None if error
        """
        if not self.conn:
            raise ValueError("Database connection not established")
        
        try:
            cursor = self.conn.cursor()
            
            # Log query for audit (without parameters for security)
            logger.info(f"Executing secure query: {query}")
            
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                if fetchall:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows] if rows else []
                else:
                    row = cursor.fetchone()
                    return dict(row) if row else None
            else:
                self.conn.commit()
                return cursor.rowcount
                
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if self.conn:
                self.conn.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def get_department_data(self, org_name: str) -> List[Dict]:
        """
        Get department data for an organization securely
        
        Args:
            org_name (str): Organization name
            
        Returns:
            List of department records
        """
        query = """
            SELECT Department, Budget, Actual, (Budget - Actual) as Underspent 
            FROM DepartmentPerformance 
            WHERE Organization = ? 
            ORDER BY Budget DESC
        """
        return self.execute_secure_query(query, (org_name,), fetchall=True)
    
    def get_transaction_data(
        self, 
        department: Optional[str] = None, 
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict]:
        """
        Get transaction data with optional filters
        
        Args:
            department (str, optional): Department filter
            date_from (str, optional): Start date filter
            date_to (str, optional): End date filter
            
        Returns:
            List of transaction records
        """
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if department:
            query += " AND department = ?"
            params.append(department)
        
        if date_from:
            query += " AND transaction_date >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND transaction_date <= ?"
            params.append(date_to)
        
        query += " ORDER BY transaction_date DESC"
        
        return self.execute_secure_query(query, tuple(params), fetchall=True)
    
    def check_table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database
        
        Args:
            table_name (str): Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        # Validate table name to prevent injection
        try:
            safe_table_name = sanitize_sql_identifier(table_name)
        except ValueError as e:
            log_security_event("INVALID_TABLE_NAME", f"Invalid table name: {table_name}")
            return False
        
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_secure_query(query, (safe_table_name,), fetchall=False)
        
        return result is not None
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a table
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            List of column names
        """
        # Validate table name
        try:
            safe_table_name = sanitize_sql_identifier(table_name)
        except ValueError as e:
            log_security_event("INVALID_TABLE_NAME", f"Invalid table name: {table_name}")
            return []
        
        if not self.check_table_exists(safe_table_name):
            return []
        
        # Use PRAGMA to get table info safely
        query = f"PRAGMA table_info({safe_table_name})"
        results = self.execute_secure_query(query, (), fetchall=True)
        
        if results:
            return [row['name'] for row in results]
        return []

def secure_bulk_insert(
    db_path: str, 
    table_name: str, 
    data: List[Dict], 
    validate_data: bool = True
) -> bool:
    """
    Perform secure bulk insert operation
    
    Args:
        db_path (str): Database path
        table_name (str): Target table name
        data (List[Dict]): Data to insert
        validate_data (bool): Whether to validate data before insertion
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not data:
        return True
    
    # Validate table name
    try:
        safe_table_name = sanitize_sql_identifier(table_name)
    except ValueError as e:
        log_security_event("INVALID_TABLE_NAME", f"Invalid table name: {table_name}")
        return False
    
    try:
        with SecureDatabase(db_path) as db:
            # Get table columns
            columns = db.get_table_columns(safe_table_name)
            if not columns:
                logger.error(f"Table {safe_table_name} does not exist or has no columns")
                return False
            
            # Validate data structure
            if validate_data:
                for i, record in enumerate(data):
                    if not isinstance(record, dict):
                        logger.error(f"Record {i} is not a dictionary")
                        return False
                    
                    # Check for required columns
                    missing_cols = set(columns) - set(record.keys())
                    if missing_cols:
                        logger.warning(f"Record {i} missing columns: {missing_cols}")
            
            # Prepare insert query
            placeholders = ', '.join(['?' for _ in columns])
            query = f"INSERT INTO {safe_table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Execute bulk insert
            cursor = db.conn.cursor()
            for record in data:
                values = [record.get(col, None) for col in columns]
                cursor.execute(query, values)
            
            db.conn.commit()
            logger.info(f"Successfully inserted {len(data)} records into {safe_table_name}")
            return True
            
    except Exception as e:
        logger.error(f"Bulk insert error: {e}")
        return False

def secure_data_export(
    db_path: str, 
    table_name: str, 
    filters: Optional[Dict] = None,
    columns: Optional[List[str]] = None
) -> Optional[pd.DataFrame]:
    """
    Export data from database securely as pandas DataFrame
    
    Args:
        db_path (str): Database path
        table_name (str): Table to export from
        filters (Dict, optional): Column filters to apply
        columns (List[str], optional): Specific columns to export
        
    Returns:
        DataFrame or None if error
    """
    try:
        # Validate table name
        safe_table_name = sanitize_sql_identifier(table_name)
    except ValueError as e:
        log_security_event("INVALID_TABLE_NAME", f"Invalid table name: {table_name}")
        return None
    
    try:
        with SecureDatabase(db_path) as db:
            # Check table exists
            if not db.check_table_exists(safe_table_name):
                logger.error(f"Table {safe_table_name} does not exist")
                return None
            
            # Build query
            if columns:
                # Validate column names
                valid_columns = []
                for col in columns:
                    try:
                        valid_columns.append(sanitize_sql_identifier(col))
                    except ValueError:
                        logger.warning(f"Skipping invalid column: {col}")
                
                if not valid_columns:
                    logger.error("No valid columns specified")
                    return None
                
                select_clause = ', '.join(valid_columns)
            else:
                select_clause = '*'
            
            query = f"SELECT {select_clause} FROM {safe_table_name}"
            params = []
            
            # Add filters
            if filters:
                where_conditions = []
                for column, value in filters.items():
                    try:
                        safe_column = sanitize_sql_identifier(column)
                        where_conditions.append(f"{safe_column} = ?")
                        params.append(value)
                    except ValueError:
                        logger.warning(f"Skipping invalid filter column: {column}")
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
            
            # Execute query and return as DataFrame
            results = db.execute_secure_query(query, tuple(params), fetchall=True)
            
            if results:
                return pd.DataFrame(results)
            else:
                return pd.DataFrame()  # Empty DataFrame
                
    except Exception as e:
        logger.error(f"Data export error: {e}")
        return None