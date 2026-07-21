"""
Unit tests for enhanced authentication system
Tests integration with existing admin_panel.py authentication
"""

import pytest
import sys
import os
import tempfile
import csv
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.security.enhanced_auth import (
    EnhancedAuth,
    get_enhanced_auth,
    enhanced_require_login,
    enhanced_require_permission
)
from modules.security.rbac_manager import ResourceType, Permission

class TestEnhancedAuth:
    """Test EnhancedAuth class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_users_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w')
        self.temp_users_file.close()
        
        # Create test users CSV
        with open(self.temp_users_file.name, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Username", "Role", "Departments", "Password", "PasswordHashed", "PasswordHash", "PasswordSalt"])
            writer.writeheader()
            writer.writerow({
                "Username": "test_admin",
                "Role": "admin",
                "Departments": "all",
                "Password": "test123",
                "PasswordHashed": "False",
                "PasswordHash": "",
                "PasswordSalt": ""
            })
            writer.writerow({
                "Username": "test_finance",
                "Role": "finance", 
                "Departments": "all",
                "Password": "finance123",
                "PasswordHashed": "False",
                "PasswordHash": "",
                "PasswordSalt": ""
            })
        
        # Mock the users file path
        with patch('modules.security.enhanced_auth.EnhancedAuth.__init__') as mock_init:
            mock_init.return_value = None
            self.enhanced_auth = EnhancedAuth()
            self.enhanced_auth.users_file = self.temp_users_file.name
            self.enhanced_auth.settings_file = "test_settings.json"
            
            # Mock the dependencies
            self.enhanced_auth.session_manager = Mock()
            self.enhanced_auth.rbac_manager = Mock()
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_users_file.name):
            os.unlink(self.temp_users_file.name)
    
    def test_load_enhanced_users(self):
        """Test loading users with enhanced security data"""
        users = self.enhanced_auth._load_enhanced_users()
        
        assert 'test_admin' in users
        assert 'test_finance' in users
        
        admin_user = users['test_admin']
        assert admin_user['role'] == 'admin'
        assert admin_user['departments'] == 'all'
        assert admin_user['password'] == 'test123'
        assert admin_user['password_hashed'] is False
    
    def test_get_user_permissions(self):
        """Test getting permissions for different roles"""
        admin_perms = self.enhanced_auth._get_user_permissions('admin')
        assert 'admin' in admin_perms
        assert 'read' in admin_perms
        assert 'write' in admin_perms
        
        finance_perms = self.enhanced_auth._get_user_permissions('finance')
        assert 'read' in finance_perms
        assert 'write' in finance_perms
        assert 'export' in finance_perms
        assert 'admin' not in finance_perms
        
        manager_perms = self.enhanced_auth._get_user_permissions('manager')
        assert 'read' in manager_perms
        assert 'write' in manager_perms
        assert 'admin' not in manager_perms
    
    @patch('streamlit.session_state', {})
    def test_enhanced_login_success(self):
        """Test successful enhanced login"""
        # Mock session manager
        self.enhanced_auth.session_manager.create_session.return_value = 'test_session_123'
        
        # Mock Streamlit session state
        import streamlit as st
        st.session_state = {}
        
        result = self.enhanced_auth.enhanced_login(
            username='test_admin',
            password='test123',
            ip_address='192.168.1.100',
            user_agent='TestAgent/1.0'
        )
        
        assert result is True
        assert 'user' in st.session_state
        assert st.session_state['user']['username'] == 'test_admin'
        assert st.session_state['user']['role'] == 'admin'
        assert st.session_state['authenticated'] is True
    
    @patch('streamlit.session_state', {})
    def test_enhanced_login_invalid_user(self):
        """Test login with invalid username"""
        result = self.enhanced_auth.enhanced_login(
            username='invalid_user',
            password='any_password',
            ip_address='192.168.1.100'
        )
        
        assert result is False
        self.enhanced_auth.session_manager.record_failed_attempt.assert_called_with(
            user_id='invalid_user',
            ip_address='192.168.1.100',
            reason='user_not_found'
        )
    
    @patch('streamlit.session_state', {})
    def test_enhanced_login_invalid_password(self):
        """Test login with invalid password"""
        result = self.enhanced_auth.enhanced_login(
            username='test_admin',
            password='wrong_password',
            ip_address='192.168.1.100'
        )
        
        assert result is False
        self.enhanced_auth.session_manager.record_failed_attempt.assert_called_with(
            user_id='test_admin',
            ip_address='192.168.1.100',
            reason='invalid_password'
        )
    
    @patch('streamlit.session_state', {})
    def test_enhanced_login_session_creation_failure(self):
        """Test login when session creation fails"""
        # Mock session creation failure
        self.enhanced_auth.session_manager.create_session.return_value = None
        
        result = self.enhanced_auth.enhanced_login(
            username='test_admin',
            password='test123',
            ip_address='192.168.1.100'
        )
        
        assert result is False
        self.enhanced_auth.session_manager.record_failed_attempt.assert_called_with(
            user_id='test_admin',
            ip_address='192.168.1.100',
            reason='session_creation_failed'
        )
    
    @patch('streamlit.session_state', {'user': {'session_id': 'test_session_123', 'username': 'test_user'}})
    def test_validate_session_success(self):
        """Test successful session validation"""
        # Mock successful session validation
        mock_session = Mock()
        self.enhanced_auth.session_manager.validate_session.return_value = mock_session
        
        result = self.enhanced_auth.validate_session('test_session_123')
        assert result is True
    
    @patch('streamlit.session_state', {'user': {'session_id': 'invalid_session'}})
    def test_validate_session_failure(self):
        """Test failed session validation"""
        # Mock failed session validation
        self.enhanced_auth.session_manager.validate_session.return_value = None
        
        import streamlit as st
        st.session_state = {'user': {'session_id': 'invalid_session'}, 'authenticated': True}
        
        result = self.enhanced_auth.validate_session('invalid_session')
        assert result is False
        
        # Check that session state is cleared
        assert 'user' not in st.session_state
        assert 'authenticated' not in st.session_state
    
    @patch('streamlit.session_state', {'user': {'session_id': 'test_session_123', 'username': 'test_user'}})
    def test_enhanced_logout(self):
        """Test enhanced logout"""
        import streamlit as st
        st.session_state = {
            'user': {'session_id': 'test_session_123', 'username': 'test_user'},
            'authenticated': True
        }
        
        self.enhanced_auth.enhanced_logout('user_logout')
        
        # Verify session termination was called
        self.enhanced_auth.session_manager.terminate_session.assert_called_with(
            'test_session_123', 'user_logout'
        )
        
        # Verify session state is cleared
        assert 'user' not in st.session_state
        assert 'authenticated' not in st.session_state
    
    @patch('streamlit.session_state', {'user': {'username': 'test_admin', 'departments': 'all'}})
    def test_check_resource_permission(self):
        """Test resource permission checking"""
        # Mock RBAC manager permission check
        self.enhanced_auth.rbac_manager.check_permission.return_value = True
        
        result = self.enhanced_auth.check_resource_permission(
            ResourceType.BUDGET_DATA,
            Permission.READ
        )
        
        assert result is True
        self.enhanced_auth.rbac_manager.check_permission.assert_called_once()
    
    @patch('streamlit.session_state', {'user': {'username': 'test_manager', 'departments': ['Police', 'Fire']}})
    def test_check_resource_permission_with_department_context(self):
        """Test resource permission checking with department context"""
        # Mock RBAC manager permission check
        self.enhanced_auth.rbac_manager.check_permission.return_value = True
        
        result = self.enhanced_auth.check_resource_permission(
            ResourceType.DEPARTMENT_DATA,
            Permission.WRITE,
            context={'department': 'Police'}
        )
        
        assert result is True
        
        # Verify department context was added
        call_args = self.enhanced_auth.rbac_manager.check_permission.call_args
        context = call_args[1]['context']
        assert 'departments' in context
        assert context['departments'] == ['Police', 'Fire']
    
    def test_save_enhanced_users(self):
        """Test saving users with enhanced security data"""
        users = {
            'test_user': {
                'role': 'admin',
                'departments': 'all',
                'password_hashed': True,
                'password_hash': 'hashed_password',
                'password_salt': 'salt_value'
            }
        }
        
        self.enhanced_auth._save_enhanced_users(users)
        
        # Verify file was written correctly
        with open(self.enhanced_auth.users_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        assert len(rows) == 1
        assert rows[0]['Username'] == 'test_user'
        assert rows[0]['Role'] == 'admin'
        assert rows[0]['PasswordHashed'] == 'True'
        assert rows[0]['PasswordHash'] == 'hashed_password'
        assert rows[0]['PasswordSalt'] == 'salt_value'
    
    def test_get_default_users(self):
        """Test getting default users"""
        default_users = self.enhanced_auth._get_default_users()
        
        assert 'admin_user' in default_users
        assert 'finance_director' in default_users
        assert 'pw_manager' in default_users
        
        admin_user = default_users['admin_user']
        assert admin_user['role'] == 'admin'
        assert admin_user['departments'] == 'all'
        assert admin_user['password_hashed'] is False


class TestGlobalEnhancedAuth:
    """Test global enhanced auth functions"""
    
    def test_get_enhanced_auth_singleton(self):
        """Test that get_enhanced_auth returns singleton"""
        with patch('modules.security.enhanced_auth.EnhancedAuth'):
            auth1 = get_enhanced_auth()
            auth2 = get_enhanced_auth()
            assert auth1 is auth2
    
    @patch('streamlit.session_state', {'authenticated': True})
    @patch('modules.security.enhanced_auth.get_enhanced_auth')
    def test_enhanced_require_login_success(self, mock_get_auth):
        """Test enhanced login requirement when authenticated"""
        mock_auth = Mock()
        mock_auth.validate_session.return_value = True
        mock_get_auth.return_value = mock_auth
        
        result = enhanced_require_login()
        assert result is True
    
    @patch('streamlit.session_state', {})
    def test_enhanced_require_login_failure(self):
        """Test enhanced login requirement when not authenticated"""
        result = enhanced_require_login()
        assert result is False
    
    @patch('streamlit.session_state', {'authenticated': True})
    @patch('modules.security.enhanced_auth.get_enhanced_auth')
    def test_enhanced_require_permission_decorator(self, mock_get_auth):
        """Test enhanced permission requirement decorator"""
        mock_auth = Mock()
        mock_auth.validate_session.return_value = True
        mock_auth.check_resource_permission.return_value = True
        mock_get_auth.return_value = mock_auth
        
        @enhanced_require_permission(ResourceType.BUDGET_DATA, Permission.READ)
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"


if __name__ == "__main__":
    pytest.main(["-v", __file__])