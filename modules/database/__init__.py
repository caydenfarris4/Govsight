"""
Database Module
Database connections, query execution, and data management
"""

from .connection_manager import (
    get_database_connection, get_all_database_connections, get_selected_database, 
    set_selected_database, execute_query, execute_query_multiple_dbs,
    check_password, get_org_display_info, get_available_databases,
    update_database_connection, disconnect_database, test_connection, 
    test_database_file, load_db_config, save_db_config, get_default_org
)

from .backup_manager import BackupManager, create_backup_schedule

__all__ = [
    'get_database_connection', 'get_all_database_connections', 'get_selected_database', 
    'set_selected_database', 'execute_query', 'execute_query_multiple_dbs',
    'check_password', 'get_org_display_info', 'get_available_databases',
    'update_database_connection', 'disconnect_database', 'test_connection', 
    'test_database_file', 'load_db_config', 'save_db_config', 'get_default_org',
    'BackupManager', 'create_backup_schedule'
]