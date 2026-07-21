"""
Database Connection Manager
Handles database connections, configuration, and basic operations

Focused on connection management only (~200 lines)
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Union, List, Tuple

# Import database connectors
try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import pyodbc
    SQLSERVER_AVAILABLE = True
except ImportError:
    pyodbc = None
    SQLSERVER_AVAILABLE = False

# Multi-database configuration for Spanish Fork
DEFAULT_DB_CONFIG = {
    "default_org": "spanish_fork",
    "organization_name": "Spanish Fork",
    "databases": {
        "gl_primary": {
            "type": "sqlite",
            "path": "databases/core/caselle_gl0_mock.db",
            "display_name": "GL Primary Database",
            "description": "General Ledger and Financial Data",
            "connection_status": "connected",
            "host": "",
            "port": "",
            "database": "",
            "username": "",
            "password": ""
        },
        "utility_management": {
            "type": "postgres", 
            "path": "",
            "display_name": "Utility Management Database",
            "description": "Water, Sewer, Electric Utility Data",
            "connection_status": "not_connected",
            "host": "",
            "port": "5432",
            "database": "",
            "username": "",
            "password": ""
        },
        "asset_management": {
            "type": "mysql",
            "path": "",
            "display_name": "Asset Management Database", 
            "description": "Infrastructure and Equipment Assets",
            "connection_status": "not_connected",
            "host": "",
            "port": "3306",
            "database": "",
            "username": "",
            "password": ""
        },
        "permits_licensing": {
            "type": "sqlserver",
            "path": "",
            "display_name": "Permits & Licensing Database",
            "description": "Building Permits and Business Licenses",
            "connection_status": "not_connected",
            "host": "",
            "port": "1433",
            "database": "",
            "username": "",
            "password": ""
        },
        "payroll": {
            "type": "sqlite",
            "path": "databases/payroll_city_payroll_demo.db",
            "display_name": "Payroll Database",
            "description": "Employee Payroll, Benefits, Time Tracking, and HR Management (SQLite/SQL Server)",
            "connection_status": "connected",
            "host": "",
            "port": "1433",
            "database": "",
            "username": "",
            "password": "",
            "supports_dual_connection": True
        }
    }
}

def get_database_connection(db_name: Optional[str] = None):
    """Get database connection for specified database (returns appropriate connection type)"""
    if db_name is None:
        db_name = "gl_primary"  # Default to GL database
    
    db_config = load_db_config()
    db_info = db_config.get("databases", {}).get(db_name, {})
    db_type = db_info.get("type", "sqlite")
    
    if db_type == "sqlite":
        db_path = db_info.get("path", "databases/core/caselle_gl0_mock.db")
        # Ensure absolute path from project root
        if not os.path.isabs(db_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, db_path)
        
        if os.path.exists(db_path):
            return sqlite3.connect(db_path)
        
        # Fallback to organized GL database with absolute path
        fallback_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "databases/core/caselle_gl0_mock.db")
        if os.path.exists(fallback_path):
            return sqlite3.connect(fallback_path)
        
        # Final fallback to root directory
        root_fallback = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "caselle_gl0_mock.db")
        return sqlite3.connect(root_fallback)
    
    elif db_type == "postgres" and POSTGRES_AVAILABLE and 'psycopg2' in globals():
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=db_info.get("host", "localhost"),
                port=db_info.get("port", "5432"),
                database=db_info.get("database", ""),
                user=db_info.get("username", ""),
                password=db_info.get("password", "")
            )
            return conn
        except Exception as e:
            raise ConnectionError(f"PostgreSQL connection failed: {str(e)}")
    
    elif db_type == "mysql" and MYSQL_AVAILABLE and 'mysql' in dir():
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=db_info.get("host", "localhost"),
                port=db_info.get("port", "3306"),
                database=db_info.get("database", ""),
                user=db_info.get("username", ""),
                password=db_info.get("password", "")
            )
            return conn
        except Exception as e:
            raise ConnectionError(f"MySQL connection failed: {str(e)}")
    
    elif db_type == "sqlserver" and SQLSERVER_AVAILABLE and pyodbc is not None:
        try:
            # Build connection string for SQL Server
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_info.get('host', 'localhost')},{db_info.get('port', '1433')};DATABASE={db_info.get('database', '')};UID={db_info.get('username', '')};PWD={db_info.get('password', '')}"
            conn = pyodbc.connect(conn_str)
            return conn
        except Exception as e:
            raise ConnectionError(f"SQL Server connection failed: {str(e)}")
    
    else:
        # If specific database type not available, fall back to organized SQLite
        fallback_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "databases/core/caselle_gl0_mock.db")
        return sqlite3.connect(fallback_path)

def get_all_database_connections() -> Dict[str, Any]:
    """Get connections to all configured databases"""
    connections = {}
    db_config = load_db_config()
    
    for db_name, db_info in db_config.get("databases", {}).items():
        if db_info.get("connection_status") == "connected":
            try:
                # Check if we have required connection info
                db_type = db_info.get("type", "sqlite")
                if db_type == "sqlite" and db_info.get("path"):
                    connections[db_name] = get_database_connection(db_name)
                elif db_type in ["postgres", "mysql", "sqlserver"] and db_info.get("host") and db_info.get("database"):
                    connections[db_name] = get_database_connection(db_name)
            except Exception as e:
                print(f"Failed to connect to {db_name}: {e}")
    
    return connections

def _get_config_service():
    try:
        from modules.services.config_service import get_config_service
        return get_config_service()
    except Exception:
        return None

def load_db_config() -> Dict[str, Any]:
    """Load database configuration from ConfigService (database-backed).
    Falls back to system_settings.json if ConfigService unavailable."""
    svc = _get_config_service()
    if svc:
        try:
            data = svc.get("database_connections", "config")
            if data and isinstance(data, dict):
                return data
        except Exception:
            pass

    config_file = "system_settings.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get("database", DEFAULT_DB_CONFIG)
        except Exception:
            pass

    return DEFAULT_DB_CONFIG

def save_db_config(config: Dict[str, Any]):
    """Save database configuration to ConfigService (database-backed).
    Falls back to system_settings.json if ConfigService unavailable."""
    svc = _get_config_service()
    if svc:
        try:
            svc.set("database_connections", "config", config, updated_by="connection_manager")
            return
        except Exception:
            pass

    config_file = "system_settings.json"
    try:
        existing_config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                existing_config = json.load(f)
        existing_config["database"] = config
        with open(config_file, 'w') as f:
            json.dump(existing_config, f, indent=2)
    except Exception as e:
        print(f"Error saving database config: {e}")

def get_default_org() -> str:
    """Get default organization ID"""
    config = load_db_config()
    return config.get("default_org", "spanish_fork")

def get_available_databases() -> Dict[str, Dict[str, str]]:
    """Get available databases with their information"""
    config = load_db_config()
    databases = {}
    
    for db_name, db_info in config.get("databases", {}).items():
        databases[db_name] = {
            "display_name": db_info.get("display_name", db_name),
            "description": db_info.get("description", ""),
            "status": db_info.get("connection_status", "not_connected"),
            "type": db_info.get("type", "sqlite"),
            "path": db_info.get("path", ""),
            "host": db_info.get("host", ""),
            "port": db_info.get("port", ""),
            "database": db_info.get("database", ""),
            "username": db_info.get("username", "")
        }
    
    return databases

def update_database_connection(db_name: str, connection_params: Dict[str, str]) -> bool:
    """Update database connection configuration with comprehensive parameters"""
    try:
        config = load_db_config()
        
        if db_name in config.get("databases", {}):
            # Update all connection parameters
            for key, value in connection_params.items():
                if key in ["type", "path", "host", "port", "database", "username", "password"]:
                    config["databases"][db_name][key] = value
            
            config["databases"][db_name]["connection_status"] = "connected"
            
            save_db_config(config)
            return True
        return False
    except Exception as e:
        print(f"Failed to update database connection: {e}")
        return False

def update_database_connection_legacy(db_name: str, db_path: str, db_type: str = "sqlite") -> bool:
    """Legacy method for SQLite file connections"""
    return update_database_connection(db_name, {
        "type": db_type,
        "path": db_path
    })

def disconnect_database(db_name: str) -> bool:
    """Completely disconnect a database and clear all related state"""
    try:
        # Clear database configuration
        config = load_db_config()
        
        if db_name in config.get("databases", {}):
            config["databases"][db_name]["connection_status"] = "not_connected"
            config["databases"][db_name]["path"] = ""
            config["databases"][db_name]["host"] = ""
            config["databases"][db_name]["port"] = ""
            config["databases"][db_name]["database"] = ""
            config["databases"][db_name]["username"] = ""
            config["databases"][db_name]["password"] = ""
            
            save_db_config(config)
            
            # Clear session state data (if streamlit is available)
            try:
                import streamlit as st
                # Clear any cached data related to this database
                cache_keys_to_clear = []
                for key in st.session_state.keys():
                    if any(keyword in str(key).lower() for keyword in ['employee', 'payroll', 'pbb', 'connection']):
                        cache_keys_to_clear.append(key)
                
                for key in cache_keys_to_clear:
                    del st.session_state[key]
                    
                # Clear Streamlit cache related to database connections
                if hasattr(st, 'cache_data'):
                    st.cache_data.clear()
                if hasattr(st, 'cache_resource'):  
                    st.cache_resource.clear()
                    
            except (ImportError, Exception):
                # Streamlit not available or error clearing cache
                pass
            
            # Clear any connection-related environment variables
            connection_env_vars = [
                'PAYROLL_ODBC_DSN',
                'DATABASE_URL',
                'DB_CONNECTION_STRING'
            ]
            for env_var in connection_env_vars:
                if env_var in os.environ:
                    del os.environ[env_var]
            
            return True
        return False
    except Exception as e:
        print(f"Failed to disconnect database: {e}")
        return False

def test_connection(db_name: str) -> Dict[str, Any]:
    """Test database connection for specified database"""
    result = {
        "success": False,
        "error": None,
        "database_type": None,
        "server_info": None
    }
    
    try:
        db_config = load_db_config()
        db_info = db_config.get("databases", {}).get(db_name, {})
        db_type = db_info.get("type", "sqlite")
        result["database_type"] = db_type
        
        conn = get_database_connection(db_name)
        
        # Test with appropriate SQL for each database type
        if db_type == "sqlite":
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            fetch_result = cursor.fetchone()
            if fetch_result and hasattr(fetch_result, '__len__') and len(fetch_result) > 0:
                result["server_info"] = f"SQLite version {str(fetch_result[0] if fetch_result[0] is not None else 'unknown')}"
            else:
                result["server_info"] = "SQLite (version unknown)"
            
        elif db_type == "postgres":
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            fetch_result = cursor.fetchone()
            if fetch_result and hasattr(fetch_result, '__len__') and len(fetch_result) > 0:
                version_data = fetch_result[0] if fetch_result[0] is not None else 'unknown'
                version_str = str(version_data)
                if version_str:
                    version_parts = version_str.split()
                    result["server_info"] = ' '.join(str(part) for part in version_parts[0:2]) if len(version_parts) >= 2 else version_str
                else:
                    result["server_info"] = "PostgreSQL (version unknown)"
            else:
                result["server_info"] = "PostgreSQL (version unknown)"
            
        elif db_type == "mysql":
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            fetch_result = cursor.fetchone()
            if fetch_result and hasattr(fetch_result, '__len__') and len(fetch_result) > 0:
                result["server_info"] = f"MySQL version {str(fetch_result[0] if fetch_result[0] is not None else 'unknown')}"
            else:
                result["server_info"] = "MySQL (version unknown)"
            
        elif db_type == "sqlserver":
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            fetch_result = cursor.fetchone()
            if fetch_result and hasattr(fetch_result, '__len__') and len(fetch_result) > 0:
                version_data = fetch_result[0] if fetch_result[0] is not None else 'unknown'
                version_str = str(version_data)
                if version_str:
                    version_parts = version_str.split('\n')
                    result["server_info"] = "SQL Server " + (version_parts[0] if version_parts and len(version_parts) > 0 else version_str)
                else:
                    result["server_info"] = "SQL Server (version unknown)"
            else:
                result["server_info"] = "SQL Server (version unknown)"
        
        conn.close()
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result

def test_database_file(db_path: str) -> Dict[str, Any]:
    """Test if a database file is valid and get basic info"""
    result = {
        "valid": False,
        "tables": [],
        "error": None,
        "size": 0
    }
    
    try:
        if not os.path.exists(db_path):
            result["error"] = "File does not exist"
            return result
            
        result["size"] = os.path.getsize(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        result["tables"] = [table[0] for table in tables]
        result["valid"] = True
        
        conn.close()
        
    except Exception as e:
        result["error"] = str(e)
    
    return result

def get_selected_database() -> str:
    """Get currently selected database from session state"""
    import streamlit as st
    return st.session_state.get('selected_database', 'gl_primary')

def set_selected_database(db_name: str):
    """Set the currently selected database in session state"""
    import streamlit as st
    st.session_state.selected_database = db_name

def execute_query(query: str, params: Optional[Union[List[Any], Tuple[Any, ...], Dict[str, Any]]] = None, db_name: Optional[str] = None) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame"""
    if db_name is None:
        db_name = get_selected_database()
        
    conn = get_database_connection(db_name)
    
    try:
        if params:
            # Convert tuple params to list for pandas compatibility
            if isinstance(params, tuple):
                params_list = list(params)
            elif isinstance(params, dict):
                params_list = params
            else:
                params_list = params
            result = pd.read_sql_query(query, conn, params=params_list)
        else:
            result = pd.read_sql_query(query, conn)
        return result
    finally:
        conn.close()

