"""
Admin Panel Module

User management, security, and system administration
"""

from .panel_core import run_admin_panel
from .user_management import load_users, save_users, manage_user_roles
from .security import login, get_user_role, check_permissions
from .settings import load_settings, save_settings, manage_system_config

__all__ = [
    'run_admin_panel',
    'load_users',
    'save_users', 
    'manage_user_roles',
    'login',
    'get_user_role',
    'check_permissions',
    'load_settings',
    'save_settings',
    'manage_system_config'
]