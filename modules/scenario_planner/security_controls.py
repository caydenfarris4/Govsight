"""
Scenario Planner Security Controls

Implements security controls for scenario planning operations including
approval workflows, budget limit validation, and scenario access control.
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from modules.security import (
    get_enhanced_auth, ResourceType, Permission, SecurityEventType,
    ThreatLevel, log_security_event, validate_numeric_input
)

class ScenarioSecurityManager:
    """Security manager for scenario planning operations"""
    
    def __init__(self):
        self.auth = get_enhanced_auth()
        self.max_budget_variance = 0.25  # 25% variance limit
        self.approval_thresholds = {
            'manager': 100000,    # $100K
            'finance': 1000000,   # $1M
            'admin': float('inf') # No limit
        }
    
    def check_scenario_access(self, scenario_id: str = None, operation: str = 'read') -> bool:
        """Check if user has access to scenario operations"""
        permission_map = {
            'read': Permission.READ,
            'write': Permission.WRITE,
            'execute': Permission.EXECUTE,
            'approve': Permission.APPROVE
        }
        
        permission = permission_map.get(operation, Permission.READ)
        
        return self.auth.check_resource_permission(
            ResourceType.SCENARIO_PLANNING,
            permission
        )
    
    def validate_budget_allocation(self, allocation_data: Dict[str, float], total_budget: float) -> Tuple[bool, str]:
        """Validate budget allocation for security and business rules"""
        try:
            # Validate all numeric inputs
            for dept, amount in allocation_data.items():
                validate_numeric_input(amount, min_value=0, max_value=total_budget)
            
            # Check total allocation doesn't exceed budget
            total_allocated = sum(allocation_data.values())
            if total_allocated > total_budget * (1 + self.max_budget_variance):
                return False, f"Total allocation (${total_allocated:,.2f}) exceeds budget by more than {self.max_budget_variance*100}%"
            
            # Check user's approval authority
            user_role = st.session_state.get('user', {}).get('role', '')
            approval_limit = self.approval_thresholds.get(user_role, 0)
            
            if total_allocated > approval_limit:
                return False, f"Budget amount requires higher authorization level (limit: ${approval_limit:,.2f})"
            
            return True, "Budget allocation validated"
            
        except ValueError as e:
            self._log_validation_error('budget_allocation', str(e))
            return False, f"Invalid budget data: {e}"
    
    def validate_scenario_parameters(self, scenario_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate scenario parameters for security"""
        try:
            required_fields = ['name', 'description', 'department_allocations']
            
            # Check required fields
            for field in required_fields:
                if field not in scenario_data:
                    return False, f"Missing required field: {field}"
            
            # Validate scenario name
            name = scenario_data['name']
            if len(name) > 100:
                return False, "Scenario name too long (max 100 characters)"
            
            if any(char in name for char in ['<', '>', '"', "'", '&']):
                return False, "Scenario name contains invalid characters"
            
            # Validate description
            description = scenario_data.get('description', '')
            if len(description) > 1000:
                return False, "Description too long (max 1000 characters)"
            
            # Validate department allocations
            allocations = scenario_data.get('department_allocations', {})
            if not isinstance(allocations, dict):
                return False, "Department allocations must be a dictionary"
            
            total_budget = scenario_data.get('total_budget', 0)
            if total_budget <= 0:
                return False, "Total budget must be positive"
            
            is_valid, message = self.validate_budget_allocation(allocations, total_budget)
            if not is_valid:
                return False, message
            
            return True, "Scenario parameters validated"
            
        except Exception as e:
            self._log_validation_error('scenario_parameters', str(e))
            return False, f"Validation error: {e}"
    
    def require_approval(self, scenario_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if scenario requires approval workflow"""
        try:
            total_budget = scenario_data.get('total_budget', 0)
            user_role = st.session_state.get('user', {}).get('role', '')
            
            # Get user's direct approval limit
            user_limit = self.approval_thresholds.get(user_role, 0)
            
            if total_budget <= user_limit:
                return False, "Scenario within user's approval authority"
            
            # Determine required approval level
            if total_budget <= self.approval_thresholds['finance']:
                required_role = 'finance'
            else:
                required_role = 'admin'
            
            self._log_approval_required(scenario_data, required_role)
            
            return True, f"Scenario requires approval from {required_role} role (budget: ${total_budget:,.2f})"
            
        except Exception as e:
            return True, f"Approval check error: {e}"
    
    def log_scenario_operation(self, operation: str, scenario_data: Dict[str, Any], success: bool = True):
        """Log scenario operations for audit trail"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        
        event_type = SecurityEventType.ADMIN_ACTION if operation in ['create', 'approve'] else SecurityEventType.DATA_EXPORT
        threat_level = ThreatLevel.LOW if success else ThreatLevel.MEDIUM
        
        log_security_event(
            event_type,
            threat_level,
            user_id=username,
            event_details={
                'operation': operation,
                'scenario_name': scenario_data.get('name', 'unnamed'),
                'total_budget': scenario_data.get('total_budget', 0),
                'departments': list(scenario_data.get('department_allocations', {}).keys()),
                'success': success,
                'module': 'scenario_planner'
            },
            source_module='scenario_security',
            action_taken=f'scenario_{operation}_logged'
        )
    
    def validate_what_if_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate what-if analysis parameters"""
        try:
            # Validate percentage changes
            if 'percentage_changes' in parameters:
                changes = parameters['percentage_changes']
                for dept, change in changes.items():
                    if not isinstance(change, (int, float)):
                        return False, f"Invalid percentage change for {dept}"
                    
                    if abs(change) > 50:  # 50% change limit
                        return False, f"Percentage change for {dept} exceeds 50% limit"
            
            # Validate time horizon
            if 'time_horizon' in parameters:
                horizon = parameters['time_horizon']
                if not isinstance(horizon, int) or horizon < 1 or horizon > 10:
                    return False, "Time horizon must be between 1 and 10 years"
            
            return True, "What-if parameters validated"
            
        except Exception as e:
            return False, f"Parameter validation error: {e}"
    
    def check_data_sensitivity(self, scenario_data: Dict[str, Any]) -> str:
        """Classify scenario data sensitivity level"""
        total_budget = scenario_data.get('total_budget', 0)
        department_count = len(scenario_data.get('department_allocations', {}))
        
        if total_budget > 10000000 or department_count > 10:  # $10M or 10+ departments
            return "HIGH"
        elif total_budget > 1000000 or department_count > 5:   # $1M or 5+ departments
            return "MEDIUM"
        else:
            return "LOW"
    
    def _log_validation_error(self, validation_type: str, error_details: str):
        """Log validation errors"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        
        log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            ThreatLevel.MEDIUM,
            user_id=username,
            event_details={
                'validation_type': validation_type,
                'error': error_details,
                'module': 'scenario_planner'
            },
            source_module='scenario_security',
            action_taken='validation_error_logged'
        )
    
    def _log_approval_required(self, scenario_data: Dict[str, Any], required_role: str):
        """Log when approval is required"""
        username = st.session_state.get('user', {}).get('username', 'unknown')
        
        log_security_event(
            SecurityEventType.ADMIN_ACTION,
            ThreatLevel.LOW,
            user_id=username,
            event_details={
                'action': 'approval_required',
                'scenario_name': scenario_data.get('name', 'unnamed'),
                'total_budget': scenario_data.get('total_budget', 0),
                'required_role': required_role,
                'module': 'scenario_planner'
            },
            source_module='scenario_security',
            action_taken='approval_workflow_triggered'
        )

def secure_scenario_creation(scenario_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Securely create a scenario with validation and approval workflow"""
    security_manager = ScenarioSecurityManager()
    
    # Check permissions
    if not security_manager.check_scenario_access(operation='write'):
        return False, "Insufficient permissions to create scenarios", {}
    
    # Validate scenario data
    is_valid, validation_message = security_manager.validate_scenario_parameters(scenario_data)
    if not is_valid:
        security_manager.log_scenario_operation('create', scenario_data, success=False)
        return False, validation_message, {}
    
    # Check approval requirements
    needs_approval, approval_message = security_manager.require_approval(scenario_data)
    
    # Add security metadata
    enhanced_scenario_data = scenario_data.copy()
    enhanced_scenario_data.update({
        'created_by': st.session_state.get('user', {}).get('username', 'unknown'),
        'created_at': datetime.now().isoformat(),
        'sensitivity_level': security_manager.check_data_sensitivity(scenario_data),
        'requires_approval': needs_approval,
        'approval_status': 'pending' if needs_approval else 'approved',
        'approval_required_role': approval_message.split()[-1] if needs_approval else None
    })
    
    # Log successful creation
    security_manager.log_scenario_operation('create', enhanced_scenario_data, success=True)
    
    return True, "Scenario created successfully" + (f" - {approval_message}" if needs_approval else ""), enhanced_scenario_data

def secure_what_if_analysis(base_scenario: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """Perform what-if analysis with security controls"""
    security_manager = ScenarioSecurityManager()
    
    # Check permissions
    if not security_manager.check_scenario_access(operation='execute'):
        return False, "Insufficient permissions to run what-if analysis", {}
    
    # Validate parameters
    is_valid, validation_message = security_manager.validate_what_if_parameters(parameters)
    if not is_valid:
        return False, validation_message, {}
    
    # Log analysis execution
    username = st.session_state.get('user', {}).get('username', 'unknown')
    log_security_event(
        SecurityEventType.DATA_EXPORT,
        ThreatLevel.LOW,
        user_id=username,
        event_details={
            'operation': 'what_if_analysis',
            'base_scenario': base_scenario.get('name', 'unnamed'),
            'parameters': parameters,
            'module': 'scenario_planner'
        },
        source_module='scenario_security',
        action_taken='what_if_analysis_executed'
    )
    
    # Perform analysis (integrate with existing what-if logic)
    analysis_results = {
        'analysis_id': f"whatif_{datetime.now().timestamp()}",
        'base_scenario': base_scenario,
        'parameters': parameters,
        'executed_by': username,
        'executed_at': datetime.now().isoformat(),
        'sensitivity_level': security_manager.check_data_sensitivity(base_scenario)
    }
    
    return True, "What-if analysis completed successfully", analysis_results