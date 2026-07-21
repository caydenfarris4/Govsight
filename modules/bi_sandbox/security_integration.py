"""
BI Sandbox Security Integration

Adds advanced security controls to the BI Sandbox module including
data access logging, export restrictions, and query validation.
"""

import pandas as pd
import streamlit as st
from typing import Dict, Any, List, Optional
from modules.security import (
    get_enhanced_auth, ResourceType, Permission, SecurityEventType, 
    ThreatLevel, log_security_event, validate_and_sanitize_input
)

class BiSecurityManager:
    """Security manager for BI Sandbox operations"""
    
    def __init__(self):
        self.auth = get_enhanced_auth()
        self.sensitive_columns = {
            'salary', 'wages', 'compensation', 'bonus', 'ssn', 'social_security',
            'tax_id', 'account_number', 'routing_number', 'employee_id'
        }
    
    def check_data_access_permission(self, data_type: str, department: str = None) -> bool:
        """Check if user has permission to access specific data"""
        context = {}
        if department:
            context['department'] = department
        
        return self.auth.check_resource_permission(
            ResourceType.BI_SANDBOX,
            Permission.READ,
            context=context
        )
    
    def check_export_permission(self, format_type: str = "csv") -> bool:
        """Check if user has export permissions"""
        return self.auth.check_resource_permission(
            ResourceType.DATA_EXPORT,
            Permission.EXPORT
        )
    
    def filter_sensitive_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out sensitive columns based on user role"""
        if not df.empty:
            user_role = st.session_state.get('user', {}).get('role', '')
            
            # Admin and finance can see all data
            if user_role in ['admin', 'finance']:
                return df
            
            # Remove sensitive columns for other roles
            columns_to_remove = []
            for col in df.columns:
                if any(sensitive in col.lower() for sensitive in self.sensitive_columns):
                    columns_to_remove.append(col)
            
            if columns_to_remove:
                df = df.drop(columns=columns_to_remove)
                self._log_data_filtering(columns_to_remove)
        
        return df
    
    def validate_chart_query(self, query_params: Dict[str, Any]) -> bool:
        """Validate chart query parameters for security"""
        try:
            # Check for SQL injection patterns in string parameters
            for key, value in query_params.items():
                if isinstance(value, str):
                    validate_and_sanitize_input(value, max_length=500)
            
            return True
            
        except ValueError as e:
            self._log_security_violation("chart_query_validation", str(e))
            return False
    
    def log_data_access(self, operation: str, data_source: str, records_accessed: int = 0):
        """Log data access for audit purposes"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        
        log_security_event(
            SecurityEventType.DATA_EXPORT if operation == 'export' else SecurityEventType.UNAUTHORIZED_ACCESS,
            ThreatLevel.LOW,
            user_id=username,
            event_details={
                'operation': operation,
                'data_source': data_source,
                'records_accessed': records_accessed,
                'module': 'bi_sandbox'
            },
            source_module='bi_sandbox_security',
            action_taken=f'data_{operation}_logged'
        )
    
    def _log_data_filtering(self, filtered_columns: List[str]):
        """Log when sensitive data is filtered"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        
        log_security_event(
            SecurityEventType.DATA_EXPORT,
            ThreatLevel.LOW,
            user_id=username,
            event_details={
                'action': 'sensitive_data_filtered',
                'filtered_columns': filtered_columns,
                'module': 'bi_sandbox'
            },
            source_module='bi_sandbox_security',
            action_taken='sensitive_data_protected'
        )
    
    def _log_security_violation(self, violation_type: str, details: str):
        """Log security violations"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        
        log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            ThreatLevel.MEDIUM,
            user_id=username,
            event_details={
                'violation_type': violation_type,
                'details': details,
                'module': 'bi_sandbox'
            },
            source_module='bi_sandbox_security',
            action_taken='security_violation_blocked'
        )

def secure_data_loader(data_source: str, filters: Dict[str, Any] = None) -> pd.DataFrame:
    """Securely load data with access controls and logging"""
    security_manager = BiSecurityManager()
    
    # Check permissions
    department = filters.get('department') if filters else None
    if not security_manager.check_data_access_permission(data_source, department):
        st.error("Insufficient permissions to access this data")
        return pd.DataFrame()
    
    # Load data (placeholder - integrate with actual data loading)
    try:
        # This would integrate with your existing data loading logic
        from modules.database import execute_query
        
        # Build secure query
        query = f"SELECT * FROM {data_source}"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if value:
                    conditions.append(f"{key} = ?")
                    params.append(value)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        # Execute with security validation
        df = execute_query(query, tuple(params))
        
        if df is not None and not df.empty:
            # Filter sensitive data
            df = security_manager.filter_sensitive_data(df)
            
            # Log access
            security_manager.log_data_access('read', data_source, len(df))
        
        return df
        
    except Exception as e:
        security_manager._log_security_violation('data_loading_error', str(e))
        st.error("Error loading data")
        return pd.DataFrame()

def secure_chart_builder(chart_type: str, data: pd.DataFrame, config: Dict[str, Any]) -> bool:
    """Build charts with security validation"""
    security_manager = BiSecurityManager()
    
    # Validate chart configuration
    if not security_manager.validate_chart_query(config):
        st.error("Invalid chart configuration detected")
        return False
    
    # Check if user can execute charts
    if not security_manager.auth.check_resource_permission(ResourceType.BI_SANDBOX, Permission.EXECUTE):
        st.error("Insufficient permissions to create charts")
        return False
    
    # Log chart creation
    username = st.session_state.get('user', {}).get('username', 'unknown')
    log_security_event(
        SecurityEventType.DATA_EXPORT,
        ThreatLevel.LOW,
        user_id=username,
        event_details={
            'action': 'chart_created',
            'chart_type': chart_type,
            'data_records': len(data),
            'module': 'bi_sandbox'
        },
        source_module='bi_sandbox_security',
        action_taken='chart_creation_logged'
    )
    
    return True

def secure_data_export(data: pd.DataFrame, format_type: str = "csv", filename: str = None) -> bool:
    """Securely export data with permission checks and logging"""
    security_manager = BiSecurityManager()
    
    # Check export permissions
    if not security_manager.check_export_permission(format_type):
        st.error("Insufficient permissions to export data")
        return False
    
    # Filter sensitive data before export
    filtered_data = security_manager.filter_sensitive_data(data.copy())
    
    # Log export
    security_manager.log_data_access('export', filename or 'unnamed_export', len(filtered_data))
    
    # Perform export (integrate with existing export logic)
    try:
        if format_type.lower() == 'csv':
            csv_data = filtered_data.to_csv(index=False)
            st.download_button(
                label="Download Filtered Data",
                data=csv_data,
                file_name=filename or "exported_data.csv",
                mime="text/csv"
            )
        
        return True
        
    except Exception as e:
        security_manager._log_security_violation('export_error', str(e))
        return False