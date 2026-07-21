"""
Unit tests for BI Sandbox security integration
Tests data access controls, export restrictions, and query validation
"""

import pytest
import sys
import os
import pandas as pd
from unittest.mock import patch, Mock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.bi_sandbox.security_integration import (
    BiSecurityManager,
    secure_data_loader,
    secure_chart_builder,
    secure_data_export
)
from modules.security import ResourceType, Permission

class TestBiSecurityManager:
    """Test BiSecurityManager class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.security_manager = BiSecurityManager()
        
        # Mock enhanced auth
        self.security_manager.auth = Mock()
    
    def test_check_data_access_permission_success(self):
        """Test successful data access permission check"""
        self.security_manager.auth.check_resource_permission.return_value = True
        
        result = self.security_manager.check_data_access_permission('budget_data', 'Police')
        
        assert result is True
        self.security_manager.auth.check_resource_permission.assert_called_with(
            ResourceType.BI_SANDBOX,
            Permission.READ,
            context={'department': 'Police'}
        )
    
    def test_check_data_access_permission_failure(self):
        """Test failed data access permission check"""
        self.security_manager.auth.check_resource_permission.return_value = False
        
        result = self.security_manager.check_data_access_permission('budget_data')
        
        assert result is False
    
    def test_check_export_permission(self):
        """Test export permission checking"""
        self.security_manager.auth.check_resource_permission.return_value = True
        
        result = self.security_manager.check_export_permission('csv')
        
        assert result is True
        self.security_manager.auth.check_resource_permission.assert_called_with(
            ResourceType.DATA_EXPORT,
            Permission.EXPORT
        )
    
    @patch('streamlit.session_state', {'user': {'role': 'manager'}})
    def test_filter_sensitive_data_manager_role(self):
        """Test sensitive data filtering for manager role"""
        # Create test dataframe with sensitive columns
        df = pd.DataFrame({
            'department': ['Police', 'Fire'],
            'budget': [1000000, 800000],
            'salary': [50000, 45000],  # Sensitive
            'employee_id': [123, 456]  # Sensitive
        })
        
        filtered_df = self.security_manager.filter_sensitive_data(df)
        
        # Should remove sensitive columns
        assert 'salary' not in filtered_df.columns
        assert 'employee_id' not in filtered_df.columns
        assert 'department' in filtered_df.columns
        assert 'budget' in filtered_df.columns
    
    @patch('streamlit.session_state', {'user': {'role': 'admin'}})
    def test_filter_sensitive_data_admin_role(self):
        """Test sensitive data filtering for admin role"""
        # Create test dataframe with sensitive columns
        df = pd.DataFrame({
            'department': ['Police', 'Fire'],
            'budget': [1000000, 800000],
            'salary': [50000, 45000],  # Sensitive
            'employee_id': [123, 456]  # Sensitive
        })
        
        filtered_df = self.security_manager.filter_sensitive_data(df)
        
        # Admin should see all columns
        assert 'salary' in filtered_df.columns
        assert 'employee_id' in filtered_df.columns
        assert 'department' in filtered_df.columns
        assert 'budget' in filtered_df.columns
    
    def test_validate_chart_query_success(self):
        """Test successful chart query validation"""
        query_params = {
            'chart_type': 'bar',
            'x_axis': 'department',
            'y_axis': 'budget',
            'title': 'Department Budgets'
        }
        
        result = self.security_manager.validate_chart_query(query_params)
        assert result is True
    
    def test_validate_chart_query_failure(self):
        """Test chart query validation with malicious input"""
        query_params = {
            'chart_type': 'bar',
            'x_axis': 'department',
            'y_axis': "budget'; DROP TABLE users; --",  # SQL injection attempt
            'title': 'Department Budgets'
        }
        
        result = self.security_manager.validate_chart_query(query_params)
        assert result is False
    
    @patch('modules.bi_sandbox.security_integration.log_security_event')
    @patch('streamlit.session_state', {'user': {'username': 'test_user'}})
    def test_log_data_access(self, mock_log_security_event):
        """Test data access logging"""
        self.security_manager.log_data_access('read', 'budget_data', 100)
        
        mock_log_security_event.assert_called_once()
        call_args = mock_log_security_event.call_args
        
        assert call_args[1]['user_id'] == 'test_user'
        assert call_args[1]['event_details']['operation'] == 'read'
        assert call_args[1]['event_details']['data_source'] == 'budget_data'
        assert call_args[1]['event_details']['records_accessed'] == 100


class TestSecureDataLoader:
    """Test secure_data_loader function"""
    
    @patch('modules.bi_sandbox.security_integration.BiSecurityManager')
    @patch('modules.database.execute_query')
    def test_secure_data_loader_success(self, mock_execute_query, mock_security_manager_class):
        """Test successful secure data loading"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_data_access_permission.return_value = True
        mock_security_manager.filter_sensitive_data.return_value = pd.DataFrame({'dept': ['Police'], 'budget': [1000000]})
        mock_security_manager_class.return_value = mock_security_manager
        
        # Mock database query
        mock_execute_query.return_value = pd.DataFrame({'dept': ['Police'], 'budget': [1000000], 'salary': [50000]})
        
        result = secure_data_loader('budget_data', {'department': 'Police'})
        
        assert not result.empty
        mock_security_manager.check_data_access_permission.assert_called_with('budget_data', 'Police')
        mock_security_manager.filter_sensitive_data.assert_called_once()
        mock_security_manager.log_data_access.assert_called_with('read', 'budget_data', 1)
    
    @patch('modules.bi_sandbox.security_integration.BiSecurityManager')
    @patch('streamlit.error')
    def test_secure_data_loader_permission_denied(self, mock_st_error, mock_security_manager_class):
        """Test secure data loading with insufficient permissions"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_data_access_permission.return_value = False
        mock_security_manager_class.return_value = mock_security_manager
        
        result = secure_data_loader('budget_data')
        
        assert result.empty
        mock_st_error.assert_called_with("Insufficient permissions to access this data")


class TestSecureChartBuilder:
    """Test secure_chart_builder function"""
    
    @patch('modules.bi_sandbox.security_integration.BiSecurityManager')
    @patch('modules.bi_sandbox.security_integration.log_security_event')
    @patch('streamlit.session_state', {'user': {'username': 'test_user'}})
    def test_secure_chart_builder_success(self, mock_log_security_event, mock_security_manager_class):
        """Test successful secure chart building"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.validate_chart_query.return_value = True
        mock_security_manager.auth.check_resource_permission.return_value = True
        mock_security_manager_class.return_value = mock_security_manager
        
        test_data = pd.DataFrame({'dept': ['Police'], 'budget': [1000000]})
        config = {'x_axis': 'dept', 'y_axis': 'budget'}
        
        result = secure_chart_builder('bar', test_data, config)
        
        assert result is True
        mock_security_manager.validate_chart_query.assert_called_with(config)
        mock_log_security_event.assert_called_once()
    
    @patch('modules.bi_sandbox.security_integration.BiSecurityManager')
    @patch('streamlit.error')
    def test_secure_chart_builder_invalid_config(self, mock_st_error, mock_security_manager_class):
        """Test chart building with invalid configuration"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.validate_chart_query.return_value = False
        mock_security_manager_class.return_value = mock_security_manager
        
        test_data = pd.DataFrame({'dept': ['Police'], 'budget': [1000000]})
        config = {'x_axis': 'dept', 'y_axis': "'; DROP TABLE users; --"}
        
        result = secure_chart_builder('bar', test_data, config)
        
        assert result is False
        mock_st_error.assert_called_with("Invalid chart configuration detected")
    
    @patch('modules.bi_sandbox.security_integration.BiSecurityManager')
    @patch('streamlit.error')
    def test_secure_chart_builder_insufficient_permissions(self, mock_st_error, mock_security_manager_class):
        """Test chart building with insufficient permissions"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.validate_chart_query.return_value = True
        mock_security_manager.auth.check_resource_permission.return_value = False
        mock_security_manager_class.return_value = mock_security_manager
        
        test_data = pd.DataFrame({'dept': ['Police'], 'budget': [1000000]})
        config = {'x_axis': 'dept', 'y_axis': 'budget'}
        
        result = secure_chart_builder('bar', test_data, config)
        
        assert result is False
        mock_st_error.assert_called_with("Insufficient permissions to create charts")


