"""
Data Sources Manager for Admin Panel
Provides UI for managing the unified data adapter with Caselle API and file import support
"""
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def render_data_sources_manager():
    """Render the main data sources management interface"""
    st.markdown("## Data Sources Management")
    st.markdown("Configure and monitor data connections for municipal financial data")
    
    tabs = st.tabs(["Status Overview", "Caselle ERP", "File Import", "Import History", "Report Archive"])
    
    with tabs[0]:
        render_status_overview()
    
    with tabs[1]:
        render_caselle_config()
    
    with tabs[2]:
        render_file_import()
    
    with tabs[3]:
        render_import_history()
    
    with tabs[4]:
        render_report_archive()

def render_status_overview():
    """Show overall data adapter health status"""
    st.markdown("### System Health")
    
    try:
        from modules.data_adapter.unified_adapter import UnifiedDataAdapter
        adapter = UnifiedDataAdapter()
        health = adapter.health_check()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Primary Source")
            source_type = health.get("source_type", "unknown")
            if source_type == "caselle":
                st.success("Caselle ERP API")
            elif source_type == "file_import":
                st.info("File Import System")
            else:
                st.warning("Not Configured")
        
        with col2:
            st.markdown("#### Caselle API")
            caselle_status = health.get("caselle_api", {})
            if caselle_status.get("configured"):
                if caselle_status.get("connected"):
                    st.success("Connected")
                else:
                    st.error("Configured but not connected")
            else:
                st.info("Not configured - using file import")
        
        with col3:
            st.markdown("#### Report Archive")
            archive_status = health.get("archive", {})
            if archive_status.get("status") == "active":
                st.success(f"Active - {archive_status.get('session_count', 0)} sessions")
            else:
                st.warning("Inactive")
        
        st.divider()
        
        file_status = health.get("file_importer", {})
        pending_count = file_status.get("pending_files", 0)
        
        if pending_count > 0:
            st.warning(f"**{pending_count} files pending import** in `imports/incoming/` folder")
            if st.button("Process Pending Files", type="primary"):
                with st.spinner("Processing files..."):
                    results = adapter.process_pending_imports(auto_archive=True)
                    success_count = sum(1 for r in results if r.get("success"))
                    st.success(f"Processed {len(results)} files: {success_count} successful")
                    st.rerun()
        else:
            st.success("No pending imports - system up to date")
        
        st.divider()
        st.markdown("#### Available Data Years")
        years = adapter.get_available_years()
        if years:
            st.write(", ".join(str(y) for y in sorted(years, reverse=True)))
        else:
            st.info("No historical data imported yet")
            
    except Exception as e:
        st.error(f"Error loading data adapter status: {e}")
        st.info("The data adapter may not be properly initialized. Check the configuration.")

