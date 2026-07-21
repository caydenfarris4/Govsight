"""
Role-Based Access Control (RBAC) Manager

This module provides comprehensive role-based access control with fine-grained
permissions, resource-level security, and dynamic policy enforcement.
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from .audit_logger import SecurityEventType, ThreatLevel, log_security_event

class ResourceType(Enum):
    """Types of resources that can be protected"""
    BUDGET_DATA = "budget_data"
    DEPARTMENT_DATA = "department_data"
    FINANCIAL_REPORTS = "financial_reports"
    USER_MANAGEMENT = "user_management"
    SYSTEM_SETTINGS = "system_settings"
    AUDIT_LOGS = "audit_logs"
    SCENARIO_PLANNING = "scenario_planning"
    BI_SANDBOX = "bi_sandbox"
    HISTORICAL_ANALYSIS = "historical_analysis"
    ADMIN_PANEL = "admin_panel"
    DATA_EXPORT = "data_export"
    API_ACCESS = "api_access"

class Permission(Enum):
    """Available permissions for resources"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    AUDIT = "audit"

@dataclass
class Role:
    """Role definition with permissions"""
    role_id: str
    role_name: str
    description: str
    permissions: Dict[ResourceType, Set[Permission]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class UserRole:
    """User role assignment"""
    user_id: str
    role_id: str
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    scope_restrictions: Dict[str, Any]  # Additional restrictions like department-only access

class RBACManager:
    """Role-Based Access Control Manager"""
    
    def __init__(self, db_file: str = "rbac_policies.db"):
        """
        Initialize RBAC manager
        
        Args:
            db_file (str): Path to RBAC database
        """
        self.db_file = db_file
        self._init_database()
        self._load_default_roles()
    
    def _init_database(self):
        """Initialize RBAC database schema"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Roles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                role_id TEXT PRIMARY KEY,
                role_name TEXT UNIQUE NOT NULL,
                description TEXT,
                permissions TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # User roles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                scope_restrictions TEXT,
                FOREIGN KEY (role_id) REFERENCES roles (role_id)
            )
        """)
        
        # Permission cache table for performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permission_cache (
                user_id TEXT,
                resource_type TEXT,
                permission TEXT,
                granted INTEGER,
                cached_at TEXT,
                PRIMARY KEY (user_id, resource_type, permission)
            )
        """)
        
        # Resource access log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                permission TEXT NOT NULL,
                access_granted INTEGER NOT NULL,
                access_time TEXT NOT NULL,
                ip_address TEXT,
                additional_context TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_active ON user_roles(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_permission_cache_user ON permission_cache(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_user ON resource_access_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_resource ON resource_access_log(resource_type)")
        
        conn.commit()
        conn.close()
    
    def _load_default_roles(self):
        """Load default system roles if they don't exist"""
        default_roles = self._get_default_role_definitions()
        
        for role_data in default_roles:
            if not self.get_role(role_data['role_id']):
                self.create_role(
                    role_id=role_data['role_id'],
                    role_name=role_data['role_name'],
                    description=role_data['description'],
                    permissions=role_data['permissions']
                )
    
    def _get_default_role_definitions(self) -> List[Dict[str, Any]]:
        """Get default role definitions that match existing admin_panel.py roles"""
        return [
            {
                'role_id': 'admin',
                'role_name': 'Administrator',
                'description': 'Full system access with all permissions (existing admin role)',
                'permissions': {
                    resource.value: list(Permission) for resource in ResourceType
                }
            },
            {
                'role_id': 'finance',
                'role_name': 'Finance Director',
                'description': 'Full financial data access (existing finance role)',
                'permissions': {
                    ResourceType.BUDGET_DATA.value: [Permission.READ, Permission.WRITE, Permission.APPROVE, Permission.EXPORT],
                    ResourceType.DEPARTMENT_DATA.value: [Permission.READ, Permission.WRITE, Permission.EXPORT],
                    ResourceType.FINANCIAL_REPORTS.value: [Permission.READ, Permission.WRITE, Permission.EXPORT],
                    ResourceType.SCENARIO_PLANNING.value: [Permission.READ, Permission.WRITE, Permission.EXECUTE],
                    ResourceType.BI_SANDBOX.value: [Permission.READ, Permission.WRITE, Permission.EXECUTE],
                    ResourceType.HISTORICAL_ANALYSIS.value: [Permission.READ, Permission.WRITE],
                    ResourceType.DATA_EXPORT.value: [Permission.READ, Permission.EXPORT],
                    ResourceType.AUDIT_LOGS.value: [Permission.READ, Permission.AUDIT]
                }
            },
            {
                'role_id': 'manager',
                'role_name': 'Department Manager',
                'description': 'Department-specific data access (existing manager role)',
                'permissions': {
                    ResourceType.BUDGET_DATA.value: [Permission.READ, Permission.WRITE],
                    ResourceType.DEPARTMENT_DATA.value: [Permission.READ, Permission.WRITE],
                    ResourceType.FINANCIAL_REPORTS.value: [Permission.READ],
                    ResourceType.SCENARIO_PLANNING.value: [Permission.READ, Permission.EXECUTE],
                    ResourceType.BI_SANDBOX.value: [Permission.READ, Permission.EXECUTE],
                    ResourceType.HISTORICAL_ANALYSIS.value: [Permission.READ],
                    ResourceType.DATA_EXPORT.value: [Permission.READ]
                }
            }
        ]
    
    def create_role(
        self,
        role_id: str,
        role_name: str,
        description: str,
        permissions: Dict[str, List[Permission]]
    ) -> bool:
        """
        Create a new role
        
        Args:
            role_id (str): Unique role identifier
            role_name (str): Human-readable role name
            description (str): Role description
            permissions (Dict): Permissions by resource type
            
        Returns:
            bool: True if successful
        """
        try:
            # Convert permissions to serializable format
            permissions_data = {}
            for resource_type, perms in permissions.items():
                permissions_data[resource_type] = [p.value if hasattr(p, 'value') else str(p) for p in perms]
            
            current_time = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO roles 
                (role_id, role_name, description, permissions, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
            """, (
                role_id,
                role_name,
                description,
                json.dumps(permissions_data),
                current_time,
                current_time
            ))
            
            conn.commit()
            conn.close()
            
            log_security_event(
                SecurityEventType.ADMIN_ACTION,
                ThreatLevel.LOW,
                event_details={
                    "action": "role_created",
                    "role_id": role_id,
                    "role_name": role_name
                },
                source_module="rbac_manager",
                action_taken="role_created"
            )
            
            return True
            
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.MEDIUM,
                event_details={
                    "error": str(e),
                    "operation": "create_role",
                    "role_id": role_id
                },
                source_module="rbac_manager",
                action_taken="role_creation_failed"
            )
            return False
    
    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        granted_by: str,
        expires_at: Optional[datetime] = None,
        scope_restrictions: Dict[str, Any] = None
    ) -> bool:
        """
        Assign a role to a user
        
        Args:
            user_id (str): User identifier
            role_id (str): Role identifier
            granted_by (str): Who granted the role
            expires_at (datetime, optional): When the role expires
            scope_restrictions (Dict, optional): Additional access restrictions
            
        Returns:
            bool: True if successful
        """
        try:
            # Verify role exists
            if not self.get_role(role_id):
                return False
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Deactivate any existing role assignments for this user
            cursor.execute("""
                UPDATE user_roles SET is_active = 0 WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            # Insert new role assignment
            cursor.execute("""
                INSERT INTO user_roles 
                (user_id, role_id, granted_by, granted_at, expires_at, is_active, scope_restrictions)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (
                user_id,
                role_id,
                granted_by,
                datetime.now().isoformat(),
                expires_at.isoformat() if expires_at else None,
                json.dumps(scope_restrictions or {})
            ))
            
            conn.commit()
            conn.close()
            
            # Clear permission cache for user
            self._clear_permission_cache(user_id)
            
            log_security_event(
                SecurityEventType.ADMIN_ACTION,
                ThreatLevel.LOW,
                user_id=user_id,
                event_details={
                    "action": "role_assigned",
                    "role_id": role_id,
                    "granted_by": granted_by,
                    "expires_at": expires_at.isoformat() if expires_at else None
                },
                source_module="rbac_manager",
                action_taken="role_assigned"
            )
            
            return True
            
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.MEDIUM,
                user_id=user_id,
                event_details={
                    "error": str(e),
                    "operation": "assign_role",
                    "role_id": role_id
                },
                source_module="rbac_manager",
                action_taken="role_assignment_failed"
            )
            return False
    
    def check_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        permission: Permission,
        resource_id: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Check if user has permission for a resource
        
        Args:
            user_id (str): User identifier
            resource_type (ResourceType): Type of resource
            permission (Permission): Required permission
            resource_id (str, optional): Specific resource identifier
            context (Dict, optional): Additional context for permission check
            
        Returns:
            bool: True if permission granted
        """
        try:
            # Check permission cache first
            cached_result = self._get_cached_permission(user_id, resource_type, permission)
            if cached_result is not None:
                access_granted = cached_result
            else:
                # Calculate permission
                access_granted = self._calculate_permission(user_id, resource_type, permission, context)
                # Cache result
                self._cache_permission(user_id, resource_type, permission, access_granted)
            
            # Log access attempt
            self._log_resource_access(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
                access_granted=access_granted,
                context=context
            )
            
            # Log security event for denied access
            if not access_granted:
                log_security_event(
                    SecurityEventType.UNAUTHORIZED_ACCESS,
                    ThreatLevel.MEDIUM,
                    user_id=user_id,
                    event_details={
                        "resource_type": resource_type.value,
                        "permission": permission.value,
                        "resource_id": resource_id,
                        "context": context or {}
                    },
                    source_module="rbac_manager",
                    action_taken="access_denied"
                )
            
            return access_granted
            
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.HIGH,
                user_id=user_id,
                event_details={
                    "error": str(e),
                    "operation": "check_permission",
                    "resource_type": resource_type.value,
                    "permission": permission.value
                },
                source_module="rbac_manager",
                action_taken="permission_check_failed"
            )
            return False  # Deny access on error
    
    def _calculate_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        permission: Permission,
        context: Dict[str, Any] = None
    ) -> bool:
        """Calculate if user has permission based on their roles"""
        try:
            user_roles = self.get_user_roles(user_id)
            
            for user_role in user_roles:
                role = self.get_role(user_role['role_id'])
                if not role or not role.is_active:
                    continue
                
                # Check if role has the required permission for the resource
                if resource_type in role.permissions:
                    role_permissions = role.permissions[resource_type]
                    
                    # Check for specific permission or admin permission (which grants all)
                    if permission in role_permissions or Permission.ADMIN in role_permissions:
                        # Check scope restrictions
                        scope_restrictions = json.loads(user_role.get('scope_restrictions', '{}'))
                        if self._check_scope_restrictions(scope_restrictions, context):
                            return True
            
            return False
            
        except Exception:
            return False
    
    def _check_scope_restrictions(
        self,
        scope_restrictions: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> bool:
        """Check if access is allowed based on scope restrictions"""
        if not scope_restrictions:
            return True
        
        context = context or {}
        
        # Check department restrictions
        if 'departments' in scope_restrictions:
            allowed_departments = scope_restrictions['departments']
            requested_department = context.get('department')
            
            if requested_department and requested_department not in allowed_departments:
                return False
        
        # Check organization restrictions
        if 'organizations' in scope_restrictions:
            allowed_orgs = scope_restrictions['organizations']
            requested_org = context.get('organization')
            
            if requested_org and requested_org not in allowed_orgs:
                return False
        
        # Check time-based restrictions
        if 'time_restrictions' in scope_restrictions:
            time_restrictions = scope_restrictions['time_restrictions']
            current_hour = datetime.now().hour
            
            if 'allowed_hours' in time_restrictions:
                allowed_hours = time_restrictions['allowed_hours']
                if current_hour not in allowed_hours:
                    return False
        
        return True
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM roles WHERE role_id = ? AND is_active = 1
            """, (role_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Parse permissions
            permissions_data = json.loads(row['permissions'])
            permissions = {}
            for resource_type, perms in permissions_data.items():
                try:
                    resource_enum = ResourceType(resource_type)
                    permission_set = {Permission(p) for p in perms}
                    permissions[resource_enum] = permission_set
                except ValueError:
                    continue  # Skip invalid enums
            
            return Role(
                role_id=row['role_id'],
                role_name=row['role_name'],
                description=row['description'],
                permissions=permissions,
                is_active=bool(row['is_active']),
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
            
        except Exception:
            return None
    
    def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active roles for a user"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_roles 
                WHERE user_id = ? AND is_active = 1
                AND (expires_at IS NULL OR expires_at > ?)
            """, (user_id, datetime.now().isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception:
            return []
    
    def _get_cached_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        permission: Permission
    ) -> Optional[bool]:
        """Get cached permission result"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Check if cache entry is recent (within 5 minutes)
            cache_expiry = datetime.now().timestamp() - 300
            
            cursor.execute("""
                SELECT granted FROM permission_cache 
                WHERE user_id = ? AND resource_type = ? AND permission = ?
                AND strftime('%s', cached_at) > ?
            """, (user_id, resource_type.value, permission.value, cache_expiry))
            
            row = cursor.fetchone()
            conn.close()
            
            return bool(row[0]) if row else None
            
        except Exception:
            return None
    
    def _cache_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        permission: Permission,
        granted: bool
    ):
        """Cache permission result"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO permission_cache 
                (user_id, resource_type, permission, granted, cached_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                resource_type.value,
                permission.value,
                1 if granted else 0,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception:
            pass  # Non-critical operation
    
    def _clear_permission_cache(self, user_id: str):
        """Clear permission cache for a user"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM permission_cache WHERE user_id = ?", (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception:
            pass  # Non-critical operation
    
    def _log_resource_access(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_id: Optional[str],
        permission: Permission,
        access_granted: bool,
        context: Dict[str, Any] = None
    ):
        """Log resource access attempt"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO resource_access_log 
                (user_id, resource_type, resource_id, permission, access_granted, 
                 access_time, ip_address, additional_context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                resource_type.value,
                resource_id,
                permission.value,
                1 if access_granted else 0,
                datetime.now().isoformat(),
                (context or {}).get('ip_address', 'unknown'),
                json.dumps(context or {})
            ))
            
            conn.commit()
            conn.close()
            
        except Exception:
            pass  # Non-critical operation

# Global RBAC manager instance
_rbac_manager = None

def get_rbac_manager() -> RBACManager:
    """Get the global RBAC manager instance"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager

def require_permission(resource_type: ResourceType, permission: Permission):
    """
    Decorator to enforce permission requirements on functions
    
    Args:
        resource_type (ResourceType): Required resource type
        permission (Permission): Required permission
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user_id from function arguments or session
            user_id = kwargs.get('user_id')
            if not user_id and hasattr(func, '__self__'):
                # Try to get from Streamlit session state
                try:
                    import streamlit as st
                    user_id = st.session_state.get('user', {}).get('username')
                except:
                    user_id = 'unknown'
            
            if not user_id:
                user_id = 'unknown'
            
            # Check permission
            rbac = get_rbac_manager()
            if not rbac.check_permission(user_id, resource_type, permission):
                raise PermissionError(f"User {user_id} lacks {permission.value} permission for {resource_type.value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator