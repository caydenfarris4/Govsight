"""
Unit tests for scenario planner security controls
Tests budget validation, approval workflows, and access controls
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import patch, Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.scenario_planner.security_controls import (
    ScenarioSecurityManager,
    secure_scenario_creation,
    secure_what_if_analysis
)
from modules.security import ResourceType, Permission

class TestScenarioSecurityManager:
    """Test ScenarioSecurityManager class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.security_manager = ScenarioSecurityManager()
        
        # Mock enhanced auth
        self.security_manager.auth = Mock()
    
    def test_check_scenario_access_read(self):
        """Test scenario access check for read operation"""
        self.security_manager.auth.check_resource_permission.return_value = True
        
        result = self.security_manager.check_scenario_access(operation='read')
        
        assert result is True
        self.security_manager.auth.check_resource_permission.assert_called_with(
            ResourceType.SCENARIO_PLANNING,
            Permission.READ
        )
    
    def test_check_scenario_access_write(self):
        """Test scenario access check for write operation"""
        self.security_manager.auth.check_resource_permission.return_value = True
        
        result = self.security_manager.check_scenario_access(operation='write')
        
        assert result is True
        self.security_manager.auth.check_resource_permission.assert_called_with(
            ResourceType.SCENARIO_PLANNING,
            Permission.WRITE
        )
    
    def test_validate_budget_allocation_success(self):
        """Test successful budget allocation validation"""
        allocation_data = {
            'Police': 500000,
            'Fire': 300000,
            'Parks': 200000
        }
        total_budget = 1000000
        
        with patch('streamlit.session_state', {'user': {'role': 'admin'}}):
            is_valid, message = self.security_manager.validate_budget_allocation(allocation_data, total_budget)
        
        assert is_valid is True
        assert "validated" in message
    
    def test_validate_budget_allocation_exceeds_budget(self):
        """Test budget allocation validation when exceeding budget"""
        allocation_data = {
            'Police': 600000,
            'Fire': 400000,
            'Parks': 300000  # Total: 1,300,000
        }
        total_budget = 1000000  # 30% over budget (exceeds 25% variance limit)
        
        with patch('streamlit.session_state', {'user': {'role': 'admin'}}):
            is_valid, message = self.security_manager.validate_budget_allocation(allocation_data, total_budget)
        
        assert is_valid is False
        assert "exceeds budget" in message
    
    def test_validate_budget_allocation_exceeds_authority(self):
        """Test budget allocation validation when exceeding user authority"""
        allocation_data = {
            'Police': 1500000  # $1.5M
        }
        total_budget = 1500000
        
        with patch('streamlit.session_state', {'user': {'role': 'manager'}}):
            is_valid, message = self.security_manager.validate_budget_allocation(allocation_data, total_budget)
        
        assert is_valid is False
        assert "requires higher authorization" in message
    
    def test_validate_scenario_parameters_success(self):
        """Test successful scenario parameter validation"""
        scenario_data = {
            'name': 'Test Scenario',
            'description': 'A test scenario for validation',
            'department_allocations': {
                'Police': 500000,
                'Fire': 300000
            },
            'total_budget': 800000
        }
        
        with patch('streamlit.session_state', {'user': {'role': 'admin'}}):
            is_valid, message = self.security_manager.validate_scenario_parameters(scenario_data)
        
        assert is_valid is True
        assert "validated" in message
    
    def test_validate_scenario_parameters_missing_fields(self):
        """Test scenario parameter validation with missing required fields"""
        scenario_data = {
            'name': 'Test Scenario'
            # Missing description and department_allocations
        }
        
        is_valid, message = self.security_manager.validate_scenario_parameters(scenario_data)
        
        assert is_valid is False
        assert "Missing required field" in message
    
    def test_validate_scenario_parameters_invalid_name(self):
        """Test scenario parameter validation with invalid name"""
        scenario_data = {
            'name': 'Test <script>alert("xss")</script> Scenario',  # Contains dangerous characters
            'description': 'A test scenario',
            'department_allocations': {'Police': 500000},
            'total_budget': 500000
        }
        
        is_valid, message = self.security_manager.validate_scenario_parameters(scenario_data)
        
        assert is_valid is False
        assert "invalid characters" in message
    
    def test_validate_scenario_parameters_long_name(self):
        """Test scenario parameter validation with overly long name"""
        scenario_data = {
            'name': 'A' * 101,  # 101 characters (exceeds 100 limit)
            'description': 'A test scenario',
            'department_allocations': {'Police': 500000},
            'total_budget': 500000
        }
        
        is_valid, message = self.security_manager.validate_scenario_parameters(scenario_data)
        
        assert is_valid is False
        assert "too long" in message
    
    def test_require_approval_within_authority(self):
        """Test approval requirement when within user authority"""
        scenario_data = {
            'total_budget': 50000  # Within manager limit
        }
        
        with patch('streamlit.session_state', {'user': {'role': 'manager'}}):
            needs_approval, message = self.security_manager.require_approval(scenario_data)
        
        assert needs_approval is False
        assert "within user's approval authority" in message
    
    def test_require_approval_exceeds_authority(self):
        """Test approval requirement when exceeding user authority"""
        scenario_data = {
            'total_budget': 500000  # Exceeds manager limit of $100K
        }
        
        with patch('streamlit.session_state', {'user': {'role': 'manager'}}):
            needs_approval, message = self.security_manager.require_approval(scenario_data)
        
        assert needs_approval is True
        assert "requires approval from finance" in message
    
    def test_require_approval_very_high_budget(self):
        """Test approval requirement for very high budget requiring admin"""
        scenario_data = {
            'total_budget': 5000000  # $5M exceeds finance limit
        }
        
        with patch('streamlit.session_state', {'user': {'role': 'finance'}}):
            needs_approval, message = self.security_manager.require_approval(scenario_data)
        
        assert needs_approval is True
        assert "requires approval from admin" in message
    
    def test_validate_what_if_parameters_success(self):
        """Test successful what-if parameter validation"""
        parameters = {
            'percentage_changes': {
                'Police': 10.0,
                'Fire': -5.0,
                'Parks': 15.0
            },
            'time_horizon': 3
        }
        
        is_valid, message = self.security_manager.validate_what_if_parameters(parameters)
        
        assert is_valid is True
        assert "validated" in message
    
    def test_validate_what_if_parameters_excessive_change(self):
        """Test what-if parameter validation with excessive percentage change"""
        parameters = {
            'percentage_changes': {
                'Police': 60.0  # Exceeds 50% limit
            },
            'time_horizon': 3
        }
        
        is_valid, message = self.security_manager.validate_what_if_parameters(parameters)
        
        assert is_valid is False
        assert "exceeds 50% limit" in message
    
    def test_validate_what_if_parameters_invalid_horizon(self):
        """Test what-if parameter validation with invalid time horizon"""
        parameters = {
            'percentage_changes': {'Police': 10.0},
            'time_horizon': 15  # Exceeds 10 year limit
        }
        
        is_valid, message = self.security_manager.validate_what_if_parameters(parameters)
        
        assert is_valid is False
        assert "between 1 and 10 years" in message
    
    def test_check_data_sensitivity_high(self):
        """Test data sensitivity classification for high sensitivity"""
        scenario_data = {
            'total_budget': 15000000,  # $15M
            'department_allocations': {f'Dept{i}': 1000000 for i in range(12)}  # 12 departments
        }
        
        sensitivity = self.security_manager.check_data_sensitivity(scenario_data)
        assert sensitivity == "HIGH"
    
    def test_check_data_sensitivity_medium(self):
        """Test data sensitivity classification for medium sensitivity"""
        scenario_data = {
            'total_budget': 2000000,  # $2M
            'department_allocations': {f'Dept{i}': 300000 for i in range(6)}  # 6 departments
        }
        
        sensitivity = self.security_manager.check_data_sensitivity(scenario_data)
        assert sensitivity == "MEDIUM"
    
    def test_check_data_sensitivity_low(self):
        """Test data sensitivity classification for low sensitivity"""
        scenario_data = {
            'total_budget': 500000,  # $500K
            'department_allocations': {'Police': 300000, 'Fire': 200000}  # 2 departments
        }
        
        sensitivity = self.security_manager.check_data_sensitivity(scenario_data)
        assert sensitivity == "LOW"


