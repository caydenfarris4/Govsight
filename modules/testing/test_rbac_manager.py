"""
Unit tests for RBAC manager
Tests role-based access control functionality
"""

import pytest
import sys
import os
import tempfile
import sqlite3
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.security.rbac_manager import (
    RBACManager,
    ResourceType,
    Permission,
    Role,
    UserRole,
    get_rbac_manager,
    require_permission
)

class TestRBACManager:
    """Test RBACManager class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.rbac_manager = RBACManager(db_file=self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test RBAC database initialization"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check tables exist
        tables = ['roles', 'user_roles', 'permission_cache', 'resource_access_log']
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_default_roles_created(self):
        """Test that default roles are created"""
        # Check admin role exists
        admin_role = self.rbac_manager.get_role('admin')
        assert admin_role is not None
        assert admin_role.role_name == 'Administrator'
        assert admin_role.is_active is True
        
        # Check finance role exists
        finance_role = self.rbac_manager.get_role('finance')
        assert finance_role is not None
        assert finance_role.role_name == 'Finance Director'
        
        # Check manager role exists
        manager_role = self.rbac_manager.get_role('manager')
        assert manager_role is not None
        assert manager_role.role_name == 'Department Manager'
    
    def test_create_custom_role(self):
        """Test creating a custom role"""
        result = self.rbac_manager.create_role(
            role_id='test_analyst',
            role_name='Test Analyst',
            description='Test role for analysts',
            permissions={
                ResourceType.BUDGET_DATA.value: [Permission.READ],
                ResourceType.FINANCIAL_REPORTS.value: [Permission.READ, Permission.EXPORT]
            }
        )
        
        assert result is True
        
        # Verify role was created
        role = self.rbac_manager.get_role('test_analyst')
        assert role is not None
        assert role.role_name == 'Test Analyst'
        assert ResourceType.BUDGET_DATA in role.permissions
        assert Permission.READ in role.permissions[ResourceType.BUDGET_DATA]
    
    def test_assign_role_to_user(self):
        """Test assigning role to user"""
        user_id = 'test_user'
        role_id = 'admin'
        granted_by = 'system_admin'
        
        result = self.rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id=role_id,
            granted_by=granted_by
        )
        
        assert result is True
        
        # Verify role assignment
        user_roles = self.rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 1
        assert user_roles[0]['role_id'] == role_id
        assert user_roles[0]['granted_by'] == granted_by
    
    def test_check_permission_admin_role(self):
        """Test permission checking for admin role"""
        user_id = 'admin_user'
        
        # Assign admin role
        self.rbac_manager.assign_role_to_user(user_id, 'admin', 'system')
        
        # Admin should have all permissions
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        ) is True
        
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.USER_MANAGEMENT, Permission.ADMIN
        ) is True
        
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.AUDIT_LOGS, Permission.AUDIT
        ) is True
    
    def test_check_permission_finance_role(self):
        """Test permission checking for finance role"""
        user_id = 'finance_user'
        
        # Assign finance role
        self.rbac_manager.assign_role_to_user(user_id, 'finance', 'admin')
        
        # Finance should have specific permissions
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        ) is True
        
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.WRITE
        ) is True
        
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.FINANCIAL_REPORTS, Permission.EXPORT
        ) is True
        
        # Finance should NOT have admin permissions
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.USER_MANAGEMENT, Permission.ADMIN
        ) is False
    
    def test_check_permission_manager_role(self):
        """Test permission checking for manager role"""
        user_id = 'manager_user'
        
        # Assign manager role
        self.rbac_manager.assign_role_to_user(user_id, 'manager', 'admin')
        
        # Manager should have limited permissions
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        ) is True
        
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.DEPARTMENT_DATA, Permission.WRITE
        ) is True
        
        # Manager should NOT have admin or approval permissions
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.APPROVE
        ) is False
        
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.USER_MANAGEMENT, Permission.ADMIN
        ) is False
    
    def test_check_permission_no_role(self):
        """Test permission checking for user with no role"""
        user_id = 'no_role_user'
        
        # User with no role should have no permissions
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        ) is False
        
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.FINANCIAL_REPORTS, Permission.READ
        ) is False
    
    def test_scope_restrictions_department(self):
        """Test scope restrictions for department access"""
        user_id = 'dept_manager'
        
        # Assign manager role with department restrictions
        self.rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id='manager',
            granted_by='admin',
            scope_restrictions={
                'departments': ['Police', 'Fire']
            }
        )
        
        # Should have access to allowed departments
        assert self.rbac_manager.check_permission(
            user_id, 
            ResourceType.DEPARTMENT_DATA, 
            Permission.READ,
            context={'department': 'Police'}
        ) is True
        
        assert self.rbac_manager.check_permission(
            user_id, 
            ResourceType.DEPARTMENT_DATA, 
            Permission.READ,
            context={'department': 'Fire'}
        ) is True
        
        # Should NOT have access to restricted departments
        assert self.rbac_manager.check_permission(
            user_id, 
            ResourceType.DEPARTMENT_DATA, 
            Permission.READ,
            context={'department': 'Parks'}
        ) is False
    
    def test_permission_caching(self):
        """Test permission result caching"""
        user_id = 'cache_test_user'
        
        # Assign role
        self.rbac_manager.assign_role_to_user(user_id, 'finance', 'admin')
        
        # First permission check (should be calculated)
        result1 = self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        )
        assert result1 is True
        
        # Second permission check (should use cache)
        result2 = self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        )
        assert result2 is True
        
        # Verify cache entry exists
        cached_result = self.rbac_manager._get_cached_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        )
        assert cached_result is True
    
    def test_resource_access_logging(self):
        """Test resource access logging"""
        user_id = 'logging_test_user'
        
        # Assign role
        self.rbac_manager.assign_role_to_user(user_id, 'admin', 'system')
        
        # Perform permission check (which logs access)
        self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        )
        
        # Check that access was logged
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM resource_access_log 
            WHERE user_id = ? AND resource_type = ?
        """, (user_id, ResourceType.BUDGET_DATA.value))
        
        count = cursor.fetchone()[0]
        assert count >= 1
        conn.close()
    
    def test_role_expiry(self):
        """Test role assignment expiry"""
        user_id = 'expiry_test_user'
        
        # Assign role with expiry in the past
        past_time = datetime.now() - timedelta(hours=1)
        self.rbac_manager.assign_role_to_user(
            user_id=user_id,
            role_id='finance',
            granted_by='admin',
            expires_at=past_time
        )
        
        # Should have no permissions due to expiry
        assert self.rbac_manager.check_permission(
            user_id, ResourceType.BUDGET_DATA, Permission.READ
        ) is False
        
        # User should have no active roles
        user_roles = self.rbac_manager.get_user_roles(user_id)
        assert len(user_roles) == 0


