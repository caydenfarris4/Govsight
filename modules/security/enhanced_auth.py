"""
Enhanced Authentication System

This module enhances the existing admin_panel.py authentication system
with advanced security features while maintaining compatibility.
"""

import streamlit as st
import csv
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from .password_security import verify_password, hash_password, secure_compare
from .session_manager import get_session_manager
from .audit_logger import SecurityEventType, ThreatLevel, log_security_event
from .rbac_manager import get_rbac_manager, ResourceType, Permission

# Import existing functions from admin_panel.py
import sys
sys.path.append('.')

class EnhancedAuth:
    """Enhanced authentication system that extends existing admin_panel functionality"""
    
    def __init__(self):
        self.session_manager = get_session_manager()
        self.rbac_manager = get_rbac_manager()
        self.users_file = "users_table.csv"
        self.settings_file = "system_settings.json"
        
        # Initialize enhanced user storage
        self._migrate_existing_users()
    
    def _migrate_existing_users(self):
        """Migrate existing users to enhanced security system"""
        try:
            from modules.admin.admin_panel import load_users
            existing_users = load_users()
            
            # Check if users need migration to hashed passwords
            migration_needed = False
            for username, user_data in existing_users.items():
                if not user_data.get('password_hashed', False):
                    migration_needed = True
                    break
            
            if migration_needed:
                self._perform_user_migration(existing_users)
                
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.LOW,
                event_details={"error": str(e), "operation": "user_migration"},
                source_module="enhanced_auth",
                action_taken="migration_failed"
            )
    
    def _perform_user_migration(self, users: Dict[str, Any]):
        """Perform migration of plain text passwords to hashed passwords"""
        try:
            migrated_count = 0
            
            for username, user_data in users.items():
                if not user_data.get('password_hashed', False):
                    # Hash the existing password
                    plain_password = user_data.get('password', 'govsight123')
                    password_hash, salt = hash_password(plain_password)
                    
                    # Update user data
                    user_data['password_hash'] = password_hash
                    user_data['password_salt'] = salt
                    user_data['password_hashed'] = True
                    
                    # Remove plain text password
                    if 'password' in user_data:
                        del user_data['password']
                    
                    migrated_count += 1
            
            # Save migrated users
            self._save_enhanced_users(users)
            
            log_security_event(
                SecurityEventType.ADMIN_ACTION,
                ThreatLevel.LOW,
                event_details={
                    "action": "password_migration",
                    "migrated_users": migrated_count
                },
                source_module="enhanced_auth",
                action_taken="passwords_migrated"
            )
            
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.MEDIUM,
                event_details={"error": str(e), "operation": "password_migration"},
                source_module="enhanced_auth",
                action_taken="migration_failed"
            )
    
    def _save_enhanced_users(self, users: Dict[str, Any]):
        """Save users with enhanced security data"""
        try:
            # Save to CSV for backward compatibility
            with open(self.users_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["Username", "Role", "Departments", "Password", "PasswordHashed", "PasswordHash", "PasswordSalt"])
                writer.writeheader()
                
                for username, details in users.items():
                    depts = details["departments"]
                    if isinstance(depts, list):
                        depts = ", ".join(depts)
                    
                    writer.writerow({
                        "Username": username,
                        "Role": details["role"],
                        "Departments": depts,
                        "Password": "***HASHED***" if details.get('password_hashed') else details.get('password', 'govsight123'),
                        "PasswordHashed": str(details.get('password_hashed', False)),
                        "PasswordHash": details.get('password_hash', ''),
                        "PasswordSalt": details.get('password_salt', '')
                    })
                    
        except Exception as e:
            raise Exception(f"Failed to save enhanced users: {e}")
    
    def enhanced_login(self, username: str, password: str, ip_address: str = "unknown", user_agent: str = "") -> bool:
        """
        Enhanced login with security features
        
        Args:
            username (str): Username
            password (str): Password
            ip_address (str): User's IP address
            user_agent (str): User's browser user agent
            
        Returns:
            bool: True if login successful
        """
        try:
            # Load users
            users = self._load_enhanced_users()
            user = users.get(username)
            
            if not user:
                self._record_failed_login(username, ip_address, "user_not_found")
                return False
            
            # Verify password
            password_valid = False
            if user.get('password_hashed', False):
                # Use enhanced password verification
                password_valid = verify_password(
                    password, 
                    user.get('password_hash', ''), 
                    user.get('password_salt', '')
                )
            else:
                # Fall back to plain text comparison for unmigrated users
                password_valid = secure_compare(password, user.get('password', ''))
            
            if not password_valid:
                self._record_failed_login(username, ip_address, "invalid_password")
                return False
            
            # Create secure session
            session_id = self.session_manager.create_session(
                user_id=username,
                ip_address=ip_address,
                user_agent=user_agent,
                permissions=self._get_user_permissions(user['role']),
                session_data={
                    'role': user['role'],
                    'departments': user['departments'],
                    'login_time': datetime.now().isoformat()
                }
            )
            
            if not session_id:
                self._record_failed_login(username, ip_address, "session_creation_failed")
                return False
            
            # Set session state for compatibility with existing code
            st.session_state.user = {
                "username": username,
                "role": user["role"],
                "departments": user["departments"],
                "session_id": session_id,
                "enhanced_auth": True
            }
            st.session_state.authenticated = True
            
            # Log successful login
            log_security_event(
                SecurityEventType.LOGIN_SUCCESS,
                ThreatLevel.LOW,
                user_id=username,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                event_details={
                    "role": user["role"],
                    "departments": user["departments"]
                },
                source_module="enhanced_auth",
                action_taken="user_authenticated"
            )
            
            return True
            
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.HIGH,
                user_id=username,
                ip_address=ip_address,
                event_details={"error": str(e), "operation": "enhanced_login"},
                source_module="enhanced_auth",
                action_taken="login_error"
            )
            return False
    
    def _record_failed_login(self, username: str, ip_address: str, reason: str):
        """Record failed login attempt"""
        self.session_manager.record_failed_attempt(
            user_id=username,
            ip_address=ip_address,
            reason=reason
        )
        
        log_security_event(
            SecurityEventType.LOGIN_FAILURE,
            ThreatLevel.MEDIUM,
            user_id=username,
            ip_address=ip_address,
            event_details={"reason": reason},
            source_module="enhanced_auth",
            action_taken="failed_login_recorded"
        )
    
    def _load_enhanced_users(self) -> Dict[str, Any]:
        """Load users with enhanced security data"""
        users = {}
        
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Convert departments string to list if not "all"
                        if row.get("Departments", "").lower() != "all":
                            departments = [d.strip() for d in row.get("Departments", "").split(",") if d.strip()]
                        else:
                            departments = "all"
                        
                        user_data = {
                            "role": row["Role"],
                            "departments": departments,
                        }
                        
                        # Handle enhanced password fields
                        if row.get("PasswordHashed", "").lower() == "true":
                            user_data["password_hashed"] = True
                            user_data["password_hash"] = row.get("PasswordHash", "")
                            user_data["password_salt"] = row.get("PasswordSalt", "")
                        else:
                            user_data["password"] = row.get("Password", "govsight123")
                            user_data["password_hashed"] = False
                        
                        users[row["Username"]] = user_data
                        
            except Exception as e:
                # Fall back to default users if file is corrupted
                return self._get_default_users()
        else:
            return self._get_default_users()
        
        return users
    
    def _get_default_users(self) -> Dict[str, Any]:
        """Get default users with enhanced security"""
        return {
            "admin_user": {"role": "admin", "departments": "all", "password": "govsight123", "password_hashed": False},
            "finance_director": {"role": "finance", "departments": "all", "password": "govsight123", "password_hashed": False},
            "pw_manager": {"role": "manager", "departments": ["Public Works"], "password": "govsight123", "password_hashed": False},
            "police_manager": {"role": "manager", "departments": ["Police"], "password": "govsight123", "password_hashed": False},
            "parks_manager": {"role": "manager", "departments": ["Parks & Rec"], "password": "govsight123", "password_hashed": False},
        }
    
    def _get_user_permissions(self, role: str) -> List[str]:
        """Get permissions list for a role"""
        permission_map = {
            "admin": ["read", "write", "delete", "admin", "export", "audit"],
            "finance": ["read", "write", "export", "approve"],
            "manager": ["read", "write"]
        }
        
        return permission_map.get(role, ["read"])
    
    def validate_session(self, session_id: str = None) -> bool:
        """Validate current session"""
        try:
            if not session_id:
                session_id = st.session_state.get('user', {}).get('session_id')
            
            if not session_id:
                return False
            
            session = self.session_manager.validate_session(session_id)
            
            if not session:
                # Clear invalid session
                if 'user' in st.session_state:
                    del st.session_state.user
                if 'authenticated' in st.session_state:
                    del st.session_state.authenticated
                return False
            
            return True
            
        except Exception:
            return False
    
    def enhanced_logout(self, reason: str = "user_logout"):
        """Enhanced logout with session cleanup"""
        try:
            session_id = st.session_state.get('user', {}).get('session_id')
            username = st.session_state.get('user', {}).get('username', 'unknown')
            
            if session_id:
                self.session_manager.terminate_session(session_id, reason)
            
            # Clear session state
            if 'user' in st.session_state:
                del st.session_state.user
            if 'authenticated' in st.session_state:
                del st.session_state.authenticated
            
            log_security_event(
                SecurityEventType.SESSION_EXPIRY,
                ThreatLevel.LOW,
                user_id=username,
                session_id=session_id,
                event_details={"reason": reason},
                source_module="enhanced_auth",
                action_taken="user_logged_out"
            )
            
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.LOW,
                event_details={"error": str(e), "operation": "enhanced_logout"},
                source_module="enhanced_auth",
                action_taken="logout_error"
            )
    
    def check_resource_permission(
        self, 
        resource_type: ResourceType, 
        permission: Permission,
        context: Dict[str, Any] = None
    ) -> bool:
        """Check if current user has permission for a resource"""
        try:
            username = st.session_state.get('user', {}).get('username')
            if not username:
                return False
            
            # Add department context for manager roles
            user_departments = st.session_state.get('user', {}).get('departments')
            if context is None:
                context = {}
            
            if user_departments != "all" and isinstance(user_departments, list):
                context['departments'] = user_departments
            
            return self.rbac_manager.check_permission(
                user_id=username,
                resource_type=resource_type,
                permission=permission,
                context=context
            )
            
        except Exception:
            return False

# Global enhanced auth instance
_enhanced_auth = None

def get_enhanced_auth() -> EnhancedAuth:
    """Get the global enhanced authentication instance"""
    global _enhanced_auth
    if _enhanced_auth is None:
        _enhanced_auth = EnhancedAuth()
    return _enhanced_auth

def enhanced_require_login():
    """Enhanced login requirement decorator"""
    auth = get_enhanced_auth()
    
    if not st.session_state.get('authenticated', False):
        # Show enhanced login form
        return False
    
    # Validate session
    if not auth.validate_session():
        return False
    
    return True

def enhanced_require_permission(resource_type: ResourceType, permission: Permission):
    """Decorator for enhanced permission requirements"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            auth = get_enhanced_auth()
            
            if not enhanced_require_login():
                st.error("Authentication required")
                st.stop()
            
            if not auth.check_resource_permission(resource_type, permission):
                st.error("Insufficient permissions")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator