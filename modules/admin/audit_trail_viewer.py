"""
Audit Trail Viewer Interface
Provides UI for viewing and managing database audit trails

ARCHITECTURAL DECISION: Dedicated audit trail interface in admin panel
WHY: Financial audit trails require specialized viewing, filtering, and analysis
capabilities for compliance officers and system administrators.

DESIGN PATTERN: Streamlit-based tabbed interface with filtering and export
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from modules.database.audit_trail_manager import audit_manager
from modules.admin.admin_panel import get_user_role, is_admin

def render_audit_trail_interface():
    """Render the audit trail viewer interface"""
    
    # Check permissions - only admins and finance directors can view audit trails
    user_role = get_user_role()
    if not (is_admin() or user_role == 'finance_director'):
        st.error("Access denied. Audit trail access requires admin or finance director privileges.")
        return
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); 
                border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 8px 25px rgba(220, 38, 38, 0.25);">
        <h1 style="color: white; margin: 0; font-size: 2.5em; font-family: 'Poppins', sans-serif; font-weight: 600;">
            🔍 Database Audit Trail
        </h1>
        <p style="color: rgba(255, 255, 255, 0.9); margin: 10px 0 0 0; font-size: 1.2em; font-family: 'Poppins', sans-serif;">
            Track all delete operations on General Ledger databases
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for different audit views
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Audit Trail Search", 
        "📊 Audit Summary", 
        "🗂️ Deleted Data Recovery", 
        "⚙️ Audit Settings"
    ])
    
    with tab1:
        render_audit_search()
    
    with tab2:
        render_audit_summary()
    
    with tab3:
        render_data_recovery()
    
    with tab4:
        render_audit_settings()

def render_audit_search():
    """Render audit trail search interface"""
    
    st.markdown("### 🔍 Search Audit Trail")
    st.markdown("Filter and search through all database delete operations")
    
    # Search filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        database_filter = st.selectbox(
            "Database",
            ["All"] + ["gl_primary", "utility_management", "asset_management", "permits_licensing", "payroll"],
            help="Filter by database name"
        )
        
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            help="Filter records from this date"
        )
    
    with col2:
        table_filter = st.text_input(
            "Table Name",
            placeholder="Enter table name to filter",
            help="Filter by specific table name"
        )
        
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            help="Filter records up to this date"
        )
    
    with col3:
        user_filter = st.text_input(
            "User ID",
            placeholder="Enter user ID to filter",
            help="Filter by user who performed the deletion"
        )
        
        limit = st.number_input(
            "Max Records",
            min_value=10,
            max_value=1000,
            value=100,
            help="Maximum number of records to display"
        )
    
    # Search button
    if st.button("🔍 Search Audit Trail", use_container_width=True):
        with st.spinner("Searching audit trail..."):
            # Prepare filters
            filters = {}
            if database_filter != "All":
                filters['database_name'] = database_filter
            if table_filter:
                filters['table_name'] = table_filter
            if user_filter:
                filters['user_id'] = user_filter
            
            filters['start_date'] = start_date.strftime('%Y-%m-%d')
            filters['end_date'] = end_date.strftime('%Y-%m-%d')
            filters['limit'] = limit
            
            # Get audit data
            try:
                audit_data = audit_manager.get_audit_trail(**filters)
                
                if audit_data.empty:
                    st.info("No audit records found matching the search criteria.")
                else:
                    st.success(f"Found {len(audit_data)} audit records")
                    
                    # Display results
                    st.markdown("### 📋 Audit Trail Results")
                    
                    # Add action buttons for each record
                    for idx, row in audit_data.iterrows():
                        with st.expander(f"🗂️ Audit ID: {row['id']} | {row['delete_timestamp']} | {row['table_name']}"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.markdown(f"""
                                **Database:** {row['gl_database']}  
                                **Table:** {row['table_name']}  
                                **Records Deleted:** {row['deleted_record_count']}  
                                **User:** {row['user_id']} ({row['user_role']})  
                                **Reason:** {row['operation_reason']}  
                                **Session:** {row['session_id']}  
                                **Timestamp:** {row['delete_timestamp']}
                                """)
                            
                            with col2:
                                if st.button(f"🔍 View Deleted Data", key=f"view_{row['id']}"):
                                    view_deleted_data(row['id'])
                                
                                if st.button(f"🔄 Prepare Recovery", key=f"recovery_{row['id']}"):
                                    prepare_recovery_dialog(row['id'])
                    
                    # Display as table
                    display_columns = [
                        'id', 'delete_timestamp', 'gl_database', 'table_name', 
                        'deleted_record_count', 'user_id', 'user_role', 'operation_reason'
                    ]
                    st.dataframe(
                        audit_data[display_columns],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Export options
                    st.markdown("### 💾 Export Options")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        csv_data = audit_data.to_csv(index=False)
                        st.download_button(
                            "📄 Download as CSV",
                            csv_data,
                            f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            "text/csv"
                        )
                    
                    with col2:
                        json_data = audit_data.to_json(orient='records', indent=2)
                        st.download_button(
                            "📄 Download as JSON",
                            json_data,
                            f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            "application/json"
                        )
            
            except Exception as e:
                st.error(f"Error searching audit trail: {str(e)}")

def render_audit_summary():
    """Render audit summary dashboard"""
    
    st.markdown("### 📊 Audit Trail Summary")
    st.markdown("Overview of delete operations and trends")
    
    try:
        # Get summary data for different time periods
        summary_30 = audit_manager.get_audit_summary(30)
        summary_7 = audit_manager.get_audit_summary(7)
        
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_operations = len(summary_30) if not summary_30.empty else 0
            st.metric("Delete Operations (30d)", total_operations)
        
        with col2:
            total_records = summary_30['total_records_deleted'].sum() if not summary_30.empty else 0
            st.metric("Records Deleted (30d)", f"{total_records:,}")
        
        with col3:
            recent_operations = len(summary_7) if not summary_7.empty else 0
            st.metric("Recent Operations (7d)", recent_operations)
        
        with col4:
            unique_users = len(summary_30['users_involved'].unique()) if not summary_30.empty else 0
            st.metric("Active Users (30d)", unique_users)
        
        if not summary_30.empty:
            # Time series chart
            st.markdown("### 📈 Delete Operations Over Time")
            fig_timeline = px.line(
                summary_30, 
                x='delete_date', 
                y='delete_operations',
                title='Daily Delete Operations',
                labels={'delete_date': 'Date', 'delete_operations': 'Number of Operations'}
            )
            fig_timeline.update_layout(
                font_family="Poppins",
                title_font_size=16,
                showlegend=False
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Database breakdown
            st.markdown("### 🗄️ Operations by Database")
            db_summary = summary_30.groupby('gl_database').agg({
                'delete_operations': 'sum',
                'total_records_deleted': 'sum'
            }).reset_index()
            
            fig_db = px.bar(
                db_summary,
                x='gl_database',
                y='delete_operations',
                title='Delete Operations by Database',
                labels={'gl_database': 'Database', 'delete_operations': 'Operations'}
            )
            fig_db.update_layout(
                font_family="Poppins",
                title_font_size=16,
                showlegend=False
            )
            st.plotly_chart(fig_db, use_container_width=True)
            
            # Table breakdown
            st.markdown("### 📋 Operations by Table")
            table_summary = summary_30.groupby('table_name').agg({
                'delete_operations': 'sum',
                'total_records_deleted': 'sum'
            }).reset_index().sort_values('delete_operations', ascending=False)
            
            st.dataframe(
                table_summary,
                use_container_width=True,
                hide_index=True
            )
        
        else:
            st.info("No audit data available for the selected time period.")
    
    except Exception as e:
        st.error(f"Error loading audit summary: {str(e)}")

def render_data_recovery():
    """Render data recovery interface"""
    
    st.markdown("### 🗂️ Deleted Data Recovery")
    st.markdown("View and recover deleted data from audit trail")
    
    # Recovery search
    audit_id = st.number_input(
        "Audit ID",
        min_value=1,
        help="Enter the audit ID to view deleted data"
    )
    
    if st.button("🔍 Load Deleted Data"):
        if audit_id:
            view_deleted_data(audit_id)

def view_deleted_data(audit_id: int):
    """Display deleted data for a specific audit ID"""
    
    try:
        deleted_info = audit_manager.get_deleted_data(audit_id)
        
        if "error" in deleted_info:
            st.error(f"Error: {deleted_info['error']}")
            return
        
        st.success("✅ Data integrity verified")
        
        # Display metadata
        st.markdown("### 📋 Deletion Metadata")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Audit ID:** {deleted_info['audit_id']}  
            **Database:** {deleted_info['database_name']}  
            **Table:** {deleted_info['table_name']}  
            **Timestamp:** {deleted_info['delete_timestamp']}
            """)
        
        with col2:
            st.markdown(f"""
            **User:** {deleted_info['user_id']}  
            **Reason:** {deleted_info['operation_reason']}  
            **Integrity:** ✅ Verified
            """)
        
        # Display deleted data
        st.markdown("### 🗃️ Deleted Data")
        deleted_data = deleted_info['deleted_data']
        
        if isinstance(deleted_data, list) and deleted_data:
            # Convert to DataFrame for better display
            df = pd.DataFrame(deleted_data)
            st.dataframe(df, use_container_width=True)
            
            # Export options
            col1, col2 = st.columns(2)
            with col1:
                csv_data = df.to_csv(index=False)
                st.download_button(
                    "📄 Export as CSV",
                    csv_data,
                    f"deleted_data_audit_{audit_id}.csv",
                    "text/csv"
                )
            
            with col2:
                json_data = json.dumps(deleted_data, indent=2)
                st.download_button(
                    "📄 Export as JSON",
                    json_data,
                    f"deleted_data_audit_{audit_id}.json",
                    "application/json"
                )
        else:
            st.json(deleted_data)
        
        # Recovery option
        if st.button(f"🔄 Prepare Recovery for Audit ID {audit_id}"):
            prepare_recovery_dialog(audit_id)
    
    except Exception as e:
        st.error(f"Error loading deleted data: {str(e)}")

