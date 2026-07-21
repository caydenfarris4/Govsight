"""
Audit Integration Helper
Utilities to retrofit existing database operations with audit trail functionality

ARCHITECTURAL DECISION: Helper functions for gradual audit integration
WHY: Allows existing code to be gradually updated with audit trails without
breaking existing functionality. Provides backward compatibility.
"""

import functools
import pandas as pd
from typing import Dict, Any, Optional, Callable
from modules.database.audit_trail_manager import safe_delete_with_audit, audit_manager
import streamlit as st

def get_current_user_context() -> Dict[str, str]:
    """
    Extract user context from Streamlit session for audit trail
    
    Returns:
        Dictionary with user_id, user_role, session_id
    """
    user = st.session_state.get('user', {})
    
    return {
        'user_id': user.get('username', 'unknown'),
        'user_role': user.get('role', 'unknown'), 
        'session_id': st.session_state.get('session_id', 'unknown'),
        'reason': 'System operation'
    }

def audit_delete_decorator(database_name: str, table_name: str):
    """
    Decorator to automatically add audit trail to delete functions
    
    Usage:
        @audit_delete_decorator("gl_primary", "transactions")
        def delete_old_transactions(cutoff_date):
            # Function that performs delete operation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get user context
            user_context = get_current_user_context()
            user_context['reason'] = f"Operation: {func.__name__}"
            
            # Call original function with audit trail
            try:
                result = func(*args, **kwargs)
                
                # If function returns delete query, intercept and audit
                if isinstance(result, str) and 'DELETE' in result.upper():
                    return safe_delete_with_audit(
                        database_name=database_name,
                        table_name=table_name,
                        delete_query=result,
                        user_context=user_context
                    )
                
                return result
                
            except Exception as e:
                st.error(f"Error in {func.__name__}: {e}")
                return {"success": False, "error": str(e)}
        
        return wrapper
    return decorator

def manual_audit_log(database_name: str, table_name: str, 
                    deleted_data: pd.DataFrame, delete_criteria: str,
                    operation_reason: str = None) -> int:
    """
    Manually log a delete operation to audit trail
    
    Args:
        database_name: Name of the database
        table_name: Table where deletion occurred
        deleted_data: DataFrame of deleted records
        delete_criteria: Description of what was deleted
        operation_reason: Reason for deletion
        
    Returns:
        audit_id: ID of created audit record
    """
    user_context = get_current_user_context()
    if operation_reason:
        user_context['reason'] = operation_reason
    
    return audit_manager.log_delete_operation(
        database_name=database_name,
        table_name=table_name,
        delete_criteria=delete_criteria,
        deleted_data=deleted_data,
        user_id=user_context['user_id'],
        user_role=user_context['user_role'],
        session_id=user_context['session_id'],
        operation_reason=user_context['reason']
    )

def audit_aware_delete(connection, delete_query: str, 
                      database_name: str = "gl_primary",
                      table_name: str = None,
                      operation_reason: str = None) -> Dict[str, Any]:
    """
    Execute a delete with automatic audit trail
    
    Args:
        connection: Database connection object
        delete_query: DELETE SQL statement
        database_name: Name of database
        table_name: Table name (auto-extracted if None)
        operation_reason: Reason for deletion
        
    Returns:
        Result dictionary with audit information
    """
    
    # Extract table name from query if not provided
    if not table_name:
        import re
        match = re.search(r'DELETE\s+FROM\s+(\w+)', delete_query, re.IGNORECASE)
        if match:
            table_name = match.group(1)
        else:
            table_name = "unknown_table"
    
    # Get user context
    user_context = get_current_user_context()
    if operation_reason:
        user_context['reason'] = operation_reason
    
    # Use the safe delete function
    return safe_delete_with_audit(
        database_name=database_name,
        table_name=table_name,
        delete_query=delete_query,
        user_context=user_context
    )

class AuditAwareDBManager:
    """
    Database manager with built-in audit trail support
    
    Drop-in replacement for direct database operations
    """
    
    def __init__(self, database_name: str = "gl_primary"):
        self.database_name = database_name
        
    def safe_delete(self, table_name: str, where_clause: str, 
                   operation_reason: str = None) -> Dict[str, Any]:
        """
        Safely delete records with audit trail
        
        Args:
            table_name: Table to delete from
            where_clause: WHERE condition (without WHERE keyword)
            operation_reason: Reason for deletion
            
        Returns:
            Operation result with audit information
        """
        delete_query = f"DELETE FROM {table_name} WHERE {where_clause}"
        
        user_context = get_current_user_context()
        if operation_reason:
            user_context['reason'] = operation_reason
        
        return safe_delete_with_audit(
            database_name=self.database_name,
            table_name=table_name,
            delete_query=delete_query,
            user_context=user_context
        )
    
    def get_audit_history(self, table_name: str = None, 
                         days: int = 30) -> pd.DataFrame:
        """Get audit history for this database"""
        return audit_manager.get_audit_trail(
            database_name=self.database_name,
            table_name=table_name,
            start_date=(pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d'),
            end_date=pd.Timestamp.now().strftime('%Y-%m-%d')
        )

# Convenience instance for GL database
gl_audit_manager = AuditAwareDBManager("gl_primary")

# Helper function for retrofitting existing code
def retrofit_delete_with_audit(original_delete_func: Callable,
                              database_name: str,
                              table_name: str) -> Callable:
    """
    Retrofit an existing delete function with audit trail
    
    Usage:
        old_delete = delete_records
        delete_records = retrofit_delete_with_audit(old_delete, "gl_primary", "transactions")
    """
    
    @functools.wraps(original_delete_func)
    def audited_wrapper(*args, **kwargs):
        # Capture data before deletion
        try:
            # Get connection and capture data
            from modules.database.connection_manager import get_database_connection
            conn = get_database_connection(database_name)
            
            # Try to capture data before deletion
            # This is a best-effort approach
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1000")  # Safety limit
            columns = [description[0] for description in cursor.description]
            
            # Call original function
            result = original_delete_func(*args, **kwargs)
            
            # Log the operation
            user_context = get_current_user_context()
            user_context['reason'] = f"Legacy operation: {original_delete_func.__name__}"
            
            audit_manager.log_delete_operation(
                database_name=database_name,
                table_name=table_name,
                delete_criteria=f"Legacy delete via {original_delete_func.__name__}",
                deleted_data=pd.DataFrame(columns=columns),  # Empty dataframe with structure
                user_id=user_context['user_id'],
                user_role=user_context['user_role'],
                session_id=user_context['session_id'],
                operation_reason=user_context['reason']
            )
            
            conn.close()
            return result
            
        except Exception as e:
            st.warning(f"Could not fully audit delete operation: {e}")
            # Still call original function if audit fails
            return original_delete_func(*args, **kwargs)
    
    return audited_wrapper

# Example usage patterns for documentation
"""
USAGE EXAMPLES:

1. Simple decorator approach:
    @audit_delete_decorator("gl_primary", "transactions")
    def cleanup_old_transactions():
        return "DELETE FROM transactions WHERE date < '2020-01-01'"

2. Manual audit logging:
    deleted_records = pd.read_sql("SELECT * FROM accounts WHERE status='closed'", conn)
    cursor.execute("DELETE FROM accounts WHERE status='closed'")
    audit_id = manual_audit_log("gl_primary", "accounts", deleted_records, "status='closed'")

3. Audit-aware manager:
    db_manager = AuditAwareDBManager("gl_primary")
    result = db_manager.safe_delete("transactions", "amount < 0.01", "Cleanup tiny amounts")

4. Retrofit existing function:
    old_delete = existing_delete_function
    existing_delete_function = retrofit_delete_with_audit(old_delete, "gl_primary", "ledger")

5. Direct safe delete:
    result = audit_aware_delete(conn, "DELETE FROM ledger WHERE year < 2020", 
                               operation_reason="Annual cleanup")
"""