class TestSecureScenarioCreation:
    """Test secure_scenario_creation function"""
    
    @patch('modules.scenario_planner.security_controls.ScenarioSecurityManager')
    @patch('streamlit.session_state', {'user': {'username': 'test_user'}})
    def test_secure_scenario_creation_success(self, mock_security_manager_class):
        """Test successful secure scenario creation"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_scenario_access.return_value = True
        mock_security_manager.validate_scenario_parameters.return_value = (True, "Validated")
        mock_security_manager.require_approval.return_value = (False, "Within authority")
        mock_security_manager.check_data_sensitivity.return_value = "LOW"
        mock_security_manager_class.return_value = mock_security_manager
        
        scenario_data = {
            'name': 'Test Scenario',
            'description': 'Test description',
            'department_allocations': {'Police': 500000},
            'total_budget': 500000
        }
        
        success, message, enhanced_data = secure_scenario_creation(scenario_data)
        
        assert success is True
        assert "created successfully" in message
        assert 'created_by' in enhanced_data
        assert 'sensitivity_level' in enhanced_data
        assert enhanced_data['approval_status'] == 'approved'
    
    @patch('modules.scenario_planner.security_controls.ScenarioSecurityManager')
    def test_secure_scenario_creation_permission_denied(self, mock_security_manager_class):
        """Test scenario creation with insufficient permissions"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_scenario_access.return_value = False
        mock_security_manager_class.return_value = mock_security_manager
        
        scenario_data = {'name': 'Test Scenario'}
        
        success, message, enhanced_data = secure_scenario_creation(scenario_data)
        
        assert success is False
        assert "Insufficient permissions" in message
        assert enhanced_data == {}
    
    @patch('modules.scenario_planner.security_controls.ScenarioSecurityManager')
    def test_secure_scenario_creation_validation_failed(self, mock_security_manager_class):
        """Test scenario creation with validation failure"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_scenario_access.return_value = True
        mock_security_manager.validate_scenario_parameters.return_value = (False, "Validation failed")
        mock_security_manager_class.return_value = mock_security_manager
        
        scenario_data = {'name': 'Invalid Scenario'}
        
        success, message, enhanced_data = secure_scenario_creation(scenario_data)
        
        assert success is False
        assert "Validation failed" in message
        assert enhanced_data == {}
    
    @patch('modules.scenario_planner.security_controls.ScenarioSecurityManager')
    @patch('streamlit.session_state', {'user': {'username': 'test_user'}})
    def test_secure_scenario_creation_requires_approval(self, mock_security_manager_class):
        """Test scenario creation that requires approval"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_scenario_access.return_value = True
        mock_security_manager.validate_scenario_parameters.return_value = (True, "Validated")
        mock_security_manager.require_approval.return_value = (True, "Scenario requires approval from finance role")
        mock_security_manager.check_data_sensitivity.return_value = "MEDIUM"
        mock_security_manager_class.return_value = mock_security_manager
        
        scenario_data = {
            'name': 'High Budget Scenario',
            'total_budget': 2000000
        }
        
        success, message, enhanced_data = secure_scenario_creation(scenario_data)
        
        assert success is True
        assert "requires approval from finance" in message
        assert enhanced_data['approval_status'] == 'pending'
        assert enhanced_data['requires_approval'] is True


