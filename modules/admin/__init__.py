"""
Admin Module
User management, authentication, and system administration
"""

from .authentication import (
    login, is_admin, is_finance_director, is_department_manager, logout
)
from .user_database import (
    authenticate_user, get_user_role, get_user_departments, 
    create_user, update_user, delete_user, list_all_users
)

__all__ = [
    'login', 'authenticate_user', 'get_user_role', 'get_user_departments',
    'is_admin', 'is_finance_director', 'is_department_manager', 'logout',
    'create_user', 'update_user', 'delete_user', 'list_all_users'
]