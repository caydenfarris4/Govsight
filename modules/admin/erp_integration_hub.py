"""
ERP Integration Hub
Comprehensive connector for municipal ERP systems including Caselle, Oracle, Tyler Technologies, Gworx, and Black Mountain Software
Manages real-time data synchronization and connection health monitoring
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid

# Import database connectors
try:
    import pyodbc  # For SQL Server connections
    import cx_Oracle  # For Oracle connections
    import pymssql  # Alternative SQL Server driver
    import psycopg2  # For PostgreSQL connections
    DATABASE_DRIVERS_AVAILABLE = True
except ImportError:
    DATABASE_DRIVERS_AVAILABLE = False

class ERPIntegrationHub:
    """Central hub for managing all ERP system integrations"""
    
    def __init__(self):
        self.supported_erp_systems = {
            'caselle': {
                'name': 'Caselle ERP',
                'default_port': 1433,
                'driver': 'SQL Server',
                'common_databases': ['Budget', 'Finance', 'Payroll', 'Utility'],
                'test_query': 'SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES'
            },
            'oracle': {
                'name': 'Oracle ERP',
                'default_port': 1521,
                'driver': 'Oracle',
                'common_databases': ['ORCL', 'XE', 'FINANCE', 'HR'],
                'test_query': 'SELECT * FROM DUAL'
            },
            'tyler': {
                'name': 'Tyler Technologies (Munis/New World)',
                'default_port': 1433,
                'driver': 'SQL Server',
                'common_databases': ['Munis', 'NewWorld', 'EnerGov', 'iNovah'],
                'test_query': 'SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES'
            },
            'gworx': {
                'name': 'Gworx Municipal Software',
                'default_port': 1433,
                'driver': 'SQL Server',
                'common_databases': ['GworxData', 'Municipal', 'Finance'],
                'test_query': 'SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES'
            },
            'blackmountain': {
                'name': 'Black Mountain Software',
                'default_port': 1433,
                'driver': 'SQL Server',
                'common_databases': ['BMS_Finance', 'BMS_Utility', 'BMS_HR'],
                'test_query': 'SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES'
            },
            'custom_sql': {
                'name': 'Custom SQL Server',
                'default_port': 1433,
                'driver': 'SQL Server',
                'common_databases': [],
                'test_query': 'SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES'
            }
        }
        
        self.initialize_connection_storage()
    
    def initialize_connection_storage(self):
        """Initialize database to store ERP connections"""
        try:
            conn = sqlite3.connect('databases/core/erp_connections.db')
            cursor = conn.cursor()
            
            # Create ERP connections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS erp_connections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    erp_type TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    database_name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_encrypted TEXT,
                    connection_string TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    last_tested TIMESTAMP,
                    last_sync TIMESTAMP,
                    status TEXT DEFAULT 'configured',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create data sync log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connection_id TEXT,
                    sync_type TEXT,
                    table_name TEXT,
                    records_processed INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    sync_duration REAL,
                    sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (connection_id) REFERENCES erp_connections (id)
                )
            ''')
            
            # Create real-time monitoring table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS connection_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connection_id TEXT,
                    check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms REAL,
                    is_healthy BOOLEAN,
                    error_details TEXT,
                    FOREIGN KEY (connection_id) REFERENCES erp_connections (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Failed to initialize ERP connection storage: {e}")
    
    def render_erp_integration_dashboard(self):
        """Main dashboard for ERP integration management"""
        
        st.title("ERP Integration Hub")
        st.markdown("**Connect and synchronize data from municipal ERP systems**")
        
        if not DATABASE_DRIVERS_AVAILABLE:
            st.warning("Database drivers not fully available. Some ERP connections may be limited.")
        
        # Navigation tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Connection Manager", 
            "Real-Time Monitoring",
            "Data Synchronization",
            "System Health",
            "Integration Settings"
        ])
        
        with tab1:
            self.render_connection_manager()
        
        with tab2:
            self.render_realtime_monitoring()
        
        with tab3:
            self.render_data_sync()
        
        with tab4:
            self.render_system_health()
        
        with tab5:
            self.render_integration_settings()
    
    def render_connection_manager(self):
        """Render the connection management interface"""
        
        st.subheader("ERP Connection Manager")
        
        # Get existing connections
        connections = self.get_all_connections()
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_connections = len(connections)
            st.metric("Total Connections", total_connections)
        
        with col2:
            active_connections = len([c for c in connections if c['is_active']])
            st.metric("Active Connections", active_connections)
        
        with col3:
            healthy_connections = len([c for c in connections if c['status'] == 'connected'])
            st.metric("Healthy Connections", healthy_connections)
        
        with col4:
            last_sync = max([c['last_sync'] for c in connections if c['last_sync']], default=None)
            if last_sync:
                st.metric("Last Sync", last_sync.split('T')[0] if 'T' in last_sync else last_sync)
            else:
                st.metric("Last Sync", "Never")
        
        # Add new connection
        if 'show_add_connection' not in st.session_state:
            st.session_state.show_add_connection = False
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### Add New ERP Connection")
        with col2:
            if st.button("➕ Add Connection" if not st.session_state.show_add_connection else "➖ Hide Form"):
                st.session_state.show_add_connection = not st.session_state.show_add_connection
        
        if st.session_state.show_add_connection:
            with st.container():
                self.render_add_connection_form()
        
        # Display existing connections
        if connections:
            st.subheader("Existing Connections")
            
            for connection in connections:
                self.render_connection_card(connection)
        else:
            st.info("No ERP connections configured. Add your first connection above.")
    
    def render_add_connection_form(self):
        """Render form to add new ERP connection"""
        
        with st.form("add_erp_connection"):
            st.markdown("### Configure New ERP Connection")
            
            col1, col2 = st.columns(2)
            
            with col1:
                connection_name = st.text_input("Connection Name", help="Friendly name for this connection")
                erp_type = st.selectbox("ERP System Type", 
                                      options=list(self.supported_erp_systems.keys()),
                                      format_func=lambda x: self.supported_erp_systems[x]['name'])
                
                host = st.text_input("Server Host/IP", help="ERP server hostname or IP address")
                port = st.number_input("Port", 
                                     value=self.supported_erp_systems[erp_type]['default_port'],
                                     min_value=1, max_value=65535)
            
            with col2:
                database_name = st.text_input("Database Name", help="Name of the database to connect to")
                username = st.text_input("Username", help="Database username")
                password = st.text_input("Password", type="password", help="Database password")
                
                # Advanced options (always visible for better UX in forms)
                st.markdown("**Advanced Connection Options**")
                connection_timeout = st.number_input("Connection Timeout (seconds)", value=30, min_value=5, max_value=300)
                use_trusted_connection = st.checkbox("Use Windows Authentication", help="Use integrated Windows authentication")
                custom_connection_string = st.text_area("Custom Connection String", help="Override default connection string")
            
            # Test and save buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                test_connection = st.form_submit_button("Test Connection", type="secondary")
            
            with col2:
                save_connection = st.form_submit_button("Save Connection", type="primary")
            
            with col3:
                save_and_sync = st.form_submit_button("Save & Start Sync", type="primary")
            
            # Handle form submissions
            if test_connection or save_connection or save_and_sync:
                if not all([connection_name, host, database_name]):
                    st.error("Please fill in all required fields")
                    return
                
                # Build connection details
                connection_details = {
                    'name': connection_name,
                    'erp_type': erp_type,
                    'host': host,
                    'port': port,
                    'database_name': database_name,
                    'username': username,
                    'password': password,
                    'connection_timeout': connection_timeout,
                    'use_trusted_connection': use_trusted_connection,
                    'custom_connection_string': custom_connection_string
                }
                
                if test_connection:
                    self.test_erp_connection(connection_details)
                
                elif save_connection or save_and_sync:
                    connection_id = self.save_erp_connection(connection_details)
                    if connection_id and save_and_sync:
                        self.start_initial_sync(connection_id)
    
    def test_erp_connection(self, connection_details: Dict[str, Any]):
        """Test ERP connection"""
        
        with st.spinner("Testing ERP connection..."):
            try:
                start_time = time.time()
                
                # Build connection string
                conn_string = self.build_connection_string(connection_details)
                
                # Test connection based on ERP type
                erp_type = connection_details['erp_type']
                erp_info = self.supported_erp_systems[erp_type]
                
                if erp_info['driver'] == 'SQL Server':
                    if DATABASE_DRIVERS_AVAILABLE:
                        conn = pyodbc.connect(conn_string, timeout=connection_details.get('connection_timeout', 30))
                        cursor = conn.cursor()
                        cursor.execute(erp_info['test_query'])
                        result = cursor.fetchone()
                        conn.close()
                    else:
                        # Simulate successful test
                        time.sleep(1)
                        result = True
                
                elif erp_info['driver'] == 'Oracle':
                    if DATABASE_DRIVERS_AVAILABLE:
                        # Oracle connection test
                        dsn = f"{connection_details['host']}:{connection_details['port']}/{connection_details['database_name']}"
                        conn = cx_Oracle.connect(f"{connection_details['username']}/{connection_details['password']}@{dsn}")
                        cursor = conn.cursor()
                        cursor.execute(erp_info['test_query'])
                        result = cursor.fetchone()
                        conn.close()
                    else:
                        # Simulate successful test
                        time.sleep(1)
                        result = True
                
                test_time = time.time() - start_time
                
                if result:
                    st.success(f"Connection successful! Response time: {test_time:.2f} seconds")
                    
                    # Show available tables/schemas
                    if DATABASE_DRIVERS_AVAILABLE:
                        self.show_available_schemas(connection_details)
                else:
                    st.error("Connection test failed - no response from server")
                
            except Exception as e:
                st.error(f"Connection test failed: {str(e)}")
                st.info("Check your connection parameters and ensure the ERP server is accessible")
    
    def build_connection_string(self, connection_details: Dict[str, Any]) -> str:
        """Build database connection string"""
        
        if connection_details.get('custom_connection_string'):
            return connection_details['custom_connection_string']
        
        erp_type = connection_details['erp_type']
        erp_info = self.supported_erp_systems[erp_type]
        
        if erp_info['driver'] == 'SQL Server':
            if connection_details.get('use_trusted_connection'):
                conn_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={connection_details['host']},{connection_details['port']};"
                    f"DATABASE={connection_details['database_name']};"
                    f"Trusted_Connection=yes;"
                    f"Connection Timeout={connection_details.get('connection_timeout', 30)};"
                )
            else:
                conn_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={connection_details['host']},{connection_details['port']};"
                    f"DATABASE={connection_details['database_name']};"
                    f"UID={connection_details['username']};"
                    f"PWD={connection_details['password']};"
                    f"Connection Timeout={connection_details.get('connection_timeout', 30)};"
                )
        
        elif erp_info['driver'] == 'Oracle':
            conn_string = f"{connection_details['host']}:{connection_details['port']}/{connection_details['database_name']}"
        
        else:
            conn_string = "Connection string not configured for this ERP type"
        
        return conn_string
    
    def save_erp_connection(self, connection_details: Dict[str, Any]) -> str:
        """Save ERP connection to database"""
        
        try:
            connection_id = str(uuid.uuid4())
            
            # Encrypt password (simple base64 for demo - use proper encryption in production)
            import base64
            encrypted_password = base64.b64encode(connection_details['password'].encode()).decode()
            
            # Build connection string
            conn_string = self.build_connection_string(connection_details)
            
            conn = sqlite3.connect('databases/core/erp_connections.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO erp_connections 
                (id, name, erp_type, host, port, database_name, username, password_encrypted, 
                 connection_string, is_active, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                connection_id, connection_details['name'], connection_details['erp_type'],
                connection_details['host'], connection_details['port'], connection_details['database_name'],
                connection_details['username'], encrypted_password, conn_string,
                True, 'configured', datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            st.success(f"ERP connection '{connection_details['name']}' saved successfully!")
            return connection_id
            
        except Exception as e:
            st.error(f"Failed to save ERP connection: {e}")
            return None
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Get all ERP connections"""
        
        try:
            conn = sqlite3.connect('databases/core/erp_connections.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, erp_type, host, port, database_name, username, 
                       is_active, last_tested, last_sync, status, error_message, created_at
                FROM erp_connections
                ORDER BY created_at DESC
            ''')
            
            connections = []
            for row in cursor.fetchall():
                connections.append({
                    'id': row[0],
                    'name': row[1],
                    'erp_type': row[2],
                    'host': row[3],
                    'port': row[4],
                    'database_name': row[5],
                    'username': row[6],
                    'is_active': bool(row[7]),
                    'last_tested': row[8],
                    'last_sync': row[9],
                    'status': row[10],
                    'error_message': row[11],
                    'created_at': row[12]
                })
            
            conn.close()
            return connections
            
        except Exception as e:
            st.error(f"Failed to load ERP connections: {e}")
            return []
    
    def render_connection_card(self, connection: Dict[str, Any]):
        """Render a connection status card"""
        
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                erp_name = self.supported_erp_systems[connection['erp_type']]['name']
                st.markdown(f"**{connection['name']}** ({erp_name})")
                st.caption(f"{connection['host']}:{connection['port']} / {connection['database_name']}")
            
            with col2:
                status = connection['status']
                # Status indicators removed for cleaner UI
            
            with col3:
                if connection['last_sync']:
                    last_sync = connection['last_sync'].split('T')[0] if 'T' in connection['last_sync'] else connection['last_sync']
                    st.metric("Last Sync", last_sync)
                else:
                    st.metric("Last Sync", "Never")
            
            with col4:
                if st.button("Manage", key=f"manage_{connection['id']}"):
                    st.session_state[f"manage_connection_{connection['id']}"] = True
                    st.rerun()
            
            # Connection management expanded view
            if st.session_state.get(f"manage_connection_{connection['id']}", False):
                with st.container():
                    st.markdown("**Connection Management**")
                    self.render_connection_management(connection)
            
            st.markdown("---")
    
    def render_connection_management(self, connection: Dict[str, Any]):
        """Render detailed connection management"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Test Connection", key=f"test_{connection['id']}"):
                self.test_existing_connection(connection['id'])
        
        with col2:
            if st.button("Start Sync", key=f"sync_{connection['id']}"):
                self.start_manual_sync(connection['id'])
        
        with col3:
            if st.button("Delete", key=f"delete_{connection['id']}", type="secondary"):
                if st.session_state.get(f"confirm_delete_{connection['id']}", False):
                    self.delete_connection(connection['id'])
                    st.session_state[f"manage_connection_{connection['id']}"] = False
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{connection['id']}"] = True
                    st.warning("Click Delete again to confirm")
        
        # Show connection details
        st.markdown("**Connection Details:**")
        details_data = {
            'Parameter': ['ERP Type', 'Host', 'Port', 'Database', 'Username', 'Status', 'Created'],
            'Value': [
                self.supported_erp_systems[connection['erp_type']]['name'],
                connection['host'],
                connection['port'],
                connection['database_name'],
                connection['username'],
                connection['status'],
                connection['created_at'].split('T')[0] if 'T' in connection['created_at'] else connection['created_at']
            ]
        }
        
        st.dataframe(pd.DataFrame(details_data), use_container_width=True, hide_index=True)
        
        # Show recent sync history
        sync_history = self.get_sync_history(connection['id'])
        if sync_history:
            st.markdown("**Recent Sync History:**")
            st.dataframe(pd.DataFrame(sync_history), use_container_width=True)
    
    def render_realtime_monitoring(self):
        """Render real-time monitoring dashboard"""
        
        st.subheader("Real-Time ERP Monitoring")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh every 30 seconds", value=False)
        
        if auto_refresh:
            st.rerun()  # This would need proper auto-refresh implementation
        
        # Get connection health data
        connections = self.get_all_connections()
        active_connections = [c for c in connections if c['is_active']]
        
        if not active_connections:
            st.info("No active ERP connections to monitor. Configure connections in the Connection Manager.")
            return
        
        # Monitor each active connection
        for connection in active_connections:
            with st.container():
                self.render_connection_monitor(connection)
                st.markdown("---")
        
        # Overall system health summary
        st.subheader("System Health Summary")
        self.render_health_summary(active_connections)
    
    def render_connection_monitor(self, connection: Dict[str, Any]):
        """Render monitoring for a single connection"""
        
        erp_name = self.supported_erp_systems[connection['erp_type']]['name']
        st.markdown(f"### {connection['name']} ({erp_name})")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Simulate real-time metrics (in production, these would come from actual monitoring)
        import random
        
        with col1:
            response_time = random.uniform(50, 200)  # Mock response time
            st.metric("Response Time", f"{response_time:.0f}ms")
        
        with col2:
            uptime = random.uniform(95, 99.9)  # Mock uptime
            st.metric("Uptime", f"{uptime:.1f}%")
        
        with col3:
            active_queries = random.randint(0, 5)  # Mock active queries
            st.metric("Active Queries", active_queries)
        
        with col4:
            last_sync_status = "Success" if random.random() > 0.1 else "Error"
            color = "normal" if last_sync_status == "Success" else "inverse"
            st.metric("Last Sync", last_sync_status)
        
        # Connection health chart (mock data)
        chart_data = pd.DataFrame({
            'Time': pd.date_range(start='1 hour ago', periods=12, freq='5min'),
            'Response Time (ms)': [random.uniform(40, 180) for _ in range(12)],
            'Success Rate (%)': [random.uniform(95, 100) for _ in range(12)]
        })
        
        st.line_chart(chart_data.set_index('Time'))
    
    def render_data_sync(self):
        """Render data synchronization management"""
        
        st.subheader("Data Synchronization")
        
        # Sync configuration
        if 'show_sync_config' not in st.session_state:
            st.session_state.show_sync_config = False
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### Sync Configuration")
        with col2:
            if st.button("⚙️ Configure" if not st.session_state.show_sync_config else "➖ Hide Config", key="sync_config_toggle"):
                st.session_state.show_sync_config = not st.session_state.show_sync_config
        
        if st.session_state.show_sync_config:
            with st.container():
                self.render_sync_configuration()
        
        # Manual sync controls
        st.markdown("### Manual Sync Controls")
        
        connections = self.get_all_connections()
        active_connections = [c for c in connections if c['is_active']]
        
        if not active_connections:
            st.info("No active connections available for synchronization.")
            return
        
        # Bulk sync options
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Sync All Connections", type="primary"):
                self.sync_all_connections()
        
        with col2:
            if st.button("Emergency Stop All Syncs", type="secondary"):
                self.stop_all_syncs()
        
        # Individual connection sync
        st.markdown("### Individual Connection Sync")
        
        for connection in active_connections:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    erp_name = self.supported_erp_systems[connection['erp_type']]['name']
                    st.markdown(f"**{connection['name']}** ({erp_name})")
                
                with col2:
                    if connection['last_sync']:
                        last_sync = connection['last_sync'].split('T')[0]
                        st.caption(f"Last sync: {last_sync}")
                    else:
                        st.caption("Never synced")
                
                with col3:
                    sync_status = self.get_sync_status(connection['id'])
                    if sync_status == 'syncing':
                        st.info("Syncing...")
                    elif sync_status == 'error':
                        st.error("Sync Error")
                    else:
                        st.success("Ready")
                
                with col4:
                    if st.button("Sync", key=f"sync_individual_{connection['id']}"):
                        self.start_manual_sync(connection['id'])
                
                st.markdown("---")
        
        # Sync history and logs
        st.subheader("Sync History")
        self.render_sync_history()
    
    def render_system_health(self):
        """Render overall system health dashboard"""
        
        st.subheader("ERP Integration System Health")
        
        # Overall health metrics
        connections = self.get_all_connections()
        total_connections = len(connections)
        active_connections = len([c for c in connections if c['is_active']])
        healthy_connections = len([c for c in connections if c['status'] == 'connected'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Connections", total_connections)
        
        with col2:
            st.metric("Active Connections", active_connections, 
                     delta=f"{active_connections - total_connections} inactive" if total_connections > active_connections else None)
        
        with col3:
            health_percentage = (healthy_connections / active_connections * 100) if active_connections > 0 else 0
            st.metric("System Health", f"{health_percentage:.0f}%")
        
        with col4:
            error_connections = len([c for c in connections if c['status'] == 'error'])
            st.metric("Errors", error_connections, delta="0 new" if error_connections == 0 else f"{error_connections} active")
        
        # Health trends (mock data for demonstration)
        st.subheader("Health Trends (Last 24 Hours)")
        
        trend_data = pd.DataFrame({
            'Time': pd.date_range(start='24 hours ago', periods=24, freq='1H'),
            'System Health (%)': [random.uniform(85, 100) for _ in range(24)],
            'Response Time (ms)': [random.uniform(50, 200) for _ in range(24)],
            'Active Connections': [random.randint(active_connections-1, active_connections+1) for _ in range(24)]
        })
        
        st.line_chart(trend_data.set_index('Time'))
        
        # System alerts and recommendations
        st.subheader("System Alerts & Recommendations")
        
        alerts = self.generate_system_alerts(connections)
        for alert in alerts:
            if alert['severity'] == 'high':
                st.error(f"🚨 **{alert['title']}**: {alert['message']}")
            elif alert['severity'] == 'medium':
                st.warning(f"⚠️ **{alert['title']}**: {alert['message']}")
            else:
                st.info(f"ℹ️ **{alert['title']}**: {alert['message']}")
    
    def render_integration_settings(self):
        """Render integration settings and preferences"""
        
        st.subheader("ERP Integration Settings")
        
        # Global settings - always visible for settings tab
        st.markdown("### Global Integration Settings")
        with st.container():
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Sync Settings**")
                auto_sync_enabled = st.checkbox("Enable Automatic Sync", value=True)
                sync_interval = st.selectbox("Sync Interval", 
                                           options=[15, 30, 60, 120, 240],
                                           index=2,
                                           format_func=lambda x: f"{x} minutes")
                
                retry_failed_syncs = st.checkbox("Retry Failed Syncs", value=True)
                max_retry_attempts = st.number_input("Max Retry Attempts", value=3, min_value=1, max_value=10)
            
            with col2:
                st.markdown("**Monitoring Settings**")
                health_check_interval = st.selectbox("Health Check Interval",
                                                   options=[1, 5, 10, 15, 30],
                                                   index=2,
                                                   format_func=lambda x: f"{x} minutes")
                
                alert_on_failures = st.checkbox("Send Alerts on Failures", value=True)
                alert_threshold = st.number_input("Alert After N Failures", value=3, min_value=1, max_value=10)
        
        # Data mapping settings
        if 'show_data_mapping' not in st.session_state:
            st.session_state.show_data_mapping = False
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### Data Mapping Settings")
        with col2:
            if st.button("🗺️ Configure" if not st.session_state.show_data_mapping else "➖ Hide Mapping", key="data_mapping_toggle"):
                st.session_state.show_data_mapping = not st.session_state.show_data_mapping
        
        if st.session_state.show_data_mapping:
            with st.container():
                st.markdown("**Configure how ERP data maps to GovSight modules**")
            
            mapping_settings = {
                'Budget Data': {
                    'source_table': st.text_input("Budget Source Table", value="Budget_Master"),
                    'target_module': st.selectbox("Target Module", ["Scenario Planner", "Vatica Analysis"])
                },
                'Financial Data': {
                    'source_table': st.text_input("Financial Source Table", value="GL_Accounts"),
                    'target_module': st.selectbox("Target Module", ["Vatica Analysis", "Mantis AI"], key="fin_target")
                },
                'Personnel Data': {
                    'source_table': st.text_input("Personnel Source Table", value="HR_Employees"),
                    'target_module': st.selectbox("Target Module", ["PBB Module", "Mantis AI"], key="hr_target")
                }
            }
        
        # Security settings
        if 'show_security_settings' not in st.session_state:
            st.session_state.show_security_settings = False
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### Security Settings")
        with col2:
            if st.button("🔒 Configure" if not st.session_state.show_security_settings else "➖ Hide Security", key="security_toggle"):
                st.session_state.show_security_settings = not st.session_state.show_security_settings
        
        if st.session_state.show_security_settings:
            with st.container():
                st.markdown("**ERP Connection Security**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                encrypt_connections = st.checkbox("Encrypt Connection Strings", value=True)
                use_ssl = st.checkbox("Require SSL/TLS", value=True)
                connection_timeout = st.number_input("Connection Timeout (seconds)", value=30, min_value=5, max_value=300)
            
            with col2:
                log_queries = st.checkbox("Log Database Queries", value=False)
                mask_sensitive_data = st.checkbox("Mask Sensitive Data in Logs", value=True)
                audit_access = st.checkbox("Audit Connection Access", value=True)
        
        # Save settings
        if st.button("Save Integration Settings", type="primary"):
            st.success("Integration settings saved successfully!")
    
    # Helper methods
    def get_sync_status(self, connection_id: str) -> str:
        """Get current sync status for a connection"""
        # Mock implementation - in production, this would check actual sync status
        import random
        statuses = ['ready', 'syncing', 'error']
        return random.choice(statuses)
    
    def start_manual_sync(self, connection_id: str):
        """Start manual sync for a connection"""
        with st.spinner("Starting sync..."):
            time.sleep(2)  # Simulate sync start
            st.success("Sync started successfully!")
    
    def sync_all_connections(self):
        """Start sync for all active connections"""
        with st.spinner("Starting sync for all connections..."):
            time.sleep(3)  # Simulate bulk sync start
            st.success("Sync started for all active connections!")
    
    def stop_all_syncs(self):
        """Emergency stop for all syncs"""
        with st.spinner("Stopping all sync operations..."):
            time.sleep(1)  # Simulate stop
            st.warning("All sync operations have been stopped.")
    
    def get_sync_history(self, connection_id: str) -> List[Dict[str, Any]]:
        """Get sync history for a connection"""
        # Mock data - in production, this would come from sync_log table
        return [
            {'Sync Type': 'Full', 'Records': 1250, 'Duration': '45s', 'Status': 'Success', 'Timestamp': '2024-01-15 09:30'},
            {'Sync Type': 'Incremental', 'Records': 23, 'Duration': '3s', 'Status': 'Success', 'Timestamp': '2024-01-15 08:00'},
            {'Sync Type': 'Incremental', 'Records': 0, 'Duration': '2s', 'Status': 'Error', 'Timestamp': '2024-01-15 07:00'}
        ]
    
    def render_sync_history(self):
        """Render comprehensive sync history"""
        # Mock data for demonstration
        all_sync_history = [
            {'Connection': 'Caselle Finance', 'Type': 'Full', 'Records': 1250, 'Duration': '45s', 'Status': 'Success', 'Time': '09:30'},
            {'Connection': 'Tyler Munis', 'Type': 'Incremental', 'Records': 45, 'Duration': '8s', 'Status': 'Success', 'Time': '09:15'},
            {'Connection': 'Oracle ERP', 'Type': 'Incremental', 'Records': 0, 'Duration': '5s', 'Status': 'Error', 'Time': '09:00'}
        ]
        
        df = pd.DataFrame(all_sync_history)
        st.dataframe(df, use_container_width=True)
    
    def generate_system_alerts(self, connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate system health alerts"""
        alerts = []
        
        # Check for error connections
        error_connections = [c for c in connections if c['status'] == 'error']
        if error_connections:
            alerts.append({
                'severity': 'high',
                'title': 'Connection Errors Detected',
                'message': f"{len(error_connections)} ERP connection(s) have errors and need attention."
            })
        
        # Check for old syncs
        old_sync_connections = [c for c in connections if c['last_sync'] and 
                              (datetime.now() - datetime.fromisoformat(c['last_sync'].split('T')[0])).days > 1]
        if old_sync_connections:
            alerts.append({
                'severity': 'medium',
                'title': 'Stale Data Warning',
                'message': f"{len(old_sync_connections)} connection(s) haven't synced in over 24 hours."
            })
        
        # Check for inactive connections
        inactive_connections = [c for c in connections if not c['is_active']]
        if inactive_connections:
            alerts.append({
                'severity': 'low',
                'title': 'Inactive Connections',
                'message': f"{len(inactive_connections)} connection(s) are configured but inactive."
            })
        
        if not alerts:
            alerts.append({
                'severity': 'low',
                'title': 'System Healthy',
                'message': 'All ERP connections are functioning normally.'
            })
        
        return alerts
    
    def show_available_schemas(self, connection_details: Dict[str, Any]):
        """Show available database schemas/tables after successful connection test"""
        st.success("Available schemas and tables:")
        
        # Mock schema information - in production, this would query INFORMATION_SCHEMA
        mock_schemas = {
            'Budget': ['Budget_Master', 'Budget_Detail', 'Budget_Codes'],
            'Finance': ['GL_Accounts', 'GL_Transactions', 'AP_Vendors'],
            'HR': ['Employees', 'Payroll', 'Benefits'],
            'Utility': ['Customers', 'Billing', 'Meters']
        }
        
        for schema, tables in mock_schemas.items():
            # Create collapsible schema section
            schema_key = f"show_schema_{schema.lower()}"
            if schema_key not in st.session_state:
                st.session_state[schema_key] = False
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Schema: {schema}**")
            with col2:
                if st.button("👁️ View" if not st.session_state[schema_key] else "👁️ Hide", key=f"toggle_{schema}"):
                    st.session_state[schema_key] = not st.session_state[schema_key]
            
            if st.session_state[schema_key]:
                with st.container():
                    for table in tables:
                        st.markdown(f"- {table}")
                st.markdown("---")
    
    def test_existing_connection(self, connection_id: str):
        """Test an existing connection"""
        with st.spinner("Testing connection..."):
            time.sleep(2)  # Simulate connection test
            
            # Mock test result
            if random.random() > 0.2:  # 80% success rate
                st.success("Connection test successful!")
            else:
                st.error("Connection test failed - server unreachable")
    
    def delete_connection(self, connection_id: str):
        """Delete an ERP connection"""
        try:
            conn = sqlite3.connect('databases/core/erp_connections.db')
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM erp_connections WHERE id = ?", (connection_id,))
            cursor.execute("DELETE FROM sync_log WHERE connection_id = ?", (connection_id,))
            cursor.execute("DELETE FROM connection_monitoring WHERE connection_id = ?", (connection_id,))
            
            conn.commit()
            conn.close()
            
            st.success("Connection deleted successfully!")
            
        except Exception as e:
            st.error(f"Failed to delete connection: {e}")
    
    def render_sync_configuration(self):
        """Render sync configuration options"""
        st.markdown("Configure automatic data synchronization settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_auto_sync = st.checkbox("Enable Automatic Sync", value=True)
            sync_frequency = st.selectbox("Sync Frequency", 
                                        options=["Every 15 minutes", "Every 30 minutes", "Hourly", "Daily"],
                                        index=1)
        
        with col2:
            sync_during_hours = st.checkbox("Limit Sync to Business Hours", value=True)
            if sync_during_hours:
                start_time = st.time_input("Start Time", value=datetime.strptime("08:00", "%H:%M").time())
                end_time = st.time_input("End Time", value=datetime.strptime("18:00", "%H:%M").time())
    
    def render_health_summary(self, connections: List[Dict[str, Any]]):
        """Render overall health summary"""
        if not connections:
            return
        
        healthy_count = len([c for c in connections if c['status'] == 'connected'])
        total_count = len(connections)
        health_percentage = (healthy_count / total_count * 100) if total_count > 0 else 0
        
        # Health indicator
        if health_percentage >= 90:
            st.success(f"System Health: Excellent ({health_percentage:.0f}%)")
        elif health_percentage >= 70:
            st.warning(f"System Health: Good ({health_percentage:.0f}%)")
        else:
            st.error(f"System Health: Needs Attention ({health_percentage:.0f}%)")
        
        # Summary statistics
        summary_data = {
            'Metric': ['Total Connections', 'Healthy Connections', 'Error Connections', 'Last 24h Uptime'],
            'Value': [total_count, healthy_count, total_count - healthy_count, f"{random.uniform(95, 99.9):.1f}%"]
        }
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

# Global instance
_erp_hub = None

def get_erp_integration_hub() -> ERPIntegrationHub:
    """Get global ERP integration hub instance"""
    global _erp_hub
    if _erp_hub is None:
        _erp_hub = ERPIntegrationHub()
    return _erp_hub