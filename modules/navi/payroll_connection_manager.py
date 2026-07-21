"""
Payroll Connection Manager
Handles dual SQLite/SQL Server connections for Position-Based Budgeting
"""

import streamlit as st
import os
import sqlite3
from typing import Dict, Any, Optional, Tuple
import pandas as pd

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False

class PayrollConnectionManager:
    """Manages payroll database connections for both SQLite and SQL Server"""
    
    def __init__(self):
        self.connection_type = self._detect_connection_type()
    
    def _detect_connection_type(self) -> str:
        """Auto-detect which payroll connection to use"""
        # Priority: SQL Server credentials > SQLite file > None
        
        # First check if payroll database has been explicitly disconnected
        if self._is_payroll_disconnected():
            return "none"
        
        # Check for SQL Server configuration first
        if self._has_sqlserver_config():
            return "sqlserver"
        
        # Then check for SQLite files (including new uploads)
        sqlite_paths = [
            "databases/payroll_city_payroll_demo (1).db",  # New uploaded database first
            "databases/payroll_city_payroll_demo.db",
            "databases/payroll.db",
            "attached_assets/city_payroll_demo_1755893488055.db"
        ]
        
        for path in sqlite_paths:
            if os.path.exists(path):
                try:
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    conn.close()
                    if tables:
                        return "sqlite"
                except Exception:
                    continue
        
        return "none"
    
    def _is_payroll_disconnected(self) -> bool:
        """Check if payroll database has been explicitly disconnected"""
        try:
            # Check database manager config for disconnection status
            from modules.database.connection_manager import load_db_config
            config = load_db_config()
            
            payroll_db = config.get("databases", {}).get("payroll_database", {})
            if payroll_db.get("connection_status") == "not_connected":
                return True
                
        except Exception:
            pass
        
        # Check session state for disconnect flag
        try:
            import streamlit as st
            if st.session_state.get("payroll_force_disconnected", False):
                return True
        except:
            pass
        
        return False
    
    def _has_sqlserver_config(self) -> bool:
        """Check if SQL Server configuration is available"""
        # Check streamlit secrets
        try:
            if hasattr(st, "secrets") and "payroll_db" in st.secrets:
                secrets = st.secrets["payroll_db"]
                required_keys = ["server", "database", "username", "password"]
                if all(key in secrets and secrets[key] for key in required_keys):
                    return True
        except:
            pass
        
        # Check environment variable
        if os.getenv("PAYROLL_ODBC_DSN"):
            return True
        
        return False
    
    def disconnect_payroll(self) -> bool:
        """Completely disconnect payroll database and clear all state"""
        try:
            # Set force disconnect flag
            try:
                import streamlit as st
                st.session_state["payroll_force_disconnected"] = True
                
                # Clear all payroll-related session data
                payroll_keys = []
                for key in list(st.session_state.keys()):
                    if any(keyword in key.lower() for keyword in ['payroll', 'employee', 'pbb']):
                        payroll_keys.append(key)
                        
                for key in payroll_keys:
                    if key != "payroll_force_disconnected":  # Keep the disconnect flag
                        del st.session_state[key]
                        
            except (ImportError, Exception):
                pass
            
            # Update database config if payroll database exists
            try:
                from modules.database.connection_manager import disconnect_database
                disconnect_database("payroll_database")
            except Exception:
                pass
                
            # Clear environment variables
            payroll_env_vars = ['PAYROLL_ODBC_DSN', 'PAYROLL_CONNECTION_STRING']
            for env_var in payroll_env_vars:
                if env_var in os.environ:
                    del os.environ[env_var]
            
            # Update connection type
            self.connection_type = "none"
            
            return True
            
        except Exception as e:
            print(f"Error disconnecting payroll: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and details"""
        status = {
            "type": self.connection_type,
            "connected": False,
            "details": {},
            "error": None
        }
        
        if self.connection_type == "sqlite":
            sqlite_paths = [
                "databases/payroll_city_payroll_demo.db",
                "databases/payroll.db",
                "attached_assets/city_payroll_demo_1755893488055.db"
            ]
            
            for path in sqlite_paths:
                if os.path.exists(path):
                    try:
                        conn = sqlite3.connect(path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                        table_count = cursor.fetchone()[0]
                        conn.close()
                        
                        status["connected"] = True
                        status["details"] = {
                            "file_path": path,
                            "file_size": f"{os.path.getsize(path) / 1024 / 1024:.1f} MB",
                            "table_count": table_count
                        }
                        break
                    except Exception as e:
                        status["error"] = str(e)
        
        elif self.connection_type == "sqlserver":
            try:
                if PYODBC_AVAILABLE:
                    # Test SQL Server connection
                    conn_str = self._get_sqlserver_connection_string()
                    conn = pyodbc.connect(conn_str, timeout=5)
                    cursor = conn.cursor()
                    cursor.execute("SELECT @@VERSION")
                    version = cursor.fetchone()[0]
                    conn.close()
                    
                    status["connected"] = True
                    status["details"] = {
                        "server_version": version.split('\n')[0],
                        "connection_string": conn_str.replace(conn_str.split('PWD=')[1].split(';')[0], '***')
                    }
                else:
                    status["error"] = "pyodbc not available"
            except Exception as e:
                status["error"] = str(e)
        
        return status
    
    def _get_sqlserver_connection_string(self) -> str:
        """Build SQL Server connection string"""
        if hasattr(st, "secrets") and "payroll_db" in getattr(st, "secrets", {}):
            s = st.secrets["payroll_db"]
            driver = s.get("driver", "{ODBC Driver 17 for SQL Server}")
            server = s.get("server")
            database = s.get("database")
            username = s.get("username")
            password = s.get("password")
            trust = s.get("trusted_connection", "no")
            
            if trust.lower() in ("yes", "true", "1"):
                return f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
            return f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};"
        
        env = os.getenv("PAYROLL_ODBC_DSN")
        if env:
            return env
        
        return "DSN=PAYROLL_DB"
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the current payroll database connection"""
        result = {
            "success": False,
            "connection_type": self.connection_type,
            "message": "",
            "details": {}
        }
        
        try:
            if self.connection_type == "sqlite":
                from modules.navi.payroll_live_adapter import get_paycodes
                df, _ = get_paycodes()
                result["success"] = True
                result["message"] = f"SQLite connection successful - {len(df)} pay codes loaded"
                result["details"]["records_loaded"] = len(df)
                
            elif self.connection_type == "sqlserver":
                from modules.navi.payroll_live_adapter import get_paycodes
                df, _ = get_paycodes()
                result["success"] = True
                result["message"] = f"SQL Server connection successful - {len(df)} pay codes loaded"
                result["details"]["records_loaded"] = len(df)
                
            else:
                result["message"] = "No payroll database connection configured"
                
        except Exception as e:
            result["message"] = f"Connection test failed: {str(e)}"
        
        return result
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about available payroll tables"""
        info = {
            "tables": [],
            "total_records": 0,
            "connection_type": self.connection_type
        }
        
        try:
            if self.connection_type == "sqlite":
                sqlite_paths = [
                    "databases/payroll_city_payroll_demo.db",
                    "databases/payroll.db",
                    "attached_assets/city_payroll_demo_1755893488055.db"
                ]
                
                for path in sqlite_paths:
                    if os.path.exists(path):
                        conn = sqlite3.connect(path)
                        cursor = conn.cursor()
                        
                        # Get table names
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        
                        for table in tables:
                            table_name = table[0]
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                            count = cursor.fetchone()[0]
                            
                            info["tables"].append({
                                "name": table_name,
                                "records": count,
                                "type": "table"
                            })
                            info["total_records"] += count
                        
                        conn.close()
                        break
                        
        except Exception as e:
            info["error"] = str(e)
        
        return info

def render_payroll_connection_status():
    """Render payroll connection status in the admin panel"""
    st.subheader("Payroll Database Connection")
    
    manager = PayrollConnectionManager()
    status = manager.get_connection_status()
    
    if status["connected"]:
        if status["type"] == "sqlite":
            # Connection status display removed for cleaner UI
        elif status["type"] == "sqlserver":
            # Connection status display removed for cleaner UI
    else:
        # Warning status removed for cleaner UI
        if status["error"]:
            st.error(f"Error: {status['error']}")
    
    # Connection action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Test Payroll Connection", type="primary"):
            with st.spinner("Testing connection..."):
                test_result = manager.test_connection()
                if test_result["success"]:
                    st.success(test_result["message"])
                else:
                    st.error(test_result["message"])
    
    with col2:
        if st.button("Show Table Info"):
            table_info = manager.get_table_info()
            if table_info["tables"]:
                st.write("**Available Tables:**")
                for table in table_info["tables"]:
                    st.write(f"- {table['name']}: {table['records']:,} records")
                st.write(f"**Total Records:** {table_info['total_records']:,}")
    
    with col3:
        if status["connected"]:
            if st.button("🔌 Disconnect Payroll", type="secondary", 
                        help="Completely disconnect payroll database and clear all cached data"):
                with st.spinner("Disconnecting payroll database..."):
                    if manager.disconnect_payroll():
                        st.success("✅ Payroll database disconnected completely!")
                        st.info("All cached data cleared. No fallback to old databases will occur.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to disconnect payroll database")
    
    # Connection type info
    st.markdown("---")
    st.markdown("**Connection Priority:**")
    st.markdown("1. 🖥️ **SQL Server** (live connection via ODBC)")
    st.markdown("2. 🗃️ **SQLite File** (uploaded databases)")
    st.markdown("3. ❌ **None** (no connection available)")
    
    if status["type"] == "none":
        st.info("💡 **To connect a payroll database:**\n"
                "- Configure SQL Server connection in Streamlit secrets, OR\n"
                "- Upload a SQLite database file")