def execute_query_multiple_dbs(queries: Dict[str, str]) -> Dict[str, pd.DataFrame]:
    """Execute queries across multiple databases"""
    results = {}
    
    for db_name, query in queries.items():
        try:
            results[db_name] = execute_query(query, db_name=db_name)
        except Exception as e:
            print(f"Query failed for {db_name}: {e}")
            results[db_name] = pd.DataFrame()
    
    return results

def check_password(username: Optional[str] = None, password: Optional[str] = None) -> bool:
    """Check if password is correct for given username (compatibility function)"""
    if username and password:
        from modules.admin.authentication import authenticate_user
        return authenticate_user(username, password) is not None
    # For single-parameter legacy compatibility
    return True

def get_org_display_info(org_id: Optional[str] = None) -> Dict[str, Union[str, int]]:
    """Get organization display information"""
    config = load_db_config()
    org_name = config.get("organization_name", "Spanish Fork")
    
    svc = _get_config_service()
    if svc:
        try:
            city_config = svc.get_namespace("city_config")
            if "cityA" in city_config:
                city_data = city_config["cityA"]
                if isinstance(city_data, dict) and "org_name" in city_data:
                    org_name = city_data["org_name"]
                elif isinstance(city_data, str):
                    import json as _json
                    try:
                        parsed = _json.loads(city_data)
                        if "org_name" in parsed:
                            org_name = parsed["org_name"]
                    except Exception:
                        pass
        except Exception:
            pass

    if org_name == config.get("organization_name", "Spanish Fork"):
        try:
            if os.path.exists("config.json"):
                with open("config.json", 'r') as f:
                    main_config = json.load(f)
                    if "cityA" in main_config and "org_name" in main_config["cityA"]:
                        org_name = main_config["cityA"]["org_name"]
        except Exception:
            pass
    
    return {
        "org_id": config.get("default_org", "spanish_fork"),
        "name": org_name,
        "display_name": org_name,
        "theme_color": "#1E3A8A",
        "databases_connected": len([db for db in config.get("databases", {}).values() 
                                  if db.get("connection_status") == "connected"])
    }


