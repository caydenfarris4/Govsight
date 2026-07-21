"""
Central Connection Registry for Managing Multiple Database Connections
Handles live database selection and connection pooling
"""

import streamlit as st
import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib
import os
from pathlib import Path
import pandas as pd
from .caselle_adapter import CaselleServerAdapter, CaselleDatabaseSet


class ConnectionRegistry:
    """Singleton registry for managing all database connections"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.servers = {}  # server_id -> CaselleServerAdapter
            self.database_sets = {}  # set_id -> CaselleDatabaseSet
            self.live_connections = {}  # function -> (server_id, database_name)
            self.credentials = {}  # server_id -> encrypted credentials
            self._init_storage()
            self._load_configurations()
            ConnectionRegistry._initialized = True
    
    def _init_storage(self):
        """Initialize persistent storage for configurations"""
        db_path = Path("databases/core")
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.config_db = db_path / "erp_connections.db"
        
        # Create tables if they don't exist
        with sqlite3.connect(self.config_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    server_id TEXT PRIMARY KEY,
                    server_name TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER DEFAULT 1433,
                    instance TEXT,
                    auth_type TEXT DEFAULT 'windows',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    last_modified TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS database_sets (
                    set_id TEXT PRIMARY KEY,
                    set_name TEXT NOT NULL,
                    server_id TEXT NOT NULL,
                    organization TEXT,
                    gl_database TEXT,
                    ap_database TEXT,
                    payroll_database TEXT,
                    utility_database TEXT,
                    ar_database TEXT,
                    budget_database TEXT,
                    purchasing_database TEXT,
                    assets_database TEXT,
                    is_live BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES servers(server_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS live_mappings (
                    function TEXT PRIMARY KEY,
                    set_id TEXT NOT NULL,
                    database_name TEXT NOT NULL,
                    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activated_by TEXT,
                    FOREIGN KEY (set_id) REFERENCES database_sets(set_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    user TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def _load_configurations(self):
        """Load saved configurations from database"""
        with sqlite3.connect(self.config_db) as conn:
            # Load servers
            servers_df = pd.read_sql_query("SELECT * FROM servers WHERE is_active = 1", conn)
            for _, row in servers_df.iterrows():
                server_id = row['server_id']
                adapter = CaselleServerAdapter(
                    server=row['host'],
                    port=row['port'],
                    instance=row['instance']
                )
                self.servers[server_id] = adapter
            
            # Load database sets
            sets_df = pd.read_sql_query("SELECT * FROM database_sets", conn)
            for _, row in sets_df.iterrows():
                set_id = row['set_id']
                server_id = row['server_id']
                
                if server_id in self.servers:
                    db_set = CaselleDatabaseSet(row['set_name'], self.servers[server_id])
                    
                    # Assign databases
                    for func in ['GL', 'AP', 'PAYROLL', 'UTILITY', 'AR', 'BUDGET', 'PURCHASING', 'ASSETS']:
                        db_name = row.get(f"{func.lower()}_database")
                        if db_name:
                            db_set.assign_database(func, db_name)
                    
                    db_set.is_live = bool(row['is_live'])
                    self.database_sets[set_id] = db_set
            
            # Load live mappings
            mappings_df = pd.read_sql_query("SELECT * FROM live_mappings", conn)
            for _, row in mappings_df.iterrows():
                self.live_connections[row['function']] = (row['set_id'], row['database_name'])
    
    def add_server(self, server_id: str, server_name: str, host: str, 
                  port: int = 1433, instance: str = None, auth_type: str = 'windows',
                  username: str = None, password: str = None) -> bool:
        """Add a new server configuration"""
        try:
            # Create adapter
            adapter = CaselleServerAdapter(host, port, instance)
            
            # Test connection
            success, message = adapter.test_connection(username, password)
            if not success:
                st.error(f"Failed to connect to server: {message}")
                return False
            
            # Save to registry
            self.servers[server_id] = adapter
            
            # Store credentials securely (encrypted)
            if username and password:
                self._store_credentials(server_id, username, password)
            
            # Save to database
            with sqlite3.connect(self.config_db) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO servers 
                    (server_id, server_name, host, port, instance, auth_type, created_by, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (server_id, server_name, host, port, instance, auth_type,
                     st.session_state.get('username', 'system'), datetime.now()))
                
                self._audit_log(conn, 'SERVER_ADD', 'server', server_id, 
                              {'name': server_name, 'host': host})
                conn.commit()
            
            st.success(f"Server '{server_name}' added successfully!")
            return True
            
        except Exception as e:
            st.error(f"Failed to add server: {str(e)}")
            return False
    
    def discover_databases(self, server_id: str) -> List[Dict]:
        """Discover databases on a server"""
        if server_id not in self.servers:
            st.error(f"Server {server_id} not found")
            return []
        
        adapter = self.servers[server_id]
        creds = self._get_credentials(server_id)
        
        return adapter.discover_databases(
            username=creds.get('username') if creds else None,
            password=creds.get('password') if creds else None
        )
    
    def create_database_set(self, set_name: str, server_id: str, organization: str = None) -> str:
        """Create a new database set"""
        set_id = hashlib.md5(f"{server_id}_{set_name}_{datetime.now()}".encode()).hexdigest()[:16]
        
        if server_id not in self.servers:
            st.error(f"Server {server_id} not found")
            return None
        
        db_set = CaselleDatabaseSet(set_name, self.servers[server_id])
        self.database_sets[set_id] = db_set
        
        # Save to database
        with sqlite3.connect(self.config_db) as conn:
            conn.execute("""
                INSERT INTO database_sets 
                (set_id, set_name, server_id, organization, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (set_id, set_name, server_id, organization, datetime.now()))
            
            self._audit_log(conn, 'SET_CREATE', 'database_set', set_id,
                          {'name': set_name, 'server': server_id})
            conn.commit()
        
        return set_id
    
    def assign_database_to_set(self, set_id: str, function: str, database_name: str):
        """Assign a database to a function in a set"""
        if set_id not in self.database_sets:
            st.error(f"Database set {set_id} not found")
            return
        
        self.database_sets[set_id].assign_database(function, database_name)
        
        # Update database
        column_name = f"{function.lower()}_database"
        with sqlite3.connect(self.config_db) as conn:
            conn.execute(f"""
                UPDATE database_sets 
                SET {column_name} = ?, last_accessed = ?
                WHERE set_id = ?
            """, (database_name, datetime.now(), set_id))
            
            self._audit_log(conn, 'DATABASE_ASSIGN', 'database_set', set_id,
                          {'function': function, 'database': database_name})
            conn.commit()
    
    def activate_database_set(self, set_id: str):
        """Make a database set live"""
        if set_id not in self.database_sets:
            st.error(f"Database set {set_id} not found")
            return
        
        # Deactivate all other sets
        for sid, db_set in self.database_sets.items():
            db_set.is_live = (sid == set_id)
        
        # Update live mappings
        db_set = self.database_sets[set_id]
        self.live_connections.clear()
        
        with sqlite3.connect(self.config_db) as conn:
            # Clear existing live mappings
            conn.execute("DELETE FROM live_mappings")
            
            # Set new live mappings
            for function, database in db_set.databases.items():
                if database:
                    self.live_connections[function] = (set_id, database)
                    conn.execute("""
                        INSERT INTO live_mappings (function, set_id, database_name, activated_by)
                        VALUES (?, ?, ?, ?)
                    """, (function, set_id, database, st.session_state.get('username', 'system')))
            
            # Update database set status
            conn.execute("UPDATE database_sets SET is_live = 0")
            conn.execute("UPDATE database_sets SET is_live = 1 WHERE set_id = ?", (set_id,))
            
            self._audit_log(conn, 'SET_ACTIVATE', 'database_set', set_id, 
                          {'name': db_set.name})
            conn.commit()
        
        st.success(f"Database set '{db_set.name}' is now live!")
    
    def get_live_connection(self, function: str):
        """Get the live database connection for a function"""
        if function not in self.live_connections:
            return None
        
        set_id, database_name = self.live_connections[function]
        
        if set_id not in self.database_sets:
            return None
        
        db_set = self.database_sets[set_id]
        creds = self._get_credentials(db_set.server.server)
        
        return db_set.server.create_engine(
            database_name,
            username=creds.get('username') if creds else None,
            password=creds.get('password') if creds else None
        )
    
    def get_live_dataframe(self, function: str, query: str) -> pd.DataFrame:
        """Execute query on live database and return DataFrame"""
        if function not in self.live_connections:
            st.error(f"No live database configured for {function}")
            return pd.DataFrame()
        
        set_id, database_name = self.live_connections[function]
        db_set = self.database_sets[set_id]
        creds = self._get_credentials(db_set.server.server)
        
        return db_set.server.execute_query(
            database_name, query,
            username=creds.get('username') if creds else None,
            password=creds.get('password') if creds else None
        )
    
    def _store_credentials(self, server_id: str, username: str, password: str):
        """Store encrypted credentials"""
        # In production, use proper encryption
        # For now, storing in session state (will need secure vault)
        key = f"creds_{server_id}"
        st.session_state[key] = {
            'username': username,
            'password': password
        }
    
    def _get_credentials(self, server_id: str) -> Optional[Dict]:
        """Retrieve credentials for a server"""
        key = f"creds_{server_id}"
        return st.session_state.get(key)
    
    def _audit_log(self, conn, action: str, entity_type: str, entity_id: str, details: Dict):
        """Add entry to audit log"""
        conn.execute("""
            INSERT INTO audit_log (action, entity_type, entity_id, user, details)
            VALUES (?, ?, ?, ?, ?)
        """, (action, entity_type, entity_id, 
              st.session_state.get('username', 'system'),
              json.dumps(details)))
    
    def get_audit_log(self, limit: int = 100) -> pd.DataFrame:
        """Get audit log entries"""
        with sqlite3.connect(self.config_db) as conn:
            return pd.read_sql_query(f"""
                SELECT * FROM audit_log 
                ORDER BY timestamp DESC 
                LIMIT {limit}
            """, conn)
    
    def dispose_all(self):
        """Dispose all connections"""
        for server in self.servers.values():
            server.dispose_all_engines()


# Global registry instance
_registry = None

def get_registry() -> ConnectionRegistry:
    """Get the global connection registry instance"""
    global _registry
    if _registry is None:
        _registry = ConnectionRegistry()
    return _registry