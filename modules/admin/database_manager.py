"""
Database Manager Module - Multi-Database Connection Management
Allows Spanish Fork to connect up to 4 different databases for comprehensive data integration
"""

import streamlit as st
import os
import pandas as pd
from typing import Dict, List, Any
from modules.database.connection_manager import (
    get_available_databases, 
    update_database_connection, 
    update_database_connection_legacy,
    disconnect_database,
    test_database_file,
    test_connection,
    load_db_config,
    save_db_config
)

def render_database_manager():
    """Render the multi-database connection management interface"""
    
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 30px;">
        <h2 style="color: white; margin: 0;">Database Connection Manager</h2>
        <p style="color: white; margin: 10px 0 0 0; opacity: 0.9;">Connect up to 4 databases for comprehensive data integration</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get current database configuration
    databases = get_available_databases()
    
    # Database connection status overview
    st.markdown("### Connection Status Overview")
    
    if databases:
        # Ensure we have at least 1 database and limit to 4 columns
        num_databases = len(databases)
        if num_databases > 0:
            num_cols = min(4, num_databases)
            cols = st.columns(num_cols)
            
            for i, (db_name, db_info) in enumerate(databases.items()):
                # Only process databases that fit in our column layout
                col_index = i % num_cols  # Use modulo to wrap around if more than 4 databases
                if col_index < len(cols):
                    with cols[col_index]:
                        status_color = "#28a745" if db_info["status"] == "connected" else "#dc3545"
                        status_text = "✓ Connected" if db_info["status"] == "connected" else "○ Not Connected"
                        
                        st.markdown(f"""
                        <div style="border: 2px solid {status_color}; border-radius: 10px; padding: 15px; margin-bottom: 10px; background: white;">
                            <h4 style="margin: 0 0 5px 0; color: #333;">{db_info['display_name']}</h4>
                            <p style="margin: 0 0 10px 0; font-size: 0.9rem; color: #666;">{db_info['description']}</p>
                            <div style="color: {status_color}; font-weight: bold;">{status_text}</div>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.warning("No databases configured")
    
    st.markdown("---")
    
    # Database connection management
    st.markdown("### Manage Database Connections")
    
    # Select database to configure
    db_options = {name: info['display_name'] for name, info in databases.items()}
    selected_db = st.selectbox(
        "Select Database to Configure:",
        options=list(db_options.keys()),
        format_func=lambda x: db_options[x],
        help="Choose which database connection to configure"
    )
    
    if selected_db:
        db_info = databases[selected_db]
        
        st.markdown(f"#### Configuring: {db_info['display_name']}")
        st.write(f"**Purpose:** {db_info['description']}")
        
        # Current status
        if db_info['status'] == 'connected':
            # Show connection details based on database type
            if db_info['type'] == 'sqlite':
                st.success(f"✓ Currently connected to SQLite file: `{db_info['path']}`")
            else:
                st.success(f"✓ Currently connected to {db_info['type'].upper()} server: `{db_info['host']}:{db_info['port']}/{db_info['database']}`")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Test Connection", key=f"test_{selected_db}"):
                    with st.spinner("Testing connection..."):
                        test_result = test_connection(selected_db)
                        if test_result["success"]:
                            st.success(f"✓ Connection test successful!")
                            if test_result["server_info"]:
                                st.info(f"Server: {test_result['server_info']}")
                        else:
                            st.error(f"✗ Connection test failed: {test_result['error']}")
            
            with col2:
                if st.button(f"Disconnect", key=f"disconnect_{selected_db}", type="secondary"):
                    if disconnect_database(selected_db):
                        st.success(f"✓ {db_info['display_name']} disconnected successfully")
                        st.rerun()
                    else:
                        st.error("Failed to disconnect database")
        else:
            st.warning(f"○ {db_info['display_name']} is not connected")
            
            # Connection options based on database type
            st.markdown("##### Connect Database")
            
            # Get current database type or allow selection
            current_type = db_info.get('type', 'sqlite')
            
            # Database type selection
            db_type_options = ['sqlite', 'postgres', 'mysql', 'sqlserver']
            db_type_labels = {
                'sqlite': 'SQLite (File-based)',
                'postgres': 'PostgreSQL',
                'mysql': 'MySQL',
                'sqlserver': 'SQL Server'
            }
            
            selected_type = st.selectbox(
                "Database Type:",
                options=db_type_options,
                format_func=lambda x: db_type_labels[x],
                index=db_type_options.index(current_type) if current_type in db_type_options else 0,
                key=f"type_{selected_db}",
                help="Select the type of database to connect"
            )
            
            if selected_type == 'sqlite':
                # SQLite file upload option
                uploaded_file = st.file_uploader(
                    f"Upload {db_info['display_name']} SQLite File",
                    type=['db', 'sqlite', 'sqlite3'],
                    help=f"Upload the {db_info['display_name']} SQLite file to connect",
                    key=f"upload_{selected_db}"
                )
                
                if uploaded_file:
                    # Save uploaded file
                    file_path = f"databases/{selected_db}_{uploaded_file.name}"
                    os.makedirs("databases", exist_ok=True)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.read())
                    
                    # Test the uploaded database
                    test_result = test_database_file(file_path)
                    
                    if test_result['valid']:
                        st.success(f"✓ Valid database file uploaded ({len(test_result['tables'])} tables found)")
                        
                        # Show table preview
                        with st.expander("Database Tables Preview"):
                            if test_result['tables']:
                                st.write("**Tables found:**")
                                for table in test_result['tables']:
                                    st.write(f"- {table}")
                            else:
                                st.warning("No tables found in database")
                        
                        if st.button(f"Connect {db_info['display_name']}", key=f"connect_{selected_db}"):
                            if update_database_connection_legacy(selected_db, file_path, selected_type):
                                st.success(f"✓ {db_info['display_name']} connected successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to update database connection")
                    else:
                        st.error(f"✗ Invalid database file: {test_result['error']}")
                
                # Option 2: Manual path entry
                st.markdown("**OR**")
                
                manual_path = st.text_input(
                    f"Manual Path to {db_info['display_name']}",
                    placeholder="/path/to/your/database.db",
                    help="Enter the full path to your database file",
                    key=f"path_{selected_db}"
                )
                
                if manual_path:
                    if st.button(f"Connect via Path", key=f"connect_path_{selected_db}"):
                        test_result = test_database_file(manual_path)
                        
                        if test_result['valid']:
                            if update_database_connection_legacy(selected_db, manual_path, selected_type):
                                st.success(f"✓ {db_info['display_name']} connected successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to update database connection")
                        else:
                            st.error(f"✗ Invalid database file: {test_result['error']}")
            
            else:
                # Live database connection form
                st.markdown(f"**Connect to {db_type_labels[selected_type]} Server**")
                
                # Special handling for payroll database
                if selected_db == "payroll":
                    st.info("🔄 **Dual Connection Support**: This payroll database supports both SQLite files and SQL Server connections automatically.")
                    
                    # Show current payroll connection status
                    try:
                        from modules.navi.payroll_connection_manager import render_payroll_connection_status
                        render_payroll_connection_status()
                    except ImportError:
                        st.warning("Payroll connection manager not available")
                
                with st.form(f"live_db_form_{selected_db}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        host = st.text_input(
                            "Host/Server:",
                            value=db_info.get('host', 'localhost'),
                            help="Database server hostname or IP address"
                        )
                        
                        database = st.text_input(
                            "Database Name:",
                            value=db_info.get('database', ''),
                            help="Name of the database to connect to"
                        )
                        
                        username = st.text_input(
                            "Username:",
                            value=db_info.get('username', ''),
                            help="Database username"
                        )
                    
                    with col2:
                        # Default ports for each database type
                        default_ports = {
                            'postgres': '5432',
                            'mysql': '3306', 
                            'sqlserver': '1433'
                        }
                        
                        port = st.text_input(
                            "Port:",
                            value=db_info.get('port', default_ports.get(selected_type, '5432')),
                            help=f"Database server port (default: {default_ports.get(selected_type, '5432')})"
                        )
                        
                        password = st.text_input(
                            "Password:",
                            type="password",
                            help="Database password (will be stored securely)",
                            placeholder="Enter database password"
                        )
                        
                        # Add SSL/security options for production databases
                        use_ssl = st.checkbox(
                            "Use SSL/TLS",
                            value=True,
                            help="Enable secure connection (recommended for production)"
                        )
                    
                    submitted = st.form_submit_button(f"Connect to {db_type_labels[selected_type]}")
                    
                    if submitted:
                        if not all([host, database, username]):
                            st.error("Please fill in all required fields (Host, Database, Username)")
                        else:
                            # Test the connection first
                            connection_params = {
                                "type": selected_type,
                                "host": host,
                                "port": port,
                                "database": database,
                                "username": username,
                                "password": password
                            }
                            
                            # Temporarily update connection to test
                            if update_database_connection(selected_db, connection_params):
                                with st.spinner(f"Testing {db_type_labels[selected_type]} connection..."):
                                    test_result = test_connection(selected_db)
                                    
                                    if test_result["success"]:
                                        st.success(f"✓ Successfully connected to {db_type_labels[selected_type]}!")
                                        if test_result["server_info"]:
                                            st.info(f"Server: {test_result['server_info']}")
                                        st.rerun()
                                    else:
                                        # Connection failed, disconnect
                                        disconnect_database(selected_db)
                                        st.error(f"✗ Connection failed: {test_result['error']}")
                                        
                                        # Show common troubleshooting tips
                                        with st.expander("Troubleshooting Tips"):
                                            st.markdown(f"""
                                            **Common issues for {db_type_labels[selected_type]}:**
                                            
                                            1. **Network Access**: Ensure the database server is accessible from this application
                                            2. **Firewall**: Check that port {port} is open
                                            3. **Credentials**: Verify username and password are correct
                                            4. **Database Exists**: Confirm the database '{database}' exists on the server
                                            5. **Permissions**: Ensure the user has access to the specified database
                                            """)
                                            
                                            if selected_type == 'postgres':
                                                st.markdown("**PostgreSQL specific**: Check pg_hba.conf for connection permissions")
                                            elif selected_type == 'mysql':
                                                st.markdown("**MySQL specific**: Verify user has proper host permissions (not just localhost)")
                                            elif selected_type == 'sqlserver':
                                                st.markdown("**SQL Server specific**: Ensure SQL Server Authentication is enabled if using username/password")
                            else:
                                st.error("Failed to update database configuration")

def render_database_overview():
    """Render database overview and summary statistics"""
    
    st.markdown("### Connected Databases Summary")
    
    databases = get_available_databases()
    connected_dbs = {name: info for name, info in databases.items() if info['status'] == 'connected'}
    
    if not connected_dbs:
        st.info("No databases are currently connected. Use the Database Manager to connect your databases.")
        return
    
    # Summary statistics
    for db_name, db_info in connected_dbs.items():
        with st.expander(f"📊 {db_info['display_name']} Statistics", expanded=False):
            try:
                from modules.database.connection_manager import execute_query
                
                # Get basic table information
                tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
                tables_df = execute_query(tables_query, db_name=db_name)
                
                if not tables_df.empty:
                    st.write(f"**Tables:** {len(tables_df)} found")
                    
                    # Show table list
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Table Names:**")
                        for table in tables_df['name'].head(10):
                            st.write(f"- {table}")
                        if len(tables_df) > 10:
                            st.write(f"... and {len(tables_df) - 10} more")
                    
                    with col2:
                        # Try to get record counts for some tables
                        st.write("**Record Counts:**")
                        for table in tables_df['name'].head(5):
                            try:
                                count_query = f"SELECT COUNT(*) as count FROM `{table}`"
                                count_df = execute_query(count_query, db_name=db_name)
                                if not count_df.empty:
                                    st.write(f"- {table}: {count_df['count'].iloc[0]:,} records")
                            except:
                                st.write(f"- {table}: Unable to count")
                else:
                    st.warning("No tables found in this database")
                    
            except Exception as e:
                st.error(f"Error accessing database: {str(e)}")

def get_connected_databases() -> List[str]:
    """Get list of currently connected database names"""
    databases = get_available_databases()
    return [name for name, info in databases.items() if info['status'] == 'connected']

def get_database_selector() -> str:
    """Render database selector and return selected database"""
    connected_dbs = get_connected_databases()
    
    if not connected_dbs:
        st.warning("No databases connected. Please use the Database Manager to connect databases.")
        return None
    
    if len(connected_dbs) == 1:
        return connected_dbs[0]
    
    # Multiple databases available - show selector
    databases = get_available_databases()
    db_options = {name: databases[name]['display_name'] for name in connected_dbs}
    
    selected_db = st.selectbox(
        "Select Database:",
        options=connected_dbs,
        format_func=lambda x: db_options[x],
        help="Choose which database to query"
    )
    
    return selected_db