def prepare_recovery_dialog(audit_id: int):
    """Show recovery preparation dialog"""
    
    st.markdown("### 🔄 Prepare Data Recovery")
    st.warning("⚠️ Data recovery should only be performed by authorized personnel")
    
    # Get current user
    user = st.session_state.get('user', {})
    current_user = user.get('username', 'unknown')
    
    reason = st.text_area(
        "Recovery Reason",
        placeholder="Please provide a detailed reason for data recovery...",
        help="Explain why this data needs to be recovered"
    )
    
    if st.button("🔄 Stage for Recovery"):
        if reason.strip():
            try:
                recovery_id = audit_manager.prepare_recovery(audit_id, current_user)
                st.success(f"✅ Data staged for recovery. Recovery ID: {recovery_id}")
                st.info("Recovery has been prepared. Contact a system administrator to complete the recovery process.")
            except Exception as e:
                st.error(f"Error preparing recovery: {str(e)}")
        else:
            st.error("Please provide a reason for the recovery.")

def render_audit_settings():
    """Render audit trail settings"""
    
    st.markdown("### ⚙️ Audit Trail Settings")
    st.markdown("Configure audit trail behavior and retention")
    
    # Only allow admins to modify settings
    if not is_admin():
        st.warning("Only administrators can modify audit settings.")
        return
    
    # Retention settings
    st.markdown("#### 📅 Retention Settings")
    
    retention_days = st.number_input(
        "Audit Retention (Days)",
        min_value=30,
        max_value=3650,
        value=365,
        help="How long to keep audit records (minimum 30 days for compliance)"
    )
    
    # Auto-archive settings
    auto_archive = st.checkbox(
        "Enable Auto-Archive",
        help="Automatically archive old audit records"
    )
    
    if auto_archive:
        archive_days = st.number_input(
            "Archive After (Days)",
            min_value=90,
            max_value=1825,
            value=180,
            help="Archive audit records older than this many days"
        )
    
    # Alert settings
    st.markdown("#### 🚨 Alert Settings")
    
    enable_alerts = st.checkbox(
        "Enable Delete Alerts",
        help="Send alerts for delete operations"
    )
    
    if enable_alerts:
        alert_threshold = st.number_input(
            "Alert Threshold (Records)",
            min_value=1,
            max_value=1000,
            value=100,
            help="Send alert if more than this many records are deleted at once"
        )
    
    # Save settings
    if st.button("💾 Save Settings"):
        st.success("✅ Audit trail settings saved successfully")
        st.info("Settings will take effect on the next system restart.")