def render_caselle_config():
    """Configure Caselle ERP API connection"""
    st.markdown("### Caselle ERP Configuration")
    st.markdown("Connect to your Caselle ERP system for real-time data access")
    
    config_path = "configs/data_adapter_config.json"
    
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except:
            config = {}
    
    caselle_config = config.get("caselle_api", {})
    
    api_key_configured = bool(os.environ.get("CASELLE_API_KEY"))
    
    st.markdown("#### API Key Status")
    if api_key_configured:
        st.success("API Key is configured securely in environment secrets")
    else:
        st.warning("API Key not configured")
        st.info("""
        **To configure the Caselle API Key securely:**
        1. Go to the Secrets tab in Replit (lock icon in sidebar)
        2. Add a new secret with key: `CASELLE_API_KEY`
        3. Paste your Caselle API key as the value
        4. The key will be stored securely and never exposed in config files
        """)
    
    st.divider()
    
    with st.form("caselle_config_form"):
        st.markdown("#### Connection Settings")
        st.caption("Non-sensitive configuration stored in config file")
        
        api_url = st.text_input(
            "API Base URL", 
            value=caselle_config.get("base_url", ""),
            placeholder="https://api.caselle.com/v1",
            help="Your Caselle API endpoint URL"
        )
        
        client_id = st.text_input(
            "Client ID",
            value=caselle_config.get("client_id", ""),
            placeholder="Your municipality's client ID"
        )
        
        st.markdown("#### Connection Options")
        
        col1, col2 = st.columns(2)
        with col1:
            timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=5,
                max_value=120,
                value=caselle_config.get("timeout", 30)
            )
        
        with col2:
            retry_count = st.number_input(
                "Retry Attempts",
                min_value=0,
                max_value=5,
                value=caselle_config.get("retry_count", 3)
            )
        
        submitted = st.form_submit_button("Save Configuration", type="primary")
        
        if submitted:
            new_config = config.copy()
            new_config["caselle_api"] = {
                "enabled": bool(api_url) and api_key_configured,
                "base_url": api_url,
                "client_id": client_id,
                "timeout": timeout,
                "retry_count": retry_count
            }
            
            os.makedirs("configs", exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(new_config, f, indent=2)
            
            if api_url and api_key_configured:
                st.success("Configuration saved successfully!")
            elif api_url and not api_key_configured:
                st.warning("Configuration saved. Add CASELLE_API_KEY secret to enable connection.")
            else:
                st.info("Configuration cleared. File import will be used as data source.")
            st.rerun()
    
    if caselle_config.get("base_url") and api_key_configured:
        st.divider()
        st.markdown("#### Test Connection")
        
        if st.button("Test Caselle Connection"):
            with st.spinner("Testing connection..."):
                try:
                    from modules.data_adapter.caselle_client import CaselleAPIClient
                    client = CaselleAPIClient()
                    result = client.test_connection()
                    if result.get("connected"):
                        st.success("Connection successful!")
                    else:
                        st.error(f"Connection failed: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Connection test failed: {e}")
    else:
        st.info("Configure Caselle API credentials above, or use the File Import system as your data source.")

def render_file_import():
    """Manage file-based data import"""
    st.markdown("### File Import System")
    st.markdown("Import financial reports from CSV or PDF exports")
    
    import_tabs = st.tabs(["Manual Upload", "Scheduled Auto-Import"])
    
    with import_tabs[0]:
        render_manual_upload()
    
    with import_tabs[1]:
        render_scheduled_import()

def render_manual_upload():
    """Manual file upload interface"""
    import_folder = "imports/incoming"
    os.makedirs(import_folder, exist_ok=True)
    
    st.markdown("#### Upload Files")
    
    uploaded_files = st.file_uploader(
        "Drop CSV or PDF files here",
        type=["csv", "pdf"],
        accept_multiple_files=True,
        help="Supported formats: General Ledger exports, Budget reports, Payroll summaries"
    )
    
    if uploaded_files:
        col1, col2 = st.columns(2)
        with col1:
            fiscal_year = st.number_input(
                "Fiscal Year",
                min_value=2000,
                max_value=2100,
                value=datetime.now().year
            )
        with col2:
            report_type = st.selectbox(
                "Report Type (optional - auto-detect if blank)",
                options=["Auto-Detect", "general_ledger", "budget", "payroll", "ap_ar", "utility_billing", "fixed_assets"],
                index=0
            )
        
        if st.button("Upload and Import", type="primary"):
            with st.spinner("Processing files..."):
                try:
                    from modules.data_adapter.unified_adapter import UnifiedDataAdapter
                    adapter = UnifiedDataAdapter()
                    
                    results = []
                    for file in uploaded_files:
                        temp_path = os.path.join(import_folder, file.name)
                        with open(temp_path, 'wb') as f:
                            f.write(file.getbuffer())
                        
                        result = adapter.import_file(
                            file_path=temp_path,
                            report_type=None if report_type == "Auto-Detect" else report_type,
                            fiscal_year=fiscal_year,
                            auto_archive=True
                        )
                        results.append({"file": file.name, **result})
                    
                    success_count = sum(1 for r in results if r.get("success"))
                    st.success(f"Imported {success_count} of {len(results)} files successfully")
                    
                    for result in results:
                        if result.get("success"):
                            st.write(f"- {result['file']}: {result.get('result', {}).get('record_count', 0)} records")
                        else:
                            st.error(f"- {result['file']}: {result.get('result', {}).get('error', 'Unknown error')}")
                    
                except Exception as e:
                    st.error(f"Import failed: {e}")
    
    st.divider()
    st.markdown("#### Pending Files")
    
    pending_files = []
    if os.path.exists(import_folder):
        for f in os.listdir(import_folder):
            if f.endswith(('.csv', '.pdf')):
                file_path = os.path.join(import_folder, f)
                stat = os.stat(file_path)
                pending_files.append({
                    "File": f,
                    "Size": f"{stat.st_size / 1024:.1f} KB",
                    "Modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
    
    if pending_files:
        st.dataframe(pd.DataFrame(pending_files), use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Process All Pending"):
                with st.spinner("Processing..."):
                    try:
                        from modules.data_adapter.unified_adapter import UnifiedDataAdapter
                        adapter = UnifiedDataAdapter()
                        results = adapter.process_pending_imports(auto_archive=True)
                        st.success(f"Processed {len(results)} files")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        with col2:
            if st.button("Clear Pending Files", type="secondary"):
                for f in os.listdir(import_folder):
                    os.remove(os.path.join(import_folder, f))
                st.success("Cleared pending files")
                st.rerun()
    else:
        st.info("No files pending import")
    
    st.divider()
    st.markdown("#### Import Templates")
    st.markdown("Download CSV templates for manual data entry:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("General Ledger Template"):
            template_data = {
                "required_columns": ["Date", "Account", "Description", "Debit", "Credit", "Fund", "Department"],
                "example_row": ["2025-01-15", "101-4100", "Revenue Receipt", "", "5000.00", "General", "Administration"]
            }
            st.json(template_data)
    
    with col2:
        if st.button("Budget Template"):
            template_data = {
                "required_columns": ["Account", "Description", "FY_Budget", "FY_Actual", "Variance"],
                "example_row": ["101-5100", "Salaries", "500000.00", "485000.00", "15000.00"]
            }
            st.json(template_data)
    
    with col3:
        if st.button("Payroll Template"):
            template_data = {
                "required_columns": ["Employee_ID", "Name", "Department", "Position", "Gross_Pay", "Period"],
                "example_row": ["E001", "John Smith", "Public Works", "Director", "4500.00", "2025-PP01"]
            }
            st.json(template_data)

def render_scheduled_import():
    """Configure scheduled auto-import from ERP exports"""
    st.markdown("#### Scheduled Auto-Import")
    st.markdown("Configure automatic import of files exported by your ERP system")
    
    try:
        from modules.data_adapter.file_watcher import get_file_watcher
        watcher = get_file_watcher()
        status = watcher.get_status()
        config = status.get("config", {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if config.get("enabled"):
                st.success("Auto-Import: ENABLED")
            else:
                st.warning("Auto-Import: DISABLED")
        
        with col2:
            last_check = status.get("last_check")
            if last_check:
                st.info(f"Last Check: {last_check[:16]}")
            else:
                st.info("Last Check: Never")
        
        with col3:
            pending = status.get("pending_count", 0)
            if pending > 0:
                st.warning(f"Pending Files: {pending}")
            else:
                st.success("Pending Files: 0")
        
        st.divider()
        
        with st.form("auto_import_config"):
            st.markdown("#### Configuration")
            
            enabled = st.checkbox(
                "Enable Scheduled Auto-Import",
                value=config.get("enabled", False),
                help="When enabled, the system will automatically check for and import new files"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                watch_folder = st.text_input(
                    "Watch Folder Path",
                    value=config.get("watch_folder", "imports/incoming"),
                    help="Folder where your ERP exports files. Can be a local path or network share."
                )
                
                interval_options = {
                    "Every 15 minutes": 0.25,
                    "Every 30 minutes": 0.5,
                    "Every hour": 1,
                    "Every 2 hours": 2,
                    "Every 4 hours": 4,
                    "Every 6 hours": 6,
                    "Every 12 hours": 12,
                    "Once daily": 24
                }
                
                current_interval = config.get("check_interval_hours", 1)
                default_label = next(
                    (k for k, v in interval_options.items() if v == current_interval),
                    "Every hour"
                )
                
                interval_label = st.selectbox(
                    "Check Frequency",
                    options=list(interval_options.keys()),
                    index=list(interval_options.keys()).index(default_label),
                    help="How often to check for new files"
                )
                check_interval = interval_options[interval_label]
            
            with col2:
                archive_folder = st.text_input(
                    "Archive Folder (processed files)",
                    value=config.get("archive_folder", "imports/processed"),
                    help="Where to move files after successful import"
                )
                
                default_fiscal_year = st.number_input(
                    "Default Fiscal Year",
                    min_value=2000,
                    max_value=2100,
                    value=config.get("default_fiscal_year") or datetime.now().year,
                    help="Fiscal year to use if not detected from file"
                )
            
            auto_archive = st.checkbox(
                "Move processed files to archive folder",
                value=config.get("auto_archive", True),
                help="Automatically move successfully imported files to archive"
            )
            
            submitted = st.form_submit_button("Save Configuration", type="primary")
            
            if submitted:
                result = watcher.configure(
                    enabled=enabled,
                    watch_folder=watch_folder,
                    check_interval_hours=check_interval,
                    archive_folder=archive_folder,
                    auto_archive=auto_archive,
                    default_fiscal_year=default_fiscal_year
                )
                
                if result.get("success"):
                    st.success("Configuration saved!")
                    st.rerun()
                else:
                    st.error("Failed to save configuration")
        
        st.divider()
        st.markdown("#### Manual Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Check Now", type="primary", help="Immediately check for and process new files"):
                with st.spinner("Checking for new files..."):
                    result = watcher.check_and_process(force=True)
                    if result.get("files_processed", 0) > 0:
                        st.success(f"Imported {result['files_processed']} files")
                    elif result.get("files_found", 0) == 0:
                        st.info("No new files found")
                    else:
                        st.warning(f"Found {result['files_found']} files, {result['files_failed']} failed")
                    st.rerun()
        
        with col2:
            pending_files = status.get("pending_files", [])
            if pending_files:
                st.write("**Pending files:**")
                for f in pending_files[:5]:
                    st.write(f"- {f}")
                if len(pending_files) > 5:
                    st.write(f"...and {len(pending_files) - 5} more")
        
        if status.get("last_import_results"):
            st.divider()
            st.markdown("#### Recent Auto-Import Results")
            results_df = pd.DataFrame(status["last_import_results"])
            if not results_df.empty:
                st.dataframe(results_df, use_container_width=True)
                
    except Exception as e:
        st.error(f"Error loading auto-import configuration: {e}")
        st.info("The file watcher service may not be properly initialized.")

def render_import_history():
    """Show import history and session details"""
    st.markdown("### Import History")
    
    try:
        from modules.data_adapter.unified_adapter import UnifiedDataAdapter
        adapter = UnifiedDataAdapter()
        history = adapter.get_import_history(limit=50)
        
        if history:
            df = pd.DataFrame(history)
            
            if "imported_at" in df.columns:
                df["imported_at"] = pd.to_datetime(df["imported_at"]).dt.strftime("%Y-%m-%d %H:%M")
            
            display_cols = ["filename", "report_type", "fiscal_year", "record_count", "imported_at", "status"]
            available_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(df[available_cols] if available_cols else df, use_container_width=True)
        else:
            st.info("No import history available")
            
    except Exception as e:
        st.error(f"Error loading import history: {e}")

def render_report_archive():
    """View and manage the report archive database"""
    st.markdown("### Report Archive")
    st.markdown("Historical financial data stored for multi-year analysis")
    
    try:
        from modules.data_adapter.report_archive import ReportArchive
        archive = ReportArchive()
        
        sessions = archive.get_sessions(limit=20)
        
        if sessions:
            st.markdown("#### Recent Archive Sessions")
            df = pd.DataFrame(sessions)
            
            if "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
            
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            st.markdown("#### Query Archive")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                query_type = st.selectbox("Report Type", ["general_ledger", "budget", "payroll"])
            with col2:
                years = archive.get_available_years(query_type)
                query_year = st.selectbox("Fiscal Year", options=years if years else [datetime.now().year])
            with col3:
                limit = st.number_input("Limit", min_value=10, max_value=1000, value=100)
            
            if st.button("Query Archive"):
                data = archive.get_records(
                    report_type=query_type,
                    fiscal_year=query_year,
                    limit=limit
                )
                if data:
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                else:
                    st.info("No records found for the selected criteria")
        else:
            st.info("No archive sessions yet. Import files to build your historical archive.")
            
    except Exception as e:
        st.error(f"Error loading archive: {e}")
        st.info("The report archive database may need to be initialized.")