class TestSecureWhatIfAnalysis:
    """Test secure_what_if_analysis function"""
    
    @patch('modules.scenario_planner.security_controls.ScenarioSecurityManager')
    @patch('modules.scenario_planner.security_controls.log_security_event')
    @patch('streamlit.session_state', {'user': {'username': 'test_analyst'}})
    def test_secure_what_if_analysis_success(self, mock_log_security_event, mock_security_manager_class):
        """Test successful what-if analysis"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_scenario_access.return_value = True
        mock_security_manager.validate_what_if_parameters.return_value = (True, "Parameters validated")
        mock_security_manager.check_data_sensitivity.return_value = "LOW"
        mock_security_manager_class.return_value = mock_security_manager
        
        base_scenario = {
            'name': 'Base Scenario',
            'total_budget': 1000000
        }
        
        parameters = {
            'percentage_changes': {'Police': 10.0, 'Fire': -5.0},
            'time_horizon': 3
        }
        
        success, message, results = secure_what_if_analysis(base_scenario, parameters)
        
        assert success is True
        assert "completed successfully" in message
        assert 'analysis_id' in results
        assert 'executed_by' in results
        assert results['executed_by'] == 'test_analyst'
        mock_log_security_event.assert_called_once()
    
    @patch('modules.scenario_planner.security_controls.ScenarioSecurityManager')
    def test_secure_what_if_analysis_permission_denied(self, mock_security_manager_class):
        """Test what-if analysis with insufficient permissions"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_scenario_access.return_value = False
        mock_security_manager_class.return_value = mock_security_manager
        
        base_scenario = {'name': 'Base Scenario'}
        parameters = {'percentage_changes': {'Police': 10.0}}
        
        success, message, results = secure_what_if_analysis(base_scenario, parameters)
        
        assert success is False
        assert "Insufficient permissions" in message
        assert results == {}
    
    @patch('modules.scenario_planner.security_controls.ScenarioSecurityManager')
    def test_secure_what_if_analysis_invalid_parameters(self, mock_security_manager_class):
        """Test what-if analysis with invalid parameters"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_scenario_access.return_value = True
        mock_security_manager.validate_what_if_parameters.return_value = (False, "Invalid parameters")
        mock_security_manager_class.return_value = mock_security_manager
        
        base_scenario = {'name': 'Base Scenario'}
        parameters = {'percentage_changes': {'Police': 60.0}}  # Exceeds limit
        
        success, message, results = secure_what_if_analysis(base_scenario, parameters)
        
        assert success is False
        assert "Invalid parameters" in message
        assert results == {}


if __name__ == "__main__":
    pytest.main(["-v", __file__])