class TestSecureDataExport:
    """Test secure_data_export function"""
    
    @patch('modules.bi_sandbox.security_integration.BiSecurityManager')
    @patch('streamlit.download_button')
    def test_secure_data_export_success(self, mock_download_button, mock_security_manager_class):
        """Test successful secure data export"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_export_permission.return_value = True
        mock_security_manager.filter_sensitive_data.return_value = pd.DataFrame({'dept': ['Police'], 'budget': [1000000]})
        mock_security_manager_class.return_value = mock_security_manager
        
        test_data = pd.DataFrame({'dept': ['Police'], 'budget': [1000000], 'salary': [50000]})
        
        result = secure_data_export(test_data, 'csv', 'test_export.csv')
        
        assert result is True
        mock_security_manager.check_export_permission.assert_called_with('csv')
        mock_security_manager.filter_sensitive_data.assert_called_once()
        mock_security_manager.log_data_access.assert_called_with('export', 'test_export.csv', 1)
        mock_download_button.assert_called_once()
    
    @patch('modules.bi_sandbox.security_integration.BiSecurityManager')
    @patch('streamlit.error')
    def test_secure_data_export_permission_denied(self, mock_st_error, mock_security_manager_class):
        """Test data export with insufficient permissions"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.check_export_permission.return_value = False
        mock_security_manager_class.return_value = mock_security_manager
        
        test_data = pd.DataFrame({'dept': ['Police'], 'budget': [1000000]})
        
        result = secure_data_export(test_data, 'csv')
        
        assert result is False
        mock_st_error.assert_called_with("Insufficient permissions to export data")


if __name__ == "__main__":
    pytest.main(["-v", __file__])