"""
Centralized Database Configuration for Production
Ensures all environments (development and production) use the same database
"""

import os

def get_production_db_path():
    """
    Get the production database path
    This path is used by both development and deployed production environments
    to ensure data consistency across all deployments
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    production_db = os.path.join(base_dir, "production_data", "users.db")
    
    os.makedirs(os.path.dirname(production_db), exist_ok=True)
    
    return production_db

PRODUCTION_USERS_DB = get_production_db_path()