def get_scenarios(limit=None):
    """Get saved scenarios from the database
    
    Args:
        limit (int, optional): Maximum number of scenarios to return. If None, returns all.
    
    Returns:
        list: List of scenario dictionaries
    """
    try:
        conn = get_database_connection()
        if conn:
            query = "SELECT * FROM scenarios ORDER BY created_date DESC"
            if limit is not None:
                query += f" LIMIT {limit}"
            result = pd.read_sql_query(query, conn)
            conn.close()
            
            # Convert to the expected format for compatibility
            scenarios = []
            for _, row in result.iterrows():
                scenarios.append({
                    'id': row.get('id'),
                    'name': row.get('name', ''),
                    'total_amount': row.get('total_cost', 0),
                    'department_count': 0,  # Will be filled if available
                    'created_at': row.get('created_date', ''),
                    'project_name': row.get('project_name', 'Unknown')
                })
            return scenarios
    except Exception as e:
        print(f"Error loading scenarios: {e}")
    return []


def get_detailed_scenario_data(scenario_id):
    """Get detailed data for a specific scenario"""
    try:
        conn = get_database_connection()
        if conn:
            query = "SELECT * FROM scenarios WHERE id = ?"
            result = pd.read_sql_query(query, conn, params=[scenario_id])
            conn.close()
            if not result.empty:
                return result.iloc[0].to_dict()
    except Exception as e:
        print(f"Error loading scenario {scenario_id}: {e}")
    return {}


def load_org_data(org="cityA"):
    """Load organization data from the primary database"""
    try:
        conn = get_database_connection()
        if conn:
            # Load basic financial data
            query = """
            SELECT * FROM tblGLAccount 
            WHERE OrganizationName = ? 
            ORDER BY AccountNumber
            """
            result = pd.read_sql_query(query, conn, params=[org])
            conn.close()
            return result
    except Exception as e:
        print(f"Error loading organization data: {e}")
        # Return empty DataFrame with expected columns
        return pd.DataFrame({'AccountNumber': [], 'AccountName': [], 'OrganizationName': []})