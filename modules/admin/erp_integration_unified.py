"""
Unified ERP Integration Hub with Database Management
Consolidates all database connections and Super Admin controls
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Import existing modules
from modules.database.connection_registry import get_registry
from modules.security.super_admin_auth import get_super_auth
from modules.database.caselle_adapter import CaselleServerAdapter
from modules.admin.super_admin_database import (
    render_super_admin_login,
    render_servers_management,
    render_database_sets,
    render_live_connections,
    render_database_discovery,
    render_audit_log,
    render_settings,
    render_city_admin_database_interface
)


def render_unified_erp_integration():
    """Main entry point for unified ERP Integration with sub-tabs"""
    
    # Get authentication status
    super_auth = get_super_auth()
    is_super = super_auth.is_super_admin()
    
    # Determine user role
    user_role = st.session_state.get("user", {}).get("role", "viewer")
    is_admin = user_role in ["admin", "finance"]
    
    # Display role banner
    if is_super:
        st.success("🔐 **Super Admin Mode** - Full database management access")
    elif is_admin:
        st.info("🏢 **City Admin Mode** - Database selection and monitoring")
    else:
        st.warning("👤 **Viewer Mode** - Read-only access")
    
    # Define sub-tabs based on role
    if is_super:
        # Super Admin gets all tabs
        sub_tabs = st.tabs([
            "📊 Overview",
            "🖥️ Servers",
            "📁 Database Sets",
            "🔄 Live Connections",
            "🔍 Discovery",
            "📝 Audit Log",
            "⚙️ Settings"
        ])
        
        with sub_tabs[0]:
            render_overview_tab(is_super=True)
        
        with sub_tabs[1]:
            registry = get_registry()
            render_servers_management(registry)
        
        with sub_tabs[2]:
            registry = get_registry()
            render_database_sets(registry)
        
        with sub_tabs[3]:
            registry = get_registry()
            render_live_connections(registry)
        
        with sub_tabs[4]:
            registry = get_registry()
            render_database_discovery(registry)
        
        with sub_tabs[5]:
            registry = get_registry()
            render_audit_log(registry)
        
        with sub_tabs[6]:
            render_settings()
    
    elif is_admin:
        # City Admin gets limited tabs
        sub_tabs = st.tabs([
            "📊 Overview",
            "📁 Database Selection", 
            "📊 Connection Status"
        ])
        
        with sub_tabs[0]:
            render_overview_tab(is_super=False)
        
        with sub_tabs[1]:
            render_city_admin_database_selection()
        
        with sub_tabs[2]:
            render_connection_status()
    
    else:
        # Viewers get minimal access
        st.info("You have read-only access to view database connection status")
        render_overview_tab(is_super=False, read_only=True)


def render_overview_tab(is_super=False, read_only=False):
    """Render the overview tab showing current database status"""
    
    st.subheader("ERP Integration Overview")
    
    registry = get_registry()
    
    # Display connection summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_servers = len(registry.servers)
        st.metric("SQL Servers", total_servers, help="Total configured SQL Server connections")
    
    with col2:
        total_sets = len(registry.database_sets)
        st.metric("Database Sets", total_sets, help="Total configured database sets")
    
    with col3:
        active_set = None
        for db_set in registry.database_sets.values():
            if db_set.is_live:
                active_set = db_set
                break
        
        if active_set:
            st.metric("Active Set", active_set.name, delta="Live", help="Currently active database set")
        else:
            st.metric("Active Set", "None", delta="Offline", help="No active database set")
    
    # Show active databases
    st.markdown("---")
    st.subheader("Active Database Connections")
    
    if active_set:
        # Create a DataFrame showing active databases
        active_data = []
        for func_type, db_config in active_set.databases.items():
            if db_config:
                active_data.append({
                    "Function": func_type,
                    "Database": db_config.get("database", "Unknown"),
                    "Server": db_config.get("server", "Unknown"),
                    "Status": "🟢 Connected"
                })
        
        if active_data:
            df = pd.DataFrame(active_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No databases configured in the active set")
    else:
        st.info("No active database set. Configure and activate a database set to begin.")
    
    # Super Admin quick actions
    if is_super and not read_only:
        st.markdown("---")
        st.subheader("Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🖥️ Add New Server", key="overview_add_server"):
                st.session_state["erp_tab_override"] = 1  # Switch to Servers tab
                st.rerun()
        
        with col2:
            if st.button("📁 Create Database Set", key="overview_create_set"):
                st.session_state["erp_tab_override"] = 2  # Switch to Database Sets tab
                st.rerun()
        
        with col3:
            if st.button("🔍 Discover Databases", key="overview_discover"):
                st.session_state["erp_tab_override"] = 4  # Switch to Discovery tab
                st.rerun()
    
    # Connection health check
    if not read_only:
        st.markdown("---")
        st.subheader("Connection Health")
        
        if st.button("🔍 Test All Connections", key="overview_test_connections"):
            test_database_connections()


def render_city_admin_database_selection():
    """City Admin interface for selecting active database set"""
    
    st.subheader("Database Set Selection")
    st.markdown("Select which database set should be active for your organization")
    
    registry = get_registry()
    
    if not registry.database_sets:
        st.warning("No database sets configured. Contact your Super Administrator.")
        return
    
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
            'Budget': '✓' if db_set.databases.get('BUDGET') else '—',
            'Created': db_set.created_at.strftime('%Y-%m-%d')
        })
    
    df = pd.DataFrame(sets_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Allow activation
    st.markdown("---")
    set_names = [db_set.name for db_set in registry.database_sets.values()]
    selected_set = st.selectbox("Select database set to activate:", 
                                options=set_names,
                                key="city_admin_set_select")
    
    if st.button("🔄 Activate Selected Set", type="primary", key="city_admin_activate"):
        # Find set_id
        for set_id, db_set in registry.database_sets.items():
            if db_set.name == selected_set:
                if registry.activate_database_set(set_id):
                    st.success(f"✓ Successfully activated '{selected_set}'")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to activate database set")
                break


def render_connection_status():
    """Display detailed connection status for City Admins"""
    
    st.subheader("Connection Status Monitor")
    
    registry = get_registry()
    
    # Get active set
    active_set = None
    for db_set in registry.database_sets.values():
        if db_set.is_live:
            active_set = db_set
            break
    
    if not active_set:
        st.warning("No active database set. Please activate a database set first.")
        return
    
    st.success(f"Active Set: **{active_set.name}**")
    
    # Test connections
    if st.button("🔍 Test All Connections", key="status_test_all"):
        test_database_connections()
    
    # Show connection details
    st.markdown("---")
    st.markdown("### Connection Details")
    
    for func_type, db_config in active_set.databases.items():
        if db_config:
            with st.expander(f"📊 {func_type} Database"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Server:**")
                    st.code(db_config.get("server", "Unknown"))
                    st.markdown("**Database:**")
                    st.code(db_config.get("database", "Unknown"))
                
                with col2:
                    st.markdown("**Port:**")
                    st.code(db_config.get("port", 1433))
                    st.markdown("**Driver:**")
                    st.code(db_config.get("driver", "SQL Server"))
                
                # Test individual connection
                if st.button(f"Test {func_type} Connection", key=f"test_{func_type}"):
                    test_single_connection(func_type, db_config)


def test_database_connections():
    """Test all active database connections"""
    
    registry = get_registry()
    
    # Get active set
    active_set = None
    for db_set in registry.database_sets.values():
        if db_set.is_live:
            active_set = db_set
            break
    
    if not active_set:
        st.error("No active database set")
        return
    
    results = []
    
    with st.spinner("Testing connections..."):
        for func_type, db_config in active_set.databases.items():
            if db_config:
                # Test connection
                try:
                    from modules.database.caselle_adapter import CaselleServerAdapter
                    adapter = CaselleServerAdapter()
                    
                    # Create test connection
                    conn = adapter.create_connection(
                        server=db_config["server"],
                        database=db_config["database"],
                        username=db_config.get("username"),
                        password=db_config.get("password"),
                        port=db_config.get("port", 1433)
                    )
                    
                    if conn:
                        conn.close()
                        results.append({
                            "Database": func_type,
                            "Status": "✅ Connected",
                            "Response Time": "< 1s"
                        })
                    else:
                        results.append({
                            "Database": func_type,
                            "Status": "❌ Failed",
                            "Response Time": "N/A"
                        })
                
                except Exception as e:
                    results.append({
                        "Database": func_type,
                        "Status": "❌ Error",
                        "Response Time": str(e)[:50]
                    })
    
    # Display results
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)


def test_single_connection(func_type, db_config):
    """Test a single database connection"""
    
    with st.spinner(f"Testing {func_type} connection..."):
        try:
            from modules.database.caselle_adapter import CaselleServerAdapter
            adapter = CaselleServerAdapter()
            
            # Create test connection
            conn = adapter.create_connection(
                server=db_config["server"],
                database=db_config["database"],
                username=db_config.get("username"),
                password=db_config.get("password"),
                port=db_config.get("port", 1433)
            )
            
            if conn:
                # Test with simple query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
                st.success(f"✅ {func_type} connection successful!")
            else:
                st.error(f"❌ {func_type} connection failed!")
        
        except Exception as e:
            st.error(f"❌ {func_type} connection error: {str(e)}")


def render_super_admin_access():
    """Entry point for Super Admin authentication"""
    
    super_auth = get_super_auth()
    
    if not super_auth.is_super_admin():
        st.subheader("🔐 Super Admin Access Required")
        st.info("Super Administrator privileges are required to manage database connections.")
        
        render_super_admin_login()
        
        if super_auth.is_super_admin():
            st.rerun()
    else:
        # Super admin is authenticated, show full interface
        render_unified_erp_integration()