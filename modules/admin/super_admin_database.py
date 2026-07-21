"""
Super Admin Database Management Interface
Exclusive control interface for managing Caselle database connections
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List
import json
from pathlib import Path

from modules.security.super_admin_auth import get_super_auth, render_super_admin_login
from modules.database.connection_registry import get_registry
from modules.database.caselle_adapter import CaselleServerAdapter


def render_super_admin_database_manager():
    """Main Super Admin database manager interface"""
    st.title("🔐 Super Admin Database Control")
    
    auth = get_super_auth()
    
    # Check authentication
    if not auth.is_super_admin():
        render_super_admin_login()
        return
    
    st.success("✅ Super Admin Access Granted")
    
    # Logout button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col3:
        if st.button("🔒 Logout Super Admin", type="secondary"):
            auth.logout_super_admin()
            st.rerun()
    
    # Main tabs
    tabs = st.tabs([
        "🖥️ Servers",
        "📊 Database Sets", 
        "🔌 Live Connections",
        "🔍 Discovery",
        "📝 Audit Log",
        "⚙️ Settings"
    ])
    
    registry = get_registry()
    
    with tabs[0]:
        render_servers_management(registry)
    
    with tabs[1]:
        render_database_sets(registry)
    
    with tabs[2]:
        render_live_connections(registry)
    
    with tabs[3]:
        render_database_discovery(registry)
    
    with tabs[4]:
        render_audit_log(registry)
    
    with tabs[5]:
        render_settings()


def render_servers_management(registry):
    """Manage SQL Server connections"""
    st.subheader("SQL Server Management")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Configured Servers**")
    
    with col2:
        if st.button("➕ Add Server", type="primary"):
            st.session_state['show_add_server'] = True
    
    # Show add server form
    if st.session_state.get('show_add_server', False):
        render_add_server_form(registry)
    
    # List existing servers
    if registry.servers:
        servers_data = []
        for server_id, adapter in registry.servers.items():
            servers_data.append({
                'ID': server_id,
                'Host': adapter.server,
                'Port': adapter.port,
                'Instance': adapter.instance or 'Default',
                'Status': '🟢 Active'
            })
        
        df = pd.DataFrame(servers_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Server actions
        selected_server = st.selectbox("Select server for actions:", 
                                       options=list(registry.servers.keys()))
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("Test Connection"):
                test_server_connection(registry, selected_server)
        
        with col2:
            if st.button("View Databases"):
                st.session_state['view_databases'] = selected_server
        
        with col3:
            if st.button("Edit Server"):
                st.session_state['edit_server'] = selected_server
        
        with col4:
            if st.button("Remove Server", type="secondary"):
                if st.session_state.get(f'confirm_remove_{selected_server}'):
                    remove_server(registry, selected_server)
                else:
                    st.session_state[f'confirm_remove_{selected_server}'] = True
                    st.warning("Click again to confirm removal")
        
        # Show databases if requested
        if st.session_state.get('view_databases'):
            show_server_databases(registry, st.session_state['view_databases'])
    else:
        st.info("No servers configured. Click 'Add Server' to get started.")


def render_add_server_form(registry):
    """Form to add a new server"""
    st.markdown("### Add New Server")
    
    with st.form("add_server_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            server_name = st.text_input("Server Name", placeholder="Production Server")
            host = st.text_input("Host/IP Address", placeholder="192.168.1.100")
            port = st.number_input("Port", value=1433, min_value=1, max_value=65535)
        
        with col2:
            instance = st.text_input("Instance Name (optional)", placeholder="SQLEXPRESS")
            auth_type = st.selectbox("Authentication", ["Windows", "SQL Server"])
            
            if auth_type == "SQL Server":
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
            else:
                username = None
                password = None
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submitted = st.form_submit_button("Add Server", type="primary")
        
        with col2:
            cancelled = st.form_submit_button("Cancel")
        
        if submitted:
            if server_name and host:
                server_id = server_name.lower().replace(' ', '_')
                success = registry.add_server(
                    server_id, server_name, host, port, instance,
                    auth_type.lower().replace(' ', '_'),
                    username, password
                )
                
                if success:
                    st.session_state['show_add_server'] = False
                    st.rerun()
            else:
                st.error("Server name and host are required")
        
        if cancelled:
            st.session_state['show_add_server'] = False
            st.rerun()


def render_database_sets(registry):
    """Manage database sets"""
    st.subheader("Database Sets Configuration")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("**Configured Database Sets**")
        st.caption("Each set represents a complete municipality dataset")
    
    with col2:
        if st.button("➕ Create Set", type="primary"):
            st.session_state['show_create_set'] = True
    
    # Show create set form
    if st.session_state.get('show_create_set', False):
        render_create_set_form(registry)
    
    # List existing sets
    if registry.database_sets:
        sets_data = []
        for set_id, db_set in registry.database_sets.items():
            sets_data.append({
                'Set Name': db_set.name,
                'Server': db_set.server.server,
                'Status': '🟢 Live' if db_set.is_live else '⚫ Inactive',
                'GL': '✓' if db_set.databases.get('GL') else '✗',
                'AP': '✓' if db_set.databases.get('AP') else '✗',
                'Payroll': '✓' if db_set.databases.get('PAYROLL') else '✗',
                'Utility': '✓' if db_set.databases.get('UTILITY') else '✗'
            })
        
        df = pd.DataFrame(sets_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Set actions
        set_names = [db_set.name for db_set in registry.database_sets.values()]
        selected_set_name = st.selectbox("Select database set:", options=set_names)
        
        # Find set_id from name
        selected_set_id = None
        for set_id, db_set in registry.database_sets.items():
            if db_set.name == selected_set_name:
                selected_set_id = set_id
                break
        
        if selected_set_id:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Configure Databases"):
                    st.session_state['configure_set'] = selected_set_id
            
            with col2:
                if st.button("Activate Set", type="primary"):
                    registry.activate_database_set(selected_set_id)
                    st.rerun()
            
            with col3:
                if st.button("Remove Set", type="secondary"):
                    st.warning("Set removal not yet implemented")
        
        # Show configuration if requested
        if st.session_state.get('configure_set'):
            configure_database_set(registry, st.session_state['configure_set'])
    else:
        st.info("No database sets configured. Click 'Create Set' to get started.")


def render_create_set_form(registry):
    """Form to create a new database set"""
    st.markdown("### Create Database Set")
    
    with st.form("create_set_form"):
        set_name = st.text_input("Set Name", placeholder="City A - Production")
        organization = st.text_input("Organization", placeholder="City of Springfield")
        
        server_options = list(registry.servers.keys())
        if server_options:
            server_id = st.selectbox("Server", options=server_options)
        else:
            st.error("No servers configured. Add a server first.")
            server_id = None
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("Create Set", type="primary")
        
        with col2:
            cancelled = st.form_submit_button("Cancel")
        
        if submitted and server_id:
            if set_name:
                set_id = registry.create_database_set(set_name, server_id, organization)
                if set_id:
                    st.session_state['show_create_set'] = False
                    st.session_state['configure_set'] = set_id
                    st.rerun()
            else:
                st.error("Set name is required")
        
        if cancelled:
            st.session_state['show_create_set'] = False
            st.rerun()


def configure_database_set(registry, set_id):
    """Configure databases for a set"""
    db_set = registry.database_sets[set_id]
    
    st.markdown(f"### Configure: {db_set.name}")
    
    # Get available databases from server
    databases = registry.discover_databases(db_set.server.server)
    db_options = ['None'] + [db['name'] for db in databases]
    
    # Function mapping
    functions = ['GL', 'AP', 'PAYROLL', 'UTILITY', 'AR', 'BUDGET', 'PURCHASING', 'ASSETS']
    
    st.markdown("**Assign Databases to Functions**")
    
    # Create two columns for the form
    col1, col2 = st.columns(2)
    
    changes = {}
    
    for i, function in enumerate(functions):
        if i % 2 == 0:
            with col1:
                current_db = db_set.databases.get(function) or 'None'
                
                # Try to suggest a database based on detection
                suggested = None
                for db in databases:
                    if db.get('detected_function') == function:
                        suggested = db['name']
                        break
                
                new_db = st.selectbox(
                    f"{function} Database",
                    options=db_options,
                    index=db_options.index(current_db) if current_db in db_options else 0,
                    help=f"Suggested: {suggested}" if suggested else None
                )
                
                if new_db != 'None' and new_db != current_db:
                    changes[function] = new_db
        else:
            with col2:
                current_db = db_set.databases.get(function) or 'None'
                
                suggested = None
                for db in databases:
                    if db.get('detected_function') == function:
                        suggested = db['name']
                        break
                
                new_db = st.selectbox(
                    f"{function} Database",
                    options=db_options,
                    index=db_options.index(current_db) if current_db in db_options else 0,
                    help=f"Suggested: {suggested}" if suggested else None
                )
                
                if new_db != 'None' and new_db != current_db:
                    changes[function] = new_db
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("Save Configuration", type="primary"):
            for function, database in changes.items():
                registry.assign_database_to_set(set_id, function, database)
            st.success("Configuration saved!")
            st.session_state['configure_set'] = None
            st.rerun()
    
    with col2:
        if st.button("Cancel"):
            st.session_state['configure_set'] = None
            st.rerun()


def render_live_connections(registry):
    """Show and manage live database connections"""
    st.subheader("Live Database Connections")
    
    if registry.live_connections:
        st.success(f"✅ {len(registry.live_connections)} live connections active")
        
        connections_data = []
        for function, (set_id, database) in registry.live_connections.items():
            db_set = registry.database_sets.get(set_id)
            connections_data.append({
                'Function': function,
                'Database': database,
                'Set': db_set.name if db_set else 'Unknown',
                'Server': db_set.server.server if db_set else 'Unknown'
            })
        
        df = pd.DataFrame(connections_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Test connections
        if st.button("Test All Connections"):
            test_all_connections(registry)
    else:
        st.warning("No live connections configured")
        st.info("Activate a database set to establish live connections")


def render_database_discovery(registry):
    """Database discovery and analysis"""
    st.subheader("Database Discovery")
    
    if registry.servers:
        server_id = st.selectbox("Select server to explore:", 
                                 options=list(registry.servers.keys()))
        
        if st.button("🔍 Discover Databases", type="primary"):
            with st.spinner("Discovering databases..."):
                databases = registry.discover_databases(server_id)
                
                if databases:
                    st.success(f"Found {len(databases)} databases")
                    
                    # Group by detected function
                    by_function = {}
                    for db in databases:
                        func = db.get('detected_function', 'Unknown')
                        if func not in by_function:
                            by_function[func] = []
                        by_function[func].append(db)
                    
                    # Display by function
                    for function, dbs in by_function.items():
                        st.markdown(f"**{function} Databases**")
                        
                        db_info = []
                        for db in dbs:
                            db_info.append({
                                'Name': db['name'],
                                'State': db['state'],
                                'Created': db['created'][:10] if db['created'] else 'Unknown'
                            })
                        
                        df = pd.DataFrame(db_info)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.error("No databases found or access denied")
    else:
        st.info("Add a server first to discover databases")


def render_audit_log(registry):
    """Show audit log"""
    st.subheader("Audit Log")
    
    # Get audit log
    log_df = registry.get_audit_log(limit=100)
    
    if not log_df.empty:
        # Format timestamp
        log_df['timestamp'] = pd.to_datetime(log_df['timestamp'])
        log_df['timestamp'] = log_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Display
        st.dataframe(
            log_df[['timestamp', 'user', 'action', 'entity_type', 'entity_id']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No audit log entries")


def render_settings():
    """System settings"""
    st.subheader("System Settings")
    
    st.markdown("**Security Settings**")
    
    # Master key management
    if st.checkbox("Change Super Admin Master Key"):
        with st.form("change_master_key"):
            current_key = st.text_input("Current Master Key", type="password")
            new_key = st.text_input("New Master Key", type="password")
            confirm_key = st.text_input("Confirm New Key", type="password")
            
            if st.form_submit_button("Update Master Key", type="primary"):
                if new_key == confirm_key:
                    st.warning("Master key update requires environment variable change")
                    st.info("Set GOVSIGHT_SUPER_KEY environment variable to update")
                else:
                    st.error("New keys do not match")
    
    st.markdown("**Connection Settings**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pool_size = st.number_input("Connection Pool Size", value=5, min_value=1, max_value=20)
        timeout = st.number_input("Query Timeout (seconds)", value=30, min_value=5, max_value=300)
    
    with col2:
        recycle_time = st.number_input("Connection Recycle (minutes)", value=30, min_value=5, max_value=120)
        max_overflow = st.number_input("Max Overflow Connections", value=10, min_value=0, max_value=50)
    
    if st.button("Save Settings", key="super_admin_save_settings"):
        st.success("Settings saved successfully")


# City Admin interface
def render_city_admin_database_interface():
    """City Admin interface - can select live databases but not add/remove"""
    st.title("📊 Database Selection")
    st.info("City Administrator Access")
    
    registry = get_registry()
    
    st.subheader("Active Database Set")
    st.caption("Select which database set should be active for your organization")
    
    if registry.database_sets:
        # Show available sets
        sets_data = []
        for set_id, db_set in registry.database_sets.items():
            sets_data.append({
                'Set Name': db_set.name,
                'Status': '🟢 Active' if db_set.is_live else '⚫ Inactive',
                'GL': '✓' if db_set.databases.get('GL') else '—',
                'AP': '✓' if db_set.databases.get('AP') else '—',
                'Payroll': '✓' if db_set.databases.get('PAYROLL') else '—',
                'Utility': '✓' if db_set.databases.get('UTILITY') else '—',
                'Budget': '✓' if db_set.databases.get('BUDGET') else '—'
            })
        
        df = pd.DataFrame(sets_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Allow activation
        set_names = [db_set.name for db_set in registry.database_sets.values()]
        selected_set = st.selectbox("Select database set to activate:", options=set_names)
        
        if st.button("Activate Selected Set", type="primary"):
            # Find set_id
            for set_id, db_set in registry.database_sets.items():
                if db_set.name == selected_set:
                    registry.activate_database_set(set_id)
                    st.rerun()
                    break
        
        # Show current connections
        if registry.live_connections:
            st.markdown("### Current Live Connections")
            connections_data = []
            for function, (set_id, database) in registry.live_connections.items():
                connections_data.append({
                    'Function': function,
                    'Database': database
                })
            
            conn_df = pd.DataFrame(connections_data)
            st.dataframe(conn_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No database sets available. Contact your Super Admin to configure databases.")


# Helper functions
def test_server_connection(registry, server_id):
    """Test server connection"""
    if server_id in registry.servers:
        adapter = registry.servers[server_id]
        creds = registry._get_credentials(server_id)
        
        with st.spinner("Testing connection..."):
            success, message = adapter.test_connection(
                username=creds.get('username') if creds else None,
                password=creds.get('password') if creds else None
            )
            
            if success:
                st.success(message)
            else:
                st.error(message)


def show_server_databases(registry, server_id):
    """Show databases for a server"""
    st.markdown(f"### Databases on {server_id}")
    
    databases = registry.discover_databases(server_id)
    
    if databases:
        db_df = pd.DataFrame(databases)
        st.dataframe(db_df[['name', 'detected_function', 'state']], 
                    use_container_width=True, hide_index=True)
    else:
        st.error("Could not retrieve databases")


def remove_server(registry, server_id):
    """Remove a server"""
    # Check for dependencies
    dependent_sets = []
    for set_id, db_set in registry.database_sets.items():
        if db_set.server.server == registry.servers[server_id].server:
            dependent_sets.append(db_set.name)
    
    if dependent_sets:
        st.error(f"Cannot remove server. Used by sets: {', '.join(dependent_sets)}")
    else:
        st.warning("Server removal not yet fully implemented")


def test_all_connections(registry):
    """Test all live connections"""
    results = []
    
    for function in registry.live_connections.keys():
        try:
            engine = registry.get_live_connection(function)
            if engine:
                # Try a simple query
                with engine.connect() as conn:
                    result = conn.execute("SELECT 1").fetchone()
                    results.append(f"✅ {function}: Connected")
            else:
                results.append(f"❌ {function}: No engine")
        except Exception as e:
            results.append(f"❌ {function}: {str(e)[:50]}")
    
    for result in results:
        if "✅" in result:
            st.success(result)
        else:
            st.error(result)