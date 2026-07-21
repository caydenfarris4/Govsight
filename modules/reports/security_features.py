"""
Report Generation Security Features

Implements security controls for report generation including access logging,
watermarking, and distribution restrictions.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from modules.security import (
    get_enhanced_auth, ResourceType, Permission, SecurityEventType,
    ThreatLevel, log_security_event
)

class ReportSecurityManager:
    """Security manager for report operations"""
    
    def __init__(self):
        self.auth = get_enhanced_auth()
        self.confidentiality_levels = {
            'PUBLIC': 0,
            'INTERNAL': 1, 
            'CONFIDENTIAL': 2,
            'RESTRICTED': 3
        }
    
    def check_report_access(self, report_type: str, confidentiality: str = 'INTERNAL') -> bool:
        """Check if user has access to generate specific report types"""
        # Map report types to required permissions
        report_permissions = {
            'budget_summary': Permission.READ,
            'financial_analysis': Permission.READ,
            'audit_report': Permission.AUDIT,
            'executive_summary': Permission.APPROVE,
            'departmental_breakdown': Permission.READ
        }
        
        required_permission = report_permissions.get(report_type, Permission.READ)
        
        # Check base permission
        has_permission = self.auth.check_resource_permission(
            ResourceType.FINANCIAL_REPORTS,
            required_permission
        )
        
        if not has_permission:
            return False
        
        # Check confidentiality level access
        user_role = st.session_state.get('user', {}).get('role', '')
        user_clearance = self._get_user_clearance_level(user_role)
        required_clearance = self.confidentiality_levels.get(confidentiality, 1)
        
        return user_clearance >= required_clearance
    
    def _get_user_clearance_level(self, role: str) -> int:
        """Get user's security clearance level"""
        clearance_map = {
            'admin': 3,     # RESTRICTED
            'finance': 2,   # CONFIDENTIAL  
            'manager': 1,   # INTERNAL
            'viewer': 0     # PUBLIC
        }
        return clearance_map.get(role, 0)
    
    def add_security_watermark(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add security watermark and metadata to reports"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        user_role = st.session_state.get('user', {}).get('role', 'unknown')
        
        watermark_data = {
            'generated_by': username,
            'user_role': user_role,
            'generation_time': datetime.now().isoformat(),
            'report_id': f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{username}",
            'security_classification': report_data.get('confidentiality', 'INTERNAL'),
            'distribution_restriction': self._get_distribution_restriction(user_role)
        }
        
        enhanced_report = report_data.copy()
        enhanced_report['security_metadata'] = watermark_data
        
        return enhanced_report
    
    def _get_distribution_restriction(self, role: str) -> str:
        """Get distribution restrictions based on user role"""
        restrictions = {
            'admin': 'UNRESTRICTED',
            'finance': 'DEPARTMENT_HEADS_ONLY',
            'manager': 'INTERNAL_USE_ONLY',
            'viewer': 'PERSONAL_USE_ONLY'
        }
        return restrictions.get(role, 'PERSONAL_USE_ONLY')
    
    def log_report_generation(self, report_type: str, report_data: Dict[str, Any]):
        """Log report generation for audit purposes"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        
        log_security_event(
            SecurityEventType.DATA_EXPORT,
            ThreatLevel.LOW,
            user_id=username,
            event_details={
                'operation': 'report_generation',
                'report_type': report_type,
                'report_id': report_data.get('security_metadata', {}).get('report_id'),
                'confidentiality': report_data.get('confidentiality', 'INTERNAL'),
                'data_points': len(report_data.get('data', [])),
                'module': 'reports'
            },
            source_module='report_security',
            action_taken='report_generated'
        )
    
    def validate_report_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, str]:
        """Validate report generation parameters"""
        try:
            # Check date ranges
            if 'date_from' in parameters and 'date_to' in parameters:
                from datetime import datetime
                date_from = datetime.fromisoformat(parameters['date_from'])
                date_to = datetime.fromisoformat(parameters['date_to'])
                
                if date_to < date_from:
                    return False, "End date cannot be before start date"
                
                # Limit historical data access
                max_history_days = 365 * 3  # 3 years
                if (datetime.now() - date_from).days > max_history_days:
                    return False, f"Historical data limited to {max_history_days} days"
            
            # Validate department filters
            if 'departments' in parameters:
                user_departments = st.session_state.get('user', {}).get('departments')
                if user_departments != 'all' and isinstance(user_departments, list):
                    requested_departments = parameters['departments']
                    unauthorized_depts = set(requested_departments) - set(user_departments)
                    if unauthorized_depts:
                        return False, f"Access denied to departments: {', '.join(unauthorized_depts)}"
            
            return True, "Parameters validated"
            
        except Exception as e:
            return False, f"Parameter validation error: {e}"

def secure_report_generator(report_type: str, parameters: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
    """Generate reports with comprehensive security controls"""
    security_manager = ReportSecurityManager()
    
    # Check access permissions
    confidentiality = parameters.get('confidentiality', 'INTERNAL')
    if not security_manager.check_report_access(report_type, confidentiality):
        return False, "Insufficient permissions to generate this report", {}
    
    # Validate parameters
    is_valid, validation_message = security_manager.validate_report_parameters(parameters)
    if not is_valid:
        return False, validation_message, {}
    
    # Generate report (integrate with existing report generation logic)
    try:
        report_data = {
            'report_type': report_type,
            'parameters': parameters,
            'confidentiality': confidentiality,
            'data': []  # This would be populated by actual report logic
        }
        
        # Add security watermark
        secured_report = security_manager.add_security_watermark(report_data)
        
        # Log generation
        security_manager.log_report_generation(report_type, secured_report)
        
        return True, "Report generated successfully", secured_report
        
    except Exception as e:
        log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            ThreatLevel.MEDIUM,
            event_details={'error': str(e), 'operation': 'report_generation'},
            source_module='report_security',
            action_taken='report_generation_failed'
        )
        return False, f"Report generation failed: {e}", {}

def secure_report_export(report_data: Dict[str, Any], export_format: str = 'pdf') -> bool:
    """Export reports with security controls"""
    security_manager = ReportSecurityManager()
    
    # Check export permissions
    if not security_manager.auth.check_resource_permission(ResourceType.DATA_EXPORT, Permission.EXPORT):
        st.error("Insufficient permissions to export reports")
        return False
    
    # Add export metadata
    export_metadata = {
        'exported_at': datetime.now().isoformat(),
        'export_format': export_format,
        'exported_by': st.session_state.get('user', {}).get('username', 'unknown')
    }
    
    report_data['export_metadata'] = export_metadata
    
    # Log export
    username = st.session_state.get('user', {}).get('username', 'unknown')
    log_security_event(
        SecurityEventType.DATA_EXPORT,
        ThreatLevel.LOW,
        user_id=username,
        event_details={
            'operation': 'report_export',
            'report_id': report_data.get('security_metadata', {}).get('report_id'),
            'export_format': export_format,
            'module': 'reports'
        },
        source_module='report_security',
        action_taken='report_exported'
    )
    
    return True