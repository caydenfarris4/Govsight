"""
Database Status UI Component
Displays real-time database connection status and schema information for all 5 municipal databases.
Integrates with the /health/databases API endpoint for live status updates.
"""

import streamlit as st
import requests
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

def display_database_status():
    """
    Display comprehensive database status dashboard showing connection status,
    schema information, and verification details for all 5 municipal databases.
    """
    st.subheader("🗄️ Database Connection Status")
    
    # Fetch database status from API
    try:
        response = requests.get("http://0.0.0.0:8000/health/databases", timeout=10)
        if response.status_code == 200:
            db_status = response.json()
            display_comprehensive_status(db_status)
        else:
            st.error(f"Failed to fetch database status (HTTP {response.status_code})")
            display_fallback_status()
            
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not connect to database health API: {e}")
        display_fallback_status()
    except Exception as e:
        st.error(f"Error fetching database status: {e}")
        display_fallback_status()

def display_comprehensive_status(db_status: Dict[str, Any]):
    """Display comprehensive database status from API response."""
    
    # Overall health summary
    summary = db_status.get("summary", {})
    verification = db_status.get("verification", {})
    
    # Health status indicator
    overall_health = summary.get("overall_health", "unknown")
    health_colors = {
        "excellent": "🟢",
        "good": "🟡", 
        "needs_attention": "🟠",
        "critical_error": "🔴"
    }
    
    st.markdown(f"### {health_colors.get(overall_health, '⚪')} Overall Status: {overall_health.title()}")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Connected Databases",
            f"{summary.get('connected_databases', 0)}/{summary.get('total_databases', 0)}",
            delta=None
        )
    
    with col2:
        st.metric(
            "Tables Discovered", 
            summary.get('total_tables_discovered', 0),
            delta=None
        )
    
    with col3:
        drivers = db_status.get("drivers", {})
        all_drivers = all(drivers.values()) if drivers else False
        st.metric(
            "Driver Status",
            "All Available" if all_drivers else "Missing Drivers",
            delta=None
        )
    
    with col4:
        phase3_met = verification.get('phase3_requirements_met', False)
        st.metric(
            "Phase 3 Status",
            "✅ Complete" if phase3_met else "⏳ In Progress",
            delta=None
        )
    
    # Driver availability
    st.subheader("🔧 Database Drivers")
    driver_col1, driver_col2, driver_col3 = st.columns(3)
    
    drivers = db_status.get("drivers", {})
    with driver_col1:
        psycopg2_status = "✅ Available" if drivers.get("psycopg2") else "❌ Missing"
        st.write(f"**PostgreSQL**: {psycopg2_status}")
    
    with driver_col2:
        mysql_status = "✅ Available" if drivers.get("mysql_connector") else "❌ Missing" 
        st.write(f"**MySQL**: {mysql_status}")
    
    with driver_col3:
        pyodbc_status = "✅ Available" if drivers.get("pyodbc") else "❌ Missing"
        st.write(f"**SQL Server**: {pyodbc_status}")
    
    # Individual database status
    st.subheader("🗃️ Individual Database Status")
    
    databases = db_status.get("databases", {})
    for db_name, db_info in databases.items():
        display_database_card(db_name, db_info)
    
    # Verification details
    if verification:
        st.subheader("✅ Phase 3 Verification")
        ver_col1, ver_col2, ver_col3 = st.columns(3)
        
        with ver_col1:
            schema_available = verification.get('schema_catalog_available', False)
            st.write(f"**Schema Catalog**: {'✅' if schema_available else '❌'}")
        
        with ver_col2:
            multi_db = verification.get('multi_database_integration', False) 
            st.write(f"**Multi-DB Integration**: {'✅' if multi_db else '❌'}")
        
        with ver_col3:
            requirements_met = verification.get('phase3_requirements_met', False)
            st.write(f"**Requirements Met**: {'✅' if requirements_met else '❌'}")
    
    # Last updated timestamp
    timestamp = db_status.get("timestamp", "Unknown")
    st.caption(f"Last updated: {timestamp}")

