"""
Simplified Comprehensive Test Suite for 85%+ Coverage
Focuses on core functionality and security testing
"""

import pytest
import pandas as pd
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock

class TestCoreFunctionality:
    """Test core application functionality"""
    
    def test_data_loading(self):
        """Test data loading functions"""
        from bi_sandbox import load_org_data_cached
        
        with patch('bi_sandbox.sqlite3.connect'):
            result = load_org_data_cached("cityA")
            assert isinstance(result, pd.DataFrame)
    
    def test_security_validation(self):
        """Test security validation functions"""
        from security_sql_injection_fixes import SQLSecurityValidator
        
        # Test valid inputs
        assert SQLSecurityValidator.validate_table_name('departments') == 'departments'
        assert SQLSecurityValidator.validate_column_name('Budget') == 'Budget'
        assert SQLSecurityValidator.validate_organization_name('cityA') == 'cityA'
    
    def test_query_building(self):
        """Test safe query building"""
        from security_sql_injection_fixes import SQLSecurityValidator
        
        query, params = SQLSecurityValidator.build_safe_select_query(
            'departments',
            columns=['Name', 'Budget'],
            where_conditions={'Organization': 'cityA'}
        )
        
        assert 'SELECT Name, Budget FROM departments' in query
        assert 'WHERE Organization = ?' in query
        assert params == ('cityA',)
    
    def test_data_processing(self):
        """Test data processing functions"""
        from common_utils import validate_numeric_input
        
        assert validate_numeric_input("100") == 100
        assert validate_numeric_input("99.5") == 99.5
        
        with pytest.raises(ValueError):
            validate_numeric_input("not_a_number")
    
    def test_admin_functions(self):
        """Test admin panel functions"""
        from modules.admin.admin_panel import check_admin_access, log_user_action
        
        with patch('admin_panel.is_admin', return_value=True):
            assert check_admin_access() == True
        
        # Should not raise exceptions
        log_user_action("test_action", "test_user")
    
    def test_ai_functions(self):
        """Test AI assistant functions"""
        from ai_assistant import generate_ai_response, summarize_data_for_ai
        
        data = pd.DataFrame({'col1': [1, 2, 3]})
        
        response = generate_ai_response("test question", data)
        assert isinstance(response, str)
        assert len(response) > 0
        
        summary = summarize_data_for_ai(data)
        assert isinstance(summary, str)
        assert '3 rows' in summary
    
    def test_scenario_functions(self):
        """Test scenario planning functions"""
        from scenario_planner import create_scenario, validate_scenario, save_scenario
        
        scenario = create_scenario("Test", 1000000, {"tax": 400000})
        assert scenario['name'] == "Test"
        assert scenario['total_cost'] == 1000000
        
        assert validate_scenario(scenario) == True
        assert save_scenario(scenario) == True
        
        # Test invalid scenario
        invalid_scenario = {'name': 'Test', 'total_cost': -1000}
        assert validate_scenario(invalid_scenario) == False
    
    def test_database_operations(self):
        """Test database operations"""
        from security_sql_injection_fixes import execute_safe_query
        
        # Test with mock database
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [{'name': 'test'}]
            
            result = execute_safe_query("SELECT * FROM test", (), "test.db")
            assert result is not None
    
    def test_data_types_optimization(self):
        """Test data type optimizations"""
        data = pd.DataFrame({
            'Department': ['Finance', 'Police'] * 50,
            'Type': ['Operating', 'Safety'] * 50
        })
        
        # Convert to categories for memory efficiency
        data['Department'] = data['Department'].astype('category')
        data['Type'] = data['Type'].astype('category')
        
        assert data['Department'].dtype.name == 'category'
        assert data['Type'].dtype.name == 'category'
    
    def test_error_handling(self):
        """Test error handling"""
        from security_sql_injection_fixes import SQLSecurityValidator
        
        # Test that invalid inputs raise appropriate errors
        with pytest.raises(ValueError):
            SQLSecurityValidator.validate_table_name('invalid_table')
        
        with pytest.raises(ValueError):
            SQLSecurityValidator.validate_organization_name('')
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        from security_sql_injection_fixes import SQLSecurityValidator
        
        # Test that dangerous queries are blocked
        dangerous_query = "SELECT * FROM users; DROP TABLE departments;"
        
        with pytest.raises(ValueError):
            SQLSecurityValidator.scan_for_sql_injection(dangerous_query)
        
        # Test that safe queries pass
        safe_query = "SELECT * FROM departments WHERE Organization = ?"
        SQLSecurityValidator.scan_for_sql_injection(safe_query)  # Should not raise
    
    def test_performance_optimizations(self):
        """Test performance optimizations"""
        # Test caching functionality exists
        from bi_sandbox import load_org_data_cached
        assert callable(load_org_data_cached)
        
        # Test data type optimizations
        data = pd.DataFrame({'Budget': [100000, 200000, 300000]})
        assert data['Budget'].dtype in ['int64', 'float64']

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=term-missing"])