class TestEnumTypes:
    """Test ResourceType and Permission enums"""
    
    def test_resource_types_exist(self):
        """Test that all required resource types exist"""
        required_types = [
            'BUDGET_DATA', 'DEPARTMENT_DATA', 'FINANCIAL_REPORTS',
            'USER_MANAGEMENT', 'SYSTEM_SETTINGS', 'AUDIT_LOGS',
            'SCENARIO_PLANNING', 'BI_SANDBOX', 'HISTORICAL_ANALYSIS',
            'ADMIN_PANEL', 'DATA_EXPORT', 'API_ACCESS'
        ]
        
        for resource_type in required_types:
            assert hasattr(ResourceType, resource_type)
            assert isinstance(getattr(ResourceType, resource_type), ResourceType)
    
    def test_permissions_exist(self):
        """Test that all required permissions exist"""
        required_permissions = [
            'READ', 'WRITE', 'DELETE', 'EXECUTE', 'ADMIN',
            'EXPORT', 'IMPORT', 'APPROVE', 'AUDIT'
        ]
        
        for permission in required_permissions:
            assert hasattr(Permission, permission)
            assert isinstance(getattr(Permission, permission), Permission)


class TestGlobalRBACManager:
    """Test global RBAC manager function"""
    
    def test_get_rbac_manager_singleton(self):
        """Test that get_rbac_manager returns singleton"""
        manager1 = get_rbac_manager()
        manager2 = get_rbac_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, RBACManager)


class TestRequirePermissionDecorator:
    """Test require_permission decorator"""
    
    @patch('modules.security.rbac_manager.get_rbac_manager')
    def test_require_permission_decorator_success(self, mock_get_manager):
        """Test decorator with sufficient permissions"""
        mock_manager = Mock()
        mock_manager.check_permission.return_value = True
        mock_get_manager.return_value = mock_manager
        
        @require_permission(ResourceType.BUDGET_DATA, Permission.READ)
        def test_function(user_id='test_user'):
            return "success"
        
        result = test_function(user_id='test_user')
        assert result == "success"
        mock_manager.check_permission.assert_called_once()
    
    @patch('modules.security.rbac_manager.get_rbac_manager')
    def test_require_permission_decorator_failure(self, mock_get_manager):
        """Test decorator with insufficient permissions"""
        mock_manager = Mock()
        mock_manager.check_permission.return_value = False
        mock_get_manager.return_value = mock_manager
        
        @require_permission(ResourceType.BUDGET_DATA, Permission.ADMIN)
        def test_function(user_id='test_user'):
            return "success"
        
        with pytest.raises(PermissionError):
            test_function(user_id='test_user')


if __name__ == "__main__":
    pytest.main(["-v", __file__])