def display_database_card(db_name: str, db_info: Dict[str, Any]):
    """Display an individual database status card."""
    
    with st.expander(f"📊 {db_info.get('display_name', db_name)}", expanded=False):
        
        # Connection status
        connection_status = db_info.get('connection_status', 'unknown')
        status_icons = {
            'connected': '🟢',
            'not_connected': '🔴', 
            'failed': '🟠',
            'error': '⚠️'
        }
        
        status_icon = status_icons.get(connection_status, '⚪')
        st.markdown(f"**Status**: {status_icon} {connection_status.title()}")
        
        # Database details
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Type**: {db_info.get('type', 'Unknown')}")
            st.write(f"**Description**: {db_info.get('description', 'No description')}")
            
            driver_available = db_info.get('driver_available', False)
            st.write(f"**Driver**: {'✅ Available' if driver_available else '❌ Missing'}")
        
        with col2:
            # Schema information
            schema_info = db_info.get('schema_info', {})
            table_count = schema_info.get('tables_count', 0)
            st.write(f"**Tables**: {table_count}")
            
            sample_tables = schema_info.get('sample_tables', [])
            if sample_tables:
                st.write(f"**Sample Tables**: {', '.join(sample_tables[:3])}")
            
            discovery_time = schema_info.get('discovery_timestamp')
            if discovery_time:
                st.write(f"**Last Discovery**: {discovery_time[:19].replace('T', ' ')}")
        
        # Connection test results
        connection_test = db_info.get('connection_test')
        if connection_test:
            if connection_test.get('success'):
                server_info = connection_test.get('server_info', 'Connected')
                st.success(f"✅ {server_info}")
            else:
                error_msg = connection_test.get('error', 'Connection failed')
                st.error(f"❌ {error_msg}")
        
        # Show any errors
        error = db_info.get('error')
        if error:
            st.error(f"Error: {error}")

def display_fallback_status():
    """Display fallback status when API is unavailable."""
    
    st.warning("⚠️ Database status API unavailable - showing static configuration")
    
    try:
        import json
        config = {}
        try:
            from modules.services.config_service import get_config_service
            svc = get_config_service()
            config = svc.get_namespace("system_settings")
        except Exception:
            for path in ["configs/system/system_settings.json", "system_settings.json"]:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        config = json.load(f)
                    break
        
        databases = config.get("database", {}).get("databases", {})
        
        for db_name, db_info in databases.items():
            with st.expander(f"📊 {db_info.get('display_name', db_name)}", expanded=False):
                
                status = db_info.get('connection_status', 'unknown')
                st.write(f"**Status**: {status}")
                st.write(f"**Type**: {db_info.get('type', 'Unknown')}")
                st.write(f"**Description**: {db_info.get('description', 'No description')}")
                
                if db_info.get('path'):
                    st.write(f"**Path**: {db_info['path']}")
                
                st.caption("Note: This is static configuration. API needed for live status.")
                
    except Exception as e:
        st.error(f"Could not load database configuration: {e}")

def run_credential_migration():
    """Run and display credential migration results."""
    
    st.subheader("🔐 Credential Security Migration")
    
    if st.button("🔄 Migrate Credentials to Environment Variables"):
        try:
            from modules.security.credential_manager import credential_manager
            
            with st.spinner("Migrating credentials..."):
                migration_result = credential_manager.migrate_plaintext_credentials()
            
            if migration_result.get("success"):
                st.success("✅ Credential migration completed successfully!")
                
                st.write("**Migration Summary:**")
                st.write(f"- Databases migrated: {len(migration_result.get('databases_migrated', []))}")
                st.write(f"- Credentials removed: {len(migration_result.get('credentials_removed', []))}")
                
                if migration_result.get("databases_migrated"):
                    st.write("**Migrated databases:**")
                    for db in migration_result["databases_migrated"]:
                        st.write(f"  - {db}")
                
            else:
                st.error("❌ Credential migration failed!")
                for error in migration_result.get("errors", []):
                    st.error(f"- {error}")
                    
        except Exception as e:
            st.error(f"Migration error: {e}")
    
    # Security verification
    if st.button("🔍 Verify Credential Security"):
        try:
            from modules.security.credential_manager import credential_manager
            
            verification = credential_manager.verify_credentials_security()
            
            if verification.get("secure"):
                st.success("✅ Credentials are properly secured!")
            else:
                st.warning("⚠️ Security issues found:")
                for issue in verification.get("issues", []):
                    st.warning(f"- {issue}")
            
            if verification.get("environment_variables_found"):
                st.info(f"Found {len(verification['environment_variables_found'])} environment variables")
            
            if verification.get("plaintext_found"):
                st.error(f"Found {len(verification['plaintext_found'])} plaintext credentials")
                
        except Exception as e:
            st.error(f"Verification error: {e}")

# Streamlit component for easy integration
def database_status_component():
    """Main component for database status display."""
    display_database_status()
    
    st.markdown("---")
    
    # Add credential management section
    run_credential_migration()